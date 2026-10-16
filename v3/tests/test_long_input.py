import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import long_input

BLOCK = {"prefill_s": 140.5, "heat_wait_s": 2.0, "cached": 0, "rounds": 3}
BLOCK_KEPT = {"prefill_s": 140.5, "heat_wait_s": 2.0, "cached": 0}
USAGE = {
    "prompt_tokens": 199652,
    "completion_tokens": 9,
    "prompt_tokens_details": {"cached_tokens": 0},
}


def ledger(messages):
    """The ledger rows of a request's user message (before the question)."""
    return messages[1]["content"].split("\n\n")[0].split("\n")


def tokens(messages):
    """A stand-in for /tokenize: 20 tokens per line and 30 for the rest."""
    return 20 * len(ledger(messages)) + 30


def answer(content):
    reply = {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": USAGE,
        "tensorfold": dict(BLOCK, token_ids=[1, 2]),
    }
    return [json.dumps(reply).encode()]


def streamed(content):
    chunks = [{"choices": [{"delta": {"reasoning_content": "look"}}]}]
    chunks += [{"choices": [{"delta": {"content": line}}]} for line in content]
    chunks += [
        {
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "tensorfold": dict(BLOCK, token_ids=[1, 2]),
        },
        {"choices": [], "usage": USAGE},
    ]
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(argv, content, sent=None, auth=None):
    """Run main() against canned replies; return (exit status, printed JSON line).

    /tokenize answers with tokens(); the short request with "ok"; the measured
    request with `content` (a list of streamed pieces when streamed). Every
    monotonic reading is one second after the previous.
    """
    sent = [] if sent is None else sent
    auth = [] if auth is None else auth

    def urlopen(req, timeout=None):
        auth.append(req.get_header("Authorization"))
        body = json.loads(req.data)
        sent.append((req.full_url, body))
        if req.full_url.endswith("/tokenize"):
            return Reply([json.dumps({"count": tokens(body["messages"])}).encode()])
        if body["max_tokens"] == 4:
            return Reply(answer("ok"))
        if body["stream"]:
            return Reply(streamed(content))
        return Reply(answer(content))

    out = io.StringIO()
    clock = iter(range(1000))
    with (
        patch.object(long_input.urllib.request, "urlopen", urlopen),
        patch.object(long_input.time, "monotonic", lambda: next(clock)),
        patch.object(long_input.time, "time", lambda: 1759700000.04),
        contextlib.redirect_stdout(out),
    ):
        status = long_input.main(argv)
    return status, json.loads(out.getvalue())


class PromptTests(unittest.TestCase):
    def test_one_passphrase_sits_in_the_middle_of_1xs_ledger(self):
        messages = long_input.one_messages(8806)
        self.assertEqual(
            messages[0],
            {
                "role": "system",
                "content": "You are a careful archivist. Read the ledger.",
            },
        )
        rows = ledger(messages)
        self.assertEqual(len(rows), 8807)
        self.assertEqual(
            rows[0],
            "Ledger 0: the river barge delivered sacks of barley "
            "to the northern granary at dusk.",
        )
        self.assertEqual(
            rows[4403],
            "IMPORTANT: the passphrase for the archive is AMBER-FALCON-4817.",
        )
        self.assertTrue(rows[4402].startswith("Ledger 4402:"))
        self.assertTrue(rows[4404].startswith("Ledger 4403:"))
        self.assertTrue(rows[-1].startswith("Ledger 8805:"))
        self.assertTrue(
            messages[1]["content"].endswith(
                "\n\nWhat is the passphrase for the archive? "
                "Reply with the passphrase only."
            )
        )

    def test_three_passphrases_at_a_twentieth_the_middle_and_nineteen_twentieths(self):
        rows = ledger(long_input.three_messages(100))
        self.assertEqual(len(rows), 103)
        self.assertEqual(
            rows[5],
            "IMPORTANT: the start passphrase of the archive is AMBER-FALCON-4817.",
        )
        self.assertEqual(
            rows[51],
            "IMPORTANT: the middle passphrase of the archive is COBALT-HERON-2093.",
        )
        self.assertEqual(
            rows[97],
            "IMPORTANT: the end passphrase of the archive is SAFFRON-LYNX-7731.",
        )
        # Each passphrase goes before the ledger line at its position.
        self.assertTrue(rows[4].startswith("Ledger 4:"))
        self.assertTrue(rows[6].startswith("Ledger 5:"))
        self.assertTrue(rows[52].startswith("Ledger 50:"))
        self.assertTrue(rows[98].startswith("Ledger 95:"))
        self.assertTrue(
            long_input.three_messages(100)[1]["content"].endswith(
                "\n\nList the start, middle and end passphrases of the archive, "
                "one per line, nothing else."
            )
        )

    def test_the_fitted_line_count_stays_at_or_below_the_target(self):
        def growing(messages):
            # Tokens per line that grow with the length: the first estimate overshoots.
            rows = len(ledger(messages))
            return 20 * rows + rows * rows // 1000000

        for count in (tokens, growing):
            for target in (5000, 499622, 1036859):
                for build in (long_input.one_messages, long_input.three_messages):
                    with self.subTest(count=count, target=target, build=build):
                        lines, n = long_input.fit(target, build, count)
                        self.assertLessEqual(n, target)
                        self.assertEqual(n, count(build(lines)))
                        self.assertGreater(n, 0.99 * target)


