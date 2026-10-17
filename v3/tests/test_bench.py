import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import bench

# The native server's two blocks (10-17's probe): `tensorfold` with the prompt pass and the ids'
# hash, `speculative` with the draft counts. Prefill keeps the times, decode adds the rounds and the
# hash, edit the draft counts and the hash.
SHA = "6cfce86a7e1b71d88b66e40ac527671dae0d9bf02bc9db06d46d9b03cf5c7a53"
BLOCK = {
    "prefill_seconds": 30.25,
    "time_to_first_token": 30.3,
    "token_sha256": SHA,
    "token_sha": SHA[:12],
    "engine": "lanes",
    "drafts": True,
}
SPECULATIVE = {
    "rounds": 1,
    "drafted": 5,
    "accepted": 3,
    "acceptance_rate": 0.6,
    "tokens_per_round": 3.5,
}
BLOCK_KEPT = {"prefill_seconds": 30.25, "time_to_first_token": 30.3}
DECODE_KEPT = dict(BLOCK_KEPT, rounds=1, tokens_per_round=3.5, token_sha256=SHA)
EDIT_KEPT = {"rounds": 1, "drafted": 5, "accepted": 3, "token_sha256": SHA}


def prefill_reply(prompt_tokens=38960, cached=0):
    reply = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "length"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 1,
            "prompt_tokens_details": {"cached_tokens": cached},
        },
        "tensorfold": BLOCK,
        "speculative": SPECULATIVE,
    }
    return [json.dumps(reply).encode()]


def decode_reply(n=4, finish="length"):
    """A streamed reply: one reasoning chunk, then content, the end chunk and usage."""
    chunks = [{"choices": [{"delta": {"reasoning_content": "go"}}]}]
    chunks += [{"choices": [{"delta": {"content": f"{i}\n"}}]} for i in range(n - 1)]
    chunks += [
        {
            "choices": [{"delta": {}, "finish_reason": finish}],
            "tensorfold": BLOCK,
            "speculative": SPECULATIVE,
        },
        {"choices": [], "usage": {"prompt_tokens": 17, "completion_tokens": n}},
    ]
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(argv, sent=None, auth=None, edit_finish="stop"):
    """Run main() against canned replies; return its printed JSON lines.

    Every monotonic reading is one second after the previous; `sent` collects the
    request bodies and `auth` their Authorization headers. The decode reply runs to
    its limit; an edit reply ends with `edit_finish` (on its own unless told).
    """
    sent = [] if sent is None else sent
    auth = [] if auth is None else auth

    def urlopen(req, timeout=None):
        auth.append(req.get_header("Authorization"))
        body = json.loads(req.data)
        sent.append(body)
        if body == bench.edit_body():
            return Reply(decode_reply(finish=edit_finish))
        return Reply(decode_reply() if body.get("stream") else prefill_reply())

    out = io.StringIO()
    clock = iter(range(1000))
    with (
        patch.object(bench.urllib.request, "urlopen", urlopen),
        patch.object(bench.time, "monotonic", lambda: next(clock)),
        patch.object(bench.time, "time", lambda: 1759700000.04),
        contextlib.redirect_stdout(out),
    ):
        bench.main(argv)
    return [json.loads(line) for line in out.getvalue().splitlines()]


