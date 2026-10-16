"""Wait for the existing downloader, then verify a locked checkpoint's HF cache checksums
(the pinned one, or with --checkpoint axl the published option's)."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import CHECKPOINT_HELP, CHECKPOINTS, STATE, checkpoint
from .download import STATUS_FILE
from .io import write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument(
        "--checkpoint", choices=CHECKPOINTS, default="pinned", help=CHECKPOINT_HELP
    )
    args = parser.parse_args(argv)
    model, revision, state = checkpoint(args.checkpoint, STATE)
    args.output.mkdir(parents=True, exist_ok=True)
    status_file = args.output / "checksum-status.json"

    def save(status, **extra):
        write_json(
            status_file,
            {
                "status": status,
                "model": model,
                "revision": revision,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **extra,
            },
        )

    save("waiting_for_download")
    if not (state / STATUS_FILE).is_file():
        # A host that received a copied cache has no download status until download
        # registers the snapshot (it reuses the copied files).
        save("failed", reason="no download status")
        print(
            f"no {STATUS_FILE} in {state}: run download first"
            + (
                ""
                if args.checkpoint == "pinned"
                else f" --checkpoint {args.checkpoint}"
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
    while True:
        status = json.loads((state / STATUS_FILE).read_text())
        if status["model"] != model or status["revision"] != revision:
            save("failed", reason="revision mismatch")
            raise SystemExit(1)
        if status["status"] == "complete":
            break
        if status["status"] in ("failed", "paused") or not args.wait:
            paused = status["status"] == "paused"
            save("paused" if paused else "failed", reason="download not complete")
            raise SystemExit(2 if paused else 1)
        # Polling cadence only; does not bound or retry downloads.
        time.sleep(30)
    save("verifying")
    command = [
        str(args.hf),
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
        (args.output / "checksum.json").open("w", encoding="utf-8") as out,
        (args.output / "checksum.log").open("w", encoding="utf-8") as err,
    ):
        result = subprocess.run(command, stdout=out, stderr=err, check=False)
    save(
        "complete" if result.returncode == 0 else "failed", exit_code=result.returncode
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
