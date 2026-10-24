"""Japanese and Korean answers checked for broken characters, as 1.x's `server mojibake` checks them.

A ModelOpt checkpoint whose gate and up scales disagree was reported to garble multibyte text (vLLM
#54150). Run on rank 0 against the loopback API: Japanese and Korean answers of 400 characters or more,
--repeats times each, at temperature 0, or sampled with --temperature, --top-p and --seed together (run
i of the run draws with seed + i). The answer (content) and the reasoning (reasoning_content) are
searched for U+FFFD, lone surrogates and control characters other than line breaks and tabs. One such
character fails the check. An answer that errs, is malformed, empty or short, is mostly outside the
target script or was cut at max_tokens is inconclusive, never a pass. The requests name no reasoning
effort, so the server's default reasons (serve.sh's high), and max_tokens counts the reasoning too (the
engine's message at start: serve.sh sets no thinking reserve). Each row keeps its finish reason, its
lengths, the reply's completion tokens and the effort and sampling of the reply's `tensorfold` block.
Exit 0 when every answer passes, 1 when one has a broken character, 2 otherwise. The full answers are in
--out; the terminal gets each row without its texts, then the summary.

    python -m glm53_tf mojibake --out ../records/<run>/mojibake.json
    python -m glm53_tf mojibake --temperature 1.0 --top-p 0.95 --seed 42 --out ../records/<run>/sampled.json

Environment: BASE (default http://127.0.0.1:8095), MODEL (default glm-tf), TENSORFOLD_API_KEY (sent as
the bearer token when set). The prompts, the counts and the verdicts are 1.x's v1/glm53_setup/mojibake.py,
except that an answer cut at max_tokens is inconclusive here: the reasoning shares the limit, so a cut
answer was not given room to finish. --max-tokens defaults to serve.sh's limit for a request that names
none (32,768); the timeout is long-input's for one request not streamed (3,600 s).
"""

import argparse
import json
import os
import time
import unicodedata
import urllib.request

BASE = os.environ.get("BASE", "http://127.0.0.1:8095")
MODEL = os.environ.get("MODEL", "glm-tf")
MAX_TOKENS = 32768  # serve.sh's --max-tokens
TIMEOUT = 3600  # long_input.whole's
MIN_CHARACTERS = 400  # The length the prompts ask for.
PROMPTS = {
    "ja": (
        "日本の四季それぞれについて、気候の特徴と代表的な行事を、"
        "400文字以上の日本語の文章で説明してください。箇条書きは使わないでください。"
    ),
    "ko": (
        "한국의 사계절 각각에 대해 기후의 특징과 대표적인 행사를 "
        "400자 이상의 한국어 문장으로 설명해 주세요. 글머리 기호는 사용하지 마세요."
    ),
}
SCRIPTS = {
    "ja": ((0x3040, 0x30FF), (0x4E00, 0x9FFF)),  # Kana and CJK ideographs
    "ko": ((0xAC00, 0xD7A3), (0x1100, 0x11FF), (0x3130, 0x318F)),  # Hangul
}
EXIT = {"pass": 0, "fail": 1, "inconclusive": 2}


def count_invalid_text(text):
    counts = {"replacement": 0, "lone_surrogate": 0, "control": 0}
    for character in text:
        code = ord(character)
        if character == "\N{REPLACEMENT CHARACTER}":
            counts["replacement"] += 1
        elif 0xD800 <= code <= 0xDFFF:
            counts["lone_surrogate"] += 1
        elif unicodedata.category(character) == "Cc" and character not in "\n\r\t":
            counts["control"] += 1
    return counts


def script_share(text, language):
    characters = [c for c in text if not c.isspace()]
    if not characters:
        return 0.0
    inside = sum(
        any(low <= ord(c) <= high for low, high in SCRIPTS[language])
        for c in characters
    )
    return inside / len(characters)


