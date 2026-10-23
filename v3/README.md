# NVFP4 BIZ 3.x (TensorFold native)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2 or three hosts at TP=3. 3.0.0 was its first release, on upstream TensorFold 1.0.12; 3.1.0 moves it onto upstream 1.1.1, and 3.2.0 adds image and video input. 3.3.0 moves onto upstream 1.1.2 and adds a second checkpoint to choose: [XSFP4](#checkpoints), a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local whose experts this repository's maintainer requantized; NVIDIA's pinned checkpoint stays the default. 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **Status.** 3.3.0 was accepted on the reference hosts on 2026-10-22 and 23 against the reference values of [validation](docs/validation.md), measured there, at TP=2 and TP=3 on both checkpoints, with the vision tower loaded and the containers on the efficiency cores ([measured on the release](#measured-on-the-release)); on XSFP4 at TP=3 the stop string's request runs to its limit and a short greedy reply differs from the pinned checkpoint's, known behaviours set down there. The acceptance ran the release image, started by its own `serve.sh`; the pinned checkpoint's full runs used the image one engine commit before it, and the release image gave it the same answers. That is the scope of the claim; other hosts are qualified by running the same checks.
- **What it is.** Build steps, launch scripts and acceptance checks that serve the pinned checkpoint through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems.
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` are upstream TensorFold's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018 ([API](#api)).
- **Images and videos.** Chat requests may carry PNG, JPEG and WebP images and H.264, HEVC, VP8, VP9 and MPEG-4 videos as data URLs, read by the checkpoint's vision tower on rank 0 through the engine's `--vision`, which `serve.sh` passes by default ([limits](#limits)).
- **Precision.** On the pinned checkpoint, W4A16 for the routed experts and the dense MLP, BF16 elsewhere; on XSFP4, W4A16 for the routed experts and every other projection in the form the checkpoint stores: mostly 8-bit, with NVFP4 in the vision tower's MLP and merger ([checkpoints](#checkpoints)). BF16 KV on both (2.x keeps an FP8 KV cache). NVIDIA's model cards measured their checkpoints under other recipes on other hardware, so their accuracy tables do not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine; weights that the operator downloads, MIT (the pinned checkpoint) or the NVIDIA Open Model Agreement (XSFP4, commercially usable); xgrammar (Apache-2.0) in the image for structured output, and libjpeg-turbo, libwebp (BSD-style) and FFmpeg's decoders (LGPL-2.1) for images and videos; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image and video URLs (`--vision-urls`, off), the published AXL weights, more than one request at a time (the acceptance sent one at a time), harness integration (ZCode, Claude Code), other world sizes and hardware, full application quality and production reliability ([limits](#limits)).

## What It Is

- **Weights**: by default `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93` ([`config/model.lock.json`](config/model.lock.json)), the same as 1.x and 2.x, derived from [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash). The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16. The option is `Bizuayeu/GLM-5.3-Flash-XSFP4` ([`config/xsfp4.lock.json`](config/xsfp4.lock.json), [checkpoints](#checkpoints)).
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.3.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.1.2 plus the code of upstream pull request #1050, the patch of upstream pull request #1179 (merged after 1.1.2: an index may name a shard in a folder inside the model folder, which FP4-Local's and XSFP4's indexes need on 1.1.2) and one commit of this line's. #1050's code (fifteen commits; the pull request is open upstream) loads NVIDIA's GLM-5.3-Flash-FP4-Local as stored, and with it the XSFP4 checkpoint, which keeps FP4-Local's tensors outside the experts: it tells each projection's format from the checkpoint's `MIXED_PRECISION` recipe, runs the MXFP8 and 128×128-block FP8 projections as stored, reads FP4-Local's compressed expert scales, and keeps the float32 norm weights float32. This line's commit is kept to it for TP=3: rank 0 hands its NCCL id to the other ranks in a file (`TF_GLM_NCCL_ID_FILE`), and each rank then takes `NCCL_COMM_ID`, through which the ranks' liveness lines reach rank 0, out of NCCL's environment, because NCCL cannot bootstrap through the ring's point-to-point `/32` addresses (until upstream's TP bootstrap, pull request #636). 3.1.0 and 3.2.0's heat look-ahead to a ceiling (`TF_HEAT_CEILING`) is gone: the heat wait is upstream's band alone ([serving defaults](#serving-defaults)). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256, and `/usr/share/doc/tf3/engine/` holds the engine's license and notices.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order. Nothing is built on the hosts: the kernels are in the binary.

## Requirements

- **Hosts**: two or three DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x or 2.x server on the same hosts is stopped first, and 2.x's container too, since it claims every GPU ([hand the hosts to 2.x](docs/operations.md#hand-the-hosts-to-2x)).
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Both rails of each port are used.
- **Host kernel**: as in 1.x and 2.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)).
- **GPU clock** capped on every host ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 3.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, as in 1.x and 2.x ([what you deploy](../v1/README.md#what-you-deploy-and-supported-hardware)), plus the image; XSFP4 takes 186 GB beside the pinned one.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v3/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v3.*` tag on every host.

