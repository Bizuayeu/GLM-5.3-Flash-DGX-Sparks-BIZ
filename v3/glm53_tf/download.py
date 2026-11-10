"""Download a locked GLM checkpoint (config/xsfp4.lock.json, config/jammed.lock.json) into
the shared Hugging Face cache."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    DEFAULT_CHECKPOINT,
    LINE,
    STATE,
    add_checkpoint_arguments,
    checkpoint,
    chosen_checkpoint,
)
from .io import write_json

# In the checkpoint's state folder (config.checkpoint); the checksum run
# (verify_download) reads what this writes there.
STATUS_FILE = "download-status.json"


def started(model, revision):
    """The status a job starts from; the background start writes it before it returns."""
    return {
        "model": model,
        "revision": revision,
        "status": "downloading",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def download(name=DEFAULT_CHECKPOINT):
    os.environ.setdefault("HF_XET_NUM_CONCURRENT_RANGE_GETS", "4")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
    from huggingface_hub import HfApi, snapshot_download

    model, revision, state = checkpoint(name, STATE)
    state.mkdir(parents=True, exist_ok=True)
    status = started(model, revision)

    def save():
        write_json(state / STATUS_FILE, status)

    save()
    try:
        info = HfApi().model_info(model, revision=revision, files_metadata=True)
        if info.sha != revision:
            raise RuntimeError("Unexpected model revision")
        files = [{"path": item.rfilename, "bytes": item.size} for item in info.siblings]
        (state / "model-manifest.json").write_text(
            json.dumps({"model": model, "revision": revision, "files": files}, indent=2)
            + "\n"
        )
        status["total_bytes"] = sum(item["bytes"] or 0 for item in files)
        save()
        print("Downloading:", model, revision, status["total_bytes"], flush=True)
        # Bound simultaneous shard downloads on unified-memory hosts.
        snapshot = Path(snapshot_download(model, revision=revision, max_workers=2))
        for item in files:
            file = snapshot / item["path"]
            if (
                not file.is_file()
                or item["bytes"] is not None
                and file.stat().st_size != item["bytes"]
            ):
                raise RuntimeError("Incomplete download: " + item["path"])
        weights = json.loads((snapshot / "model.safetensors.index.json").read_text())[
            "weight_map"
        ]
        if not weights or not all(
            (snapshot / shard).is_file() for shard in set(weights.values())
        ):
            raise RuntimeError("Indexed model weights are missing")
        status.update(
            status="complete",
            snapshot=str(snapshot),
            file_count=len(files),
            weight_shards=len(set(weights.values())),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        save()
        print("COMPLETE:", snapshot, flush=True)
    except Exception as error:  # noqa: BLE001 -- persist unexpected failures at the job boundary
        status.update(status="failed", error_type=type(error).__name__)
        save()
        print("DOWNLOAD FAILED:", type(error).__name__, flush=True)
        raise SystemExit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background", action="store_true")
    add_checkpoint_arguments(parser)
    args = parser.parse_args(argv)
    name = chosen_checkpoint(args)
    model, revision, state = checkpoint(name, STATE)
    busy = "A download already owns this workspace; inspect its state"
    if args.background:
        if os.name != "posix":
            parser.error("Background jobs require Linux; use foreground mode here")
        from filelock import FileLock, Timeout

        state.mkdir(parents=True, exist_ok=True)
        # Written before this returns, so a verify-download started right after finds this
        # job's status rather than none or the last job's. The job takes the lock itself.
        try:
            with FileLock(state / "download.lock", timeout=0):
                status = started(model, revision)
                write_json(state / STATUS_FILE, status)
        except Timeout:
            raise SystemExit(busy) from None
        env = os.environ.copy()
        with (state / "download.log").open("a", encoding="utf-8") as log:
            try:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "glm53_tf",
                        "download",
                        "--checkpoint",
                        name,
                    ],
                    cwd=LINE,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as error:
                status.update(status="failed", error_type=type(error).__name__)
                write_json(state / STATUS_FILE, status)
                print("DOWNLOAD FAILED:", type(error).__name__, flush=True)
                raise SystemExit(1) from None
        print("Download PID:", process.pid)
    else:
        from filelock import FileLock, Timeout

        state.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(state / "download.lock", timeout=0):
                (state / "download.pid").write_text(str(os.getpid()) + "\n")
                download(name)
        except Timeout:
            raise SystemExit(busy) from None


if __name__ == "__main__":
    main()
