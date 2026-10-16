"""Long inputs, as docs/benchmarks.md ("Long inputs") describes.

Run on rank 0 against the loopback API. The prompt is a ledger of numbered lines after the system message
`You are a careful archivist. Read the ledger.`, at temperature 0 and effort low, with one passphrase in
the middle (--passphrases 1: not streamed, up to 512 tokens) or three at one twentieth from the start, the
middle and one twentieth from the end (--passphrases 3: streamed, up to 256 tokens). --lines gives the
ledger's line count; --tokens fits it to that many prompt tokens or fewer with the engine's /tokenize.
The engine has no endpoint that drops its kept prompts, so a short unrelated request goes first and the
row's `cached` shows whether the long prompt resumed one. Correct when the reply contains every
passphrase. The row carries the time to the first streamed token (`ttft`, streamed only; when not
streamed it is the `ttft` of rank 0's `[tensorfold] done` line), the request's time at the client, the
prompt and cached tokens, the reply's `tensorfold` fields prefill_s, heat_wait_s and cached, and the
start and end epochs. Exit 0 when correct, 1 when not.

    python -m glm53_tf long-input --passphrases 1 --lines 8806          (199,652 tokens, 1.x's text)
    python -m glm53_tf long-input --passphrases 3 --tokens 500000 --out ../records/<run>/long.jsonl

Environment: BASE (default http://127.0.0.1:8095), MODEL (default glm-tf), TENSORFOLD_API_KEY (sent as
the bearer token when set). The texts, requests and timeouts are those of the scripts that took the
release's figures, copied: one passphrase is 1.x's text, three are 1.x's TP=3 window check.
"""

import argparse
import json
import os
import time
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8095")
MODEL = os.environ.get("MODEL", "glm-tf")
SYSTEM = "You are a careful archivist. Read the ledger."
LINE = "Ledger {0}: the river barge delivered sacks of barley to the northern granary at dusk."
ONE = {"middle": "AMBER-FALCON-4817"}
THREE = {
    "start": "AMBER-FALCON-4817",
    "middle": "COBALT-HERON-2093",
    "end": "SAFFRON-LYNX-7731",
}
KEPT = ("prefill_s", "heat_wait_s", "cached")


def auth():
    """The server's API key, when TENSORFOLD_API_KEY is set where the check runs."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def post(path, body, timeout):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **auth()},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def one_messages(lines):
    half = lines // 2
    needle = f"IMPORTANT: the passphrase for the archive is {ONE['middle']}."
    text = "\n".join(LINE.format(i) for i in range(half)) + "\n" + needle + "\n"
    text += "\n".join(LINE.format(i) for i in range(half, lines))
    question = "What is the passphrase for the archive? Reply with the passphrase only."
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": text + "\n\n" + question},
    ]


def three_messages(lines):
    rows = [LINE.format(i) for i in range(lines)]
    at = {"start": lines // 20, "middle": lines // 2, "end": lines - lines // 20}
    # Last position first, so each passphrase goes before the ledger line at its position.
    for where in sorted(THREE, key=lambda w: -at[w]):
        rows.insert(
            at[where],
            f"IMPORTANT: the {where} passphrase of the archive is {THREE[where]}.",
        )
    question = "List the start, middle and end passphrases of the archive, one per line, nothing else."
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "\n".join(rows) + "\n\n" + question},
    ]


def tokenize(messages):
    with post("/tokenize", {"model": MODEL, "messages": messages}, 600) as r:
        return json.load(r)["count"]


def fit(target, build, count):
    """The line count whose prompt is at most `target` tokens, and its tokens: estimated
    from 2,000 lines, then lowered until the count fits."""
    per = count(build(2000)) / 2000
    lines = int(target / per)
    n = count(build(lines))
    while n > target:
        lines -= max(1, int((n - target) / per) + 1)
        n = count(build(lines))
    return lines, n


def found(content, passphrases):
    return {where: value in (content or "") for where, value in passphrases.items()}


def kept(block):
    """The fields of the reply's `tensorfold` block the row keeps."""
    return {k: v for k, v in (block or {}).items() if k in KEPT}


def evict():
    """A short unrelated request, so that the long prompt cannot resume a kept one."""
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"Say ok. {time.time()}"}],
        "max_tokens": 4,
        "temperature": 0,
        "reasoning_effort": "low",
    }
    with post("/v1/chat/completions", body, 300) as r:
        r.read()


def whole(messages):
    body = {
        "model": MODEL,
        "stream": False,
        "temperature": 0,
        "max_tokens": 512,
        "reasoning_effort": "low",
        "messages": messages,
    }
    start = time.monotonic()
    with post("/v1/chat/completions", body, 3600) as r:
        reply = json.load(r)
    elapsed = time.monotonic() - start
    choice = reply["choices"][0]
    return {
        "usage": reply.get("usage") or {},
        "ttft": None,
        "elapsed": round(elapsed, 3),
        "finish_reason": choice.get("finish_reason"),
        "content": choice["message"].get("content"),
        "block": reply.get("tensorfold"),
    }


def streamed(messages):
    body = {
        "model": MODEL,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0,
        "max_tokens": 256,
        "reasoning_effort": "low",
        "messages": messages,
    }
    start = time.monotonic()
    first = None
    content = ""
    usage = {}
    finish = None
    block = None
    with post("/v1/chat/completions", body, 5400) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            if chunk.get("tensorfold"):
                block = chunk["tensorfold"]
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if first is None and (
                    delta.get("content")
                    or delta.get("reasoning_content")
                    or delta.get("reasoning")
                ):
                    first = time.monotonic()
                content += delta.get("content") or ""
                finish = choice.get("finish_reason") or finish
    end = time.monotonic()
    return {
        "usage": usage,
        "ttft": round(first - start, 3) if first is not None else None,
        "elapsed": round(end - start, 3),
        "finish_reason": finish,
        "content": content,
        "block": block,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--passphrases", type=int, choices=(1, 3), required=True)
    size = parser.add_mutually_exclusive_group(required=True)
    size.add_argument("--lines", type=int, help="the ledger's line count")
    size.add_argument(
        "--tokens", type=int, help="fit the line count to this many tokens"
    )
    parser.add_argument("--out", help="a JSONL file that receives the row")
    args = parser.parse_args(argv)
    build, passphrases, request = (
        (one_messages, ONE, whole)
        if args.passphrases == 1
        else (three_messages, THREE, streamed)
    )
    lines, tokens = args.lines, None
    if args.tokens is not None:
        lines, tokens = fit(args.tokens, build, tokenize)
    evict()
    start_epoch = time.time()
    reply = request(build(lines))
    usage = reply["usage"]
    hits = found(reply["content"], passphrases)
    row = {
        "passphrases": args.passphrases,
        "lines": lines,
        "tokens": tokens,
        "prompt_tokens": usage.get("prompt_tokens"),
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "completion_tokens": usage.get("completion_tokens"),
        "ttft": reply["ttft"],
        "elapsed": reply["elapsed"],
        "finish_reason": reply["finish_reason"],
        "content": reply["content"],
        "found": hits,
        "correct": all(hits.values()),
        "tensorfold": kept(reply["block"]),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }
    if args.out:
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)
    return 0 if row["correct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
