# Validation (3.x)

[日本語](validation.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Benchmark method](benchmarks.md)

What a 3.x launch is accepted on, in the order to run it, with the reference values. The reference values are the native engine's own, measured on the reference hosts in 3.0.0's acceptance on 2026-10-18 with the release image (engine `3d3d61d5`), `serve.sh`'s defaults and every container on the efficiency cores. 2.x's references do not apply: the native engine's kernels and its BF16 KV cache give other tokens, so the two lines compare by teacher-forced NLL, and 2.x's values appear here as information only. Which images were accepted against them is the README's [status](../README.md#summary). A check that differs is a finding to explain before routine use, not a value to replace.

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
| count | `3c8dee2084715576` | `bbf97d42e5d45bd3` | `1cf31fa39a420336` | `6835af3a11c0b3e6` |
| prose | `f1d18bd46cdc4a6e` | `da21339524bf4382` | `72c9b1e2cf183215` | `d22f429e247f196f` |
| code | `74c0d1859ed63614` | `bc00b6fc275d9595` | `59e2a180d1b9ccc7` | `3dd2e6dd1afd23cf` |

The hashes held in two launches at each TP size, in a TP=2 launch with `PARALLEL=` empty (count), at TP=2 with the containers on every core, and on the release image at TP=2 (count). TP=2 and TP=3 differ from each other by design (the ranks split the sums differently). Acceptance length: 3.34 / 1.879 / 2.747 at TP=2 and 3.048 / 1.787 / 2.839 at TP=3. `bench --kinds edit` returns the same reply at both TP sizes, `token_sha256` `c419bce559d86b66` in 363 rounds; a different reply stops the acceptance.

## Drafted equals serial

The same prompt with and without drafts (`"draft": false` in the request body decodes one token a round) must give the same text: prose, code and counting prompts, up to 256 tokens, temperature 0, effort low, at both TP sizes, compared as whole texts (reasoning and answer). `bench --kinds edit` gives the same reply in every run and in a second launch.

## Image input refused

The native engine reads no images on GLM's CUDA path. **Accepted when** a request with an image part is refused with 400.

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
| Japanese (6,826) | 2.5293 | 2.5246 | 2.5474 | 2.5313 |
| English (6,678) | 2.9109 | 2.9206 | 2.9257 | 2.9001 |
| Code (5,941) | 1.3138 | 1.3147 | 1.3184 | 1.3101 |
| Math (5,847) | 0.6272 | 0.6241 | 0.6250 | 0.6237 |

**Accepted when** the run passes and each domain equals the reference of its TP. The two scores of every text agreed exactly (largest move 0.0) at both TP sizes, and the TP=2 values are those the engine gave before its release in the same scoring.

## Prompt scores and structured output

These came to the native engine with this line's engine release ([API](../README.md#api)). **Accepted when**, at both TP sizes:

- **`prompt_logprobs`**: every prompt token after the first has a row with its own rank and log-probability and the best alternatives ranked from 1; the same request again, and with `"draft": false`, gives the same rows; a prompt of 5,000 tokens has a row for every token, and the rows of its first 2,048-token chunk equal those of the same prompt cut at 3,001 tokens; a request without scores keeps its token hash.
- **Structured output**: a `json_schema` reply parses with the schema's keys and types, with thinking off and on; a schema the plain greedy reply already meets gives the same text under the grammar, and with `"draft": false`; the same seeded request at temperature 0.7 gives the same valid text twice; `tool_choice` `required` gives a call whose arguments parse, in GLM's tool markup; a request without a grammar keeps its token hash.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), after one uncounted prompt of the same length, then up to 512 tokens after a short fixed prompt, three times ([benchmark method](benchmarks.md#prefill-and-decode-speed)):

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

Reference: 1,433.5 tok/s prefill and 42.01 tok/s decode at TP=2, 1,454.9 and 55.61 at TP=3. Every decode row stops at the limit (`finish_reason` `length`), and each prefill row's `cached` is 0. With the containers on every core the same build measured 1,481.6 and 42.45 at TP=2 ([why the efficiency cores](../README.md#serving-defaults)).

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens:

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

The targets fit 199,307, 499,254 and 1,035,295 tokens. Reference: the passphrase found at 199,307 tokens in 152.7 s at TP=2 and 150.2 s at TP=3; at TP=3, 3 of 3 at 499,254 tokens with the first token after 425.4 s and 3 of 3 at 1,035,295 after 1,082.9 s. None resumed a kept prompt (`cached` 0) or waited for heat. The 1,036,859-token target is TP=3's alone; TP=2's window is 245,760 tokens.

## Tools through the tool-argument gate

tool-eval-bench with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#6-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

The engine does not pass `clear_thinking` to the chat template ([limits](../README.md#limits)); the invocation keeps it so that the scores compare with 1.x's and 2.x's.

Reference: 93/100 at both TP sizes with the Safety Gate passed; TP=2 failed TC-21 and TC-61, TP=3 TC-61 alone. One trial each, so a point or two is within what one trial moves.

## Stopping a reply

**Accepted when**, at both TP sizes, with thinking off: a streamed request to write the numbers from 1 to 1,000, cut by the client after about 5 s, leaves no connection in `/health`'s `live` block within 15 s, and a short request right after answers within 10 s; the same request with the stop string `"\n300\n"` ends at 299 with `finish_reason` `stop`; a ledger prompt of about 93,000 tokens cut by the client after 3 s, while it is read, lets a short request right after answer in less than half the time the whole prompt takes to its first token. Reference: the connection gone 1.0 s after the cut at both TP sizes; after the cut prompt a short request answered in 0.32 s at TP=2 and 1.49 s at TP=3, against 67.8 s and 66.6 s to the whole prompt's first token.

## Long runs of replies

Forty requests back to back, each a fresh nonce and a module of about 6,000 tokens of Python with a request for a detailed review, up to 1,024 tokens each, temperature 0, effort low. This is the load that heated the CPU's zones on every core ([why the efficiency cores](../README.md#serving-defaults)). **Accepted when** all forty answer and the thermal watch does not stop an engine.

Reference: forty of forty at both TP sizes, in 1,599 s at TP=2 and 1,245 s at TP=3. The hottest zone reached 82.6 °C on rank 0's host at TP=2 and 79.7 °C at TP=3, no host read 92 °C, and the GPUs did not slow for heat. With the containers on every core the same run at TP=2 stopped at the seventh reply, at 94.7 °C.

## Memory and temperature

The memory guard's log (`<WORK>/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run; the hosts' telemetry gives the hottest ACPI zone every 2 s. Rank 0's log gives each prefill heat wait's seconds in a `heat_wait_s` line; the reply does not carry them.

Reference: the lowest `MemAvailable` of a launch was 16 GiB on both ranks at TP=2 and 30, 30 and 36 GiB on ranks 0, 1 and 2 at TP=3. The hottest zone of a whole launch was 89.0 °C on rank 0's host and 83.0 °C on rank 1's at TP=2, and 89.0, 88.8 and 83.3 °C at TP=3. No request of the acceptance waited for heat, the 1M-token prompt included.

**Accepted when** no run is stopped by the memory guard or the thermal watch (two readings in a row at or above 94 °C).
