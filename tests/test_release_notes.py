import tempfile
import unittest
from pathlib import Path

from tools.release_notes import notes, project_dir, section

CHANGELOG = """# Changelog

## Unreleased

- pending

## 1.10.0 — 2026-09-18

### Changed

- ten

## 1.1.0 — 2026-09-15

- one
"""


class ReleaseNotesTests(unittest.TestCase):
    def test_returns_only_the_named_version(self):
        self.assertEqual(section(CHANGELOG, "1.10.0"), "### Changed\n\n- ten\n")
        self.assertEqual(section(CHANGELOG, "1.1.0"), "- one\n")

    def test_refuses_a_version_without_notes(self):
        for version in ("1.1", "1.2.0", "Unreleased", "1.1.0 "):
            with self.assertRaises(ValueError):
                section(CHANGELOG, version)
        with self.assertRaises(ValueError):
            section("## 2.0.0 — 2026-10-01\n\n## 1.0.0 — 2026-09-15\n\n- x\n", "2.0.0")


def line(repo, name, version, changelog):
    directory = repo / name
    directory.mkdir()
    (directory / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8"
    )
    (directory / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


class LineTests(unittest.TestCase):
    """A tag's major version picks the line directory: v1.* reads v1/, v2.* v2/."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        line(self.repo, "v1", "1.10.0", CHANGELOG)
        line(self.repo, "v2", "2.0.0", "# Changelog\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_major_version_names_the_directory(self):
        self.assertEqual(project_dir(self.repo, "1.10.0"), self.repo / "v1")
        self.assertEqual(project_dir(self.repo, "2.0.0"), self.repo / "v2")
        for version in ("3.0.0", "0.1.0", "1.10", "v1.10.0"):
            with self.assertRaises(ValueError):
                project_dir(self.repo, version)

    def test_notes_come_from_the_line_of_the_tag(self):
        self.assertEqual(notes(self.repo, "1.10.0"), "### Changed\n\n- ten\n")
        self.assertEqual(notes(self.repo, "1.1.0"), "- one\n")
        # A line without the version's section publishes nothing.
        with self.assertRaises(ValueError):
            notes(self.repo, "2.0.0")

    def test_match_project_compares_the_line_version(self):
        self.assertEqual(
            notes(self.repo, "1.10.0", match_project=True), "### Changed\n\n- ten\n"
        )
        with self.assertRaisesRegex(ValueError, "v1/pyproject.toml"):
            notes(self.repo, "1.1.0", match_project=True)

    def test_a_tag_publishes_only_a_dated_section(self):
        # A line in preparation carries its version and a section the checks read,
        # but its heading has no date until the release, so a tag cannot publish it.
        line(self.repo, "v3", "3.0.0", "## 3.0.0 — in preparation\n\n- soon\n")
        self.assertEqual(notes(self.repo, "3.0.0"), "- soon\n")
        with self.assertRaisesRegex(ValueError, "v3/CHANGELOG.md: the 3.0.0 heading"):
            notes(self.repo, "3.0.0", match_project=True)


if __name__ == "__main__":
    unittest.main()
