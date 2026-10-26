# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 3.x line, served by TensorFold's native engine. A `v3.*` tag publishes its section from this file once the section's heading carries the release date. The 2.x line's history is in [v2/CHANGELOG.md](../v2/CHANGELOG.md).

## 3.8.0 — 2026-10-26

The engine moves onto upstream TensorFold 1.1.5 itself, upstream's first release with this line's pull requests, so the release branch carries no commit of this line's. At TP=3 the KV cache moves onto pages and rank 0's NCCL id reaches the other ranks over their lines, and `clear_thinking` reaches the chat template. The documents' measured values are 3.8.0's acceptance's.

### Engine

- The fork's branch `release/3.8.0` is upstream v1.1.5 (`84e0d560`) with no commit added. Upstream took this line's pull requests into its main on 2026-10-25: #1050, the loader of NVIDIA's GLM-5.3-Flash-FP4-Local and XSFP4 that rode 3.6.0's release branch; #1163 and #1211, KV pages for GLM; and #1178, rank 0's NCCL id over the ranks' liveness lines (upstream had closed its TP bootstrap, #636). Zig, xgrammar and the media libraries stay at 3.6.0's versions, which 1.1.5 pins too.
- At TP=3 every stream's KV cache and the engine's own sequence take pages of one pool, the engine's default at three ranks (`TF_KV_PAGES` unset or `auto`); TP=2 keeps a window per stream. Rank 0's load line names the pages, and its model figure no longer holds the engine's own sequence ([checkpoints](README.md#checkpoints)). `TF_KV_PAGES=off` in every rank file keeps the windows, as up to 3.7.0.
- GLM-5.3's chat template gets `clear_thinking` (upstream's `c767bd766`): false, true with `TF_GLM_CLEAR_THINKING=1` in rank 0's file, and a request's `chat_template_kwargs.clear_thinking` for that request. XSFP4's template takes an unset value as false, so a request that names none renders as before.

### Image and launch

- `serve.sh` no longer sets `TF_GLM_NCCL_ID_FILE`, and `cluster.sh` no longer waits for rank 0's `/work/nccl-id` or copies it to the other hosts, so its `FAILED: rank 0 wrote no NCCL id` is gone. Rank 0 makes its NCCL id at `NCCL_COMM_ID` and the other ranks take it over their lines; a rank other than 0 whose file names `NCCL_SOCKET_IFNAME`, as every example's does, drops `NCCL_COMM_ID` before NCCL's first call. TP=2's rank 1 bootstraps that way too.
- The TP=3 rank files trade their commented `ID_FILE` line for a commented `TF_KV_PAGES=off`.
- `config/engine.lock.json` and the Dockerfile's `ENGINE_REF` pin `release/3.8.0` at `84e0d560`, upstream 1.1.5.

### Documentation

