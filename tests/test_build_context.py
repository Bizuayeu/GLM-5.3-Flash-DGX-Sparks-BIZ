"""Every line's images build from the checkout root through its one .dockerignore."""

import re
import unittest
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[1]


def ignore_patterns():
    lines = (CHECKOUT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def pattern(text):
    """A .dockerignore pattern as a regular expression over slash-separated paths."""
    out, i = "", 0
    while i < len(text):
        if text.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif text.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            out += {"*": "[^/]*", "?": "[^/]"}.get(text[i], re.escape(text[i]))
            i += 1
    return re.compile(out)


def admitted(path, patterns):
    """Docker's rule: the last pattern matching the path or a parent of it decides."""
    parts = path.split("/")
    keep = True
    for line in patterns:
        negated = line.startswith("!")
        regex = pattern(line.removeprefix("!").strip("/"))
        if any(regex.fullmatch("/".join(parts[:n])) for n in range(1, len(parts) + 1)):
            keep = negated
    return keep


class BuildContextTests(unittest.TestCase):
    def test_the_ignore_rule_reads_parents_and_last_matches(self):
        patterns = ["*", "!v2/scripts/", "**/__pycache__"]
        self.assertTrue(admitted("v2/scripts/serve.sh", patterns))
        self.assertFalse(admitted("v2/README.md", patterns))
        self.assertFalse(admitted("v2/scripts/__pycache__/x.pyc", patterns))

    def test_every_image_copies_only_what_the_context_admits(self):
        # Every line builds from the checkout root through its one .dockerignore.
        patterns = ignore_patterns()
        for dockerfile in (
            "v1/docker/Dockerfile.reference",
            "v2/docker/Dockerfile",
            "v3/docker/Dockerfile",
            "v3/docker/Dockerfile.build",
        ):
            text = (CHECKOUT / dockerfile).read_text(encoding="utf-8")
            self.assertTrue(admitted(dockerfile, patterns), dockerfile)
            for line in text.splitlines():
                if not line.startswith("COPY ") or line.startswith("COPY --from="):
                    continue  # a stage's files come from that stage, not from the context
                for source in line.split()[1:-1]:
                    path = CHECKOUT / source
                    files = [path] if path.is_file() else sorted(path.rglob("*"))
                    self.assertTrue(path.exists(), source)
                    for f in files:
                        if f.is_file() and "__pycache__" not in f.parts:
                            name = f.relative_to(CHECKOUT).as_posix()
                            with self.subTest(dockerfile=dockerfile, file=name):
                                self.assertTrue(admitted(name, patterns))


if __name__ == "__main__":
    unittest.main()
