import json
import tempfile
import unittest
from pathlib import Path

from glm53_tf import config

LINE = Path(__file__).resolve().parents[1]


class LoadLockTests(unittest.TestCase):
    def load(self, **lock):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "xsfp4.lock.json"
            values = {"model": "m", "revision": "0" * 40, **lock}
            path.write_text(json.dumps(values), encoding="utf-8")
            return config.load_lock(path)

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
        self.assertEqual(config.LOCK_PATH, LINE / "config/xsfp4.lock.json")

    def test_the_line_keeps_no_lock_of_the_checkpoints_it_no_longer_serves(self):
        # 3.6.0 took NVIDIA's NVFP4 (model.lock.json) and the AXL weights off 3.x.
        locks = sorted(p.name for p in (LINE / "config").glob("*.lock.json"))
        self.assertEqual(
            locks, ["engine.lock.json", "jammed.lock.json", "xsfp4.lock.json"]
        )


class CheckpointTests(unittest.TestCase):
    def test_xsfp4_and_jammed_are_the_choices(self):
        self.assertEqual(config.CHECKPOINTS, ("xsfp4", "jammed"))
        for name in ("pinned", "axl"):
            with (
                self.subTest(checkpoint=name),
                self.assertRaisesRegex(ValueError, "unknown checkpoint"),
            ):
                config.checkpoint(name, Path("state"))

    def test_xsfp4_is_its_own_full_revision_in_its_own_state_folder(self):
        model, revision, state = config.checkpoint("xsfp4", Path("state"))
        self.assertEqual(model, "Bizuayeu/GLM-5.3-Flash-XSFP4")
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertEqual(state, Path("state/xsfp4"))

    def test_jammed_is_its_own_full_revision_in_its_own_state_folder(self):
        model, revision, state = config.checkpoint("jammed", Path("state"))
        self.assertEqual(model, "Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4")
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertEqual(state, Path("state/jammed"))

    def test_both_tools_explain_the_checkpoint_choice(self):
        import contextlib
        import io

        from glm53_tf import download, verify_download

        for tool in (download, verify_download):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                tool.main(["--help"])
            for shown in (config.CHECKPOINT_HELP, config.TP_HELP):
                self.assertIn(
                    " ".join(shown.split()),
                    " ".join(out.getvalue().split()),
                )

    def test_an_unknown_checkpoint_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown checkpoint"):
            config.checkpoint("other", Path("state"))


if __name__ == "__main__":
    unittest.main()
