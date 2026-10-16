import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from glm53_tf import score_nll

SET = Path(__file__).resolve().parents[1] / "config/nll_set.json"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def small_set():
    """Two Japanese texts of 3 and 5 tokens, one code text of 2 (one character a token)."""
    texts = [("ja1", "ja", "abc"), ("ja2", "ja", "abcde"), ("code1", "code", "xy")]
    return {
        "version": 1,
        "max_tokens": 1800,
        "tokenizer": {"sha256": sha("tok")},
        "texts": [
            {"name": n, "domain": d, "text": t, "sha256": sha(t), "tokens": len(t)}
            for n, d, t in texts
        ],
    }


def tokenize(text):
    return [ord(c) for c in text]


def complete_at(logprob_of):
    """A /v1/completions reply in vLLM's prompt_logprobs shape; every prompt token of a
    text at ``logprob_of(token_ids)``."""

    def complete(token_ids, top_k):
        value = logprob_of(token_ids)
        rows = [{str(t): {"logprob": value, "rank": 1}} for t in token_ids[1:]]
        return {"choices": [{"prompt_logprobs": [None, *rows], "text": ""}]}

    return complete


class SetTests(unittest.TestCase):
    def test_the_published_set_matches_its_recorded_hashes(self):
        data = json.loads(SET.read_text(encoding="utf-8"))
        self.assertEqual(score_nll.problems(data, None), [])
        domains = [t["domain"] for t in data["texts"]]
        self.assertEqual(
            {d: domains.count(d) for d in domains},
            dict.fromkeys(score_nll.DOMAINS, 4),
        )
        self.assertTrue(all(t["tokens"] <= data["max_tokens"] for t in data["texts"]))

    def test_a_different_tokenizer_or_text_is_named(self):
        data = small_set()
        self.assertEqual(score_nll.problems(data, b"tok"), [])
        self.assertEqual(
            score_nll.problems(data, b"other"),
            ["tokenizer.json differs from the one the set was built with"],
        )
        changed = copy.deepcopy(data)
        changed["texts"][1]["text"] += " "
        self.assertEqual(
            score_nll.problems(changed, b"tok"),
            ["text ja2 differs from its recorded sha256"],
        )


class ScoreTests(unittest.TestCase):
    def test_each_domain_is_weighted_by_its_positions(self):
        # ja1: 2 positions at NLL 1, ja2: 4 at NLL 2 -> (2 + 8) / 6; code1: 1 position at 0.5
        summary, result = score_nll.score(
            small_set(),
            tokenize,
            complete_at(lambda ids: {3: -1.0, 5: -2.0, 2: -0.5}[len(ids)]),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(summary["ja"]["positions"], 6)
        self.assertEqual(summary["ja"]["mean_nll"], round(10 / 6, 4))
        self.assertEqual(summary["ja"]["texts"], {"ja1": 1.0, "ja2": 2.0})
        self.assertEqual(
            summary["code"], {"mean_nll": 0.5, "positions": 1, "texts": {"code1": 0.5}}
        )
        self.assertNotIn("en", summary)

    def test_a_failed_text_is_left_out_of_its_domain_and_fails_the_run(self):
        def complete(token_ids, top_k):
            if token_ids[0] == ord("x"):
                raise OSError("refused")
            return complete_at(lambda ids: -1.0)(token_ids, top_k)

        summary, result = score_nll.score(small_set(), tokenize, complete)
        self.assertFalse(result["passed"])
        self.assertNotIn("code", summary)
        self.assertEqual(summary["ja"]["positions"], 6)


class MainTests(unittest.TestCase):
    """main() sends each text's token ids, teacher-forced, to the server's model."""

    def test_the_server_scores_the_tokenizers_ids_at_temperature_zero(self):
        data = small_set()
        tokenizer = SimpleNamespace(
            encode=lambda text, add_special_tokens: SimpleNamespace(ids=tokenize(text))
        )
        tokenizers = SimpleNamespace(
            Tokenizer=SimpleNamespace(from_file=lambda path: tokenizer)
        )
        reply = complete_at(lambda ids: -1.0)
        posts = []

        def post(url, path, body=None, timeout=900.0):
            posts.append((url, path, body))
            if path == "/v1/models":
                return {"data": [{"id": "glm-tf"}]}
            return reply(body["prompt"], body["prompt_logprobs"])

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "set.json").write_text(json.dumps(data), encoding="utf-8")
            (tmp / "tok.json").write_text("tok", encoding="utf-8")
            argv = ["--url", "http://h:1", "--set", str(tmp / "set.json")]
            argv += ["--tokenizer", str(tmp / "tok.json"), "--out", str(tmp / "o.json")]
            with (
                patch.dict(sys.modules, {"tokenizers": tokenizers}),
                patch.object(score_nll, "post", post),
                redirect_stdout(io.StringIO()),
            ):
                code = score_nll.main(argv)
            out = json.loads((tmp / "o.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(out["model"], "glm-tf")
        self.assertEqual(posts[0][1], "/v1/models")
        _, path, body = posts[1]
        self.assertEqual(path, "/v1/completions")
        self.assertEqual(
            {k: v for k, v in body.items() if k != "prompt_logprobs"},
            {
                "model": "glm-tf",
                "prompt": tokenize("abc"),
                "max_tokens": 1,
                "temperature": 0,
                "seed": 42,
            },
        )


class ApiKeyTests(unittest.TestCase):
    """score-nll sends the server's API key when TENSORFOLD_API_KEY is set where it runs."""

    def seen(self, env):
        got = []

        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def urlopen(req, timeout=None):
            got.append(req.get_header("Authorization"))
            return Reply(b"{}")

        with (
            patch.dict("os.environ", env),
            patch.object(score_nll.urllib.request, "urlopen", urlopen),
        ):
            if "TENSORFOLD_API_KEY" not in env:
                os.environ.pop("TENSORFOLD_API_KEY", None)
            score_nll.post("http://127.0.0.1:8095", "/v1/completions", {"prompt": [1]})
        return got

    def test_with_a_key_the_request_carries_it(self):
        self.assertEqual(self.seen({"TENSORFOLD_API_KEY": "k2"}), ["Bearer k2"])

    def test_without_a_key_it_carries_none(self):
        self.assertEqual(self.seen({}), [None])


class SetCopyTests(unittest.TestCase):
    # The root's tests/test_lines.py checks this copy against 1.x's.
    def test_the_default_set_is_this_lines_copy(self):
        self.assertEqual(score_nll.SET, SET)


if __name__ == "__main__":
    unittest.main()
