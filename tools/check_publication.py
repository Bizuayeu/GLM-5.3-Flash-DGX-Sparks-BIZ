"""Audit checkout/public-export contents without displaying matched sensitive text."""

import argparse
import fnmatch
import json
import posixpath
import re
import subprocess
import tomllib
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

# The repository root: the 1.x line lives in v1/, the 2.x line in v2/, the 3.x line in v3/.
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "README.md",
    "README.ja.md",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    ".gitignore",
    ".dockerignore",
}
# The project checks below name files relative to this directory.
PROJECT = "v1"
PROJECT_REQUIRED = {
    "README.md",
    "README.ja.md",
    "SETUP.md",
    "SETUP.ja.md",
    "CHANGELOG.md",
    "CHANGELOG.ja.md",
    "config/runtime.lock.json",
    "pyproject.toml",
}
PRIVATE_DIRS = {"state", "records", "upstream", ".ssh", ".venv", ".claude-local-test"}
PRIVATE_SUFFIXES = {
    ".safetensors",
    ".gguf",
    ".bin",
    ".pt",
    ".pth",
    ".onnx",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".bundle",
    ".tar",
    ".gz",
    ".zip",
    ".log",
    ".jsonl",
}
SENSITIVE = [
    re.compile(r"-----BEGIN " + r"(?:OPENSSH |RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"\bhf_" + r"[A-Za-z0-9]{25,}\b"),
    re.compile(r"\bgh[pousr]_" + r"[A-Za-z0-9]{30,}\b"),
    re.compile(r"(?i)[a-z]:[/\\]Users[/\\][a-z0-9_.-]+"),
    re.compile(r"/home/" + r"[a-z0-9_.-]+/"),
]
# Images the READMEs show: only in an assets/ directory, by file signature.
IMAGE_SIGNATURES = {".png": (b"\x89PNG\r\n\x1a\n",), ".webp": (b"RIFF", b"WEBP")}


def is_asset_image(name, data):
    """A PNG or WebP under an assets/ directory whose bytes are what it claims."""
    signature = IMAGE_SIGNATURES.get(Path(name).suffix.lower())
    if "assets" not in Path(name).parts[:-1] or signature is None:
        return False
    if len(signature) == 1:
        return data.startswith(signature[0])
    return data.startswith(signature[0]) and data[8:12] == signature[1]


# README headline table and the benchmark document that owns its numbers.
VERSION = r"(\d+\.\d+\.\d+)"
HEADLINES = {
    "README.md": (
        "docs/benchmarks.md",
        rf"(?m)^#+ Headline measurements \({VERSION}\)",
        rf"(?m)^## Measurements on {VERSION}$",
    ),
    "README.ja.md": (
        "docs/benchmarks.ja.md",
        rf"(?m)^#+ 主要な測定値（{VERSION}）",
        rf"(?m)^## {VERSION}での測定$",
    ),
}


def headline_problems(name, readme, benchmarks):
    """The README headline must carry the newest version the benchmarks measured."""
    _, headline, measured = HEADLINES[name]
    versions = re.findall(measured, benchmarks)
    if not versions:
        return [f"no versioned measurements beside {name}"]
    latest = max(versions, key=lambda v: tuple(map(int, v.split("."))))
    shown = re.search(headline, readme)
    if shown is None:
        return [f"missing headline measurements: {name}"]
    if shown[1] != latest:
        return [
            f"stale headline measurements: {name} has {shown[1]}, latest is {latest}"
        ]
    return []


# Other recipes: README's table owns their links and licences; documents cite by name.
RECIPE_LINK = re.compile(r"https://(?:github\.com|huggingface\.co)/([\w.-]+/[\w.-]+)")
RESTATED_LICENSE = re.compile(
    r"[(（](?:AGPL-3\.0|MIT|Apache-2\.0|no license|ライセンスなし)[,;、]"
    r"|[,、] ?(?:MIT|no license|ライセンスなし)[)）]"
)


def recipe_problems(readme, documents):
    """Recipes come from README's table rows; other documents hold no copy.

    A link to some other repository of the same author is evidence, not a copy.
    """
    recipes = {
        recipe
        for line in readme.splitlines()
        if line.startswith("| [")
        for recipe in RECIPE_LINK.findall(line)
    }
    owners = sorted({recipe.split("/")[0] for recipe in recipes})
    cited = re.compile("|".join(map(re.escape, owners + ["Mia PR"])))
    problems = []
    for name, text in sorted(documents.items()):
        if recipes & set(RECIPE_LINK.findall(text)):
            problems.append(f"recipe link outside README: {name}")
        if owners and any(
            cited.search(line) and RESTATED_LICENSE.search(line)
            for line in text.splitlines()
        ):
            problems.append(f"recipe license restated outside README: {name}")
    return problems


# The README cites the stack by short name and version; pyproject.toml owns the version.
CITATIONS = {
    "README.md": rf'cite as "NVFP4 BIZ {VERSION}"',
    "README.ja.md": rf"引用は「NVFP4 BIZ {VERSION}」",
}


def citation_problems(name, readme, version):
    """The short-name citation in a README carries the released version."""
    shown = re.search(CITATIONS[name], readme)
    if shown is None:
        return [f"missing short-name citation: {name}"]
    if shown[1] != version:
        return [
            f"stale short-name citation: {name} cites {shown[1]}, version is {version}"
        ]
    return []


# A document map lists every public page of its directory's docs/ in its language;
# an unlisted page is lost. The repository's map and 1.x's both follow it.
MAPS = {"docs/README.md": False, "docs/README.ja.md": True}


def map_problems(map_name, map_text, documents):
    """Every docs/*.md of the map's language is a link target of the map."""
    japanese = MAPS[map_name]
    linked = {target.strip() for target in re.findall(r"\]\(([^)#]+)", map_text)}
    problems = []
    for name in sorted(documents):
        if name in MAPS or not name.startswith("docs/") or name.count("/") != 1:
            continue
        if name.endswith(".ja.md") != japanese:
            continue
        if name.removeprefix("docs/") not in linked:
            problems.append(f"document missing from {map_name}: {name}")
    return problems


# Architecture names every module, by file name or by a pattern such as benchmark_*.py.
MODULE_DIRS = (
    "glm53_setup/",
    "glm53_setup/runtime/",
    "glm53_setup/validation/",
    "tools/",
)


def architecture_problems(architecture, modules):
    """Every module is matched by a backticked name or pattern in the architecture page."""
    patterns = re.findall(r"`([\w*/.-]+\.py)`", architecture)
    problems = []
    for name in sorted(modules):
        base = name.rsplit("/", 1)[-1]
        if base == "__init__.py":
            continue
        if not any(
            fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(base, pattern)
            for pattern in patterns
        ):
            problems.append(f"module not in architecture: {name}")
    return problems


def prose(content):
    """Markdown without its fenced blocks; fenced examples are not links."""
    return re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", content)


def plan_link_problems(root):
    """Relative links in the untracked plans resolve to something on disk."""
    problems = []
    for path in sorted((root / "docs/plans").glob("*.md")):
        text = prose(path.read_text(encoding="utf-8"))
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            url = urlsplit(target.strip().strip("<>"))
            if url.scheme or not url.path:
                continue
            # Resolved first: docs/plans may be a link, and Windows resolves ".." textually.
            if not (path.resolve().parent / unquote(url.path)).exists():
                problems.append(
                    f"broken plan link: docs/plans/{path.name} -> {url.path}"
                )
    return problems


def heading_anchors(text):
    """The anchors GitHub gives the headings of a Markdown text."""
    anchors = set()
    seen = {}
    for heading in re.findall(r"(?m)^#{1,6}[ \t]+(.+?)[ \t#]*$", prose(text)):
        heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.replace("`", ""))
        slug = "".join(
            "-" if ch == " " else ch
            for ch in heading.strip().lower()
            if ch in " -_" or unicodedata.category(ch)[0] in "LNM"
        )
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def anchor_problems(documents):
    """Each #anchor of a relative Markdown link names a heading of its target."""
    anchors = {name: heading_anchors(text) for name, text in documents.items()}
    problems = []
    for name in sorted(documents):
        for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)", prose(documents[name])):
            url = urlsplit(target.strip("<>"))
            if url.scheme or not url.fragment:
                continue
            path = name
            if url.path:
                path = posixpath.normpath(
                    posixpath.join(posixpath.dirname(name), unquote(url.path))
                )
            if path in anchors and unquote(url.fragment) not in anchors[path]:
                problems.append(f"broken Markdown anchor: {name} -> {target}")
    return problems


