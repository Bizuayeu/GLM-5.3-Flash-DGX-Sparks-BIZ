# Validation (3.x)

[日本語](validation.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Benchmark method](benchmarks.md)

What a 3.x launch is accepted on, in the order to run it, with the reference values. The reference values are the native engine's own on XSFP4, the checkpoint 3.x serves ([checkpoints](../README.md#checkpoints)), measured on the reference hosts with the defaults of their release's `serve.sh` and every container on the efficiency cores. The decode-check hashes, the edit reply and the NLL were set in 3.3.0's acceptance on 2026-10-22, on upstream 1.1.2, whose tiled BF16 linears run at both TP sizes (issue #1067), and 3.4.0's, 3.6.0's and 3.8.0's release images gave them again at both TP sizes, 3.5.0's at TP=2; the other reference values are 3.8.0's acceptance's, on 2026-10-26, on upstream 1.1.5. NVIDIA's NVFP4, the default until 3.3.0 and a choice up to 3.5.x, had reference values of its own, which those releases' tags and the [changelog](../CHANGELOG.md) keep. 2.x's references do not apply: the native engine's kernels and its BF16 KV cache give other tokens, so the two lines compare by teacher-forced NLL, and 2.x's values appear here as information only. Which images were accepted against them is the README's [status](../README.md#summary). A check that differs is a finding to explain before routine use, not a value to replace.

