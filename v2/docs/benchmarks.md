# Benchmark method (2.x)

[日本語](benchmarks.ja.md) · [2.x overview](../README.md) · [Validation](validation.md) · [Decisions](decisions.md)

How the 2.x figures were taken: those of [measured on the release](../README.md#measured-on-the-release) and the reference values of [validation](validation.md). The values live on those two pages; this page gives the conditions and the procedure behind them. The scripts that took the speed and long-input figures were outside the repository; 2.1.5 made `glm53_tf` copies of them with the same prompts and requests, `python -m glm53_tf bench` and `python -m glm53_tf long-input` (run from `v2/` on rank 0), so that a figure can be reproduced or questioned.

## Hosts and conditions

- **Hosts.** The reference hosts, MSI EdgeXpert (GB10): the pair over a direct link for TP=2, three hosts in a ring for TP=3, nothing else on their GPUs (1.x stopped).
- **GPU clock** capped at 2,200 MHz by the boot unit of the [host tools](../../host/README.md) ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)). The telemetry logged 2,171-2,197 MHz under load.
- **Engine (2.0.0's figures).** The release image and the images one and two engine commits before it; [which engine](../README.md#measured-on-the-release) gives the commit of each row: the decode check on `b44c2f1` at TP=2 and `2d4fa9b` at TP=3, the TP=3 prefill and the 1M-token prompt on `2d4fa9b`, the other rows on `304109c`.
- **Watchers.** The memory guard on every host and the thermal watch on rank 0's host.
- **Clients.** Every request from rank 0 to the engine on loopback, one at a time, temperature 0 and reasoning effort low unless a check says otherwise. At the release the checks used 1.x's tools from the same checkout: the decode check, the NLL scorer (run inside the container, where `tokenizers` is installed) and the tool-argument gate on port 8897. 2.0.5 made `glm53_tf` copies of them with the same arguments, the commands of [validation](validation.md).

## Cooling between long requests

A cooling gate ran on every host at once before each group of measurements (the decode check, NLL, the prefill and decode bench, the long inputs). It waits until the host's hottest ACPI zone is at or below a band, or for a cap, the rule of [`host/cool-gate`](../../host/README.md#during-long-runs):

| Host | Band | Cap |
|---|---|---|
| rank 0's | 55.8 °C | 936 s |
| rank 1's | 53.2 °C | 936 s |
| rank 2's (TP=3) | 60 °C | 600 s |

The first two bands were calibrated on those hosts during 1.x's measurements; rank 2's host had no calibration and took `cool-gate`'s defaults. The gates were run because prefill seemed to slow as a host heated; [validation](validation.md#prefill-and-decode-speed) has since found two speeds that heat does not explain.

The heat wait was on at 92 °C / 88 °C in the runs on `2d4fa9b` and `b44c2f1` that the release figures come from, except the control with it off; `304109c` predates it.

## Decode check

As [validation](validation.md#decode-check) describes: three samples of each task (count, prose, code), greedy 512 tokens after the fixed prompt of about 2,048 tokens, with the eviction requests before each sample so that every sample prefills the whole prompt (`cached` 0). The tool reports the speed, the MTP acceptance length and one hash per distinct completion.

## Prefill and decode speed

Before anything was timed, a prefill of about 3,000 tokens warmed up the prompt kernels' compilation. It does not reach every kernel a 38,960-token prompt compiles; from 2.9.3 `bench` runs one uncounted prompt of the same length first ([validation](validation.md#prefill-and-decode-speed)).

**Prefill.** One user message: a line `nonce <a fresh UUID>`, 3,200 fixed lines (`measurement line <i> of the fixed prefill prompt.`) and `Reply ok.`, 38,960 tokens with the chat template; `max_tokens` 1, temperature 0, effort low, `clear_thinking`. The rate is the prompt tokens over the request's wall time at the client. The fresh nonce at the start keeps any kept prompt from matching, since the engine has no endpoint to reset its kept prompts; each reply's `cached` was 0. The figure is the median of three:

- TP=2 (`304109c`): three prompts back to back after one cooling gate; they stayed within 0.1% of each other.
- TP=3 (`2d4fa9b`): one prompt after each cooling gate, three times with the heat wait on, then three times with it off for the control. Three prompts back to back without the gate slowed one after another; heat and the uniform slowdown [validation](validation.md#prefill-and-decode-speed) leaves open were not told apart.

**Decode after a short prompt.** `Write the numbers from 1 to 1000, one per line, and nothing else.`, streamed, up to 512 tokens without `ignore_eos`, temperature 0, effort low. The rate is the completion tokens after the first over the time after the first streamed token; the median of three. The reply counts until the limit cuts it (`finish_reason` `length`), so every token rated is the counting itself, and the prompt is the same every time, so the acceptance stays comparable between runs; a row with another `finish_reason` stopped early and does not compare. Each row adds `finish_reason` and, from the reply's `tensorfold` block, `rounds`, `tokens_per_round` and the reply's `sha256`. Before 2.5.0 the request was `Count upward from one, one number per line.` with `ignore_eos`, replaced because the model ends that reply by itself after about 100 tokens and the rest of the 512 was a conversation it made up past its end, different between the weights.

`python -m glm53_tf bench` runs both, three of each, the prefill after one uncounted prompt of the same length (`--warmup`, from 2.9.3; its rate is the summary's `warmup`); `--kinds prefill --runs 1 --warmup 0` sends one prompt (after each cooling gate), `--lines 250` gives a warm-up of about 3,000 tokens, and `--out` appends one row per request with the reply's `prefill_s`, `heat_wait_s` and `cached` and the request's start and end epochs.

**Decode of an edit (`--kinds edit`, only when asked for).** Added for copy drafts, which draft from the context and only gain where the reply repeats it. The prompt is a fixed Python module of about 6,000 characters in a code block and three named one-line edits, `Return the whole module with only these edits, in one code block`, the same every run (no nonce, so a repeat may resume from the kept prompt; that does not touch the decode rate). Streamed, temperature 0, effort low, up to 4,096 tokens, ending on its own: a `finish_reason` of `length` means the reply was cut and the row does not measure an edit (from 2.6.0 the summary's median leaves such a row out and its `cut` counts it). Rated as the decode above, so the reasoning tokens before the code count too. The row adds `prompt_tokens`, `finish_reason` and the reply's `rounds`, `drafted`, `accepted`, `copy_rounds`, `copy_drafted`, `copy_accepted` and `sha256`, the hash of the token ids, which stays the same from run to run and with copy drafts on or off.

## Long inputs

Every long prompt is a ledger of numbered lines, `Ledger <i>: the river barge delivered sacks of barley to the northern granary at dusk.`, after the system message `You are a careful archivist. Read the ledger.`, at temperature 0 and effort low. A short unrelated request went before each, so that no kept prompt could be resumed, and the reply's `cached` was 0. The hosts were cooled before each.

- **One passphrase at 199,652 tokens.** 8,806 lines with the passphrase in the middle, the line count 1.x recorded, so the text is 1.x's. Not streamed, up to 512 tokens; correct when the reply contains the passphrase. The time to the first token is the `ttft` of rank 0's `[tensorfold] done` line. At the release, on `304109c` at both TP sizes.
- **Three passphrases** (one twentieth from the start, the middle, one twentieth from the end) **at 499,622 and 1,036,859 tokens.** The number of lines is fitted to the target with the engine's `/tokenize`. Streamed, up to 256 tokens; the client times the first streamed token; correct when the reply lists all three. The release's 1,036,859-token figure is TP=3 on `2d4fa9b` with the heat wait on, whose total the reply's `tensorfold` block gives as `heat_wait_s`.

`python -m glm53_tf long-input --passphrases 1 --lines 8806` gives the first, `--passphrases 3 --tokens <target>` the second (the fitted prompt is at most the target: from 2.2.0 the target 1,036,859 fitted 45,808 lines, 1,035,295 tokens, and AXL's TP=2 run took its window, 262,144, as the target, 11,591 lines, 262,113 tokens); the row carries `ttft` (streamed only), `prompt_tokens`, `cached` and `heat_wait_s`, and the exit status is 1 when a passphrase is missing.

The development-build references of validation at 199,652 and 499,622 tokens were taken with the engine's profiling on (`TF_GLM_PROFILE=1`), which added about 11% to a 38,960-token prefill. Scaling the part of a prefill that does not grow with length by that much accounts for the 200K reference (146.4 s modelled, 145.6 measured) and leaves about 16 s unexplained at 500K (438.5 s modelled, 454.1 measured).

## Teacher-forced NLL

The NLL set and the scorer as [validation](validation.md#teacher-forced-nll) describes, with the checkpoint's own tokenizer; every text scored twice. At the release on `304109c`; the result equals the development builds' at full precision.

## Drafted equals serial and stopping

- **Drafted equals serial**: prose, code and counting prompts of 256 tokens, with and without `"draft": false`, compared as whole texts ([validation](validation.md#drafted-equals-serial)). A comparison that read one field per streamed delta reported a false difference at TP=2, because one delta can carry both `reasoning_content` and `content`.
- **Stopping a reply**: a request to list the numbers 1 to 1,000, one per line (about 4,000 tokens, more than a minute of decoding). Cut by the client after about 5 s: the `rounds` of `/health` and the completion tokens must not grow between 10 and 30 s after the cut, and a short request right after must start at once. With the stop string `"\n300\n"`: `finish_reason` `stop`, the text ending at 299, and a short request right after. An earlier form that asked the model to count upward was dropped: the model finished on its own before the disconnect, so it showed nothing. At the release on `304109c`.

## Tools through the gate

tool-eval-bench with 1.x's invocation through the tool-argument gate ([validation](validation.md#tools-through-the-tool-argument-gate)), one trial at each TP size, on `304109c`. Its 69 scenarios run back to back without cooling, about 9.5 minutes; rank 0's host reached 93 °C during the TP=2 run.

## Memory and temperature

The lowest `MemAvailable` of each host is read from the memory guard's log (every 2 s), the temperatures from the hosts' telemetry (every 2 s, the hottest ACPI zone) and the heat waits from the `[tensorfold] heat:` lines and each reply's `heat_wait_s` ([validation](validation.md#memory-and-temperature)).
