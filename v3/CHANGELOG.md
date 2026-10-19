# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 3.x line, served by TensorFold's native engine. A `v3.*` tag publishes its section from this file once the section's heading carries the release date. The 2.x line's history is in [v2/CHANGELOG.md](../v2/CHANGELOG.md).

## 3.1.0

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