class CorrectnessTests(unittest.TestCase):
    def test_correct_only_when_every_passphrase_is_in_the_reply(self):
        all_three = "AMBER-FALCON-4817\nCOBALT-HERON-2093\nSAFFRON-LYNX-7731"
        found = long_input.found(all_three, long_input.THREE)
        self.assertEqual(found, {"start": True, "middle": True, "end": True})
        found = long_input.found("AMBER-FALCON-4817\nCOBALT-HERON", long_input.THREE)
        self.assertEqual(found, {"start": True, "middle": False, "end": False})
        self.assertEqual(long_input.found(None, long_input.ONE), {"middle": False})


class RunTests(unittest.TestCase):
    def test_one_passphrase_not_streamed_after_a_short_request(self):
        sent = []
        status, row = run(
            ["--passphrases", "1", "--lines", "8806"], "AMBER-FALCON-4817", sent
        )
        self.assertEqual(status, 0)
        (url0, evict), (url1, body) = sent
        self.assertTrue(url0.endswith("/v1/chat/completions"))
        self.assertTrue(evict["messages"][0]["content"].startswith("Say ok."))
        self.assertEqual(body["messages"], long_input.one_messages(8806))
        self.assertEqual(
            {k: body[k] for k in ("stream", "temperature", "max_tokens")},
            {"stream": False, "temperature": 0, "max_tokens": 512},
        )
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(
            row,
            {
                "passphrases": 1,
                "lines": 8806,
                "tokens": None,
                "prompt_tokens": 199652,
                "cached": 0,
                "completion_tokens": 9,
                "ttft": None,
                "elapsed": 1.0,
                "finish_reason": "stop",
                "content": "AMBER-FALCON-4817",
                "found": {"middle": True},
                "correct": True,
                "tensorfold": BLOCK_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )

    def test_three_passphrases_fitted_and_streamed(self):
        sent = []
        pieces = ["AMBER-FALCON-4817\n", "COBALT-HERON-2093\n", "SAFFRON-LYNX-7731"]
        status, row = run(["--passphrases", "3", "--tokens", "5000"], pieces, sent)
        self.assertEqual(status, 0)
        urls = [url.rsplit("/", 1)[1] for url, _ in sent]
        self.assertEqual(urls[-2:], ["completions", "completions"])
        self.assertTrue(all(u == "tokenize" for u in urls[:-2]))
        body = sent[-1][1]
        self.assertEqual(
            {k: body[k] for k in ("stream", "temperature", "max_tokens")},
            {"stream": True, "temperature": 0, "max_tokens": 256},
        )
        self.assertEqual(body["stream_options"], {"include_usage": True})
        self.assertEqual(body["messages"], long_input.three_messages(row["lines"]))
        self.assertEqual(row["tokens"], tokens(body["messages"]))
        self.assertLessEqual(row["tokens"], 5000)
        # monotonic: 0 at the request, 1 at the first (reasoning) piece, 2 at the end.
        self.assertEqual((row["ttft"], row["elapsed"]), (1.0, 2.0))
        self.assertEqual(row["content"], "".join(pieces))
        self.assertEqual(row["found"], {"start": True, "middle": True, "end": True})
        self.assertTrue(row["correct"])
        self.assertEqual(row["tensorfold"], BLOCK_KEPT)

    def test_a_missed_passphrase_exits_1(self):
        status, row = run(["--passphrases", "1", "--lines", "10"], "I do not know.")
        self.assertEqual(status, 1)
        self.assertFalse(row["correct"])

    def test_out_appends_the_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "long.jsonl")
            path.write_text('{"earlier": 1}\n', encoding="utf-8")
            _, row = run(
                ["--passphrases", "1", "--lines", "10", "--out", str(path)],
                "AMBER-FALCON-4817",
            )
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(rows, [{"earlier": 1}, row])

    def test_lines_or_tokens_is_required(self):
        for argv in (
            ["--passphrases", "1"],
            ["--passphrases", "1", "--lines", "10", "--tokens", "10"],
            ["--passphrases", "2", "--lines", "10"],
        ):
            with (
                self.subTest(argv=argv),
                self.assertRaises(SystemExit) as caught,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                long_input.main(argv)
            self.assertEqual(caught.exception.code, 2)


class ApiKeyTests(unittest.TestCase):
    def test_with_a_key_every_request_carries_it(self):
        auth = []
        with patch.dict(os.environ, {"TENSORFOLD_API_KEY": "k1"}):
            run(["--passphrases", "3", "--tokens", "5000"], ["x"], auth=auth)
        self.assertGreater(len(auth), 3)
        self.assertEqual(set(auth), {"Bearer k1"})

    def test_without_a_key_no_request_carries_one(self):
        auth = []
        with patch.dict(os.environ):
            os.environ.pop("TENSORFOLD_API_KEY", None)
            run(["--passphrases", "1", "--lines", "10"], "x", auth=auth)
        self.assertEqual(set(auth), {None})


if __name__ == "__main__":
    unittest.main()
