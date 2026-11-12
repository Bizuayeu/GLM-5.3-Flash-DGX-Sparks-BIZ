"""Wait for the existing downloader, then verify the locked checkpoint's HF cache checksums."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import STATE, add_checkpoint_arguments, checkpoint, chosen_checkpoint
from .download import STATUS_FILE
from .io import write_json


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait", action="store_true")
    add_checkpoint_arguments(parser)
    return parser.parse_args(argv)


def recorder(path, model, revision):
    """A writer of the check's status file: the status, the checkpoint, the time and any extra fields."""

    def save(status, **extra):
        write_json(
            path,
            {
                "status": status,
                "model": model,
                "revision": revision,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **extra,
            },
        )

    return save


def wait_for_download(state, model, revision, wait, save):
    """Returns once the download of this model and revision is complete. Otherwise it saves why and exits:
    2 while the download is paused, 1 without a download status, for another model or revision, for a failed
    download, or for an unfinished one without wait."""
    if not (state / STATUS_FILE).is_file():
        # A host that received a copied cache has no download status until download
        # registers the snapshot (it reuses the copied files).
        save("failed", reason="no download status")
        print(f"no {STATUS_FILE} in {state}: run download first", file=sys.stderr)
        raise SystemExit(1)
    while True:
        status = json.loads((state / STATUS_FILE).read_text(encoding="utf-8"))
        if status["model"] != model or status["revision"] != revision:
            save("failed", reason="revision mismatch")
            raise SystemExit(1)
        if status["status"] == "complete":
            return
        if status["status"] in ("failed", "paused") or not wait:
            paused = status["status"] == "paused"
            save("paused" if paused else "failed", reason="download not complete")
            raise SystemExit(2 if paused else 1)
        # Polling cadence only; does not bound or retry downloads.
        time.sleep(30)


def verify(hf, model, revision, output):
    """hf cache verify's exit code for this model and revision, its JSON in checksum.json and its errors
    in checksum.log."""
    command = [
        str(hf),
        "cache",
        "verify",
        model,
        "--revision",
        revision,
        "--fail-on-missing-files",
        "--fail-on-extra-files",
        "--json",
    ]
    with (
        (output / "checksum.json").open("w", encoding="utf-8") as out,
        (output / "checksum.log").open("w", encoding="utf-8") as err,
    ):
        return subprocess.run(command, stdout=out, stderr=err, check=False).returncode


def main(argv=None):
    args = parse(argv)
    model, revision, state = checkpoint(chosen_checkpoint(args), STATE)
    args.output.mkdir(parents=True, exist_ok=True)
    save = recorder(args.output / "checksum-status.json", model, revision)
    save("waiting_for_download")
    wait_for_download(state, model, revision, args.wait, save)
    save("verifying")
    code = verify(args.hf, model, revision, args.output)
    save("complete" if code == 0 else "failed", exit_code=code)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
