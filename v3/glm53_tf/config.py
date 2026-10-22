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
# The published options' weights, which download and verify-download fetch with
# --checkpoint axl (NVFP4 BIZ AXL) or xsfp4 (the XSFP4 checkpoint, from 3.3.0); serving
# them is the rank file's CHECKPOINT (README.md).
OPTION_LOCK_PATHS = {
    "axl": LINE / "config/axl.lock.json",
    "xsfp4": LINE / "config/xsfp4.lock.json",
}
CHECKPOINTS = ("pinned", *OPTION_LOCK_PATHS)
CHECKPOINT_HELP = (
    "pinned (NVIDIA's, the default), axl or xsfp4 (the published options, kept under"
    " state/axl and state/xsfp4)"
)


def load_lock(path=None):
    lock = json.loads((path or LOCK_PATH).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
        raise ValueError("Model revision must be a full commit hash")
    return lock


def checkpoint(name, state):
    """A checkpoint's model, revision and state folder under ``state``: the pinned one
    keeps ``state`` itself, each option ``state/<name>``, so one's download status never
    overwrites another's."""
    if name == "pinned":
        lock = load_lock()
        return lock["model"], lock["revision"], state
    if name in OPTION_LOCK_PATHS:
        lock = load_lock(OPTION_LOCK_PATHS[name])
        return lock["model"], lock["revision"], state / name
    raise ValueError("unknown checkpoint: " + name)


def version():
    return tomllib.loads((LINE / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