The checks rest on what repeats. Within a launch the same request gives the same tokens, drafted or not (`"draft": false`), and a prompt resumed from the prompt cache gives the tokens of a fresh one; a launch gives the token ids of the launch before it at the same TP size and build. TP=2 and TP=3 differ by design, and so do kernels that sum differently, such as the glue kernels against the tiled ones (`TF_GLM_MM`). The same commit built on another host can give binaries with other SHA-256s that answer alike, so the decode check, not the hash, tells two builds apart ([setup §3](../SETUP.md#3-image)). More than one request at once was not checked for this. A number written twice in a count is the known place where generation and prompts part ([3.3.0's measurements](measurements.md#330)).

Run the tools from `v3/` of the checkout on rank 0, in its virtual environment ([setup §2](../SETUP.md#2-checkout-and-checkpoint)) or in the container, which has Python and `tokenizers`, against the engine on loopback (`http://127.0.0.1:8095`, model `glm-tf` unless the rank file sets others). The container mounts only the work directory (at `/work`) and the cache, so a checkout used there lives under the work directory. Every option and environment variable of the tools is in [configuration](configuration.md#tools). Let the hosts cool between long requests ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)), and keep the memory guard and the [thermal watch](../../host/README.md#during-long-runs) running (`--container glm53-tf3 --process 'tensorfold-native serve'`).

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
| count | `4e3411bd357abdd4` | `cbe6552f4f1efcca` | `e63b580fa9ac5e6b` | `f6afacd228e848bc` |
| prose | `3b1a0be713e866f7` | `065a835f86734482` | `098fe1f21f591775` | `32a387104a712248` |
| code | `4a2d744c5cc1fb10` | `c4dfca7b73492c81` | `d2768fdc1e974d89` | `9f6e8043c234c19d` |

The hashes held in a second launch at each TP size and, for the count, in a launch at each TP size with `PARALLEL=` empty and in one at TP=2's 245,760-token window with `PARALLEL=` empty. TP=2 and TP=3 differ from each other by design (the ranks split the sums differently). Acceptance length: 3.276 / 1.796 / 2.971 at TP=2 and 3.362 / 1.947 / 2.823 at TP=3. `bench --kinds edit` returns the same reply at both TP sizes, `token_sha256` `c419bce559d86b66` in 190 rounds; a different reply stops the acceptance.

## Drafted equals serial

The same prompt with and without drafts (`"draft": false` in the request body decodes one token a round) must give the same text: prose, code and counting prompts, up to 256 tokens, temperature 0, effort low, at both TP sizes, compared as whole texts (reasoning and answer). With the vision tower loaded the check also sends a small PNG with a request to describe it, up to 64 tokens, and compares the two replies the same way. `bench --kinds edit` gives the same reply in every run and in a second launch.

## Image and video input

`serve.sh` starts the engine with `--vision` (`VISION=1`, the default). The checks send greedy requests with thinking off. **Accepted when**:

- **Text unchanged**: with the tower loaded, the decode check and `bench --kinds edit` give the hashes and reply above, at both TP sizes.
- **Images**, at both TP sizes: the same picture as a PNG, a JPEG and a WebP data URL answers, each with the same reply drafted and with `"draft": false`, and a GIF is refused with 400; a conversation with the picture in its first message resumes its later turn from the prompt cache past the picture, with the cold run's reply, and with `"draft": false` and at once with another the same.
- **Videos**, at both TP sizes: an H.264 MP4 and a VP9 WebM answer, each with the same reply drafted and with `"draft": false`, and an audio part is refused with 400.

Upstream's own served checks of these inputs, `tools/zig/vision_served.py` and `video_served.py` in the engine's source, run against any engine started with `--vision`. 3.x's acceptance sent the requests above; 3.2.0's also ran `video_served.py`, at TP=2 on NVIDIA's NVFP4 ([changelog](../CHANGELOG.md)).

## Teacher-forced NLL

The NLL set of [`config/nll_set.json`](../config/nll_set.json), a byte copy of 1.x's and 2.x's: four domains (Japanese, English, code, math) of four texts each, 5,851-6,830 tokens per domain, scored through `prompt_logprobs` on `/v1/completions`. The tokenizer must be the checkpoint's own (XSFP4's, below):

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/88736f916f8939607fde8a4b881dcae749f7551d/tokenizer.json \
  --out ../records/<run>/nll.json
```

Needs the `tokenizers` package where it runs. Each text is scored twice; the run passes when every request answered, and its `self-agreement` line gives the largest move between the two scores of a text.

| Domain (positions) | TP=2 | TP=3 | 2.x TP=2 (information) | 2.x TP=3 (information) |
|---|---|---|---|---|
| Japanese (6,826) | 2.5494 | 2.5369 | 2.5474 | 2.5313 |
| English (6,678) | 2.9219 | 2.9244 | 2.9257 | 2.9001 |
| Code (5,941) | 1.3104 | 1.3098 | 1.3184 | 1.3101 |
| Math (5,847) | 0.6249 | 0.6224 | 0.6250 | 0.6237 |

**Accepted when** the run passes and each domain equals the reference of its TP. The two scores of every text agreed exactly (largest move 0.0) at both TP sizes. 2.x's columns are NVIDIA's NVFP4 on 2.x's engine, a checkpoint 3.x no longer serves: information only.

## Prompt scores and structured output

These are upstream's own on GLM's CUDA engine since 1.1.1 ([API](../README.md#api)). **Accepted when**, at both TP sizes:

- **`prompt_logprobs`**: every prompt token after the first has a row with its own rank and log-probability and the best alternatives ranked from 1; the same request again, and with `"draft": false`, gives the same rows; a prompt of 5,000 tokens has a row for every token, and the rows of its first 2,048-token chunk equal those of the same prompt cut at 3,001 tokens; a request without scores keeps its token hash.
- **Structured output**: a `json_schema` reply parses with the schema's keys and types, with thinking off and on; a schema the plain greedy reply already meets gives the same text under the grammar, and with `"draft": false`; the same seeded request at temperature 0.7 gives the same valid text twice; `tool_choice` `required` gives a call whose arguments parse, in GLM's tool markup; a request without a grammar keeps its token hash.

The request without scores or a grammar ("The capital of France is", 8 tokens) gives `token_sha256` `09a15f0582e7…` at TP=2 and `a094669ab5de…` at TP=3; TP=3's reply is a known behaviour ([XSFP4](#xsfp4)). Upstream's own check of structured output, `tools/zig/structured_served.py` in the engine's source (valid replies, drafted against plain and concurrent against solo, refusals), was not run on 3.x.

## Multibyte output

ModelOpt NVFP4 checkpoints whose gate and up projections carry different global scales were reported to garble multibyte text ([vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)), and 1.x monitors it with `server mojibake` ([1.x's multibyte output](../../v1/docs/correctness-gates.md#multibyte-output)). `mojibake` asks 1.x's prompts for Japanese and Korean answers of at least 400 characters, three of each, at temperature 0 or sampled, and counts U+FFFD, lone surrogates and control characters other than line breaks and tabs in the answer and in the reasoning (`reasoning_content`). The full answers stay in `--out`:

```sh
python -m glm53_tf mojibake --out ../records/<run>/mojibake.json
python -m glm53_tf mojibake --temperature 1.0 --top-p 0.95 --seed 42 --out ../records/<run>/mojibake-sampled.json
```

The requests name no reasoning effort, so the engine reasons at `serve.sh`'s default (high), within `serve.sh`'s limit of 32,768 tokens for the reasoning and the answer together. An answer that errs, is empty or short, is mostly outside its script or is cut at the limit is inconclusive (exit 2), never a pass; one broken character fails the check (exit 1). **Accepted when** every answer passes at both TP sizes.

Reference, on 3.8.0's image (2026-10-26): twelve answers at each TP size, six at temperature 0 and six sampled (temperature 1.0, top_p 0.95, seeds 42 to 47), none with a broken character. They ran from 753 to 1,301 characters, 91 to 95% in the target script, every one finished with `stop`, and the longest reply was 1,067 tokens. The reasoning was empty in 20 of the 24 and 106 or 138 characters in the other four (the sampled Japanese answers of seeds 43 and 44 at both sizes), so the reasoning text was hardly exercised.

## Prefill and decode speed

A 38,960-token prompt three times with a fresh nonce at its start (median), after one uncounted prompt of the same length, then up to 512 tokens after a short fixed prompt, three times ([benchmark method](benchmarks.md#prefill-and-decode-speed)):

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

Reference: 1,417.5 tok/s prefill and 53.89 tok/s decode at TP=2, 1,703.5 and 65.33 at TP=3. Every decode row stops at the limit (`finish_reason` `length`), and each prefill row's `cached` is 0.

## Long inputs

A passphrase in the middle of 199,652 tokens of ledger lines, and three passphrases (start, middle, end) in 499,622 and 1,036,859 tokens:

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 499622
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

Fitted to the targets, the prompts came to 199,307, 499,254 and 1,035,295 tokens. Reference: the passphrase found at 199,307 tokens in 151.5 s at TP=2 and 128.7 s at TP=3; 3 of 3 at 499,254 tokens with the first token after 429.2 s at TP=2 and 376.3 s at TP=3; at TP=3, 3 of 3 at 1,035,295 after 1,013.6 s, 30 s of it waiting for heat. The 1,036,859-token target is TP=3's alone; TP=2's window is 524,288 tokens from 3.5.0 (245,760 before it).

## Tools through the tool-argument gate

tool-eval-bench 2.8.0 with 1.x's invocation (69 scenarios, seed 42, temperature 0, parallel 1, effort low, `clear_thinking`, 4,096-token output, 600 s timeout), through the [gate](../SETUP.md#6-tool-argument-gate-optional):

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

From 3.8.0 the engine passes `clear_thinking` to the chat template, as 2.x's does (upstream 1.1.5; [configuration](configuration.md#rank-0s-server)); 3.0.0 to 3.7.0's did not. The invocation keeps it so that the scores compare with 1.x's and 2.x's.

Reference, on 3.8.0's image (2026-10-26): 95/100 at TP=2 and 92/100 at TP=3 with the Safety Gate passed; TP=2 left TC-39, TC-52 and TC-55 partial and failed TC-62 and TC-68, TP=3 left TC-14, TC-21, TC-39, TC-50 and TC-52 partial and failed TC-29, TC-62 and TC-68: the scores and scenarios of 3.5.3's and 3.6.0's images, whose engines did not pass `clear_thinking`. tool-eval-bench 2.6.1.dev52 (`81eae0a`) gave XSFP4 93 at both TP sizes; 2.7.0 and 2.8.0 grade many scenarios more strictly, so scores of different versions do not compare. One trial each, so a point or two is within what one trial moves. The gate is this repository's relay in front of the engine, not part of TensorFold ([setup §6](../SETUP.md#6-tool-argument-gate-optional)), so these scores and the Safety Gate are the engine's behind it. Without the gate, the same invocation straight to the engine on 3.8.0's image gave 93 at TP=2 and 91 at TP=3, the Safety Gate passed, failing TC-43 as well at both sizes: a `web_search` call with an empty `query`, which through the gate becomes a refusal to call it without one.

## Stopping a reply

**Accepted when**, at both TP sizes, with thinking off: a streamed request to write the numbers from 1 to 1,000, cut by the client after about 5 s, leaves no connection in `/health`'s `live` block within 15 s, and a short request right after answers within 10 s; the same request with the stop string `"\n300\n"` ends at 299 with `finish_reason` `stop`; a ledger prompt of about 93,000 tokens cut by the client after 3 s, while it is read, lets a short request right after answer in less than half the time the whole prompt takes to its first token. Reference: after the cut prompt a short request answered in 0.32 s at TP=2 and 0.94 s at TP=3, against 68.5 s and 57.1 s to the whole prompt's first token. At TP=3 the stop string's request runs to its limit, a known behaviour ([XSFP4](#xsfp4)).

## Long runs of replies

Forty requests back to back, each a fresh nonce and a module of about 6,000 tokens of Python with a request for a detailed review, up to 1,024 tokens each, temperature 0, effort low. This is the load that heated the CPU's zones on every core ([why the efficiency cores](../README.md#serving-defaults)). **Accepted when** all forty answer and the thermal watch does not stop an engine.

Reference: forty of forty at both TP sizes, in 1,248.8 s at TP=2 and 989.8 s at TP=3, rank 0's host at 75.9 °C and 86.0 °C at the hottest. On every core forty such replies at TP=2 (NVIDIA's NVFP4, 3.1.0) finished with rank 0's host at 93.0 °C, 1 °C under the thermal watch's stop ([why the efficiency cores](../README.md#serving-defaults)).

## Memory and temperature

The memory guard's log (`<WORK>/logs/hostwatch-<label>.log`) gives each host's lowest `MemAvailable` during the run; the hosts' telemetry gives the hottest ACPI zone every 2 s. Rank 0's log gives each prefill heat wait's seconds in a `heat_wait_s` line; the reply does not carry them.

Reference: the lowest `MemAvailable` of a launch was 11 and 12 GiB on ranks 0 and 1 at TP=2 and 21, 23 and 28 GiB on ranks 0, 1 and 2 at TP=3; the hottest zone of a whole launch was 87.9 and 88.9 °C at TP=2 and 92.4, 89.9 and 87.9 °C at TP=3, during the 1M-token prompt, the only request that waited for heat ([long inputs](#long-inputs)).

**Accepted when** no run is stopped by the memory guard or the thermal watch (two readings in a row at or above 94 °C).

## XSFP4

The reference values above are XSFP4's ([checkpoints](../README.md#checkpoints)): its decode-check hashes, edit reply and NLL, set in 3.3.0's acceptance on 2026-10-22, which 3.8.0's acceptance on 2026-10-26 gave again (the hashes and the edit reply in two launches at each TP size, the NLL in the first), and that acceptance's other figures. 3.8.0's acceptance read the published revision, whose routed experts of layers 3 to 44 store their block scales compressed losslessly; 3.3.0's read one with the same tensors and plain block scales. `score-nll` takes XSFP4's own `tokenizer.json` (byte for byte NVIDIA's NVFP4's). The speeds belong to this checkpoint and compare only with themselves ([checkpoints](../README.md#checkpoints)).

With `PARALLEL=` empty the engine took three streams at TP=2's 245,760-token window and one at its 524,288, and at TP=3, on KV pages, eight; each gave the count hash of its TP size. After every TP=3 launch each of rank 0's `kv pool idle` lines had every page free. Drafted equalled serial, a picture's included; an H.264 and a VP9 clip answered the same drafted and with `"draft": false`, and a GIF and an audio part were refused with 400. No request waited for heat at TP=2; at TP=3 only the 1,035,295-token prompt did, in 15 pauses of 2 s.

**Known behaviours at TP=3.** The stop string's request of [stopping a reply](#stopping-a-reply) runs to its 4,000-token limit: the count falls into a loop before 300, as on upstream 1.1.1 and again on 1.1.5 (the cut reply and the cut prompt pass). The request without scores or a grammar of [prompt scores and structured output](#prompt-scores-and-structured-output) ends " Paris. In French, Paris is spelled" where NVIDIA's NVFP4 ended "… pronounced"; its hash is the value above. Both are known behaviours ([3.3.0's measurements](measurements.md#330)), not reasons to stop the acceptance.
