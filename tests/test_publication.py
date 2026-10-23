import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tools.check_publication import (
    anchor_problems,
    architecture_problems,
    audit,
    citation_problems,
    duplicate_numbers,
    heading_anchors,
    headline_problems,
    line_problems,
    map_problems,
    pair_problems,
    plan_link_problems,
    problems,
    recipe_problems,
    record_path_problems,
)


class PublicationTests(unittest.TestCase):
    def test_harness_settings_are_not_public_even_if_explicitly_tracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = ".claude-local-test/settings.json"
            target = root / name
            target.parent.mkdir()
            target.write_text("{}", encoding="utf-8")
            self.assertIn(f"private/generated path: {name}", audit(root, {name}))

    def test_locally_existing_private_link_is_not_public(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "guide.md").write_text("[result](records/run.md)", encoding="utf-8")
            (root / "records").mkdir()
            (root / "records/run.md").write_text("private", encoding="utf-8")
            issues = audit(root, {"guide.md"})
            self.assertIn(
                "non-public Markdown target: guide.md -> records/run.md", issues
            )

    def test_sensitive_candidate_is_reported_without_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = "hf" + "_" + "a" * 30
            (root / "sample.txt").write_text(candidate, encoding="utf-8")
            issues = audit(root, {"sample.txt"})
            self.assertIn("sensitive-text candidate: sample.txt", issues)
            self.assertNotIn(candidate, "\n".join(issues))

    def test_images_in_an_assets_directory_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = {
                "assets/banner.png": b"\x89PNG\r\n\x1a\n" + b"\xff" * 64,
                "v2/assets/banner.webp": b"RIFF\x00\x00\x00\x00WEBP" + b"\xff" * 64,
            }
            for name, data in images.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(data)
            issues = audit(root, set(images))
            self.assertEqual([i for i in issues if "assets/" in i], [])

    def test_binaries_outside_assets_or_not_images_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "docs/banner.png": b"\x89PNG\r\n\x1a\n" + b"\xff" * 64,
                "assets/tool.png": b"MZ" + b"\xff" * 64,
                "assets/tool.exe": b"MZ" + b"\xff" * 64,
            }
            for name, data in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(data)
            issues = audit(root, set(files))
            for name in files:
                self.assertIn(f"unexpected binary file: {name}", issues)

    def test_large_image_in_assets_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "assets/banner.png"
            (root / "assets").mkdir()
            (root / name).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff" * 2_000_000)
            self.assertIn(f"unexpected large file: {name}", audit(root, {name}))

    def test_tracked_weight_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.safetensors").write_text("{}", encoding="utf-8")
            self.assertIn(
                "private/generated path: model.safetensors",
                audit(root, {"model.safetensors"}),
            )


class LayoutTests(unittest.TestCase):
    """The audit covers the repository; the 1.x checks read the project in v1/."""

    def test_plans_under_any_docs_directory_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("docs/plans/X_PLAN.md", "v1/docs/X_PLAN.md"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("plan", encoding="utf-8")
                self.assertIn(f"private/generated path: {name}", audit(root, {name}))

    def test_required_files_are_split_between_the_root_and_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("licence", encoding="utf-8")
            (root / "v1").mkdir()
            (root / "v1/SETUP.md").write_text("# Setup\n", encoding="utf-8")
            found = problems(root, {"LICENSE", "v1/SETUP.md"})
            self.assertIn("missing required file: NOTICE", found)
            self.assertIn("missing required file: v1/pyproject.toml", found)
            self.assertNotIn("missing required file: LICENSE", found)
            self.assertNotIn("missing required file: v1/SETUP.md", found)
            self.assertNotIn("missing required file: SETUP.md", found)

    def test_the_repository_map_lists_the_shared_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "docs/README.md": "[Hosts](hosts.md)\n",
                "docs/hosts.md": "# Hosts\n",
                "docs/qsfp-network.md": "# QSFP\n",
            }
            for name, text in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text, encoding="utf-8")
            found = problems(root, set(files))
            self.assertIn(
                "document missing from docs/README.md: docs/qsfp-network.md", found
            )
            self.assertNotIn(
                "document missing from docs/README.md: docs/hosts.md", found
            )


class HeadlineTests(unittest.TestCase):
    BENCHMARKS = "## Measurements on 1.4.0\n\n## Measurements on 1.10.0\n"

    def test_readme_headline_must_name_the_latest_measured_version(self):
        self.assertEqual(
            headline_problems(
                "README.md", "### Headline measurements (1.10.0)\n", self.BENCHMARKS
            ),
            [],
        )
        self.assertEqual(
            headline_problems(
                "README.ja.md", "### 主要な測定値（1.4.0）\n", "## 1.10.0での測定\n"
            ),
            ["stale headline measurements: README.ja.md has 1.4.0, latest is 1.10.0"],
        )

    def test_missing_headline_or_measurements_are_reported(self):
        self.assertEqual(
            headline_problems("README.md", "# Title\n", self.BENCHMARKS),
            ["missing headline measurements: README.md"],
        )
        self.assertEqual(
            headline_problems("README.md", "### Headline measurements (1.0.0)\n", ""),
            ["no versioned measurements beside README.md"],
        )


