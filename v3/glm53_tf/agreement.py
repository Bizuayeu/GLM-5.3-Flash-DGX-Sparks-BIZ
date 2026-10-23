"""Teacher-forced scoring of texts, per token, and the agreement of its repeats.

Quality gates so far (FreedomBench, tool-eval, MTP acceptance) score answers.
None says how often the model's next-token choice still equals the unmodified
server's choice. This module feeds the callers' texts through
``/v1/completions`` with ``prompt_logprobs`` and records, per position, the
rank and log-probability of the actual next token.

Two readings, kept apart:

* teacher-forced: how often the actual token is rank 1 / within the top five,
  and its mean negative log-probability. This is the number SAGE-style model
  cards report against the native checkpoint.
* agreement: between two scorings of the same text, how often the argmax token is
  the same, how much of the top-k overlaps, and how far the actual token's
  log-probability moved.

Nothing here talks to a server or a file; the callers pass senders in.
"""

import math

TOP_K = 5


def parse_prompt_logprobs(prompt_logprobs, prompt_token_ids):
    """vLLM's completions ``prompt_logprobs`` into rows of (token_id, logprob).

    The first entry is None (no prediction for the first token). Each later
    entry maps token-id strings to {"logprob", "rank", "decoded_token"} and
    always contains the actual prompt token, even when it is outside the
    top-k. Rows are sorted by log-probability, highest first. The shape is
    checked, not assumed; a different server would raise here, not mis-score.
    """
    if not isinstance(prompt_logprobs, list) or not prompt_logprobs:
        raise ValueError("prompt_logprobs must be a non-empty list")
    if len(prompt_logprobs) != len(prompt_token_ids):
        raise ValueError("prompt_logprobs and prompt token ids differ in length")
    if prompt_logprobs[0] is not None:
        raise ValueError("The first prompt_logprobs entry must be None")
    rows = []
    for position, entry in enumerate(prompt_logprobs[1:], start=1):
        if not isinstance(entry, dict) or not entry:
            raise ValueError(f"prompt_logprobs[{position}] is not a token map")
        row = []
        for token, detail in entry.items():
            logprob = detail["logprob"]
            if not isinstance(logprob, (int, float)) or not math.isfinite(logprob):
                raise ValueError(f"prompt_logprobs[{position}] has a non-finite value")
            row.append((int(token), float(logprob)))
        row.sort(key=lambda pair: (-pair[1], pair[0]))
        actual = prompt_token_ids[position]
        if all(token != actual for token, _ in row):
            raise ValueError(f"prompt_logprobs[{position}] omits the prompt token")
        rows.append(row)
    return rows


def teacher_forced(rows, prompt_token_ids, top_k=TOP_K):
    """How the actual next token ranks in each predicted distribution."""
    if len(rows) != len(prompt_token_ids) - 1:
        raise ValueError("rows must cover every prompt position but the first")
    ranks, logprobs = [], []
    for row, actual in zip(rows, prompt_token_ids[1:]):
        rank = next(i for i, (token, _) in enumerate(row, start=1) if token == actual)
        ranks.append(rank)
        logprobs.append(next(lp for token, lp in row if token == actual))
    positions = len(rows)
    return {
        "positions": positions,
        "top1": sum(rank == 1 for rank in ranks) / positions,
        f"top{top_k}": sum(rank <= top_k for rank in ranks) / positions,
        "mean_nll": -sum(logprobs) / positions,
        "ranks": ranks,
        "logprobs": logprobs,
    }


