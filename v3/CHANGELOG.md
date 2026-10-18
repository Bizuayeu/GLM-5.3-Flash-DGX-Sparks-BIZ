# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 3.x line, served by TensorFold's native engine. A `v3.*` tag publishes its section from this file once the section's heading carries the release date. The 2.x line's history is in [v2/CHANGELOG.md](../v2/CHANGELOG.md).

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
