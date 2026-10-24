import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glm53_tf import mojibake

JAPANESE = "日本の春は桜が咲き、夏は祭りでにぎわう。" * 30
KOREAN = "한국의 봄에는 벚꽃이 피고 여름에는 축제가 열립니다. " * 20
# The reply's block as the engine writes it (chat.zig): the effort the template heard and the sampling.
BLOCK = {"reasoning_effort": "high", "sampling": "greedy", "token_sha256": "ab" * 32}


def response(content, reasoning=None, finish="stop", tokens=900, block=BLOCK):
    message = {"role": "assistant", "content": content}
    if (
        reasoning is not None
    ):  # the engine leaves reasoning_content out when it is empty
        message["reasoning_content"] = reasoning
    return {
        "choices": [{"message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 40, "completion_tokens": tokens},
        "tensorfold": block,
    }


def clean(request):
    return response(JAPANESE if "日本" in request["messages"][0]["content"] else KOREAN)


class MojibakeTests(unittest.TestCase):
    def test_counts_each_invalid_kind_and_keeps_line_breaks_and_tabs(self):
        text = "a\N{REPLACEMENT CHARACTER}b\ud800c\x00d\x1be\n\r\tf"
        self.assertEqual(
            mojibake.count_invalid_text(text),
            {"replacement": 1, "lone_surrogate": 1, "control": 2},
        )
        self.assertEqual(
            mojibake.count_invalid_text("正常な文章"),
            {"replacement": 0, "lone_surrogate": 0, "control": 0},
        )

    def test_target_script_share_ignores_whitespace(self):
        self.assertGreater(mojibake.script_share(KOREAN, "ko"), 0.5)
        self.assertGreater(mojibake.script_share(JAPANESE, "ja"), 0.5)
        self.assertLess(
            mojibake.script_share("Spring brings cherry blossoms.", "ja"), 0.5
        )
        self.assertEqual(mojibake.script_share(" \n", "ko"), 0.0)

    def judge(self, language, result):
        return mojibake.judge(language, result)["verdict"]

    def test_long_target_language_without_invalid_characters_passes(self):
        self.assertEqual(self.judge("ja", response(JAPANESE)), "pass")
        self.assertEqual(
            self.judge("ko", response(KOREAN, "봄과 여름을 생각한다")), "pass"
        )

    def test_one_invalid_character_fails_in_content_or_reasoning_content(self):
        self.assertEqual(
            self.judge("ko", response(KOREAN + "\N{REPLACEMENT CHARACTER}")), "fail"
        )
        self.assertEqual(
            self.judge("ja", response(JAPANESE, "考え\N{REPLACEMENT CHARACTER}")),
            "fail",
        )
        # A short or cut answer that still carries a broken character is evidence.
        self.assertEqual(
            self.judge("ja", response("短い\N{REPLACEMENT CHARACTER}")), "fail"
        )
        self.assertEqual(
            self.judge("ja", response("", "考え\ud800", finish="length")), "fail"
        )

    def test_the_reasoning_is_read_under_either_name(self):
        reply = response(JAPANESE)
        reply["choices"][0]["message"]["reasoning"] = "考え\x00"
        self.assertEqual(self.judge("ja", reply), "fail")

    def test_errors_empty_short_or_wrong_language_never_pass(self):
        for result in (
            RuntimeError("HTTP 500"),
            response(None),
            response(""),
            response(JAPANESE[:399]),
            response("Spring brings cherry blossoms. " * 20),
        ):
            with self.subTest(result=repr(result)[:40]):
                self.assertEqual(self.judge("ja", result), "inconclusive")

    def test_an_answer_cut_at_max_tokens_is_inconclusive_and_marked(self):
        # Unlike 1.x: max_tokens counts the reasoning too, so the answer had no room to finish.
        row = mojibake.judge("ko", response(KOREAN, "생각", finish="length"))
        self.assertEqual(row["verdict"], "inconclusive")
        self.assertIs(row["truncated"], True)

    def test_the_row_keeps_the_lengths_tokens_effort_and_sampling(self):
        row = mojibake.judge("ja", response(JAPANESE, "季節を考える", tokens=1234))
        self.assertEqual(row["characters"], len(JAPANESE))
        self.assertEqual(row["reasoning_characters"], 6)
        self.assertEqual(row["completion_tokens"], 1234)
        self.assertEqual(row["reasoning_effort"], "high")
        self.assertEqual(row["sampling"], "greedy")
        self.assertEqual((row["content"], row["reasoning"]), (JAPANESE, "季節を考える"))
        bare = mojibake.judge("ja", {**response(JAPANESE), "tensorfold": None})
        self.assertIsNone(bare["reasoning_effort"])
        self.assertEqual(bare["verdict"], "pass")

    def test_malformed_response_is_inconclusive_and_run_never_raises(self):
        no_finish = {"choices": [{"message": {"content": JAPANESE}}]}
        for result in [{"choices": []}, no_finish]:
            record = mojibake.run(lambda request, result=result: result, repeats=1)
            self.assertEqual(
                [row["verdict"] for row in record["runs"]], ["inconclusive"] * 2
            )
            self.assertEqual(record["verdict"], "inconclusive")

    def test_run_repeats_each_language_at_temperature_zero_and_aggregates(self):
        requests = []

        def ask(request):
            requests.append(request)
            if "한국" in request["messages"][0]["content"] and len(requests) == 5:
                return response(KOREAN + "\N{REPLACEMENT CHARACTER}")
            return clean(request)

        record = mojibake.run(ask, repeats=3)
        self.assertEqual(len(requests), 6)
        self.assertTrue(all(r["temperature"] == 0 for r in requests))
        self.assertEqual(
            [row["language"] for row in record["runs"]], ["ja"] * 3 + ["ko"] * 3
        )
        self.assertEqual(record["verdict"], "fail")
        self.assertIs(record["passed"], False)
        self.assertEqual(mojibake.run(clean, repeats=1)["verdict"], "pass")

        def flaky(request):
            raise TimeoutError

        record = mojibake.run(flaky, repeats=1)
        self.assertEqual(record["verdict"], "inconclusive")
        self.assertIs(record["passed"], False)
        self.assertEqual(record["runs"][0]["error"], "TimeoutError")

    def test_requests_name_the_answer_limit_and_leave_the_effort_to_the_server(self):
        requests = []

        def ask(request):
            requests.append(request)
            return clean(request)

        mojibake.run(ask, repeats=1, max_tokens=1000)
        for request in requests:
            self.assertEqual(
                set(request), {"messages", "temperature", "max_tokens", "stream"}
            )
            self.assertEqual(request["max_tokens"], 1000)
            self.assertIs(request["stream"], False)
        requests.clear()
        mojibake.run(ask, repeats=1)
        self.assertEqual({r["max_tokens"] for r in requests}, {32768})


class SampledMojibakeTests(unittest.TestCase):
    SAMPLING = {"temperature": 1.0, "top_p": 0.95, "seed": 100}

    def test_each_run_draws_its_own_seed_and_the_record_names_the_settings(self):
        requests = []

        def ask(request):
            requests.append(request)
            return clean(request)

        record = mojibake.run(ask, repeats=2, sampling=self.SAMPLING)
        self.assertEqual(len(requests), 4)
        self.assertEqual({r["temperature"] for r in requests}, {1.0})
        self.assertEqual({r["top_p"] for r in requests}, {0.95})
        self.assertEqual([r["seed"] for r in requests], [100, 101, 102, 103])
        self.assertEqual([row["seed"] for row in record["runs"]], [100, 101, 102, 103])
        self.assertEqual(
            record["sampling"],
            {"temperature": 1.0, "top_p": 0.95, "seed": 100, "repeats": 2},
        )
        self.assertEqual(record["verdict"], "pass")

    def test_the_default_record_is_unchanged(self):
        record = mojibake.run(clean, repeats=1)
        self.assertEqual(list(record), ["runs", "verdict", "passed"])
        self.assertTrue(all("seed" not in row for row in record["runs"]))

    def test_sampling_outside_its_range_is_refused_before_any_request(self):
        def ask(request):
            raise AssertionError("no request expected")

        for bad in (
            {"temperature": 0, "top_p": 0.95, "seed": 1},
            {"temperature": 1.0, "top_p": 0, "seed": 1},
            {"temperature": 1.0, "top_p": 1.5, "seed": 1},
            {"temperature": 1.0, "top_p": 0.95},
        ):
            with self.subTest(sampling=bad):
                with self.assertRaises(ValueError):
                    mojibake.run(ask, sampling=bad)


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class CommandTests(unittest.TestCase):
    def main(self, argv, reply=clean, env=None):
        """main() against canned replies: (exit status, printed lines, the urlopen calls)."""
        calls = []

        def urlopen(req, timeout=None):
            body = json.loads(req.data)
            calls.append((req.full_url, req.get_header("Authorization"), body, timeout))
            return Reply(json.dumps(reply(body)).encode())

        out = io.StringIO()
        with (
            patch.object(mojibake.urllib.request, "urlopen", urlopen),
            patch.dict(mojibake.os.environ, env or {}, clear=False),
            contextlib.redirect_stdout(out),
        ):
            status = mojibake.main(argv)
        return status, [json.loads(line) for line in out.getvalue().splitlines()], calls

    def test_a_clean_run_exits_0_and_the_file_keeps_the_full_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "moji.json"
            status, lines, calls = self.main(["--out", str(out)])
            record = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(status, 0)
        self.assertEqual(len(calls), 6)
        url, auth, body, timeout = calls[0]
        self.assertEqual(url, "http://127.0.0.1:8095/v1/chat/completions")
        self.assertIsNone(auth)
        self.assertEqual(body["model"], "glm-tf")
        self.assertEqual(timeout, 3600)
        self.assertEqual(record["verdict"], "pass")
        self.assertEqual(record["model"], "glm-tf")
        self.assertEqual(record["max_tokens"], 32768)
        self.assertEqual(record["runs"][0]["content"], JAPANESE)
        # The terminal gets each row without its texts, then the summary.
        self.assertEqual(len(lines), 7)
        self.assertNotIn("content", lines[0])
        self.assertNotIn("reasoning", lines[0])
        self.assertEqual(lines[-1]["summary"]["verdict"], "pass")
        self.assertEqual(lines[-1]["summary"]["answers"], 6)

    def test_a_broken_character_exits_1_and_an_inconclusive_run_2(self):
        def broken(body):
            return (
                response(KOREAN + "\x00")
                if "한국" in body["messages"][0]["content"]
                else clean(body)
            )

        def short(body):
            return response("短い")

        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "moji.json")
            self.assertEqual(self.main(["--out", out, "--repeats", "1"], broken)[0], 1)
            self.assertEqual(self.main(["--out", out, "--repeats", "1"], short)[0], 2)

    def test_sampled_runs_need_all_three_settings_and_send_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "moji.json")
            status, lines, calls = self.main(
                [
                    "--out",
                    out,
                    "--temperature",
                    "1.0",
                    "--top-p",
                    "0.95",
                    "--seed",
                    "42",
                ]
            )
            self.assertEqual(status, 0)
            self.assertEqual([c[2]["seed"] for c in calls], [42, 43, 44, 45, 46, 47])
            self.assertEqual({c[2]["top_p"] for c in calls}, {0.95})
            self.assertEqual(
                lines[-1]["summary"]["sampling"],
                {"temperature": 1.0, "top_p": 0.95, "seed": 42, "repeats": 3},
            )
            for partial in (
                ["--temperature", "1.0"],
                ["--top-p", "0.95", "--seed", "1"],
            ):
                with self.subTest(partial=partial):
                    with (
                        self.assertRaises(SystemExit) as caught,
                        contextlib.redirect_stderr(io.StringIO()),
                    ):
                        self.main(["--out", out, *partial])
                    self.assertEqual(caught.exception.code, 2)

    def test_the_key_base_and_model_come_from_the_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "moji.json")
            env = {"TENSORFOLD_API_KEY": "k1"}
            with (
                patch.object(mojibake, "BASE", "http://10.0.0.1:9000"),
                patch.object(mojibake, "MODEL", "other"),
            ):
                _, _, calls = self.main(["--out", out, "--repeats", "1"], env=env)
        url, auth, body, _ = calls[0]
        self.assertEqual(url, "http://10.0.0.1:9000/v1/chat/completions")
        self.assertEqual(auth, "Bearer k1")
        self.assertEqual(body["model"], "other")


if __name__ == "__main__":
    unittest.main()
