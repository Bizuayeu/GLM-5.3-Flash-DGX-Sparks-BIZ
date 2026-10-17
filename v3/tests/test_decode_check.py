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

# The native server's two blocks on the chunk that ends a streamed reply (10-17's probe).
SHA = "6cfce86a7e1b71d88b66e40ac527671dae0d9bf02bc9db06d46d9b03cf5c7a53"
TF_BLOCK = {"token_sha256": SHA, "token_sha": SHA[:12], "prefill_seconds": 0.3}
SPEC = {
    "rounds": 26,
    "accepted": 38,
    "drafted": 59,
    "acceptance_rate": 0.644,
    "tokens_per_round": 2.423,
}


def stream(spec=SPEC, ids=(16, 17), cached=0):
    """A streamed chat reply: one content chunk per id, then the end chunk with the engine's blocks, then
    usage (the server returns no token ids)."""
    chunks = [{"choices": [{"delta": {"content": f"{t}\n"}}]} for t in ids]
    end = {
        "choices": [{"delta": {}, "finish_reason": "length"}],
        "tensorfold": TF_BLOCK,
    }
    if spec is not None:
        end["speculative"] = spec
    usage = {
        "prompt_tokens": 2066,
        "completion_tokens": len(ids),
        "prompt_tokens_details": {"cached_tokens": cached},
    }
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

    A streamed request gets the next reply; any other request fails the test: the check sends nothing but
    its samples. `sent` collects every request body in order and `auth` every request's Authorization
    header (None when it has none).
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
        if not body.get("stream"):
            raise AssertionError(f"unexpected request {body}")
        return Reply(next(replies))

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
    """A server started with an API key (API_KEY_FILE in rank 0's file) refuses requests without
    it: the check sends the key when TENSORFOLD_API_KEY is set where it runs."""

    def test_with_a_key_every_request_carries_it(self):
        auth = []
        run([stream()] * 3, env={"TENSORFOLD_API_KEY": "k1"}, auth=auth)
        self.assertEqual(auth, ["Bearer k1"] * 3)

    def test_without_a_key_no_request_carries_one(self):
        auth = []
        with patch.dict(os.environ):
            os.environ.pop("TENSORFOLD_API_KEY", None)
            run([stream()] * 3, auth=auth)
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
                "tensorfold": TF_BLOCK,
                "speculative": SPEC,
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
    def test_speculative_reply_blocks_give_one_plus_accepted_over_rounds(self):
        lines = run([stream()] * 3)
        summary = lines[-1]["summary"]
        self.assertEqual(summary["acceptance_length"], round(1 + 114 / 78, 3))
        self.assertEqual(summary["acceptance_from"], "speculative reply blocks")

    def test_the_summary_holds_no_counter_snapshots(self):
        record = run([stream()] * 3)[-1]
        self.assertEqual(sorted(record), ["all", "at", "summary"])

    def test_the_t5_needle_reply_matches_its_tokens_per_round(self):
        block = {"rounds": 11, "accepted": 26, "drafted": 33, "tokens_per_round": 3.364}
        self.assertEqual(decode_check.acceptance([block])[0], 3.364)

    def test_no_drafts_is_null_with_a_reason(self):
        block = {"rounds": 511, "accepted": 0, "drafted": 0}
        length, extra = decode_check.acceptance([block] * 3)
        self.assertIsNone(length)
        self.assertIn("acceptance_null", extra)

    def test_replies_without_any_block_are_null_with_a_reason(self):
        length, extra = decode_check.acceptance([None] * 3)
        self.assertIsNone(length)
        self.assertEqual(extra["acceptance_null"], "a reply without rounds/accepted")

    def test_a_reply_without_its_speculative_block_is_null_with_a_reason(self):
        lines = run([stream(), stream(spec=None), stream()])
        self.assertIsNone(lines[-1]["summary"]["acceptance_length"])
        self.assertIn("acceptance_null", lines[-1]["summary"])


class TokenHashTests(unittest.TestCase):
    def test_the_row_carries_the_servers_token_hash(self):
        lines = run([stream(ids=[16, 17, 18])] * 3)
        self.assertEqual(lines[0]["token_sha256"], SHA[:16])
        self.assertEqual(lines[-1]["summary"]["distinct_token_sha256"], 1)

    def test_tokens_out_keeps_each_samples_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "a.json")
            run([stream(ids=[16, 17, 18])] * 3, tokens_out=path)
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(saved["kind"], "count")
        self.assertEqual(len(saved["samples"]), 3)
        self.assertEqual(saved["samples"][0]["text"], "16\n17\n18\n")
        self.assertNotIn("token_ids", saved["samples"][0])

    def test_decode_divergence_reads_tokens_out_to_the_first_differing_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [str(Path(tmp) / "a.json"), str(Path(tmp) / "b.json")]
            for path, ids in zip(paths, ([16, 17, 18], [16, 99, 18])):
                run([stream(ids=ids)] * 3, tokens_out=path)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                decode_divergence.main(paths)
        first = out.getvalue().splitlines()[0]
        self.assertEqual(first, "sample 0: first differing character 3/9")


class PromptCacheTests(unittest.TestCase):
    def test_the_samples_follow_each_other_and_resumed_rows_are_counted(self):
        sent = []
        lines = run([stream(), stream(cached=2048), stream(cached=2048)], sent)
        self.assertEqual(len(sent), 3)
        self.assertTrue(all(body["stream"] for body in sent))
        self.assertEqual([row["cached"] for row in lines[:3]], [0, 2048, 2048])
        self.assertEqual(lines[-1]["summary"]["resumed"], 2)

    def test_the_request_asks_for_no_token_ids(self):
        sent = []
        run([stream()] * 3, sent)
        self.assertNotIn("return_token_ids", sent[0])
        self.assertTrue(sent[0]["ignore_eos"])


class DefaultsTests(unittest.TestCase):
    def test_without_base_or_model_it_asks_serve_sh_s_rank_0(self):
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