```sh
# Once, from v3/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# XSFP4 instead (Checkpoints below): add --checkpoint xsfp4 to both, another --output to the check (SETUP §2), and CHECKPOINT to every rank file

# One host builds the image, the others load it; compare the image IDs (SETUP §3)
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.3.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.3.0 ~/glm53-tf3
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

**Security.** `serve.sh` binds rank 0 to `127.0.0.1`, and the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) also listens on loopback only; reach them through an SSH tunnel (`ssh -L 8095:127.0.0.1:8095 <rank 0>`) or a proxy that adds authentication. To serve beyond loopback (`HOST=0.0.0.0` in rank 0's file), set `API_KEY_FILE` too: a file readable by its owner only (`chmod 600`; the engine refuses another mode), one key a line (`label: key` or the key alone), which the engine rereads when it changes. Every route but `/health` then needs `Authorization: Bearer <key>` (or `x-api-key: <key>`), and `/health` answers only `{"status": "ok"}`. This line's decode check, `score-nll`, `bench` and `long-input` send the key when `TENSORFOLD_API_KEY` is set where they run, and the tool-argument gate passes the header on. Without a key, `HOST=0.0.0.0` exposes the API unauthenticated.

## Checkpoints

NVIDIA's pinned checkpoint is the default; 3.3.0 accepts XSFP4 beside it. Every rank serves the same one.

| | Pinned (default) | XSFP4 (from 3.3.0) |
|---|---|---|
| Weights | `nvidia/GLM-5.3-Flash-NVFP4` ([`config/model.lock.json`](config/model.lock.json)) | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) ([`config/xsfp4.lock.json`](config/xsfp4.lock.json)) |
| Made by | NVIDIA, from Z.ai's BF16 weights | this repository's maintainer, from NVIDIA's [`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local) (revision `76348ddb`) and Z.ai's BF16 weights |
| Routed experts | NVFP4, served W4A16 | XSFP4, served W4A16: NVFP4 blocks fitted again from the BF16 weights with a smoothing folded into them, so no kernel applies anything at run time; the MTP layer's experts too |
| Everything else | dense MLP NVFP4 (W4A16); attention, shared experts and head BF16 | FP4-Local's tensors as stored: MXFP8 (dense MLP, KDA, `lm_head`, the MTP layer's attention and shared expert), FP8 in 128×128 blocks (MLA and the shared experts), BF16 (KDA's small projections, MLA's `kv_b` and indexer, the router, the embeddings), BF16 and F32 norms; the vision tower's MXFP8 and NVFP4 |
| Model on rank 0 at TP=2 / TP=3 (load line) | 97.38 / 79.30 GiB | 93.44 / 76.36 GiB |
| Next token against the BF16 weights on this engine at TP=2 (128 documents, 144,285 positions): top-1 agreement / NLL above BF16 / KL, lower bound | 92.68% / +1.37% / 0.0510 | 93.26% / +0.85% / 0.0431 |
| The same at TP=3 | 92.71% / +1.38% / 0.0511 | 93.30% / +0.85% / 0.0436 |
| License | MIT | NVIDIA Open Model Agreement (a derivative of FP4-Local; `LICENSE` and `NOTICE` in the repository) |
| Download (SETUP §2) | `download`, `verify-download` | the same with `--checkpoint xsfp4`, into `state/xsfp4` |
| Rank files | nothing: `serve.sh`'s default | `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/<revision>`, the lock's revision, on every rank |

