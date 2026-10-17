import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from glm53_tf import decode_divergence


def sample(text):
    return {"text": text}


def compare(a, b):
    """Run the tool on two text records; return its exit code and printed lines."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, samples in (("a", a), ("b", b)):
            path = Path(tmp) / f"{name}.json"
            path.write_text(json.dumps({"samples": samples}), encoding="utf-8")
            paths.append(str(path))
        out = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out):
            try:
                decode_divergence.main(paths)
            except SystemExit as error:
                code = error.code
    return code, out.getvalue().splitlines()


class DecodeDivergenceTests(unittest.TestCase):
    def test_identical_runs_report_each_sample_identical(self):
        samples = [sample("abc"), sample("de")]
        code, lines = compare(samples, samples)
        self.assertIn(code, (0, None))
        self.assertEqual(
            lines,
            [
                "sample 0: identical (3 characters)",
                "sample 1: identical (2 characters)",
            ],
        )

    def test_the_first_differing_character_and_text_are_reported(self):
        _, lines = compare([sample("abcd")], [sample("abXd")])
        self.assertEqual(lines[0], "sample 0: first differing character 2/4")
        self.assertEqual(lines[1:], ["   A: 'abcd'", "   B: 'abXd'"])

    def test_a_shorter_first_run_differs_where_it_ends(self):
        _, lines = compare([sample("ab")], [sample("abc")])
        self.assertEqual(lines[0], "sample 0: first differing character 2/2")

    def test_a_shorter_second_run_differs_where_it_ends(self):
        _, lines = compare([sample("abc")], [sample("ab")])
        self.assertEqual(lines[0], "sample 0: first differing character 2/3")

    def test_differing_sample_counts_are_not_reported_as_matching(self):
        _, lines = compare([sample("a"), sample("b")], [sample("a")])
        self.assertEqual(lines[-1], "samples: A has 2, B has 1")


if __name__ == "__main__":
    unittest.main()
