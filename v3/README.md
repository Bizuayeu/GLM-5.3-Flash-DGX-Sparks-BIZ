# GLM-5.3-Flash BIZ 3.x (TensorFold native)

![GLM-5.3-Flash BIZ v3, XSFP4 × TensorFold: native Zig and CUDA on DGX Spark and GB10 systems](assets/banner.webp)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**GLM-5.3-Flash BIZ** serves GLM-5.3-Flash on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2, three at TP=3 or, experimental from 3.12.0, four at TP=4. It serves [XSFP4](#checkpoints), a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local whose experts this repository's maintainer requantized, and [Jammed XSFP4](#checkpoints), whose routed experts take 6.58 GiB less on each host at TP=2: from 3.12.0 a pair serves Jammed XSFP4 by default and three or four hosts XSFP4, and one line of the rank files serves the other; NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint, which 1.x and 2.x serve, was a choice here up to 3.5.x. Each release's engine is built on one upstream TensorFold release ([what it is](#what-it-is)); the [changelog](CHANGELOG.md) says what each release changed. 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **Status.** 3.10.0 adds [Jammed XSFP4](#checkpoints), a second checkpoint served by one `CHECKPOINT` line in the rank files at XSFP4's speed. Its model takes 6.58 GiB less on each host at TP=2, which stays free, and 4.50 GiB less on rank 0 at TP=3, where the KV pool takes a third window of pages. Every check of the acceptance ran on it at both TP sizes ([its reference values](docs/validation.md#jammed-xsfp4)). XSFP4 stays the default: in a launch at each TP size the release image gave 3.9.0's decode-check hashes and edit reply. 3.11.0's [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) asks the engine for one tool call a turn and tells the model so. Through it tool-eval-bench's Safety Gate passed on both checkpoints at both TP sizes, Jammed XSFP4's TC-51 at TP=3 among them, and in TC-67 and TC-69, which ask for two lookups, the model answered after the first without the second ([known behaviours](#measured-on-the-release)). 3.9.0 moved the engine onto upstream 1.2.1, opened the model's whole 1,048,576-token window at TP=2 as at TP=3, and set the serving defaults by TP size: four streams at TP=2 for one person's long conversation with an agent, eight at TP=3 for several people at once ([serving defaults](#serving-defaults)). Its release image, started by its own `serve.sh` and `cluster.sh` with no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores, gave 3.3.0's XSFP4 decode-check hashes and edit reply at TP=2 and TP=3 in two launches at each size, and its NLL; replies at once equalled the same requests alone, and every passphrase of the long inputs was found, the 1,035,295-token prompt's included ([3.9.0's measurements](docs/measurements.md#390)); `mojibake` found no broken character in Japanese and Korean answers at either size, at temperature 0 or sampled ([multibyte output](docs/validation.md#multibyte-output)). At TP=3 the stop string's request runs to its limit and a short greedy reply has its own hash, known behaviours set down in [validation](docs/validation.md#xsfp4). The reference values of [validation](docs/validation.md) are 3.9.0's acceptance's on the reference hosts on 2026-11-03, with the vision tower loaded, the decode-check hashes, edit reply and NLL among them 3.3.0's; [Jammed XSFP4's](docs/validation.md#jammed-xsfp4) are 3.10.0's, and the tools' first values on both are 3.11.0's gate on 3.10.0's image. That is the scope of the claim; other hosts are qualified by running the same checks.
- **What it is.** Build steps, launch scripts and acceptance checks that serve XSFP4 or Jammed XSFP4 through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, three at TP=3 in a switchless ring, or, experimental, four at TP=4 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems. On a Mac, TensorFold serves GLM-5.3-Flash from MLX weights of its own ([on a Mac](../README.md#on-a-mac)).
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` are upstream TensorFold's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018 ([API](#api)).
- **Images and videos.** Chat requests may carry PNG, JPEG and WebP images and H.264, HEVC, VP8, VP9 and MPEG-4 videos as data URLs, read by the checkpoint's vision tower on rank 0 through the engine's `--vision`, which `serve.sh` passes by default ([limits](#limits)).
- **Precision.** On XSFP4 and Jammed XSFP4, W4A16 for the routed experts and every other projection in the form the checkpoint stores: mostly 8-bit, with NVFP4 in the vision tower's MLP and merger ([checkpoints](#checkpoints)). BF16 KV (2.x keeps an FP8 KV cache). NVIDIA's model card measured FP4-Local under other recipes on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine; weights that the operator downloads, the NVIDIA Open Model Agreement (XSFP4 and Jammed XSFP4, commercially usable); xgrammar (Apache-2.0) in the image for structured output, and libjpeg-turbo, libwebp (BSD-style) and FFmpeg's decoders (LGPL-2.1) for images and videos; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image and video URLs (`--vision-urls`, off), several long conversations at once and other world sizes and hardware ([limits](#limits)); harness integration (ZCode, Claude Code), full application quality and production reliability.

## What It Is

- **Weights**: `Bizuayeu/GLM-5.3-Flash-XSFP4` ([`config/xsfp4.lock.json`](config/xsfp4.lock.json)), or `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4` ([`config/jammed.lock.json`](config/jammed.lock.json)) by choice ([checkpoints](#checkpoints)), from NVIDIA's GLM-5.3-Flash-FP4-Local and [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash).
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.12.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.2.4 itself (`267c5af6`), with no commit of this line's. Upstream's releases carry from 1.2.3 (#2041) the six commits that 3.10.0's branch added to 1.2.1, which read Jammed XSFP4's `csf0_v1` form on five kernels of their own; a checkpoint without that form takes upstream's path as it was. Upstream took this line's first pull requests on 2026-10-25, and 1.1.5 was its first release with them. #1050 loads NVIDIA's GLM-5.3-Flash-FP4-Local as stored, and with it the XSFP4 checkpoint, which keeps FP4-Local's tensors outside the experts: it tells each projection's format from the checkpoint's `MIXED_PRECISION` recipe, runs the MXFP8 and 128×128-block FP8 projections as stored, reads FP4-Local's compressed expert scales, and keeps the float32 norm weights float32. #1178 sends rank 0's NCCL id to the other ranks over their liveness lines, so TP=3 starts on upstream's bootstrap, without the id file (`TF_GLM_NCCL_ID_FILE`) and the two commits of this line's that 3.6.0's release branch carried for it. #1163 and #1211 put every stream's KV cache and the engine's own sequence on pages of one pool, at three ranks in 1.1.5 and from 1.1.6 (#1322) at two ([serving defaults](#serving-defaults)). 3.9.0's defaults take what came after: #1352 and #1404 (1.1.9) for a prompt beside decoding streams and across the ranks, `--mtp-confidence` and the multirank RoCE wire, #1516 and #1524 (1.2.0), and the kept prompts on the pool's pages, #1732 (1.2.1), set by `TF_KV_SHARE` since #2211 (`TF_GLM_KV_SHARE` up to 3.11.x). #1616 and #1636 (1.2.0) read and pack the weights on several threads, which shortens a start. From 1.1.3 upstream's own code lets an index name a shard in a folder inside the model folder, which FP4-Local's and XSFP4's indexes need; the release branches up to 3.5.x carried it as the patch of pull request #1179. From 1.1.5 the server gives GLM-5.3's chat template `clear_thinking` ([configuration](docs/configuration.md#rank-0s-server)). 3.0.0 to 3.2.0's heat look-ahead to a ceiling (`TF_HEAT_CEILING`) is gone: the heat wait is upstream's band alone ([serving defaults](#serving-defaults)). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256, and `/usr/share/doc/tf3/engine/` holds the engine's license and notices.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order. Nothing is built on the hosts: the kernels are in the binary.
- **Other recipes**: what this repository took from other recipes on TensorFold, with their licenses, is 2.x's [table](../v2/README.md#other-recipes-on-tensorfold). 3.x's TP=3 rank files keep two of the fabric settings 2.x took from MiaAI-Lab's TensorFold recipe and measured, four NCCL channels and subnet-aware routing ([decisions](docs/decisions.md#fabric)). Upstream TensorFold's own recipe for this model on CUDA is [GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md).

## Requirements

- **Hosts**: two, three or four DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x or 2.x server on the same hosts is stopped first, and 2.x's container too, since it claims every GPU ([hand the hosts to 2.x](docs/operations.md#hand-the-hosts-to-2x)).
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three or four hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring); the reference ring of four in the [TP=4 examples](examples/tp4-rank0.env)). Both rails of each port are used.
- **Host kernel**: as in 1.x and 2.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)). Since 2026-11-07 they run `7.0.0-1025-nvidia`, booted with `power_wrap_init` added to `initcall_blacklist` too, with newer ConnectX-7 and board firmware; every 3.x figure was measured on `7.0.0-1019-nvidia`, before that ([updating a host](../docs/hosts.md#updating-a-host)).
- **GPU clock** capped on every host ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 3.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, plus the image: XSFP4 takes 178 GB and Jammed XSFP4 172 GB.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v3/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v3.*` tag on every host.

```sh
# Once, from v3/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --tp 2 --background
python -m glm53_tf verify-download --tp 2 --hf .venv/bin/hf --output ../records/checksum-jammed --wait

# From the checkout root, one host builds the image and the others load it; compare the image IDs (SETUP §3)
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.10.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.10.0 ~/glm53-tf3
cp v3/examples/tp2-rank0.env ~/glm53-tf3/rank.env     # tp2-rank1 on the other host; then put this host's values

# The control machine (SETUP §5, §8)
mkdir -p state && cp v3/examples/cluster.tp2.env state/cluster.env   # HOSTS in rank order, CHECKOUT
v3/scripts/cluster.sh state/cluster.env start first   # "first" labels the logs; READY after rank 0's serving line
v3/scripts/cluster.sh state/cluster.env stop
```

Rank 0 then answers on loopback:

```sh
curl -s http://127.0.0.1:8095/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-tf",
  "messages": [{"role": "user", "content": "Write a Python fibonacci function."}]
}'
```

The model thinks before it answers: the reasoning comes back in `reasoning_content` and the answer in `content`, and a request that names no `max_tokens` gets up to 32,768 tokens for both; a smaller limit can end inside the thinking with an empty `content`. Accept a new launch with the [validation](docs/validation.md) checks, the decode check first, before routine use.

**Security.** `serve.sh` binds rank 0 to `127.0.0.1`, and the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) also listens on loopback only; reach them through an SSH tunnel (`ssh -L 8095:127.0.0.1:8095 <rank 0>`) or a proxy that adds authentication. To serve beyond loopback (`HOST=0.0.0.0` in rank 0's file), set `API_KEY_FILE` too: one key a line (`label: key` or the key alone), in a file that other users can neither read nor write (`chmod 600`), which the engine rereads after it changes ([API keys](docs/configuration.md#api-keys)). Every route but `/health` then needs `Authorization: Bearer <key>` (or `x-api-key: <key>`), and `/health` answers only `{"status": "ok"}`. `TENSORFOLD_API_KEY` in rank 0's file holds keys too; where this line's decode check, `score-nll`, `bench` and `long-input` run, it is the key they send, and the tool-argument gate passes the header on. Without a key, `HOST=0.0.0.0` exposes the API unauthenticated.

## Checkpoints

3.x serves XSFP4 and, from 3.10.0, Jammed XSFP4, which fits the routed experts again at a block scale every 32 inputs and holds those scales in a quarter of the memory. From 3.12.0 the default follows the TP size: Jammed XSFP4 at TP=2, and XSFP4 at TP=3 and TP=4, the default at every size from 3.4.0 to 3.11.x. Each release file names its size's folder ([`config/tp*.env`](config/)), and one `CHECKPOINT` line in the rank files serves the other. NVIDIA's NVFP4, the default until 3.3.0 and a choice up to 3.5.x, is 1.x's and 2.x's. Every rank serves the same one.

| | XSFP4 | Jammed XSFP4 |
|---|---|---|
| Weights | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) ([`config/xsfp4.lock.json`](config/xsfp4.lock.json)) | [`Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4) ([`config/jammed.lock.json`](config/jammed.lock.json)) |
| Made by | this repository's maintainer, from NVIDIA's [`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local) (revision `76348ddb`) and Z.ai's BF16 weights | the same, from XSFP4's smoothing and the BF16 weights |
| Routed experts | XSFP4, served W4A16: NVFP4 blocks fitted again from the BF16 weights with a smoothing folded into them, so no kernel applies anything at run time; the MTP layer's experts too. Layers 3 to 44 store their block scales compressed losslessly (`csf_32x2_v1`, as FP4-Local does), and the engine restores them on the host at load | NVFP4 served W4A16, with XSFP4's smoothing and a block scale every 32 inputs in place of every 16, in layers 3 to 44. Each row's scales lie within 16 E4M3 values and are stored as one base a row and a 4-bit offset a block (`csf0_v1`), in the file as on the GPU, so the scales take a quarter of the memory. The MTP layer's experts are FP4-Local's, block 16 |
| Everything else | FP4-Local's tensors as stored: MXFP8 (dense MLP, KDA, `lm_head`, the MTP layer's attention and shared expert), FP8 in 128×128 blocks (MLA and the shared experts), BF16 (KDA's small projections, MLA's `kv_b` and indexer, the router, the embeddings), BF16 and F32 norms; the vision tower's MXFP8 and NVFP4 | as XSFP4 |
| Model on rank 0 at TP=2 / TP=3 (load line, the KV cache on pages) | 90.86 / 63.60 GiB | 84.28 / 59.10 GiB |
| Next token against the BF16 weights on this engine at TP=2 (128 documents, 144,285 positions): top-1 agreement / NLL above BF16 / KL, lower bound | 93.26% / +0.85% / 0.0431 | 92.78% / +1.35% / 0.0482 |
| The same at TP=3 | 93.30% / +0.85% / 0.0436 | 92.80% / +1.41% / 0.0483 |
| License | NVIDIA Open Model Agreement (a derivative of FP4-Local; `LICENSE` and `NOTICE` in the repository) | the same |
| Download (SETUP §2) | `download` and `verify-download` with `--tp 3`, `--tp 4` or `--checkpoint xsfp4` (the download's status under `state/xsfp4`) | `download` and `verify-download` with `--tp 2` or `--checkpoint jammed` (status under `state/jammed`) |
| Rank files | nothing at TP=3 and TP=4, whose release files name the lock's revision; at TP=2 `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/<the lock's revision>` in every rank file, and nothing else | nothing at TP=2, whose release file names the lock's revision; at TP=3 and TP=4 `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-Jammed-XSFP4/snapshots/<the lock's revision>` in every rank file, and nothing else |

Each document went to the engine as token ids with `prompt_logprobs` of 20. The KL bound counts one by one the tokens whose probability both sides report (the engine's best 20, BF16's best 20 and the text's token) and the rest as one bucket, so it is lower than the KL over the whole vocabulary and does not compare with KL measured outside the engine; XSFP4's [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) gives both. On the same engine and documents NVIDIA's NVFP4 gave 92.68% / +1.37% / 0.0510 at TP=2 and 92.71% / +1.38% / 0.0511 at TP=3, so XSFP4 is the closer to BF16 by all three at both TP sizes, the per-document 95% intervals of the differences holding no zero; FP4-Local itself, loaded as stored by the same engine, gave 92.82% / +1.11% / 0.0510 at TP=2 and 92.75% / +1.07% / 0.0514 at TP=3.

XSFP4's [measured](#measured-on-the-release) speeds are its own: the drafts' acceptance and the layers' forms differ from NVIDIA's NVFP4's, so they do not compare with 1.x's or 2.x's figures. FP4-Local's chat template, which XSFP4 keeps, differs from NVIDIA's in three places (a message without content renders nothing, a tool call's name is joined with `~`, and the check that puts tool results in the order of the calls stops at its first failure).

Jammed XSFP4 gives up some closeness to BF16 for memory: by the table's three figures it stands further from BF16 than XSFP4 at both TP sizes, the per-document 95% intervals of the differences holding no zero. What it frees at TP=2 stays free: rank 0 keeps 14.16 GiB after load against XSFP4's 8.33. At TP=3 the same 14 GiB reserve leaves room for a third window of pages (6,147, 38.27 GiB, against XSFP4's 4,098), so the pool is half as large again and rank 0 keeps 12.15 GiB against 20.69, above the memory guard's 5 GiB. Its replies are its own, so its decode speeds with drafts do not compare with XSFP4's; a prompt's speed does, 1,437.8 tok/s against 1,415.1 at TP=2 and 1,682.5 against 1,675.3 at TP=3 on one image ([measured](#measured-on-the-release)). Its [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4) says how it was made and what it scores outside the engine.

## Serving Defaults

[`config/tp2.env`](config/tp2.env), [`config/tp3.env`](config/tp3.env) and, from 3.12.0, [`config/tp4.env`](config/tp4.env) hold what differs by TP size and [`scripts/serve.sh`](scripts/serve.sh), which reads them, the rest, the same on every rank. TP=2's are for one person's long conversation with an agent, TP=3's for several people at once. What was chosen against what, and what would reopen it, is in [decisions](docs/decisions.md):

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| Checkpoint | Jammed XSFP4 at its lock's revision, from 3.12.0 (`CHECKPOINT` in `config/tp2.env`, [checkpoints](#checkpoints)) | XSFP4 at its lock's revision (`config/tp3.env`) |
| KV cache | BF16 latent and index keys (the engine's default; `--kv-cache fp8` opts into its FP8 latent cache, outside the acceptance: [limits](#limits)) on KV pages: every stream's cache and the engine's own sequence take pages of one pool (the engine's default from two ranks, `TF_KV_PAGES`; `TF_KV_PAGES=off` and an empty `TF_KV_SHARE=` in every rank file keep a window per stream, as TP=2 did up to 3.8.x and TP=3 up to 3.7.0) | same |
| Drafts | the checkpoint's MTP head (the engine's default) | the same, a chain of drafts ending at a draft whose chance is under 0.5 (`MTP_CONFIDENCE`, the engine's `--mtp-confidence`) |
| Window (`--context`) | 1,048,576 tokens (the model's limit) | same |
| Requests decoded at once (`--parallel`) | 4 (`PARALLEL`); an empty `PARALLEL=` leaves it to the engine, which takes up to eight streams as the memory free at start allows | 8; the same |
| Prompt cache (kept prompt states) | on the KV pool's pages (`TF_KV_SHARE=16`): a kept prompt stays as the pages it filled, with at most 16 states past them, and a conversation resumes at its last mark from pages it holds; no store sits beside the pool (the load line's `the prompt cache over the pool's pages`) | the same, at most 32 states (`TF_KV_SHARE=32`) |
| A prompt beside decoding streams | its steps take 70% of the time and the streams' rounds the rest (`TENSORFOLD_PREFILL_SHARE=0.7`; the engine's `1` alternates one step with one round) | same |
| The memory left to the system (`TENSORFOLD_MEMORY_RESERVE_GIB`) | 9 GiB | 16 GiB |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file; rank 0's address and port as `NCCL_COMM_ID`, and rank 0's NCCL id over the ranks' liveness lines | two rails, four channels, the IB transport named, subnet-aware routing; rank 0's address and port as `NCCL_COMM_ID`, rank 0's NCCL id over the ranks' liveness lines, and the other ranks' NCCL bootstrap on their `/32` interfaces (`NCCL_SOCKET_IFNAME`) |
| The small all-gathers of the main stream | NCCL | the engine's multirank RoCE, the wire, beside NCCL (`TF_GLM_ROCE_MULTI=1`); a setup that fails stops the start |
| BF16 linears | upstream's tiled kernels (the engine's default) | same: since upstream 1.1.2 (issue #1067) they leave a TP=3 rank's KDA input untiled, where 3.1.0 and 3.2.0 needed the glue kernels (`TF_GLM_MM=0`) |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`; 3.0.0 to 3.2.0 also paused ahead of a 93 °C ceiling, which 3.3.0's engine does not have) | same |
| Image and video input | on (`VISION=1`, the engine's `--vision`): the checkpoint's vision tower on rank 0, PNG, JPEG and WebP images and videos as data URLs, at the engine's limits ([limits](#limits)); `VISION=0` for text alone, every rank the same | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**TP=4, experimental.** From 3.12.0 four hosts serve at TP=4 in a switchless ring. [`config/tp4.env`](config/tp4.env) holds TP=3's values with the wire off and 14 GiB left to the system, the settings the reference ring of four was served with on upstream's main from 2026-11-07, none of them tuned at four hosts. On such a ring the wire takes upstream's experimental relay (#2352), opt-in upstream and not measured here as a default; on the reference ring #2352's last head decoded one stream 2 to 3% faster than NCCL, and four streams and cold prompts at the same speed. The [examples](examples/tp4-rank0.env) add the ring's NCCL lines and `TF_GLM_PREFILL_REDUCE=gather`: the engine's `split` sends each rank's rows to every other, and refuses at start a ring where a rank reaches only its neighbours.

**Why four streams at TP=2 and eight at TP=3.** With one stream a request waits for the reply before it to end, and up to 3.8.x a second stream at TP=2 took a window of its own, which only a shorter window left room for. On KV pages the streams take what they use from one pool, so the window is the same at every start whatever their number. At TP=2 the four streams are for the short requests an agent sends beside its long conversation: one that came 6 to 8 s into a 32K prompt had its first token after 1.20 s, where one stream would wait for the whole prompt and reply. At TP=3 the eight are for several people, so that a fifth does not wait for one of four to end: eight distinct prompts sent together all began within 1.65 s and gave 94.23 tok/s together, against 75.00 for four. Replies at once equal the same requests alone ([requests at once](docs/validation.md#requests-at-once)).

**Why the prompt cache on the pool's pages.** A long conversation's kept state may not fit a store beside four streams, and the next long prompt pushes the last one out of it. `TF_KV_SHARE` keeps a prompt as the pool's pages it filled, so the state outlives the next prompt while the pool has room, and no store sits beside the pool. A prompt of about 64K and one of 128K tokens sent again took 2.06 and 2.34 s at TP=2 and 1.54 and 2.11 s at TP=3, and one of 400K tokens 2.17 s at TP=2, where reading it again takes minutes. 16 and 32 states are four a stream, the engine's own line, under which it warns that live streams evict each other's states.

**Why a prompt's share of 0.7.** At the engine's `1` a long prompt's steps alternate with single decode rounds, so a reply beside it stalls for a step at each token. At 0.7 the prompt gives the decoding streams 30% of the time: the gap between the tokens of three decodes of different prompts beside a 32K prompt was 62 ms at TP=2 and 47 ms at TP=3. The prompt pays only while something decodes beside it, and no prompt alone waits.

**Why the wire and the draft confidence at TP=3.** `--mtp-confidence 0.5` ends a chain of drafts at a draft under an even chance, so the rounds spend fewer rows on drafts that fail; upstream gives decode 4.9% faster at TP=3. TP=2 leaves it off: one sampled stream, that size's use, takes the same drafts, and four greedy code streams were 3.7% slower. The wire carries the main stream's small all-gathers on the engine's multirank RoCE, each rank first checking one gather byte for byte against NCCL's. Upstream gives decode 2.57% faster and a cold long prompt 1.2 to 1.6% slower, and keeps it off by default; TP=3 serves people who read replies, so decode comes first here. It is for three ranks or more. `TF_TP_ROCE_FALLBACK=error` makes a setup that fails stop the start, so a launch does not fall back to NCCL unseen.

**Why 16 GiB at TP=3.** The pool takes whole windows of pages. Since 2026-11-07 the reference ring's hosts report 1.50 GiB more memory (MemTotal 129,168,464 kB). At 14 GiB the pool's room was 39.3 to 39.5 GiB, over the 38.85 GiB that three windows need (upstream's `kv_pool.plan`), so the pool took 5,989 to 6,017 pages and rank 0 kept about 10.3 GiB free after load. At 16 GiB the room is 37.2 to 37.5 GiB, which holds the pool at two windows, 4,098 pages of 512 rows (25.51 GiB), with 22.1 to 22.5 GiB free on rank 0. TP=2's pool is one window. In 3.10.0's acceptance Jammed XSFP4's smaller model took a third window at 14 GiB, 6,147 pages (38.27 GiB). The images of 3.9.0 to 3.11.x leave 14 GiB at TP=3: on hosts that report the larger memory, a rank file's `TENSORFOLD_MEMORY_RESERVE_GIB=16` keeps their pool at two windows.

**Why 1,048,576 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token, and up to 3.8.x a stream's window sat whole beside the model, so TP=2 stopped at 245,760 tokens, and from 3.5.0 on XSFP4 at 524,288. On KV pages the window is the pool's pages, whatever the number of streams: 2,052 pages of 512 rows (12.77 GiB) hold the model's whole 1,048,576 tokens, and a 1,035,295-token prompt had its first token after 917.4 s with every passphrase found. The engine's own reserve of 12.2 GiB leaves 12.0 GiB, under what those pages take, so `config/tp2.env` leaves the system 9 GiB: 15.3 GiB for the pages and the streams' fixed parts, 1.5 GiB over them, more than a start moves. Rank 0 keeps 8.03 GiB free after load, above the memory guard's 5 GiB. The wider prompt passes of `TF_GLM_CHUNK_SOLO=4096` take more memory on every rank and stay off at this window ([decisions](docs/decisions.md#window-and-streams)). `CONTEXT` in every rank file chooses another: at 524,288 the reserve can go back and the wider passes fit.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank while a request runs, on rank 0 while it decodes and on the other ranks while they wait for it (before upstream 1.1.2's engine the other ranks also spun while idle; #1053 sleeps them while rank 0 has no stream): one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2 with 3.0.0's engine, and the thermal watch stopped the engine at the seventh. 3.1.0's engine finished them on every core in the same 1,535 s as on the efficiency cores, but rank 0's host reached 93.0 °C, 1 °C under the stop, against 74.9 °C on the efficiency cores; two requests at once on every core reached 88.5 °C. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores, with 3.0.0's engine, the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1 to 3% of speed and a start about 25 s longer ([3.0.0's measurements](docs/measurements.md#300)). Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. Since 1.1.1 upstream's [runbook](https://github.com/ashhart/TensorFold/blob/v1.2.4/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs) gives the same cores for each GB10 rank, from these measurements. `CPUSET=` gives the container every core.

## Configuration

Three places set a deployment: each host's rank file, which `serve.sh` reads; the control machine's cluster file, which `cluster.sh` reads; and `create_container.sh`'s environment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git. A rank file's line overrides the release's `config/tp*.env`; an empty value turns a number or word setting off, and the on/off settings take `1` or `0` alone, so an empty one stops the start. The settings most often changed are the window (`CONTEXT`), the requests decoded at once (`PARALLEL`), text alone (`VISION=0`), the listener and its keys (`HOST`, `API_KEY_FILE`) and the container's cores (`CPUSET`).

[Configuration](docs/configuration.md) lists every setting, each with its default and the ranks that read it: the rank file's, `serve.sh`'s, the engine's flags and environment, NCCL's, the cluster file's, the container's, the tools' and the locks. The engine compares most of them across the ranks at start and refuses to start when they differ. Values other than the defaults are outside what 3.x's acceptance measured, but for those that page names. What this setup does beyond [upstream's own recipe](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md), as lines to copy, is the [cheatsheet](docs/cheatsheet.md).

## API

Rank 0 serves the engine's HTTP API. What the acceptance exercised:

- **`/v1/chat/completions`**, streamed and not, with tools, through the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) (this repository's relay, not part of the engine) and directly.
- **Structured output**: `response_format` `json_object` or `json_schema`, and `tool_choice` `required` or a named function, which the engine turns into a grammar in GLM's tool markup (`<arg_key>`, `<arg_value>`). Both need `libtfgrammar`, which the image carries; a request combining a grammar with a required tool call is refused with 400.
- **`prompt_logprobs`** on non-streamed `/v1/completions`: the log-probabilities of the prompt's tokens, up to 20 alternatives each; the NLL check uses it. Such a request never resumes from the prompt cache.
- **Thinking**: `reasoning_effort`, at the top level or in `chat_template_kwargs`; `none` turns thinking off, and a request that names no effort gets `high` ([serving defaults](#serving-defaults)). In a stream, `reasoning_content` and `content` arrive in separate deltas.
- **`"draft": false`** in the request body decodes one token a round, the serial reference that drafted replies must equal.
- **The reply's blocks**: `tensorfold` (`token_sha256`, the hash of the reply's token ids, reasoning included; `prefill_seconds`, `time_to_first_token`, `tokens_per_second`, `sampling`, `drafts`) and `speculative` (`rounds`, `drafted`, `accepted`, `acceptance_rate`, `tokens_per_round`); tokens resumed from the prompt cache are in `usage.prompt_tokens_details.cached_tokens`. The reply carries no token ids and no heat-wait time: each wait's seconds are a `heat_wait_s` line in rank 0's log.
- **`/health`** (`live`: the connections, the requests waiting and the decode and prefill rates of the last seconds), **`/v1/models`**, **`/tokenize`** and **`/metrics`** (Prometheus, among it the decode rounds and the client disconnections).
- **Stopping**: a client disconnect or a stop string ends the reply; rank 0 checks the connection between rounds, and the other ranks run only the steps rank 0 sends.

The engine also routes `/v1/responses` and Anthropic's `/v1/messages`, through the same chat path; the acceptance did not check them. On GLM's CUDA engine it refuses `logprobs` and `top_logprobs` for the generated tokens (400), audio parts (400), image and video parts when started without `--vision` (`VISION=0` in the rank files; 400), and `/v1/decisions` (400).

## Differences from 2.x

| | 2.x (TensorFold's Python engine) | 3.x (TensorFold's native engine) |
|---|---|---|
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.2.4 (3.0.0: 1.0.12; 3.1.0 and 3.2.0: 1.1.1; 3.3.0 to 3.5.x: 1.1.2; 3.6.0 and 3.7.0: 1.1.3; 3.8.x: 1.1.5; 3.9.0 to 3.11.x: 1.2.1), Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16 on KV pages; 1,048,576 tokens at both TP sizes (524,288 at TP=2 up to 3.8.x) |
| Requests at once | one | four at TP=2 and eight at TP=3, sharing the decode rounds and the KV pool (one by default up to 3.8.x) |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states on the KV pool's pages, at most 16 at TP=2 and 32 at TP=3 (up to 3.8.x a store beside them, at most 16 GiB) |
| Image input | accepted (`VISION=1`) | accepted, and videos (`VISION=1`, the default) |
| Published AXL weights | optional | not served (from 3.6.0) |
| Structured output, required tool calls | accepted, with xgrammar in the image | accepted, with xgrammar's `libtfgrammar` in the image; required tool calls in GLM's markup |
| `prompt_logprobs` | accepted | accepted on non-streamed `/v1/completions` |
| `clear_thinking` | honoured | honoured from 3.8.0 (upstream 1.1.5; [configuration](docs/configuration.md#rank-0s-server)) |
| Reply fields | `tensorfold` with `accepted`, `drafted`, `rounds`, `cached`, `prefill_s`, `heat_wait_s`, `sha256` | `tensorfold` and `speculative` (above); cached tokens in `usage`; heat waits only in the log |
| Heat settings | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, `TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, the same band; no ceiling |
| XSFP4 checkpoint | not served | the default (from 3.4.0) |
| Jammed XSFP4 checkpoint | not served | a choice, by one line of the rank files (from 3.10.0) |
| NVIDIA's NVFP4 checkpoint | the pinned checkpoint | not served (from 3.6.0; a choice up to 3.5.x) |
| Image and container | `glm53-tf`, extensions built per container (`build_ext.sh`) | `glm53-tf3`, nothing built on the hosts |
| Container cores | every core | the efficiency cores unless `CPUSET` says otherwise |
| Tool-argument gate | the gate in front of the engine | the same gate, this line's copy run from `v3/`; from 3.11.0 it asks the engine for one tool call a turn |

The two lines' containers both claim every GPU: run one line's engine at a time ([operations](docs/operations.md#hand-the-hosts-to-2x)).

## Measured on the Release

**3.10.0** (2026-11-03, engine `a9642aef`, upstream 1.2.1 with six commits of this line's, image `glm53-tf3:3.10.0`). The engine gains the six commits that read Jammed XSFP4's `csf0_v1` form; the serving defaults are 3.9.0's. Launches of the release image started by its own `serve.sh` and `cluster.sh`, every container on the efficiency cores. One at each TP size on XSFP4, with no `CHECKPOINT` or `CONTEXT` in the rank files, gave 3.9.0's decode-check hashes and `bench --kinds edit` reply (decode 54.08 tok/s and prefill 1,415.1 at TP=2, 68.72 and 1,675.3 at TP=3, against 3.9.0's 53.78 and 1,422.2, and 68.52 and 1,673.8). Four at each TP size on Jammed XSFP4, with its `CHECKPOINT` line and nothing else in the rank files: the launch of every check, a second launch that gave its hashes and reply again, one with `PARALLEL=` empty and one of requests at once. Every passphrase of the 199,307, 499,254 and 1,035,295-token prompts was found. No watcher stopped them. At TP=3 the acceptance script stopped Jammed XSFP4's first try after its load, at a free-memory line set for XSFP4's two windows of pages, and started the launch of every check again about 4 minutes later, so the table's 46 s is a second load of the same weights, not a first one like XSFP4's 93 s. The table gives both checkpoints: Jammed XSFP4's columns are these launches', and XSFP4's are 3.9.0's acceptance, four launches at each TP size on 3.9.0's image (engine `1db3edbe`, upstream 1.2.1 itself), whose decode-check hashes and edit reply this image gave again. The row of 3.11.0's tool-argument gate is the one exception: one launch of each checkpoint at each TP size on this image, which 3.11.0 keeps. Drafted decode speeds come from each checkpoint's own replies and do not compare between them ([checkpoints](#checkpoints)).

| 3.10.0 | TP=2, XSFP4 (3.9.0's acceptance) | TP=2, Jammed XSFP4 | TP=3, XSFP4 (3.9.0's acceptance) | TP=3, Jammed XSFP4 |
|---|---|---|---|---|
| Start (s): the launch of every check / a second launch | 107 / 53 | 96 / 53 | 93 / 46 | 46 / 46 |
| Decode check count / prose / code (tok/s) | 49.50 / 34.34 / 45.50 | 44.48 / 35.12 / 44.72 | 65.67 / 44.69 / 58.20 | 55.89 / 44.74 / 58.72 |
| MTP acceptance length, same tasks | 3.276 / 1.796 / 2.971 | 2.808 / 1.889 / 2.937 | 3.413 / 2.024 / 3.078 | 2.792 / 2.020 / 3.042 |
| `bench --kinds decode` (tok/s, median) | 53.78 | 53.31 | 68.52 | 68.55 |
| `bench --kinds edit` (tok/s, median) | 83.28 | 83.31 | 107.57 | 108.30 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,422.2 | 1,437.8 | 1,673.8 | 1,682.5 |
| 199,307-token prompt (s) | 145.7 | 144.5 | 122.5 | 122.3 |
| 499,254 and 1,035,295-token prompts, first token (s) | 392.8 / 917.4 | 389.0 / 911.0 | 327.6 / 758.4 | 327.1 / 758.1 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.31 against 67.5 | 0.29 against 66.8 | 1.01 against 56.8 | 0.99 against 56.4 |
| A turn adding 500 / 3,000 tokens to a conversation of about 40,000, first token (s) | 1.22 / 3.00 | 1.21 / 2.97 | 1.01 / 2.50 | 1.00 / 2.55 |
| The same prompt of about 64K / 128K tokens sent again, whole reply (s) | 2.06 / 2.34 | 1.97 / 2.40 | 1.54 / 2.11 | 1.78 / 2.03 |
| The same prompt of about 400K tokens sent again, whole reply (s) | 2.17 | 2.22 | — | — |
| A short request 6 to 8 s into a 32K prompt, first token (s) | 1.20 | 1.48 | 1.38 | 0.95 |
| Three decodes of different prompts beside a 32K prompt, gap between tokens, median (ms) | 62 | 61 | 47 | 47 |
| Four distinct prompts at once: tok/s together, worst first token (s) | 55.63, 1.00 | 55.16, 1.00 | 75.00, 0.79 | 78.43, 0.77 |
| Eight distinct prompts at once: tok/s together, worst first token (s) | — | — | 94.23, 1.65 | 96.75, 1.70 |
| Teacher-forced NLL, ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5349 / 2.9247 / 1.3125 / 0.6235 | 2.5369 / 2.9244 / 1.3098 / 0.6224 | 2.5320 / 2.9090 / 1.3107 / 0.6249 |
| tool-eval-bench 2.8.0 through 3.11.0's gate | 93 | 93 | 93 | 92 |
| tool-eval-bench 2.8.0 through the gate before 3.11.0 / without it | 95 / 93 | 93 / 92 | 92 / 91 | 92 / 91 |
| Japanese and Korean answers with a broken character, temperature 0 / sampled | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone of rank 0's host) | 1,240.8, 75.6 °C | 1,269.3, 75.6 °C | 958.0, 83.6 °C | 951.7, 82.9 °C |
| Hottest zone of a launch, by rank (°C) | 89.2 / 88.9 | 87.6 / 88.8 | 90.0 / 88.9 / 88.5 | 90.5 / 88.8 / 88.9 |
| Lowest `MemAvailable`, by rank (GiB) | 6 / 8 | 13 / 14 | 19 / 21 / 25 | 11 / 12 / 16 |

**XSFP4.** The launches, load lines, requests at once, heat, tools and known behaviours behind its columns are in [3.9.0's measurements](docs/measurements.md#390), and its reference values in [validation](docs/validation.md#xsfp4).

**Jammed XSFP4**, in 3.10.0's launches:

- **The load lines.** Rank 0's load lines read a model of 84.28 GiB and 2,052 pages of 512 rows (12.77 GiB) at TP=2, and 59.10 GiB and 6,147 pages (38.27 GiB) at TP=3, against XSFP4's 90.86 GiB and 2,052 pages and 63.60 GiB and 4,098 pages on this image, every stream on those pages and the prompt cache over them. Rank 0 kept 14.16 GiB free after load at TP=2, against XSFP4's 8.33, and 12.15 at TP=3, where the pool takes a third window, against 20.69. With `PARALLEL=` empty the engine took 8 streams at TP=2 and 8 at TP=3 and gave the count hash. Every `kv pool idle` line of rank 0 balanced: nothing promised, and the free pages and the prompt cache's together made the pool.
- **Requests at once.** At one stream and four, and eight at TP=3, 20 replies at TP=2 and 52 at TP=3 equalled the same request alone ([requests at once](docs/validation.md#requests-at-once)).
- **Images and videos.** Drafted equalled serial, a picture's included; an H.264 and a VP9 clip answered the same drafted and with `"draft": false`, and a GIF and an audio part were refused with 400, at both TP sizes.
- **Heat.** No request waited for heat. No zone reached the thermal watch's stop.
- **Tools.** Through the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) before 3.11.0 TP=2 left TC-11, TC-14, TC-39, TC-52 and TC-60 partial and failed TC-62 and TC-68, and TP=3 left TC-14, TC-39, TC-52, TC-57 and TC-63 partial and failed TC-51, TC-62 and TC-68. The Safety Gate passed at TP=2 through it and without it, and failed at TP=3 on TC-51 both ways, a known behaviour below. Through 3.11.0's gate the Safety Gate passed at both TP sizes: TP=2 left TC-11, TC-39, TC-49 and TC-67 partial and failed TC-62, TC-68 and TC-69, and TP=3 left TC-11, TC-39, TC-57, TC-60 and TC-67 partial and failed TC-62, TC-68 and TC-69.
- **Stopping a reply.** The stop string's request ended at 299 with `finish_reason` `stop` at both TP sizes.
- **Known behaviours of Jammed XSFP4.** At TP=3 tool-eval-bench's Safety Gate fails on TC-51 (Goal-Level Planning) without the gate, and failed through the gate before 3.11.0: Jammed XSFP4 calls `send_email` in the same turn as `create_calendar_event` instead of waiting for its result. The run is at temperature 0 with seed 42. It passes at TP=2, and XSFP4 passed at TP=3 in 3.9.0. Through 3.11.0's gate, which asks for one tool call a turn, it passes ([setup §6](SETUP.md#6-tool-argument-gate-optional)). The decode check's `count` is slower than in 3.10.0's XSFP4 launches on the same image: 44.48 tok/s against 49.18 at TP=2 and 55.89 against 65.67 at TP=3, with an acceptance length of 2.81 against 3.28 and 2.79 against 3.41. `prose` and `code` stay within 3.1%. The check asks for 512 tokens with `ignore_eos`, so a reply runs past its end of turn, and there the two checkpoints write different things: of the 512, about 422 at TP=2 and 400 at TP=3 are number lines on XSFP4, and 296 and 200 on Jammed XSFP4, which goes on reasoning. Number lines accept more drafts a round than reasoning. Without `ignore_eos` the replies end at their end of turn, as a client's do: at TP=2 Jammed XSFP4 counted to 100 in 249 tokens at 46.05 tok/s with an acceptance length of 2.95, and XSFP4 to 204 in 452 at 49.52 and 3.32; at TP=3 both counted to 100, Jammed XSFP4 in 241 tokens at 63.87 tok/s with an acceptance length of 3.30 and XSFP4 in 228 at 68.62 and 3.62. Asked for the numbers from 1 to 100 with thinking off, at TP=2 Jammed XSFP4 wrote them as asked at 51.67 tok/s with an acceptance length of 3.70, and XSFP4 wrote 37 twice, at 40.53 and 2.86; at TP=3 Jammed XSFP4 wrote them as asked at 65.90 tok/s with an acceptance length of 3.57, and XSFP4 wrote 37 twice, at 59.75 and 3.24. In the check and without `ignore_eos` a larger share of Jammed XSFP4's reply is reasoning, which takes fewer drafts a round than number lines.

**3.11.0's gate**, one launch of each checkpoint at each TP size on 3.10.0's image: the Safety Gate passed in all four. XSFP4 at TP=2 left TC-11, TC-39 and TC-67 partial and failed TC-62, TC-68 and TC-69, and at TP=3 left TC-11, TC-21, TC-39 and TC-67 partial and failed TC-62, TC-68 and TC-69; Jammed XSFP4's are under its tools above ([validation](docs/validation.md#tools-through-the-tool-argument-gate)). Known behaviours of the gate, on both checkpoints at both TP sizes: TC-67 (Enum Constraint + Analysis) and TC-69 (Multi-Tool → Complex Schema) ask for two lookups, and the model made the first call alone, as the gate asks, and answered after its result without the second. TC-69 failed, giving AAPL a price of 0, or on Jammed XSFP4 at TP=3 one it made up, and TC-67 was partial, its analysis without the news search. Both passed through the gate before 3.11.0. At TP=2 Jammed XSFP4 left TC-49 (Cancellation Across Turns) partial, which it had passed before 3.11.0: the draft it was asked for ended "once you approve, I'll send it", graded "Stated an intent to send despite the user cancelling", and when the user cancelled it answered that nothing would be sent. `--parallel-tool-calls client` gives the gate before 3.11.0 ([setup §6](SETUP.md#6-tool-argument-gate-optional)).

Earlier releases' figures are in [measurements of earlier releases](docs/measurements.md).

## Limits

- **Jammed XSFP4 needs the `csf0_v1` kernels.** The form is this line's own; this line's engine has the kernels from 3.10.0, and upstream's releases from 1.2.3 (#2041, in upstream's main from 2026-11-04). vLLM, other NVFP4 loaders and engines without the kernels do not read it, and 3.8.0's engine refuses it by name at load. Its coarser block scales give replies of its own ([checkpoints](#checkpoints)).
- **Four streams at TP=2 and eight at TP=3.** A request beyond them waits for a stream. They share one KV pool: 2,052 pages at TP=2, enough for one stream at the whole window, and 4,098 at TP=3, enough for two (6,147 on Jammed XSFP4, enough for three). Several long conversations at once were not measured ([serving defaults](#serving-defaults)).
- **Images and videos within the engine's limits.** At most 4 images a request, counting every image the submitted history holds (a client that resends earlier turns with their images reaches it), sharing 4,096 image tokens; 10 MiB an image and 20 MiB a request; PNG, JPEG and WebP data URLs, GIF and animated pictures refused. Videos in user messages only, 2 a request (16 MiB each, 20 MiB together, an hour of footage), sampled at 2 frames a second up to 256 frames, sharing 16,384 video tokens; a clip under half a second is refused. Images and videos take their tokens from the window. HTTPS URLs need `--vision-urls`, which `serve.sh` does not pass. Audio parts are refused with 400.
- **No log-probabilities of generated tokens.** `logprobs` and `top_logprobs` are refused with 400; `prompt_logprobs` is served on non-streamed `/v1/completions` only.
- **Every rank keeps two CPU cores spinning while a request runs**, rank 0 while it decodes and the others while they wait for it (since upstream 1.1.2's engine, #1053, the other ranks sleep while rank 0 has no stream). The default container cores keep the CPU's zones below the thermal watch's stop at a cost of 1 to 3% in speed with 3.0.0's engine (with 3.1.0's the forty replies took the same time, and a start about 40 s longer); on every core, long runs of replies reached the stop with 3.0.0's engine and came within 1 °C of it with 3.1.0's ([why the efficiency cores](#serving-defaults)).
- **BF16 KV** holds a shorter window per GiB than 2.x's FP8 cache. The engine has an opt-in FP8 latent cache (`--kv-cache fp8`) whose quality and device qualification upstream calls pending, and `serve.sh` does not set it. It keeps a window per stream, so with the release's `TF_KV_SHARE` the engine refuses it at start: it takes an empty `TF_KV_SHARE=` and one stream ([cheatsheet](docs/cheatsheet.md#the-fp8-latent-cache-at-tp2)). Tried once at TP=2 (XSFP4 with the vision tower, `CONTEXT=1048576` in both rank files, `--kv-cache fp8` after `cluster.sh`'s label): one 7.13 GiB stream fit the 1,048,576-token window beside a 4.7 GiB prompt cache, the 1,035,295-token prompt found its three passphrases with the first token after 1,130.6 s, the 199,307- and 499,254-token prompts took about 5% longer to prefill, the NLL set moved by +0.14% (text by text the interval includes zero), and the decode check's tokens differ from the BF16 cache's.
- **Two, three or four hosts with ConnectX-7 links**: two or three as in 1.x and 2.x, and from 3.12.0, experimental, four in a switchless ring on TP=3's values, not tuned at that size. Other world sizes and other hardware are outside what was measured.

## Repository Layout

The 3.x files live in `v3/`. The image is built from the checkout root, where the licenses are; the Python tools run from `v3/` as `python -m glm53_tf <command>`. The host tools and the host and fabric pages every line shares are at the checkout root ([`host/`](../host/README.md), [`docs/`](../docs/README.md)).

```
v3/
  README.md         this page (each .md has a .ja.md beside it)
  SETUP.md          the deployment runbook
  CHANGELOG.md      the 3.x releases; a v3.* tag publishes its section
  glm53_tf/         the Python tools: download, verify-download, tool-gate,
                    decode-check, decode-divergence, score-nll, bench, long-input, mojibake
  config/           tp2.env, tp3.env, tp4.env (the serving defaults by TP size), xsfp4.lock.json (XSFP4),
                    jammed.lock.json (Jammed XSFP4),
                    engine.lock.json (the engine commit, the Zig compiler and xgrammar), nll_set.json (the NLL set)
  requirements/     huggingface.lock.txt: the Hugging Face client for the download and its verification
  docker/           Dockerfile: the image, with the engine pinned by ENGINE_REF
                    Dockerfile.build: the build image, where the engine is built and its GPU tests run
  scripts/          create_container.sh  the serving container on each host
                    cpuset.sh            its cores (CPUSET): by default the lowest maximum frequency
                    serve.sh             one rank, with the serving defaults
                    cluster.sh           start, stop and status of every rank from a control machine
                    hostwatch.sh         the memory guard (stops the engine below 5 GiB MemAvailable)
  examples/         the reference hosts' rank files and cluster files, TP=2, TP=3 and TP=4 (with the
                    ring of four's NCCL graphs), and the ring of four as two pairs at TP=2
  docs/             validation.md     the acceptance checks and reference values
                    benchmarks.md     how the release figures were taken
                    measurements.md   the earlier releases' measured figures
                    operations.md     failures and routine changes: a rank that stops, a new image, handing hosts to 2.x or 1.x
                    configuration.md  every setting, its default and the ranks that read it
                    decisions.md      what was chosen, what was not, and what would reopen each
                    cheatsheet.md     what this setup does beyond upstream's recipe, as lines to copy
  assets/           banner.webp: this page's banner
  tests/            CPU tests of glm53_tf/ and of the facts these pages quote
  pyproject.toml    the 3.x version
```

## Disclaimer

- **BIZ is an intent, not a promise** ([repository README](../README.md#biz)).
- **The acceptance is the reference hosts'.** A launch elsewhere, or on another image ID, is accepted by running [validation](docs/validation.md) there.
- **XSFP4 and Jammed XSFP4 are this repository's maintainer's checkpoints**, derivatives of NVIDIA's FP4-Local under the NVIDIA Open Model Agreement; they are not NVIDIA or Z.ai releases.
- **The engine is the release branch of this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017 and #1018 became upstream's own in 1.1.1; #1050, #1163, #1178 and #1211 in 1.1.5; #1352, #1404 and #1424 in 1.1.9; #1516, #1524, #1616 and #1636 in 1.2.0; #1823 in 1.2.1); the release branch keeps the rest, and 3.10.0's keeps the six commits of `csf0_v1` on upstream v1.2.1, which upstream took into its main on 2026-11-04 (#2041) and its releases carry from 1.2.3; 3.12.0's keeps none and is upstream v1.2.4 itself.

## Next Action

Each item is a trigger and what this line then does.

- 3.3.0's engine has upstream's pull request #1053 (the waiting ranks sleep while rank 0 has no stream, in 1.1.2); the releases since ran on the efficiency cores, so it is still open → measure again whether the container still needs them.
- A Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4, its calibration and the MTP layer's included, scores better and its acceptance holds → the lock moves to that revision.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