- The documents' measured values are 3.8.0's acceptance's: [validation](docs/validation.md)'s reference values, whose decode-check hashes, edit reply and NLL stay those 3.3.0's acceptance set, the README's checkpoints, serving defaults, limits and [measured on the release](README.md#measured-on-the-release) (3.8.0's table first, the earlier releases' kept), configuration's `PARALLEL` and setup's start times.
- [Configuration](docs/configuration.md) lists `TF_KV_PAGES`, `TF_GLM_CLEAR_THINKING`, and two settings upstream added on 2026-10-25 that GLM's path reads, `TENSORFOLD_PREFILL_SHARE` and `TF_QMMF_HALF_BELOW`, with what their empty values do. Its NCCL section, setup §1 and §5, operations, decisions and the cheatsheet describe upstream's bootstrap.
- The README's engine line and its differences from 2.x name 1.1.5; its limit on `clear_thinking` and Next Action's items for #1178, #1050 and `clear_thinking` go. Decisions' rows for upstream's releases and TP=3's bootstrap say that 3.8.0's release branch is the tag itself.
- The commands in the README, setup and operations build and name `glm53-tf3:3.8.0`.

### Accepted

On the reference hosts on 2026-10-26, with the release image (`glm53-tf3:3.8.0`) started by its own `serve.sh` and `cluster.sh`, no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores: in two launches at each TP size XSFP4's decode-check hashes and `bench --kinds edit` reply were 3.3.0's, and in the first its NLL and 3.3.0's reply to the 199,307-token prompt, with all three passphrases found in the 499,254-token prompt and, at TP=3, the 1,035,295-token one. With `PARALLEL=` empty the engine took one stream at TP=2's 524,288-token window, three at its 245,760 and, at TP=3 on KV pages, eight, each giving the count hash. tool-eval-bench 2.8.0 gave 95 at TP=2 and 92 at TP=3 through the gate and 93 and 91 without it, 3.6.0's scores with the same scenarios left partial or failed, the Safety Gate passed, and `mojibake` found no broken character. On the same engine NVIDIA's NVFP4 and FP4-Local, like XSFP4, gave 3.3.0's next-token figures against the BF16 weights at both TP sizes ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.8.0

NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them) and log-probabilities of generated tokens ([limits](README.md#limits)).

## 3.7.0 — 2026-10-24

Tools and documents. No file of the image changes; it stays 3.6.0's (`glm53-tf3:3.6.0`, `sha256:cad32a5c50462d4223d16937a83940b5f7a5419ff66278e86e420e46d9fc5083`).

### Tools

- `python -m glm53_tf mojibake`: 1.x's check for broken characters in Japanese and Korean answers ([vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)), against 3.x's engine. It sends 1.x's prompts for answers of at least 400 characters, three in each language, at temperature 0 or sampled (`--temperature`, `--top-p` and `--seed`; answer *i* draws with seed + *i*), counts U+FFFD, lone surrogates and control characters other than line breaks and tabs in the answer and in `reasoning_content`, and keeps the full answers in `--out`. The requests name no reasoning effort, so the engine reasons at `serve.sh`'s default, and `max_tokens` is `serve.sh`'s 32,768, which the reasoning and the answer share; an answer cut at it is therefore inconclusive, where 1.x passes it marked as truncated. Each row keeps its lengths, its completion tokens and the effort and sampling the reply's `tensorfold` block reports. It exits 0 when every answer passes, 1 on a broken character and 2 otherwise ([configuration](docs/configuration.md#tools)).

### Accepted

- On 3.6.0's image, one launch at each TP size: twelve answers each, six at temperature 0 and six sampled (temperature 1.0, top_p 0.95, seeds 42 to 47), none with a broken character, and the decode check's count gave the reference hashes in both launches. The reasoning was empty in 20 of the 24 answers, so its text was hardly exercised ([multibyte output](docs/validation.md#multibyte-output)).

### Documentation

- [Validation](docs/validation.md) gains [multibyte output](docs/validation.md#multibyte-output): the check, its commands, when it is accepted and its reference. The README's status and layout, [configuration](docs/configuration.md#tools)'s tools and the [cheatsheet](docs/cheatsheet.md#checking-a-launch)'s launch checks name it.
- The [cheatsheet](docs/cheatsheet.md) and the README link upstream TensorFold's own recipe for this model on CUDA, [GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md), which upstream took into its main from this line's pull request #1224.

### Repository

- The repository README says what to use on a Mac ([on a Mac](../README.md#on-a-mac)): every line here runs on NVIDIA GB10 systems, and TensorFold serves GLM-5.3-Flash on Macs from its own MLX checkpoints, the 4-bit one on the two Macs its model table qualifies and mixed-width ones on one Mac. 3.x's README points there.

### Not in 3.7.0

NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them), log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.6.1 — 2026-10-24

Documents only. No file of the image changes; it stays 3.6.0's (`glm53-tf3:3.6.0`, `sha256:cad32a5c50462d4223d16937a83940b5f7a5419ff66278e86e420e46d9fc5083`).

### Documentation

- [Configuration](docs/configuration.md), a new page: every setting a deployment reads, from the scripts and from the source of the engine the image pins: the rank file, what `serve.sh` fixes, the engine's flags (what can follow the label and what GLM refuses), the API keys, the engine's environment (what the ranks compare at start and what they do not, `TF_ROCE`, `TF_ROCE_MAX_KB` and `TF_GLM_PREFILL_REDUCE` among it), NCCL, the cluster file, the container, the memory guard, the tools and the locks. The README's configuration section becomes a summary that points to it.
- [Decisions](docs/decisions.md), a new page, as 2.x keeps one: what 3.x chose and did not, with dates, measured effects and what would reopen each, for the engine, the checkpoint, the window and streams, the KV cache, heat, cores, drafts, the fabric and image input, and what 3.x has not evaluated. A reason is given only where one was recorded.
- [Cheatsheet](docs/cheatsheet.md), a new page: what this setup does beyond upstream TensorFold's own recipe, as lines to copy with each one's cost, and two notes for harness clients: images count across the history a client resends, and a 1M-token prompt's first token comes after about 1,000 s at TP=3, past the 700 s stream timeout 1.x's harness notes give ZCode.
- Corrections, checked against the engine's source: the key file is refused when other users can read or write it (0400 passes, as 0600 does), and `TENSORFOLD_API_KEY` in rank 0's file holds keys too; the prompt cache is what the window leaves up to 16 GiB, TP=3's 16.0 GiB being that cap; `REASONING_EFFORT` takes `low` to `xhigh`, and `max` stops the engine at start, though a request may still name it; videos are limited in MiB; the heat ceiling shipped in 3.0.0 as well, where 3.3.0's section names 3.1.0 and 3.2.0 alone; and the efficiency cores' cost of 1 to 3% and about 25 s at start was 3.0.0's engine's.
- [Operations](docs/operations.md) hands the hosts to 1.x as well, whose launch check refuses to start while a 3.x container that only sleeps holds the GPUs; [setup](SETUP.md) §8 points there, and §6 gives the gate's timeout and body limit.
- [Validation](docs/validation.md) says in one paragraph what its checks rest on, and names upstream's own served checks of images, videos and structured output, saying which the acceptance ran. The README links 2.x's table of the other recipes on TensorFold and 1.1.3's runbook section on the efficiency cores. The TP=2 rank file examples no longer quote 2.x's measured effect of four channels as if it were 3.x's.
- Swap, host daemons and a lost peer move from 1.x's operations to [host preparation](../docs/hosts.md), the page every line shares; 3.x's operations links there and says what its ranks do when a host vanishes, read from the engine's source.

### Not in 3.6.1

NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them), log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.6.0 — 2026-10-24

The engine moves onto upstream TensorFold 1.1.3, and 3.x serves XSFP4 alone: NVIDIA's NVFP4 and the published AXL weights leave its choices, and 1.x and 2.x keep them.

### Engine

- The fork's branch `release/3.6.0` (`21778b05`) is upstream v1.1.3 with the code of pull request #1050 (fifteen commits, open upstream) and this line's NCCL id file for TP=3, whose comment now names this line's pull request #1178 (upstream closed its TP bootstrap, #636). From 1.1.3 upstream's own code lets an index name a shard in a folder inside the model folder, so the patch of pull request #1179, carried since 3.3.0, leaves the branch; the other commits change the same lines as 3.5.0's, but for that comment.
- 1.1.3's `zig build grammar` installs `libtfgrammar` beside the native server, in `zig-out/native/lib`, and the image takes it from there. Zig, xgrammar and the media libraries stay at 3.5.0's versions, which 1.1.3 pins too.

### XSFP4 alone

- `download` and `verify-download` take `--checkpoint xsfp4` alone, the default, with its status under `state/xsfp4` as before; `pinned` and `axl` are refused, and `config/model.lock.json` and `config/axl.lock.json` leave the line. `serve.sh`'s comments name XSFP4 alone and its arguments are unchanged: `CHECKPOINT` in the rank files still names another folder, which 3.x's acceptance does not cover.
- The rank file examples drop the commented `CHECKPOINT` line for NVIDIA's NVFP4 and, at TP=2, the 245,760-token window that came with it.
- XSFP4 is pinned at `88736f91`. The hub's revision after `59c49ac9` changes the model card alone (every file's size, blob and LFS sha256 compared, 53 files on both sides), so `serve.sh` loads the same bytes and the snapshot carries the corrected card.
- The publication audit asks each TensorFold line for the lock of the checkpoint it serves (2.x `config/model.lock.json`, 3.x `config/xsfp4.lock.json`), and the cross-line test that the lines pin the same checkpoint covers 1.x and 2.x.

### Image

- `serve.sh` names rank 0's address once for both TP sizes and reads `REASONING_EFFORT` once, with the same arguments as before. Its header says the NCCL id file stays until upstream takes #1178 and that `cluster.sh` copies only the default `/work/nccl-id`, and no longer that TP=3 needs `TF_GLM_MM=0` (upstream 1.1.2 fixed issue #1067).
- The Dockerfile's NCCL comment names no host, and the image carries the repository's `LICENSES/`, which its NOTICE names.

### Documentation

- The 3.x README, setup, operations and validation describe XSFP4 alone. Validation's reference values are XSFP4's, set in 3.3.0's acceptance, in every section; the TP=2 video check against NVIDIA's processor goes with NVIDIA's NVFP4, and 2.x's NLL columns stay as information. The checkpoints section gives NVIDIA's NVFP4's figures on the same engine as a comparison alone.
- Validation's tool-eval-bench reference is 2.8.0's on 3.5.3's image: 95 at TP=2 and 92 at TP=3, the Safety Gate passed. 2.7.0 and 2.8.0 grade many scenarios more strictly than 2.6.1.dev52, which gave XSFP4 93 at both sizes, so scores of different versions do not compare.
- The tool-argument gate is named as this repository's relay, not part of TensorFold, in setup §6, validation and the README, and validation and the README's measurements give tool-eval-bench's scores without it beside those through it.
- The repository README, the document map and the licensing guide name XSFP4 as 3.x's checkpoint. Next Action waits for #1178 for the NCCL id file; #1179's item is met. The commands in the README, setup and operations build and name `glm53-tf3:3.6.0`, and setup's start times are 3.6.0's.

### Accepted

On the reference hosts on 2026-10-24, with the release image (`glm53-tf3:3.6.0`) started by its own `serve.sh` and `cluster.sh`, no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores: in two launches at each TP size XSFP4's decode-check hashes and `bench --kinds edit` reply were 3.3.0's, and in the first its NLL and 3.3.0's reply to the 199,307-token prompt, with all three passphrases found in the 499,254-token prompt and, at TP=3, the 1,035,295-token one; at TP=2 a launch with `PARALLEL=` empty took one stream and gave the count hash. tool-eval-bench 2.8.0 through the gate gave 95 at TP=2 and 92 at TP=3, 3.5.3's image's scores with the same scenarios left partial or failed; without the gate, in one more launch at each size, 93 and 91, the Safety Gate passed and TC-43 failed as well ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.6.0

NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them), log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.5.3 — 2026-10-24

Documents and tools only. No file of the image changes; it stays 3.5.0's (`glm53-tf3:3.5.0`, `sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`).

### Documentation

- [Validation](docs/validation.md): `score-nll`'s example reads XSFP4's `tokenizer.json` (the same file as NVIDIA's NVFP4's), a run passes when every request answered and reports how far a text's two scores moved, the thermal watch takes 3.x's container and process, and the tools run in the container from a checkout under the work directory, the only host directory it mounts besides the cache.
- [README](README.md): rank 0's model size at TP=2 is the 245,760-token window's; at that window NVIDIA's NVFP4 leaves a 1.5 GiB prompt cache to two streams against one stream's 5.2 GiB, and the serving defaults give one stream's 5.1 to 5.2 GiB; the KV row of the serving defaults points to the opt-in FP8 latent cache in the limits; the configuration table gains `VISION` and says `cluster.sh` copies `/work/nccl-id` alone; the layout lists `docker/Dockerfile.build` and `assets/`; the Not validated list links where each item is; and Next Action keeps #1053's measurement open, since the releases after 3.3.0 ran on the efficiency cores.
- [Setup](SETUP.md): `API_KEY_FILE` is rank 0's; the tool-argument gate runs in the container from a checkout under the work directory. [Benchmark method](docs/benchmarks.md): the 499,622-token prompt runs at TP=2 too from 3.5.0.
- The TP=3 rank file examples drop two comments copied from 2.x (its engine's timings for four channels, its TCPStore) and say `cluster.sh` copies the default `ID_FILE` path alone.

### Tools

- No behaviour changes: `agreement.py` drops `TEXTS` and `compare_records`, which no 3.x tool used (`score-nll` passes the NLL set's texts), with their six tests; `tool-gate`'s help names `--timeout`; `bench` and `download` no longer reuse a name another holds.

### Repository

- The [host tools](../host/README.md) give the thermal watch's 3.x command: with its defaults, 2.x's container and process, it finds no engine on a 3.x host and ends at once without a reading. They also name 3.x's own heat wait and list `nccl_probe.py`, and the watch's help says the same.
- The repository README, [licensing](../docs/licensing.md), the host, network and NCCL pages, the document map, `CONTRIBUTING` and `AGENTS.md` name the 3.x line where they named two: images and videos, and the image's libjpeg-turbo, libwebp and FFmpeg (LGPL-2.1-or-later); XSFP4's Open Model Agreement beside the MIT weights; 3.x's setup, rank files and releases on the 7.0 kernel.

### Not in 3.5.3

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.5.2 — 2026-10-24

Documents only. No file of the image changes; it stays 3.5.0's (`glm53-tf3:3.5.0`, `sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`).

### Documentation

- The count's known behaviour in [measured on the release](README.md#measured-on-the-release) is corrected after an fp32 reference and a run on vLLM: its places belong to the checkpoint, not to this engine. Computed in fp32 from the same weights, NVIDIA's NVFP4 itself picks 152 again where generation writes it twice, and vLLM on the same checkpoint leaves the count at the same places about as often. 3.5.1's "It comes from the engine, not the weights" is withdrawn, and the item is now called "A number written twice", as on XSFP4's model card. The measurements are in [TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214).

### Not in 3.5.2

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.5.1 — 2026-10-24

Documents only. No file of the image changes; it stays 3.5.0's (`glm53-tf3:3.5.0`, `sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`).

### Documentation

- The engine's known behaviour in [measured on the release](README.md#measured-on-the-release) is reworded: no single wrong value has been found, and whether it is a bug is asked upstream in [TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214), where 3.4.0 said it looked like one. Neither generation nor the prefill always keeps the count, it happens at TP=3 too, and its places also move with the build.
- The limits give the opt-in FP8 latent cache's one trial at TP=2: one stream fit a 1,048,576-token window and the 1,035,295-token prompt found its three passphrases. `serve.sh` keeps BF16.
- 3.5.0's paragraph adds an A/B of edit's speed on the same image: medians of 82.4 to 82.8 tok/s at both 245,760 and 524,288 tokens.

### Not in 3.5.1

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.5.0 — 2026-10-23

TP=2's default window becomes 524,288 tokens, on 3.4.0's engine.

### Window

- `serve.sh` serves TP=2 with a 524,288-token window when the rank files name no `CONTEXT` (245,760 until 3.4.0); TP=3 keeps 1,048,576 ([serving defaults](README.md#serving-defaults)). 245,760 was set on NVIDIA's NVFP4, the default until 3.3.0, as about the most that fit one stream beside it; XSFP4 takes about 3.9 GiB less on rank 0, and at 524,288 rank 0's load line read one stream of 6.71 GiB and a 5.5 GiB prompt cache.
- NVIDIA's NVFP4 starts at 524,288 too, with a 1.0 GiB prompt cache: the TP=2 rank file examples carry `CONTEXT=245760` right after its `CHECKPOINT` line.
- A second stream no longer fits the default window at TP=2: `PARALLEL=2` needs a smaller window, such as `CONTEXT=245760`, and an empty `PARALLEL=` takes one stream (three on XSFP4 at 245,760).
- The image differs from 3.4.0's in `serve.sh` alone; its engine binary is 3.4.0's byte for byte, and the engine, `d2d95b11`, is published again as the fork's branch `release/3.5.0`.

### Documentation

- The README's checkpoints, serving defaults, configuration, reason for TP=2's window, differences from 2.x and limits, setup's start lines, the benchmark method and validation's long inputs describe the new window, and the steps that choose NVIDIA's NVFP4 (the README, setup §2, operations' change of checkpoint) add its `CONTEXT=245760` at TP=2; validation adds XSFP4's 499,254-token prompt at TP=2. The commands in setup and operations build and name `glm53-tf3:3.5.0`.

### Accepted

On the reference hosts on 2026-10-23 at TP=2, with the release image (`glm53-tf3:3.5.0`) started by its own `serve.sh` and `cluster.sh`, no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores: XSFP4's decode-check hashes, `bench --kinds edit` reply and NLL were 3.3.0's, the 199,307-token prompt gave 3.3.0's reply and the 499,254-token prompt found its three passphrases, with no wait for heat. With `PARALLEL=` empty the engine took one stream and gave the count hash, and NVIDIA's NVFP4 at the default window gave its count hash. TP=3 was not launched again: its engine binary and window are 3.4.0's ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.5.0

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.4.0 — 2026-10-23

XSFP4 becomes the default checkpoint, on 3.3.0's engine, and the repository takes its new name, GLM-5.3-Flash-DGX-Sparks-BIZ, with the short name GLM-5.3-Flash BIZ. NVIDIA's NVFP4 checkpoint stays a choice.

### XSFP4 the default

- `serve.sh` serves XSFP4 at the revision in [`config/xsfp4.lock.json`](config/xsfp4.lock.json) when the rank files name no `CHECKPOINT`, and `download` and `verify-download` take it when no `--checkpoint` is given ([checkpoints](README.md#checkpoints)). NVIDIA's NVFP4 checkpoint is `--checkpoint pinned` and `CHECKPOINT` in every rank file, a line the rank file examples carry as a comment. Each download keeps its status where it did (`state/xsfp4`, `state`), and the setup verifies XSFP4 into `../records/checksum-xsfp4`.
- XSFP4 is pinned at `59c49ac9`. The hub's two commits on top of 3.3.0's `dbcb7b65` change only the model card: the repository's new name, XSFP4 as the 3.x line's recommended checkpoint, its speeds as measured for 3.3.0 and the number written twice as the engine's; every other file is the same blob, checked file by file. The published AXL weights are pinned at `c0232adb`, whose card has the new name; 2.x's AXL lock keeps `bbad98c8`.
- The image's inputs differ from 3.3.0's only in `serve.sh`'s default and the notices. The engine is 3.3.0's, `d2d95b11`, published again as the fork's branch `release/3.4.0`; built again from that commit, its binary differs from 3.3.0's byte for byte and gave 3.3.0's answers.

### Name

- The repository is `Bizuayeu/GLM-5.3-Flash-DGX-Sparks-BIZ` from 2026-10-23, and GitHub forwards the old name. Every line's documents, NOTICE, the cluster examples' `CHECKOUT`, the tools' docstrings and the LPA projector's Release URLs use the new name; 1.x's setup code and examples and the changelogs' past sections stay as written.
- The stack's short name is GLM-5.3-Flash BIZ in every line's README and in the citation the publication audit checks; the published AXL weights keep the name NVFP4 BIZ AXL.
- New banners for the repository and for the 3.x line, the latter as lossless WebP.

### Documentation

- The documents call NVIDIA's checkpoint NVIDIA's NVFP4 and name XSFP4 the default: the README's checkpoints (XSFP4 first), serving defaults and configuration, setup §2, operations' change of checkpoint, validation (whose XSFP4 values are the default's), the licensing guide and the repository README's licensing table.
- Figures and reference values measured on NVIDIA's NVFP4 say so: validation's tables before XSFP4's, the reason for TP=2's window, the limits' streams and setup's start times, beside XSFP4's where they were measured.
- A number counted twice token by token is now described as the engine's, not as XSFP4's and FP4-Local's: NVIDIA's NVFP4, generated from the start at TP=2, writes 152 twice, past the 150 numbers 3.3.0's checks read, with the same tokens on upstream 1.1.1's own binary. It looks like an engine bug, reported upstream as TensorFold #1214 ([measured on the release](README.md#measured-on-the-release), the XSFP4 model card).
- The third-party notices list the XSFP4 checkpoint.
- The limits name both checkpoints' chat templates, which both take a missing `clear_thinking` as false.
- The limits name the engine's opt-in FP8 latent cache (`--kv-cache fp8`), pending upstream and not validated on this line.

### Accepted

On the reference hosts on 2026-10-23, with the release image (`glm53-tf3:3.4.0`) started by its own `serve.sh` and `cluster.sh`, no `CHECKPOINT` in the rank files and every container on the efficiency cores, one launch at each TP size: XSFP4's decode-check hashes, `bench --kinds edit` reply and NLL were 3.3.0's at TP=2 and TP=3, and rank 0's load line read the same model size ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.4.0

The published AXL weights (their lock moved for the card's new name alone), log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.3.0 — 2026-10-23

A second checkpoint to choose, XSFP4, on upstream 1.1.2, and the heat wait by the band alone. NVIDIA's pinned checkpoint stays the default; on it the TP=2 text path is 3.2.0's, and TP=3 runs on upstream's tiled BF16 linears, which give other tokens than 3.2.0's glue kernels.

### XSFP4 checkpoint

- [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4), pinned in [`config/xsfp4.lock.json`](config/xsfp4.lock.json): a derivative of NVIDIA's `GLM-5.3-Flash-FP4-Local` (revision `76348ddb`) whose routed experts (layers 3 to 44) and the MTP layer's experts were requantized from Z.AI's BF16 weights as XSFP4, NVFP4 blocks fitted again with a smoothing folded into the weights; every other tensor is FP4-Local's as stored. As in FP4-Local, the routed experts' block scales of layers 3 to 44 are compressed losslessly (`csf_32x2_v1`), 178 GB in all, and the engine restores them at load, so the GPU memory and the speed are those of plain scales. NVIDIA Open Model Agreement ([checkpoints](README.md#checkpoints)).
- `download` and `verify-download` take `--checkpoint xsfp4`, the download's status kept under `state/xsfp4`; a rank file serves it with `CHECKPOINT` set to its snapshot, the same on every rank. The rank file examples carry the line as a comment.
- At TP=2 the model takes 93.44 GiB on rank 0 (97.38 on the pinned checkpoint), which leaves an 8.9 GiB prompt cache beside the 245,760-token window (5.2 GiB), and with `PARALLEL=` empty the engine took three streams (two).

### Engine

- `release/3.3.0` of the fork, `d2d95b11`: upstream 1.1.2 with the code of upstream pull request #1050 (fifteen commits; the pull request is open upstream), which loads FP4-Local's formats as stored (each projection's format from the `MIXED_PRECISION` recipe, MXFP8 and 128×128-block FP8 projections on the engine's quantized linears, FP4-Local's compressed expert scales, float32 norm weights kept float32); the patch of upstream pull request #1179, merged after 1.1.2, without which 1.1.2 refuses FP4-Local's and XSFP4's indexes (214 of their tensors are in a shard inside a folder); and this line's NCCL id file for TP=3. The pinned checkpoint loads as before.
- Upstream 1.1.2 runs a TP=3 rank's KDA input projections untiled (issue #1067), so TP=3 serves on upstream's default BF16 linears and the TP=3 rank files no longer set `TF_GLM_MM=0`; TP=3's decode-check hashes and NLL move with it ([validation](docs/validation.md)). In 1.1.2 the waiting ranks also sleep while rank 0 has no stream (#1053).
- No heat ceiling: 3.1.0 and 3.2.0 also paused a prompt when the hottest zone plus the last chunk's rise would pass 93 °C (`TF_HEAT_CEILING`); 3.3.0's engine waits by the band alone, above 92 °C until 88 °C, and `serve.sh` no longer sets a ceiling.

### Documentation

- The README describes both checkpoints and how to choose ([checkpoints](README.md#checkpoints)); setup §2 downloads XSFP4, operations changes the checkpoint, and [validation](docs/validation.md) gives XSFP4's own reference values.
- The [licensing guide](../docs/licensing.md) and the repository README's licensing table add the XSFP4 checkpoint and the NVIDIA Open Model Agreement.

### Accepted

On the reference hosts on 2026-10-22 and 23, with the vision tower loaded, `TF_GLM_MM` unset and every container on the efficiency cores, five launches on each checkpoint (three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3): on XSFP4 with the release image (`glm53-tf3:3.3.0`) started by its own `serve.sh`; on the pinned checkpoint with the image one engine commit before it, and one more launch at each TP size with the release image ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)):

- Pinned checkpoint: at TP=2 the decode check gave 3.1.0's hashes in both launches and `bench --kinds edit` 3.1.0's reply in 190 rounds. At TP=3, on the tiled kernels, the decode check gave new hashes in both launches, now TP=3's reference values, and the edit reply stayed 3.1.0's. The release image gave the same hashes, edit reply and NLL at both TP sizes, and in one more launch with `TF_GLM_MM=0` the engine gave 3.1.0's TP=3 hashes, edit reply and NLL.
- XSFP4: the decode check gave its own hashes in both launches of each TP size, which set its reference values, and `bench --kinds edit` the pinned checkpoint's reply in 190 rounds. These launches read a revision with the same tensors and plain block scales, no longer on the hub; the published revision gave the same decode-check hashes, edit reply, NLL and model size on rank 0 in one more launch at each TP size.
- Drafted replies equalled serial ones, a picture's included. PNG, JPEG and WebP pictures and an H.264 and a VP9 video answered, each the same drafted and with `"draft": false`, and a GIF and an audio part were refused with 400.
- `prompt_logprobs` and structured output passed their checks, but for XSFP4's plain request at TP=3, which has its own reply; the NLL set was scored twice with no movement.
- tool-eval-bench through the tool-argument gate, with the Safety Gate passed: 92 and 95 on the pinned checkpoint at TP=2 and TP=3, 93 and 93 on XSFP4.
- Forty replies of up to 1,024 tokens after 6,000-token prompts, back to back, finished in every launch that ran them, the hottest zone at most 85.8 °C. The 1,035,295-token prompts (3 of 3) gave their first token after 1,064.9 s on the pinned checkpoint and 1,015.7 s on XSFP4, 38 s and 42 s of it waiting for heat; no other request waited.
- A cut reply, a stop string and a cut prompt stopped the work at both TP sizes on the pinned checkpoint and at TP=2 on XSFP4. On XSFP4 at TP=3 the stop string's request ran to its 4,000-token limit, as on upstream 1.1.1: the count falls into a loop before 300.
- The lowest `MemAvailable` was 11 GiB at TP=2 and 18 GiB at TP=3, and no zone reached the thermal watch's stop.

The known behaviours, XSFP4's at TP=3 and a number counted twice token by token, are in [measured on the release](README.md#measured-on-the-release).

### Not in 3.3.0

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.2.0 — 2026-10-20

Image and video input. The engine, the checkpoint and the text path are 3.1.0's; the serving defaults add the engine's `--vision`.

### Image and video input

- `serve.sh` starts every rank with `--vision` unless the rank file sets an empty `VISION=`: the checkpoint's vision tower is loaded on rank 0, and chat requests may carry `image_url` parts (PNG, JPEG and WebP data URLs, in user messages and tool results) and `video_url` parts (data URLs in user messages: H.264, HEVC, VP8, VP9 and MPEG-4 Part 2 in MP4, QuickTime, Matroska or WebM). The limits are the engine's defaults: 4 images a request, counting every image the submitted history holds, sharing 4,096 image tokens, 2 videos and 16,384 video tokens a request, sampled at 2 frames a second up to 256 frames ([limits](README.md#limits)). Public HTTPS URLs stay off (`--vision-urls`, which a rank file can add).
- The image builds the libraries the engine opens at the first such input, at the releases it checks by version: libjpeg-turbo 3.1.4.1 (TurboJPEG) for JPEG, libwebp 1.6.0's decoder for WebP, and the engine's `libtfvideo.so` over FFmpeg 9.0.2, built static with the engine's decoder-only configuration (LGPL-2.1, no GPL parts). [`config/engine.lock.json`](config/engine.lock.json) pins each release by URL and SHA-256, and `/usr/share/doc/tf3/ENGINE` adds each library's SHA-256.
- At TP=2 the model takes 1.27 GiB more on rank 0 with the tower (97.38 GiB against 96.11) and each stream 0.16 GiB more (3.32 against 3.16): the 245,760-token window stays, and the prompt cache is 4.4 to 5.4 GiB on the reference hosts (5.2 to 6.3 GiB with `VISION=`). At TP=3 the model takes 79.30 GiB on rank 0 (78.03) and the stream 13.03 GiB (12.88): the 1,048,576-token window and the 16.0 GiB prompt cache stay.

### Documentation

- The README, setup, operations and validation describe image and video input, its limits and its checks; [validation](docs/validation.md) replaces "image input refused" with the image and video checks.
- [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) and the [licensing guide](../docs/licensing.md) name libjpeg-turbo, libwebp and FFmpeg, with FFmpeg's LGPL terms and the H.264 and HEVC patents for anyone redistributing a built image.

### Accepted

On the reference hosts on 2026-10-20, on the pinned checkpoint, with the release image (`glm53-tf3:3.2.0`) started by its own `serve.sh`, the vision tower loaded, in five launches (three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3), every container on the efficiency cores ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)):

- The decode check gave 3.1.0's hashes in both launches of each TP size, and `bench --kinds edit` 3.1.0's reply in 190 rounds. Drafted replies equalled serial ones, a picture's included. The engine binary was built on another host than 3.1.0's and differs from it byte for byte; the same answers show the builds alike.
- `prompt_logprobs` and structured output passed their checks at both TP sizes; the NLL set was scored twice with no movement, equal to 3.1.0's text by text at both TP sizes.
- tool-eval-bench through the tool-argument gate: 92 at TP=2 and 93 at TP=3, with the Safety Gate passed.
- Forty replies of up to 1,024 tokens after 6,000-token prompts, back to back, finished at both TP sizes with the hottest zone at 75.6 °C (TP=2) and 82.5 °C (TP=3). The 1,035,295-token prompt (3 of 3) gave its first token after 1,056.9 s, 34 s of it waiting for heat in the afternoon; no other request waited.
- A cut reply, a stop string and a cut prompt stopped the work at both TP sizes.
- The lowest `MemAvailable` was 12 GiB at TP=2 (15 GiB in 3.1.0's acceptance) and 22 GiB at TP=3, and no zone reached the thermal watch's stop.

In shorter launches of the same image the same day:

- Images at TP=2: PNG, JPEG and WebP answered, each with the same reply drafted and with `"draft": false`; a GIF and an audio part were refused with 400. A conversation with the picture in its first message resumed 6,144 of its 7,604 prompt tokens from the prompt cache with the cold run's reply, also with `"draft": false` and with two sent at once. At TP=3 the same pictures and an H.264 and a VP9 video answered, each the same drafted and with `"draft": false`, a GIF and an audio part were refused, and the conversation resumed past its picture.
- Videos at TP=2: upstream's `video_served.py` passed on its 13 clips: all 12 it compares gave the processor's prompt ids, a later turn resumed past its video, drafted equalled `"draft": false`, four sent at once equalled their runs alone, a video and an image answered in one request, and eight malformed requests were refused with the reason.

### Not in 3.2.0

The published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.1.0 — 2026-10-20

The 3.x line on upstream TensorFold 1.1.1. The checkpoint, the serving defaults and the tools are 3.0.0's; TP=2 gives new tokens on upstream's tiled BF16 linears, and TP=3 gives 3.0.0's.

### Engine

- The image compiles the engine from the branch `release/3.1.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `1a8f1efdc47b778c68cfdd30c1ba4966b2fe9064` ([`config/engine.lock.json`](config/engine.lock.json)), with Zig 0.17.0 and CUDA 13.3.1 for sm_121 as before. That is upstream TensorFold 1.1.1 with two commits:
  - **The heat wait's look-ahead** (`TF_HEAT_CEILING`), as in 3.0.0.
  - **Rank 0's NCCL id in a file** at TP=3 (`TF_GLM_NCCL_ID_FILE`). 1.1.x opens the ranks' liveness lines to rank 0 through `NCCL_COMM_ID` before NCCL, so each rank now takes `NCCL_COMM_ID` out of NCCL's environment once the lines are up, and rank 0 writes the id then. Kept to this line until upstream's TP bootstrap (pull request #636).
- `prompt_logprobs`, structured output and required or named tool calls in GLM's tool markup are upstream's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018, which upstream closed; the release branch no longer carries its own commits for them. `libtfgrammar` is still built from xgrammar v0.2.8.
- Upstream runs GLM's BF16 linears on tiled kernels by default. They refuse a TP=3 rank's KDA width (upstream issue #1067), so the TP=3 rank files set `TF_GLM_MM=0`, the glue kernels 3.0.0 ran: TP=3 gives 3.0.0's decode-check hashes, edit reply and NLL. TP=2 runs the tiled kernels and gives new reference values ([validation](docs/validation.md)).

### Launch

- `serve.sh` exports `NCCL_COMM_ID` at TP=3 too (`MASTER:NCCL_PORT`), beside the id file, and its startup line names `TF_GLM_MM`.
- `cluster.sh` starts the three TP=3 ranks together, rank 0 last, waits up to 5 minutes for rank 0's NCCL id and copies it to the other hosts, whose ranks wait for it.
- [`examples/`](examples/): the TP=3 rank files set `TF_GLM_MM=0`, with the line to remove once upstream fixes #1067.

### Documentation

- Setup, the README and operations describe TP=3's start on 1.1.x and `TF_GLM_MM=0`; the README states what upstream 1.1.1 changed for this line (image input with `--vision`, which `serve.sh` does not pass, and the efficiency cores in upstream's runbook).
- Operations: on GB10 the engine counts the page cache as free memory (`MemAvailable`), so dropping it before a start is not needed; the acceptance windows still do, as a step kept from 2.x.

### Accepted

On the reference hosts on 2026-10-19 and 20, on the pinned checkpoint, in five launches (three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3), every container on the efficiency cores ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)):

- The decode check gave the same hashes in both launches of each TP size: TP=3's are 3.0.0's, TP=2's new on the tiled kernels. Drafted replies equalled serial ones, `bench --kinds edit` gave 3.0.0's reply at both TP sizes in 190 rounds instead of 363, and an image part was refused with 400.
- `prompt_logprobs` and structured output passed their checks at both TP sizes; the NLL set was scored twice with no movement, TP=3 equal to 3.0.0 and TP=2 within 0.02 of it.
- tool-eval-bench through the tool-argument gate: 92 at TP=2 and 93 at TP=3, with the Safety Gate passed.
- Forty replies of up to 1,024 tokens after 6,000-token prompts, back to back, finished at both TP sizes with the hottest zone at 74.9 °C (TP=2) and 79.8 °C (TP=3). No request waited for heat, the 1,035,295-token prompt (3 of 3, first token after 1,022.7 s) included.
- A cut reply, a stop string and a cut prompt stopped the work at both TP sizes.
- On every core, recorded and not the default: the forty replies at TP=2 finished in the same time with rank 0's host at 93.0 °C, and two requests at once at 88.5 °C.

The release image, started by its own `serve.sh` and this release's `cluster.sh`, gave the same decode-check hashes and edit reply in one launch at each TP size.

### Not in 3.1.0

Image input (upstream's engine reads images on GLM's CUDA path with `--vision`, which `serve.sh` does not pass), the published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).

## 3.0.0 — 2026-10-18

The first release of the 3.x line. It serves the same pinned checkpoint as 1.x and 2.x, `nvidia/GLM-5.3-Flash-NVFP4` at `423acf37583782c51c142d145aef733d72943d93`, with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine 2.x runs, on two hosts at TP=2 or three hosts at TP=3. The 2.x line continues in [`v2/`](../v2/README.md).

### Engine

- The image compiles the engine from the branch `release/3.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `3d3d61d5937fea3bac68e13d75d5d2c7585ce3df` ([`config/engine.lock.json`](config/engine.lock.json)), with Zig 0.17.0 (checked by SHA-256) and CUDA 13.3.1 for sm_121. That is upstream TensorFold 1.0.12 with these additions for GLM-5.3-Flash on CUDA:
  - **`prompt_logprobs`** on non-streamed `/v1/completions`, up to 20 alternatives a token (upstream pull request #1016).
  - **Structured output**: `response_format` `json_object` or `json_schema`, and `tool_choice` `required` or a named function, through `libtfgrammar` over xgrammar v0.2.8 (#1017), with required tool calls written in GLM's tool markup (#1018).
  - **The heat wait's look-ahead** (`TF_HEAT_CEILING`): a prompt also waits while its hottest zone plus the rise of the last chunk run straight after another would pass the ceiling, as 2.x's does.
  - **Rank 0's NCCL id in a file** at TP=3 (`TF_GLM_NCCL_ID_FILE`), since the ring's point-to-point `/32` addresses cannot bootstrap through `NCCL_COMM_ID`; kept to this line until upstream's TP bootstrap (pull request #636).

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) sets them on every rank ([serving defaults](README.md#serving-defaults)):

- One request at a time (`PARALLEL=1`): the engine's own choice, from the memory free at start, changed the number of streams and the prompt cache from one start to the next.
- A window of 245,760 tokens at TP=2, about the most that fits one stream beside the model with BF16 KV, and 1,048,576 at TP=3, the model's limit.
- The checkpoint's MTP head as the drafter, replies of up to 32,768 tokens and reasoning effort `high` when a request names none, the served name `glm-tf` on `127.0.0.1:8095`.
- The prefill heat wait at 92 °C, resuming at 88 °C, with the look-ahead to 93 °C.

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile): the engine built on NVIDIA's CUDA 13.3.1 devel image and its binaries alone on the runtime image (both by digest), with NCCL 2.30.7, the RDMA userspace and Python with `tokenizers` for the checks. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256; the notices of this repository, xgrammar and the engine are beside it. Nothing is built on the hosts.
- [`scripts/`](scripts/):
  - `create_container.sh`: the container on each host, by default on the cores with the lowest maximum frequency (`cpuset.sh`; a GB10's efficiency cores). The engine keeps two CPU threads spinning on every rank, and on every core long runs of replies took a CPU zone past the thermal watch's 94 °C; on the efficiency cores the hottest zone stayed about 10 °C lower for 1 to 3% of speed ([why](README.md#serving-defaults)).
  - `serve.sh`: one rank from its rank file. `cluster.sh`: start, stop and status of every rank from a control machine, at TP=3 with the NCCL id copied between the hosts. `hostwatch.sh`: the memory guard.
- [`examples/`](examples/): the reference hosts' rank files and cluster files for TP=2 and TP=3.

### Tools

- `glm53_tf`, copied from 2.x and fitted to the native engine's replies: `decode-check` hashes the completion text and reads the engine's `token_sha256` (the engine returns no token ids), `decode-divergence` compares texts, `score-nll` scores through `prompt_logprobs`, and `bench`, `long-input`, `tool-gate`, `download` and `verify-download` work as in 2.x.

### Documentation

- [README](README.md), [setup](SETUP.md), [validation](docs/validation.md), [benchmark method](docs/benchmarks.md) and [operations](docs/operations.md), in English and Japanese. The repository's README, document map, licensing guide, third-party notices, `AGENTS.md` and `CONTRIBUTING` name the 3.x line.

### Accepted

On the reference hosts on 2026-10-18, on the pinned checkpoint, in five launches (two at TP=2, one at TP=2 with `PARALLEL=` empty, two at TP=3), every container on the efficiency cores ([measured](README.md#measured-on-the-release); [validation](docs/validation.md)):

- The decode check gave the same hashes in both launches of each TP size, drafted replies equalled serial ones, `bench --kinds edit` gave the same reply at both TP sizes, and an image part was refused with 400.
- `prompt_logprobs` and structured output passed their checks at both TP sizes; the NLL set was scored twice with no movement, within 0.021 of 2.x's references per domain.
- tool-eval-bench through the tool-argument gate: 93 at both TP sizes, with the Safety Gate passed.
- Forty replies of up to 1,024 tokens after 6,000-token prompts, back to back, finished at both TP sizes with the hottest zone at 82.6 °C (TP=2) and 79.7 °C (TP=3). No request waited for heat, the 1,035,295-token prompt (3 of 3, first token after 1,082.9 s) included.
- A cut reply, a stop string and a cut prompt stopped the work at both TP sizes.

The window ran the image `glm53-tf3:3x-bc82bc4`. The release image `glm53-tf3:3.0.0` (linux/arm64 `sha256:73dcd449b44314e5ca1bb6462c8c14c44d7002535dc9fadd4a7f68b2ed7ec4d1`, the same on the three hosts) adds the engine's notices to it with the same binaries (`/usr/share/doc/tf3/ENGINE`), and gave the same decode-check count hash and edit reply in a TP=2 launch.

### Not in 3.0.0

Image input, the published AXL weights, log-probabilities of generated tokens and passing `clear_thinking` to the chat template ([limits](README.md#limits)).
