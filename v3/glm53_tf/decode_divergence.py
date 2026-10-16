"""First diverging token between two decode-check token records (their TOKENS_OUT files).

    python -m glm53_tf decode-divergence ../records/<run-a>/tokens-prose.json ../records/<run-b>/tokens-prose.json

Prints, per sample index, the token count, the first index where the ids differ (or "identical") and the text
around it, so a launch difference reads as one tie-break flip or as an early systematic drift. Runs holding
different sample counts end with a line that says so.
"""

import argparse
import json


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m glm53_tf decode-divergence", description=__doc__
    )
    parser.add_argument("a")
    parser.add_argument("b")
    args = parser.parse_args(argv)
    a, b = load(args.a), load(args.b)
    for i, (x, y) in enumerate(zip(a["samples"], b["samples"])):
        ia, ib = x["token_ids"], y["token_ids"]
        k = next((j for j in range(min(len(ia), len(ib))) if ia[j] != ib[j]), None)
        if k is None and len(ia) == len(ib):
            print(f"sample {i}: identical ({len(ia)} tokens)")
            continue
        k = min(len(ia), len(ib)) if k is None else k
        ta, tb = x["text"], y["text"]
        c = next(
            (j for j in range(min(len(ta), len(tb))) if ta[j] != tb[j]),
            min(len(ta), len(tb)),
        )
        print(
            f"sample {i}: first differing token {k}/{len(ia)} "
            f"(ids {ia[k : k + 3]} vs {ib[k : k + 3]}), char {c}"
        )
        print("   A:", repr(ta[max(0, c - 60) : c + 60]))
        print("   B:", repr(tb[max(0, c - 60) : c + 60]))
    if len(a["samples"]) != len(b["samples"]):
        print(f"samples: A has {len(a['samples'])}, B has {len(b['samples'])}")
