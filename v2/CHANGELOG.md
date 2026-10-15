# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 2.x line, served by TensorFold. A `v2.*` tag publishes its section from this file. The 1.x line's history is in [v1/CHANGELOG.md](../v1/CHANGELOG.md).

## 2.9.3 — 2026-10-16

### Changed

- `bench` runs `--warmup` prefill requests of the prompt's length before the counted ones (default 1) and reports their rates as the summary's `warmup`, outside the median and `--out`; `--warmup 0` runs none. The first prompt of many chunks that a container serves compiles Triton kernels on its way: in the release windows from 2.2.0 to 2.9.2 the first of the two counted prompts took 0.4-1.8 s longer than the second at TP=2 and 0.8-1.6 s at TP=3 in all but two launches, the slower of the two speeds [validation](docs/validation.md#prefill-and-decode-speed) described.

### Documentation

- The rank file examples set `TRITON_CACHE_DIR=/work/triton-cache`, and the README's table of settings names it: Triton's compiled kernels then outlive the container, and a container made again from an image whose kernels did not change compiles none (none did in such a container at TP=2, at its start or in four prompts).
- [Validation](docs/validation.md#prefill-and-decode-speed)'s prefill paragraph keeps the references, the measurement and the verdict: the first prompt's compiles as the cause of its slower speed, measured on 2026-10-16 at TP=2 (29.03-29.04 s a prompt with the kernels compiled, 34.12 s for the first without them), and the rarer slowdown of a whole prompt as open. [Benchmarks](docs/benchmarks.md#prefill-and-decode-speed) says the 3,000-token warm-up does not reach every kernel a 38,960-token prompt compiles.

No file of the image changes; it stays 2.9.2's (linux/arm64 `sha256:cb25e8db168fc18928d37c923a7e3da5e15b75d576c9cb318d429db15f21dc74`).

## 2.9.2 — 2026-10-15

### Engine

- The image builds TensorFold from the branch `release/2.9.2` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `7bf0aa3e4ec2b8f7e774e1d3d7985336b41410dc` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.9.1's engine with one change:
  - The prefill's heat look-ahead (`TF_GLM_HEAT_CEILING`) judges the next chunk by the last rise of a chunk run straight after another, kept across waits and prompts, where 2.9.1 took the last chunk's rise. A chunk begun after a rest (a wait, or the gap before a prompt) also climbs back the few seconds' cooling, about 15 °C, and 2.9.1 counted that climb: once a prompt waited, it waited before each later chunk. A wait still ends where the larger of the two rises stays within the ceiling; the wait changes when chunks run, never their bits. Measured before the release on 2.9.1's image with the two changed files, against 2.9.1's engine at the default bands: a 70,000-token prompt after a 6 s rest at TP=2 took 59.9 s against 93.8 s, and the 1M-token prompt at TP=3 gave its first token in 1,337.9 s against 1,644.1 s, with the same reply. In that prompt the engine read up to 93.7 °C at a check (2.9.1's engine: 92.7 °C) and the thermal watch never read 94 °C ([decisions](docs/decisions.md#heat)).

The image is `glm53-tf:2.9.2` (linux/arm64 `sha256:cb25e8db168fc18928d37c923a7e3da5e15b75d576c9cb318d429db15f21dc74`).

### Documentation

- The serving defaults, [operations](docs/operations.md), [validation](docs/validation.md) and `serve.sh`'s comments describe the look-ahead by the rise of the last chunk run straight after another, and say that a chunk can still pass the ceiling (once in 2.4.0's acceptance, nine times in 2.9.2's 1M-token check, up to 93.7 °C).
- [Host tools](../host/README.md#during-long-runs): the thermal watch's record names 95.0 °C (2026-10-15, at or above 94 °C twice, never twice in a row) as the highest reading that ended without a power-off, and says the engine's heat wait covers prefill only, leaving decode's heat to the watch.

### Accepted

On the reference hosts on 2026-10-15 with image input on, with the release candidate image (linux/arm64 `sha256:cb25e8db168fc18928d37c923a7e3da5e15b75d576c9cb318d429db15f21dc74`, the same on the three hosts), on the pinned weights at TP=2 and TP=3:

- The decode check gave 2.9.1's token ids and acceptance lengths in both launches; `bench --kinds decode` gave 2.9.1's replies and `bench --kinds edit` the reference reply (`ecd7a283a48a0cc4`). The image checks passed.
- Two 38,960-token prompts back to back took 30.47 / 28.93 s at TP=2 with no heat wait in the launch, and 23.81 / 22.95 s at TP=3 with no heat wait.
- A prompt cut by its client 3 s into its prefill: the next request was answered 2.06 s after the cut at TP=2 and 1.07 s at TP=3.
- Not run in this window, because the engine's bits are 2.9.1's (the same decode-check ids and edit reply here, the same 1M-token reply before it): AXL, the NLL set and tool-eval-bench. 2.9.1's results stand.

## 2.9.1 — 2026-10-15

### Changed

- The image moves to NVIDIA's PyTorch container 26.09-py3, pinned by its index digest (`nvcr.io/nvidia/pytorch@sha256:6e8ccc607fc2a51e3741667b86316a0889418ba8b78ed0ba96e8d282b648a7a6`): PyTorch 2.14.0a0 and CUDA 13.4, where 26.07 had 2.13.0a0 and 13.3. Triton stays at 3.7.1, the version 2.0.0 to 2.9.0 ran, in place of the base's 3.8.0: with 3.8.0 the engine's sums change (the tiny model's bit checks gave other hashes for 26 of 48 states and one other token), and with 3.7.1 on the new base every hash is 2.9.0's ([decisions](docs/decisions.md)). The engine is 2.9.0's, `release/2.9.0` at `d2dd932a2da15478b85d4b0bd5f60a4bae61599c`.
- The reference hosts run DGX OS 7.6.0: kernel `7.0.0-1019-nvidia` booted with `kho=off`, driver 580.178.04 ([host preparation](../docs/hosts.md)). 2.9.0 and earlier were measured on `6.17.0-1032-nvidia` with 580.173.02.

The image is `glm53-tf:2.9.1` (linux/arm64 `sha256:b5ad2aff993b211edcb1792bd3a6579823819aab506e967ebad247551a58cc9f`).

### Accepted

On the reference hosts on 2026-10-15, on the new kernel and driver, with image input on, with the release candidate image (linux/arm64 `sha256:b5ad2aff993b211edcb1792bd3a6579823819aab506e967ebad247551a58cc9f`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- The decode check gave 2.9.0's token ids and acceptance lengths in all four launches; `bench --kinds decode` gave 2.9.0's replies and `bench --kinds edit` the reference reply (`ecd7a283a48a0cc4`).
- The NLL set at TP=2 equalled 2.9.0's on both weights; tool-eval-bench at TP=2 gave pinned 92 / 93 and AXL 89 / 91, failing the Safety Gate directly on TC-43 and passing it through the gate, as on 2.9.0. Pinned, TP=2 and TP=3: the image checks passed. `top_k` 0 (pinned, TP=2): every reply's tokens equal the host rule.
- A prompt cut by its client 3 s into its prefill: the next request was answered 2.09 s after the cut at TP=2 and 1.08 s at TP=3.
- Not run in this window: as on 2.9.0.
- Before the window, on 03, with the engine at `d2dd932`: the tiny model's bit checks gave 2.9.0's hashes in BF16 and FP8, and the brief set 1,544 passed (42 skipped).

## 2.9.0 — 2026-10-11

### Engine

- The image builds TensorFold from the branch `release/2.9.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `d2dd932a2da15478b85d4b0bd5f60a4bae61599c` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.8.0's engine with these:
  - A prompt whose client left stops after the chunk being filled, on every rank: after each chunk but the last, the ranks all-gather one int32 each and stop together when any of them wishes, the caches keeping the rows already filled, and the request ends as cancelled. Before it, both ranks filled a prompt to its end after its client left. A prompt that is not stopped computes the same bits. `TF_GLM_PROMPT_STOP=0`, the same on every rank, fills every prompt to its end ([decisions](docs/decisions.md#prefill)). After MiaAI-Lab's patch 0109-glm-prompt-stop (branch `tp4`, Apache-2.0), itself after upstream TensorFold's prompt stop at chunk boundaries.
  - The server tokenizes through the tokenizer's batch call, which releases Python's GIL, so a long request's tokenization no longer stops the server's other threads; the ids are the same. After MiaAI-Lab's patch 0099-glm-tokenize-nogil (Apache-2.0).

The image is `glm53-tf:2.9.0` (linux/arm64 `sha256:1f811b00bb30a756ac342a05905f57832f6a2d555b7dd6f72dbf408dcf67d567`).

### Accepted

On the reference hosts on 2026-10-11 with image input on, with the release candidate image (linux/arm64 `sha256:1f811b00bb30a756ac342a05905f57832f6a2d555b7dd6f72dbf408dcf67d567`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- The decode check gave 2.8.0's token ids and acceptance lengths in all four launches; `bench --kinds decode` gave 2.8.0's replies and `bench --kinds edit` the reference reply (`ecd7a283a48a0cc4`).
- A prompt cut by its client (pinned weights; about 70,000 tokens, the client gone 3 s into the prefill, then a short request): the short request was answered 2.12 s after the cut at TP=2 and 1.04 s at TP=3, where the same prompt uncut took 54.58 s and 41.92 s to fill.
- `top_k` 0 (pinned, TP=2, 2.8.0's requests): every reply's tokens equal 2.7.0's host rule.
- The NLL set at TP=2 equalled 2.8.0's on both weights; tool-eval-bench at TP=2 gave pinned 92 / 93 and AXL 89 / 91, failing the Safety Gate directly on TC-43 and passing it through the gate, as on 2.8.0. Pinned, TP=2 and TP=3: the image checks passed.
- Not run in this window: as on 2.8.0.
- Before the window, on 03, on the engine at `d2dd932`: the tiny model's bit checks gave 2.8.0's hashes in BF16 and FP8, the brief set 1,544 passed (42 skipped; 2.8.0's 1,528 and the prompt stop's 16) and the tokenizing tests 14, and the GLM tokenizer gave the same ids through the batch call as through `encode` for 1,106 texts (the longest 2.1M tokens), with and without special tokens.

## 2.8.0 — 2026-10-09

### Engine

- The image builds TensorFold from the branch `release/2.8.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `7458b111c9aab673460eedf9f60167d5fa8c925f` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.7.0's engine with these:
  - A request at `top_k` 0 draws on the device instead of falling back to the host's nucleus over the whole vocabulary: a keyed Triton pass scores every token with the host rule's per-position uniform, radix passes over a 64-bit key find each row's `top_p` cut, and the host keeps the best only when it clears every rank's runner-up, running its own rule wherever the draw cannot decide. The tokens are the host rule's. Two commits by sfxnz from sfxnz/TensorFold's `dsv41-recipe-engine4` (Apache-2.0), the continuation of the closed upstream #408, taken as they are. Only a client that asks `top_k: 0` meets it; the server's default is 20 ([decisions](docs/decisions.md#decode)).
  - The engine's `THIRD_PARTY_NOTICES.md` says the loop guard's count is in the reply's `tensorfold` block, where it is, not its usage.

The image is `glm53-tf:2.8.0` (linux/arm64 `sha256:4324f7c0b246935fdee31a1ad3fba1c14f933b17991a58a97dda16898638f92d`).

### Accepted

On the reference hosts on 2026-10-09 and 10 with image input on, with the release candidate image (linux/arm64 `sha256:4324f7c0b246935fdee31a1ad3fba1c14f933b17991a58a97dda16898638f92d`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- The decode check gave 2.7.0's token ids and acceptance lengths in all four launches; `bench --kinds decode` gave 2.7.0's replies and `bench --kinds edit` the reference reply (`ecd7a283a48a0cc4`).
- `top_k` 0 (pinned, TP=2; temperature 1, `top_p` 0.95, seed 7, two prompts, two requests each): every reply's tokens equal those of the same requests on 2.7.0, at 36.80 and 23.98 tok/s against 2.7.0's 12.64 and 8.82; at `top_k` 20 the tokens and rates are 2.7.0's.
- The NLL set at TP=2 equalled 2.7.0's to four places on both weights; tool-eval-bench at TP=2 gave pinned 92 / 93 and AXL 89 / 91, failing the Safety Gate directly on TC-43 and passing it through the gate, as on 2.7.0. Pinned, TP=2 and TP=3: the image checks passed.
- Not run in this window: the NLL set at TP=3, the long inputs, the tool gate at 1M tokens, AXL's prefill and the image checks on AXL, as on 2.7.0.
- Before the window, on 03: the engine's sampling and nucleus tests passed (one MLX-only test cannot run on Linux), the tiny model's bit checks gave 2.7.0's hashes in BF16 and FP8, and the brief set 1,528 passed (42 skipped), as on 2.7.0.

## 2.7.0 — 2026-10-09

### Changed

- **A request that names no reasoning effort gets `high`, not the chat template's `max`.** The pinned chat template renders an unnamed effort as `max`, where the thinking runs on almost without end and takes most of the reply limit; 1.x serves such a request at `high` (`api.default_reasoning_effort`). `serve.sh` passes the engine's `--reasoning-effort high` on rank 0, from `REASONING_EFFORT` in rank 0's file (empty: none, the template's own); a client's own effort still wins. The checks name their own effort, so their reference values stand ([serving defaults](README.md#serving-defaults)).

### Engine

- The image builds TensorFold from the branch `release/2.7.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `9cdd935bba7b6092f7471bc42d88b19b7df8a515` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.5.0's engine with these:
  - A prompt chunk's DSA pool scores take one row and 32 pool blocks a program, loading the row's index queries and head weights once for its blocks, with the same bits. At TP=3 on the pinned weights a prefill of about 226K tokens took 5.8-5.9% less time, heat waits left out ([measured on the release](README.md#measured-on-the-release)). After MiaAI-Lab's patch 0086 (Apache-2.0), rewritten for this tree's FP8 pooled keys and scored columns.
  - `/v1/responses` accepts OpenAI's `include` values and ignores them: each asks for output this server has nothing to add to, and some clients send one by habit. A value OpenAI does not define, or an `include` that is not a list of strings, is still refused with 400. After MiaAI-Lab's patch 0093 (Apache-2.0), rewritten.
  - `TF_GLM_LOOP_GUARD=1` in rank 0's file closes a think block that collapsed into an exact cycle of at most 16 tokens held for 256 tokens, or into one token taking half of the last 256, and counts it as `loop_guard` in the reply's `tensorfold` block. Off by default: no gate is built and no request changes ([decisions](docs/decisions.md#engine)). Taken from MiaAI-Lab's patch 0091 (Apache-2.0), its test rewritten.
  - `MODELS` lists the two NVFP4 checkpoints the CUDA engine reads, the pinned one and the published AXL weights, so `tensorfold models` shows them and pulling or serving one by its repo id no longer prints that it is not a checkpoint TensorFold is tested with.
  - When the ranks' settings differ at start, the refusal names each setting that differs, with rank 0's value and the others'.
  - At start the engine reads the checkpoint's tensor headers once, not twice: the checkpoint's kind for the ranks' comparison is counted from the headers the memory estimate read.
- Also: refactors and tests with the same bits (the E2M1 table and the row alignment held in one place each, one helper for a mixed-precision block's algorithms, the NVFP4 head chosen as every other NVFP4 projection), and the GLM recipe describes the published AXL weights. The engine's `THIRD_PARTY_NOTICES.md` names patches 0086, 0091 and 0093.

### Documentation

- The [README](README.md#configuration) gives `TF_GLM_LOOP_GUARD`, what `/v1/responses` does with `include` and MiaAI-Lab's three patches among [other recipes](README.md#other-recipes-on-tensorfold); [decisions](docs/decisions.md) has the rows for the effort, the pool scores and the loop guard.

The image is `glm53-tf:2.7.0` (linux/arm64 `sha256:7e9fe184cb406f6592f74b4ba3d5d1d11cd4184147283edf84bfc4d3ef9d6dd0`).

### Accepted

On the reference hosts on 2026-10-09 with image input on, with the release candidate image (linux/arm64 `sha256:7e9fe184cb406f6592f74b4ba3d5d1d11cd4184147283edf84bfc4d3ef9d6dd0`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- The decode check gave 2.5.0's token ids in all four launches, with 2.5.0's acceptance lengths: 3.961 / 2.098 / 3.180 (pinned TP=2), 3.813 / 2.004 / 2.893 (AXL TP=2), 4.056 / 2.222 / 3.234 (pinned TP=3) and 3.631 / 2.060 / 2.994 (AXL TP=3).
- `bench --kinds decode` gave 2.5.0's replies: `7754eb09bd6615fd` on both weights at TP=2 and on AXL at TP=3, `27fc79ab52b7830f` on the pinned weights at TP=3; every row stopped at the limit.
- `bench --kinds edit` gave the reference reply (`ecd7a283a48a0cc4`) in all four launches.
- The NLL set at TP=2 equalled 2.5.0's to four places on both weights: pinned 2.5474 / 2.9257 / 1.3184 / 0.6250, AXL 2.5556 / 2.9438 / 1.3334 / 0.6474.
- Pinned, TP=2 and TP=3: the image checks passed.
- tool-eval-bench at TP=2 with the same invocation (69 scenarios): pinned 92 directly and 93 through the tool-argument gate, AXL 89 and 91, failing the Safety Gate directly on TC-43 and passing it through the gate. The same scores and outcome as on 2.5.0.
- Not run in this window: the NLL set at TP=3, the long inputs (262K and 1M tokens), the tool gate at 1M tokens, AXL's prefill and the image checks on AXL; the default path's token ids equal 2.5.0's and 2.4.0's at both TP sizes, so 2.4.0's results stand for this engine.
- Before the window: the old and the new pool scores chose the same tokens with the same counts and read the same score columns in 14 cases (decode windows and prompt chunks, BF16 and FP8, positions 2,047 to 262,144); the engine's brief set 1,528 passed (42 skipped), with the GPU tests of GLM's engine; the selected tests, with the loop guard's and thinking's, 237 passed (8 skipped); the tiny model's bit checks gave the same hashes as without the two patches, in BF16 and FP8.

## 2.6.1 — 2026-10-09

### Changed

- The publication audit (`tools/check_publication.py`, run by CI) reports a public file that names a run directory of the untracked `records/`, which no reader of the repository can open; a public file says what was measured instead. The files that name runs today are listed with their counts: the measured sets' provenance in `config/`, for good, and 1.x's benchmarks, FreedomBench and candidate-order pages and one overlay until they are next rewritten. A listed file above its count, or below it, is reported too, so the list only shrinks.

No file of the image changes; it stays 2.5.0's (linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`).

## 2.6.0 — 2026-10-08

### Changed

- `bench`'s summary leaves an edit reply cut at its 4,096-token limit (`finish_reason` `length`) out of the edit median, and its new `cut` counts such rows by kind. The row is still printed and written, and `all` keeps its rate. Before, a cut reply, which [benchmarks](docs/benchmarks.md) already said does not measure an edit, went into the median.
- `verify-download` on a host whose `state/` holds no download status (a copied cache that `download` has not registered) records `no download status` in `checksum-status.json`, prints the `download` command to run and exits 1, instead of stopping on `FileNotFoundError`; [SETUP](SETUP.md#2-checkout-and-checkpoint) says to run `download` once after a copy.

No file of the image changes; it stays 2.5.0's (linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`).

## 2.5.1 — 2026-10-08

### Changed

- `config.MODEL` and `config.REVISION` are gone: since 2.4.0 the tools resolve the checkpoint through `checkpoint()`, and only the tests read them. `download` and `verify-download` explain `--checkpoint` in their help. `bench`'s prefill runs through the same table as the other kinds; its rows and requests do not change.
- The example rank files carry a commented `CHECKPOINT` line with the published AXL weights' locked snapshot, which the [README](README.md#configuration) and SETUP tell an operator to add.

### Documentation

- Each 2.x measurement is told once, in the README's [measured on the release](README.md#measured-on-the-release): [decisions](docs/decisions.md) keep the gist of each difference with a link, [validation](docs/validation.md) its criteria and current references, [operations](docs/operations.md) the caution and a link. The 94.4 °C reading of 2.4.0's AXL 1M prompt at TP=3 is described as the acceptance's one-second log, beside the thermal watch's 93.5 °C every 2 s.
- Decisions' reopen conditions follow upstream's freeze of its Python engine (#286) instead of merges that will not come; Next Action's #243 item loses a date that has passed.
- The README's differences from 1.x name the 93 °C look-ahead (`TF_GLM_HEAT_CEILING`) beside the 92/88 °C bands; the reply's `tensorfold` block lists `drafted`, `prefill_s` and `sha256`.
- [SETUP §8](SETUP.md#8-accept) runs validation in its order, from the decode check with `bench --kinds edit`'s reply to memory and temperature; the checkpoint step says how to register a copied cache (`download` once, then `verify-download` without `--wait`), without which `verify-download` stops for want of a download status.
- [Benchmarks](docs/benchmarks.md) say what the long-input targets fitted to (1,035,295 tokens from 2.2.0, 262,113 for AXL at TP=2); `bench`'s docstring says which fields each row keeps; [operations](docs/operations.md) tags the image in use, not the new one, before an image change.
- A test comment cites what was measured, not a local record path.

No file of the image changes; it stays 2.5.0's (linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`).

## 2.5.0 — 2026-10-08

### Changed

- **`bench --kinds decode` sends a new request, a change in what the tool measures: the reply counts until the limit, not past the model's own end.** The request is `Write the numbers from 1 to 1000, one per line, and nothing else.`, streamed, up to 512 tokens without `ignore_eos`, at temperature 0 with the same `chat_template_kwargs`; each row adds `finish_reason` and, from the reply's `tensorfold` block, `rounds`, `tokens_per_round` and the reply's `sha256`. The request before it, `Count upward from one, one number per line.` with `ignore_eos`, let the model end its reply by itself after about 100 tokens; the rest of the 512 was a conversation the model made up past its end, and it differed between the weights (the pinned weights counted on, AXL wrote prose), so the row compared different texts. With the new request every row of the acceptance stopped at the limit (`finish_reason` `length`), and at TP=2 both weights gave the same reply token for token. Its figures do not compare with earlier releases' `bench --kinds decode` ([benchmark method](docs/benchmarks.md#prefill-and-decode-speed)).

### Engine

- The image builds TensorFold from the branch `release/2.5.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `8a36b2cb6449821d6204dcaf28618106e8502b63` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.4.0's engine with these from upstream and its recipes:
  - GLM tool calls whose end token arrived before `</tool_call>` are sent as calls when they parse whole, and a missing `<arg_key>` is put back (TensorFold #285 by MiaAI-Lab).
  - The server raises its open-file soft limit to the hard limit at start and logs once when accepts run out of descriptors (TensorFold #294 by plotarmordev). In the reference containers the shell's soft limit is 1,024 with a hard limit of 524,288; the running engine's soft limit read 524,288.
  - An `<|image|>` quoted in the conversation stays text beside a real picture instead of failing the request with 400 (after MiaAI-Lab's patch 0080, Apache-2.0; a rewrite, no code copied). A conversation that quotes the whole begin/image/end sequence still counts it as an image.
  - GLM's EXL3/TR3 checkpoint is named as `brandonmusic/GLM-5.3-Flash-tr3-4bpw`; Mia-AiLab's withdrawn re-host stays listed so copies pulled under it are still recognized as tested.
- Also: #294's upstream test could fail by timing (the test server closed an accepted socket on its worker thread, sometimes between the test's squeeze and the next accept); the fork's test now closes it in place. The engine's `THIRD_PARTY_NOTICES.md` names patch 0080 beside MiaAI-Lab's other patches and describes copy drafts' cap after a missed round as this tree's `MISS_MOST`.
- On the default path (no image, no tools) the tokens are unchanged: the decode check gave 2.4.0's token ids on both weights at both TP sizes.

### Documentation

- The cause of the 2% that AXL's `bench --kinds decode` ran over the pinned weights' at TP=2 on 2.4.0 is stated where the [README](README.md#measured-on-the-release) and [validation](docs/validation.md#prefill-and-decode-speed) called it unknown: the old request's follow-on conversation. [Validation](docs/validation.md) gives this release's `bench --kinds decode` values and the quoted-`<|image|>` check; [benchmark method](docs/benchmarks.md#prefill-and-decode-speed) the new request; [decisions](docs/decisions.md) has the rows for the request and for the engine's intake.
- The published AXL weights' tool-eval-bench is measured on 2.x (TP=2, below); HLE is still not run on them on 2.x.

### Accepted

On the reference hosts on 2026-10-08 with image input on, with the release candidate image (linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- The decode check gave 2.4.0's token ids in all four launches, with acceptance lengths 3.961 / 2.098 / 3.180 (pinned TP=2), 3.813 / 2.004 / 2.893 (AXL TP=2), 4.056 / 2.222 / 3.234 (pinned TP=3) and 3.631 / 2.060 / 2.994 (AXL TP=3).
- `bench --kinds decode` with the new request: every row stopped at the limit (`finish_reason` `length`, 512 tokens). At TP=2 both weights gave the same reply (`7754eb09bd6615fd`), AXL at 57.09 tok/s against the pinned weights' 42.63 (+34%). At TP=3 AXL ran at 76.55 tok/s against the pinned weights' 56.73 (+35%), with the qualification of the next item.
- At TP=3 the pinned weights' reply (`27fc79ab52b7830f`) also counted one number a line until the limit, to 230 where the others reach 234: it thinks for 41 tokens before the count, 11 more than AXL's, so the two TP=3 replies are not the same token for token.
- `bench --kinds edit` gave the reference reply (`ecd7a283a48a0cc4`) in all four launches.
- The NLL set at TP=2 equalled 2.4.0's to four places on both weights: pinned 2.5474 / 2.9257 / 1.3184 / 0.6250, AXL 2.5556 / 2.9438 / 1.3334 / 0.6474.
- Pinned, TP=2 and TP=3: the image checks passed, and a conversation that quotes `<|image|>` beside a real picture answered 200 and read the picture, as did the same request without the quote (2.4.0 refused the quoted one with 400).
- tool-eval-bench at TP=2 with the same invocation as before (69 scenarios): pinned 92 directly and 93 through the tool-argument gate, AXL 89 and 91. Directly both failed the Safety Gate on TC-43 (an empty `query` for `web_search`); through the gate both passed. The same scores and outcome as on 2.4.0.
- Not run in this window: the NLL set at TP=3, the long inputs (262K and 1M tokens), the tool gate at 1M tokens, AXL's prefill and the image checks on AXL. The default path's token ids equal 2.4.0's at both TP sizes, so 2.4.0's NLL at TP=3, long-input and 1M tool-gate results stand for this engine.
- The engine's own tests: the brief set 1,511 passed (42 skipped), with the GPU tests of GLM's engine, EXL3 and vision; the intake and AXL tests 129 passed (3 skipped); the tiny model's bit checks equal their references, in BF16 and FP8.

## 2.4.0 — 2026-10-08

### Added

- **The published AXL weights can be served, as an option; the pinned checkpoint stays the default.** NVFP4 BIZ AXL ([Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16) at revision `bbad98c8f380588c16a2326bf5a2ab7344190b07`, pinned in [`config/axl.lock.json`](config/axl.lock.json)) has the attention projections and `lm_head` repacked to W4A16 NVFP4 and everything else as in the pinned checkpoint: the checkpoint 1.x serves as its published option. `download --checkpoint axl` and `verify-download --checkpoint axl` fetch and verify it, with their state under `state/axl/`, apart from the pinned download's ([setup §2](SETUP.md#2-checkout-and-checkpoint)); `CHECKPOINT` in every rank's rank file serves it ([configuration](README.md#configuration)). At TP=2 the decode check ran at 57.30 / 37.53 / 44.80 tok/s against the pinned weights' 43.80 / 27.54 / 36.01 and `bench --kinds edit` at 74.26 against 58.13, with a higher NLL (2.5556 / 2.9438 / 1.3334 / 0.6474 against 2.5474 / 2.9257 / 1.3184 / 0.6250); its task-level quality was not measured on 2.x ([measured on the release](README.md#measured-on-the-release)).

### Changed

- **Copy drafts no longer cut after a miss** (`MISS_MOST` 3 → 5 in the engine's copy drafts): a round right after a miss drafts up to 5, as the others do. At TP=2 against 3, on edits and on two loads whose copies miss often (the module returned with five renames, 10% of copied drafts missed; unit tests for it, 41%), 5 ran 1.0% faster on edits and renames and the same on the tests, with the same tokens ([decisions](docs/decisions.md#decode)).

### Engine

- The image builds TensorFold from the branch `release/2.4.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `ab8e74161ba807d9a637fee02d19edb932276257` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.3.0's engine with a loader for W4A16 NVFP4 attention and head, and `MISS_MOST` 5. The engine picks the path per tensor from the checkpoint, with no switch: a projection with `weight_scale` loads as an NVFP4 linear layer (the decode lane matmul and the prompt GEMM), and `kv_b` is dequantized to fp32 for the latent path. The ranks' startup agreement includes the checkpoint's kind, so ranks started on different checkpoints refuse to start. The pinned path is unchanged bit for bit.

### Documentation

- [Setup §2](SETUP.md#2-checkout-and-checkpoint) gives the AXL download and its verification, and says how to copy a cache whose files are not in the model's folder: newer Hugging Face hub clients can keep a model's files in a store shared by the whole cache (`hub/blobs/`), with only links in the model's folder (huggingface_hub 1.32.0 on one reference host did; 1.30.0 on the others kept them under the model's own `blobs/`). Copying the model's folder then copies links only, and the next `download` on the receiving host fetches everything from the Internet again, as it did while the AXL weights were copied for this release.
- [Validation](docs/validation.md) gives the AXL weights' reference values beside the pinned ones; [decisions](docs/decisions.md) has the AXL and `MISS_MOST` rows.

### Accepted

On the reference hosts on 2026-10-07 and 08 with image input on, with the release candidate image (linux/arm64 `sha256:7d47fc819ded734e87b0a881b913ee0e5ffa4b866e3d813090c09ff038b145f6`, the same on the three hosts), on the pinned weights and on AXL, at TP=2 and TP=3:

- Pinned, TP=2 and TP=3: the decode check gave 2.3.0's token ids, with counting's acceptance length 3.961 and 4.056; the NLL set gave the reference values; the image checks passed.
- AXL, TP=2 and TP=3: the decode check gave AXL's reference token ids ([validation](docs/validation.md#decode-check)), at TP=2 the same in two launches; the NLL set gave TP=2 2.5556 / 2.9438 / 1.3334 / 0.6474 and TP=3 2.5590 / 2.9471 / 1.3357 / 0.6439.
- `bench --kinds edit` gave the reference reply (`ecd7a283a48a0cc4`) in all four launches, at both TP sizes on both weights.
- Long inputs: three passphrases at 262,113 tokens on AXL at TP=2, 3 of 3; at 1,035,295 tokens at TP=3, 3 of 3 on both weights, first token after 1,588.4 s on the pinned weights and 1,524.1 s on AXL, with 480.5 s and 454.4 s of heat waits.
- The tool gate at 1M tokens on the pinned weights at TP=3: the first call answered 200 after 1,553.3 s (448.4 s of heat waits) with `tool_calls`; the repair's second call answered 200 in 3.6 s from the kept prompt.
- Heat: on the pinned weights the hottest host peaked at 92.6 °C, as with 2.3.0. During AXL's 1M-token prompt at TP=3 one host read 94.4 °C once in the 1 s telemetry (93.5 °C in the thermal watch's 2 s readings), about 4 minutes in, after more than 30 s at 90.5-91 °C: the check before that chunk read below 92 °C with the last chunk's rise near 0, so the look-ahead did not hold it. The next check started a wait, and the later waits allowed for rises of 12-15 °C. The thermal watch did not stop the engine (its rule is two readings in a row at or above 94 °C); the reading was accepted since the wait started within a second.
- The engine's own tests: the brief set 1,461 passed (42 skipped) and the AXL tests 34 passed; the tiny model's bit checks equal 2.3.0's, in BF16 and FP8.

## 2.3.2 — 2026-10-07

### Changed

- Comments only, shared with 1.30.0: `glm53_tf/download.py` names the readers of its status file in words true for both lines' copies, and the tool gate's repair note names the measurement instead of a local record path. No file of the image changes; it stays 2.3.0's (linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`).

## 2.3.1 — 2026-10-07

### Fixed

- The documentation contract test that 2.3.0 added for `TF_GLM_HEAT_CEILING` is formatted as `ruff format` wants it, so the CPU checks pass again (they failed on 2.3.0's commit and tag; the tests themselves passed).

No file of the image changes; it stays 2.3.0's (linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`).

## 2.3.0 — 2026-10-07

### Changed

- **The prefill heat wait also looks one chunk ahead** (`TF_GLM_HEAT_CEILING`, 93 °C by default; the bands stay at 92 °C and 88 °C). Before a chunk the ranks wait while the hottest zone plus the last chunk's rise would pass 93 °C, and the wait ends only when it would not. Near the end of a 1M-token prompt one chunk adds about 7 °C after the check between chunks, so 2.2.0's acceptance read 94.3 °C once; with the look-ahead the hottest host peaked at 92.6 °C. The 1M-token prompt at TP=3 waits longer: its first token came after 1,440.6 s against 1,154.3 s, 350.3 s of it heat waits; the prefill without waits is unchanged ([decisions](docs/decisions.md#heat)). Every rank takes the same value, or the start is refused; empty turns the look-ahead off.

### Engine

- The image builds TensorFold from the branch `release/2.3.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `7410d1d76b4403a209dd2a5617fa85afe1ed1e32` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.2.0's engine with the heat look-ahead and the same tokens. The GLM recipe's NVFP4 section comes from a run on the real weights and loads the visual tower with `--vision`; the third-party notices give `SCORE_RB` as this tree sets it; comments name measurements instead of local record paths; the FP8 row pad, the BF16 split-K partials and the prompt overlap's piece limit are each named once; tests check the formats and settings without a GPU. Copy drafts keep 3 drafts after a miss, measured against 1 and 5 ([decisions](docs/decisions.md#decode)).

### Fixed

- `THIRD_PARTY_NOTICES.md` points the HLE row at `v1/config/hle.lock.json`, where the lock moved with the v1/v2 split.

### Documentation

- The tool-argument gate's body ceiling (64 MiB) and timeout (2,400 s a call) are measured on 2.x: a 1,035,454-token request with one declared tool is 4.1 MB and answered through the gate after 1,494 s at TP=3; a repair's second call resumed the kept prompt in 3.5 s.
- [Validation](docs/validation.md) and [operations](docs/operations.md) give the reason for the look-ahead; [Next Action](README.md#next-action) names a heat check within a chunk as the next step.

### Accepted

On the reference hosts on 2026-10-07 with image input on, with the release candidate image (linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`, the same on the three hosts):

- TP=2 and TP=3: the decode check gave the reference token ids and texts, with counting's acceptance length 3.961 and 4.024; `bench --kinds edit` gave 2.2.0's reply at both sizes; the image checks passed; the NLL set gave the reference values (TP=2 2.5474 / 2.9257 / 1.3184 / 0.6250, TP=3 2.5313 / 2.9001 / 1.3101 / 0.6237).
- TP=3: three passphrases at 1,035,295 tokens, 3 of 3, first token after 1,440.6 s with 350.3 s of heat waits; the hottest ACPI zone peaked at 92.6 °C and no host read 94 °C.
- The tool gate at 1M tokens, as above.
- The engine's own tests: the brief set 1,427 passed; the tiny model's bit checks equal 2.2.0's.

## 2.2.0 — 2026-10-06

### Engine

- The image builds TensorFold from the branch `release/2.2.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `440e631345dd4a1a6762741a73522475df9782ad` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.1.4's engine and decode work that leaves the tokens unchanged ([decisions](docs/decisions.md#decode)):
  - **Copy drafts** (`TF_GLM_COPY_DRAFTS`): when the reply's last tokens occurred earlier, the tokens that followed are drafted ahead of the MTP head and verified like any draft, after MiaAI-Lab's patches 0007 and the first half of 0032. An edit that returns a module whole ran +34% (43.0 → 57.6 tok/s at TP=2), counting +3.6%, other loads within ±0.3%.
  - **KDA decode windows on the three-kernel chain** (`TF_GLM_KDA_DECODE_WIDE`), after MiaAI-Lab's patch 0016c: decode +0.6%.
  - **Per-shape tiles for the BF16 decode matmuls** (`TF_GLM_B16_DECODE_TABLE`), with the K slices counted on fixed 64-wide tiles so that a tile cannot change the sum order: decode +0.9% at TP=2.
  - **No unread copy of the DSA key and value rows** on the latent path: 192 MiB more per rank at TP=2.
  - Each switch defaults to on, `0` turns it off with the same tokens, and a rank given another value is refused at start ([configuration](README.md#configuration)).

### Added

- `python -m glm53_tf bench --kinds edit`: a module returned whole with three named edits, the load where copy drafts work ([benchmark method](docs/benchmarks.md#prefill-and-decode-speed)).

### Documentation

- The README treats the engine as this line's own fork: upstream froze its Python engine (TensorFold issue #286) and answered every issue and pull request of this line on 2026-10-06 ([other recipes](README.md#other-recipes-on-tensorfold)). [Next Action](README.md#next-action) names the Zig port, a further 0.6.x, pull request #243 taken into the release branch, the lossy-cache question (#309, #401) and the heat bands.
- [Validation](docs/validation.md) gives 2.2.0's acceptance lengths and the edit reply, and states the heat check as the thermal watch's rule (two readings in a row at or above 94 °C). The README's reply fields name the copy-draft counters.

### Accepted

On the reference hosts on 2026-10-06 with image input on, with the release candidate image (linux/arm64 `sha256:f2c992676bc399367fd4f23f9d60e8146a05d4e9bd6811ba1ea6e484322b18bd`, the same on the three hosts):

- TP=2 and TP=3: the decode check gave the reference token ids and texts, with counting's acceptance length 3.961 and 4.024; the image checks passed; `bench --kinds edit` gave the same reply at both sizes.
- TP=3: three passphrases at 1,035,295 tokens, 3 of 3, first token after 1,154.3 s with 64.1 s of heat waits. One host read 94.3 °C once for one second near the end; the thermal watch did not stop it, and the prefill without waits matched 2.0.0's.
- The A/B behind each switch: ten launches at TP=2, each switch off alone between launches with all on, every launch with 2.1.4's token ids.
- The engine's own tests: the brief set 1,410 passed; the tiny model's bit checks equal 2.1.4's.

## 2.1.9 — 2026-10-06

### Changed

- The decode check reads TensorFold only. It no longer parses vLLM's `/metrics` counters or reads `/metrics` to tell the engines apart: the acceptance length comes from the replies' `tensorfold` blocks, the kept prompts are pushed out before every sample, and the summary drops `spec_before` and `spec_after`, which were empty on TensorFold. 1.x keeps its own vLLM check.

### Documentation

- [SETUP step 8](SETUP.md#8-accept) says where the acceptance scope and its evidence are, as AGENTS.md says each line's SETUP does. The clock-cap statement stays in the README only. [Validation](docs/validation.md#tools-through-the-tool-argument-gate) says its tool-eval-bench values are the development build's reference and points at the README for each release's score. The README's API list no longer says the decode check reads `/metrics`.

### Tests

- The decode check's tests drop the three vLLM cases, fail on any GET, and check the summary's keys and replies with no block.

The image is unchanged; it stays 2.1.4's.

## 2.1.8 — 2026-10-06

### Documentation

- [Validation](docs/validation.md#image-input) has the image checks, with their criterion (each answered correctly, a video refused with 400); the README's row links them instead of listing them. Validation keeps the acceptance lengths and links each release's speeds.
- The README's Status names the accepted images through their changelog sections and the current one, 2.1.4's, which it had left out. Limits no longer says several images are encoded in one call (each has its own call since 2.1.1), and its memory note links the serving defaults. The heat note and the [benchmark method](docs/benchmarks.md) no longer say prefill slows as a host heats: two speeds about 7.5% apart are not explained by heat ([validation](docs/validation.md#prefill-and-decode-speed)). The 2.1.0 prefill row names its first run (1,221.5 tok/s). The engine description names #421; the settings table names the TP=3 rank files' `NCCL_NET_PLUGIN=none`.

### Tests

- The image tag in the pages' build, inspect and create-container commands is the Dockerfile's, and the README's Status and release measurements name that image's version. The memory guard's floor is quoted from `hostwatch.sh`.

The image is unchanged; it stays 2.1.4's.

## 2.1.7 — 2026-10-06

### Documentation

- [Decisions](docs/decisions.md): the heat bands' row no longer says `serve.sh` keeps them provisional (2.0.7 dropped that), and the 2.0.0 row without image input points to the row that reopened it. The example rank files no longer date their values. The [repository README](../README.md) lists images among this line's inputs. `decode-check` and `score-nll` say what they still share with 1.x's tools.

### Tests

- The publication audit checks that each Japanese page has its English page's headings, table rows and code blocks. This line's copies of 1.x's `download`, `io`, `verify_download` and the tool gate's check and repair are checked to differ only in the package name. CI's required job installs filelock, so this line's download lock test runs there.

The image is unchanged; it stays 2.1.4's.

## 2.1.6 — 2026-10-06

### Fixed

- The [host tools'](../host/README.md#install) `install.sh` restarts the telemetry logger, so a reinstall runs the new program; before, `enable --now` left a running logger on the old one, and 2.1.5's counters appeared only after a manual `systemctl restart gb10-telemetry`. It also reads the last record from the newest day's file: with more than one day of records, `tail -1` over all of them stopped the script before it printed `installed for <user>`. Hosts that reinstalled 2.1.5 and restarted the logger by hand need nothing more.

## 2.1.5 — 2026-10-06

### Added

- `python -m glm53_tf bench`: the prefill and decode speed of [benchmark method](docs/benchmarks.md#prefill-and-decode-speed) (a 38,960-token prompt with a fresh nonce, then 512 tokens after a short fixed prompt), one JSON line per request with the reply's `prefill_s`, `heat_wait_s` and `cached`, and a summary of medians.
- `python -m glm53_tf long-input`: the [long inputs](docs/benchmarks.md#long-inputs), one passphrase in the middle of a ledger or three at one twentieth from the start, the middle and one twentieth from the end, the length set in lines or fitted to a token count with the engine's `/tokenize`; it exits 1 when a passphrase is missing.
- The [host telemetry](../host/README.md#telemetry-record) records the GPU's cumulative clock event counters (`event_counters_us`: SW power cap, sync boost, SW and HW thermal slowdown, HW power brake). On GB10 the power limit and the memory clock read N/A, and an SW power cap that comes and goes between samples shows only there. The existing fields keep their names and order. Reinstall the host tools to pick it up.

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed): on 2.1.4 at TP=2, 22 prompts of 38,960 tokens in two launches, each after a cooling gate, all ran at the faster of the two speeds, and the SW power cap counter did not grow during any of them; it grows only while no engine runs. The cause stays open.
- [Benchmark method](docs/benchmarks.md) names the two commands instead of scripts outside the repository.

### Accepted

On the reference pair on 2026-10-06 at TP=2 with 2.1.4's image (unchanged): `bench` read a 38,961-token prompt at 1,322.0 tok/s and decoded 512 tokens at 35.88 tok/s; `long-input` fitted three passphrases to 59,976 tokens and one passphrase over 800 lines, and the replies held all of them. The new telemetry field read integers on rank 0's host.

## 2.1.4 — 2026-10-06

### Engine

- The image builds TensorFold from the branch `release/2.1.4` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `a265436de869bd596b20a915758de0cc829fb5a0` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.1.1's engine and TensorFold pull request #421 (m-naoki-m), taken before upstream merges it. `_take_over` now decides which kept prompts stay before it copies any, so a new conversation after a long one no longer copies and drops the others first; issue #420 measured that at about 15 GiB per rank. The pull request's tests failed on 2.1.1's engine (3 of 6) and pass on this one, and two upstream tests' fake snapshots gained the `drafter_rows` field the real one has.

### Documentation

- [Operations](docs/operations.md#start-outcomes): a start that refuses the window right after a new image or another engine read the weights, and what to do (the page cache).

### Accepted

Measured on the reference pair on 2026-10-06 at TP=2 with image input on, with the release candidate image (linux/arm64 `sha256:257c69ba7c8586bd8ce5f158e9cf87af6365a78e2b7baa00338d1ac0c0d4a717`, the same on the three hosts):

- The decode check gave 2.1.1's token ids and texts, and the image checks passed.
- Issue #420's scenario: a conversation grown to 247,330 tokens over 11 turns, then one that shares no prefix with it. Through the new conversation `MemAvailable` held at 11–12 GiB on rank 0 and 12–15 GiB on rank 1, and its first request answered in 1.4 s.
- A 200,000×20 image (vLLM #59126's) and a 114,000×28 one were refused with 400 (the decoded pixel limit), and the engine kept serving.
- The engine's own tests: the brief set 1,263 passed; the tiny model's bit checks equal 2.1.1's.

## 2.1.3 — 2026-10-06

### Added

- The decode check and `score-nll` send the server's API key (`Authorization: Bearer`) when `TENSORFOLD_API_KEY` is set where they run, and nothing without it. An engine started with a key, from a `TENSORFOLD_API_KEY` line in rank 0's rank file, refuses every request without it, `/metrics` included; the [Security](README.md#quick-start) note says how to serve beyond loopback with one, and the rank 0 examples carry the line commented out.

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed) corrects 2.1.2: a long prompt runs at one of two speeds about 7.5% apart at the same clocks and temperatures, and three prompts back to back held in two launches but not in a third; heat does not explain it and the cause is not known. The claim that the first long prompt after a start is slower is withdrawn (it was fast in one launch). [Decisions](docs/decisions.md) adds TP=2's comparison of `split` and `gather`: about 5% for `split` in both speeds, the same tokens.
- [Setup](SETUP.md#3-image): the image tag names the last version that changed a file the image copies; a version for documents or host-side tools keeps it.
- [CONTRIBUTING](../CONTRIBUTING.md): the 1.x tests that need CUDA or the pinned vLLM image run on the GPU hosts only.

### Accepted

On the reference pair on 2026-10-06 at TP=2 with 2.1.1's image (unchanged) and a key in rank 0's rank file: `/health` answered 200 without the key; `/v1/models` and `/metrics` answered 401 without it or with a wrong one and 200 with it; the decode check with the key gave 2.1.1's token ids and texts; without it, it stopped at 401. Rank 0's serve and memory-guard logs and the check logs did not contain the key.

## 2.1.2 — 2026-10-05

### Documentation

- [Validation](docs/validation.md#prefill-and-decode-speed) no longer says to cool the hosts because back-to-back prefills slow down: on 2.1.1 three 38,960-token prefills without cooling held their speed at TP=2 and TP=3, with the clocks and CPU frequencies unchanged and below the heat wait. The fall from 1,670 to 1,540 tok/s at TP=3 it quoted, seen while 2.0.0 was accepted, did not come back. It also says to run one long prompt after a start before measuring, since the first is slower.

The image, the scripts and the serving defaults are unchanged, so 2.1.1's image and acceptance stand.

## 2.1.1 — 2026-10-05

### Engine

- The image builds TensorFold from the branch `release/2.1.1` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `1a3fb1789830f4c336179eae21129f21c5abae0f` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.1.0's engine and the fix below.

### Fixed

- A request with several images had them encoded in one call of the image tower, and an image's features then changed with the other images in that call (on the real tower, a 448×448 image beside an 896×672 one gave the first different bits wherever it stood). Each image is now its own tower call, so its features are the same whatever else the request carries.

### Accepted

Measured on the reference hosts on 2026-10-05 at TP=2 with image input on, with the release candidate image (linux/arm64 `sha256:54cf0e5bc7fe56a218a91f704443285caa11f68f5389fa618ef577d7b9fcad67`, the same on the three hosts) ([measured](README.md#measured-on-the-release)):

- The decode check gave 2.1.0's token ids, text hashes and acceptance lengths.
- The image checks passed; two images of one size read the same numbers asked one at a time and together.
- Three 38,960-token prefills back to back, without cooling between them, ran at 1,327.0, 1,326.8 and 1,322.8 tok/s. Through them the GPU clock held 2,184 MHz with no clock event reason, every CPU core held its full frequency, and the hottest ACPI zone rose from 56 to 88.5 °C, below the heat wait.

## 2.1.0 — 2026-10-05

### Engine

- The image builds TensorFold from the branch `release/2.1.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `9a1c7cc9fd231c65ebf5bffaed421937303e0796` ([`TENSORFOLD_REF`](docker/Dockerfile)): 2.0.0's additions moved onto upstream v0.6.5 without a conflict, plus:
  - **Image input** from upstream pull request #194 (rank 0 encodes, the features go to the other ranks), carried to three ranks, with one image up to the checkpoint's 8,000 visual tokens and rank 0's workspace from a measurement of the tower ([decisions](docs/decisions.md#engine-commits-not-named-elsewhere)).
  - The latent path's second copy of `kv_b` (`latent.AbsorbW`, `AbsorbQ4`) counted in the weights' bytes and the startup estimate, which had left it out.
- Upstream v0.6.5 brings API keys (`--api-key`, `--api-key-file`, `TENSORFOLD_API_KEY`); this line sets none ([Quick Start](README.md#quick-start)).

### Serving defaults

- **Image input is on, by a switch in the rank file**: `VISION=1` on every rank, as the examples set it, makes `serve.sh` pass `--vision`; `VISION=0` turns it off. The window is unchanged; at TP=2 rank 0 holds the 1.05 GiB tower and other conversations' kept prompts get 2.4 GiB of the default 3 GiB (TP=3 keeps the 3 GiB).
- **TP=2 opens four NCCL channels and names the IB transport** in its rank files, as TP=3 does: decode +0.8-1.0% and about 1.5 GiB more room at start against the 64 channels NCCL opened on its own, prefill within 0.4%. Pinning the ranks to the performance cores and fixed draft depths were measured and not taken ([decisions](docs/decisions.md)).

### Fixed

- The decode check kept one field of a streamed delta, so when a draft round's chunk ended the reasoning and started the content it dropped the reasoning's tail ("200." read "200"), and its text hash moved with the draft depth while the token ids did not. It keeps both now. Counting and code have new reference hashes for their texts ([validation](docs/validation.md#decode-check)); the token ids are 2.0.0's.

### Accepted

Measured on the reference hosts on 2026-10-05 with the release candidate image (linux/arm64 `sha256:d4d2014ca311841a5ff65c09d97a33abdf2c7db00ba4386dc7ecf7fd689cbb69`, the same on the three hosts) ([measured](README.md#measured-on-the-release)):

- The decode check gave 2.0.0's token ids and acceptance lengths at TP=2 and TP=3, with image input off and on.
- At TP=2 with image input off, the NLL set equalled 2.0.0's at full precision, and three 38,960-token prefills ran at 1,221.5 (the first), 1,331.1 and 1,329.9 tok/s.
- Image input at both TP sizes: one image, a 4:3 image of 7,966 prompt tokens, two images in order, a single colour, an image in a tool result, a text question and a tool round trip answered correctly; a video part was refused with 400.

The other 2.0.0 results stand: the prompt and decode paths give the same tokens. The tag in the commands is `glm53-tf:2.1.0`.

## 2.0.10 — 2026-10-05

### Documentation

- [Decisions](docs/decisions.md) lists LPA among 1.x's measures 2.x has not taken up: 1.x's late-prefill approximation changes a long prefill's result by design, while 2.x's reference hashes and NLL are the exact prefill's.
- The [QSFP network](../docs/qsfp-network.md#8-three-hosts-in-a-ring) page says that its dummy interface `glmhost` is an example name; the reference ring's is `tp3host0`, the name this line's TP=3 rank files give `NCCL_SOCKET_IFNAME`.

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand.

## 2.0.9 — 2026-10-05

### Tests

- The tool-argument gate's test of an oversized body waits for the gate's handler threads to end before it checks that nothing reached the upstream, instead of sleeping 0.3 s; a relay put back 0.5 s late now fails it.

### Changed

- CI installs the check tools from the checkout root's `requirements/dev.lock.txt` (Ruff, one version for every line) rather than from 1.x's lock ([CONTRIBUTING](../CONTRIBUTING.md)).

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand.

## 2.0.8 — 2026-10-05

### Documentation

- The comparison with 1.x said that 1.x handled heat with the cooling gate and the thermal watch. 1.x has no wait in the engine; its measurements rested the hosts between requests with a cooling gate, and no record shows the thermal watch on 1.x.
- The cluster file's `CHECKOUT` is the repository's root on every host, where 1.x's `--checkout` names its `v1/`; the configuration table says so.

### Tests

- The test of a paused download under `--wait` is one test with all its checks; the separate `test_transfer_state.py` repeated it.

The image, the scripts and the serving defaults are unchanged, so 2.0.7's image and acceptance stand (the repository's `.dockerignore` lost lines that admitted nothing more; the build context is the same).

## 2.0.7 — 2026-10-05

### Changed

- The image is rebuilt and accepted again. The Dockerfile pins NVIDIA's base by digest (`nvcr.io/nvidia/pytorch@sha256:2140e699…`, the one 2.0.0 was accepted on) instead of the tag `26.07-py3`; the image carries a changed `THIRD_PARTY_NOTICES.md` (the licensing guide's new place, and that this image carries the file) and a corrected comment in `serve.sh`. The base, the packages and the engine are 2.0.0's, layer for layer. On 2026-10-05 the rebuilt image was accepted on the reference hosts by equivalence: at TP=2 and TP=3 the [decode check](docs/validation.md#decode-check) gave the reference hashes, token ids and acceptance lengths, and the NLL set equalled 2.0.0's at full precision. 2.0.0's other results stand for it. The tag in the commands is `glm53-tf:2.0.7`.
- The host tools moved from `v2/host/` to [`host/`](../host/README.md) at the checkout root, beside the [host preparation](../docs/hosts.md) and fabric pages every line shares: `python3 host/cool-gate`, `python3 host/thermal-watch`, and `sudo sh install.sh` from `host/`.
- The cluster file goes to `state/cluster.env`, which Git ignores; the steps had it at `my-cluster.env` in the checkout root, which Git does not ignore.

### Added

- [Operations](docs/operations.md): how a start ends, a rank that stops while the others wait, NCCL over sockets, recreating the container, moving to a new image, a host that powered off, handing the hosts to 1.x.
- [Decisions](docs/decisions.md): what 2.x adopted or rejected, with the date, the measured effect and what would reopen it; the release branch's commits the changelog does not name; the measures from 1.x not yet evaluated on 2.x.
- [Benchmark method](docs/benchmarks.md): how the release measurements and the validation references were taken.

### Documentation

- [Setup](SETUP.md) §6 and §9 say how `cluster.sh` start ends (READY, FAILED with every rank's log tail, TIMEOUT after 15 minutes), where the logs are, and that stop waits up to 60 s a rank. The README names `TF_GLM_CACHE_GIB` and the endpoints the NLL check uses, and its prefill row says that TP=2's three prompts ran back to back after one cooling.

### Tests

- The pages' quotes of `serve.sh`, the scripts' defaults, the gate's ports, `TENSORFOLD_REF`, the pinned base and revision are tested in both languages; the cluster file stays under `state/`; every shell script must parse. Two checks lost in the copy from 1.x are back (the body score-nll sends, and the decode check's token record read by decode-divergence).

## 2.0.6 — 2026-10-04

### Added

- The publication audit now checks this line too: its required files, a release version with a changelog section in both languages, the Apache-2.0 license and a pinned model revision in `config/model.lock.json`.

### Documentation

- The release measurements describe the engine builds they ran on (the release, the build one printed line before it, a build before the heat wait) instead of naming unreleased commits, and say that without the heat wait the [thermal watch](../host/README.md#during-long-runs) stopped the engine at 94 °C, as recorded. The slowing of prefill as a host heats is stated once, in [validation](docs/validation.md#prefill-and-decode-speed). The 1.x column of the comparison names its sources in 1.x's benchmarks.

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.5 — 2026-10-04

### Changed

- This line runs its own tools: [`glm53_tf`](README.md#repository-layout), run from `v2/` as `python -m glm53_tf download | verify-download | tool-gate | decode-check | decode-divergence | score-nll`, in place of 1.x's tools from `v1/`. They are copies of 1.x's, with the same arguments; the decode check and the tool-argument gate default to this line's engine (`http://127.0.0.1:8095`, model `glm-tf`; the gate listens on 8896). The model pin is `config/model.lock.json`, the NLL set `config/nll_set.json` (a byte copy of 1.x's) and the Hugging Face client lock `requirements/huggingface.lock.txt`; tests keep `scripts/serve.sh`'s revision and the set's hash from drifting. The [setup runbook](SETUP.md) and [validation](docs/validation.md) give the new commands. The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

### Documentation

- [`host/`](../host/README.md) records what was checked on a reference host without sudo (the logger, `cool-gate` in both outcomes, `thermal-watch` stopping a process started in the container) and that `thermal-watch` cannot stop a container's PID 1.
- The repository README says that each line is self-contained and that the root's `tools/` holds the repository's publication audit and release notes.

## 2.0.4 — 2026-10-04

### Fixed

- `host/gb10-telemetry` and the host-tool tests write `datetime.UTC` for UTC, the spelling ruff asks for on Python 3.11 and later; 2.0.3's CI stopped on it. Nothing else changes.

## 2.0.3 — 2026-10-04

### Added

- [`host/`](../host/README.md): the hosts' thermal tools this line was measured with, which lived only in the maintainer's records: the GPU clock-cap unit, the telemetry logger with its unit and installer, `cool-gate` (waits for a host to cool between long requests) and `thermal-watch` (stops the engine after two readings in a row at or above 94 °C). The installer takes the service user as an argument; `thermal-watch` was verified with this line's engine only. Their CPU tests are in `tests/`, and CI runs them.

### Documentation

- The comparison with 1.x cites 1.x's published TP=3 decode check, 51.00 / 30.10 / 39.48 tok/s; 49.59 / 28.32 / 38.33 came from a run with a prefill cap of 512 that no template sets. The 1.x tool-argument gate result is TP=2's, the rows that compare runs of other lengths give 1.x's lengths, and the NLL row names its set.
- What both lines share moved to the [repository README](../README.md). The facts 1.x owns (the clock cap, the checkpoint size per host, the host kernel, the download, the decode check, the repeatability switches) are pointed to instead of restated; [validation](docs/validation.md) keeps the reference values and states the decode check's prompt as `decode_check.py` does.
- The example cluster files name the default clone directory as `CHECKOUT`.

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.2 — 2026-10-04

### Documentation

- [Next Action](README.md#next-action), from a review of upstream and the recipes on 2026-10-04:
  - Upstream reviews pull request #320 for 0.6.6 as the GLM stop on both ranks, not #301, which the release branch carries; either one merged replaces #301. None of this line's issues #308, #309, #310, #339 and pull request #333 is on upstream's list for 0.6.6.
  - Following upstream to v0.6.5 brings API keys to the engine. The security note in [Quick Start](README.md#quick-start) now says that the missing authentication is v0.6.4's.
  - Upstream 0.6.6 is watched for three fixes this line meets: tool-call markup leaking into the reply text, a guard against a token repeated without end, and the open-file limit.
  - Image input reads upstream pull request #194 (GLM-5.3-Flash image input on CUDA over two ranks) before wiring its own.
  - The hosts' CPU-frequency check in 1.x's Next Action applies to this line's figures too.

## 2.0.1 — 2026-10-04

### Documentation

- The [README](README.md) gains the sections a first reader needs; the existing ones are unchanged: a summary with the scope of the acceptance, requirements, a quick start for TP=2 with a `curl` request and a note that the engine has no authentication (rank 0 and the tool-argument gate listen on loopback only), the settings of the rank, cluster and container files in one table, the API the acceptance exercised beside the routes it did not check, the repository layout, licensing at a glance, a disclaimer, Next Action, and local data. Its headings are in title case.
- [Other Recipes on TensorFold](README.md#other-recipes-on-tensorfold): a table that owns the links of the public recipes serving GLM-5.3-Flash on TensorFold and what this line took from each. Upstream TensorFold; MiaAI-Lab's TensorFold recipe (the FP8 latent KV after its patch 0038, the TP=3 shares by the same rule as its patch 0066, its upstream pull request #301); jakejharris/jspark3 v2.0.1, from which nothing was taken. 1.x's table of recipes points here for MiaAI-Lab's TensorFold recipe (1.28.2).

The image, the scripts and the serving defaults are unchanged, so 2.0.0's image and acceptance stand.

## 2.0.0 — 2026-10-04

The first release of the 2.x line. It serves the same pinned checkpoint as 1.x, `nvidia/GLM-5.3-Flash-NVFP4` at `423acf37583782c51c142d145aef733d72943d93`, with [TensorFold](https://github.com/ashhart/TensorFold) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. The 1.x line continues in [`v1/`](../v1/README.md).

### Engine

- The image builds TensorFold from the branch `release/2.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `b44c2f197863f889659874e9be4b8e318768a828` ([`TENSORFOLD_REF`](docker/Dockerfile)). That is upstream v0.6.4 with these additions for GLM-5.3-Flash on CUDA:
  - **NVIDIA's NVFP4 checkpoint read as stored**, W4A16: the routed experts and the dense MLP from its NVFP4 blocks, attention, the shared experts and the head in BF16 (upstream issue #308).
  - **FP8 latent KV** (`TF_GLM_KV=fp8`): the DSA latent cache and the indexer's pooled keys as e4m3 rows (upstream issue #309).
  - **TP=3** (`--tp 3`): one shard plan for two or three ranks, with unequal shares where a size does not divide by three, and vocabulary gathers over shards of unequal width (upstream issue #310).
  - **Prompt work that leaves the bits unchanged.**
    - BF16 prompt matmuls sum their K slices in registers (upstream pull request #333).
    - A prompt chunk's rank exchanges run in row pieces on a second stream.
    - The exchanges use an exact reduce-scatter in which each rank glues only its own rows (`split`, the default where ranks can send to each other).
    - The indexer scores 16 rows a program, scores only the pool columns its selection reads, and reads a long row three times instead of five for its top 512.
  - **A stopped request ends on every rank within a round**, when the client disconnects or a stop string appears (upstream pull request #301).
  - **A long prefill waits for heat.** Before every prompt chunk the ranks share their hottest thermal zone; above `TF_GLM_HEAT_HIGH` every rank waits together until all are at or below `TF_GLM_HEAT_LOW`. The wait moves when a chunk runs, not its bits. Each wait prints a `[tensorfold] heat:` line, and the reply reports `heat_wait_s` (upstream issue #339).

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) sets them on every rank ([serving defaults](README.md#serving-defaults)):

- FP8 latent KV and the checkpoint's MTP head as the drafter (`--drafter none`).
- A window of 300,000 tokens at TP=2, which leaves the default 3 GiB for other conversations' kept prompts, and the largest that fits at TP=3: 1,048,576 tokens, the model's limit, on the reference ring.
- Replies of up to 32,768 tokens when a request names no limit.
- The prefill heat wait at 92 °C, resuming at 88 °C. The hosts' thermal watch stops an engine at 94 °C; without the wait, a 1M-token prompt at TP=3 reached that in six and a half minutes.

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile): NVIDIA's PyTorch container 26.07, transformers 5.18.0, xgrammar 0.2.8 and the Hugging Face hub client, the measured versions, plus the engine at its pinned commit. Build it from the checkout root ([setup](SETUP.md#3-image)).
- [`scripts/`](scripts/):
  - `create_container.sh` and `build_ext.sh`: the container and the engine's CUDA extensions on each host.
  - `serve.sh`: one rank.
  - `cluster.sh`: start and stop every rank from one machine, the other ranks first and rank 0 last.
  - `hostwatch.sh`: a memory guard that stops the engine through its container. The engine runs as root inside it.
- [`examples/`](examples/): the reference hosts' rank files for TP=2 and TP=3: two rails, GID 3, RoCE v2, subnet-aware routing and four channels at TP=3. `NCCL_DEBUG=INFO` makes NCCL log each connection's transport at start.

### Accepted

Measured on the reference hosts on 2026-10-04 ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)). The decode check and the 1M-token prompt were run on the release image (`glm53-tf:2.0.0`, linux/arm64 image `sha256:3d06b02953398603580edcecef22c06c3c8ed0d9e3d1568d66f1bd0d1ae21b44`; the ID that `docker images` shows also covers the build's provenance and changes with each checkout it is built from) or the image one print change before it. The other items were run on the image of `304109c`, the branch before the heat wait, which only changes when prompt chunks run.

- The decode check gives the reference hashes at both TP sizes, also while heat waits were happening.
- Drafted replies equal serial ones.
- The teacher-forced NLL equals the development builds' at full precision.
- At TP=3, three passphrases in 1,036,859 tokens were found with the heat wait on: first token after 1,264.8 s, 170.1 s of it waiting, hottest reading 92.8 °C.
- tool-eval-bench through the tool-argument gate: 93/100 at TP=2 and 91/100 at TP=3, the Safety Gate passed at both.