def judge(language, result):
    """One run's verdict: pass, fail, or inconclusive (never a silent pass)."""
    row = {"language": language}
    if isinstance(result, Exception):
        return {**row, "verdict": "inconclusive", "error": type(result).__name__}
    choice = result["choices"][0]
    message = choice["message"]
    content = message.get("content") or ""
    # reasoning_content and reasoning are one field under two names (decode_check.py)
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    block = result.get("tensorfold") or {}
    row.update(
        finish_reason=choice["finish_reason"],
        truncated=choice["finish_reason"] == "length",
        characters=len(content),
        reasoning_characters=len(reasoning),
        completion_tokens=(result.get("usage") or {}).get("completion_tokens"),
        reasoning_effort=block.get("reasoning_effort"),
        sampling=block.get("sampling"),
        script_share=round(script_share(content, language), 3),
        content_invalid=count_invalid_text(content),
        reasoning_invalid=count_invalid_text(reasoning),
    )
    if any(row["content_invalid"].values()) or any(row["reasoning_invalid"].values()):
        row["verdict"] = "fail"
    elif (
        row["truncated"] or len(content) < MIN_CHARACTERS or row["script_share"] <= 0.5
    ):
        row["verdict"] = "inconclusive"
    else:
        row["verdict"] = "pass"
    row["content"], row["reasoning"] = content, reasoning
    return row


def run(ask, repeats=3, sampling=None, max_tokens=MAX_TOKENS):
    """Ask each prompt repeats times at temperature 0; never raise on answers.

    ``sampling`` ({temperature, top_p, seed}) counts broken characters in
    sampled answers instead: run i draws with seed + i, so repeats are distinct
    draws, and the record names the settings.
    """
    if sampling is not None and not (
        sampling.get("temperature", 0) > 0
        and 0 < sampling.get("top_p", 0) <= 1
        and isinstance(sampling.get("seed"), int)
    ):
        raise ValueError("Sampling needs temperature > 0, 0 < top_p <= 1 and a seed")
    rows = []
    for language, prompt in PROMPTS.items():
        for _ in range(repeats):
            request = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if sampling is not None:
                request.update(
                    temperature=sampling["temperature"],
                    top_p=sampling["top_p"],
                    seed=sampling["seed"] + len(rows),
                )
            try:
                row = judge(language, ask(request))
            except Exception as error:  # noqa: BLE001 - a failed or malformed answer is recorded, not a pass
                row = judge(language, error)
            if sampling is not None:
                row["seed"] = request["seed"]
            rows.append(row)
    verdicts = {row["verdict"] for row in rows}
    verdict = (
        "fail"
        if "fail" in verdicts
        else "pass"
        if verdicts == {"pass"}
        else "inconclusive"
    )
    result = {"runs": rows, "verdict": verdict, "passed": verdict == "pass"}
    if sampling is not None:
        result["sampling"] = {**sampling, "repeats": repeats}
    return result


def ask(request):
    """One chat request to the engine, the reply parsed."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        json.dumps({"model": MODEL, **request}).encode(),
        headers,
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as reply:
        return json.loads(reply.read())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repeats", type=int, default=3, help="answers per language")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--seed", type=int, help="run i draws with seed + i")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--out", required=True, help="the JSON record, full answers")
    args = parser.parse_args(argv)
    given = [v is not None for v in (args.temperature, args.top_p, args.seed)]
    if any(given) and not all(given):
        parser.error("a sampled run needs --temperature, --top-p and --seed together")
    sampling = None
    if all(given):
        sampling = {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
        }
    try:
        result = run(ask, args.repeats, sampling, args.max_tokens)
    except ValueError as error:
        parser.error(str(error))
    record = {
        "model": MODEL,
        "max_tokens": args.max_tokens,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        **result,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    for row in result["runs"]:
        print(
            json.dumps(
                {k: v for k, v in row.items() if k not in ("content", "reasoning")},
                ensure_ascii=False,
            ),
            flush=True,
        )
    counts = {v: sum(r["verdict"] == v for r in result["runs"]) for v in EXIT}
    summary = {"verdict": result["verdict"], "answers": len(result["runs"]), **counts}
    if sampling is not None:
        summary["sampling"] = result["sampling"]
    print(json.dumps({"summary": summary, "out": args.out}, ensure_ascii=False))
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