class RecipeCitationTests(unittest.TestCase):
    README = (
        "### Other recipes\n\n| Recipe | License |\n|---|---|\n"
        "| [Mia](https://github.com/MiaAI-Lab/GLM-Sparks) | AGPL-3.0 |\n"
        "| [sfxnz](https://github.com/sfxnz/GLM-vLLM) | MIT |\n"
    )

    def test_license_beside_a_citation_is_a_second_copy(self):
        issues = recipe_problems(
            self.README,
            {"docs/a.md": "Informed by Mia PR #1 (AGPL-3.0, no code adopted).\n"},
        )
        self.assertEqual(issues, ["recipe license restated outside README: docs/a.md"])
        self.assertEqual(
            recipe_problems(
                self.README,
                {"docs/a.ja.md": "sfxnz PR #1（MIT、コードは採用しない）\n"},
            ),
            ["recipe license restated outside README: docs/a.ja.md"],
        )

    def test_recipe_links_live_in_the_readme_table_only(self):
        issues = recipe_problems(
            self.README, {"docs/a.md": "See https://github.com/sfxnz/GLM-vLLM/pull/1\n"}
        )
        self.assertEqual(issues, ["recipe link outside README: docs/a.md"])

    def test_plain_citations_and_unrelated_licenses_pass(self):
        docs = {
            "docs/a.md": "Informed by Mia PR #1 (no code adopted); no new AGPL "
            "dependency. vLLM is Apache-2.0 (pinned, unchanged).\n"
        }
        self.assertEqual(recipe_problems(self.README, docs), [])


class CitationTests(unittest.TestCase):
    def test_short_name_citation_carries_the_project_version(self):
        self.assertEqual(
            citation_problems(
                "README.md", 'cite as "GLM-5.3-Flash BIZ 1.9.2"', "1.9.2"
            ),
            [],
        )
        self.assertEqual(
            citation_problems(
                "README.ja.md", "（引用は「GLM-5.3-Flash BIZ 1.9.1」の形）", "1.9.2"
            ),
            ["stale short-name citation: README.ja.md cites 1.9.1, version is 1.9.2"],
        )
        self.assertEqual(
            citation_problems("README.md", "# Title\n", "1.9.2"),
            ["missing short-name citation: README.md"],
        )


class DocumentMapTests(unittest.TestCase):
    DOCUMENTS = {
        "docs/README.md",
        "docs/README.ja.md",
        "docs/a.md",
        "docs/a.ja.md",
        "docs/b.md",
        "docs/plans/PLAN.md",
        "README.md",
    }

    def test_each_map_lists_every_page_of_its_language(self):
        english = "[EN](a.md) | [JA](a.ja.md)\n[EN](b.md)\n"
        self.assertEqual(map_problems("docs/README.md", english, self.DOCUMENTS), [])
        self.assertEqual(
            map_problems("docs/README.ja.md", "[EN](a.md)\n", self.DOCUMENTS),
            ["document missing from docs/README.ja.md: docs/a.ja.md"],
        )
        self.assertEqual(
            map_problems(
                "docs/README.md", "[EN](a.md#x) [JA](a.ja.md)", self.DOCUMENTS
            ),
            ["document missing from docs/README.md: docs/b.md"],
        )


class PairTests(unittest.TestCase):
    ENGLISH = "# A\n\n## B\n\n| x | y |\n|---|---|\n\n```sh\nrun\n```\n"

    def test_a_pair_with_the_same_shape_passes(self):
        japanese = "# あ\n\n## い\n\n| x | y |\n|---|---|\n\n```sh\nrun\n```\n"
        documents = {"a.md": self.ENGLISH, "a.ja.md": japanese, "b.md": "# only\n"}
        self.assertEqual(pair_problems(documents), [])

    def test_headings_table_rows_and_fences_are_compared(self):
        for japanese in (
            "# あ\n\n### い\n\n| x | y |\n|---|---|\n\n```sh\nrun\n```\n",
            "# あ\n\n## い\n\n| x | y |\n\n```sh\nrun\n```\n",
            "# あ\n\n## い\n\n| x | y |\n|---|---|\n",
        ):
            with self.subTest(japanese=japanese):
                self.assertEqual(
                    pair_problems({"a.md": self.ENGLISH, "a.ja.md": japanese}),
                    ["English/Japanese pair differs in shape: a.md, a.ja.md"],
                )

    def test_a_heading_inside_a_fence_is_not_a_heading(self):
        english = "# A\n\n```sh\n# a comment\n```\n"
        japanese = "# あ\n\n```sh\nrun\n```\n"
        self.assertEqual(pair_problems({"a.md": english, "a.ja.md": japanese}), [])


