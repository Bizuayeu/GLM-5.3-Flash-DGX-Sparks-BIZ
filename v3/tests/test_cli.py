import io
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from glm53_tf import __main__ as cli
from glm53_tf import score_nll

LINE = Path(__file__).resolve().parents[1]
# What a command must not import to print its help: the engine's and the clients'.
HEAVY = ("torch", "huggingface_hub", "tokenizers", "filelock")
HELP = [
    ("download", "--background"),
    ("verify-download", "--hf"),
    ("tool-gate", "--upstream"),
    ("decode-check", "PROMPT_KIND"),
    ("decode-divergence", "TOKENS_OUT"),
    ("score-nll", "--tokenizer"),
    ("bench", "--kinds"),
    ("long-input", "--passphrases"),
]


class PublicCliTests(unittest.TestCase):
    def invoke(self, *args, cwd=LINE):
        return subprocess.run(
            [sys.executable, "-m", "glm53_tf", *args],
            cwd=cwd,
            env={**os.environ, "PYTHONPATH": str(LINE)},
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version_is_the_lines_and_each_command_has_help(self):
        version = tomllib.loads((LINE / "pyproject.toml").read_text())["project"][
            "version"
        ]
        result = self.invoke("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), version)
        self.assertEqual(sorted(cli.COMMANDS), sorted(c for c, _ in HELP))
        for command, option in HELP:
            with self.subTest(command=command):
                result = self.invoke(command, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(option, result.stdout)

    def test_help_imports_no_engine_or_client_package(self):
        script = (
            "import sys\n"
            "from glm53_tf.__main__ import main\n"
            "try:\n"
            "    main([sys.argv[1], '--help'])\n"
            "except SystemExit:\n"
            "    pass\n"
            f"print([m for m in {HEAVY!r} if m in sys.modules])\n"
        )
        for command, _ in HELP:
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "-c", script, command],
                    cwd=LINE,
                    env={**os.environ, "PYTHONPATH": str(LINE)},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip().splitlines()[-1], "[]")

    def test_an_unknown_command_exits_with_a_usage_error(self):
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as caught, redirect_stderr(stderr):
            cli.main(["nope"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("unknown command: nope", stderr.getvalue())

    def test_checkout_resources_do_not_depend_on_callers_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.invoke("--version", cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_commands_exit_status_is_the_processs(self):
        # score-nll returns 2 for a set it cannot score and 1 for a failed request.
        for status in (0, 1, 2):
            with (
                self.subTest(status=status),
                patch.object(score_nll, "main", return_value=status) as main,
                self.assertRaises(SystemExit) as caught,
            ):
                cli.main(["score-nll", "--url", "u"])
            self.assertEqual(caught.exception.code, status)
            main.assert_called_once_with(["--url", "u"])


if __name__ == "__main__":
    unittest.main()
