"""The decode check after a switch: 512 greedy tokens after a fixed ~2,048-token prompt, with the completion.

Run on rank 0 against the loopback API, once per task type (PROMPT_KIND=count|prose|code), SAMPLES times at
temperature 0. Each sample prints one JSON line with the speed, the hash of the completion text and the
server's hash of its token ids (`token_sha256` in the reply's `tensorfold` block: the SHA-256 of the ids as
comma-separated decimals, so it does not compare with 2.x's records); the summary carries the MTP acceptance
length over the run, 1 + accepted / draft rounds, from each reply's `speculative` block (`rounds`,
`accepted`; `acceptance_from` says so, and `acceptance_null` why a run has none). TOKENS_OUT, a path,
receives the completion text of every sample, so two launches can be compared at their first diverging
character with `python -m glm53_tf decode-divergence` (the server returns no token ids). The engine keeps
prompts in a cache sized in GiB, with no request field or endpoint that drops them, so a sample after the
first may resume the prompt kept before it: each row's `cached` says so and the summary counts those rows
(`resumed`); a resumed prompt gives the same tokens as a fresh one. Within a launch the samples agree, and
across launches the hashes are compared with the previous launch of the same profile.

    PROMPT_KIND=prose SAMPLES=3 TOKENS_OUT=../records/<run>/tokens-prose.json python -m glm53_tf decode-check

Environment: BASE (default http://127.0.0.1:8095), MODEL (default glm-tf), PROMPT_TOKENS (2048),
MAX_TOKENS (512), SAMPLES (3). The BASE and MODEL defaults are scripts/serve.sh's on rank 0. The prompt, the
samples and the text hash are those of 1.x's v1/tools/decode_check.py, from which this one split for
TensorFold, so the same measurement reads the same on every line.
"""

import argparse
import hashlib
import json
import os
import statistics
import time
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8095")
MODEL = os.environ.get("MODEL", "glm-tf")
PROMPT_TOKENS = int(os.environ.get("PROMPT_TOKENS", "2048"))
SAMPLES = int(os.environ.get("SAMPLES", "3"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "512"))
KIND = os.environ.get("PROMPT_KIND", "count")
TASKS = {
    "count": "Count upward from one, one number per line.",
    "prose": "上の行は無視して、日本の古代の道路網と現代の物流網の関係について、"
    "具体例を挙げながら随筆を書いてください。段落を分け、最後まで書き切ってください。",
    "code": "Ignore the lines above. Write a complete Python module implementing an LRU "
    "cache with TTL expiry, a thread-safe API, docstrings, type hints and unit tests.",
}
TEMPLATE = {"reasoning_effort": "low", "clear_thinking": True}


def auth():
    """The server's API key, when TENSORFOLD_API_KEY is set where the check runs (a server
    started with one refuses requests without it)."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **auth()},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def prompt_text():
    # About 10 tokens per line on this tokenizer; the usage field gives the exact count.
    lines = "".join(
        f"measurement line {i} of the fixed decode prompt.\n"
        for i in range(PROMPT_TOKENS // 10)
    )
    return f"{lines}{TASKS[KIND]}"


def decode(prompt):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "ignore_eos": True,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": TEMPLATE,
    }
    start = time.monotonic()
    first = None
    block = {}
    usage = None
    text = hashlib.sha256()
    pieces = []
    with post("/v1/chat/completions", body) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            # the engine's two blocks ride the chunk that ends the reply, before usage
            block.update(chunk.get("tensorfold") or {})
            block.update(chunk.get("speculative") or {})
            choice = (chunk.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            # a draft round's chunk can end the reasoning and start the content: keep both, reasoning first
            # (reasoning_content and reasoning are one field under two names)
            piece = (delta.get("reasoning_content") or delta.get("reasoning") or "") + (
                delta.get("content") or ""
            )
            if piece:
                text.update(piece.encode())
                pieces.append(piece)
                if first is None:
                    first = time.monotonic()
    end = time.monotonic()
    tokens = usage["completion_tokens"]
    row = {
        "kind": "decode",
        "prompt_tokens": usage["prompt_tokens"],
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "completion_tokens": tokens,
        "ttft": round(first - start, 3),
        "seconds_after_first": round(end - first, 3),
        "tok_per_s": round((tokens - 1) / (end - first), 2),
        "completion_sha256": text.hexdigest()[:16],
        "token_sha256": (block.get("token_sha256") or "")[:16] or None,
    }
    return row, {"text": "".join(pieces)}, block or None


def acceptance(blocks):
    """The acceptance length and the keys it adds to the summary: the sum of the replies'
    `speculative` blocks, exact per request (the engine's `/metrics` has no draft rounds).
    Without drafts, or with a reply that has no block, it is null with the reason."""
    extra = {"acceptance_from": "speculative reply blocks"}
    if not all(b and "rounds" in b and "accepted" in b for b in blocks):
        return None, dict(extra, acceptance_null="a reply without rounds/accepted")
    rounds = sum(b["rounds"] for b in blocks)
    if not rounds or not sum(b.get("drafted", 0) for b in blocks):
        return None, dict(extra, acceptance_null="no drafts")
    return round(1 + sum(b["accepted"] for b in blocks) / rounds, 3), extra


def main(argv=None):
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    ).parse_args(argv)
    prompt = prompt_text()
    rows = []
    fulls = []
    blocks = []
    for _ in range(SAMPLES):
        row, full, block = decode(prompt)
        rows.append(row)
        fulls.append(full)
        blocks.append(block)
        print(json.dumps(row), flush=True)
    if os.environ.get("TOKENS_OUT"):
        with open(os.environ["TOKENS_OUT"], "w", encoding="utf-8") as f:
            json.dump(
                {"kind": KIND, "samples": [dict(r, **x) for r, x in zip(rows, fulls)]},
                f,
                ensure_ascii=False,
            )
    speeds = [r["tok_per_s"] for r in rows]
    length, extra = acceptance(blocks)
    print(
        json.dumps(
            {
                "summary": {
                    "samples": len(rows),
                    "kind": KIND,
                    "median_tok_per_s": round(statistics.median(speeds), 2),
                    "min_tok_per_s": min(speeds),
                    "max_tok_per_s": max(speeds),
                    "acceptance_length": length,
                    "distinct_completions": len({r["completion_sha256"] for r in rows}),
                    "distinct_token_sha256": len({r["token_sha256"] for r in rows}),
                    "resumed": sum(1 for r in rows if r["cached"]),
                    **extra,
                },
                "all": speeds,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