Each document went to the engine as token ids with `prompt_logprobs` of 20. The KL bound counts one by one the tokens whose probability both sides report (the engine's best 20, BF16's best 20 and the text's token) and the rest as one bucket, so it is lower than the KL over the whole vocabulary and does not compare with KL measured outside the engine; XSFP4's [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) gives both. XSFP4 is closer to BF16 than the pinned checkpoint by all three at both TP sizes, the per-document 95% intervals of the differences holding no zero. For reference, FP4-Local itself, loaded as stored by the same engine, gave 92.82% / +1.11% / 0.0510 at TP=2 and 92.75% / +1.07% / 0.0514 at TP=3.

The two give different tokens, so each has its own reference values in [validation](docs/validation.md). XSFP4 leaves more memory beside the window: at TP=2 rank 0 kept an 8.9 GiB prompt cache against 5.2 GiB, and with `PARALLEL=` empty the engine took three streams against two. Its speeds are not the pinned checkpoint's: the drafts' acceptance and the layers' forms differ, so the [measured](#measured-on-the-release) figures belong to each checkpoint and compare only with themselves. FP4-Local's chat template, which XSFP4 keeps, differs from the pinned one in three places (a message without content renders nothing, a tool call's name is joined with `~`, and the check that puts tool results in the order of the calls stops at its first failure).

## Serving Defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank:

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | BF16 latent and index keys (the engine's only form) | same |
| Drafts | the checkpoint's MTP head (the engine's default) | same |
| Window (`--context`) | 245,760 tokens: about the most one stream fits beside the model on each rank | 1,048,576 tokens (the model's limit) |
| Requests decoded at once (`--parallel`) | 1 (`PARALLEL=1`); an empty `PARALLEL=` leaves it to the engine, which sizes the streams and the prompt cache from the memory free at start | same |
| Prompt cache (kept prompt states, at the starts of 2,048-token chunks) | what the window leaves: on the reference hosts with the vision tower loaded, 5.2 GiB on the pinned checkpoint and 8.9 GiB on XSFP4 (rank 0's load line; it moves with the memory free at the start: the earlier 3.x engines kept 4.4 to 5.4 GiB, 5.2 to 6.3 GiB with `VISION=`) | 16.0 GiB on the reference ring |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file; rank 0's address and port as `NCCL_COMM_ID` | two rails, four channels, the IB transport named, subnet-aware routing; rank 0's address and port as `NCCL_COMM_ID` for the ranks' liveness lines alone, and rank 0's NCCL id handed over in a file |
| BF16 linears | upstream's tiled kernels (the engine's default) | same: since upstream 1.1.2 (issue #1067) they leave a TP=3 rank's KDA input untiled, where 3.1.0 and 3.2.0 needed the glue kernels (`TF_GLM_MM=0`) |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`; 3.1.0 and 3.2.0 also paused ahead of a 93 °C ceiling, which 3.3.0's engine does not have) | same |
| Image and video input | on (`VISION=1`, the engine's `--vision`): the checkpoint's vision tower on rank 0, PNG, JPEG and WebP images and videos as data URLs, at the engine's limits ([limits](#limits)); `VISION=` for text alone, every rank the same | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**Why one request at a time.** With `--parallel` unset the engine asks for eight streams and serves as many as fit, so the number of streams and the room left for the prompt cache change from one start to the next with the memory free at that moment (at TP=3 one start took two streams and 0.1 GiB of prompt cache). One stream, as 2.x serves, keeps the window the same at every start, and the prompt cache moves only with the memory free (5.2 and 5.1 GiB at TP=2 with the vision tower in 3.3.0's two launches on the pinned checkpoint). At TP=2 3.0.0's engine fitted no second stream beside the 245,760-token window (it needed 4.55 GiB on each rank, and rank 1 had 4.41 GiB). From 3.1.0 the engine does: with `PARALLEL=` empty, 3.3.0's took two streams and left a 1.5 GiB prompt cache, against one stream's 5.2 GiB.

**Why 245,760 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token, so the pair holds a shorter window than 2.x's 300,000 tokens. 245,760 is about the most that fit one stream on the reference pair. `CONTEXT` in every rank file chooses another.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank while a request runs, on rank 0 while it decodes and on the other ranks while they wait for it (before upstream 1.1.2's engine the other ranks also spun while idle; #1053 sleeps them while rank 0 has no stream): one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2 with 3.0.0's engine, and the thermal watch stopped the engine at the seventh. 3.1.0's engine finished them on every core in the same 1,535 s as on the efficiency cores, but rank 0's host reached 93.0 °C, 1 °C under the stop, against 74.9 °C on the efficiency cores; two requests at once on every core reached 88.5 °C. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1 to 3% of speed and a start about 25 s longer ([measured on the release](#measured-on-the-release)). Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. Since 1.1.1 upstream's [runbook](https://github.com/ashhart/TensorFold/blob/v1.1.1/RUNBOOK.md) gives the same cores for each GB10 rank, from these measurements. `CPUSET=` gives the container every core.

## Configuration

Three places set a deployment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git.

| Where | Setting | Default | Meaning |
|---|---|---|---|
| Rank file (`/work/rank.env`, sourced by `serve.sh`) | `MASTER` | none, required | rank 0's address on the link, the same on every rank |
| | `NCCL_PORT` | `29583` | rank 0's port on `MASTER` in `NCCL_COMM_ID`: NCCL's bootstrap at TP=2; the ranks' liveness lines take the port after it at both TP sizes |
| | `ID_FILE` (TP=3) | `/work/nccl-id` | where rank 0 writes its NCCL id and the other ranks read it (`cluster.sh` copies it between the hosts) |
| | `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX`, `NCCL_SOCKET_IFNAME` | the reference hosts' values | the RDMA devices on the links (both rails), the RoCE v2 GID index, the bootstrap interface |
| | `NCCL_NET`, `NCCL_IB_DISABLE`, `NCCL_IB_ROCE_VERSION_NUM`, `NCCL_IB_ADDR_FAMILY`, `NCCL_SOCKET_FAMILY`, `NCCL_MIN_NCHANNELS`, `NCCL_MAX_NCHANNELS` | NCCL's IB transport over RoCE v2 and IPv4, four channels | as in 2.x ([2.x decisions](../v2/docs/decisions.md#fabric)); TP=3 adds subnet-aware routing and `NCCL_NET_PLUGIN=none` ([`tp3-rank0.env`](examples/tp3-rank0.env)) |
| | `NCCL_DEBUG`, `NCCL_DEBUG_SUBSYS` | `INFO`, `INIT,NET` | NCCL logs each connection's transport once at start, which [setup §5](SETUP.md#5-start) reads |
| | `PARALLEL` | `1` | requests decoded at once; empty for the engine's own choice ([serving defaults](#serving-defaults)); the same on every rank |
| | `CONTEXT` | `245760` at TP=2, `1048576` at TP=3 | the window; the same on every rank |
| | `MODEL_NAME`, `HOST`, `PORT` | `glm-tf`, `127.0.0.1`, `8095` | rank 0's model id and listener |
| | `REASONING_EFFORT` | `high` | rank 0's effort for a request that names none (`low`, `medium`, `high`, `xhigh`, `max`; empty: the chat template's own) |
| | `API_KEY_FILE` | none | rank 0's key file for serving beyond loopback (above) |
| | `CHECKPOINT` | the pinned snapshot under `/hub` | the checkpoint directory inside the container, the same on every rank; XSFP4's snapshot for that checkpoint ([checkpoints](#checkpoints)) |
| | `TF_HEAT_HIGH`, `TF_HEAT_LOW` | `92`, `88` (°C) | the prefill heat wait's band; empty values for none; the same on every rank |
| | `TF_GLM_MM` | unset (the tiled kernels) | `0` runs the BF16 linears on the engine's glue kernels instead, which give other tokens ([validation](docs/validation.md)); the same on every rank |
| `serve.sh` arguments | after `TP RANK RANK_ENV` | none | passed to `tensorfold-native serve` after the defaults, so they win (`--context 131072`) |
| Cluster file (`cluster.sh`) | `TP`, `HOSTS`, `CHECKOUT` | none, required | the TP size, SSH names in rank order, this repository's root on every host |
| | `SSH`, `CONTAINER`, `WORK` | `ssh -o ConnectTimeout=20`, `glm53-tf3`, `$HOME/glm53-tf3` | how to reach the hosts, the container, the host directory at `/work` |
| `create_container.sh` | `IMAGE WORK_DIR`, `CONTAINER`, `HF_HUB` | none, required; `glm53-tf3`, `~/.cache/huggingface/hub` | the image, the work directory (rank file, NCCL id, logs), the container name, the Hugging Face cache mounted read-only at `/hub` |
| | `CPUSET` | the cores with the lowest maximum frequency (`0-4,10-14` on a GB10) | the container's cores ([why](#serving-defaults)); empty for every core, or a list for docker's `--cpuset-cpus` |

The engine compares its settings across the ranks at start (drafts, the window, the prefill and heat settings, the checkpoint and the binary) and refuses to start when they differ. The rank file is sourced by `bash` with every variable exported, so any other `TF_GLM_*`, `TF_HEAT_*` or `NCCL_*` setting in it reaches the engine. Settings outside this table were not measured on this line. Most of 2.x's settings for its Python engine are not read here: `TF_GLM_HEAT_*` (this engine's are `TF_HEAT_*`), `TF_GLM_CACHE_*`, `TF_GLM_KV`, `TF_GLM_COPY_DRAFTS`, `TF_GLM_B16_DECODE_TABLE` and `TF_GLM_LOOP_GUARD`.

## API

Rank 0 serves the engine's HTTP API. What the acceptance exercised:

- **`/v1/chat/completions`**, streamed and not, with tools, through the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) and directly.
- **Structured output**: `response_format` `json_object` or `json_schema`, and `tool_choice` `required` or a named function, which the engine turns into a grammar in GLM's tool markup (`<arg_key>`, `<arg_value>`). Both need `libtfgrammar`, which the image carries; a request combining a grammar with a required tool call is refused with 400.
- **`prompt_logprobs`** on non-streamed `/v1/completions`: the log-probabilities of the prompt's tokens, up to 20 alternatives each; the NLL check uses it. Such a request never resumes from the prompt cache.
- **Thinking**: `reasoning_effort`, at the top level or in `chat_template_kwargs`; `none` turns thinking off, and a request that names no effort gets `high` ([serving defaults](#serving-defaults)). In a stream, `reasoning_content` and `content` arrive in separate deltas.
- **`"draft": false`** in the request body decodes one token a round, the serial reference that drafted replies must equal.
- **The reply's blocks**: `tensorfold` (`token_sha256`, the hash of the reply's token ids, reasoning included; `prefill_seconds`, `time_to_first_token`, `tokens_per_second`, `sampling`, `drafts`) and `speculative` (`rounds`, `drafted`, `accepted`, `acceptance_rate`, `tokens_per_round`); tokens resumed from the prompt cache are in `usage.prompt_tokens_details.cached_tokens`. The reply carries no token ids and no heat-wait time: each wait's seconds are a `heat_wait_s` line in rank 0's log.
- **`/health`** (`live`: the connections, the requests waiting and the decode and prefill rates of the last seconds), **`/v1/models`**, **`/tokenize`** and **`/metrics`** (Prometheus, among it the decode rounds and the client disconnections).
- **Stopping**: a client disconnect or a stop string ends the reply; rank 0 checks the connection between rounds, and the other ranks run only the steps rank 0 sends.

The engine also routes `/v1/responses` and Anthropic's `/v1/messages`, through the same chat path; the acceptance did not check them. On GLM's CUDA engine it refuses `logprobs` and `top_logprobs` for the generated tokens (400), audio parts (400), image and video parts when started without `--vision` (an empty `VISION=` in the rank files; 400), and `/v1/decisions` (400).

## Differences from 2.x

| | 2.x (TensorFold's Python engine) | 3.x (TensorFold's native engine) |
|---|---|---|
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.1.2 (3.0.0: 1.0.12; 3.1.0 and 3.2.0: 1.1.1), Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16; 245,760 tokens at TP=2, 1,048,576 at TP=3 |
| Requests at once | one | one by default; `PARALLEL` lets the engine share its decode rounds among more, within the memory the window leaves |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states at chunk starts in what the window leaves (on the pinned checkpoint, 5.1 to 5.2 GiB at TP=2 with the vision tower and 16.0 GiB at TP=3); no entry count |
| Image input | accepted (`VISION=1`) | accepted, and videos (`VISION=1`, the default) |
| Published AXL weights | optional | not validated |
| Structured output, required tool calls | accepted, with xgrammar in the image | accepted, with xgrammar's `libtfgrammar` in the image; required tool calls in GLM's markup |
| `prompt_logprobs` | accepted | accepted on non-streamed `/v1/completions` |
| `clear_thinking` | honoured | not passed to the chat template ([limits](#limits)) |
| Reply fields | `tensorfold` with `accepted`, `drafted`, `rounds`, `cached`, `prefill_s`, `heat_wait_s`, `sha256` | `tensorfold` and `speculative` (above); cached tokens in `usage`; heat waits only in the log |
| Heat settings | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, `TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, the same band; no ceiling |
| XSFP4 checkpoint | not served | optional (`CHECKPOINT`) |
| Image and container | `glm53-tf`, extensions built per container (`build_ext.sh`) | `glm53-tf3`, nothing built on the hosts |
| Container cores | every core | the efficiency cores unless `CPUSET` says otherwise |
| Tool-argument gate | the gate in front of the engine | the same gate, this line's copy run from `v3/` |

The two lines' containers both claim every GPU: run one line's engine at a time ([operations](docs/operations.md#hand-the-hosts-to-2x)).

## Measured on the Release

**3.3.0** (2026-10-23, engine `d2d95b11`, upstream 1.1.2 with pull requests #1050 and #1179, image `glm53-tf3:3.3.0`). Launches started by the release's own `serve.sh` (the vision tower loaded, its default) and `cluster.sh`, every container on the efficiency cores, `TF_GLM_MM` unset at both TP sizes: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, on each checkpoint. XSFP4's ran the release image. The pinned checkpoint's ran the image one engine commit before it (`aa12d8df`, without #1179's patch, which lets an index name a shard in a folder), and in one more launch at each TP size the release image gave the pinned checkpoint the same decode-check hashes, edit reply and NLL. Nothing stopped them.

| 3.3.0 | Pinned TP=2 | Pinned TP=3 | XSFP4 TP=2 | XSFP4 TP=3 |
|---|---|---|---|---|
| Start (s): the launch of every check / a second launch | 366 / 301 | 260 / 246 | 377 / 334 | 318 / 258 |
| Decode check count / prose / code (tok/s) | 38.98 / 28.13 / 33.89 | 67.12 / 34.01 / 46.37 | 49.03 / 34.15 / 45.27 | 64.78 / 45.64 / 55.71 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 4.645 / 1.858 / 2.954 | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode` (tok/s, median) | 44.00 | 56.03 | 54.15 | 66.23 |
| `bench --kinds edit` (tok/s, median) | 71.33 | 90.99 | 82.76 | 106.43 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,411.2 | 1,559.7 | 1,415.1 | 1,717.3 |
| 199,307-token prompt (s) | 155.0 | 140.3 | 151.9 | 127.9 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 399.5 / 1,064.9 | — | 373.0 / 1,015.7 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.36 against 68.8 | 1.29 against 62.8 | 0.32 against 68.6 | 0.91 against 56.7 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5285 / 2.9129 / 1.3158 / 0.6262 | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench through the gate | 92 | 95 | 93 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,505, 75.2 °C | 1,233, 85.1 °C | 1,250, 76.5 °C | 981, 85.8 °C |
| Hottest zone of a launch, by rank (°C) | 82.6 / 84.1 | 93.0 / 90.0 / 86.0 | 84.1 / 86.3 | 92.7 / 89.7 / 84.7 |
| Lowest `MemAvailable`, by rank (GiB) | 11 / 13 | 18 / 20 / 26 | 11 / 13 | 21 / 22 / 28 |

- **Against 3.2.0.** At TP=2 the pinned checkpoint's text path is 3.2.0's: 3.1.0's decode-check hashes, edit reply in 190 rounds and NLL, text by text, and the launch with `PARALLEL=` empty the same count hash. Decode, prefill and the edit reply moved by at most 0.7%, and rank 0 keeps a 5.2 GiB prompt cache (4.7). At TP=3 the BF16 linears run on upstream's tiled kernels, which upstream 1.1.2 opened to a TP=3 rank (issue #1067), in place of 3.2.0's glue kernels: the decode-check hashes and the NLL are new ([validation](docs/validation.md#decode-check)); the edit reply is 3.2.0's in 190 rounds, 1.3% faster (90.99 tok/s against 89.83), and the prefill 2.7% faster (1,559.7 against 1,518.2).
- **Images.** Drafted equalled serial on a picture in every launch of every check.
- **XSFP4.** Its decode-check hashes, edit reply and NLL are its own reference values ([validation](docs/validation.md#xsfp4)); a second launch gave the same hashes and edit reply at each TP size. Its speeds belong to its own text (see [checkpoints](#checkpoints)).
- **Known behaviours of XSFP4.** At TP=3 the stop string's request of [validation](docs/validation.md#stopping-a-reply) (the numbers 1 to 1,000 at temperature 0, stopped at `\n300\n`) falls into a loop before 300 and runs to its 4,000-token limit, as on upstream 1.1.1; it stops at 300 at TP=2, and on the pinned checkpoint at both sizes. Generated token by token, such a count sometimes writes one number twice, at a place that moves with the TP size and with where generation starts; from a prefilled context at the same place the engine picks the right number (checked at one place). The pinned checkpoint showed no such repeat in the same checks (after 157 it, FP4-Local and XSFP4 all write a space and 157 again, and the prefill picks that space too), MTP drafts change nothing, and the cause is not established. At TP=3 XSFP4's 8-token greedy reply to "The capital of France is" ends "Paris is spelled" where the pinned checkpoint's ends "Paris is pronounced", so the plain request of the prompt-score and structured-output checks has its own hash there ([validation](docs/validation.md#xsfp4)).
- **Heat.** With no ceiling, a prompt waits only while the hottest zone is above 92 °C, until 88 °C. Only the 1,035,295-token prompts waited, at TP=3: on the pinned checkpoint, in the afternoon, 38 s in 19 pauses of 2 s, its first token after 1,064.9 s (1,026.9 s without the waits, against 3.2.0's 1,022.9 s), and on XSFP4, at night, 42 s in 21 pauses. No zone reached the thermal watch's stop.

**3.2.0** (2026-10-20, engine `1a8f1efd`, upstream 1.1.1, image `glm53-tf3:3.2.0`). Five launches on the pinned checkpoint with the release image, started by its own `serve.sh` (the vision tower loaded, its default) and this release's `cluster.sh`: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, every container on the efficiency cores, `TF_GLM_MM=0` at TP=3; nothing stopped them.

| 3.2.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 301 / 301 | 246 / 258 |
| Decode check count / prose / code (tok/s) | 38.73 / 27.82 / 33.73 | 51.78 / 33.03 / 44.31 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 3.368 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 43.75 | 55.19 |
| `bench --kinds edit` (tok/s, median) | 70.85 | 89.83 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,408.1 | 1,518.2 |
| 199,307-token prompt (s) | 154.4 | 140.5 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 398.7 / 1,056.9 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.42 against 68.8 | 1.53 against 62.6 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 92 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,548, 75.6 °C | 1,317, 82.5 °C |
| Hottest zone of a launch, by rank (°C) | 81.7 / 84.2 | 92.5 / 89.2 / 86.7 |
| Lowest `MemAvailable`, by rank (GiB) | 13 / 12 | 22 / 24 / 29 |

- **Against 3.1.0.** The text path is 3.1.0's: with the tower loaded both TP sizes gave 3.1.0's decode-check hashes, edit reply in 190 rounds and NLL, text by text, and tool-eval-bench's scores, and the TP=2 launch with `PARALLEL=` empty (two streams) the same count hash. Decode, prefill and the edit reply moved by at most 0.7%. The tower takes 1.27 GiB on rank 0 at both TP sizes, and the lowest `MemAvailable` at TP=2 fell from 15 GiB to 12.
- **Images and videos.** Drafted equalled serial on a picture at both TP sizes in the acceptance; the image and video checks of [validation](docs/validation.md#image-and-video-input) passed in shorter launches the same day, at TP=2 and TP=3.
- **Heat.** The TP=3 launch ran in the afternoon: the 1,035,295-token prompt waited 34 s for heat in 17 pauses of 2 s, 10 while rank 0's hottest zone read 92.1 to 92.5 °C and 7 when it read 91.3 to 91.9 °C and the look-ahead (`TF_HEAT_CEILING`) put the next chunk past 93 °C, and its first token came 34 s later than 3.1.0's, run at night. No other request waited, and no zone reached the thermal watch's stop. The cut prompt at TP=3 let the next request answer in 1.53 s (3.1.0: 0.25 s; 3.0.0: 1.49 s), within the check's bound of half the uncut prompt's first token.

**3.1.0** (2026-10-20, engine `1a8f1efd`, upstream 1.1.1, image `glm53-tf3:3.1.0`). Five launches on the pinned checkpoint with the engine built from `1a8f1efd`, started the way this release's `serve.sh` and `cluster.sh` start it: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, every container on the efficiency cores and `serve.sh`'s defaults, `TF_GLM_MM=0` at TP=3; nothing stopped them. Two more at TP=2 on every core recorded the heat. The release image, started by its own `serve.sh` and this release's `cluster.sh`, gave the same decode-check hashes and edit reply in one launch at each TP size.

| 3.1.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 301 / 301 | 540 / 247 |
| Decode check count / prose / code (tok/s) | 38.85 / 27.72 / 33.84 | 51.59 / 32.43 / 44.14 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 3.368 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 43.80 | 55.05 |
| `bench --kinds edit` (tok/s, median) | 71.26 | 89.53 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,415.7 | 1,507.9 |
| 199,307-token prompt (s) | 153.4 | 140.4 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 398.1 / 1,022.7 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.39 against 68.4 | 0.25 against 62.8 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 92 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,536, 74.9 °C | 1,315, 79.8 °C |
| Hottest zone of a launch, by rank (°C) | 81.8 / 83.6 | 90.8 / 89.3 / 85.5 |
| Lowest `MemAvailable`, by rank (GiB) | 15 / 15 | 23 / 11 / 26 |

- **Repeatable.** The two launches at each TP size gave the same decode-check hashes and edit reply, and the TP=2 launch with `PARALLEL=` empty, which took two streams, the same count hash. TP=3 gave 3.0.0's decode-check hashes, edit reply and NLL on the glue kernels; TP=2's are new on the tiled kernels ([validation](docs/validation.md)).
- **Against 3.0.0.** 3.1.0's TP=2 ran on a second pair of the same systems, so its comparison with 3.0.0's TP=2 mixes the engine with the hosts; TP=3 ran on the same three. The same reply of `bench --kinds edit` in 190 rounds instead of 363, so 57% faster at TP=2 and 48% at TP=3; decode 4.3% faster at TP=2 and 1.0% slower at TP=3; prefill 1.2% slower at TP=2 and 3.6% faster at TP=3. At TP=3 the start's load line holds less (model 78.03 GiB and one stream 12.88 GiB, against 84.01 and 18.86), yet the lowest `MemAvailable` was lower; rank 1's 11 GiB was one 2-s reading during tool-eval-bench, with 24 GiB before and after it.
- **Heat.** No request waited for heat, no zone read 92 °C on the efficiency cores, and the GPUs did not slow for heat, the 1M-token prompt included. On every core at TP=2 the forty replies finished in 1,535 s with rank 0's host at 93.0 °C (74.9 °C on the efficiency cores), and two requests at once (`PARALLEL=2`, a 131,072-token window) at 88.5 °C; neither stopped.

**3.0.0** (2026-10-18, engine `3d3d61d5`, image `glm53-tf3:3.0.0`). Five launches in one window on the pinned checkpoint, two at each TP size and one at TP=2 with `PARALLEL=` empty, every container on the efficiency cores and `serve.sh`'s defaults; nothing stopped them. The window ran the image `glm53-tf3:3x-bc82bc4`; the release image adds the engine's notices to it with the same binaries (`/usr/share/doc/tf3/ENGINE`), and gave the same count hash and edit reply in a TP=2 launch.

| 3.0.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 281 / 268 | 235 / 235 |
| Decode check count / prose / code (tok/s) | 38.68 / 26.25 / 32.91 | 47.87 / 33.17 / 44.59 |
| MTP acceptance length, same tasks | 3.34 / 1.879 / 2.747 | 3.048 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 42.01 | 55.61 |
| `bench --kinds edit` (tok/s, median) | 45.40 | 60.69 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,433.5 | 1,454.9 |
| 199,307-token prompt (s) | 152.7 | 150.2 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 425.4 / 1,082.9 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.32 against 67.8 | 1.49 against 66.6 |
| Teacher-forced NLL, ja / en / code / math | 2.5293 / 2.9109 / 1.3138 / 0.6272 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 93 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,599, 82.6 °C | 1,245, 79.7 °C |
| Hottest zone of a launch, by rank (°C) | 89.0 / 83.0 | 89.0 / 88.8 / 83.3 |
| Lowest `MemAvailable`, by rank (GiB) | 16 / 16 | 30 / 30 / 36 |

- **Repeatable.** The two launches at each TP size gave the same decode-check hashes, and the launch with `PARALLEL=` empty the same count hash (the engine chose one stream at TP=2); drafted equalled serial, and `bench --kinds edit` gave the same reply at both TP sizes ([validation](docs/validation.md)).
- **Heat.** No request waited for heat, no zone read 92 °C and the GPUs did not slow for heat, the 1M-token prompt included. With the containers on every core the same image's earlier window stopped when rank 0's CPU zone reached 96.1 °C during tool-eval-bench, and the forty replies stopped at the seventh at 94.7 °C. Against every core at TP=2, decode was 1.0% slower, prefill 3.2% and the 200K-token prompt 2.7% ([why the efficiency cores](#serving-defaults)).
- **Against 2.x (information).** The tokens are the native engine's own; NLL differs from 2.x's reference values by at most 0.021 per domain. 2.9.2's `bench --kinds decode` gave 42.96 and 57.25 tok/s at TP=2 and TP=3.

## Limits

- **One request at a time by default.** More need `PARALLEL`; at TP=2 the 245,760-token window holds two streams with half the prompt cache, and more need a smaller window ([serving defaults](#serving-defaults)).
- **Images and videos within the engine's limits.** At most 4 images a request, counting every image the submitted history holds (a client that resends earlier turns with their images reaches it), sharing 4,096 image tokens; 10 MiB an image and 20 MiB a request; PNG, JPEG and WebP data URLs, GIF and animated pictures refused. Videos in user messages only, 2 a request (16 MB each, 20 MB together, an hour of footage), sampled at 2 frames a second up to 256 frames, sharing 16,384 video tokens; a clip under half a second is refused. Images and videos take their tokens from the window. HTTPS URLs need `--vision-urls`, which `serve.sh` does not pass. Audio parts are refused with 400.
- **No log-probabilities of generated tokens.** `logprobs` and `top_logprobs` are refused with 400; `prompt_logprobs` is served on non-streamed `/v1/completions` only.
- **`clear_thinking` is not passed to the chat template.** The native server passes the template only `enable_thinking`, `thinking_mode` and `reasoning_effort`; the pinned template takes a missing `clear_thinking` as false and keeps the reasoning of earlier turns that a client sends back. A client that sends earlier turns without their reasoning sees no difference.
- **Every rank keeps two CPU cores spinning while a request runs**, rank 0 while it decodes and the others while they wait for it (since upstream 1.1.2's engine, #1053, the other ranks sleep while rank 0 has no stream). The default container cores keep the CPU's zones below the thermal watch's stop at a cost of 1 to 3% in speed with 3.0.0's engine (with 3.1.0's the forty replies took the same time, and a start about 40 s longer); on every core, long runs of replies reached the stop with 3.0.0's engine and came within 1 °C of it with 3.1.0's ([why the efficiency cores](#serving-defaults)).
- **BF16 KV** holds a shorter window per GiB than 2.x's FP8 cache, and 2.x's FP8 path is not in this engine.
- **Two or three hosts with ConnectX-7 links**, as in 1.x and 2.x. Other world sizes and other hardware are outside what was measured.

## Repository Layout

The 3.x files live in `v3/`. The image is built from the checkout root, where the licenses are; the Python tools run from `v3/` as `python -m glm53_tf <command>`. The host tools and the host and fabric pages every line shares are at the checkout root ([`host/`](../host/README.md), [`docs/`](../docs/README.md)).

```
v3/
  README.md         this page (each .md has a .ja.md beside it)
  SETUP.md          the deployment runbook
  CHANGELOG.md      the 3.x releases; a v3.* tag publishes its section
  glm53_tf/         the Python tools: download, verify-download, tool-gate,
                    decode-check, decode-divergence, score-nll, bench, long-input
  config/           model.lock.json (the pinned checkpoint), xsfp4.lock.json (the XSFP4 checkpoint),
                    engine.lock.json (the engine commit, the Zig compiler and xgrammar), axl.lock.json
                    (the published AXL weights), nll_set.json (the NLL set)
  requirements/     huggingface.lock.txt: the Hugging Face client for the download and its verification
  docker/           Dockerfile: the image, with the engine pinned by ENGINE_REF
  scripts/          create_container.sh  the serving container on each host
                    cpuset.sh            its cores (CPUSET): by default the lowest maximum frequency
                    serve.sh             one rank, with the serving defaults
                    cluster.sh           start, stop and status of every rank from a control machine
                    hostwatch.sh         the memory guard (stops the engine below 5 GiB MemAvailable)
  examples/         the reference hosts' rank files and cluster files, TP=2 and TP=3
  docs/             validation.md  the acceptance checks and reference values
                    benchmarks.md  how the release figures were taken
                    operations.md  failures and routine changes: a rank that stops, a new image, handing hosts to 2.x
  tests/            CPU tests of glm53_tf/ and of the facts these pages quote
  pyproject.toml    the 3.x version
```

## Disclaimer

- **BIZ is an intent, not a promise** ([repository README](../README.md#biz)).
- **The acceptance is the reference hosts'.** A launch elsewhere, or on another image ID, is accepted by running [validation](docs/validation.md) there.
- **XSFP4 is this repository's maintainer's checkpoint**, a derivative of NVIDIA's FP4-Local under the NVIDIA Open Model Agreement; it is not an NVIDIA or Z.ai release.
- **The engine is this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017 and #1018 became upstream's own in 1.1.1); the release branch keeps the rest.

## Next Action

Each item is a trigger and what this line then does.

- Upstream's TP bootstrap (pull request #636) lands → start TP=3 on it and drop the NCCL id file from the release branch.
- Upstream takes pull request #1050 (FP4-Local's loader) in a release → move onto it and drop its commits from the release branch; accept both checkpoints again.
- Upstream releases pull request #1179 (an index may name a shard in a folder inside the model folder; merged after 1.1.2) → move onto it and drop its patch from the release branch.
- 3.3.0's engine has upstream's pull request #1053 (the waiting ranks sleep while rank 0 has no stream, in 1.1.2) → measure again whether the container still needs the efficiency cores.
- `chat_template_kwargs.clear_thinking` → pass it to the chat template as 2.x does, and offer it upstream.
- The published AXL weights on the native engine → accept them as 2.x did.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
