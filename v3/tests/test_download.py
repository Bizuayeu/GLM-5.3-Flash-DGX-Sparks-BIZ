import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_tf import config, download

LINE = Path(__file__).resolve().parents[1]


class BackgroundTests(unittest.TestCase):
    def background(self, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            posix = SimpleNamespace(name="posix", environ=os.environ)
            with (
                patch.object(download, "STATE", Path(tmp)),
                patch.object(download, "os", posix),
                patch.object(download.subprocess, "Popen") as popen,
                redirect_stdout(io.StringIO()),
            ):
                popen.return_value.pid = 1
                download.main(["--background", *extra])
            logs = sorted(
                str(p.relative_to(tmp)).replace(os.sep, "/")
                for p in Path(tmp).rglob("download.log")
            )
        return popen, logs

    def test_the_background_job_runs_this_lines_package_from_v2(self):
        popen, logs = self.background()
        self.assertEqual(logs, ["download.log"])
        command = popen.call_args.args[0]
        self.assertEqual(
            command[1:], ["-m", "glm53_tf", "download", "--checkpoint", "pinned"]
        )
        self.assertEqual(popen.call_args.kwargs["cwd"], LINE)

    def test_an_axl_job_passes_its_checkpoint_on_and_logs_in_its_folder(self):
        popen, logs = self.background("--checkpoint", "axl")
        self.assertEqual(logs, ["axl/download.log"])
        self.assertEqual(popen.call_args.args[0][-2:], ["--checkpoint", "axl"])


def fake_hub(snapshot, sha, sizes):
    """A huggingface_hub whose model lists ``sizes`` and downloads into ``snapshot``."""
    siblings = [SimpleNamespace(rfilename=n, size=s) for n, s in sizes.items()]
    api = SimpleNamespace(
        model_info=lambda *a, **k: SimpleNamespace(sha=sha, siblings=siblings)
    )
    return SimpleNamespace(
        HfApi=lambda: api, snapshot_download=lambda *a, **k: str(snapshot)
    )


INDEX = json.dumps({"weight_map": {"a": "model-1.safetensors"}})


class DownloadTests(unittest.TestCase):
    """download() records why it stopped, so the status file is the job's verdict."""

    def run_download(self, sha=None, files=None, sizes=None, which="pinned"):
        with tempfile.TemporaryDirectory() as tmp:
            root, snapshot = Path(tmp) / "state", Path(tmp) / "snapshot"
            model, revision, state = config.checkpoint(which, root)
            snapshot.mkdir()
            files = (
                {"model.safetensors.index.json": INDEX, "model-1.safetensors": "w"}
                if files is None
                else files
            )
            for name, text in files.items():
                (snapshot / name).write_text(text, encoding="utf-8")
            if sizes is None:
                sizes = {n: len(t.encode("utf-8")) for n, t in files.items()}
            hub = fake_hub(snapshot, sha or revision, sizes)
            with (
                patch.dict(sys.modules, {"huggingface_hub": hub}),
                patch.dict(os.environ),
                patch.object(download, "STATE", root),
                redirect_stdout(io.StringIO()),
            ):
                try:
                    download.download(which)
                    code = None
                except SystemExit as error:
                    code = error.code
            status = json.loads((state / download.STATUS_FILE).read_text("utf-8"))
        return code, status

    def test_a_complete_snapshot_is_recorded_with_its_shards(self):
        code, status = self.run_download()
        self.assertIsNone(code)
        self.assertEqual(status["status"], "complete")
        self.assertEqual((status["file_count"], status["weight_shards"]), (2, 1))

    def test_axl_records_its_own_model_and_revision_in_its_own_folder(self):
        code, status = self.run_download(which="axl")
        model, revision, _ = config.checkpoint("axl", Path("state"))
        self.assertIsNone(code)
        self.assertEqual(
            (status["model"], status["revision"], status["status"]),
            (model, revision, "complete"),
        )

    def test_another_revision_fails_the_job(self):
        code, status = self.run_download(sha="0" * 40)
        self.assertEqual(code, 1)
        self.assertEqual(
            (status["status"], status["error_type"]), ("failed", "RuntimeError")
        )

    def test_a_file_of_the_wrong_size_fails_the_job(self):
        files = {"model.safetensors.index.json": INDEX, "model-1.safetensors": "w"}
        sizes = {"model.safetensors.index.json": len(INDEX), "model-1.safetensors": 2}
        code, status = self.run_download(files=files, sizes=sizes)
        self.assertEqual((code, status["status"]), (1, "failed"))

    def test_an_indexed_shard_that_is_missing_fails_the_job(self):
        files = {"model.safetensors.index.json": INDEX}
        code, status = self.run_download(files=files)
        self.assertEqual((code, status["status"]), (1, "failed"))


@unittest.skipUnless(importlib.util.find_spec("filelock"), "needs filelock")
class LockTests(unittest.TestCase):
    def test_a_second_download_in_the_same_workspace_is_refused(self):
        from filelock import FileLock

        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(download, "STATE", Path(tmp)),
                FileLock(Path(tmp) / "download.lock"),
                self.assertRaisesRegex(SystemExit, "already owns this workspace"),
            ):
                download.main([])


if __name__ == "__main__":
    unittest.main()
