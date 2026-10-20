# Validation (3.x)

[日本語](validation.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Benchmark method](benchmarks.md)

What a 3.x launch is accepted on, in the order to run it, with the reference values. The reference values are the native engine's own, measured on the reference hosts in 3.1.0's acceptance on 2026-10-19 and 20 with the engine built from `1a8f1efd` (upstream 1.1.1 and this line's two commits), `serve.sh`'s defaults and every container on the efficiency cores. TP=3 runs the BF16 linears on the glue kernels 3.0.0 ran (`TF_GLM_MM=0`) and gave 3.0.0's decode-check hashes, edit reply and NLL; TP=2 runs upstream's tiled kernels and gave new ones ([serving defaults](../README.md#serving-defaults)). 3.2.0's acceptance on 2026-10-20 ran the same checks with the vision tower loaded and gave the same hashes, edit reply, NLL and tool-eval-bench scores at both TP sizes; where its speed, memory or heat differed, the sections below say so. 2.x's references do not apply: the native engine's kernels and its BF16 KV cache give other tokens, so the two lines compare by teacher-forced NLL, and 2.x's values appear here as information only. Which images were accepted against them is the README's [status](../README.md#summary). A check that differs is a finding to explain before routine use, not a value to replace.

Run the tools from `v3/` of the checkout on rank 0, in its virtual environment ([setup §2](../SETUP.md#2-checkout-and-checkpoint)) or in the container, which has Python and `tokenizers`, against the engine on loopback (`http://127.0.0.1:8095`, model `glm-tf` unless the rank file sets others). Let the hosts cool between long requests ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)), and keep the memory guard and the [thermal watch](../../host/README.md#during-long-runs) running.

## Decode check

Greedy 512 tokens after the fixed prompt of about 2,048 tokens, three times for each task, as in 1.x and 2.x:

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python -m glm53_tf decode-check
done
```

The engine returns no token ids: each row gives the hash of the completion text and `token_sha256`, the engine's hash of the reply's token ids (the ids as comma-separated decimals, which does not compare with 2.x's `token_ids_sha256`). The engine keeps prompts in a cache sized in GiB that no request can drop, so a sample after the first may resume the prompt (`cached` in the row, `resumed` in the summary); a resumed prompt gives the same tokens. `TOKENS_OUT` keeps each sample's text, and two launches whose hashes differ are compared at their first diverging character with `python -m glm53_tf decode-divergence A.json B.json`.

**Accepted when** each task gives one completion within the launch (`distinct_completions` 1) and its hashes are the reference of its TP:

| Task | TP=2 `completion_sha256` | TP=2 `token_sha256` | TP=3 `completion_sha256` | TP=3 `token_sha256` |
|---|---|---|---|---|
| count | `96385e4d65278eac` | `6faafd98ec90322f` | `1cf31fa39a420336` | `6835af3a11c0b3e6` |
| prose | `464e122fc0c4a71e` | `b82116bdbaa49958` | `72c9b1e2cf183215` | `d22f429e247f196f` |
| code | `3b7e3ee097146c50` | `ddd42119a8be799e` | `59e2a180d1b9ccc7` | `3dd2e6dd1afd23cf` |

The hashes held in two launches at each TP size and in a TP=2 launch with `PARALLEL=` empty (count; the engine took two streams); TP=3's are 3.0.0's. On every core, upstream 1.1.1 without this line's two commits gave the same TP=2 token ids, and the release image gave each TP size's hashes and edit reply in one launch each. TP=2 and TP=3 differ from each other by design (the ranks split the sums differently, and TP=2's linears run on other kernels). 3.0.0's TP=2 hashes (count `bbf97d42e5d45bd3`, prose `da21339524bf4382`, code `bc00b6fc275d9595`) belong to its engine's kernels. Acceptance length: 3.066 / 1.882 / 2.621 at TP=2 and 3.368 / 1.787 / 2.839 at TP=3. `bench --kinds edit` returns the same reply at both TP sizes, `token_sha256` `c419bce559d86b66` in 190 rounds (3.0.0's engine took 363 for the same reply); a different reply stops the acceptance.

## Drafted equals serial

The same prompt with and without drafts (`"draft": false` in the request body decodes one token a round) must give the same text: prose, code and counting prompts, up to 256 tokens, temperature 0, effort low, at both TP sizes, compared as whole texts (reasoning and answer). With the vision tower loaded the check also sends a small PNG with a request to describe it, up to 64 tokens, and compares the two replies the same way. `bench --kinds edit` gives the same reply in every run and in a second launch.

## Image and video input

`serve.sh` starts the engine with `--vision` (`VISION=1`, the default). The checks send greedy requests with thinking off. **Accepted when**:

- **Text unchanged**: with the tower loaded, the decode check and `bench --kinds edit` give the hashes and reply above, at both TP sizes.
- **Images**, at both TP sizes: the same picture as a PNG, a JPEG and a WebP data URL answers, each with the same reply drafted and with `"draft": false`, and a GIF is refused with 400; a conversation with the picture in its first message resumes its later turn from the prompt cache past the picture, with the cold run's reply, and with `"draft": false` and at once with another the same.
- **Videos**: at TP=2, upstream's `tools/zig/video_served.py` at the engine's commit passes on its 13 clips (made by `tools/zig/glm_video_fixtures.py` with PyAV 19.0.1), against the pinned checkpoint's processor in transformers 5.19.0, with `REASONING_EFFORT=` in the rank files (the tool renders the chat template at its own default effort): each clip's prompt ids equal the processor's; a later turn resumes past its video, and another video under the same text resumes only the text before it; drafted equals `"draft": false`; four requests at once equal their runs alone; a video and an image answer in one request; and eight malformed requests are refused with 400 and the reason. At TP=3, an H.264 MP4 and a VP9 WebM answer, each with the same reply drafted and with `"draft": false`.

## Teacher-forced NLL

The NLL set of [`config/nll_set.json`](../config/nll_set.json), a byte copy of 1.x's and 2.x's: four domains (Japanese, English, code, math) of four texts each, 5,851-6,830 tokens per domain, scored through `prompt_logprobs` on `/v1/completions`. The tokenizer must be the checkpoint's own:

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

Needs the `tokenizers` package where it runs. Each text is scored twice; the run passes when every request answered and the two scores of each text agree.

| Domain (positions) | TP=2 | TP=3 | 2.x TP=2 (information) | 2.x TP=3 (information) |
|---|---|---|---|---|
| Japanese (6,826) | 2.5412 | 2.5246 | 2.5474 | 2.5313 |
| English (6,678) | 2.9293 | 2.9206 | 2.9257 | 2.9001 |
| Code (5,941) | 1.3145 | 1.3147 | 1.3184 | 1.3101 |
| Math (5,847) | 0.6261 | 0.6241 | 0.6250 | 0.6237 |

**Accepted when** the run passes and each domain equals the reference of its TP. The two scores of every text agreed exactly (largest move 0.0) at both TP sizes. TP=3's values are 3.0.0's, text by text; TP=2's moved from 3.0.0's (2.5293, 2.9109, 1.3138, 0.6272) by at most 0.0184 with the tiled kernels, and stay within 0.007 of 2.x's.

## Prompt scores and structured output

These are upstream's own on GLM's CUDA engine since 1.1.1 ([API](../README.md#api)). **Accepted when**, at both TP sizes:

- **`prompt_logprobs`**: every prompt token after the first has a row with its own rank and log-probability and the best alternatives ranked from 1; the same request again, and with `"draft": false`, gives the same rows; a prompt of 5,000 tokens has a row for every token, and the rows of its first 2,048-token chunk equal those of the same prompt cut at 3,001 tokens; a request without scores keeps its token hash.
- **Structured output**: a `json_schema` reply parses with the schema's keys and types, with thinking off and on; a schema the plain greedy reply already meets gives the same text under the grammar, and with `"draft": false`; the same seeded request at temperature 0.7 gives the same valid text twice; `tool_choice` `required` gives a call whose arguments parse, in GLM's tool markup; a request without a grammar keeps its token hash.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), after one uncounted prompt of the same length, then up to 512 tokens after a short fixed prompt, three times ([benchmark method](benchmarks.md#prefill-and-decode-speed)):

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

Reference: 1,415.7 tok/s prefill and 43.80 tok/s decode at TP=2, 1,507.9 and 55.05 at TP=3. Every decode row stops at the limit (`finish_reason` `length`), and each prefill row's `cached` is 0.

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens:

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

Fitted to the targets, the prompts came to 199,307, 499,254 and 1,035,295 tokens. Reference: the passphrase found at 199,307 tokens in 153.4 s at TP=2 and 140.4 s at TP=3; at TP=3, 3 of 3 at 499,254 tokens with the first token after 398.1 s and 3 of 3 at 1,035,295 after 1,022.7 s. None resumed a kept prompt (`cached` 0) or waited for heat. In 3.2.0's acceptance, run in the afternoon, the 1,035,295-token prompt waited 34 s for heat (17 pauses of 2 s: 10 by the band, rank 0's hottest zone at 92.1 to 92.5 °C, and 7 by the look-ahead of `TF_HEAT_CEILING`, the zone at 91.3 to 91.9 °C) and gave its first token after 1,056.9 s; all three passphrases were found. The 1,036,859-token target is TP=3's alone; TP=2's window is 245,760 tokens.

## Tools through the tool-argument gate

tool-eval-bench with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#6-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

The engine does not pass `clear_thinking` to the chat template ([limits](../README.md#limits)); the invocation keeps it so that the scores compare with 1.x's and 2.x's.

Reference: 92/100 at TP=2 and 93/100 at TP=3 with the Safety Gate passed; TP=2 failed TC-21 and TC-61, TP=3 TC-61 alone. One trial each, so a point or two is within what one trial moves.

## Stopping a reply

**Accepted when**, at both TP sizes, with thinking off: a streamed request to write the numbers from 1 to 1,000, cut by the client after about 5 s, leaves no connection in `/health`'s `live` block within 15 s, and a short request right after answers within 10 s; the same request with the stop string `"\n300\n"` ends at 299 with `finish_reason` `stop`; a ledger prompt of about 93,000 tokens cut by the client after 3 s, while it is read, lets a short request right after answer in less than half the time the whole prompt takes to its first token. Reference: the connection gone 1.0 s after the cut at both TP sizes; after the cut prompt a short request answered in 0.39 s at TP=2 and 0.25 s at TP=3, against 68.4 s and 62.8 s to the whole prompt's first token. In 3.2.0's acceptance the short request answered in 0.42 s at TP=2 and 1.53 s at TP=3 (3.0.0's TP=3: 1.49 s), against 68.8 s and 62.6 s.

## Long runs of replies

Forty requests back to back, each a fresh nonce and a module of about 6,000 tokens of Python with a request for a detailed review, up to 1,024 tokens each, temperature 0, effort low. This is the load that heated the CPU's zones on every core ([why the efficiency cores](../README.md#serving-defaults)). **Accepted when** all forty answer and the thermal watch does not stop an engine.

Reference: forty of forty at both TP sizes, in 1,536 s at TP=2 and 1,315 s at TP=3. The hottest zone reached 74.9 °C on rank 0's host at TP=2 and 79.8 °C at TP=3 (3.2.0's acceptance: 1,548 s and 75.6 °C at TP=2, 1,317 s and 82.5 °C at TP=3, run in the afternoon). No GPU slowed for heat. On every core the same forty at TP=2 finished in 1,535 s with rank 0's host at 93.0 °C, 1 °C under the thermal watch's stop ([why the efficiency cores](../README.md#serving-defaults)).

## Memory and temperature

The memory guard's log (`<WORK>/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run; the hosts' telemetry gives the hottest ACPI zone every 2 s. Rank 0's log gives each prefill heat wait's seconds in a `heat_wait_s` line; the reply does not carry them.

Reference: the lowest `MemAvailable` of a launch was 15 GiB on both ranks at TP=2 and 23, 11 and 26 GiB on ranks 0, 1 and 2 at TP=3; rank 1's 11 GiB was one 2-s reading during tool-eval-bench, with 24 GiB before and after it. The hottest zone of a whole launch was 81.8 °C on rank 0's host and 83.6 °C on rank 1's at TP=2, and 90.8, 89.3 and 85.5 °C at TP=3. No request of the acceptance waited for heat, the 1M-token prompt included. With the vision tower loaded (3.2.0's acceptance) the lowest was 13 and 12 GiB at TP=2 and 22, 24 and 29 GiB at TP=3, the hottest zone 81.7 and 84.2 °C at TP=2 and 92.5, 89.2 and 86.7 °C at TP=3, and the 1M-token prompt waited 34 s for heat ([long inputs](#long-inputs)).

**Accepted when** no run is stopped by the memory guard or the thermal watch (two readings in a row at or above 94 °C).