def shape(text):
    """Heading levels, table rows and fences of a Markdown text: what a translation keeps."""
    levels, rows, fences, fenced = [], 0, 0, False
    for line in text.splitlines():
        if line.startswith("```"):
            fences += 1
            fenced = not fenced
        elif not fenced:
            heading = re.match(r"(#{1,6}) ", line)
            if heading:
                levels.append(len(heading.group(1)))
            rows += line.startswith("|")
    return levels, rows, fences


def pair_problems(documents):
    """Each *.ja.md has the shape of its English page, so a section added to one is in both."""
    problems = []
    for name in sorted(documents):
        english = name.removesuffix(".ja.md") + ".md"
        if name.endswith(".ja.md") and english in documents:
            if shape(documents[english]) != shape(documents[name]):
                problems.append(
                    f"English/Japanese pair differs in shape: {english}, {name}"
                )
    return problems


def public_files(root, export_tree=False):
    if export_tree:
        return {
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts
        }
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={root.as_posix()}",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        capture_output=True,
        check=True,
    )
    return set(result.stdout.decode("utf-8").strip("\0").split("\0")) - {""}


def audit(root, files):
    problems = [f"missing required file: {name}" for name in sorted(REQUIRED - files)]
    for name in sorted(files):
        path = root / name
        parts = Path(name).parts
        if (
            set(parts) & PRIVATE_DIRS
            or path.suffix.lower() in PRIVATE_SUFFIXES
            or path.name == "site.json"
            or path.name.endswith(".local.json")
            or (path.name.startswith(".env") and path.name != ".env.example")
            or ("docs" in parts and "PLAN" in path.name)
        ):
            problems.append(f"private/generated path: {name}")
        if not path.is_file():
            problems.append(f"missing working file: {name}")
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            problems.append(f"linked/outside file: {name}")
            continue
        if path.stat().st_size > 2_000_000:
            problems.append(f"unexpected large file: {name}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if not is_asset_image(name, path.read_bytes()):
                problems.append(f"unexpected binary file: {name}")
            continue
        if any(pattern.search(content) for pattern in SENSITIVE):
            problems.append(f"sensitive-text candidate: {name}")
        if path.suffix.lower() != ".md":
            continue
        # The repository uses inline Markdown links.
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", prose(content)):
            target = target.strip().strip("<>")
            url = urlsplit(target)
            if url.scheme or not url.path:
                continue
            resolved = (path.parent / unquote(url.path)).resolve()
            if not resolved.is_relative_to(root.resolve()):
                problems.append(f"outside Markdown link: {name}")
            else:
                relative = resolved.relative_to(root.resolve()).as_posix()
                if relative not in files and not any(
                    f.startswith(relative + "/") for f in files
                ):
                    problems.append(f"non-public Markdown target: {name} -> {relative}")
    return problems


def project_problems(root, files):
    """The 1.x checks, on ``files`` named relative to the project directory ``root``."""
    problems = [
        f"missing required file: {PROJECT}/{name}"
        for name in sorted(PROJECT_REQUIRED - files)
    ]
    documents = {name for name in files if name.endswith(".md")}
    for map_name in MAPS:
        if map_name in files:
            problems += map_problems(
                map_name, (root / map_name).read_text(encoding="utf-8"), documents
            )
    modules = {
        name
        for name in files
        if name.endswith(".py") and name.rsplit("/", 1)[0] + "/" in MODULE_DIRS
    }
    for name in ("docs/architecture.md", "docs/architecture.ja.md"):
        if name in files:
            problems += architecture_problems(
                (root / name).read_text(encoding="utf-8"), modules
            )
    if "config/runtime.lock.json" in files:
        lock = json.loads(
            (root / "config/runtime.lock.json").read_text(encoding="utf-8")
        )
        if not re.fullmatch(
            r"[^\s]+@sha256:[0-9a-f]{64}", lock["image"]
        ) or not re.fullmatch(r"[0-9a-f]{40}", lock["revision"]):
            problems.append("runtime artifacts must be digest/revision pinned")
    for name, (benchmarks, *_) in HEADLINES.items():
        if name in files and benchmarks in files:
            problems += headline_problems(
                name,
                (root / name).read_text(encoding="utf-8"),
                (root / benchmarks).read_text(encoding="utf-8"),
            )
    if "README.md" in files:
        problems += recipe_problems(
            (root / "README.md").read_text(encoding="utf-8"),
            {
                name: (root / name).read_text(encoding="utf-8")
                for name in files
                if name.startswith("docs/") and name.endswith(".md")
            },
        )
    if "pyproject.toml" in files:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
        if not re.fullmatch(r"\d+\.\d+\.\d+", project["version"]):
            problems.append("expected release version")
        if project["license"] != "Apache-2.0":
            problems.append("unexpected project license")
        for name in CITATIONS:
            if name in files:
                problems += citation_problems(
                    name, (root / name).read_text(encoding="utf-8"), project["version"]
                )
    return problems


# The TensorFold lines' checks (2.x, 3.x): the files a line needs, its version, license
# and model pin. 1.x has its own, above.
TENSORFOLD_LINES = ("v2", "v3")
LINE_REQUIRED = {
    "README.md",
    "README.ja.md",
    "SETUP.md",
    "SETUP.ja.md",
    "CHANGELOG.md",
    "CHANGELOG.ja.md",
    "pyproject.toml",
    "config/model.lock.json",
}


def line_problems(line, root, files):
    """A TensorFold line's checks, on ``files`` named relative to its directory ``root``."""
    problems = [
        f"missing required file: {line}/{name}"
        for name in sorted(LINE_REQUIRED - files)
    ]
    if "config/model.lock.json" in files:
        lock = json.loads((root / "config/model.lock.json").read_text(encoding="utf-8"))
        if not lock.get("model") or not re.fullmatch(
            r"[0-9a-f]{40}", str(lock.get("revision", ""))
        ):
            problems.append(f"{line}: model and revision must be pinned")
    if "pyproject.toml" in files:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
        version = project.get("version", "")
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            problems.append(f"{line}: expected release version")
        if project.get("license") != "Apache-2.0":
            problems.append(f"{line}: unexpected project license")
        for name in ("CHANGELOG.md", "CHANGELOG.ja.md"):
            if name in files and not re.search(
                rf"(?m)^## {re.escape(version)} ",
                (root / name).read_text(encoding="utf-8"),
            ):
                problems.append(f"{line}: {name} has no section for {version}")
    return problems


# A measured-looking number: thousands separators or two or more decimals, not part
# of a version or a longer number.
MEASURED = re.compile(
    r"(?<![\w.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2,})(?![\w.,]*\d)"
)


def duplicate_numbers(root, files):
    """Measured-looking numbers on more than one English page of a line, by line.

    A warning for whoever edits the documents (``--duplicates``), not a failure: a
    number has one owner page, but a page may cite it deliberately. Changelogs,
    Japanese pages and code spans are left out.
    """
    seen = {}
    for name in sorted(files):
        path = Path(name)
        if (
            path.suffix != ".md"
            or name.endswith(".ja.md")
            or path.name.startswith("CHANGELOG")
        ):
            continue
        line = path.parts[0] if path.parts[0] in (PROJECT, *TENSORFOLD_LINES) else ""
        text = re.sub(
            r"`[^`\n]*`", "", prose((root / name).read_text(encoding="utf-8"))
        )
        for number in set(MEASURED.findall(text)):
            seen.setdefault((line, number), set()).add(name)
    return {key: sorted(names) for key, names in seen.items() if len(names) > 1}


# A run directory of the untracked records/ (records/<YYYYMMDD>-<topic>), which no reader of
# the public repository can open: a public file says what was measured instead.
RECORD_PATH = re.compile(r"records/\d{8}-")
# Files allowed their current count: the data's own provenance, which stays with the data.
RECORD_PATHS_ALLOWED = {
    "v1/config/nll_set.json": 4,  # provenance of each measured set
    "v2/config/nll_set.json": 4,  # 1.x's set, byte for byte
    "v3/config/nll_set.json": 4,  # the same set
    "v1/config/freedombench-ja.lock.json": 1,  # provenance
}


def record_path_problems(root, files):
    """A public file that names a private records/ run directory, beyond what
    ``RECORD_PATHS_ALLOWED`` allows it; an allowance above the file's count is stale."""
    found = []
    for name in sorted(files):
        try:
            text = (root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        count = len(RECORD_PATH.findall(text))
        allowed = RECORD_PATHS_ALLOWED.get(name, 0)
        if count > allowed:
            found.append(f"private record path: {name} ({count}, allowed {allowed})")
        elif count < allowed:
            found.append(
                f"stale record-path allowance: {name} ({count}, allowed {allowed})"
            )
    for name in sorted(set(RECORD_PATHS_ALLOWED) - set(files)):
        found.append(f"stale record-path allowance: {name} (not a public file)")
    return found


def problems(root, files, plans=False):
    """Every issue of the repository at ``root`` whose public files are ``files``."""
    found = audit(root, files)
    found += record_path_problems(root, files)
    documents = {name for name in files if name.endswith(".md")}
    texts = {name: (root / name).read_text(encoding="utf-8") for name in documents}
    found += anchor_problems(texts)
    found += pair_problems(texts)
    for map_name in MAPS:
        # The repository's own map, under the same rule as 1.x's in v1/docs/.
        if map_name in files:
            found += map_problems(
                map_name, (root / map_name).read_text(encoding="utf-8"), documents
            )
    if plans:
        found += plan_link_problems(root)
    prefix = PROJECT + "/"
    found += project_problems(
        root / PROJECT,
        {name.removeprefix(prefix) for name in files if name.startswith(prefix)},
    )
    for line in TENSORFOLD_LINES:
        prefix = line + "/"
        line_files = {
            name.removeprefix(prefix) for name in files if name.startswith(prefix)
        }
        if line_files:
            found += line_problems(line, root / line, line_files)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--export-tree",
        action="store_true",
        help="Inspect an exported tree without Git",
    )
    parser.add_argument(
        "--plans",
        action="store_true",
        help="Also check the relative links of the untracked docs/plans/",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="Also list measured-looking numbers found on more than one page of a line"
        " (a warning; the exit status does not change)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    files = public_files(root, args.export_tree)
    found = problems(root, files, args.plans)
    for problem in found:
        print(problem)
    if args.duplicates:
        duplicates = duplicate_numbers(root, files)
        for (line, number), names in sorted(duplicates.items()):
            print(f"duplicate candidate: {line or '.'} {number}: {', '.join(names)}")
        print(f"Duplicate candidates: {len(duplicates)}")
    print(f"Publication audit: {len(files)} files, {len(found)} issues")
    raise SystemExit(bool(found))


if __name__ == "__main__":
    main()
