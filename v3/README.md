# NVFP4 BIZ 3.x (TensorFold native)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, without retraining or requantizing it, on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2 or three hosts at TP=3. 3.0.0 is its first release; 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

<!-- S6: the status line and the acceptance date from the window (records/20261018-s6) -->

- **What it is.** Build steps, launch scripts and acceptance checks that serve the pinned checkpoint through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems.
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` come to the native engine with this line's engine release ([API](#api)).
- **Precision.** W4A16 for the routed experts and the dense MLP, BF16 elsewhere, BF16 KV (2.x keeps an FP8 KV cache). NVIDIA's model card measured its checkpoint under another recipe on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine, MIT weights that the operator downloads, and xgrammar (Apache-2.0) in the image for structured output; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image input (the native engine refuses it on CUDA), the published AXL weights, more than one request at a time beyond [the checks run](#measured-on-the-release), harness integration (ZCode, Claude Code), other world sizes and hardware, full application quality and production reliability ([limits](#limits)).

## What It Is

- **Weights**: `nvidia/GLM-5.3-Flash-NVFP4` at revision `423acf37583782c51c142d145aef733d72943d93` ([`config/model.lock.json`](config/model.lock.json)), the same as 1.x and 2.x, derived from [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash). The routed experts and the dense MLP run as W4A16 from the checkpoint's NVFP4 blocks; attention, the shared experts and the head stay BF16.
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.0.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.0.12 plus `prompt_logprobs`, structured output and GLM's tool markup for required tool calls on GLM's CUDA engine (offered upstream as pull requests #1016, #1017 and #1018), the heat wait's look-ahead to a ceiling (`TF_HEAT_CEILING`, as 2.x has it), and one commit kept to this line: rank 0 hands its NCCL id to the other ranks in a file (`TF_GLM_NCCL_ID_FILE`), because the ring's point-to-point `/32` addresses cannot bootstrap through `NCCL_COMM_ID` (until upstream's TP bootstrap, pull request #636). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256.
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
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.0.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.0.0 ~/glm53-tf3
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

<!-- S6: TP=3's prompt cache from s6-p3's load line -->

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| KV cache | BF16 latent and index keys (the engine's only form) | same |
| Drafts | the checkpoint's MTP head (the engine's default) | same |
| Window (`--context`) | 245,760 tokens: about the most one stream fits beside the model on each rank | 1,048,576 tokens (the model's limit) |
| Requests decoded at once (`--parallel`) | 1 (`PARALLEL=1`); an empty `PARALLEL=` leaves it to the engine, which sizes the streams and the prompt cache from the memory free at start | same |
| Prompt cache (kept prompt states, at the starts of 2,048-token chunks) | what the window leaves: 4.4 GiB on the reference pair (rank 0's load line) | |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file; rank 0's address and port as `NCCL_COMM_ID` | two rails, four channels, the IB transport named, subnet-aware routing; rank 0's NCCL id handed over in a file |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`); also while that zone plus the rise of the last chunk run straight after another would pass 93 °C (`TF_HEAT_CEILING`) | same |
| Image input | none: the native engine reads no images on CUDA | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**Why one request at a time.** With `--parallel` unset the engine asks for eight streams and serves as many as fit, so the number of streams and the room left for the prompt cache change from one start to the next with the memory free at that moment (at TP=3 one start took two streams and 0.1 GiB of prompt cache). One stream, as 2.x serves, keeps the window and the prompt cache the same at every start. At TP=2 a second stream does not fit beside the 245,760-token window (it needs 4.55 GiB on each rank, and rank 1 had 4.41 GiB); two requests at once need a smaller `CONTEXT`.

**Why 245,760 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token, so the pair holds a shorter window than 2.x's 300,000 tokens. 245,760 is about the most that fit one stream on the reference pair. `CONTEXT` in every rank file chooses another.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank, on rank 0 while it decodes and on the other ranks while they wait: one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2, and the thermal watch stopped the engine at the seventh. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1.1% slower decode, 2.7% slower prefill, a 200,000-token prompt 2.5% slower and a start 25 s longer. Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. `CPUSET=` gives the container every core.

