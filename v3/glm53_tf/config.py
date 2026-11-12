"""Resolve checkout assets independently of the caller's working directory."""

import json
import re
import tomllib
from pathlib import Path

# v3/, the 3.x line: its package, pyproject.toml and config/.
LINE = Path(__file__).resolve().parents[1]
# The checkout root above v3/: its untracked state/ and records/ are what a deploy
# checkout links to the host's persistent directories, whichever line it serves.
ROOT = LINE.parent
STATE = ROOT / "state"
# The checkpoints 3.x serves, which download and verify-download fetch by --checkpoint, or
# by --tp as that TP's release file (config/tp*.env) serves it at its lock's revision: from
# 3.12.0 Jammed XSFP4 at TP=2 and XSFP4 at TP=3 and TP=4. One of the two is required (up to
# 3.11.x a run without either fetched XSFP4).
# A rank file's CHECKPOINT line serves the other one at its lock's revision.
LOCK_PATH = LINE / "config/xsfp4.lock.json"
LOCKS = {"xsfp4": LOCK_PATH, "jammed": LINE / "config/jammed.lock.json"}
CHECKPOINTS = tuple(LOCKS)
TP_CHECKPOINTS = {2: "jammed", 3: "xsfp4", 4: "xsfp4"}
CHECKPOINT_HELP = "xsfp4 (XSFP4, kept under state/xsfp4) or jammed (Jammed XSFP4, kept under state/jammed)"
TP_HELP = "the checkpoint this TP serves by default: jammed at 2, xsfp4 at 3 and 4"


def load_lock(path):
    lock = json.loads(path.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
        raise ValueError("Model revision must be a full commit hash")
    return lock


def add_checkpoint_arguments(parser):
    """--checkpoint by name, or --tp for the checkpoint that TP serves by default; one of the two
    is required. Neither has a default: argparse does not count an option given at its default's
    value, which would let it through beside the other or fail it as missing."""
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--checkpoint", choices=CHECKPOINTS, help=CHECKPOINT_HELP)
    which.add_argument("--tp", type=int, choices=sorted(TP_CHECKPOINTS), help=TP_HELP)


def chosen_checkpoint(args):
    return TP_CHECKPOINTS[args.tp] if args.tp else args.checkpoint


def checkpoint(name, state):
    """The checkpoint's model, revision and state folder, ``state/<name>`` (where 3.4.0 and
    3.5.x kept XSFP4's download status beside the others', so a host's status stays put)."""
    if name in CHECKPOINTS:
        lock = load_lock(LOCKS[name])
        return lock["model"], lock["revision"], state / name
    raise ValueError("unknown checkpoint: " + name)


def version():
    return tomllib.loads((LINE / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
