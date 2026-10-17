"""Prefill and decode speed, as docs/benchmarks.md ("Prefill and decode speed") describes.

Run on rank 0 against the loopback API, one request at a time, temperature 0, effort low.
prefill: one user message, a line `nonce <a fresh UUID>`, --lines fixed lines and `Reply ok.`,
  max_tokens 1; the default 3,200 lines give 38,960 tokens with the chat template. The rate is the
  prompt tokens over the request's wall time at the client. The engine has no endpoint that drops its
  kept prompts, so the fresh nonce keeps any of them from matching; each row's `cached` shows it.
  --warmup requests of the same length (default 1) run first and are not counted; their rates are the
  summary's "warmup".
decode: `Write the numbers from 1 to 1000, one per line, and nothing else.`, streamed, up to 512 tokens.
  The rate is the completion tokens after the first over the time after the first streamed token. The
  reply counts until the limit cuts it (`finish_reason` `length`, the count in the 200s), so every token
  rated is the counting itself, and at TP=2 the pinned and the published AXL weights give the same tokens;
  a row with another `finish_reason` stopped early and does not compare. Before 2.5.0 the request was
  `Count upward from one, one number per line.` with ignore_eos: the model stops by itself after about
  100 tokens, and the rest of the 512 was a conversation the model made up past its end, different per
  weights and TP. The row adds `finish_reason` and the reply's rounds, tokens_per_round and token_sha256.
edit (only when asked for): a fixed Python module of about 6,000 characters and three named one-line
  edits, `Return the whole module with only these edits, in one code block:`, streamed, temperature 0,
  up to 4,096 tokens and ending on its own (a `finish_reason` of `length` means the reply was cut).
  Rated as decode is; most of the reply copies the prompt, the load copy drafts are for. Its row adds
  `prompt_tokens`, `cached`, `finish_reason` and the reply's rounds, drafted, accepted and token_sha256
  (the token ids' hash: the same every run at temperature 0).
The prefill and decode rows also carry the reply's prefill_seconds and time_to_first_token (the reply's
`tensorfold` and `speculative` blocks, kept under `tensorfold`; a prompt's heat waits are in rank 0's
log), and every row the request's start and end epochs. One JSON line per request, then a summary with each
kind's median; an edit reply cut at its limit is left out of the median and counted under "cut".

    python -m glm53_tf bench --kinds prefill --runs 1 --lines 250    (a short warm-up, about 3,000 tokens)
    python -m glm53_tf bench --out ../records/<run>/bench.jsonl

Environment: BASE (default http://127.0.0.1:8095), MODEL (default glm-tf), TENSORFOLD_API_KEY (sent as
the bearer token when set). The prompts and requests are those of the scripts that took the release's
figures, copied, so the same measurement reads the same.
"""

import argparse
import json
import os
import statistics
import time
import urllib.request
import uuid

