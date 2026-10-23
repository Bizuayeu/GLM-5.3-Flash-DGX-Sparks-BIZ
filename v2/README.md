# GLM-5.3-Flash BIZ 2.x (TensorFold)

![NVFP4 BIZ v2 on TensorFold: repeatable inference on two or three nodes, a 300K-token window at TP=2 and 1M at TP=3](assets/banner.png)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**GLM-5.3-Flash BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The name does not depend on the engine. The 2.x line serves it with [TensorFold](https://github.com/ashhart/TensorFold) (Apache-2.0) in place of vLLM, on two hosts at TP=2 or three hosts at TP=3. 2.0.0 is its first release; the [1.x line](../v1/README.md) continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **What it is.** Build steps, launch scripts and acceptance checks that serve the pinned checkpoint through a pinned TensorFold commit as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems.
- **Status.** 2.0.0 was accepted on the reference hosts on 2026-10-04 against the reference values of [validation](docs/validation.md), at both TP sizes ([measured on the release](#measured-on-the-release)). Each later image was accepted against the same reference values, at the TP sizes and with the checks its [changelog](CHANGELOG.md) section names; the current one, 2.9.2's, at TP=2 and TP=3 with image input on, on the pinned checkpoint, with the hosts on DGX OS 7.6.0; its engine computes 2.9.1's bits, so 2.9.1's acceptance on the published AXL weights stands ([measured on the release](#measured-on-the-release), [host preparation](../docs/hosts.md)). That is the scope of the claim; other hosts are qualified by running the same checks.
- **Repeatable by contract.** Drafted replies equal serial ones, a resumed prompt equals a fresh one, and the result does not depend on how the prompt is chunked. These are the engine's contract, where 1.x buys repeatability with switches on vLLM ([differences from 1.x](#differences-from-1x)).
- **Precision.** W4A16 for the routed experts and the dense MLP, BF16 elsewhere, FP8 KV; the published AXL weights, an option, also take the attention projections and the head to W4A16. NVIDIA's model card measured its checkpoint under another recipe on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine, MIT weights that the operator downloads, nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** More than one sequence at a time, image input beyond [the checks run](#measured-on-the-release), the published AXL weights beyond the checks run on them (the decode check, NLL, the edit reply, long inputs and tool-eval-bench at TP=2), harness integration (ZCode, Claude Code), other world sizes and hardware, full application quality and production reliability ([limits](#limits)).

## What It Is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93`, the same as 1.x, derived from [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash). The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16. One exception, inside the engine: the MTP layer's routed experts are BF16 in the checkpoint and are quantized to NVFP4 for drafting only. Every drafted token is verified by the full model, so replies are unchanged. This checkpoint is the default. The option is the published AXL weights (NVFP4 BIZ AXL, the published option of [1.x](../v1/README.md)): `Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16` at revision `bbad98c8f380588c16a2326bf5a2ab7344190b07` ([`config/axl.lock.json`](config/axl.lock.json)), the attention projections and `lm_head` repacked to W4A16 NVFP4 and everything else as in the pinned checkpoint; the rank file's `CHECKPOINT` chooses it ([configuration](#configuration)).
- **Engine**: the BIZ release of TensorFold, published as the branch `release/2.9.2` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): TensorFold v0.6.5 with the GLM NVFP4 loader, which also loads W4A16 NVFP4 attention and head (the published AXL weights, by their tensors), FP8 latent KV, the TP=3 split, prefill work that leaves the bits unchanged (among it a prompt chunk's pool scores taking one row and 32 pool blocks a program, after MiaAI-Lab's patch 0086), a prefill that waits for heat between chunks, image input from upstream pull request #194, carried to three ranks, and decode work that leaves the tokens unchanged: copy drafts (no cut after a miss), KDA decode windows on the three-kernel chain, per-shape tiles for the BF16 decode matmuls, and no unread copy of the DSA key and value rows. From upstream and its recipes it carries pull requests #301 (a stopped request ends on every rank within a round), #421 (a new conversation no longer copies and drops the kept prompts first), #285 (a GLM tool call whose end token arrived before `</tool_call>` is sent when it parses whole) and #294 (the open-file limit raised at start), a quoted `<|image|>` kept as text beside a real picture (after MiaAI-Lab's patch 0080), OpenAI's `include` values accepted by `/v1/responses` (after its patch 0093), a guard that closes a think block collapsed into repeating itself, off by default (`TF_GLM_LOOP_GUARD`, from its patch 0091), a prompt whose client left stopped after the chunk being filled on every rank (after its patch 0109) and tokenizing with Python's GIL released (after its patch 0099); TR3's checkpoint is named as brandonmusic's ([decisions](docs/decisions.md)). The image pins one commit of it ([`TENSORFOLD_REF`](docker/Dockerfile)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile), NVIDIA's PyTorch container 26.09 plus the measured package versions (transformers 5.18.0, xgrammar 0.2.8 for structured output, the Hugging Face hub client, Triton 3.7.1 in place of the base's 3.8.0) and the engine.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order.

## Requirements

- **Hosts**: two or three DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x server on the same hosts is stopped first.
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Both rails of each port are used.
- **Host kernel**: as in 1.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)).
- **GPU clock** capped on every host, as in 1.x ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 2.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, as in 1.x ([what you deploy](../v1/README.md#what-you-deploy-and-supported-hardware)), plus the image; the published AXL weights too where they serve.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v2/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v2.*` tag on every host.

```sh
# Once, from v2/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# Each host, from the checkout root (SETUP §3-§5); build once and `docker load` it elsewhere, then compare image IDs
docker build -f v2/docker/Dockerfile -t glm53-tf:2.9.2 .
v2/scripts/create_container.sh glm53-tf:2.9.2
cp v2/examples/tp2-rank0.env ~/glm53-tf/rank.env      # tp2-rank1 on the other host; then put this host's values
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh

# The control machine (SETUP §6, §9)
mkdir -p state && cp v2/examples/cluster.tp2.env state/cluster.env  # HOSTS in rank order, CHECKOUT
v2/scripts/cluster.sh state/cluster.env start first    # "first" labels the logs; READY after rank 0's serving line
v2/scripts/cluster.sh state/cluster.env stop
```

Rank 0 then answers on loopback:

```sh
curl -s http://127.0.0.1:8095/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-tf",
  "messages": [{"role": "user", "content": "Write a Python fibonacci function."}]
}'
```

The model thinks before it answers: the reasoning comes back in `reasoning_content` and the answer in `content`, and a request that names no `max_tokens` gets 32,768 tokens for both; a smaller limit can end inside the thinking with an empty `content`. Accept a new launch with the [validation](docs/validation.md) checks, the decode check first, before routine use.

**Security.** `serve.sh` binds rank 0 to `127.0.0.1`, and the [tool-argument gate](SETUP.md#7-tool-argument-gate-optional) also listens on loopback only; reach them through an SSH tunnel (`ssh -L 8095:127.0.0.1:8095 <rank 0>`) or a proxy that adds authentication. To serve beyond loopback (`HOST=0.0.0.0` in the rank file), set an API key too: a line `TENSORFOLD_API_KEY=<key>` in rank 0's rank file (the example has it commented out) makes the engine refuse every request without `Authorization: Bearer <key>`, `/metrics` included, while `/health` stays open. This line's decode check, `score-nll`, `bench` and `long-input` send the key when `TENSORFOLD_API_KEY` is set where they run, and the tool-argument gate passes the header on. The key is a secret in a plain file: keep the rank file readable by its owner only (`chmod 600`). Without a key, `HOST=0.0.0.0` exposes the API unauthenticated.

## Serving Defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank:

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | FP8 latent and pooled index keys (`TF_GLM_KV=fp8`) | same |
| Drafts | the checkpoint's MTP head (`--drafter none`: no DFlash2) | same |
| Window (`--context`) | 300,000 tokens | 0 = the largest that fits: 1,048,576 (the model's limit) on the reference ring |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`, from rank 0's file) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file | two rails, four channels, the IB transport named, subnet-aware routing |
| Image input | on: `VISION=1` in every rank file adds `--vision`; rank 0 holds the image tower (1.05 GiB), and other conversations' kept prompts get 2.4 GiB of the 3 GiB | on; the kept prompts keep 3 GiB |
| Prefill exchange between ranks | the engine's default, `split` | same |
| Prefill pause for heat | between chunks, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_GLM_HEAT_HIGH`/`TF_GLM_HEAT_LOW`); also while that zone plus the rise of the last chunk run straight after another would pass 93 °C, until it would not (`TF_GLM_HEAT_CEILING`) | same |
| Kept prompts of other conversations | the engine's defaults: 8 entries, 3 GiB | same |

**Why effort high.** The pinned chat template renders a request that names no effort as `max`, where the thinking runs on almost without end and takes most of the reply limit; 1.x serves such a request at `high` (`api.default_reasoning_effort`), and from 2.7.0 2.x does too. A client's own effort, `low` or `max`, still wins.

**Why 300,000 at TP=2.** With `--context 0` the pair took a window of 567,255 tokens and left nothing for other conversations' kept prompts, which matter for chat and agents that resend a long history. By the engine's own memory geometry, 300,000 tokens free about 3.3 GiB per rank against 567,255, enough for the default 3 GiB of kept prompts. 1.x serves 262,144; this window is not matched to it. Pass another `--context` to `serve.sh` to choose differently (the last flag wins); the most the pair holds is about 567K.

## Configuration

Three places set a deployment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git.

| Where | Setting | Default | Meaning |
|---|---|---|---|
| Rank file (`/work/rank.env`, sourced by `serve.sh`) | `MASTER` | none, required | rank 0's address on the link, the same on every rank |
| | `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX`, `NCCL_SOCKET_IFNAME` | the reference hosts' values | the RDMA devices on the links (both rails), the RoCE v2 GID index, the bootstrap interface |
| | `NCCL_NET`, `NCCL_IB_DISABLE`, `NCCL_IB_ROCE_VERSION_NUM`, `NCCL_IB_ADDR_FAMILY`, `NCCL_SOCKET_FAMILY`, `NCCL_MIN_NCHANNELS`, `NCCL_MAX_NCHANNELS` | NCCL's IB transport over RoCE v2 and IPv4, four channels | named so that NCCL does not fall back to sockets unseen; four channels gave TP=2 decode +1% and more room at start ([decisions](docs/decisions.md#fabric)); TP=3 adds subnet-aware routing and `NCCL_NET_PLUGIN=none`, NCCL's own IB transport ([`tp3-rank0.env`](examples/tp3-rank0.env)) |
| | `VISION` | `1` in the examples (`0` when unset) | image input (`serve.sh` adds `--vision`); `0` turns it off; the same on every rank |
| | `TRITON_CACHE_DIR` | `/work/triton-cache` in the examples (unset: inside the container) | where Triton keeps the kernels it compiles; on the `/work` mount they outlive the container, so a container made again from an image whose kernels did not change compiles none, where one without it compiles them at its start and on its first long prompt ([validation](docs/validation.md#prefill-and-decode-speed)) |
| | `NCCL_DEBUG`, `NCCL_DEBUG_SUBSYS` | `INFO`, `INIT,NET` | NCCL logs each connection's transport once at start, which [SETUP §6](SETUP.md#6-start) reads |
| | `MODEL_NAME`, `HOST`, `PORT` | `glm-tf`, `127.0.0.1`, `8095` | rank 0's model id and listener |
| | `REASONING_EFFORT` | `high` | rank 0's effort for a request that names none (`low`, `medium`, `high`, `xhigh`; empty: none, the chat template's `max`) |
| | `CHECKPOINT` | the pinned snapshot under `/hub` | the checkpoint directory inside the container; `/hub/models--Bizuayeu--GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16/snapshots/bbad98c8f380588c16a2326bf5a2ab7344190b07` serves the published AXL weights ([setup §2](SETUP.md#2-checkout-and-checkpoint) downloads them); the same on every rank, or the start is refused |
| | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW` | `92`, `88` (°C) | the prefill heat wait; the same on every rank, empty for none |
| | `TF_GLM_HEAT_CEILING` | `93` (°C) | the wait's look-ahead: the hottest zone plus the rise of the last chunk run straight after another stays within it; needs the bands, the same on every rank, empty for none |
| | `TF_GLM_CACHE_GIB` | `3` (the engine's) | the most memory per rank for other conversations' kept prompts, out of what the window leaves; the same on every rank |
| | `TF_GLM_CACHE_ENTRIES` | `8` (the engine's) | kept prompts of other conversations; the decode check must be told another value ([decode check](docs/validation.md#decode-check)) |
| | `TF_GLM_COPY_DRAFTS`, `TF_GLM_KDA_DECODE_WIDE`, `TF_GLM_B16_DECODE_TABLE` | `1` (the engine's) | copy drafts, the KDA decode chain and the BF16 decode tiles ([decisions](docs/decisions.md)); `0` turns one off, with the same tokens either way; the same on every rank, or the start is refused |
| | `TF_GLM_LOOP_GUARD` | `0` (the engine's) | `1` in rank 0's file closes a think block that collapsed into an exact short cycle or one dominant token, counted as `loop_guard` in the reply's `tensorfold` block ([decisions](docs/decisions.md#engine)) |
| `serve.sh` arguments | after `TP RANK RANK_ENV` | none | passed to `tensorfold serve` after the defaults, so they win (`--context 500000`) |
| Cluster file (`cluster.sh`) | `TP`, `HOSTS`, `CHECKOUT` | none, required | the TP size, SSH names in rank order, this repository's root on every host (1.x's `--checkout` names its `v1/` instead) |
| | `SSH`, `CONTAINER`, `WORK` | `ssh -o ConnectTimeout=20`, `glm53-tf`, `$HOME/glm53-tf` | how to reach the hosts, the container, the host directory at `/work` |
| `create_container.sh` | `IMAGE [WORK_DIR]`, `CONTAINER`, `HF_HUB` | `~/glm53-tf`, `glm53-tf`, `~/.cache/huggingface/hub` | the image, the work directory (rank file, extensions, logs), the container name, the Hugging Face cache mounted read-only at `/hub` |

The rank file is sourced by `bash` with every variable exported, so any other `TF_GLM_*` or `NCCL_*` setting in it reaches the engine. Settings outside this table were not measured on this line.

## API

Rank 0 serves the engine's HTTP API. What the acceptance exercised:

- **`/v1/chat/completions`**, streamed and not, with tools and structured output (tool-eval-bench's TC-64 to TC-69, which need xgrammar in the image), through the [tool-argument gate](SETUP.md#7-tool-argument-gate-optional).
- **Thinking**: `chat_template_kwargs.reasoning_effort` and `clear_thinking`, as the checks send them; a request that names no effort gets `high` ([serving defaults](#serving-defaults)). A streamed delta can carry both `reasoning_content` and `content` ([limits](#limits)).
- **`"draft": false`** in the request body decodes one token a round, the serial reference that drafted replies must equal.
- **The reply's `tensorfold` block**: `accepted`, `drafted` and `rounds` (MTP acceptance), `cached` (prompt tokens resumed from a kept prompt), `prefill_s` and `heat_wait_s`, `copy_rounds`, `copy_drafted` and `copy_accepted` (copy drafts), and `sha256` (the reply's token ids' hash).
- **`/health`** (the decode `rounds`, among others) and **`/metrics`**.
- **Stopping**: a client disconnect or a stop string ends the decode on every rank within a round.
- **Images** (`VISION=1`): `image_url` parts as data URLs, in user messages and in tool results; a video part is refused with 400.

The NLL check also uses **`/v1/models`** (the model it scores) and **`/v1/completions`** (teacher-forced, with `prompt_logprobs`). The engine also routes `/v1/responses`, Anthropic's `/v1/messages` and `/tokenize`; 2.0.0's acceptance did not check them. From 2.7.0 `/v1/responses` accepts OpenAI's `include` values and ignores them, and refuses any other value with 400.

## Differences from 1.x

| | 1.x (vLLM) | 2.x (TensorFold) |
|---|---|---|
| Repeatable output | vLLM with the [repeatability switches](../v1/docs/server-configuration.md#repeatability-switches) on | the engine's contract: drafted replies equal serial ones, a resumed prompt equals a fresh one, and the result does not depend on the prompt chunking |
| KV and window | FP8, 262,144 tokens (3 GiB per rank) | FP8 latent and index keys, 300,000 tokens at TP=2 and 1,048,576 at TP=3 |
| Launch | `glm53_setup` reads one server TOML; `server preflight`, `cluster switch`, warmup ladder | the scripts here; no preflight or switch |
| Sequences in flight | one, or two with the published option's two-sequence profile | one |
| Image input | accepted | accepted (`VISION=1` in the example rank files) |
| Published AXL weights | optional | optional from 2.4.0 (`CHECKPOINT` in every rank file), at one sequence |
| Tool calls | the model API, optionally behind the tool-argument gate | the same gate, this line's copy run from `v2/`, in front of the engine |
| Heat during a long prefill | no wait in the engine; its measurements rested the hosts between requests with a cooling gate, the one [`host/`](../host/README.md#during-long-runs) now holds | the engine waits between prompt chunks, every rank together, at 92 °C until 88 °C, and while the hottest zone plus the last chunk's rise would pass 93 °C ([serving defaults](#serving-defaults)) |

Why each 2.x setting was chosen, and what was tried and not adopted, is in [decisions](docs/decisions.md).

## Measured on the Release

**2.9.2** (2026-10-15, engine `7bf0aa3`, image `glm53-tf:2.9.2`). The prefill's heat look-ahead judges a chunk by the rise of the last chunk run straight after another, not by the climb back after a rest; the engine is otherwise 2.9.1's ([decisions](docs/decisions.md#heat)). On the pinned weights at both TP sizes with image input on, the decode check gave 2.9.1's token ids, `bench --kinds edit` the reference reply and the image checks passed.

| 2.9.2, image input on | Pinned, TP=2 | Pinned, TP=3 |
|---|---|---|
| Decode check count / prose / code (tok/s) | 44.04 / 27.58 / 36.10 | 59.52 / 38.34 / 48.97 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 4.056 / 2.222 / 3.234 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 42.96 | 57.25 |
| `bench --kinds edit` (tok/s, median) | 58.04 | 77.26 |
| A prompt cut 3 s into its prefill: the next request answered after (s), against the same prompt's uncut fill | 2.06 against 52.22 (69,847 tokens) | 1.07 against 46.86 (78,850 tokens) |
| Prefill of 38,960 tokens (s, two prompts) | 30.47 / 28.93 | 23.81 / 22.95 |
| Rank 0's startup estimate (GiB) | 101.35 | 81.93 |

- **Against 2.9.1.** The same token ids in the decode check and the same replies in `bench --kinds decode` and `bench --kinds edit`; the decode check, `bench --kinds decode` and edits within −0.3% to +0.5%, one launch each. At TP=2 the first 38,960-token prompt took 30.47 s against 28.93 s (2.9.0's and 2.9.1's other launches: 29.99 and 30.24 s), and the second 28.93 s against 67.03 s, where 2.9.1 waited 19 times on heat.
- **Heat.** In the launches, no heat wait at TP=2 and no heat wait at TP=3. Before the release, against 2.9.1's engine on its image: 59.9 s against 93.8 s for a 70,000-token prompt after a rest, and a first token in 1,337.9 s against 1,644.1 s for the 1M-token prompt, where the engine read up to 93.7 °C and the thermal watch never 94 °C ([decisions](docs/decisions.md#heat)).
- **Not measured on this release:** AXL, the NLL set and tool-eval-bench, because the bits are 2.9.1's; 2.9.1's results stand, and 2.9.0's where 2.9.1 did not run.

**2.9.1** (2026-10-15, engine `d2dd932`, image `glm53-tf:2.9.1`). NVIDIA's PyTorch container 26.09 with Triton kept at 3.7.1, on hosts updated to DGX OS 7.6.0 (kernel `7.0.0-1019-nvidia` with `kho=off`, driver 580.178.04); the engine is 2.9.0's ([decisions](docs/decisions.md)). On both weights at both TP sizes with image input on, the decode check gave 2.9.0's token ids and `bench --kinds edit` the reference reply; at TP=2 the NLL set and tool-eval-bench equalled 2.9.0's, and on the pinned weights at both TP sizes the image checks passed.

| 2.9.1, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.94 / 27.53 / 36.05 | 57.83 / 37.85 / 45.32 | 59.23 / 38.19 / 48.84 | 73.32 / 49.97 / 60.87 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 43.03 | 57.79 | 57.17 | 78.01 |
| `bench --kinds edit` (tok/s, median) | 58.23 | 75.04 | 77.00 | 98.24 |
| A prompt cut 3 s into its prefill: the next request answered after (s), against the same prompt's uncut fill | 2.09 against 49.52 (66,846 tokens) | — | 1.08 against 43.31 (72,848 tokens) | — |
| Prefill of 38,960 tokens (s, two prompts) | 28.93 / 67.03 (the second with heat waits, below) | — | 24.30 / 22.91 | — |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | — | — |
| tool-eval-bench, directly / through the tool-argument gate | 92 / 93 | 89 / 91 | — | — |

- **Against 2.9.0.** The same token ids in the decode check, the same replies in `bench --kinds decode` and `bench --kinds edit`, at TP=2 the same NLL and the same tool-eval-bench scores and outcome, and `top_k` 0's tokens still the host rule (37.48 and 24.12 tok/s). The decode check, `bench --kinds decode` and edits within +0.8% to +3.7%. One launch each, after the hosts' update.
- **Heat waits in the second prompt at TP=2.** It waited 19 times between chunks, 38 s in all, on `TF_GLM_HEAT_CEILING`: the room was warm, and the look-ahead counted the zone's climb back after a rest as a chunk's rise ([decisions](docs/decisions.md#heat)). The same image's earlier launch that day, without waits, took 30.24 / 28.92 s.
- **Not measured on this release** (`—`): as on 2.9.0, whose results stand for this engine on the default path.

**2.9.0** (2026-10-11, engine `d2dd932`, image `glm53-tf:2.9.0`). A prompt whose client left stops after the chunk being filled, on every rank, and the server tokenizes with Python's GIL released; the engine is otherwise 2.8.0's ([decisions](docs/decisions.md)). On both weights at both TP sizes with image input on, the decode check gave 2.8.0's token ids and `bench --kinds edit` the reference reply; at TP=2 the NLL set and tool-eval-bench equalled 2.8.0's, and on the pinned weights at both TP sizes the image checks passed.

| 2.9.0, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.30 / 27.20 / 35.47 | 56.97 / 37.38 / 44.77 | 58.08 / 36.83 / 48.29 | 71.71 / 48.84 / 59.80 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 42.37 | 57.25 | 56.70 | 76.62 |
| `bench --kinds edit` (tok/s, median) | 57.63 | 74.00 | 76.32 | 96.27 |
| A prompt cut 3 s into its prefill: the next request answered after (s), against the same prompt's uncut fill | 2.12 against 54.58 (72,848 tokens) | — | 1.04 against 41.92 (69,847 tokens) | — |
| Prefill of 38,960 tokens (s, two prompts) | 29.99 / 29.55 | — | 24.08 / 24.39 | — |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | — | — |
| tool-eval-bench, directly / through the tool-argument gate | 92 / 93 | 89 / 91 | — | — |

- **A cut prompt.** About 70,000 tokens streamed, the client's socket closed 3 s in, then at once a short request (thinking off, 8 tokens); afterwards the same prompt with another nonce, not cut. Without the stop the ranks would fill the cut prompt to its end before the short request.
- **Against 2.8.0.** The same token ids in the decode check, the same replies in `bench --kinds decode` and `bench --kinds edit`, at TP=2 the same NLL and the same tool-eval-bench scores and outcome, and `top_k` 0's tokens still 2.7.0's host rule (36.65 and 23.88 tok/s). `bench --kinds decode` and edits within −0.5% to +0.2%; the decode check within −3.5% to +0.3% (a decode check prompt fills in one chunk, so the stop's vote never runs there). One launch each.
- **Not measured on this release** (`—`): as on 2.8.0, whose results stand for this engine on the default path.

**2.8.0** (2026-10-09, engine `7458b11`, image `glm53-tf:2.8.0`). A request at `top_k` 0 draws on the device, with the host rule's tokens; the engine is otherwise 2.7.0's ([decisions](docs/decisions.md)). On both weights at both TP sizes with image input on, the decode check gave 2.7.0's token ids and `bench --kinds edit` the reference reply; at TP=2 the NLL set and tool-eval-bench equalled 2.7.0's, and on the pinned weights at both TP sizes the image checks passed.

| 2.8.0, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.57 / 27.30 / 35.69 | 56.88 / 37.37 / 44.66 | 58.86 / 38.17 / 48.50 | 71.59 / 48.80 / 59.67 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 42.59 | 57.14 | 56.79 | 76.48 |
| `bench --kinds edit` (tok/s, median) | 57.75 | 74.08 | 76.54 | 96.52 |
| `top_k` 0, temperature 1, `top_p` 0.95, two prompts (tok/s, against 2.7.0) | counting 12.64 → 36.80, a story 8.82 → 23.98 | — | — | — |
| Prefill of 38,960 tokens (s, two prompts) | 30.41 / 28.95 | — | 24.00 / 22.99 | — |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | — | — |
| tool-eval-bench, directly / through the tool-argument gate | 92 / 93 | 89 / 91 | — | — |

- **`top_k` 0.** Temperature 1, `top_p` 0.95, seed 7, thinking off, 512 tokens, two requests each, against the same requests on 2.7.0 in a launch before the window: every reply's tokens equal 2.7.0's, and the device draw runs about as fast as the server's default `top_k` 20 (38.70 and 24.12 tok/s, unchanged from 2.7.0's 38.67 and 24.13).
- **Against 2.7.0.** The same token ids in the decode check, the same replies in `bench --kinds decode` and `bench --kinds edit`, and at TP=2 the same NLL to four places and the same tool-eval-bench scores and outcome. The decode check, `bench --kinds decode` and edits within −0.2% to +0.4% on both weights at both TP sizes.
- **Not measured on this release** (`—`): as on 2.7.0, whose results stand for this engine on the default path.

**2.7.0** (2026-10-09, engine `9cdd935`, image `glm53-tf:2.7.0`). A request that names no reasoning effort gets `high` ([serving defaults](#serving-defaults)); the checks name their own effort. The engine's prompt chunks score the DSA pools one row and 32 pool blocks a program, with the same bits; `/v1/responses` accepts OpenAI's `include` values; a loop guard is there, off by default ([decisions](docs/decisions.md)). Before the release, in six launches at TP=3 on the pinned weights, three without the new pool scores and three with them, the median prefill without its heat waits fell from 154.15 to 145.12 s at 226,154 tokens and from 155.16 to 146.11 s at 227,369 tokens (5.8-5.9%); every launch with them ran faster than every launch without, and the replies were the same. On both weights at both TP sizes with image input on, the decode check gave 2.5.0's token ids and `bench --kinds edit` the reference reply; at TP=2 the NLL set and tool-eval-bench equalled 2.5.0's, and on the pinned weights at both TP sizes the image checks passed.

| 2.7.0, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.48 / 27.26 / 35.65 | 56.99 / 37.42 / 44.75 | 58.91 / 38.03 / 48.60 | 71.45 / 48.80 / 59.71 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 42.55 | 57.22 | 56.80 | 76.45 |
| `bench --kinds edit` (tok/s, median) | 57.70 | 74.04 | 76.43 | 96.30 |
| Prefill of 38,960 tokens (s, two prompts) | 29.24 / 29.10 | — | 23.14 / 23.08 | — |
| Long inputs (262K and 1M tokens), the tool gate at 1M tokens | — | — | — | — |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | — | — |
| tool-eval-bench, directly / through the tool-argument gate | 92 / 93 | 89 / 91 | — | — |

- **Against 2.5.0.** The same token ids in the decode check, the same replies in `bench --kinds decode` (at TP=3 the pinned weights' is again `27fc79ab52b7830f`, the others `7754eb09bd6615fd`) and `bench --kinds edit`; at TP=2 the same NLL to four places and the same tool-eval-bench scores and outcome (directly both weights fail the Safety Gate on TC-43, through the gate both pass). The decode check, `bench --kinds decode` and edits within −0.7% to +0.3% on both weights at both TP sizes.
- **Prefill of 38,960 tokens.** 0.8-4.5% shorter than 2.5.0's on the pinned weights, one launch each; the A/B above measures the pool scores.
- **Not measured on this release** (`—`). The default path's token ids equal 2.5.0's and 2.4.0's at both TP sizes, so 2.4.0's NLL at TP=3, long-input and 1M tool-gate results stand for this engine; AXL's prefill and the image checks on AXL were not run.

**2.5.0** (2026-10-08, engine `8a36b2c`, image `glm53-tf:2.5.0`). `bench --kinds decode` sends a new request that counts until the limit ([benchmark method](docs/benchmarks.md#prefill-and-decode-speed)), and the engine takes upstream pull requests #285 and #294, a quoted `<|image|>` kept as text beside a real picture and TR3's new name; on the default path (no image, no tools) the tokens are 2.4.0's ([decisions](docs/decisions.md#engine)). On both weights at both TP sizes with image input on, the decode check gave 2.4.0's token ids and `bench --kinds edit` the reference reply; at TP=2 the NLL set equalled 2.4.0's to four places on both weights. On the pinned weights at both TP sizes the image checks passed, and a conversation that quotes `<|image|>` beside a real picture answered 200 and read the picture.

| 2.5.0, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.59 / 27.37 / 35.71 | 57.03 / 37.45 / 44.70 | 58.82 / 38.04 / 48.46 | 71.97 / 48.83 / 59.70 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode`, 2.5.0's request (tok/s, median) | 42.63 | 57.09 | 56.73 | 76.55 |
| `bench --kinds edit` (tok/s, median) | 57.81 | 74.20 | 76.26 | 96.50 |
| Prefill of 38,960 tokens (s, two prompts) | 30.17 / 29.32 | — | 24.24 / 23.45 | — |
| Long inputs (262K and 1M tokens), the tool gate at 1M tokens | — | — | — | — |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | — | — |
| tool-eval-bench, directly / through the tool-argument gate | 92 / 93 | 89 / 91 | — | — |

- **`bench --kinds decode`.** Every row stopped at the limit (`finish_reason` `length`, 512 tokens), with the same reply in each launch's three runs. At TP=2 both weights gave the same reply, and AXL ran 34% over the pinned weights. The row does not compare with earlier releases' `bench --kinds decode`, whose request let the model end its reply and then decoded what it made up past its end.
- **Pinned at TP=3.** The pinned weights' reply at TP=3 also counts to the limit, but thinks for 41 tokens before the count, 11 more than AXL's, so the TP=3 replies are not the same token for token and AXL's 35% over the pinned weights there compares two counts, not one text.
- **tool-eval-bench** (TP=2, 69 scenarios, the invocation of [validation](docs/validation.md#tools-through-the-tool-argument-gate)). Directly both weights failed the Safety Gate on TC-43, an empty `query` for `web_search`; through the gate both passed. The same scores and outcome as on 2.4.0.
- **Not measured on this release** (`—`). The default path's token ids equal 2.4.0's at both TP sizes, so 2.4.0's NLL at TP=3, long-input and 1M tool-gate results stand for this engine; AXL's prefill and the image checks on AXL were not run.
- **Against 2.4.0.** The decode check and edits within −0.8% to +0.1% on both weights at both TP sizes.
- **Prefill.** The first of the two pinned TP=2 prompts took 2.9% longer than the second; the two prefill speeds stay open ([validation](docs/validation.md#prefill-and-decode-speed)).

**2.4.0** (2026-10-08, engine `ab8e741`, image `glm53-tf:2.4.0`). The published AXL weights can be served as an option, and copy drafts no longer cut after a miss (`MISS_MOST` 5); on the pinned checkpoint the engine is otherwise 2.3.0's, with the same tokens ([decisions](docs/decisions.md#precision-and-memory)). On both weights at both TP sizes with image input on, the decode check gave the reference token ids of its weights, the NLL set the values below and `bench --kinds edit` the reference reply; the image checks passed on the pinned weights.

| 2.4.0, image input on | Pinned, TP=2 | AXL, TP=2 | Pinned, TP=3 | AXL, TP=3 |
|---|---|---|---|---|
| Decode check count / prose / code (tok/s) | 43.80 / 27.54 / 36.01 | 57.30 / 37.53 / 44.80 | 59.20 / 38.19 / 48.68 | 71.89 / 49.03 / 59.90 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 3.813 / 2.004 / 2.893 | 4.056 / 2.222 / 3.234 | 3.631 / 2.060 / 2.994 |
| `bench --kinds decode` (tok/s, median) | 36.82 | 37.57 | 55.68 | 68.00 |
| `bench --kinds edit` (tok/s, median) | 58.13 | 74.26 | 76.40 | 96.75 |
| Prefill of 38,960 tokens (s, two prompts) | 30.22 / 29.59 | 28.73 / 28.81 | 24.51 / 23.52 | 23.22 / 22.86 |
| Three passphrases at 262,113 tokens | — | 3 of 3, first token after 227.5 s, 8.0 s of it heat waits | — | — |
| Three passphrases at 1,035,295 tokens | — | — | 3 of 3, first token after 1,588.4 s, 480.5 s of it heat waits | 3 of 3, first token after 1,524.1 s, 454.4 s of it heat waits |
| Rank 0's startup estimate (GiB) | 101.35 | 96.71 | 81.93 | 78.68 |
| Teacher-forced NLL, ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5556 / 2.9438 / 1.3334 / 0.6474 | 2.5313 / 2.9001 / 1.3101 / 0.6237 | 2.5590 / 2.9471 / 1.3357 / 0.6439 |

- **Weights.** AXL ran faster than the pinned weights at both TP sizes, at a higher NLL; its task-level quality was not measured in this acceptance. Its decode-check token ids are its own reference ([validation](docs/validation.md#decode-check)), the same in two launches at TP=2, and its edit reply equals the pinned weights'. At TP=2 AXL's `bench --kinds decode` ran only 2% over the pinned weights' while its decode check and edits ran more than a fifth over. The cause, found after the release, was the request: both weights ended the count by themselves after about 100 tokens, and the rest of the 512 was a conversation each model made up past its end, which differed between the weights, so the row compared different texts. 2.5.0's request counts until the limit (2.5.0 above).
- **Heat.** On the pinned weights the hottest host peaked at 92.6 °C, as with 2.3.0. During AXL's 1M-token prompt at TP=3 one host read 94.4 °C once in a log of the hosts' temperatures the acceptance took every second (93.5 °C in the thermal watch's readings, every 2 s), about 4 minutes in, after more than 30 s at 90.5-91 °C: the check before that chunk read below 92 °C with the last chunk's rise near 0, so the look-ahead did not hold it. The next check started a wait, and the later waits allowed for rises of 12-15 °C; the thermal watch did not stop the engine. The reading was accepted since the wait started within a second ([Next Action](#next-action)).
- **Tool gate at 1M tokens** (pinned, TP=3). The first call answered 200 after 1,553.3 s, 448.4 s of it heat waits, with `tool_calls`; the repair's second call answered 200 in 3.6 s from the kept prompt.
- **Against 2.3.0.** On the pinned weights edits ran 1.1% faster at TP=2 (57.49 → 58.13 tok/s) and 0.2% at TP=3 (76.22 → 76.40); the decode check and `bench --kinds decode` within ±1.3%.
- **Prefill.** The first of the two pinned TP=2 prompts took 2.1% longer than the second; the two prefill speeds stay open ([validation](docs/validation.md#prefill-and-decode-speed)).

**2.3.0** (2026-10-07, engine `7410d1d`, image `glm53-tf:2.3.0`). The prefill heat wait also looks one chunk ahead (`TF_GLM_HEAT_CEILING` 93 °C); the engine is otherwise 2.2.0's, with the same tokens ([decisions](docs/decisions.md#heat)). At both TP sizes with image input on, the decode check gave the reference token ids and texts, the NLL set the reference values, and the image checks passed.

| 2.3.0, image input on | TP=2 | TP=3 |
|---|---|---|
| Decode check count / prose / code (tok/s) | 43.61 / 27.32 / 35.69 | 58.44 / 38.14 / 48.71 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 4.024 / 2.222 / 3.234 |
| `bench --kinds decode` (tok/s, median of three) | 36.54 | 55.40 |
| `bench --kinds edit` (tok/s, median of three) | 57.49 | 76.22 |
| Prefill of 38,960 tokens (tok/s) | 1,254.3 / 1,329.9 | 1,559.9 / 1,665.6 |
| Three passphrases at 1,035,295 tokens | — | 3 of 3, first token after 1,440.6 s, 350.3 s of it heat waits |

- **Heat.** During the 1M-token prompt the hottest host peaked at 92.6 °C and no host read 94 °C (2.2.0: 94.3 °C once). Late chunks rose 4 to 8.6 °C, so the look-ahead waited for 84 to 88 °C before them: 350.3 s of waits against 2.2.0's 64.1 s, the prefill without its waits 1,089 s against 1,090 s.
- **Prefill.** At both TP sizes the first of the two prompts ran under the second (5.7% at TP=2, 6.3% at TP=3); the two prefill speeds stay open ([validation](docs/validation.md#prefill-and-decode-speed)).

**2.2.0** (2026-10-06, engine `440e631`, image `glm53-tf:2.2.0`). Decode work that leaves the tokens unchanged: copy drafts, KDA decode windows on the three-kernel chain, per-shape tiles for the BF16 decode matmuls, and no unread copy of the DSA key and value rows ([decisions](docs/decisions.md#decode)). At both TP sizes with image input on, the decode check gave the reference token ids and texts and the image checks passed; the counting task's acceptance length rose (copy drafts), the others held.

| 2.2.0, image input on | TP=2 | TP=3 |
|---|---|---|
| Decode check count / prose / code (tok/s) | 43.69 / 27.42 / 35.80 | 58.52 / 38.11 / 48.70 |
| MTP acceptance length, same tasks | 3.961 / 2.098 / 3.180 | 4.024 / 2.222 / 3.234 |
| `bench --kinds decode` (tok/s, median of three) | 36.56 | 55.68 |
| `bench --kinds edit` (tok/s, median of three; copy drafts on / off at TP=2 in the A/B) | 57.43 (A/B 57.6 / 43.0) | 76.29 |
| Prefill of 38,960 tokens (tok/s) | 1,285.3 / 1,290.6 | 1,607.1 / 1,668.8 |
| Three passphrases at 1,035,295 tokens | — | 3 of 3, first token after 1,154.3 s, 64.1 s of it heat waits |

- **Heat.** During the 1M-token prompt one host read 94.3 °C once, for one second, near the end, where a prompt chunk adds about 7 °C after the check between chunks; the wait then brought it to 78.5 °C in 2 s and the thermal watch (two readings in a row at or above 94 °C) did not stop it. The prefill without its waits took 1,090 s against 2.0.0's 1,095 s: the heat behaviour is not this release's change ([Next Action](#next-action)).
- **Prefill.** Both TP=2 prompts ran about 3% under the A/B's 1,326-1,332 tok/s, and the first TP=3 prompt about 3.7% under the second; the two prefill speeds stay open ([validation](docs/validation.md#prefill-and-decode-speed)).

**2.1.4** (2026-10-06, engine `a265436`, image `glm53-tf:2.1.4`). A new conversation after a long one no longer copies and drops the kept prompts first (TensorFold pull request #421). At TP=2 with image input on, the decode check gave 2.1.1's token ids and texts and the image checks passed; after a conversation of 247,330 tokens over 11 turns, a new one kept `MemAvailable` at 11–12 GiB on rank 0 and 12–15 GiB on rank 1.

**2.1.1** (2026-10-05, engine `1a3fb17`, image `glm53-tf:2.1.1`). Each image of a request is its own call of the image tower. At TP=2 with image input on, the decode check gave 2.1.0's token ids, texts and acceptance lengths, and the image checks passed, with two images of one size read alike one at a time and together.

| 2.1.1, TP=2, image input on | |
|---|---|
| Decode check count / prose / code (tok/s) | 41.62 / 27.03 / 35.37 |
| Prefill of 38,960 tokens, three back to back without cooling (tok/s) | 1,327.0 / 1,326.8 / 1,322.8 |

**2.1.0** (2026-10-05, engine `9a1c7cc`, image `glm53-tf:2.1.0`). The engine moved onto upstream v0.6.5 and gained image input; TP=2 took four NCCL channels. At both TP sizes the decode check gave 2.0.0's token ids and acceptance lengths ([validation](docs/validation.md#decode-check) gives its texts' new hashes), with image input off and on; at TP=2 the NLL set equalled 2.0.0's at full precision. The rows below are 2.0.0's unless the table says otherwise; the other measurements were not repeated, since the prompt and decode paths give the same tokens.

| 2.1.0 | TP=2 | TP=3 |
|---|---|---|
| Decode check count / prose / code (tok/s) | 41.67 / 27.02 / 35.38 | 52.37 / 37.92 / 48.41 (image input on) |
| Prefill of 38,960 tokens (tok/s, the second and third of three; the first 1,221.5) | 1,331.1 / 1,329.9 | — |
| [Image checks](docs/validation.md#image-input) (`VISION=1`) | all passed | all passed |

**2.0.0.** Taken on 2026-10-04 on the reference hosts (MSI EdgeXpert, GPU clock capped at 2,200 MHz). The engine was the release (`b44c2f1`), the build one printed line before it, or a build before the heat wait, which only changes when prompt chunks run; the notes say which. The [validation page](docs/validation.md) has the commands and reference values. The 1.x column is from [1.x's benchmarks](../v1/docs/benchmarks.md), its NLL from [the NLL set on 1.26.0's defaults](../v1/docs/benchmarks.md#the-nll-set-on-1260s-distributed-defaults-2026-10-02).

| Measurement | TP=2 | TP=3 | 1.x |
|---|---|---|---|
| Decode check count / prose / code (tok/s) | 41.04 / 26.73 / 34.85 | 52.47 / 37.99 / 48.47 | TP=2 defaults 32.59 / 21.12 / 28.21; TP=3 AXL 51.00 / 30.10 / 39.48 |
| MTP acceptance length, same tasks | 3.821 / 2.098 / 3.180 | 3.549 / 2.222 / 3.234 | — |
| Prefill of 38,960 tokens (tok/s, median of three; TP=3 cooled before each, TP=2 back to back after one cooling) | 1,329.9 | 1,668.5 (1,671.4 with the heat wait off) | TP=2 defaults 1,233.4 (38,962 tokens) |
| Decode after a short fixed prompt, 512 tokens (tok/s) | 35.31 | 52.93 | TP=2 defaults 27.18 |
| Window (tokens) | 300,000 (567,255 with `--context 0`) | 1,048,576 | 262,144 (TP=2) |
| Passphrase at 199,652 tokens | correct, first token after 163.7 s | correct, first token after 133.2 s | TP=3 AXL 150.5 s |
| Three passphrases at 1,036,859 tokens | — | 3 of 3, first token after 1,264.8 s, 170.1 s of it heat waits | TP=3 AXL 1,058 s (1,038,423 tokens) |
| Teacher-forced NLL on the NLL set (`config/nll_set.json`), ja / en / code / math | 2.5474 / 2.9257 / 1.3184 / 0.6250 | 2.5313 / 2.9001 / 1.3101 / 0.6237 | TP=2 defaults (1.26.0) 2.5412 / 2.9079 / 1.3145 / 0.6285 |
| tool-eval-bench through the tool-argument gate | 93/100, Safety Gate passed | 91/100, Safety Gate passed | TP=2 AXL 90/100 |
| A client disconnect or a stop string mid-reply | stops within a round, the next request starts at once | same | — |

- **Repeatability.** TP=2 and TP=3 do not give bit-identical outputs to each other or to 1.x, because the ranks split the sums differently. Each repeats itself: within a launch, across launches, with one or two rails, and with heat waits happening, the decode check gave one completion per task, the [reference hashes](docs/validation.md#decode-check). The NLL equals the [reference values](docs/validation.md#teacher-forced-nll), taken on builds before the release, at full precision.
- **Which engine.**
  - The decode check ran on the release at TP=2 and on the build one printed line before it at TP=3.
  - The TP=3 prefill and the 1M-token prompt ran on the build one printed line before the release.
  - The other rows ran on the build before the heat wait.
- **Heat.** During the 1M-token prompt the hottest host held at about 92 °C, waited about 80 times for a few seconds each, and peaked at 92.8 °C. Without the wait the same prompt reached 94 °C after six and a half minutes, and the [thermal watch](../host/README.md#during-long-runs) stopped the engine. Prefill runs at one of two speeds about 7.5% apart, and heat does not explain which ([prefill and decode speed](docs/validation.md#prefill-and-decode-speed)). Cool the hosts between long requests.
- **tool-eval-bench** used the same 69 scenarios and invocation as 1.x's. Both TP sizes failed TC-61 only.

## Limits

- **One sequence at a time.** The engine's CUDA path decodes one GLM request at a time; the others wait their turn.
- **Images take memory at TP=2.** With image input on, the tower takes part of the memory for other conversations' kept prompts ([serving defaults](#serving-defaults)); `VISION=0` on every rank gives the 3 GiB back.
- **The published AXL weights trade quality for speed.** Their NLL is higher on every domain of the set, and at TP=2 tool-eval-bench gave 89 directly and 91 through the tool-argument gate against the pinned weights' 92 and 93 ([measured on the release](#measured-on-the-release)); HLE was not run on them on 2.x. Every rank serves the same checkpoint.
- **TP=3 refuses DFlash2 and EXL3.** Both split only over two ranks. This line uses neither: `serve.sh` passes `--drafter none` and the checkpoint is NVFP4.
- **Streamed replies.** With drafts, one round can cross from thinking into the answer, so one delta can carry both `reasoning_content` and `content`. A client that reads only one field per delta loses text; non-streamed replies are whole.
- **FP8 KV is lossy** against BF16 KV, as in 1.x; drafted replies still equal serial ones. On four short texts the two caches gave NLL within 0.011 of each other (2026-10-02).
- **Two or three hosts with ConnectX-7 links**, as in 1.x. Other world sizes, other hardware and concurrent requests are outside what was measured.

## Repository Layout

The 2.x files live in `v2/`. The image is built from the checkout root, where the licenses are; the Python tools run from `v2/` as `python -m glm53_tf <command>`. The host tools and the host and fabric pages every line shares are at the checkout root ([`host/`](../host/README.md), [`docs/`](../docs/README.md)).

```
v2/
  README.md         this page (each .md has a .ja.md beside it)
  SETUP.md          the deployment runbook
  CHANGELOG.md      the 2.x releases; a v2.* tag publishes its section
  glm53_tf/         the Python tools: download, verify-download, tool-gate,
                    decode-check, decode-divergence, score-nll, bench, long-input
  config/           model.lock.json (the pinned checkpoint), axl.lock.json (the published AXL weights),
                    nll_set.json (the NLL set, a byte copy of 1.x's)
  requirements/     huggingface.lock.txt: the Hugging Face client for the download and its verification
  docker/           Dockerfile: the image, with the engine pinned by TENSORFOLD_REF
  scripts/          create_container.sh  the serving container on each host
                    build_ext.sh         the engine's CUDA extensions, once per image
                    serve.sh             one rank, with the serving defaults
                    cluster.sh           start, stop and status of every rank from a control machine
                    hostwatch.sh         the memory guard (stops the engine below 5 GiB MemAvailable)
  examples/         the reference hosts' rank files and cluster files, TP=2 and TP=3
  docs/             validation.md  the acceptance checks and reference values
                    benchmarks.md  how the release figures were taken
                    operations.md  failures and routine changes: a rank that stops, a new image, handing hosts to 1.x
                    decisions.md   what was tried for 2.x, adopted or rejected, and why
  tests/            CPU tests of glm53_tf/ and of the facts these pages quote
  pyproject.toml    the 2.x version
```

## Other Recipes on TensorFold

Public recipes that serve GLM-5.3-Flash on TensorFold. This table owns their links, their licenses as read on 2026-10-04 and what this line took from each; the recipes on other engines are in [1.x's table](../v1/README.md#other-glm-53-flash-recipes-for-dgx-spark-systems). Their measurements use other weights and settings and do not compare with the ones above.

| Recipe | License | What this line took from it |
|---|---|---|
| [ashhart/TensorFold](https://github.com/ashhart/TensorFold) | Apache-2.0 (MIT up to 0.5.0) | The engine. The release branch is upstream v0.6.5 plus its own commits. Upstream froze its Python engine (issue #286) and answered each of this line's issues and pull requests on 2026-10-06: none lands on 0.6.x; the Zig engine, where new work goes, will follow the designs of #308, #310, #339, #333 and #396-#399 once GLM is ported there, and declines the lossy FP8 cache (#309, #401) |
| [MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold) | Apache-2.0 | The FP8 latent KV follows its patch 0038, rewritten on v0.6.x and credited in the engine's notices (upstream issue #309). Copy drafts follow its patches 0007 and the first half of 0032, and the KDA decode windows its 0016c, credited the same way. The TP=3 shares use the same rule as its patch 0066 (cut at unit boundaries, the remainder to the lower ranks). Its upstream pull requests #301 (a stopped request ends on every rank) and #285 (a GLM tool call whose end token arrived before `</tool_call>`, from 2.5.0) are in the release as they are, and an image marker quoted in the conversation kept as text beside a real picture follows its patch 0080, rewritten. From 2.7.0 a prompt chunk's pool scores follow its patch 0086, rewritten for this tree's FP8 pooled keys, and the Responses API's `include` its 0093, rewritten; the loop guard is its 0091, taken with its test rewritten. It serves its own EXL3 checkpoint with DFlash2 drafts, up to eight requests at once and image and video input |
| [jakejharris/jspark3 v2.0.1](https://github.com/jakejharris/jspark3/releases/tag/v2.0.1) | Apache-2.0 (recipe); MIT (its engine, a fork of TensorFold 0.3.6.2) | Nothing. Three hosts at TP=3 on its own TensorFold fork with 4-bit MLX-format weights split across the hosts, DFlash2 drafts by default with `--drafter none` as its commercial path, a session cache on disk, measured with RigMark |

## Disclaimer

- **BIZ is an intent, not a promise** ([repository README](../README.md#biz)).
- **The acceptance is the reference hosts'.** A launch elsewhere, or on another image ID, is accepted by running [validation](docs/validation.md) there.
- **The engine is this line's own fork.** Upstream froze its Python engine (issue #286, 2026-10-06), so the release branch keeps its own commits for good; [other recipes](#other-recipes-on-tensorfold) says what upstream answered.

## Next Action

Each item is a trigger and what this line then does.

- Upstream TensorFold serves GLM-5.3-Flash on CUDA from its Zig engine (as of 2026-10-06 the Python engine is frozen, issue #286, and Zig CUDA serves no model yet; upstream said it would follow this line's designs from issues #308, #310 and #339 and pull requests #333 and #396-#399 there) → read it against the release branch and decide whether 2.x moves to it.
- Upstream releases another 0.6.x of the Python engine (0.6.6 was under test before the freeze: unoffered `<tool_call>` markup leaking into the reply text, #285 with #256; `--loop-guard` against a token repeated without end, #210 and #262 for #204; the open-file limit raised at start, #294) → read it against the release branch and follow it in a 2.x release (2.5.0 took #285 and #294; 2.7.0's loop guard is MiaAI-Lab's patch 0091, off by default).
- More than one sequence at a time: upstream closed MiaAI-Lab's pull request #243 (`--parallel N` on two ranks) with the freeze → this line takes it into its own release branch, then measures the published AXL weights at two sequences, as 1.x did.
- Upstream reopens the lossy KV cache question for GLM (it declined FP8 and 4-bit caches in issues #309 and #401, 2026-10-06), or this line moves to an engine without FP8 KV → measure BF16 KV's window first (TP=2 held 344,820 tokens against about 490K with FP8 on 2026-10-02).
- A host reads 94 °C twice in a row during a long prefill (once in 2.4.0's 1M-token acceptance, past the look-ahead: [measured on the release](#measured-on-the-release)), or its waits weigh on long prompts (480 s of the pinned prompt's 1,588 s) → check the heat within a chunk as well as between chunks, and measure the 1M-token prompt again.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 2.x changes.
