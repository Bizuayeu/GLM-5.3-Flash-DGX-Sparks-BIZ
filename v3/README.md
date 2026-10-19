# NVFP4 BIZ 3.x (TensorFold native)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2 or three hosts at TP=3. 3.0.0 was its first release, on upstream TensorFold 1.0.12; 3.1.0 moves it onto upstream 1.1.1. 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **Status.** 3.1.0 was accepted on the reference hosts on 2026-10-19 and 20 against the reference values of [validation](docs/validation.md), measured there, at TP=2 and TP=3 on the pinned checkpoint, with the containers on the efficiency cores ([measured on the release](#measured-on-the-release)). The acceptance ran the engine built from the release's commit, and the release image gave the same decode-check hashes and edit reply in a launch at each TP size. That is the scope of the claim; other hosts are qualified by running the same checks.
- **What it is.** Build steps, launch scripts and acceptance checks that serve the pinned checkpoint through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems.
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` are upstream TensorFold's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018 ([API](#api)).
- **Precision.** W4A16 for the routed experts and the dense MLP, BF16 elsewhere, BF16 KV (2.x keeps an FP8 KV cache). NVIDIA's model card measured its checkpoint under another recipe on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine, MIT weights that the operator downloads, and xgrammar (Apache-2.0) in the image for structured output; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image input (`serve.sh` starts the engine without `--vision`), the published AXL weights, more than one request at a time (the acceptance sent one at a time), harness integration (ZCode, Claude Code), other world sizes and hardware, full application quality and production reliability ([limits](#limits)).

## What It Is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93` ([`config/model.lock.json`](config/model.lock.json)), the same as 1.x and 2.x, derived from [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash). The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16.
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.1.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.1.1 plus two commits. One is the heat wait's look-ahead to a ceiling (`TF_HEAT_CEILING`, as 2.x has it). The other is kept to this line for TP=3: rank 0 hands its NCCL id to the other ranks in a file (`TF_GLM_NCCL_ID_FILE`), and each rank then takes `NCCL_COMM_ID`, through which the ranks' liveness lines reach rank 0, out of NCCL's environment, because NCCL cannot bootstrap through the ring's point-to-point `/32` addresses (until upstream's TP bootstrap, pull request #636). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256, and `/usr/share/doc/tf3/engine/` holds the engine's license and notices.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order. Nothing is built on the hosts: the kernels are in the binary.

## Requirements

- **Hosts**: two or three DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x or 2.x server on the same hosts is stopped first, and 2.x's container too, since it claims every GPU ([hand the hosts to 2.x](docs/operations.md#hand-the-hosts-to-2x)).
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Both rails of each port are used.
- **Host kernel**: as in 1.x and 2.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)).
- **GPU clock** capped on every host ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 3.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, as in 1.x and 2.x ([what you deploy](../v1/README.md#what-you-deploy-and-supported-hardware)), plus the image.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v3/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v3.*` tag on every host.

```sh
# Once, from v3/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# One host builds the image, the others load it; compare the image IDs (SETUP §3)
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.1.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.1.0 ~/glm53-tf3
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

## Serving Defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank:

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | BF16 latent and index keys (the engine's only form) | same |
| Drafts | the checkpoint's MTP head (the engine's default) | same |
| Window (`--context`) | 245,760 tokens: about the most one stream fits beside the model on each rank | 1,048,576 tokens (the model's limit) |
| Requests decoded at once (`--parallel`) | 1 (`PARALLEL=1`); an empty `PARALLEL=` leaves it to the engine, which sizes the streams and the prompt cache from the memory free at start | same |
| Prompt cache (kept prompt states, at the starts of 2,048-token chunks) | what the window leaves: 5.2 to 6.3 GiB on the reference hosts, with the memory free at the start (rank 0's load line; 4.4 to 4.5 GiB with 3.0.0's engine) | 16.0 GiB on the reference ring |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file; rank 0's address and port as `NCCL_COMM_ID` | two rails, four channels, the IB transport named, subnet-aware routing; rank 0's address and port as `NCCL_COMM_ID` for the ranks' liveness lines alone, and rank 0's NCCL id handed over in a file |
| BF16 linears | upstream's tiled kernels (the engine's default) | the engine's glue kernels (`TF_GLM_MM=0` in the rank files): the tiled ones refuse a TP=3 rank's KDA width (upstream issue #1067) |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`); also while that zone plus the rise of the last chunk run straight after another would pass 93 °C (`TF_HEAT_CEILING`) | same |
| Image input | none: `serve.sh` passes no `--vision`, so image parts are refused with 400 (upstream reads images on GLM's CUDA engine with it since 1.1.0; not validated here) | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**Why one request at a time.** With `--parallel` unset the engine asks for eight streams and serves as many as fit, so the number of streams and the room left for the prompt cache change from one start to the next with the memory free at that moment (at TP=3 one start took two streams and 0.1 GiB of prompt cache). One stream, as 2.x serves, keeps the window the same at every start, and the prompt cache moves only with the memory free (5.2 to 6.3 GiB at TP=2). At TP=2 3.0.0's engine fitted no second stream beside the 245,760-token window (it needed 4.55 GiB on each rank, and rank 1 had 4.41 GiB). 3.1.0's does: with `PARALLEL=` empty it took two streams of 3.16 GiB and left a 3.1 GiB prompt cache, against one stream's 6.3 GiB.

**Why 245,760 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token, so the pair holds a shorter window than 2.x's 300,000 tokens. 245,760 is about the most that fit one stream on the reference pair. `CONTEXT` in every rank file chooses another.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank, on rank 0 while it decodes and on the other ranks while they wait: one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2 with 3.0.0's engine, and the thermal watch stopped the engine at the seventh. 3.1.0's engine finished them on every core in the same 1,535 s as on the efficiency cores, but rank 0's host reached 93.0 °C, 1 °C under the stop, against 74.9 °C on the efficiency cores; two requests at once on every core reached 88.5 °C. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1 to 3% of speed and a start about 25 s longer ([measured on the release](#measured-on-the-release)). Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. Since 1.1.1 upstream's [runbook](https://github.com/ashhart/TensorFold/blob/v1.1.1/RUNBOOK.md) gives the same cores for each GB10 rank, from these measurements. `CPUSET=` gives the container every core.

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
| | `CHECKPOINT` | the pinned snapshot under `/hub` | the checkpoint directory inside the container, the same on every rank |
| | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, `TF_HEAT_CEILING` | `92`, `88`, `93` (°C) | the prefill heat wait and its look-ahead; the ceiling needs both bands; empty values for none; the same on every rank |
| | `TF_GLM_MM` | unset (the tiled kernels); `0` in the TP=3 examples | `0` runs the BF16 linears on the engine's glue kernels, which TP=3 needs until upstream fixes issue #1067; the same on every rank |
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

The engine also routes `/v1/responses` and Anthropic's `/v1/messages`, through the same chat path; the acceptance did not check them. On GLM's CUDA engine it refuses `logprobs` and `top_logprobs` for the generated tokens (400), image, audio and video parts when started without `--vision`, as `serve.sh` starts it (400), and `/v1/decisions` (400).

## Differences from 2.x

| | 2.x (TensorFold's Python engine) | 3.x (TensorFold's native engine) |
|---|---|---|
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.1.1 (3.0.0: 1.0.12), Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16; 245,760 tokens at TP=2, 1,048,576 at TP=3 |
| Requests at once | one | one by default; `PARALLEL` lets the engine share its decode rounds among more, within the memory the window leaves |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states at chunk starts in what the window leaves (5.2 to 6.3 GiB at TP=2, 16.0 GiB at TP=3); no entry count |
| Image input | accepted (`VISION=1`) | refused (`serve.sh` passes no `--vision`) |
| Published AXL weights | optional | not validated |
| Structured output, required tool calls | accepted, with xgrammar in the image | accepted, with xgrammar's `libtfgrammar` in the image; required tool calls in GLM's markup |
| `prompt_logprobs` | accepted | accepted on non-streamed `/v1/completions` |
| `clear_thinking` | honoured | not passed to the chat template ([limits](#limits)) |
| Reply fields | `tensorfold` with `accepted`, `drafted`, `rounds`, `cached`, `prefill_s`, `heat_wait_s`, `sha256` | `tensorfold` and `speculative` (above); cached tokens in `usage`; heat waits only in the log |
| Heat settings | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, `TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, `TF_HEAT_CEILING`, the same values |
| Image and container | `glm53-tf`, extensions built per container (`build_ext.sh`) | `glm53-tf3`, nothing built on the hosts |
| Container cores | every core | the efficiency cores unless `CPUSET` says otherwise |
| Tool-argument gate | the gate in front of the engine | the same gate, this line's copy run from `v3/` |

The two lines' containers both claim every GPU: run one line's engine at a time ([operations](docs/operations.md#hand-the-hosts-to-2x)).

## Measured on the Release

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
- **No image input.** `serve.sh` passes no `--vision`, and the engine answers image, audio and video parts with 400. Upstream's engine reads images on GLM's CUDA path with `--vision` since 1.1.0; this line has not accepted it. 2.x reads images.
- **No log-probabilities of generated tokens.** `logprobs` and `top_logprobs` are refused with 400; `prompt_logprobs` is served on non-streamed `/v1/completions` only.
- **`clear_thinking` is not passed to the chat template.** The native server passes the template only `enable_thinking`, `thinking_mode` and `reasoning_effort`; the pinned template takes a missing `clear_thinking` as false and keeps the reasoning of earlier turns that a client sends back. A client that sends earlier turns without their reasoning sees no difference.
- **Every rank keeps two CPU cores spinning**, rank 0 while it decodes and the others while they wait. The default container cores keep the CPU's zones below the thermal watch's stop at a cost of 1 to 3% in speed with 3.0.0's engine (with 3.1.0's the forty replies took the same time, and a start about 40 s longer); on every core, long runs of replies reached the stop with 3.0.0's engine and came within 1 °C of it with 3.1.0's ([why the efficiency cores](#serving-defaults)).
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
  config/           model.lock.json (the pinned checkpoint), engine.lock.json (the engine commit, the Zig
                    compiler and xgrammar), axl.lock.json (the published AXL weights), nll_set.json (the NLL set)
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
- **The engine is this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017 and #1018 became upstream's own in 1.1.1); the release branch keeps the rest.

## Next Action

Each item is a trigger and what this line then does.

- Upstream fixes issue #1067 (the tiled BF16 linears at a TP=3 rank's KDA width) in a release → move onto it, drop `TF_GLM_MM=0` from the TP=3 rank files and accept TP=3 again on the default kernels.
- Upstream's TP bootstrap (pull request #636) lands → start TP=3 on it and drop the NCCL id file from the release branch.
- Upstream takes pull request #1053 (the waiting ranks sleep while rank 0 has no stream) → follow it in a 3.x release and measure again whether the container still needs the efficiency cores.
- `chat_template_kwargs.clear_thinking` → pass it to the chat template as 2.x does, and offer it upstream.
- Image input (`--vision`, upstream's on GLM's CUDA engine since 1.1.0) and the published AXL weights on the native engine → accept them as 2.x did.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
