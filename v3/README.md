# GLM-5.3-Flash BIZ 3.x (TensorFold native)

![GLM-5.3-Flash BIZ v3, XSFP4 × TensorFold: native Zig and CUDA on DGX Spark and GB10 systems](assets/banner.webp)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Validation](docs/validation.md) · [Changelog](CHANGELOG.md)

**GLM-5.3-Flash BIZ** serves GLM-5.3-Flash on DGX Spark or compatible GB10 systems. The 3.x line serves it with TensorFold's native engine, the Zig and CUDA engine that took the place of the Python engine the [2.x line](../v2/README.md) runs, on two hosts at TP=2 or three hosts at TP=3. It serves [XSFP4](#checkpoints), a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local whose experts this repository's maintainer requantized; NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint, which 1.x and 2.x serve, was a choice here up to 3.5.x. 3.0.0 was the line's first release, on upstream TensorFold 1.0.12; 3.1.0 moves it onto upstream 1.1.1, 3.2.0 adds image and video input, 3.3.0 moves onto upstream 1.1.2 and adds XSFP4 beside NVIDIA's checkpoint, 3.4.0 makes XSFP4 the default, 3.6.0 moves onto upstream 1.1.3 and serves XSFP4 alone, and 3.8.0 moves onto upstream 1.1.5, which holds this line's pull requests. 2.x continues beside it.

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

## Summary

