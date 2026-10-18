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

<!-- S6: the TP=2 and TP=3 hashes from s6-p2 and s6-p3, equal in s6-p2b and s6-p3b -->

| Task | TP=2 `completion_sha256` | TP=2 `token_sha256` | TP=3 `completion_sha256` | TP=3 `token_sha256` |
|---|---|---|---|---|
| count | | | | |
| prose | | | | |
| code | | | | |

<!-- S6: two launches each; acceptance length; edit's reply sha256 at both TP sizes; PARALLEL= count -->

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

<!-- S6: the TP=2 and TP=3 values from s6-p2 and s6-p3, 2.x's beside them as information -->

| Domain (positions) | TP=2 | TP=3 | 2.x TP=2 (information) | 2.x TP=3 (information) |
|---|---|---|---|---|
| Japanese (6,826) | | | 2.5474 | 2.5313 |
| English (6,678) | | | 2.9257 | 2.9001 |
| Code (5,941) | | | 1.3184 | 1.3101 |
| Math (5,847) | | | 0.6250 | 0.6237 |

**Accepted when** the run passes and each domain equals the reference of its TP.

## Prompt scores and structured output

These came to the native engine with this line's engine release ([API](../README.md#api)). **Accepted when**, at both TP sizes:

- **`prompt_logprobs`**: every prompt token after the first has a row with its own rank and log-probability and the best alternatives ranked from 1; the same request again, and with `"draft": false`, gives the same rows; a prompt of 5,000 tokens has a row for every token, and the rows of its first 2,048-token chunk equal those of the same prompt cut at 3,001 tokens; a request without scores keeps its token hash.
- **Structured output**: a `json_schema` reply parses with the schema's keys and types, with thinking off and on; a schema the plain greedy reply already meets gives the same text under the grammar, and with `"draft": false`; the same seeded request at temperature 0.7 gives the same valid text twice; `tool_choice` `required` gives a call whose arguments parse, in GLM's tool markup; a request without a grammar keeps its token hash.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), after one uncounted prompt of the same length, then up to 512 tokens after a short fixed prompt, three times ([benchmark method](benchmarks.md#prefill-and-decode-speed)):

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

<!-- S6: TP=2 and TP=3 prefill and decode from s6-p2 and s6-p3 -->

Every decode row stops at the limit (`finish_reason` `length`). The prompt cache does not hold these prompts: each row's `cached` is 0.

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens:

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

<!-- S6: TP=2 200K, TP=3 200K, 500K and 1M with their first-token times and heat waits -->

The 1,036,859-token prompt is TP=3's alone; TP=2's window is 245,760 tokens.

## Tools through the tool-argument gate

tool-eval-bench with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#6-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

The engine does not pass `clear_thinking` to the chat template ([limits](../README.md#limits)); the invocation keeps it so that the scores compare with 1.x's and 2.x's.

<!-- S6: TP=2 and TP=3 scores, the Safety Gate, the failed scenarios -->

One trial each, so a point or two is within what one trial moves.

## Stopping a reply

**Accepted when**, at both TP sizes, with thinking off: a streamed request to write the numbers from 1 to 1,000, cut by the client after about 5 s, leaves no connection in `/health`'s `live` block within 15 s, and a short request right after answers within 10 s; the same request with the stop string `"\n300\n"` ends at 299 with `finish_reason` `stop`; a ledger prompt of 93,178 tokens cut by the client after 3 s, while it is read, lets a short request right after answer in less than half the time the whole prompt takes to its first token.

## Long runs of replies

Forty requests back to back, each a fresh nonce and a module of about 6,000 tokens of Python with a request for a detailed review, up to 1,024 tokens each, temperature 0, effort low. This is the load that heated the CPU's zones on every core ([why the efficiency cores](../README.md#serving-defaults)). **Accepted when** all forty answer and the thermal watch does not stop an engine.

<!-- S6: TP=2 and TP=3: hottest zone of each host, seconds at or above 92 °C, GPU thermal slowdowns -->

## Memory and temperature

The memory guard's log (`<WORK>/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run; the hosts' telemetry gives the hottest ACPI zone every 2 s. Rank 0's log gives each prefill heat wait's seconds in a `heat_wait_s` line; the reply does not carry them.

<!-- S6: lowest MemAvailable per rank (TP=3 1M), the hottest zone per launch, heat waits, the followers' idle temperature -->

**Accepted when** no run is stopped by the memory guard or the thermal watch (two readings in a row at or above 94 °C).