## Configuration

Three places set a deployment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git.

| Where | Setting | Default | Meaning |
|---|---|---|---|
| Rank file (`/work/rank.env`, sourced by `serve.sh`) | `MASTER` | none, required | rank 0's address on the link, the same on every rank |
| | `NCCL_PORT` (TP=2) | `29583` | rank 0's NCCL bootstrap port on `MASTER` |
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
| `serve.sh` arguments | after `TP RANK RANK_ENV` | none | passed to `tensorfold-native serve` after the defaults, so they win (`--context 131072`) |
| Cluster file (`cluster.sh`) | `TP`, `HOSTS`, `CHECKOUT` | none, required | the TP size, SSH names in rank order, this repository's root on every host |
| | `SSH`, `CONTAINER`, `WORK` | `ssh -o ConnectTimeout=20`, `glm53-tf3`, `$HOME/glm53-tf3` | how to reach the hosts, the container, the host directory at `/work` |
| `create_container.sh` | `IMAGE WORK_DIR`, `CONTAINER`, `HF_HUB` | `glm53-tf3`, `~/.cache/huggingface/hub` | the image, the work directory (rank file, NCCL id, logs), the container name, the Hugging Face cache mounted read-only at `/hub` |
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

The engine also routes `/v1/responses` and Anthropic's `/v1/messages`, through the same chat path; the acceptance did not check them. On GLM's CUDA engine it refuses `logprobs` and `top_logprobs` for the generated tokens (400), image, audio and video parts (400) and `/v1/decisions` (400).

## Differences from 2.x

| | 2.x (TensorFold's Python engine) | 3.x (TensorFold's native engine) |
|---|---|---|
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.0.12, Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16; 245,760 tokens at TP=2, 1,048,576 at TP=3 |
| Requests at once | one | one by default; `PARALLEL` lets the engine share its decode rounds among more, within the memory the window leaves |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states at chunk starts in what the window leaves (4.4 GiB at TP=2); no entry count |
| Image input | accepted (`VISION=1`) | refused |
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

<!-- S6: the 3.0.0 table and notes from the window (records/20261018-s6) -->

## Limits

- **One request at a time by default.** More need `PARALLEL` and, at TP=2, a smaller window ([serving defaults](#serving-defaults)).
- **No image input.** The engine refuses `--vision` on GLM's CUDA path and answers image, audio and video parts with 400; 2.x reads images.
- **No log-probabilities of generated tokens.** `logprobs` and `top_logprobs` are refused with 400; `prompt_logprobs` is served on non-streamed `/v1/completions` only.
- **`clear_thinking` is not passed to the chat template.** The native server passes the template only `enable_thinking`, `thinking_mode` and `reasoning_effort`; the pinned template takes a missing `clear_thinking` as false and keeps the reasoning of earlier turns that a client sends back. A client that sends earlier turns without their reasoning sees no difference.
- **Every rank keeps two CPU cores spinning**, rank 0 while it decodes and the others while they wait. The default container cores keep the CPU's zones below the thermal watch's stop at a cost of 1 to 3% in speed; on every core, long runs of replies reached it ([why the efficiency cores](#serving-defaults)).
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
- **The engine is this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017, #1018); the release branch keeps the rest.

## Next Action

Each item is a trigger and what this line then does.

<!-- S6: check each against the window -->

- Upstream merges pull requests #1016, #1017 and #1018, or asks for changes → follow the merged form in a 3.x release; the NLL and decode checks tell whether the bits moved.
- Upstream's TP bootstrap (pull request #636) lands → start TP=3 on it and drop the NCCL id file from the release branch.
- The engine's spinning threads (above) → give upstream the measurements of each remedy (the container's cores, a context that sleeps, lower heat bands) and follow the one it chooses in a 3.x release.
- `chat_template_kwargs.clear_thinking` → pass it to the chat template as 2.x does, and offer it upstream.
- Image input and the published AXL weights on the native engine → accept them as 2.x did.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