class PromptTests(unittest.TestCase):
    def test_the_prefill_prompt_is_the_documented_one(self):
        body = bench.prefill_body("N")
        text = body["messages"][0]["content"]
        lines = text.split("\n")
        self.assertEqual(bench.LINES, 3200)
        self.assertEqual(lines[0], "nonce N")
        self.assertEqual(lines[1], "measurement line 0 of the fixed prefill prompt.")
        self.assertEqual(
            lines[3200], "measurement line 3199 of the fixed prefill prompt."
        )
        self.assertEqual(lines[-1], "Reply ok.")
        self.assertEqual(len(lines), 3202)
        self.assertEqual(body["messages"][0]["role"], "user")
        self.assertEqual(
            {k: body[k] for k in ("model", "max_tokens", "temperature")},
            {"model": bench.MODEL, "max_tokens": 1, "temperature": 0},
        )
        self.assertEqual(
            body["chat_template_kwargs"],
            {"reasoning_effort": "low", "clear_thinking": True},
        )
        self.assertNotIn("stream", body)

    def test_the_line_count_can_be_changed(self):
        text = bench.prefill_body("N", 250)["messages"][0]["content"]
        self.assertEqual(len(text.split("\n")), 252)

    def test_every_prefill_has_a_fresh_nonce(self):
        sent = []
        run(["--kinds", "prefill", "--runs", "2"], sent=sent)
        first = [b["messages"][0]["content"].split("\n")[0] for b in sent]
        self.assertEqual(len(set(first)), 3)  # the warm-up's and the two counted
        self.assertTrue(all(line.startswith("nonce ") for line in first))

    def test_the_decode_prompt_is_the_documented_one(self):
        body = bench.decode_body()
        self.assertEqual(
            body["messages"],
            [
                {
                    "role": "user",
                    "content": "Write the numbers from 1 to 1000, "
                    "one per line, and nothing else.",
                }
            ],
        )
        self.assertEqual(
            {k: body[k] for k in ("max_tokens", "temperature", "stream")},
            {"max_tokens": 512, "temperature": 0, "stream": True},
        )
        self.assertEqual(body["stream_options"], {"include_usage": True})
        self.assertEqual(
            body["chat_template_kwargs"],
            {"reasoning_effort": "low", "clear_thinking": True},
        )

    def test_the_decode_reply_ends_at_the_limit_not_past_the_models_end(self):
        # The count runs past 512 tokens, so the limit ends it; ignore_eos would rate
        # what the model makes up after it stops by itself.
        self.assertNotIn("ignore_eos", bench.decode_body())

    def test_the_edit_prompt_is_the_same_every_time(self):
        body = bench.edit_body()
        self.assertEqual(body, bench.edit_body())
        self.assertNotIn("nonce", json.dumps(body))
        (message,) = body["messages"]
        self.assertEqual(message["role"], "user")
        self.assertIn("```python\n" + bench.PASSAGE + "```", message["content"])
        self.assertEqual(
            {k: body[k] for k in ("max_tokens", "temperature", "stream")},
            {"max_tokens": bench.EDIT_TOKENS, "temperature": 0, "stream": True},
        )
        # the reply ends on its own: a cut reply would not be the edit it claims
        self.assertNotIn("ignore_eos", body)
        self.assertEqual(body["stream_options"], {"include_usage": True})
        self.assertEqual(
            body["chat_template_kwargs"],
            {"reasoning_effort": "low", "clear_thinking": True},
        )

    def test_each_named_edit_has_one_target_in_the_passage(self):
        # a few small edits: the rest of the reply is the passage, copied
        self.assertEqual(len(bench.EDITS), 3)
        for old, new in bench.EDITS:
            self.assertEqual(bench.PASSAGE.count(old), 1, old)
            self.assertNotIn(new, bench.PASSAGE)
            self.assertIn(f"`{old}`", bench.edit_body()["messages"][0]["content"])
            self.assertIn(f"`{new}`", bench.edit_body()["messages"][0]["content"])

    def test_the_passage_is_a_fixed_python_module_of_some_length(self):
        compile(bench.PASSAGE, "passage", "exec")
        # about 1.5-2k tokens of code (code runs 3-4 characters a token)
        self.assertTrue(5000 <= len(bench.PASSAGE) <= 8000, len(bench.PASSAGE))
        self.assertTrue(bench.PASSAGE.endswith("\n"))


