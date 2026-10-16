import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import decode_check, decode_divergence

# The stream's last chunk on TensorFold (a TP=3 run, 2026-10-03).
TF_BLOCK = {"rounds": 26, "accepted": 38, "drafted": 59, "tokens_per_round": 2.423}


def stream(block=None, ids=(16, 17)):
    """A streamed chat reply: one content chunk per id, then the end chunk and usage.

    vLLM puts each chunk's ids in its choice. TensorFold puts none there and, with
    `return_token_ids`, all of them in the end chunk's block (its cuda/server.py).
    """
    chunks = [
        {"choices": [{"delta": {"content": f"{t}\n"}, "token_ids": [t]}]} for t in ids
    ]
    end = {"choices": [{"delta": {}, "finish_reason": "length"}]}
    if block is not None:
        for c in chunks:
            del c["choices"][0]["token_ids"]
        end["tensorfold"] = dict(block, token_ids=list(ids))
    usage = {"prompt_tokens": 2066, "completion_tokens": len(ids)}
    chunks += [end, {"choices": [], "usage": usage}]
    return [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [b"data: [DONE]\n"]


class Reply(list):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


def run(replies, sent=None, tokens_out=None, env=None, auth=None):
    """Run main() against canned replies; return its printed JSON lines.

    A streamed request gets the next reply, any other POST a short non-streamed one, and
    a GET fails the test: the check reads nothing but replies. `sent` collects every
    request body in order and `auth` every request's Authorization header (None when it
    has none).
    """
    replies = iter(replies)
    sent = [] if sent is None else sent
    auth = [] if auth is None else auth

    def urlopen(req, timeout=None):
        auth.append(req.get_header("Authorization"))
        if req.data is None:
            raise AssertionError(f"unexpected GET {req.full_url}")
        body = json.loads(req.data)
        sent.append(body)
        if body.get("stream"):
            return Reply(next(replies))
        return Reply(
            [json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()]
        )

    out = io.StringIO()
    clock = iter(range(1000))
    env = dict(env or {}, **({"TOKENS_OUT": tokens_out} if tokens_out else {}))
    with (
        patch.object(decode_check.urllib.request, "urlopen", urlopen),
        patch.object(decode_check.time, "monotonic", lambda: next(clock)),
        patch.object(decode_check, "SAMPLES", 3),
        patch.dict(os.environ, env),
        contextlib.redirect_stdout(out),
    ):
        decode_check.main([])
    return [json.loads(line) for line in out.getvalue().splitlines()]


class ApiKeyTests(unittest.TestCase):
    """A server started with an API key (TENSORFOLD_API_KEY in rank 0's file) refuses
    requests without it: the check sends the key when the variable is set where it runs."""

    def test_with_a_key_every_request_carries_it(self):
        auth = []
        run(
            [stream(TF_BLOCK)] * 3,
            env={"TENSORFOLD_API_KEY": "k1"},
            auth=auth,
        )
        self.assertGreater(len(auth), 3)
        self.assertEqual(set(auth), {"Bearer k1"})

    def test_without_a_key_no_request_carries_one(self):
        auth = []
        with patch.dict(os.environ):
            os.environ.pop("TENSORFOLD_API_KEY", None)
            run([stream(TF_BLOCK)] * 3, auth=auth)
        self.assertEqual(set(auth), {None})


class TextTests(unittest.TestCase):
    def test_a_chunk_with_reasoning_and_content_keeps_both(self):
        """A draft round's chunk can end the reasoning and start the content; the text keeps both, in order."""
        chunks = [
            {"choices": [{"delta": {"reasoning_content": "go to 200"}}]},
            {"choices": [{"delta": {"reasoning_content": ".", "content": "1\n"}}]},
            {"choices": [{"delta": {"content": "2\n"}}]},
            {
                "choices": [{"delta": {}, "finish_reason": "length"}],
                "tensorfold": dict(TF_BLOCK, token_ids=[7, 8, 9]),
            },
            {"choices": [], "usage": {"prompt_tokens": 2066, "completion_tokens": 3}},
        ]
        reply = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks] + [
            b"data: [DONE]\n"
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tokens.json")
            lines = run([reply] * 3, tokens_out=path)
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
        want = "go to 200.1\n2\n"
        self.assertEqual(saved["samples"][0]["text"], want)
        self.assertEqual(
            lines[0]["completion_sha256"],
            hashlib.sha256(want.encode()).hexdigest()[:16],
        )


class AcceptanceLengthTests(unittest.TestCase):
    def test_tensorfold_reply_blocks_give_one_plus_accepted_over_rounds(self):
        lines = run([stream(TF_BLOCK)] * 3)
        summary = lines[-1]["summary"]
        self.assertEqual(summary["acceptance_length"], round(1 + 114 / 78, 3))
        self.assertEqual(summary["acceptance_from"], "tensorfold reply blocks")

    def test_the_summary_holds_no_counter_snapshots(self):
        record = run([stream(TF_BLOCK)] * 3)[-1]
        self.assertEqual(sorted(record), ["all", "at", "summary"])

    def test_the_t5_needle_reply_matches_its_tokens_per_round(self):
        block = {"rounds": 11, "accepted": 26, "drafted": 33, "tokens_per_round": 3.364}
        self.assertEqual(decode_check.acceptance([block])[0], 3.364)

    def test_tensorfold_without_drafts_is_null_with_a_reason(self):
        block = {"rounds": 511, "accepted": 0, "drafted": 0, "drafts": False}
        length, extra = decode_check.acceptance([block] * 3)
        self.assertIsNone(length)
        self.assertIn("acceptance_null", extra)

    def test_replies_without_any_block_are_null_with_a_reason(self):
        length, extra = decode_check.acceptance([None] * 3)
        self.assertIsNone(length)
        self.assertEqual(extra["acceptance_null"], "a reply without rounds/accepted")

    def test_a_sample_without_its_block_is_null_with_a_reason(self):
        length, extra = decode_check.acceptance([TF_BLOCK, None, TF_BLOCK])
        self.assertIsNone(length)
        self.assertIn("acceptance_null", extra)


class TensorFoldTokenIdsTests(unittest.TestCase):
    def test_the_ids_come_from_the_block_when_the_choices_carry_none(self):
        ids = [16, 17, 18]
        row = run([stream(TF_BLOCK, ids)] * 3)[0]
        self.assertEqual(row["n_token_ids"], 3)
        digest = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:16]
        self.assertEqual(row["token_ids_sha256"], digest)

    def test_tokens_out_keeps_each_samples_text_and_token_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "a.json")
            run([stream(TF_BLOCK, [16, 17, 18])] * 3, tokens_out=path)
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(saved["kind"], "count")
        self.assertEqual(len(saved["samples"]), 3)
        self.assertEqual(saved["samples"][0]["token_ids"], [16, 17, 18])
        self.assertEqual(saved["samples"][0]["text"], "16\n17\n18\n")

    def test_decode_divergence_reads_tokens_out_to_the_first_differing_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [str(Path(tmp) / "a.json"), str(Path(tmp) / "b.json")]
            for path, ids in zip(paths, ([16, 17, 18], [16, 99, 18])):
                run([stream(TF_BLOCK, ids)] * 3, tokens_out=path)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                decode_divergence.main(paths)
        first = out.getvalue().splitlines()[0]
        self.assertIn("first differing token 1/3 (ids [17, 18] vs [99, 18])", first)


class TensorFoldPrefixCacheTests(unittest.TestCase):
    def test_each_sample_follows_enough_distinct_requests_to_drop_kept_prompts(self):
        sent, n = [], 3
        with patch.object(decode_check, "TF_GLM_CACHE_ENTRIES", n):
            lines = run([stream(TF_BLOCK)] * 3, sent)
        summary = lines[-1]["summary"]
        streamed = [i for i, body in enumerate(sent) if body.get("stream")]
        self.assertEqual(streamed, [n, 2 * n + 1, 3 * n + 2])
        fillers = [b["messages"][0]["content"] for b in sent if not b.get("stream")]
        self.assertEqual(len(set(fillers)), 3 * n)
        self.assertEqual(summary["evicted_before_each"], n)


class DefaultsTests(unittest.TestCase):
    def test_without_base_or_model_it_asks_the_2x_engine(self):
        env = {k: v for k, v in os.environ.items() if k not in ("BASE", "MODEL")}
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from glm53_tf import decode_check as d; print(d.BASE, d.MODEL)",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["http://127.0.0.1:8095", "glm-tf"])

    def test_it_takes_no_arguments(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            decode_check.main(["--samples", "3"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