class ArchitectureTests(unittest.TestCase):
    ARCHITECTURE = (
        "| `glm53_setup/server.py`, `io.py` | launcher |\n"
        "| `glm53_setup/validation/benchmark_*.py` | benches |\n"
        "| `tools/` | `check_publication.py` |\n"
    )

    def test_every_module_is_named_or_matched(self):
        modules = {
            "glm53_setup/__init__.py",
            "glm53_setup/server.py",
            "glm53_setup/io.py",
            "glm53_setup/validation/benchmark_unpack.py",
            "tools/check_publication.py",
        }
        self.assertEqual(architecture_problems(self.ARCHITECTURE, modules), [])
        self.assertEqual(
            architecture_problems(self.ARCHITECTURE, modules | {"tools/new_tool.py"}),
            ["module not in architecture: tools/new_tool.py"],
        )


def link_directory(link, target):
    """A directory symlink, or a junction where Windows refuses symlinks."""
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        import _winapi

        _winapi.CreateJunction(str(target), str(link))


class PlanLinkTests(unittest.TestCase):
    def test_plan_links_must_resolve_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/plans").mkdir(parents=True)
            (root / "docs/other.md").write_text("x", encoding="utf-8")
            (root / "docs/plans/A_PLAN.md").write_text(
                "[ok](../other.md#top) [gone](../../records/run/REPORT.md) "
                "[web](https://example.org)\n```\n[fenced](missing.md)\n```\n",
                encoding="utf-8",
            )
            self.assertEqual(
                plan_link_problems(root),
                [
                    "broken plan link: docs/plans/A_PLAN.md -> ../../records/run/REPORT.md"
                ],
            )

    def test_linked_plans_resolve_from_where_they_live(self):
        # A checkout may link docs/plans to a directory outside it; the plans'
        # links are relative to that directory, and Windows resolves ".."
        # textually unless the path is resolved first.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / "repo"
            (root / "docs").mkdir(parents=True)
            (root / "docs/x.md").write_text("x", encoding="utf-8")
            (home / "plans").mkdir()
            (home / "plans/A_PLAN.md").write_text(
                "[x](../repo/docs/x.md)\n", encoding="utf-8"
            )
            link_directory(root / "docs/plans", home / "plans")
            self.assertEqual(plan_link_problems(root), [])


class AnchorTests(unittest.TestCase):
    def test_heading_anchors_follow_github_slugs(self):
        text = (
            "# Launch contracts\n"
            "## 6. Qualify the full model\n"
            "## `server preflight` and [links](x.md)\n"
            "## 切替後の decode 検査\n"
            "## Notes\n"
            "## Notes\n"
            "```\n# not a heading\n```\n"
        )
        self.assertEqual(
            heading_anchors(text),
            {
                "launch-contracts",
                "6-qualify-the-full-model",
                "server-preflight-and-links",
                "切替後の-decode-検査",
                "notes",
                "notes-1",
            },
        )

    def test_links_to_existing_anchors_pass(self):
        documents = {
            "SETUP.md": "## Run it\nSee [ops](docs/operations.md#storage-paths).\n",
            "docs/operations.md": "## Storage paths\n"
            "Back to [run](../SETUP.md#run-it) and [here](#storage-paths).\n",
        }
        self.assertEqual(anchor_problems(documents), [])

    def test_missing_anchor_is_reported_per_link(self):
        documents = {
            "a.md": "[x](b.md#gone) [y](#nowhere) [web](https://example.org/#frag)\n",
            "b.md": "## Here\n",
        }
        self.assertEqual(
            anchor_problems(documents),
            [
                "broken Markdown anchor: a.md -> b.md#gone",
                "broken Markdown anchor: a.md -> #nowhere",
            ],
        )

    def test_encoded_fenced_and_non_markdown_targets(self):
        documents = {
            "a.md": "[j](b.ja.md#%E6%A4%9C%E6%9F%BB) [code](tool.py#L3)\n"
            "```\n[not](b.ja.md#missing)\n```\n",
            "b.ja.md": "## 検査\n",
        }
        self.assertEqual(anchor_problems(documents), [])


def write(root, files):
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    return set(files)


RUN = "records/" + "20260101-run"  # built, so this file names no run itself


