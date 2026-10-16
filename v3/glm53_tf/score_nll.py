"""Score the NLL set (config/nll_set.json) teacher-forced on a running server: TensorFold or vLLM.

Both engines get the same token ids (the checkpoint's tokenizer.json, special tokens added) on
/v1/completions with prompt_logprobs, read by glm53_tf.agreement with each text twice, so the
self-agreement shows how far the server moves by itself. Prints the NLL of each domain, weighted by
its positions, and writes the full result. Exit status 2 when the tokenizer or a text is not the
one the set was built with, 1 when a request failed.

    python -m glm53_tf score-nll --url http://127.0.0.1:8095 \\
        --tokenizer <checkpoint snapshot>/tokenizer.json --out ../records/<run>/nll.json

The arguments and the scoring are 1.x's v1/tools/score_nll_set.py (this one also sends the API key); the set is a byte copy
of 1.x's, so the two lines' figures compare.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from . import agreement
from .config import LINE

SET = LINE / "config/nll_set.json"
DOMAINS = ("ja", "en", "code", "math")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def problems(data, tokenizer_bytes):
    """Why ``data`` cannot be scored as built; ``tokenizer_bytes`` None skips that check."""
    found = []
    if (
        tokenizer_bytes is not None
        and sha256(tokenizer_bytes) != data["tokenizer"]["sha256"]
    ):
        found.append("tokenizer.json differs from the one the set was built with")
    for t in data["texts"]:
        if sha256(t["text"].encode("utf-8")) != t["sha256"]:
            found.append(f"text {t['name']} differs from its recorded sha256")
    return found


def score(data, tokenize, complete):
    """(summary per domain, agreement.run's result) for the set's texts."""
    texts = {t["name"]: t["text"] for t in data["texts"]}
    result = agreement.run(tokenize, complete, texts=texts)
    return summarize(data, result), result


def summarize(data, result):
    """Each domain's NLL over the first scored repeat of its texts, weighted by positions."""
    domain = {t["name"]: t["domain"] for t in data["texts"]}
    first = {}  # each text's first scored repeat: (summed NLL, positions)
    for row in result["texts"]:
        if "error" not in row and row["name"] not in first:
            positions = len(row["logprobs"])
            first[row["name"]] = (row["mean_nll"] * positions, positions)
    summary = {}
    for d in DOMAINS:
        names = [n for n in domain if domain[n] == d and n in first]
        if not names:
            continue
        positions = sum(first[n][1] for n in names)
        summary[d] = {
            "mean_nll": round(sum(first[n][0] for n in names) / positions, 4),
            "positions": positions,
            "texts": {n: round(first[n][0] / first[n][1], 4) for n in names},
        }
    return summary


def post(url, path, body=None, timeout=900.0):
    data = None if body is None else json.dumps(body).encode()
    # The server's API key, when TENSORFOLD_API_KEY is set where this runs.
    key = os.environ.get("TENSORFOLD_API_KEY")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url.rstrip("/") + path, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--set", type=Path, default=SET)
    parser.add_argument("--model", help="model id (default: the server's first)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    from tokenizers import Tokenizer

    data = json.loads(args.set.read_text(encoding="utf-8"))
    found = problems(data, args.tokenizer.read_bytes())
    for line in found:
        print(line, file=sys.stderr)
    if found:
        return 2
    tokenizer = Tokenizer.from_file(str(args.tokenizer))

    def tokenize(text):
        return list(tokenizer.encode(text, add_special_tokens=True).ids)

    model = args.model or post(args.url, "/v1/models")["data"][0]["id"]

    def complete(token_ids, top_k):
        body = {"model": model, "prompt": token_ids, "max_tokens": 1}
        body.update(temperature=0, seed=args.seed, prompt_logprobs=top_k)
        return post(args.url, "/v1/completions", body)

    summary, result = score(data, tokenize, complete)
    for row in result["texts"]:
        if "error" in row:
            print(f"{row['name']}: {row['error']}")
    for d, s in summary.items():
        each = "  ".join(f"{n}={v}" for n, v in s["texts"].items())
        print(
            f"{d}: mean_nll {s['mean_nll']:.4f} over {s['positions']} positions  {each}"
        )
    checks = result["self_agreement"]
    print(
        "self-agreement: largest logprob move "
        f"{max((c['max_abs_logprob_move'] for c in checks), default=None)}, "
        f"argmax agreement min {min((c['argmax_agreement'] for c in checks), default=None)}"
    )
    out = {
        "server": args.url,
        "model": model,
        "set_sha256": sha256(args.set.read_bytes()),
        "summary": summary,
        "result": result,
    }
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("passed" if result["passed"] else f"failed ({result['errors']} errors)")
    return 0 if result["passed"] else 1
