"""The 3.x line's checkout-local CLI; each command imports its client packages only when it runs."""

import argparse
import importlib
import sys

from .config import version

COMMANDS = {
    "download": "download",
    "verify-download": "verify_download",
    "tool-gate": "tool_gate.proxy",
    "decode-check": "decode_check",
    "decode-divergence": "decode_divergence",
    "score-nll": "score_nll",
    "bench": "bench",
    "long-input": "long_input",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="python -m glm53_tf", description=__doc__)
    parser.add_argument("command", choices=COMMANDS, nargs="?")
    parser.add_argument("--version", action="version", version=version())
    if not argv or argv[0] in ("-h", "--help", "--version"):
        parser.parse_args(argv)
        if not argv:
            parser.print_help()
        return
    if argv[0] not in COMMANDS:
        parser.error("unknown command: " + argv[0])
    target = COMMANDS[argv[0]]
    module = importlib.import_module("glm53_tf." + target)
    # score-nll and long-input return their exit status; the others return None (0) or exit.
    raise SystemExit(module.main(argv[1:]))


if __name__ == "__main__":
    main()