class RowTests(unittest.TestCase):
    def test_a_prefill_row(self):
        (row, summary) = run(["--kinds", "prefill", "--runs", "1"])
        self.assertEqual(
            row,
            {
                "kind": "prefill",
                "prompt_tokens": 38960,
                "cached": 0,
                "seconds": 1.0,
                "tok_per_s": 38960.0,
                "tensorfold": BLOCK_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )

    def test_a_decode_row_times_from_the_first_streamed_token(self):
        # monotonic: 0 at the request, 1 at the first (reasoning) piece, 2 at the end.
        (row, summary) = run(["--kinds", "decode", "--runs", "1"])
        self.assertEqual(
            row,
            {
                "kind": "decode",
                "completion_tokens": 4,
                "finish_reason": "length",
                "ttft": 1.0,
                "seconds_after_first": 1.0,
                "tok_per_s": 3.0,
                "tensorfold": DECODE_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )

    def test_an_edit_row_times_from_the_first_streamed_token(self):
        sent = []
        (row, summary) = run(["--kinds", "edit", "--runs", "1"], sent=sent)
        self.assertEqual(sent, [bench.edit_body()])
        self.assertEqual(
            row,
            {
                "kind": "edit",
                "prompt_tokens": 17,
                "cached": 0,
                "completion_tokens": 4,
                "finish_reason": "stop",
                "ttft": 1.0,
                "seconds_after_first": 1.0,
                "tok_per_s": 3.0,
                "tensorfold": EDIT_KEPT,
                "start_epoch": 1759700000.0,
                "end_epoch": 1759700000.0,
            },
        )
        self.assertEqual(summary["summary"], {"edit": 3.0})
        self.assertNotIn("cut", summary)

    def test_an_edit_reply_cut_at_its_limit_is_left_out_of_the_median(self):
        lines = run(["--kinds", "decode,edit", "--runs", "2"], edit_finish="length")
        summary = lines[-1]
        self.assertEqual(summary["summary"], {"decode": 3.0})
        self.assertEqual(summary["all"]["edit"], [3.0, 3.0])
        self.assertEqual(summary["cut"], {"edit": 2})

    def test_a_reply_without_a_block_records_an_empty_one(self):
        self.assertEqual(bench.kept(None), {})
        self.assertEqual(bench.kept({"rounds": 3}), {})
        self.assertEqual(bench.kept(None, bench.EDIT_KEPT), {})


class RunTests(unittest.TestCase):
    def test_kinds_in_order_runs_each_and_the_summary_takes_medians(self):
        lines = run(["--runs", "3"])
        self.assertEqual(
            [r["kind"] for r in lines[:-1]], ["prefill"] * 3 + ["decode"] * 3
        )
        summary = lines[-1]
        self.assertEqual(
            summary["summary"], {"prefill": 38960.0, "decode": 3.0}, summary
        )
        self.assertEqual(summary["all"]["prefill"], [38960.0] * 3)
        self.assertIn("at", summary)

    def test_runs_default_to_three(self):
        lines = run(["--kinds", "decode"])
        self.assertEqual(len(lines), 4)

    def test_out_appends_one_row_per_request(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "bench.jsonl")
            path.write_text('{"earlier": 1}\n', encoding="utf-8")
            lines = run(
                ["--kinds", "prefill,decode", "--runs", "1", "--out", str(path)]
            )
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(rows, [{"earlier": 1}] + lines[:-1])

    def test_lines_reach_the_prefill_and_leave_the_other_kinds(self):
        sent = []
        run(["--kinds", "prefill,decode,edit", "--runs", "1", "--lines", "250"], sent)
        warm, prefill, decode, edit = sent
        for body in (warm, prefill):
            self.assertEqual(len(body["messages"][0]["content"].split("\n")), 252)
        self.assertEqual((decode, edit), (bench.decode_body(), bench.edit_body()))

    def test_a_warm_up_prefill_runs_first_and_is_not_counted(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "bench.jsonl")
            lines = run(
                ["--kinds", "prefill,decode", "--runs", "2", "--out", str(path)], sent
            )
            rows = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(sent), 5)
        self.assertEqual(sent[0], {**sent[1], "messages": sent[0]["messages"]})
        self.assertEqual(len(sent[0]["messages"][0]["content"].split("\n")), 3202)
        self.assertEqual(
            [r["kind"] for r in lines[:-1]], ["prefill"] * 2 + ["decode"] * 2
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(lines[-1]["warmup"], [38960.0])
        self.assertEqual(lines[-1]["all"]["prefill"], [38960.0] * 2)

    def test_warmup_zero_runs_none_and_other_kinds_never_warm_up(self):
        sent = []
        lines = run(["--kinds", "prefill", "--runs", "1", "--warmup", "0"], sent)
        self.assertEqual(len(sent), 1)
        self.assertNotIn("warmup", lines[-1])
        sent = []
        lines = run(["--kinds", "decode", "--runs", "1"], sent)
        self.assertEqual(sent, [bench.decode_body()])
        self.assertNotIn("warmup", lines[-1])

    def test_an_unknown_kind_is_a_usage_error(self):
        with (
            self.assertRaises(SystemExit) as caught,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            bench.main(["--kinds", "prefill,nope"])
        self.assertEqual(caught.exception.code, 2)


class ApiKeyTests(unittest.TestCase):
    def test_with_a_key_every_request_carries_it(self):
        auth = []
        with patch.dict(os.environ, {"TENSORFOLD_API_KEY": "k1"}):
            run(["--runs", "1"], auth=auth)
        # the warm-up, the prefill, the decode
        self.assertEqual(auth, ["Bearer k1"] * 3)

    def test_without_a_key_no_request_carries_one(self):
        auth = []
        with patch.dict(os.environ):
            os.environ.pop("TENSORFOLD_API_KEY", None)
            run(["--runs", "1"], auth=auth)
        self.assertEqual(auth, [None] * 3)


if __name__ == "__main__":
    unittest.main()
