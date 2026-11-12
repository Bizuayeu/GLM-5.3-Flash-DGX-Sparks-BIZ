# GLM-5.3-Flash BIZ 3.x (TensorFold native)

![GLM-5.3-Flash BIZ v3, XSFP4 × TensorFold: native Zig and CUDA on DGX Spark and GB10 systems](assets/banner.webp)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**GLM-5.3-Flash BIZ** serves GLM-5.3-Flash on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2, three at TP=3 or, experimental from 3.12.0, four at TP=4. It serves [XSFP4](#checkpoints), a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local whose experts this repository's maintainer requantized, and [Jammed XSFP4](#checkpoints), whose routed experts take 6.58 GiB less on each host at TP=2: from 3.12.0 a pair serves Jammed XSFP4 by default and three or four hosts XSFP4, and one line of the rank files serves the other; NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint, which 1.x and 2.x serve, was a choice here up to 3.5.x. Each release's engine is built on one upstream TensorFold release ([what it is](#what-it-is)); the [changelog](CHANGELOG.md) says what each release changed. 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **Status.** 3.12.0 moves the engine onto upstream TensorFold 1.2.7 itself, with no commit of this line's, and the default checkpoint follows the TP size: [Jammed XSFP4](#checkpoints) at TP=2, and XSFP4 at TP=3 and at TP=4, new and experimental on four hosts in a switchless ring ([serving defaults](#serving-defaults)). Its release image, started by its own `serve.sh` and `cluster.sh` with every container on the efficiency cores, gave 3.9.0's decode-check hashes, edit reply and NLL on XSFP4 at TP=3, and 3.10.0's on Jammed XSFP4 at TP=2; every passphrase of the long inputs was found at every TP size, the 1,035,295-token prompt's included; and `mojibake` found no broken character in Japanese and Korean answers, at temperature 0 or sampled ([measured on the release](#measured-on-the-release)). Through 3.11.0's tool-argument gate, tool-eval-bench gave 93 at TP=2 on Jammed XSFP4 and at TP=3 on XSFP4, with the Safety Gate passed, as on 3.10.0's image. At TP=3 decode with drafts is slower than on 3.10.0's engine, with the same tokens, until upstream's fix ([TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)) comes in a release. From upstream 1.2.6 an empty value in a rank file reads as unset for nearly every setting ([configuration](docs/configuration.md#rank-0s-server)). At TP=3 the stop string's request runs to its limit and a short greedy reply has its own hash, known behaviours set down in [validation](docs/validation.md#xsfp4). The reference values of [validation](docs/validation.md) are XSFP4's and, in [their own section](docs/validation.md#jammed-xsfp4), Jammed XSFP4's, set by the acceptances that section names, the latest 3.12.0's on the reference hosts on 2026-11-12. That is the scope of the claim; other hosts are qualified by running the same checks.
- **What it is.** Build steps, launch scripts and acceptance checks that serve XSFP4 or Jammed XSFP4 through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, three at TP=3 in a switchless ring, or, experimental, four at TP=4 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems. On a Mac, TensorFold serves GLM-5.3-Flash from MLX weights of its own ([on a Mac](../README.md#on-a-mac)).
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` are upstream TensorFold's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018 ([API](#api)).
- **Images and videos.** Chat requests may carry PNG, JPEG and WebP images and H.264, HEVC, VP8, VP9 and MPEG-4 videos as data URLs, read by the checkpoint's vision tower on rank 0 through the engine's `--vision`, which `serve.sh` passes by default ([limits](#limits)).
- **Precision.** On XSFP4 and Jammed XSFP4, W4A16 for the routed experts and every other projection in the form the checkpoint stores: mostly 8-bit, with NVFP4 in the vision tower's MLP and merger ([checkpoints](#checkpoints)). BF16 KV (2.x keeps an FP8 KV cache). NVIDIA's model card measured FP4-Local under other recipes on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine; weights that the operator downloads, the NVIDIA Open Model Agreement (XSFP4 and Jammed XSFP4, commercially usable); xgrammar (Apache-2.0) in the image for structured output, and libjpeg-turbo, libwebp (BSD-style) and FFmpeg's decoders (LGPL-2.1) for images and videos; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image and video URLs (`--vision-urls`, off), several long conversations at once and other world sizes and hardware ([limits](#limits)); harness integration (ZCode, Claude Code), full application quality and production reliability.

## What It Is

- **Weights**: `Bizuayeu/GLM-5.3-Flash-XSFP4` ([`config/xsfp4.lock.json`](config/xsfp4.lock.json)) by default at TP=3 and TP=4, and `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4` ([`config/jammed.lock.json`](config/jammed.lock.json)) at TP=2 ([checkpoints](#checkpoints)), from NVIDIA's GLM-5.3-Flash-FP4-Local and [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash).
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.12.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.2.7 itself (`93a2e93e`), with no commit of this line's. Upstream's releases carry from 1.2.3 (#2041) the six commits that 3.10.0's branch added to 1.2.1, which read Jammed XSFP4's `csf0_v1` form on five kernels of their own; a checkpoint without that form takes upstream's path as it was. Upstream took this line's first pull requests on 2026-10-25, and 1.1.5 was its first release with them. #1050 loads NVIDIA's GLM-5.3-Flash-FP4-Local as stored, and with it the XSFP4 checkpoint, which keeps FP4-Local's tensors outside the experts: it tells each projection's format from the checkpoint's `MIXED_PRECISION` recipe, runs the MXFP8 and 128×128-block FP8 projections as stored, reads FP4-Local's compressed expert scales, and keeps the float32 norm weights float32. #1178 sends rank 0's NCCL id to the other ranks over their liveness lines, so TP=3 starts on upstream's bootstrap, without the id file (`TF_GLM_NCCL_ID_FILE`) and the two commits of this line's that 3.6.0's release branch carried for it. #1163 and #1211 put every stream's KV cache and the engine's own sequence on pages of one pool, at three ranks in 1.1.5 and from 1.1.6 (#1322) at two ([serving defaults](#serving-defaults)). 3.9.0's defaults take what came after: #1352 and #1404 (1.1.9) for a prompt beside decoding streams and across the ranks, `--mtp-confidence` and the multirank RoCE wire, #1516 and #1524 (1.2.0), and the kept prompts on the pool's pages, #1732 (1.2.1), set by `TF_KV_SHARE` since #2211 (`TF_GLM_KV_SHARE` up to 3.11.x). #1616 and #1636 (1.2.0) read and pack the weights on several threads, which shortens a start. From 1.1.3 upstream's own code lets an index name a shard in a folder inside the model folder, which FP4-Local's and XSFP4's indexes need; the release branches up to 3.5.x carried it as the patch of pull request #1179. From 1.1.5 the server gives GLM-5.3's chat template `clear_thinking` ([configuration](docs/configuration.md#rank-0s-server)). 3.0.0 to 3.2.0's heat look-ahead to a ceiling (`TF_HEAT_CEILING`) is gone: the heat wait is upstream's band alone ([serving defaults](#serving-defaults)). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256, and `/usr/share/doc/tf3/engine/` holds the engine's license and notices.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order. Nothing is built on the hosts: the kernels are in the binary.
- **Other recipes**: what this repository took from other recipes on TensorFold, with their licenses, is 2.x's [table](../v2/README.md#other-recipes-on-tensorfold). 3.x's TP=3 rank files keep two of the fabric settings 2.x took from MiaAI-Lab's TensorFold recipe and measured, four NCCL channels and subnet-aware routing ([decisions](docs/decisions.md#fabric)). Upstream TensorFold's own recipe for this model on CUDA is [GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md).

## Requirements

- **Hosts**: two, three or four DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x or 2.x server on the same hosts is stopped first, and 2.x's container too, since it claims every GPU ([hand the hosts to 2.x](docs/operations.md#hand-the-hosts-to-2x)).
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three or four hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring); the reference ring of four in the [TP=4 examples](examples/tp4-rank0.env)). Both rails of each port are used.
- **Host kernel**: as in 1.x and 2.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)). Since 2026-11-07 they run `7.0.0-1025-nvidia`, booted with `power_wrap_init` added to `initcall_blacklist` too, with newer ConnectX-7 and board firmware; 3.12.0's acceptance is the first 3.x one on it, and figures carried from earlier releases were measured on `7.0.0-1019-nvidia`, before that ([updating a host](../docs/hosts.md#updating-a-host)).
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
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.12.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.12.0 ~/glm53-tf3
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
| Model on rank 0 at TP=2 / TP=3 (load line, the KV cache on pages) | 91.26 / 64.01 GiB | 84.68 / 59.50 GiB |
| Next token against the BF16 weights on this engine at TP=2 (128 documents, 144,285 positions): top-1 agreement / NLL above BF16 / KL, lower bound | 93.26% / +0.85% / 0.0431 | 92.78% / +1.35% / 0.0482 |
| The same at TP=3 | 93.30% / +0.85% / 0.0436 | 92.80% / +1.41% / 0.0483 |
| License | NVIDIA Open Model Agreement (a derivative of FP4-Local; `LICENSE` and `NOTICE` in the repository) | the same |
| Download (SETUP §2) | `download` and `verify-download` with `--tp 3`, `--tp 4` or `--checkpoint xsfp4` (the download's status under `state/xsfp4`) | `download` and `verify-download` with `--tp 2` or `--checkpoint jammed` (status under `state/jammed`) |
| Rank files | nothing at TP=3 and TP=4, whose release files name the lock's revision; at TP=2 `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/<the lock's revision>` in every rank file, and nothing else | nothing at TP=2, whose release file names the lock's revision; at TP=3 and TP=4 `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-Jammed-XSFP4/snapshots/<the lock's revision>` in every rank file, and nothing else |

Each document went to the engine as token ids with `prompt_logprobs` of 20. The KL bound counts one by one the tokens whose probability both sides report (the engine's best 20, BF16's best 20 and the text's token) and the rest as one bucket, so it is lower than the KL over the whole vocabulary and does not compare with KL measured outside the engine; XSFP4's [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) gives both. On the same engine and documents NVIDIA's NVFP4 gave 92.68% / +1.37% / 0.0510 at TP=2 and 92.71% / +1.38% / 0.0511 at TP=3, so XSFP4 is the closer to BF16 by all three at both TP sizes, the per-document 95% intervals of the differences holding no zero; FP4-Local itself, loaded as stored by the same engine, gave 92.82% / +1.11% / 0.0510 at TP=2 and 92.75% / +1.07% / 0.0514 at TP=3.

XSFP4's [measured](#measured-on-the-release) speeds are its own: the drafts' acceptance and the layers' forms differ from NVIDIA's NVFP4's, so they do not compare with 1.x's or 2.x's figures. FP4-Local's chat template, which XSFP4 keeps, differs from NVIDIA's in three places (a message without content renders nothing, a tool call's name is joined with `~`, and the check that puts tool results in the order of the calls stops at its first failure).

Jammed XSFP4 gives up some closeness to BF16 for memory: by the table's three figures it stands further from BF16 than XSFP4 at both TP sizes, the per-document 95% intervals of the differences holding no zero. From 3.12.0's engine what it frees goes to the KV pool, which takes the prompt cache's rest: at TP=2, with the same 9 GiB left to the system, its pool held 2,961 to 2,981 pages against XSFP4's 2,059, and rank 0 kept 9.1 to 9.5 GiB free after load against 9.1 GiB. At TP=3 with 16 GiB its pool took a third window, 6,171 pages against XSFP4's 4,706 to 4,780, which left the prompt cache 8 of the 32 kept states' slots ([why 16 GiB](#serving-defaults)), and rank 0 kept 16.4 GiB free after load against 16.5 to 17.1. Its replies are its own, so its decode speeds with drafts do not compare with XSFP4's; a prompt's speed does, 1,535.0 tok/s against 1,507.3 at TP=2 and 1,953.9 against 1,940.9 at TP=3 on one image ([measured](#measured-on-the-release)). Its [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4) says how it was made and what it scores outside the engine.

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
| The small all-gathers of the main stream | the engine's two-rank RoCE path, up to `TF_ROCE_MAX_KB` a rank (4 MiB), and NCCL past it (`TF_ROCE`, on by default; `TF_ROCE=0` keeps them on NCCL) | the engine's multirank RoCE, the wire, beside NCCL (`TF_GLM_ROCE_MULTI=1`); a setup that fails stops the start |
| BF16 linears | upstream's tiled kernels (the engine's default) | same: since upstream 1.1.2 (issue #1067) they leave a TP=3 rank's KDA input untiled, where 3.1.0 and 3.2.0 needed the glue kernels (`TF_GLM_MM=0`) |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`; 3.0.0 to 3.2.0 also paused ahead of a 93 °C ceiling, which 3.3.0's engine does not have) | same |
| Image and video input | on (`VISION=1`, the engine's `--vision`): the checkpoint's vision tower on rank 0, PNG, JPEG and WebP images and videos as data URLs, at the engine's limits ([limits](#limits)); `VISION=0` for text alone, every rank the same | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**TP=4, experimental.** From 3.12.0 four hosts serve at TP=4 in a switchless ring. [`config/tp4.env`](config/tp4.env) holds TP=3's values with the wire off and 14 GiB left to the system, the settings the reference ring of four was served with on upstream's main from 2026-11-07, none of them tuned at four hosts. On such a ring the wire takes upstream's experimental relay (#2352), opt-in upstream and not measured here as a default; on the reference ring #2352's last head decoded one stream 2 to 3% faster than NCCL, and four streams and cold prompts at the same speed. The [examples](examples/tp4-rank0.env) add the ring's NCCL lines and `TF_GLM_PREFILL_REDUCE=gather`: the engine's `split` sends each rank's rows to every other and does not start on a ring of four: NCCL fails its peer warm-up (`ncclGroupEnd: unhandled system error`) before split's own check can name the pair.

**Why four streams at TP=2 and eight at TP=3.** With one stream a request waits for the reply before it to end, and up to 3.8.x a second stream at TP=2 took a window of its own, which only a shorter window left room for. On KV pages the streams take what they use from one pool, so the window is the same at every start whatever their number. At TP=2 the four streams are for the short requests an agent sends beside its long conversation: one that came 6 to 8 s into a 32K prompt had its first token after 1.20 s, where one stream would wait for the whole prompt and reply. At TP=3 the eight are for several people, so that a fifth does not wait for one of four to end: eight distinct prompts sent together all began within 1.65 s and gave 94.23 tok/s together, against 75.00 for four. Replies at once equal the same requests alone ([requests at once](docs/validation.md#requests-at-once)).

**Why the prompt cache on the pool's pages.** A long conversation's kept state may not fit a store beside four streams, and the next long prompt pushes the last one out of it. `TF_KV_SHARE` keeps a prompt as the pool's pages it filled, so the state outlives the next prompt while the pool has room, and no store sits beside the pool. A prompt of about 64K and one of 128K tokens sent again took 2.06 and 2.34 s at TP=2 and 1.54 and 2.11 s at TP=3, and one of 400K tokens 2.17 s at TP=2, where reading it again takes minutes. 16 and 32 states are four a stream, the engine's own line, under which it warns that live streams evict each other's states.

**Why a prompt's share of 0.7.** At the engine's `1` a long prompt's steps alternate with single decode rounds, so a reply beside it stalls for a step at each token. At 0.7 the prompt gives the decoding streams 30% of the time: the gap between the tokens of three decodes of different prompts beside a 32K prompt was 62 ms at TP=2 and 47 ms at TP=3. The prompt pays only while something decodes beside it, and no prompt alone waits.

**Why the wire and the draft confidence at TP=3.** `--mtp-confidence 0.5` ends a chain of drafts at a draft under an even chance, so the rounds spend fewer rows on drafts that fail; upstream gives decode 4.9% faster at TP=3. TP=2 leaves it off: one sampled stream, that size's use, takes the same drafts, and four greedy code streams were 3.7% slower. The wire carries the main stream's small all-gathers on the engine's multirank RoCE, each rank first checking one gather byte for byte against NCCL's. Upstream gives decode 2.57% faster and a cold long prompt 1.2 to 1.6% slower, and keeps it off by default; TP=3 serves people who read replies, so decode comes first here. It is for three ranks or more. `TF_TP_ROCE_FALLBACK=error` makes a setup that fails stop the start, so a launch does not fall back to NCCL unseen.

**Why 16 GiB at TP=3.** The pool takes whole windows of pages, and from 3.12.0's engine (upstream 1.2.5, #2358) what the prompt cache leaves past the kept states' slots too; the startup plan puts every window the room holds before the cache. Since 2026-11-07 the reference ring's hosts report 1.50 GiB more memory (MemTotal 129,168,464 kB). On 3.11.x's engine at 14 GiB the pool's room was 39.3 to 39.5 GiB, over the 38.85 GiB that three windows need (upstream's `kv_pool.plan`), so the pool took 5,989 to 6,017 pages and rank 0 kept about 10.3 GiB free after load. At 16 GiB the room is under three windows: in 3.12.0's acceptance it was 36.8 to 37.2 GiB, the 32 kept states' slots took 5.3 GiB, and the pool two windows and the cache's rest, 4,706 to 4,780 pages of 512 rows (29.30 to 29.76 GiB), with 16.5 to 17.1 GiB free on rank 0. TP=2's pool is one window and the cache's rest. In 3.10.0's acceptance Jammed XSFP4's smaller model took a third window at 14 GiB, 6,147 pages (38.27 GiB). In 3.12.0's it took one at 16 GiB too, 6,171 pages (38.42 GiB), and since the plan sets the windows aside before the slots, the prompt cache kept 8 of the 32 states, with the engine's warning that live streams evict each other's; `--prompt-cache-gib 6` after `cluster.sh`'s label kept all 32 and two windows, 5,525 pages (34.40 GiB), with the same decode-check tokens ([engine flags](docs/configuration.md#engine-flags)). The images of 3.9.0 to 3.11.x leave 14 GiB at TP=3: on hosts that report the larger memory, a rank file's `TENSORFOLD_MEMORY_RESERVE_GIB=16` keeps their pool at two windows.

**Why 1,048,576 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token, and up to 3.8.x a stream's window sat whole beside the model, so TP=2 stopped at 245,760 tokens, and from 3.5.0 on XSFP4 at 524,288. On KV pages the window is the pool's pages, whatever the number of streams: 2,052 pages of 512 rows (12.77 GiB) hold the model's whole 1,048,576 tokens, and in 3.12.0's acceptance a 1,035,295-token prompt had its first token after 835.5 s on Jammed XSFP4 with every passphrase found. On Jammed XSFP4, the default from 3.12.0, the engine's own reserve of 12.3 GiB leaves 20.0 GiB and 2,451 pages, the window and some of the prompt cache's rest, and `config/tp2.env`'s 9 GiB gives 23.2 to 23.3 GiB and 2,961 to 2,981 pages, with rank 0 keeping 9.1 to 9.5 GiB free after load, above the memory guard's 5 GiB. On XSFP4, served at TP=2 by a `CHECKPOINT` line in every rank file, the 9 GiB is what makes room for the window: on 3.9.0's engine its own reserve of 12.2 GiB left 12.0 GiB, under the 12.77 GiB the window's pages take, and in 3.12.0's acceptance the 9 GiB gave 16.7 GiB and 2,059 pages with 9.1 GiB free on rank 0, and `TF_KV_SHARE=16` kept 12 states, what that room holds at any `--prompt-cache-gib`; that acceptance did not start XSFP4 at TP=2 on the engine's own reserve. The wider prompt passes of `TF_GLM_CHUNK_SOLO=4096` take more memory on every rank and stay off at this window ([decisions](docs/decisions.md#window-and-streams)). `CONTEXT` in every rank file chooses another: at 524,288 the reserve can go back and the wider passes fit.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank while a request runs, on rank 0 while it decodes and on the other ranks while they wait for it (before upstream 1.1.2's engine the other ranks also spun while idle; #1053 sleeps them while rank 0 has no stream): one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2 with 3.0.0's engine, and the thermal watch stopped the engine at the seventh. 3.1.0's engine finished them on every core in the same 1,535 s as on the efficiency cores, but rank 0's host reached 93.0 °C, 1 °C under the stop, against 74.9 °C on the efficiency cores; two requests at once on every core reached 88.5 °C. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores, with 3.0.0's engine, the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1 to 3% of speed and a start about 25 s longer ([3.0.0's measurements](docs/measurements.md#300)). Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. Since 1.1.1 upstream's [runbook](https://github.com/ashhart/TensorFold/blob/v1.2.7/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs) gives the same cores for each GB10 rank, from these measurements. `CPUSET=` gives the container every core.

## Configuration

Three places set a deployment: each host's rank file, which `serve.sh` reads; the control machine's cluster file, which `cluster.sh` reads; and `create_container.sh`'s environment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git. A rank file's line overrides the release's `config/tp*.env`; an empty value reads as unset for nearly every number or word setting, which then takes its default ([empty values](docs/configuration.md#rank-0s-server)), and the on/off settings take `1` or `0` alone, so an empty one stops the start. The settings most often changed are the window (`CONTEXT`), the requests decoded at once (`PARALLEL`), text alone (`VISION=0`), the listener and its keys (`HOST`, `API_KEY_FILE`) and the container's cores (`CPUSET`).

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
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.2.7 (3.0.0: 1.0.12; 3.1.0 and 3.2.0: 1.1.1; 3.3.0 to 3.5.x: 1.1.2; 3.6.0 and 3.7.0: 1.1.3; 3.8.x: 1.1.5; 3.9.0 to 3.11.x: 1.2.1), Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16 on KV pages; 1,048,576 tokens at every TP size (524,288 at TP=2 up to 3.8.x) |
| Requests at once | one | four at TP=2 and eight at TP=3 and TP=4, sharing the decode rounds and the KV pool (one by default up to 3.8.x) |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states on the KV pool's pages, at most 16 at TP=2 and 32 at TP=3 and TP=4 (up to 3.8.x a store beside them, at most 16 GiB) |
| Image input | accepted (`VISION=1`) | accepted, and videos (`VISION=1`, the default) |
| Published AXL weights | optional | not served (from 3.6.0) |
| Structured output, required tool calls | accepted, with xgrammar in the image | accepted, with xgrammar's `libtfgrammar` in the image; required tool calls in GLM's markup |
| `prompt_logprobs` | accepted | accepted on non-streamed `/v1/completions` |
| `clear_thinking` | honoured | honoured from 3.8.0 (upstream 1.1.5; [configuration](docs/configuration.md#rank-0s-server)) |
| Reply fields | `tensorfold` with `accepted`, `drafted`, `rounds`, `cached`, `prefill_s`, `heat_wait_s`, `sha256` | `tensorfold` and `speculative` (above); cached tokens in `usage`; heat waits only in the log |
| Heat settings | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, `TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, the same band; no ceiling |
| XSFP4 checkpoint | not served | the default at TP=3 and TP=4 (at every TP size from 3.4.0 to 3.11.x) |
| Jammed XSFP4 checkpoint | not served | the default at TP=2 from 3.12.0 (a choice by one line of the rank files from 3.10.0) |
| NVIDIA's NVFP4 checkpoint | the pinned checkpoint | not served (from 3.6.0; a choice up to 3.5.x) |
| Image and container | `glm53-tf`, extensions built per container (`build_ext.sh`) | `glm53-tf3`, nothing built on the hosts |
| Container cores | every core | the efficiency cores unless `CPUSET` says otherwise |
| Tool-argument gate | the gate in front of the engine | the same gate, this line's copy run from `v3/`; from 3.11.0 it asks the engine for one tool call a turn |

The two lines' containers both claim every GPU: run one line's engine at a time ([operations](docs/operations.md#hand-the-hosts-to-2x)).

## Measured on the Release

**3.12.0** (2026-11-12, engine `93a2e93e`, upstream 1.2.7 itself, image `glm53-tf3:3.12.0`). The engine is upstream 1.2.7, with no commit of this line's, and the default checkpoint follows the TP size: Jammed XSFP4 at TP=2, and XSFP4 at TP=3 and at TP=4, new and experimental ([checkpoints](#checkpoints)). Launches of the release image started by its own `serve.sh` and `cluster.sh`, every container on the efficiency cores, with no `CHECKPOINT` or `CONTEXT` in the rank files but where named. At TP=2 on Jammed XSFP4 and at TP=3 on XSFP4, the defaults: the launch of every check, a second launch that gave its decode-check hashes and `bench --kinds edit` reply again, and a launch of tool-eval-bench. At TP=2 on XSFP4, with its `CHECKPOINT` line in the rank files: one launch of the decode check and `bench`'s decode, edit and prefill. At TP=2 on Jammed XSFP4 and at TP=3 on XSFP4: a launch of tool-eval-bench through 3.11.0's gate each. At TP=3 on Jammed XSFP4, with its `CHECKPOINT` line: one launch of the decode check and `bench`'s decode, edit and prefill, and one of the decode check with `--prompt-cache-gib 6` after the label. At TP=4 on four other hosts in a switchless ring: the launch of every check but tool-eval-bench, and a second launch. The decode-check hashes, `bench --kinds edit` reply and NLL are 3.9.0's at TP=3 and 3.10.0's on Jammed XSFP4 at TP=2 ([validation](docs/validation.md)). Every passphrase of the 199,307, 499,254 and 1,035,295-token prompts was found at every TP size. No watcher stopped a launch; TP=2's launch of every check waited 2 s for heat, and no other launch in the table waited. The launches of XSFP4 at TP=2, of tool-eval-bench through 3.11.0's gate and of Jammed XSFP4 at TP=3 ran this release's `hostwatch.sh`: each logged a line every 2 to 3 s and its `done`, and none waited for heat. Drafted decode speeds come from each checkpoint's own replies and do not compare between them.

| 3.12.0 | TP=2, Jammed XSFP4 | TP=2, XSFP4 | TP=3, XSFP4 | TP=4, XSFP4 |
|---|---|---|---|---|
| Start (s): the launch of every check / a second launch | 118 / 53 | 64 | 114 / 56 | 113 / 48 |
| Decode check count / prose / code (tok/s) | 44.07 / 35.32 / 44.81 | 50.20 / 33.81 / 44.45 | 57.94 / 33.09 / 48.51 | 58.31 / 38.95 / 56.77 |
| MTP acceptance length, same tasks | 3.200 / 1.964 / 3.262 | 4.080 / 1.826 / 3.399 | 4.197 / 2.040 / 3.650 | 3.483 / 2.086 / 3.599 |
| `bench --kinds decode` (tok/s, median) | 58.21 | 56.64 | 63.23 | 74.14 |
| `bench --kinds edit` (tok/s, median) | 144.41 | 142.37 | 192.21 | 239.69 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,535.0 | 1,507.3 | 1,940.9 | 1,868.0 |
| 199,307-token prompt (s) | 134.8 | — | 105.0 | 107.9 |
| 499,254 and 1,035,295-token prompts, first token (s) | 360.3 / 835.5 | — | 277.9 / 635.3 | 280.9 / 626.9 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 2.85 against 62.7 | — | 1.59 against 49.2 | 1.69 against 50.8 |
| Teacher-forced NLL, ja / en / code / math | 2.5349 / 2.9247 / 1.3125 / 0.6235 | — | 2.5369 / 2.9244 / 1.3098 / 0.6224 | 2.5262 / 2.9140 / 1.3083 / 0.6248 |
| tool-eval-bench 3.0.0 through 3.11.0's gate / the gate before it / without it | 93 / 93 / 92 | — | 93 / 93 / 91 | — |
| Japanese and Korean answers with a broken character, temperature 0 / sampled | 0 / 0 | — | 0 / 0 | 0 / 0 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone of rank 0's host) | 1,236.0, 83.8 °C | — | 1,124.5, 82.3 °C | 985.1, 74.2 °C |
| Hottest zone of a launch, by rank (°C) | 92.3 / 89.6 | 89.3 / 85.5 | 91.3 / 89.1 / 89.2 | 79.3 / 83.3 / 82.7 / 84.2 |
| Lowest `MemAvailable`, by rank (GiB) | 8 / 9 | 8 / 9 | 16 / 17 / 22 | 13 / 14 / 14 / 14 |

- **The load lines.** Rank 0's load lines read a model of 84.68 GiB on Jammed XSFP4 and 91.26 GiB on XSFP4 at TP=2, and 64.01 GiB at TP=3. The pool held one window and the prompt cache's rest at TP=2, 2,961 to 2,981 pages of 512 rows on Jammed XSFP4 and 2,059 on XSFP4, and two windows and the rest at TP=3, 4,706 to 4,780 pages; the kept states' slots took 3.6 GiB at TP=2 and 5.3 GiB at TP=3, all of them ([why 16 GiB at TP=3](#serving-defaults)). Every `kv pool idle` line of rank 0 balanced: nothing promised, and the free pages and the store's together made the pool.
- **TP=3's drafted decode is slower than 3.10.0's.** On XSFP4 the decode check's `count` gave 57.94 tok/s against 3.9.0's 65.67, and `bench --kinds decode` 63.23 against 68.52, with the same tokens; on Jammed XSFP4 `bench --kinds decode` gave 62.45 against 3.10.0's 68.55. Under `--mtp-confidence` a temperature-0 stream drafts to the chain's end every round, and the window verifies only the head above the confidence floor. Upstream's fix ([TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)) comes with the first release that carries it. TP=4 takes TP=3's `MTP_CONFIDENCE`.
- **A request after a cut prompt.** The next request after a 93,000-token prompt cut 3 s in was answered after 2.85 s at TP=2 and 1.59 s at TP=3, against 0.29 and 1.01 in 3.10.0's table. On the same hosts upstream 1.2.4 gave 2.84 s against 0.35 on 3.10.0's image, at TP=2 on XSFP4. Each is one arrival, and where in the prompt's pass it arrives moves it widely.
- **Tools.** Through 3.11.0's [tool-argument gate](SETUP.md#6-tool-argument-gate-optional), one tool call a turn, the Safety Gate passed at both TP sizes: TP=2 on Jammed XSFP4 left TC-11, TC-39, TC-49 and TC-67 partial and failed TC-62, TC-68 and TC-69, as on 3.10.0's image, and TP=3 left TC-11, TC-39 and TC-67 partial and failed TC-62, TC-68 and TC-69, as on 3.10.0's image but for TC-21, which passed. Through the gate as it was before 3.11.0 (3.0.0's tree, as in the acceptances before) the Safety Gate passed at both TP sizes, and without it too. Through that gate TP=2 left TC-11, TC-14, TC-39, TC-52 and TC-60 partial and failed TC-62 and TC-68, and TP=3 left TC-14, TC-39, TC-50 and TC-52 partial and failed TC-29, TC-62 and TC-68; without it both also failed TC-43. Up to 3.11.x the table's tool-eval-bench was 2.8.0.
- **Known behaviours.** At TP=3 the stop string's request runs to its limit and a short greedy reply has its own hash, as on 3.9.0 ([validation](docs/validation.md#xsfp4)).

Earlier releases' figures are in [measurements of earlier releases](docs/measurements.md).

## Limits

- **Jammed XSFP4 needs the `csf0_v1` kernels.** The form is this line's own; this line's engine has the kernels from 3.10.0, and upstream's releases from 1.2.3 (#2041, in upstream's main from 2026-11-04). vLLM, other NVFP4 loaders and engines without the kernels do not read it, and 3.8.0's engine refuses it by name at load. Its coarser block scales give replies of its own ([checkpoints](#checkpoints)).
- **Four streams at TP=2 and eight at TP=3.** A request beyond them waits for a stream. They share one KV pool: at TP=2 2,961 to 2,981 pages on Jammed XSFP4 and 2,059 on XSFP4, enough for one stream at the whole window; 4,706 to 4,780 at TP=3 on XSFP4, enough for two, and 6,171 on Jammed XSFP4, enough for three, where the prompt cache keeps 8 of 32 states (`--prompt-cache-gib 6` keeps all 32 and two windows); 8,198 to 8,215 at TP=4, enough for four. Several long conversations at once were not measured ([serving defaults](#serving-defaults)).
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
- **The engine is the release branch of this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017 and #1018 became upstream's own in 1.1.1; #1050, #1163, #1178 and #1211 in 1.1.5; #1352, #1404 and #1424 in 1.1.9; #1516, #1524, #1616 and #1636 in 1.2.0; #1823 in 1.2.1); the release branch keeps the rest, and 3.10.0's keeps the six commits of `csf0_v1` on upstream v1.2.1, which upstream took into its main on 2026-11-04 (#2041) and its releases carry from 1.2.3; 3.12.0's keeps none and is upstream v1.2.7 itself.

## Next Action

Each item is a trigger and what this line then does.

- 3.3.0's engine has upstream's pull request #1053 (the waiting ranks sleep while rank 0 has no stream, in 1.1.2); the releases since ran on the efficiency cores, so it is still open → measure again whether the container still needs them.
- A Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4, its calibration and the MTP layer's included, scores better and its acceptance holds → the lock moves to that revision.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
