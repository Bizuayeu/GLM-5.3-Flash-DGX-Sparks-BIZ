"""First diverging character between two decode-check records (their TOKENS_OUT files).

    python -m glm53_tf decode-divergence ../records/<run-a>/tokens-prose.json ../records/<run-b>/tokens-prose.json

Prints, per sample index, the first character where the completions differ (or "identical") and the text
around it, so a launch difference reads as one tie-break flip or as an early systematic drift. The native
server returns no token ids, so a record holds each sample's text. Runs holding different sample counts end
with a line that says so.
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
        ta, tb = x["text"], y["text"]
        if ta == tb:
            print(f"sample {i}: identical ({len(ta)} characters)")
            continue
        c = next(
            (j for j in range(min(len(ta), len(tb))) if ta[j] != tb[j]),
            min(len(ta), len(tb)),
        )
        print(f"sample {i}: first differing character {c}/{len(ta)}")
        print("   A:", repr(ta[max(0, c - 60) : c + 60]))
        print("   B:", repr(tb[max(0, c - 60) : c + 60]))
    if len(a["samples"]) != len(b["samples"]):
        print(f"samples: A has {len(a['samples'])}, B has {len(b['samples'])}")
