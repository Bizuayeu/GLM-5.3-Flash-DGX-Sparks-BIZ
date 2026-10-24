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
# XSFP4, the checkpoint 3.x serves (its only one from 3.6.0): download and verify-download
# fetch it with --checkpoint xsfp4, the default, and serve.sh serves its lock's revision.
LOCK_PATH = LINE / "config/xsfp4.lock.json"
CHECKPOINTS = ("xsfp4",)
DEFAULT_CHECKPOINT = "xsfp4"
CHECKPOINT_HELP = "xsfp4 (the XSFP4 checkpoint, kept under state/xsfp4; the only one)"


def load_lock(path=None):
    lock = json.loads((path or LOCK_PATH).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
        raise ValueError("Model revision must be a full commit hash")
    return lock


def checkpoint(name, state):
    """The checkpoint's model, revision and state folder, ``state/<name>`` (where 3.4.0 and
    3.5.x kept XSFP4's download status beside the others', so a host's status stays put)."""
    if name in CHECKPOINTS:
        lock = load_lock()
        return lock["model"], lock["revision"], state / name
    raise ValueError("unknown checkpoint: " + name)


def version():
    return tomllib.loads((LINE / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