BASE = os.environ.get("BASE", "http://127.0.0.1:8095")
MODEL = os.environ.get("MODEL", "glm-tf")
LINES = 3200
KINDS = ("prefill", "decode")
OPTIONAL = ("edit",)  # run only when --kinds names them
TEMPLATE = {"reasoning_effort": "low", "clear_thinking": True}
KEPT = ("prefill_seconds", "time_to_first_token")
DECODE_KEPT = KEPT + ("rounds", "tokens_per_round", "token_sha256")
DECODE_PROMPT = "Write the numbers from 1 to 1000, one per line, and nothing else."
DECODE_TOKENS = 512  # the count reaches the 200s: the limit ends the reply
EDIT_KEPT = ("rounds", "drafted", "accepted", "token_sha256")
EDIT_TOKENS = 4096  # the passage is about 2,000 tokens; the rest is room to end
PASSAGE = r'''"""A small ledger: accounts, postings read from text lines, balances and reports."""

import csv
import datetime as dt
import io
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal

MAX_RETRIES = 3
CURRENCIES = ("EUR", "JPY", "USD")
DATE_FORMAT = "%Y-%m-%d"


class LedgerError(ValueError):
    """A line or a request the ledger cannot take."""


@dataclass(frozen=True)
class Posting:
    day: dt.date
    account: str
    amount: Decimal
    currency: str
    memo: str = ""


@dataclass
class Account:
    name: str
    currency: str
    opened: dt.date
    postings: list[Posting] = field(default_factory=list)

    def balance(self, until: dt.date | None = None) -> Decimal:
        total = Decimal(0)
        for p in self.postings:
            if until is None or p.day <= until:
                total += p.amount
        return total

    def last_day(self) -> dt.date | None:
        return max((p.day for p in self.postings), default=None)


def parse_amount(text: str) -> Decimal:
    """'1,234.50' or '-12' as a Decimal with two places."""
    cleaned = text.replace(",", "").strip()
    if not cleaned:
        raise LedgerError("empty amount")
    try:
        value = Decimal(cleaned)
    except ArithmeticError as exc:
        raise LedgerError(f"bad amount {text!r}") from exc
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def parse_line(line: str) -> Posting:
    """A line 'date;account;amount;currency;memo' as a posting."""
    parts = [p.strip() for p in line.split(";")]
    if len(parts) < 4:
        raise LedgerError(f"expected at least 4 fields, got {len(parts)}")
    day = dt.datetime.strptime(parts[0], DATE_FORMAT).date()
    currency = parts[3].upper()
    if currency not in CURRENCIES:
        raise LedgerError(f"currency {currency} is not one of {', '.join(CURRENCIES)}")
    memo = parts[4] if len(parts) > 4 else ""
    return Posting(day, parts[1], parse_amount(parts[2]), currency, memo)


class Ledger:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}

    def open(self, name: str, currency: str, opened: dt.date) -> Account:
        if name in self.accounts:
            raise LedgerError(f"account {name} exists")
        if currency not in CURRENCIES:
            raise LedgerError(f"currency {currency} is not supported")
        account = Account(name, currency, opened)
        self.accounts[name] = account
        return account

    def post(self, posting: Posting) -> None:
        account = self.accounts.get(posting.account)
        if account is None:
            raise LedgerError("unknown account")
        if posting.currency != account.currency:
            raise LedgerError(
                f"{posting.account} keeps {account.currency}, not {posting.currency}"
            )
        if posting.day < account.opened:
            raise LedgerError(f"{posting.account} opened on {account.opened}")
        account.postings.append(posting)

    def load(self, text: str) -> int:
        """Post every non-blank, non-comment line; return how many were posted."""
        count = 0
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                self.post(parse_line(line))
            except LedgerError as exc:
                raise LedgerError(f"line {number}: {exc}") from exc
            count += 1
        return count

    def total(self, currency: str, until: dt.date | None = None) -> Decimal:
        total = Decimal(0)
        for account in self.accounts.values():
            if account.currency == currency:
                total += account.balance(until)
        return total

    def monthly(self, name: str) -> dict[str, Decimal]:
        """Net change of one account by calendar month, oldest first."""
        months: dict[str, Decimal] = {}
        for p in sorted(self.accounts[name].postings, key=lambda p: p.day):
            key = p.day.strftime("%Y-%m")
            months[key] = months.get(key, Decimal(0)) + p.amount
        return months

    def report(self) -> str:
        """Each account's balance as CSV rows, by name."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["account", "currency", "balance", "last posting"])
        for name in sorted(self.accounts):
            account = self.accounts[name]
            last = account.last_day()
            writer.writerow(
                [name, account.currency, f"{account.balance():.2f}", last or "-"]
            )
        return out.getvalue()


def average_posting(ledger: Ledger, name: str) -> float:
    postings = ledger.accounts[name].postings
    if not postings:
        return 0.0
    total = sum(float(p.amount) for p in postings)
    return round(total / len(postings), 2)


def with_retries(fetch, *args, delay: float = 0.5):
    """Call fetch(*args), retrying on OSError up to MAX_RETRIES times."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return fetch(*args)
        except OSError:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(delay * (2**attempt))
    return None


def convert(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def largest_postings(ledger: Ledger, count: int = 5) -> list[Posting]:
    every = [p for a in ledger.accounts.values() for p in a.postings]
    every.sort(key=lambda p: abs(p.amount), reverse=True)
    return every[:count]


def dormant(ledger: Ledger, today: dt.date, days: int = 90) -> list[str]:
    """Accounts without a posting in the last ``days`` days."""
    names = []
    for name, account in sorted(ledger.accounts.items()):
        last = account.last_day()
        if last is None or (today - last).days > days:
            names.append(name)
    return names
'''
EDITS = (
    ("MAX_RETRIES = 3", "MAX_RETRIES = 5"),
    ('"unknown account"', 'f"unknown account {posting.account}"'),
    (
        "return round(total / len(postings), 2)",
        "return round(total / len(postings), 4)",
    ),
)


def auth():
    """The server's API key, when TENSORFOLD_API_KEY is set where the bench runs."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **auth()},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def prefill_body(nonce, lines=LINES):
    text = "".join(
        f"measurement line {i} of the fixed prefill prompt.\n" for i in range(lines)
    )
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": f"nonce {nonce}\n{text}Reply ok."}],
        "max_tokens": 1,
        "temperature": 0,
        "chat_template_kwargs": TEMPLATE,
    }


def decode_body():
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": DECODE_PROMPT}],
        "max_tokens": DECODE_TOKENS,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": TEMPLATE,
    }


def edit_body():
    edits = "".join(f"- replace `{old}` with `{new}`\n" for old, new in EDITS)
    return {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"```python\n{PASSAGE}```\n\nReturn the whole module with "
                f"only these edits, in one code block:\n{edits}",
            }
        ],
        "max_tokens": EDIT_TOKENS,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": TEMPLATE,
    }


def engine_fields(reply):
    """A reply's `tensorfold` and `speculative` blocks as one (the server sends the draft counts apart)."""
    return {**(reply.get("tensorfold") or {}), **(reply.get("speculative") or {})}


