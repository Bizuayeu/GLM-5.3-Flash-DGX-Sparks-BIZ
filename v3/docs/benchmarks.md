# Benchmark method (3.x)

[日本語](benchmarks.ja.md) · [3.x overview](../README.md) · [Validation](validation.md)

How the 3.x figures were taken: those of [measured on the release](../README.md#measured-on-the-release) and the reference values of [validation](validation.md). The values live on those two pages; this page gives the conditions and the procedure behind them. The speed, long-input, decode-check and NLL figures come from this line's `glm53_tf` tools with the requests of 2.x's, so that a figure can be reproduced or compared; the checks that have no tool here are described closely enough to repeat.

## Hosts and conditions

- **Hosts.** The reference hosts, MSI EdgeXpert (GB10): the pair over a direct link for TP=2, three hosts in a ring for TP=3, nothing else on their GPUs (2.x's containers stopped).
- **GPU clock** capped at 2,200 MHz by the boot unit of the [host tools](../../host/README.md) ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)).
- **Engine and image.** The image the window ran, `glm53-tf3:3x-bc82bc4` (engine `3d3d61d5`; the release image has the same binaries), with `serve.sh`'s defaults: one stream, the windows of 245,760 tokens at TP=2 and 1,048,576 at TP=3, the heat wait at 92 °C / 88 °C with the look-ahead to 93 °C. One launch ran with an empty `PARALLEL=`, the engine's own choice of streams, and says so.
- **Cores.** Every container on the efficiency cores 0-4 and 10-14, as `create_container.sh` creates it.
- **Watchers.** The memory guard on every host and the thermal watch on every host of the launch.
- **Clients.** Every request from rank 0 to the engine on loopback, one at a time, temperature 0 and reasoning effort low unless a check says otherwise; the tools ran in the container from the checkout's `v3/`.

## Cooling between long requests

A cooling gate ran before each start and each group of measurements. It waits until rank 0's host's hottest ACPI zone is at or below 55.8 °C, or 936 s, the rule of [`host/cool-gate`](../../host/README.md#during-long-runs) with 2.x's calibration of that host. The other ranks' hosts were recorded and not waited for: their engines keep two CPU threads spinning while they wait ([why the efficiency cores](../README.md#serving-defaults)), and on every core rank 1's host idled near 70 °C, above any band 2.x used.

## Decode check

As [validation](validation.md#decode-check) describes: three samples of each task (count, prose, code), greedy 512 tokens after the fixed prompt of about 2,048 tokens. The tool reports the speed, the MTP acceptance length (1 + accepted / rounds, from each reply's `speculative` block), the hash of each completion's text and the engine's `token_sha256`; a sample after the first may resume the prompt from the prompt cache (`cached`), which gives the same tokens. Two launches at each TP size, each compared with the first.

## Prefill and decode speed

Before anything was timed, a prefill of about 3,000 tokens (`bench --kinds prefill --runs 1 --lines 250`).

**Prefill.** One user message: a line `nonce <a fresh UUID>`, 3,200 fixed lines (`measurement line <i> of the fixed prefill prompt.`) and `Reply ok.`, 38,960 tokens with the chat template; `max_tokens` 1, temperature 0, effort low, `clear_thinking`. The rate is the prompt tokens over the request's wall time at the client. The engine has no endpoint that drops its kept prompts, so the fresh nonce keeps any of them from matching; each row's `cached` was 0. One uncounted prompt of the same length first, then the median of three back to back.

**Decode after a short prompt.** `Write the numbers from 1 to 1000, one per line, and nothing else.`, streamed, up to 512 tokens, temperature 0, effort low. The rate is the completion tokens after the first over the time after the first streamed token; the median of three. Every row stops at the limit (`finish_reason` `length`), so every token rated is the counting itself. Each row adds the reply's `rounds`, `tokens_per_round` and `token_sha256`.

**Decode of an edit (`--kinds edit`).** A fixed Python module of about 6,000 characters in a code block and three named one-line edits, `Return the whole module with only these edits, in one code block:`, the same every run, streamed, temperature 0, effort low, up to 4,096 tokens and ending on its own. Rated as the decode above; its `token_sha256` must be the same in every run and in a second launch.

`python -m glm53_tf bench` runs the prefill and the decode, three of each; `--kinds edit --runs 3` the edit; `--out` appends one row per request with the reply's `prefill_seconds`, `time_to_first_token` and `cached` tokens and the request's start and end epochs.

## Long inputs

Every long prompt is a ledger of numbered lines, `Ledger <i>: the river barge delivered sacks of barley to the northern granary at dusk.`, after the system message `You are a careful archivist. Read the ledger.`, at temperature 0 and effort low, its line count fitted to the target with the engine's `/tokenize`. Each row's `cached` gives the tokens a prompt resumed from the prompt cache; in the acceptance every long prompt was read whole (`cached` 0), TP=3's three in a row included.

- **One passphrase at 199,652 tokens**, in the middle. Not streamed, up to 512 tokens; correct when the reply contains it. At both TP sizes.
- **Three passphrases** (one twentieth from the start, the middle, one twentieth from the end) **at 499,622 and 1,036,859 tokens**, TP=3. Streamed, up to 256 tokens; the client times the first streamed token; correct when the reply lists all three.

The heat waits of a prompt are read from rank 0's `heat_wait_s` lines between the request's start and end.

## Teacher-forced NLL

The NLL set and the scorer as [validation](validation.md#teacher-forced-nll) describes, with the checkpoint's own tokenizer; every text scored twice through `prompt_logprobs`.

## Drafted equals serial, prompt scores, structured output and stopping

- **Drafted equals serial**: prose, code and counting prompts, up to 256 tokens, with and without `"draft": false`, compared as whole texts. In the same run, a request with a 1×1 PNG image part, refused with 400.
- **Prompt scores and structured output**: the checks [validation](validation.md#prompt-scores-and-structured-output) lists, each request sent on its own.
- **Stopping a reply**: thinking off. A request to write the numbers from 1 to 1,000, one per line, up to 4,000 tokens, streamed and closed by the client after 5 s; `/health` is read every second for 15 s until its `live` block has no connection, then a short request is timed. The same request with the stop string `"\n300\n"`, not streamed. A ledger of 6,000 lines (about 93,000 tokens) streamed and closed after 3 s, a short request timed right after, and the same ledger again in full for its time to the first token.

## Tools through the gate

tool-eval-bench with 1.x's invocation through the tool-argument gate ([validation](validation.md#tools-through-the-tool-argument-gate)), one trial at each TP size. Its 69 scenarios run back to back without cooling.

## Long runs of replies

Forty requests back to back with no pause, not streamed. Each is one user message: a line `nonce <a fresh UUID>`, a code block of 200 generated functions (`def helper_<i>(values, scale=<i mod 13 + 1>):` returning `[v * scale + <i> for v in values if v % <i mod 5 + 2>]`), about 6,000 tokens with the chat template, and `Review this module in detail: for each group of helpers, what it does, its bugs and how to fix them.`; up to 1,024 tokens, temperature 0, effort low, `clear_thinking`. It stands for a coding agent's turns, each reading new text and then writing, and runs after the tool-eval at each TP size.

## Memory and temperature

The lowest `MemAvailable` of each host is read from the memory guard's log (every 2 s); the temperatures from the hosts' telemetry (every 2 s, every ACPI zone and the GPU), whose hottest zone the thermal watch also reads; the GPU's thermal slowdowns from the driver's cumulative counters (`nvidia-smi`'s `clocks_event_reasons_counters`), sampled every second; and the heat waits from rank 0's `heat_wait_s` lines.
