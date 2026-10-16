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
LOCK_PATH = LINE / "config/model.lock.json"
# The published option's weights (NVFP4 BIZ AXL), which download and verify-download
# fetch with --checkpoint axl; serving them is the rank file's CHECKPOINT (README.md).
AXL_LOCK_PATH = LINE / "config/axl.lock.json"
CHECKPOINTS = ("pinned", "axl")
CHECKPOINT_HELP = (
    "pinned (NVIDIA's, the default) or axl (the published option, kept under state/axl)"
)


def load_lock(path=None):
    lock = json.loads((path or LOCK_PATH).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
        raise ValueError("Model revision must be a full commit hash")
    return lock


def checkpoint(name, state):
    """A checkpoint's model, revision and state folder under ``state``: the pinned one
    keeps ``state`` itself, AXL ``state/axl``, so one's download status never
    overwrites the other's."""
    if name == "pinned":
        lock = load_lock()
        return lock["model"], lock["revision"], state
    if name == "axl":
        lock = load_lock(AXL_LOCK_PATH)
        return lock["model"], lock["revision"], state / name
    raise ValueError("unknown checkpoint: " + name)


def version():
    return tomllib.loads((LINE / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