def kept(block, fields=KEPT):
    """The fields of the reply's engine blocks a row keeps."""
    return {k: v for k, v in (block or {}).items() if k in fields}


def prefill(args):
    start_epoch = time.time()
    start = time.monotonic()
    with post("/v1/chat/completions", prefill_body(uuid.uuid4(), args.lines)) as r:
        reply = json.load(r)
    seconds = time.monotonic() - start
    usage = reply["usage"]
    return {
        "kind": "prefill",
        "prompt_tokens": usage["prompt_tokens"],
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "seconds": round(seconds, 3),
        "tok_per_s": round(usage["prompt_tokens"] / seconds, 1),
        "tensorfold": kept(engine_fields(reply)),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }


def streamed(body):
    """A streamed request: (start epoch, start, first token, end, usage, block, finish)."""
    start_epoch = time.time()
    start = time.monotonic()
    first = None
    usage = None
    block = {}
    finish = None
    with post("/v1/chat/completions", body) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            block.update(
                engine_fields(chunk)
            )  # on the chunk that ends the reply, before usage
            choice = (chunk.get("choices") or [{}])[0]
            finish = choice.get("finish_reason") or finish
            delta = choice.get("delta") or {}
            if first is None and (
                delta.get("content")
                or delta.get("reasoning_content")
                or delta.get("reasoning")
            ):
                first = time.monotonic()
    return start_epoch, start, first, time.monotonic(), usage, block, finish


def decode(_args):
    start_epoch, start, first, end, usage, block, finish = streamed(decode_body())
    tokens = usage["completion_tokens"]
    return {
        "kind": "decode",
        "completion_tokens": tokens,
        "finish_reason": finish,
        "ttft": round(first - start, 3),
        "seconds_after_first": round(end - first, 3),
        "tok_per_s": round((tokens - 1) / (end - first), 2),
        "tensorfold": kept(block, DECODE_KEPT),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }


def edit(_args):
    start_epoch, start, first, end, usage, block, finish = streamed(edit_body())
    tokens = usage["completion_tokens"]
    return {
        "kind": "edit",
        "prompt_tokens": usage["prompt_tokens"],
        "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        "completion_tokens": tokens,
        "finish_reason": finish,
        "ttft": round(first - start, 3),
        "seconds_after_first": round(end - first, 3),
        "tok_per_s": round((tokens - 1) / (end - first), 2),
        "tensorfold": kept(block, EDIT_KEPT),
        "start_epoch": round(start_epoch, 1),
        "end_epoch": round(time.time(), 1),
    }


# Each kind's run takes the parsed arguments; only the prefill reads one (--lines).
RUN = {"prefill": prefill, "decode": decode, "edit": edit}


def compares(row):
    """An edit reply cut at its limit (finish_reason length) is not the edited module:
    its rate stays in the row and in the summary's "all" but not in the median, and the
    summary's "cut" counts it by kind."""
    return not (row["kind"] == "edit" and row["finish_reason"] == "length")


def kinds(text):
    names = text.split(",")
    unknown = [k for k in names if k not in KINDS + OPTIONAL]
    if unknown:
        raise argparse.ArgumentTypeError("unknown kind: " + ", ".join(unknown))
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--kinds",
        type=kinds,
        default=list(KINDS),
        help="comma-separated, run in this order (default prefill,decode; edit on request)",
    )
    parser.add_argument("--runs", type=int, default=3, help="requests of each kind")
    parser.add_argument("--lines", type=int, default=LINES, help="the prefill's lines")
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="prefill requests of the same length run first and not counted (default 1)",
    )
    parser.add_argument("--out", help="a JSONL file that receives one row per request")
    args = parser.parse_args(argv)
    speeds, kept, cut, warm = {}, {}, {}, []
    for kind in args.kinds:
        if kind == "prefill":
            warm = [prefill(args)["tok_per_s"] for _ in range(args.warmup)]
        for _ in range(args.runs):
            row = RUN[kind](args)
            speeds.setdefault(kind, []).append(row["tok_per_s"])
            if compares(row):
                kept.setdefault(kind, []).append(row["tok_per_s"])
            else:
                cut[kind] = cut.get(kind, 0) + 1
            if args.out:
                with open(args.out, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
    print(
        json.dumps(
            {
                "summary": {k: statistics.median(v) for k, v in kept.items()},
                "all": speeds,
                **({"warmup": warm} if warm else {}),
                **({"cut": cut} if cut else {}),
                "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
