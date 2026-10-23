import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import config

LINE = Path(__file__).resolve().parents[1]


class LoadLockTests(unittest.TestCase):
    def load(self, **lock):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.lock.json"
            values = {"model": "m", "revision": "0" * 40, **lock}
            path.write_text(json.dumps(values), encoding="utf-8")
            with patch.object(config, "LOCK_PATH", path):
                return config.load_lock()

    def test_a_full_revision_is_read(self):
        self.assertEqual(self.load()["revision"], "0" * 40)

    def test_a_short_revision_is_refused(self):
        with self.assertRaisesRegex(
            ValueError, "^Model revision must be a full commit hash$"
        ):
            self.load(revision="0" * 7)


class CheckoutLayoutTests(unittest.TestCase):
    # v3/ holds the package; the checkout root holds the licences and the
    # untracked state/ and records/ that a deploy checkout links to its host's.
    def test_state_sits_at_the_checkout_root(self):
        self.assertEqual(config.LINE, LINE)
        self.assertEqual(config.ROOT, LINE.parent)
        self.assertTrue((config.ROOT / "LICENSE").is_file())
        self.assertEqual(config.STATE, config.ROOT / "state")
        self.assertEqual(config.LOCK_PATH, LINE / "config/model.lock.json")


class CheckpointTests(unittest.TestCase):
    def test_the_pinned_checkpoint_keeps_state_itself(self):
        state = Path("state")
        lock = config.load_lock()
        self.assertEqual(
            config.checkpoint("pinned", state),
            (lock["model"], lock["revision"], state),
        )

    def test_axl_is_its_own_full_revision_in_its_own_state_folder(self):
        model, revision, state = config.checkpoint("axl", Path("state"))
        self.assertEqual(model, "Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16")
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertEqual(state, Path("state/axl"))

    def test_xsfp4_is_its_own_full_revision_in_its_own_state_folder(self):
        model, revision, state = config.checkpoint("xsfp4", Path("state"))
        self.assertEqual(model, "Bizuayeu/GLM-5.3-Flash-XSFP4")
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertEqual(state, Path("state/xsfp4"))

    def test_both_tools_explain_the_checkpoint_choice(self):
        import contextlib
        import io

        from glm53_tf import download, verify_download

        for tool in (download, verify_download):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                tool.main(["--help"])
            self.assertIn(
                " ".join(config.CHECKPOINT_HELP.split()),
                " ".join(out.getvalue().split()),
            )

    def test_an_unknown_checkpoint_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown checkpoint"):
            config.checkpoint("other", Path("state"))


class ServeScriptTests(unittest.TestCase):
    def test_serve_sh_serves_xsfp4_at_its_locked_revision_by_default(self):
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        pattern = r"/hub/models--([\w.-]+)--([\w.-]+)/snapshots/([0-9a-f]{40})"
        match = re.search(pattern, serve)
        self.assertIsNotNone(match)
        model, revision, _ = config.checkpoint("xsfp4", Path("state"))
        self.assertEqual(config.DEFAULT_CHECKPOINT, "xsfp4")
        self.assertEqual(f"{match[1]}/{match[2]}", model)
        self.assertEqual(match[3], revision)

    def test_serve_sh_reads_images_and_videos_unless_the_rank_file_says_otherwise(self):
        # Unset: --vision. Empty: text alone. Every rank the same (the ranks agree on --vision at start).
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        self.assertIn("vision=${VISION-1}\n", serve)
        self.assertIn('[ -n "$vision" ] && args+=(--vision)', serve)
        self.assertEqual(serve.count("--vision"), 1)
        self.assertIn("vision ${vision:-off}", serve)

    def test_serve_sh_serves_one_stream_unless_the_rank_file_says_otherwise(self):
        # Unset: 1. Empty: no --parallel, the engine's auto (from the memory free at start).
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        self.assertIn("parallel=${PARALLEL-1}\n", serve)
        self.assertIn('[ -n "$parallel" ] && args+=(--parallel "$parallel")', serve)
        self.assertEqual(serve.count("--parallel"), 1)

    def test_serve_sh_sets_the_window_by_tp_unless_the_rank_file_says_otherwise(self):
        # TP=2 524,288 (3.5.0: one stream and a prompt cache beside XSFP4), TP=3 1,048,576 (the model's limit).
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        self.assertIn('if [ "$tp" = 2 ]; then\n  context=${CONTEXT:-524288}\n', serve)
        self.assertIn("else\n  context=${CONTEXT:-1048576}\n", serve)
        self.assertEqual(serve.count("${CONTEXT:-"), 2)

    def test_tp2_examples_keep_nvidias_window_beside_its_checkpoint(self):
        # NVIDIA's NVFP4 weighs about 3.9 GiB more on rank 0: its line comes with 3.4.0's window.
        for rank in (0, 1):
            lines = (
                (LINE / f"examples/tp2-rank{rank}.env")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            at = next(
                i
                for i, line in enumerate(lines)
                if line.startswith("# CHECKPOINT=/hub/models--nvidia--")
            )
            self.assertTrue(
                lines[at + 1].startswith("# CONTEXT=245760 "), lines[at + 1]
            )

    def test_serve_sh_waits_for_heat_by_the_band_alone(self):
        # 92/88 unless the rank file says otherwise; no ceiling (3.3.0: the engine has no TF_HEAT_CEILING).
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        self.assertIn(
            "TF_HEAT_HIGH=${TF_HEAT_HIGH-92} TF_HEAT_LOW=${TF_HEAT_LOW-88}\n", serve
        )
        self.assertNotIn("TF_HEAT_CEILING", serve)
        self.assertIn('"heat ${TF_HEAT_HIGH:-unset}/${TF_HEAT_LOW:-unset}"', serve)


if __name__ == "__main__":
    unittest.main()
