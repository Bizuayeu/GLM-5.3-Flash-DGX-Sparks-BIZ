"""Print one version's CHANGELOG section; the release workflow publishes it.

The version's major number names its line: N.x reads vN/ (1.x v1/, 2.x v2/, 3.x v3/).
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

# The repository root, above the line directories.
REPO = Path(__file__).resolve().parents[1]
VERSION = r"\d+\.\d+\.\d+"


def section(changelog, version):
    if not re.fullmatch(VERSION, version):
        raise ValueError(f"not a release version: {version!r}")
    match = re.search(
        rf"(?ms)^## {re.escape(version)} [^\n]*\n(.*?)(?=^## |\Z)", changelog
    )
    if match is None or not match[1].strip():
        raise ValueError(f"CHANGELOG.md has no notes for {version}")
    return match[1].strip() + "\n"


def project_dir(repo, version):
    """The line directory of ``version``: vN/ for N.x."""
    if not re.fullmatch(VERSION, version):
        raise ValueError(f"not a release version: {version!r}")
    directory = repo / f"v{version.split('.')[0]}"
    if not (directory / "pyproject.toml").is_file():
        raise ValueError(f"no line directory for {version}: {directory.name}/")
    return directory


def notes(repo, version, match_project=False):
    """The section ``version`` publishes, from its line's CHANGELOG.md."""
    directory = project_dir(repo, version)
    changelog = (directory / "CHANGELOG.md").read_text(encoding="utf-8")
    if match_project:
        project = tomllib.loads(
            (directory / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        if project["version"] != version:
            raise ValueError(
                f"tag and {directory.name}/pyproject.toml disagree on the version"
            )
        # A tag publishes a released section only: a line in preparation keeps its
        # version's heading without a date until the release.
        if not re.search(
            rf"(?m)^## {re.escape(version)} — \d{{4}}-\d{{2}}-\d{{2}}$", changelog
        ):
            raise ValueError(
                f"{directory.name}/CHANGELOG.md: the {version} heading has no release date"
            )
    return section(changelog, version)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument(
        "--match-project",
        action="store_true",
        help="fail unless the line's pyproject.toml carries the same version",
    )
    args = parser.parse_args()
    try:
        text = notes(REPO, args.version, args.match_project)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()