class RecordPathTests(unittest.TestCase):
    """A public file says what was measured, not which private records/ run holds it."""

    ALLOWED = {"v1/docs/benchmarks.md": 9}

    def check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = write(root, files)
            with unittest.mock.patch(
                "tools.check_publication.RECORD_PATHS_ALLOWED", self.ALLOWED
            ):
                return record_path_problems(root, names)

    def test_a_file_naming_a_run_is_reported_without_the_path(self):
        found = self.check(
            {
                "v1/tests/test_x.py": f"# measured on the pair ({RUN})\n",
                "v1/docs/vision.md": "measured on the pair, 2026-01-01\n",
                "v1/docs/benchmarks.md": f"{RUN}/a\n" * 9,
            }
        )
        self.assertEqual(
            found, ["private record path: v1/tests/test_x.py (1, allowed 0)"]
        )

    def test_an_allowance_holds_its_count_both_ways(self):
        more = self.check({"v1/docs/benchmarks.md": f"{RUN}/a\n" * 10})
        self.assertEqual(
            more, ["private record path: v1/docs/benchmarks.md (10, allowed 9)"]
        )
        fewer = self.check({"v1/docs/benchmarks.md": f"{RUN}/a\n" * 8})
        self.assertEqual(
            fewer, ["stale record-path allowance: v1/docs/benchmarks.md (8, allowed 9)"]
        )

    def test_an_allowance_for_a_file_that_is_gone_is_stale(self):
        found = self.check({"README.md": "x"})
        self.assertEqual(
            found,
            ["stale record-path allowance: v1/docs/benchmarks.md (not a public file)"],
        )


LINE2 = {
    "README.md": "x",
    "README.ja.md": "x",
    "SETUP.md": "x",
    "SETUP.ja.md": "x",
    "CHANGELOG.md": "# Changelog\n\n## 2.0.5 — 2026-10-04\n\n- x\n",
    "CHANGELOG.ja.md": "# 変更履歴\n\n## 2.0.5 — 2026-10-04\n\n- x\n",
    "pyproject.toml": '[project]\nname = "x"\nversion = "2.0.5"\nlicense = "Apache-2.0"\n',
    "config/model.lock.json": '{"model": "nvidia/GLM-5.3-Flash-NVFP4", "revision": "'
    + "a" * 40
    + '"}',
}


class Line2Tests(unittest.TestCase):
    """The TensorFold lines get the checks that fit them: files, version, license, pin."""

    def check(self, **changes):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = dict(LINE2, **changes)
            names = write(root, {k: v for k, v in files.items() if v is not None})
            return line_problems("v2", root, names)

    def test_a_complete_line_passes(self):
        self.assertEqual(self.check(), [])

    def test_missing_files_are_named_under_v2(self):
        found = self.check(**{"SETUP.ja.md": None, "config/model.lock.json": None})
        self.assertIn("missing required file: v2/SETUP.ja.md", found)
        self.assertIn("missing required file: v2/config/model.lock.json", found)

    def test_an_unpinned_revision_is_reported(self):
        lock = '{"model": "m", "revision": "main"}'
        found = self.check(**{"config/model.lock.json": lock})
        self.assertIn("v2: model and revision must be pinned", found)

    def test_version_license_and_changelog_sections(self):
        project = '[project]\nname = "x"\nversion = "2.0.6"\nlicense = "MIT"\n'
        found = self.check(**{"pyproject.toml": project})
        self.assertIn("v2: unexpected project license", found)
        self.assertIn("v2: CHANGELOG.md has no section for 2.0.6", found)
        self.assertIn("v2: CHANGELOG.ja.md has no section for 2.0.6", found)
        project = '[project]\nname = "x"\nversion = "2.1"\nlicense = "Apache-2.0"\n'
        self.assertIn(
            "v2: expected release version", self.check(**{"pyproject.toml": project})
        )

    def test_the_audit_runs_the_line_checks_on_each_tensorfold_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = write(root, {"v2/README.md": "x", "v3/README.md": "x"})
            found = problems(root, names)
        self.assertIn("missing required file: v2/SETUP.md", found)
        self.assertIn("missing required file: v3/SETUP.md", found)


class DuplicateNumberTests(unittest.TestCase):
    """A warning: measured-looking numbers on more than one English page of a line."""

    def test_numbers_repeated_across_pages_of_a_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = write(
                root,
                {
                    "v1/README.md": "decode 45.43 tok/s, prefill 1,233.4, `99.99` in code\n",
                    "v1/docs/benchmarks.md": "| 45.43 | 1,233.4 | 99.99 |\n",
                    "v1/docs/benchmarks.ja.md": "45.43\n",
                    "v1/CHANGELOG.md": "45.43\n",
                    "v2/README.md": "45.43 and version 1.29.2\n",
                },
            )
            found = duplicate_numbers(root, names)
        self.assertEqual(
            found,
            {
                ("v1", "1,233.4"): ["v1/README.md", "v1/docs/benchmarks.md"],
                ("v1", "45.43"): ["v1/README.md", "v1/docs/benchmarks.md"],
            },
        )