def agreement(reference_rows, candidate_rows, top_k=TOP_K):
    """Argmax agreement, top-k overlap and log-probability drift, per position."""
    if len(reference_rows) != len(candidate_rows):
        raise ValueError(
            "Reference and candidate cover a different number of positions"
        )
    if not reference_rows:
        raise ValueError("Nothing to compare")
    argmax_same, overlaps = [], []
    for reference, candidate in zip(reference_rows, candidate_rows):
        argmax_same.append(reference[0][0] == candidate[0][0])
        top_reference = {token for token, _ in reference[:top_k]}
        top_candidate = {token for token, _ in candidate[:top_k]}
        overlaps.append(
            len(top_reference & top_candidate) / len(top_reference | top_candidate)
        )
    positions = len(reference_rows)
    first_divergence = next(
        (i for i, same in enumerate(argmax_same, start=1) if not same), None
    )
    return {
        "positions": positions,
        "argmax_agreement": sum(argmax_same) / positions,
        f"top{top_k}_overlap_mean": sum(overlaps) / positions,
        f"top{top_k}_overlap_min": min(overlaps),
        "first_argmax_divergence": first_divergence,
    }


def drift(reference_logprobs, candidate_logprobs):
    """Largest and mean absolute move of the actual token's log-probability."""
    if len(reference_logprobs) != len(candidate_logprobs) or not reference_logprobs:
        raise ValueError("Log-probability series differ in length or are empty")
    moves = [abs(a - b) for a, b in zip(reference_logprobs, candidate_logprobs)]
    return {
        "max_abs_logprob_move": max(moves),
        "mean_abs_logprob_move": sum(moves) / len(moves),
    }


def score_text(name, prompt_token_ids, response, top_k=TOP_K):
    """One text's teacher-forced reading plus the rows a later run compares against."""
    choice = response["choices"][0]
    rows = parse_prompt_logprobs(choice["prompt_logprobs"], prompt_token_ids)
    forced = teacher_forced(rows, prompt_token_ids, top_k)
    return {
        "name": name,
        "prompt_tokens": len(prompt_token_ids),
        "top1": forced["top1"],
        f"top{top_k}": forced[f"top{top_k}"],
        "mean_nll": forced["mean_nll"],
        "ranks": forced["ranks"],
        "logprobs": forced["logprobs"],
        "rows": rows,
        "prompt_token_ids": list(prompt_token_ids),
    }


def run(tokenize, complete, texts, top_k=TOP_K, repeats=2):
    """Score each of ``texts`` (name to text) ``repeats`` times through the given senders;
    never raise.

    ``tokenize(text)`` returns the prompt token ids; ``complete(token_ids, top_k)``
    returns the completions response. The first raw response is kept so the
    record shows the server's actual ``prompt_logprobs`` shape. Repeats of the
    same text inside one run measure how far the server moves by itself; the
    difference is reported as ``self_agreement`` and is the yardstick for any
    comparison with another run.
    """
    rows, raw_first, self_checks = [], None, []
    for name, text in texts.items():
        scored = []
        for _ in range(repeats):
            try:
                token_ids = tokenize(text)
                response = complete(token_ids, top_k)
                if raw_first is None:
                    raw_first = response
                scored.append(score_text(name, token_ids, response, top_k))
            except Exception as error:  # noqa: BLE001 - a failed request is recorded
                scored.append(
                    {"name": name, "error": f"{type(error).__name__}: {error}"}
                )
        rows.extend(scored)
        good = [row for row in scored if "error" not in row]
        if len(good) >= 2:
            check = {"name": name}
            check.update(agreement(good[0]["rows"], good[1]["rows"], top_k))
            check.update(drift(good[0]["logprobs"], good[1]["logprobs"]))
            self_checks.append(check)
    errors = [row for row in rows if "error" in row]
    return {
        "top_k": top_k,
        "repeats": repeats,
        "texts": rows,
        "self_agreement": self_checks,
        "errors": len(errors),
        "first_raw_response": raw_first,
        # Every request answered in the checked shape. Repeats are reported in
        # self_agreement, not required to be identical: whether they are depends
        # on the server (TensorFold: its contract, README.md#differences-from-1x;
        # vLLM: ../v1/docs/server-configuration.md#repeatability-switches).
        "passed": not errors and bool(self_checks),
    }
