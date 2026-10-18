"""What the serving lines must agree on, checked where all of them are visible."""

import hashlib
import json
import tomllib
import unittest
from pathlib import Path

from tools.release_notes import notes, section

REPO = Path(__file__).resolve().parents[1]
LINES = sorted(p.parent for p in REPO.glob("v[0-9]*/pyproject.toml"))


def version(line):
    text = (line / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)["project"]["version"]


class LineTests(unittest.TestCase):
    def test_every_line_is_found(self):
        self.assertEqual([line.name for line in LINES], ["v1", "v2", "v3"])

    def test_each_lines_version_has_notes_in_both_languages(self):
        # A v* tag publishes the English section once its heading carries the release
        # date (tools/release_notes.py); the Japanese changelog is its pair.
        for line in LINES:
            with self.subTest(line=line.name):
                v = version(line)
                self.assertTrue(notes(REPO, v).strip())
                japanese = (line / "CHANGELOG.ja.md").read_text(encoding="utf-8")
                self.assertTrue(section(japanese, v).strip())

    def test_the_released_lines_can_publish_their_version(self):
        # What a tag reads: the version's heading carries its release date.
        for name in ("v1", "v2", "v3"):
            with self.subTest(line=name):
                v = version(REPO / name)
                self.assertTrue(notes(REPO, v, match_project=True).strip())


class SharedCheckpointTests(unittest.TestCase):
    """Every line serves one pinned checkpoint; each keeps its own copy of what it reads."""

    def test_the_lines_pin_the_same_model_and_revision(self):
        v1 = json.loads((REPO / "v1/config/runtime.lock.json").read_text("utf-8"))
        for name in ("v2", "v3"):
            with self.subTest(line=name):
                lock = json.loads(
                    (REPO / name / "config/model.lock.json").read_text("utf-8")
                )
                self.assertEqual(
                    (v1["model"], v1["revision"]), (lock["model"], lock["revision"])
                )

    def test_the_copies_the_lines_read_are_byte_identical(self):
        # The NLL set makes the lines' figures comparable; the lock installs one client.
        for name in ("config/nll_set.json", "requirements/huggingface.lock.txt"):
            with self.subTest(name=name):
                digests = {
                    hashlib.sha256((line / name).read_bytes()).hexdigest()
                    for line in LINES
                }
                self.assertEqual(len(digests), 1)


class CopiedModuleTests(unittest.TestCase):
    """2.x and 3.x carry their own copies of 1.x modules (each line stands alone).
    These are unchanged but for the package name; one that has to differ leaves
    this list."""

    # download.py and verify_download.py left it in 2.4.0: 2.x also fetches AXL.
    SAME = (
        "io.py",
        "tool_gate/__init__.py",
        "tool_gate/check.py",
        "tool_gate/repair.py",
    )

    def test_the_copies_differ_only_in_the_package_name(self):
        for name in self.SAME:
            v1 = (REPO / "v1/glm53_setup" / name).read_text(encoding="utf-8")
            for line in ("v2", "v3"):
                with self.subTest(name=name, line=line):
                    copy = (REPO / line / "glm53_tf" / name).read_text("utf-8")
                    self.assertEqual(v1.replace("glm53_setup", "glm53_tf"), copy)


if __name__ == "__main__":
    unittest.main()