- **Status.** 3.8.0 moves the engine onto upstream 1.1.5 itself, upstream's first release with this line's pull requests, and at TP=3 the KV cache onto pages. Its release image, started by its own `serve.sh` and `cluster.sh` with no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores, gave 3.3.0's XSFP4 decode-check hashes and edit reply at TP=2 and TP=3 in two launches at each size, and its NLL, and found every passphrase of the long inputs, the 1,035,295-token prompt's at TP=3 included ([measured on the release](#measured-on-the-release)); `mojibake` found no broken character in Japanese and Korean answers at either size, at temperature 0 or sampled ([multibyte output](docs/validation.md#multibyte-output)). At TP=3 the stop string's request runs to its limit and a short greedy reply has its own hash, known behaviours set down there. The reference values of [validation](docs/validation.md) are 3.8.0's acceptance's on the reference hosts on 2026-10-26, with the vision tower loaded, the decode-check hashes, edit reply and NLL among them 3.3.0's. That is the scope of the claim; other hosts are qualified by running the same checks.
- **What it is.** Build steps, launch scripts and acceptance checks that serve XSFP4 through a pinned commit of TensorFold's native engine as one OpenAI-compatible endpoint: two hosts at TP=2 over a direct ConnectX-7 link, or three at TP=3 in a switchless ring. The published measurements come from MSI EdgeXpert (MS-C931) systems. On a Mac, TensorFold serves GLM-5.3-Flash from MLX weights of its own ([on a Mac](../README.md#on-a-mac)).
- **Repeatable.** Drafted replies equal serial ones, and a launch gives the token ids of the launch before it at the same TP size. The native engine's tokens are its own, not 2.x's: its kernels and its BF16 KV cache round differently, so the two lines compare by teacher-forced NLL, not token by token ([differences from 2.x](#differences-from-2x)).
- **Structured output and prompt scores.** `response_format` with a JSON schema, `tool_choice` `required` or a named function (written in GLM's own tool markup) and `prompt_logprobs` on `/v1/completions` are upstream TensorFold's own on GLM's CUDA engine since 1.1.1, written after this line's pull requests #1016, #1017 and #1018 ([API](#api)).
- **Images and videos.** Chat requests may carry PNG, JPEG and WebP images and H.264, HEVC, VP8, VP9 and MPEG-4 videos as data URLs, read by the checkpoint's vision tower on rank 0 through the engine's `--vision`, which `serve.sh` passes by default ([limits](#limits)).
- **Precision.** On XSFP4, W4A16 for the routed experts and every other projection in the form the checkpoint stores: mostly 8-bit, with NVFP4 in the vision tower's MLP and merger ([checkpoints](#checkpoints)). BF16 KV (2.x keeps an FP8 KV cache). NVIDIA's model card measured FP4-Local under other recipes on other hardware, so its accuracy table does not describe this serving; [validation](docs/validation.md) gives the numbers that do.
- **Licensing.** Apache-2.0 code and engine; weights that the operator downloads, the NVIDIA Open Model Agreement (XSFP4, commercially usable); xgrammar (Apache-2.0) in the image for structured output, and libjpeg-turbo, libwebp (BSD-style) and FFmpeg's decoders (LGPL-2.1) for images and videos; nothing non-commercial in the serving path ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Image and video URLs (`--vision-urls`, off), more than one request at a time (the acceptance's checks send one at a time) and other world sizes and hardware ([limits](#limits)); harness integration (ZCode, Claude Code), full application quality and production reliability.

## What It Is

- **Weights**: `Bizuayeu/GLM-5.3-Flash-XSFP4` ([`config/xsfp4.lock.json`](config/xsfp4.lock.json), [checkpoints](#checkpoints)), from NVIDIA's GLM-5.3-Flash-FP4-Local and [Z.ai's GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash).
- **Engine**: TensorFold's native engine (`tensorfold-native`), from the BIZ release published as the branch `release/3.8.0` of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold): upstream TensorFold v1.1.5 itself, with no commit of this line's. Upstream took this line's pull requests on 2026-10-25, and 1.1.5 is its first release with them. #1050 loads NVIDIA's GLM-5.3-Flash-FP4-Local as stored, and with it the XSFP4 checkpoint, which keeps FP4-Local's tensors outside the experts: it tells each projection's format from the checkpoint's `MIXED_PRECISION` recipe, runs the MXFP8 and 128×128-block FP8 projections as stored, reads FP4-Local's compressed expert scales, and keeps the float32 norm weights float32. #1178 sends rank 0's NCCL id to the other ranks over their liveness lines, so TP=3 starts on upstream's bootstrap, without the id file (`TF_GLM_NCCL_ID_FILE`) and the two commits of this line's that 3.6.0's release branch carried for it. #1163 and #1211 put every stream's KV cache and the engine's own sequence on pages of one pool at three ranks ([serving defaults](#serving-defaults)). From 1.1.3 upstream's own code lets an index name a shard in a folder inside the model folder, which FP4-Local's and XSFP4's indexes need; the release branches up to 3.5.x carried it as the patch of pull request #1179. From 1.1.5 the server gives GLM-5.3's chat template `clear_thinking` ([configuration](docs/configuration.md#rank-0s-server)). 3.0.0 to 3.2.0's heat look-ahead to a ceiling (`TF_HEAT_CEILING`) is gone: the heat wait is upstream's band alone ([serving defaults](#serving-defaults)). The image pins one commit ([`config/engine.lock.json`](config/engine.lock.json)).
- **Image**: [`docker/Dockerfile`](docker/Dockerfile). The engine is compiled in NVIDIA's CUDA 13.3.1 build image by the Zig compiler the lock names (checked by SHA-256), and `libtfgrammar` is built from xgrammar's release at a pinned commit; the runtime image is CUDA 13.3.1 with NCCL 2.30.7 and the RDMA userspace. Both base images are pinned by digest. `/usr/share/doc/tf3/ENGINE` names the engine commit and each binary's SHA-256, and `/usr/share/doc/tf3/engine/` holds the engine's license and notices.
- **Launch**: shell scripts in [`scripts/`](scripts/) and one environment file per rank ([`examples/`](examples/) holds the reference hosts' files). [SETUP.md](SETUP.md) is the order. Nothing is built on the hosts: the kernels are in the binary.
- **Other recipes**: what this repository took from other recipes on TensorFold, with their licenses, is 2.x's [table](../v2/README.md#other-recipes-on-tensorfold). 3.x's TP=3 rank files keep two of the fabric settings 2.x took from MiaAI-Lab's TensorFold recipe and measured, four NCCL channels and subnet-aware routing ([decisions](docs/decisions.md#fabric)). Upstream TensorFold's own recipe for this model on CUDA is [GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md).

## Requirements

- **Hosts**: two or three DGX Spark or compatible GB10 systems (Linux ARM64, 128 GB unified memory each) with nothing else large on their GPUs. A 1.x or 2.x server on the same hosts is stopped first, and 2.x's container too, since it claims every GPU ([hand the hosts to 2.x](docs/operations.md#hand-the-hosts-to-2x)).
- **Fabric**: ConnectX-7 links with RoCE v2, a direct cable for the pair or a switchless ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Both rails of each port are used.
- **Host kernel**: as in 1.x and 2.x; the kernel current DGX OS updates install can break multi-node RoCE by default, and the reference hosts boot it with `kho=off` ([host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce)).
- **GPU clock** capped on every host ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); [`host/`](../host/README.md) installs the cap and a telemetry logger. Every 3.x figure was measured under the cap.
- **Docker** with NVIDIA's GPU runtime and the RDMA devices (`create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets).
- **Disk**: the whole checkpoint on every host, plus the image: XSFP4 takes 178 GB.
- **A control machine** with SSH to every host, for `cluster.sh`.
- **Python 3.11+** on the hosts for this line's tools in [`glm53_tf/`](glm53_tf/) (download, verification, tool-argument gate, checks), run from `v3/` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

## Quick Start

The steps, with what to check after each, are the [setup runbook](SETUP.md); this is their outline for TP=2. Use the same reviewed `v3.*` tag on every host.

```sh
# Once, from v3/ on one host in its virtual environment; then copy the cache to the others and verify each copy (SETUP §2)
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum-xsfp4 --wait

# One host builds the image, the others load it; compare the image IDs (SETUP §3)
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.8.0 .

# Each host, from the checkout root (SETUP §4)
v3/scripts/create_container.sh glm53-tf3:3.8.0 ~/glm53-tf3
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

XSFP4 is the checkpoint 3.x serves: the default from 3.4.0 and, from 3.6.0, the only one. NVIDIA's NVFP4, the default until 3.3.0 and a choice up to 3.5.x, is 1.x's and 2.x's. Every rank serves the same one.

| | XSFP4 |
|---|---|
| Weights | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) ([`config/xsfp4.lock.json`](config/xsfp4.lock.json)) |
| Made by | this repository's maintainer, from NVIDIA's [`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local) (revision `76348ddb`) and Z.ai's BF16 weights |
| Routed experts | XSFP4, served W4A16: NVFP4 blocks fitted again from the BF16 weights with a smoothing folded into them, so no kernel applies anything at run time; the MTP layer's experts too. Layers 3 to 44 store their block scales compressed losslessly (`csf_32x2_v1`, as FP4-Local does), and the engine restores them on the host at load |
| Everything else | FP4-Local's tensors as stored: MXFP8 (dense MLP, KDA, `lm_head`, the MTP layer's attention and shared expert), FP8 in 128×128 blocks (MLA and the shared experts), BF16 (KDA's small projections, MLA's `kv_b` and indexer, the router, the embeddings), BF16 and F32 norms; the vision tower's MXFP8 and NVFP4 |
| Model on rank 0 at TP=2 (245,760-token window) / TP=3 (load line, the KV cache on pages) | 93.44 / 63.60 GiB |
| Next token against the BF16 weights on this engine at TP=2 (128 documents, 144,285 positions): top-1 agreement / NLL above BF16 / KL, lower bound | 93.26% / +0.85% / 0.0431 |
| The same at TP=3 | 93.30% / +0.85% / 0.0436 |
| License | NVIDIA Open Model Agreement (a derivative of FP4-Local; `LICENSE` and `NOTICE` in the repository) |
| Download (SETUP §2) | `download`, `verify-download` (the download's status under `state/xsfp4`) |
| Rank files | nothing: `serve.sh`'s default, the lock's revision |

Each document went to the engine as token ids with `prompt_logprobs` of 20. The KL bound counts one by one the tokens whose probability both sides report (the engine's best 20, BF16's best 20 and the text's token) and the rest as one bucket, so it is lower than the KL over the whole vocabulary and does not compare with KL measured outside the engine; XSFP4's [model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) gives both. On the same engine and documents NVIDIA's NVFP4 gave 92.68% / +1.37% / 0.0510 at TP=2 and 92.71% / +1.38% / 0.0511 at TP=3, so XSFP4 is the closer to BF16 by all three at both TP sizes, the per-document 95% intervals of the differences holding no zero; FP4-Local itself, loaded as stored by the same engine, gave 92.82% / +1.11% / 0.0510 at TP=2 and 92.75% / +1.07% / 0.0514 at TP=3.

XSFP4's [measured](#measured-on-the-release) speeds are its own: the drafts' acceptance and the layers' forms differ from NVIDIA's NVFP4's, so they do not compare with 1.x's or 2.x's figures. FP4-Local's chat template, which XSFP4 keeps, differs from NVIDIA's in three places (a message without content renders nothing, a tool call's name is joined with `~`, and the check that puts tool results in the order of the calls stops at its first failure).

## Serving Defaults

[`scripts/serve.sh`](scripts/serve.sh) holds them, the same on every rank; what was chosen against what, and what would reopen it, is in [decisions](docs/decisions.md):

| Setting | TP=2 (two hosts) | TP=3 (three hosts) |
|---|---|---|
| Checkpoint | XSFP4 at its lock's revision (`CHECKPOINT` unset, [checkpoints](#checkpoints)) | same |
| KV cache | BF16 latent and index keys (the engine's default; `--kv-cache fp8` opts into its FP8 latent cache, outside the acceptance: [limits](#limits)), a window per stream | the same keys on KV pages: every stream's cache and the engine's own sequence take pages of one pool (the engine's default at three ranks, `TF_KV_PAGES`; `TF_KV_PAGES=off` in every rank file keeps a window per stream, as up to 3.7.0) |
| Drafts | the checkpoint's MTP head (the engine's default) | same |
| Window (`--context`) | 524,288 tokens: one stream and a prompt cache beside XSFP4 on each rank | 1,048,576 tokens (the model's limit) |
| Requests decoded at once (`--parallel`) | 1 (`PARALLEL=1`); an empty `PARALLEL=` leaves it to the engine, which sizes the streams and the prompt cache from the memory free at start | same |
| Prompt cache (kept prompt states, at the starts of 2,048-token chunks) | what the window leaves, at most 16 GiB (rank 0's load line; it moves with the memory free at the start): on the reference hosts with the vision tower loaded, 5.2 to 5.5 GiB on XSFP4 at 524,288 tokens (2.0 GiB at 245,760 with `PARALLEL=` empty, beside its three streams) | 16.0 GiB on the reference ring, the cap (`--prompt-cache-gib` sets another) |
| Reply limit when a request names none | 32,768 tokens (`--max-tokens`) | same |
| Reasoning effort when a request names none | `high` (`--reasoning-effort`) | same |
| NCCL | two rails per link, four channels, the IB transport named, from each rank's file; rank 0's address and port as `NCCL_COMM_ID`, and rank 0's NCCL id over the ranks' liveness lines | two rails, four channels, the IB transport named, subnet-aware routing; rank 0's address and port as `NCCL_COMM_ID`, rank 0's NCCL id over the ranks' liveness lines, and the other ranks' NCCL bootstrap on their `/32` interfaces (`NCCL_SOCKET_IFNAME`) |
| BF16 linears | upstream's tiled kernels (the engine's default) | same: since upstream 1.1.2 (issue #1067) they leave a TP=3 rank's KDA input untiled, where 3.1.0 and 3.2.0 needed the glue kernels (`TF_GLM_MM=0`) |
| Prefill pause for heat | before each prompt chunk, every rank together, while any rank's hottest ACPI zone is above 92 °C, until all are at or below 88 °C (`TF_HEAT_HIGH`, `TF_HEAT_LOW`; 3.0.0 to 3.2.0 also paused ahead of a 93 °C ceiling, which 3.3.0's engine does not have) | same |
| Image and video input | on (`VISION=1`, the engine's `--vision`): the checkpoint's vision tower on rank 0, PNG, JPEG and WebP images and videos as data URLs, at the engine's limits ([limits](#limits)); `VISION=` for text alone, every rank the same | same |
| Container cores | the cores with the lowest maximum frequency: a GB10's efficiency cores, 0-4 and 10-14 (`create_container.sh`, `CPUSET`) | same |

**Why one request at a time.** With `--parallel` unset the engine asks for eight streams and serves as many as fit, so the number of streams and the room left for the prompt cache change from one start to the next with the memory free at that moment (at TP=3 one start before 3.0.0 took two streams and 0.1 GiB of prompt cache; on 3.8.0's KV pages the streams share one pool, and with `PARALLEL=` empty the engine took eight on 3,398 pages, 21.15 GiB, beside a 16.0 GiB prompt cache). One stream, as 2.x serves, keeps the window the same at every start, and the prompt cache moves only with the memory free (5.2 and 5.1 GiB at TP=2 with the vision tower in 3.3.0's two launches on NVIDIA's NVFP4). At TP=2 3.0.0's engine fitted no second stream beside the 245,760-token window (it needed 4.55 GiB on each rank, and rank 1 had 4.41 GiB). From 3.1.0 the engine does: with `PARALLEL=` empty, 3.3.0's took two streams on NVIDIA's NVFP4 and left a 1.5 GiB prompt cache, against one stream's 5.2 GiB (three streams on XSFP4). At 3.5.0's 524,288 it takes one ([limits](#limits)).

**Why 524,288 at TP=2.** BF16 KV takes about twice the memory of 2.x's FP8 cache per token. Until 3.4.0 the window was 245,760 tokens, shorter than 2.x's 300,000: about the most that fit one stream beside NVIDIA's NVFP4, the default when it was set. XSFP4, the default from 3.4.0, takes about 3.9 GiB less on rank 0 (93.44 against 97.38 GiB at 245,760), and from 3.5.0 the window is 524,288 tokens: rank 0's load line read one stream of 6.71 GiB and a 5.5 GiB prompt cache, and a 499,254-token prompt fits with 25,034 tokens left for the reply. A second stream (`PARALLEL=2`) takes another 6.71 GiB, which this window leaves no room for: it needs a smaller window, such as `CONTEXT=245760`. `CONTEXT` in every rank file chooses another.

**Why the efficiency cores.** The engine keeps two CPU threads spinning on every rank while a request runs, on rank 0 while it decodes and on the other ranks while they wait for it (before upstream 1.1.2's engine the other ranks also spun while idle; #1053 sleeps them while rank 0 has no stream): one waits for the GPU, and the other, by its kernel time, is most likely NCCL's. On every core they heated the CPU's thermal zones, which are five of a GB10's seven: forty 1,024-token replies in a row, each after a prompt of about 6,000 tokens, took rank 0's hottest zone to 94.7 °C at TP=2 with 3.0.0's engine, and the thermal watch stopped the engine at the seventh. 3.1.0's engine finished them on every core in the same 1,535 s as on the efficiency cores, but rank 0's host reached 93.0 °C, 1 °C under the stop, against 74.9 °C on the efficiency cores; two requests at once on every core reached 88.5 °C. The heat wait cannot hold them, since it acts between prompt chunks. On the efficiency cores, with 3.0.0's engine, the forty replies finished with that zone at 85.1 °C, and rank 1's host waited at 57 to 63 °C instead of about 70 °C, for 1 to 3% of speed and a start about 25 s longer ([3.0.0's measurements](docs/measurements.md#300)). Lower heat bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering the peak of a 1,048,576-token prompt, and a CUDA context that sleeps instead of spinning decoded 12% slower and left the other thread spinning. Since 1.1.1 upstream's [runbook](https://github.com/ashhart/TensorFold/blob/v1.1.5/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs) gives the same cores for each GB10 rank, from these measurements. `CPUSET=` gives the container every core.

## Configuration

Three places set a deployment: each host's rank file, which `serve.sh` reads; the control machine's cluster file, which `cluster.sh` reads; and `create_container.sh`'s environment. Copy the two files from [`examples/`](examples/), put your own values and keep them out of Git. The settings most often changed are the window (`CONTEXT`), the requests decoded at once (`PARALLEL`), text alone (`VISION=`), the listener and its keys (`HOST`, `API_KEY_FILE`) and the container's cores (`CPUSET`).

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

The engine also routes `/v1/responses` and Anthropic's `/v1/messages`, through the same chat path; the acceptance did not check them. On GLM's CUDA engine it refuses `logprobs` and `top_logprobs` for the generated tokens (400), audio parts (400), image and video parts when started without `--vision` (an empty `VISION=` in the rank files; 400), and `/v1/decisions` (400).

## Differences from 2.x

| | 2.x (TensorFold's Python engine) | 3.x (TensorFold's native engine) |
|---|---|---|
| Engine | the BIZ release of TensorFold 0.6.5, Python with Triton kernels compiled at run time | the BIZ release of TensorFold 1.1.5 (3.0.0: 1.0.12; 3.1.0 and 3.2.0: 1.1.1; 3.3.0 to 3.5.x: 1.1.2; 3.6.0 and 3.7.0: 1.1.3), Zig and CUDA, the kernels in the binary |
| Repeatable output | drafted equals serial, resume equals fresh, chunking does not matter, as the engine's contract | drafted equals serial and launches repeat their token ids; the tokens differ from 2.x's (other kernels, BF16 KV), so the lines compare by NLL |
| KV and window | FP8 latent and index keys; 300,000 tokens at TP=2, 1,048,576 at TP=3 | BF16; 524,288 tokens at TP=2, 1,048,576 at TP=3 |
| Requests at once | one | one by default; `PARALLEL` lets the engine share its decode rounds among more, within the memory the window leaves |
| Prompt cache | 8 entries, 3 GiB (`TF_GLM_CACHE_*`) | states at chunk starts in what the window leaves, at most 16 GiB (at TP=2 with the vision tower, 5.2 to 5.5 GiB on XSFP4 at 524,288 tokens; at TP=3, 16.0 GiB); no entry count |
| Image input | accepted (`VISION=1`) | accepted, and videos (`VISION=1`, the default) |
| Published AXL weights | optional | not served (from 3.6.0) |
| Structured output, required tool calls | accepted, with xgrammar in the image | accepted, with xgrammar's `libtfgrammar` in the image; required tool calls in GLM's markup |
| `prompt_logprobs` | accepted | accepted on non-streamed `/v1/completions` |
| `clear_thinking` | honoured | honoured from 3.8.0 (upstream 1.1.5; [configuration](docs/configuration.md#rank-0s-server)) |
| Reply fields | `tensorfold` with `accepted`, `drafted`, `rounds`, `cached`, `prefill_s`, `heat_wait_s`, `sha256` | `tensorfold` and `speculative` (above); cached tokens in `usage`; heat waits only in the log |
| Heat settings | `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, `TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`, `TF_HEAT_LOW`, the same band; no ceiling |
| XSFP4 checkpoint | not served | the checkpoint served (the default from 3.4.0, the only one from 3.6.0) |
| NVIDIA's NVFP4 checkpoint | the pinned checkpoint | not served (from 3.6.0; a choice up to 3.5.x) |
| Image and container | `glm53-tf`, extensions built per container (`build_ext.sh`) | `glm53-tf3`, nothing built on the hosts |
| Container cores | every core | the efficiency cores unless `CPUSET` says otherwise |
| Tool-argument gate | the gate in front of the engine | the same gate, this line's copy run from `v3/` |

The two lines' containers both claim every GPU: run one line's engine at a time ([operations](docs/operations.md#hand-the-hosts-to-2x)).

## Measured on the Release

**3.8.0** (2026-10-26, engine `84e0d560`, upstream 1.1.5, image `glm53-tf3:3.8.0`). The engine is upstream 1.1.5 itself, with no commit of this line's, and at TP=3 the KV cache is on pages. Launches of the release image started by its own `serve.sh` and `cluster.sh`, with no `CHECKPOINT` or `CONTEXT` in the rank files but where a launch names one, and every container on the efficiency cores: six at TP=2 and five at TP=3, each size's launch of every check, a second launch, one with `PARALLEL=` empty and one each on NVIDIA's NVFP4 and FP4-Local for the comparison with BF16 ([checkpoints](#checkpoints)), and at TP=2 the 245,760-token window with `PARALLEL=` empty. Every launch that ran them gave 3.3.0's XSFP4 decode-check hashes and `bench --kinds edit` reply in 190 rounds; the NLL was 3.3.0's, and every passphrase of the 199,307, 499,254 and 1,035,295-token prompts was found. Nothing stopped them.

| 3.8.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s): the launch of every check / a second launch | 376 / 323 | 316 / 270 |
| Decode check count / prose / code (tok/s) | 48.99 / 34.11 / 45.05 | 63.94 / 44.98 / 54.94 |
| MTP acceptance length, same tasks | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode` (tok/s, median) | 53.89 | 65.33 |
| `bench --kinds edit` (tok/s, median) | 82.60 | 105.07 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,417.5 | 1,703.5 |
| 199,307-token prompt (s) | 151.5 | 128.7 |
| 499,254 and 1,035,295-token prompts, first token (s) | 429.2 / — | 376.3 / 1,013.6 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.32 against 68.5 | 0.94 against 57.1 |
| Teacher-forced NLL, ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0 through the gate / without it | 95 / 93 | 92 / 91 |
| Japanese and Korean answers with a broken character, temperature 0 / sampled | 0 / 0 | 0 / 0 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone of rank 0's host) | 1,248.8, 75.9 °C | 989.8, 86.0 °C |
| Hottest zone of a launch, by rank (°C) | 87.9 / 88.9 | 92.4 / 89.9 / 87.9 |
| Lowest `MemAvailable`, by rank (GiB) | 11 / 12 | 21 / 23 / 28 |

- **Against [3.6.0](docs/measurements.md#360).** The same tokens. Decode, the edit reply and the prefill are 0.5 to 0.7% faster at TP=2 and within 0.9% of 3.6.0's at TP=3, and the long prompts took 0.9 to 1.2% less time at TP=2 and within 1.3% of 3.6.0's time at TP=3 (the 1,035,295-token prompt 984 s without its waits for heat, against 994 s). Rank 0's load line at TP=2 read 3.6.0's model size (96.97 GiB at the 524,288-token window) and a 5.5 GiB prompt cache; at TP=3, below.
- **KV pages at TP=3.** Rank 0's load line gives the engine's own sequence and the streams 2,049 pages of 512 rows (12.76 GiB), enough for one stream at the 1,048,576-token window, and a 63.60 GiB model, 12.76 GiB under 3.6.0's 76.36: the model figure no longer holds the engine's own sequence. With `PARALLEL=` empty the engine took eight streams on the same pages and gave the count hash. After every launch each of rank 0's `kv pool idle` lines had every page free.
- **Heat.** At TP=3 only the 1,035,295-token prompt waited for heat, 30 s in 15 pauses of 2 s (3.6.0: 10 s in 5); at TP=2 no prompt waited. No zone reached the thermal watch's stop.
- **Tools.** Through the [tool-argument gate](SETUP.md#6-tool-argument-gate-optional), this repository's relay, the scores and the scenarios left partial or failed are 3.6.0's, though from 3.8.0 the engine passes the invocation's `clear_thinking` to the chat template (upstream's `c767bd766`), which leaves out the reasoning of the turns before the latest user message. Without it the engine scored 93 at TP=2 and 91 at TP=3 with the Safety Gate passed; the one more scenario failed at both sizes is TC-43, a `web_search` call with an empty `query`, which through the gate becomes a refusal to call it without one.
- **Known behaviours of XSFP4.** They are [3.3.0's](docs/measurements.md#330): at TP=3 the stop string's request runs to its limit, and the plain request of the prompt-score and structured-output checks has its own hash.

Earlier releases' figures are in [measurements of earlier releases](docs/measurements.md).

## Limits

- **One request at a time by default.** More need `PARALLEL` and, at TP=2, a smaller window: the 524,288-token window holds one stream (an empty `PARALLEL=` took one), and `CONTEXT=245760` holds three; at TP=3 the streams share the KV pages, and an empty `PARALLEL=` took eight ([serving defaults](#serving-defaults)).
- **Images and videos within the engine's limits.** At most 4 images a request, counting every image the submitted history holds (a client that resends earlier turns with their images reaches it), sharing 4,096 image tokens; 10 MiB an image and 20 MiB a request; PNG, JPEG and WebP data URLs, GIF and animated pictures refused. Videos in user messages only, 2 a request (16 MiB each, 20 MiB together, an hour of footage), sampled at 2 frames a second up to 256 frames, sharing 16,384 video tokens; a clip under half a second is refused. Images and videos take their tokens from the window. HTTPS URLs need `--vision-urls`, which `serve.sh` does not pass. Audio parts are refused with 400.
- **No log-probabilities of generated tokens.** `logprobs` and `top_logprobs` are refused with 400; `prompt_logprobs` is served on non-streamed `/v1/completions` only.
- **Every rank keeps two CPU cores spinning while a request runs**, rank 0 while it decodes and the others while they wait for it (since upstream 1.1.2's engine, #1053, the other ranks sleep while rank 0 has no stream). The default container cores keep the CPU's zones below the thermal watch's stop at a cost of 1 to 3% in speed with 3.0.0's engine (with 3.1.0's the forty replies took the same time, and a start about 40 s longer); on every core, long runs of replies reached the stop with 3.0.0's engine and came within 1 °C of it with 3.1.0's ([why the efficiency cores](#serving-defaults)).
- **BF16 KV** holds a shorter window per GiB than 2.x's FP8 cache. The engine has an opt-in FP8 latent cache (`--kv-cache fp8`) whose quality and device qualification upstream calls pending, and `serve.sh` does not set it. Tried once at TP=2 (XSFP4 with the vision tower, `CONTEXT=1048576` in both rank files, `--kv-cache fp8` after `cluster.sh`'s label): one 7.13 GiB stream fit the 1,048,576-token window beside a 4.7 GiB prompt cache, the 1,035,295-token prompt found its three passphrases with the first token after 1,130.6 s, the 199,307- and 499,254-token prompts took about 5% longer to prefill, the NLL set moved by +0.14% (text by text the interval includes zero), and the decode check's tokens differ from the BF16 cache's.
- **Two or three hosts with ConnectX-7 links**, as in 1.x and 2.x. Other world sizes and other hardware are outside what was measured.

## Repository Layout

The 3.x files live in `v3/`. The image is built from the checkout root, where the licenses are; the Python tools run from `v3/` as `python -m glm53_tf <command>`. The host tools and the host and fabric pages every line shares are at the checkout root ([`host/`](../host/README.md), [`docs/`](../docs/README.md)).

```
v3/
  README.md         this page (each .md has a .ja.md beside it)
  SETUP.md          the deployment runbook
  CHANGELOG.md      the 3.x releases; a v3.* tag publishes its section
  glm53_tf/         the Python tools: download, verify-download, tool-gate,
                    decode-check, decode-divergence, score-nll, bench, long-input, mojibake
  config/           xsfp4.lock.json (XSFP4), engine.lock.json (the engine commit, the Zig compiler and
                    xgrammar), nll_set.json (the NLL set)
  requirements/     huggingface.lock.txt: the Hugging Face client for the download and its verification
  docker/           Dockerfile: the image, with the engine pinned by ENGINE_REF
                    Dockerfile.build: the build image, where the engine is built and its GPU tests run
  scripts/          create_container.sh  the serving container on each host
                    cpuset.sh            its cores (CPUSET): by default the lowest maximum frequency
                    serve.sh             one rank, with the serving defaults
                    cluster.sh           start, stop and status of every rank from a control machine
                    hostwatch.sh         the memory guard (stops the engine below 5 GiB MemAvailable)
  examples/         the reference hosts' rank files and cluster files, TP=2 and TP=3
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
- **XSFP4 is this repository's maintainer's checkpoint**, a derivative of NVIDIA's FP4-Local under the NVIDIA Open Model Agreement; it is not an NVIDIA or Z.ai release.
- **The engine is the release branch of this line's fork of upstream.** What serves other users goes to upstream TensorFold as pull requests (#1016, #1017 and #1018 became upstream's own in 1.1.1; #1050, #1163, #1178 and #1211 in 1.1.5); the release branch keeps the rest, and 3.8.0's keeps nothing: it is upstream v1.1.5 itself.

## Next Action

Each item is a trigger and what this line then does.

- 3.3.0's engine has upstream's pull request #1053 (the waiting ranks sleep while rank 0 has no stream, in 1.1.2); the releases since ran on the efficiency cores, so it is still open → measure again whether the container still needs them.

## Local Data and Contribution

What stays out of Git (rank and cluster files with your site's values included), licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 3.x changes.
