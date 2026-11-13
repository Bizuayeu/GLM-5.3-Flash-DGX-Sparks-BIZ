# Changelog

[日本語](CHANGELOG.ja.md) (this English file is canonical and the GitHub Release is made from it)

The 3.x line, served by TensorFold's native engine. A `v3.*` tag publishes its section from this file once the section's heading carries the release date. The 2.x line's history is in [v2/CHANGELOG.md](../v2/CHANGELOG.md).

## 3.15.0 — 2026-11-13

Tools outside the image, their tests and documents. No file of the image changes; it stays 3.12.0's (`glm53-tf3:3.12.0`, `sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Host tools

- An opt-in [heat cap](../host/README.md#heat-cap), `gb10-heat-cap`, lowers the GPU clock cap from 2,200 to 2,000 MHz while the host stays hot and raises it back once cool: at 2,200 MHz, more than 150 of the last 300 s at or above 90 °C in the hottest ACPI zone lock 2,000 MHz; at 2,000 MHz, 120 s at or below 75 °C lock 2,200 again; a missing or stale record locks 2,000. It is a root service beside the boot cap that starts at 2,200, locks 2,200 when it stops, never resets the clocks and never locks above 2,200, and it records each change in `heat-cap.log` and the cap in force in `/run/gb10-heat-cap.json` (`--status`). `install.sh` installs it only with `--heat-cap`; without the flag it installs what it did before. The lines come from the reference hosts' long prefills at 2,200 MHz (2026-11-11) and at 2,000 MHz (2026-11-12) ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)).
- `cool-gate` and `thermal-watch` read the newest row of the two newest telemetry files; up to 3.14.x, just after the UTC day changed and before the logger wrote the new day's first line, they read the record as missing, and `cool-gate` exited 2, which stopped a run that called it.

### Repository

- Tests replay the heat cap's rules on the two prefills' records in `tests/data` and run its watch against a stand-in `nvidia-smi`; the host tools' tests plant the moment the UTC day changes. CI's ruff steps name `host/gb10-heat-cap`.

### Accepted

On one reference host on 2026-11-13, with this release's host files: `install.sh --heat-cap` installed and enabled the heat cap, which started at 2,200 MHz. Restarting `gb10-clock-cap.service` while it ran restarted it; while it was stopped, the restart left it stopped. Under 178 s of GPU load, with trial lines 12 and 8 °C over the idle zone (`--high 60.8 --low 56.8 --window 60 --share 0.25 --hold 20`), it locked 2,000 MHz 32 s into the load: the busy clock read 1,969 to 1,976 MHz and the power at most 31.1 W, against 2,190 MHz and 39.2 W before. It locked 2,200 again 55 s after the load, and 2,200 when stopped. The default lines did not act there; they come from the records above.

## 3.14.0 — 2026-11-13

Tools outside the image, their tests and documents. No file of the image changes; it stays 3.12.0's (`glm53-tf3:3.12.0`, `sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Image and launch

- `create_container.sh` takes the RDMA devices it gives the container from `RDMA_DEVICES` (unset or empty: `/dev/infiniband`, as before) and refuses a host without them by that path ([configuration](docs/configuration.md#container)).

### Repository

- Tests run `create_container.sh` against a stand-in docker and hold the whole `docker run` it builds: the devices, every GPU, host network and IPC, `IPC_LOCK` with locked memory unlimited, the 64 MiB `/dev/shm`, the cache at `/hub` read-only or writable, `/work`, and the cores when some are picked.

## 3.13.1 — 2026-11-13

Tools outside the image, their tests and documents. No file of the image changes; it stays 3.12.0's (`glm53-tf3:3.12.0`, `sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Documentation

- `bench`'s help says only the decode request it sends; the request used before 2.5.0 is left to [2.x's changelog](../v2/CHANGELOG.md), which has it.
- The Japanese page of the [licensing guide](../docs/licensing.md) heads its weight notices 重みの通知, as the English page heads them Weight notices, since the section covers the NVIDIA Open Model Agreement beside MIT; the links to the section from the page, the Japanese README and 1.x's Japanese changelog follow.

### Repository

- The root tests check that the measuring texts the lines copy from one another are the same on every line: decode-check's tasks, mojibake's prompts, bench's passage, and long-input's ledger line and passphrases.
- A serving-defaults test's comment names the engine source behind its warning below four kept prompt states a stream, the GLM family's `cuda_share.zig`, where it named a function the engine does not have.

## 3.13.0 — 2026-11-13

Tools outside the image, their tests and documents. No file of the image changes; it stays 3.12.0's (`glm53-tf3:3.12.0`, `sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Fixes

- `cluster.sh` tells a count it could not take from no engine. When SSH to a host or its Docker fails, `start` stops before any rank starts (`rank R HOST: its engines cannot be counted (ssh or docker failed)`, exit 1), and `status` and `stop` print `?` for that host's engines. A stopped container counts as running no engine, as the memory guard reads it, and so does a missing one, which Docker names "No such object" or "No such container", or in lower case as docker 29.6.2 does; a Docker that cannot reach its daemon ("… no such file or directory") is a failure. Up to 3.12.x a Docker failure read as no engine, and an SSH failure as an engine already running.
- The memory guard, `hostwatch.sh`, also ends when Docker says its container is gone in lower case, as docker 29.6.2 on the reference hosts does, and still watches on when Docker cannot reach its daemon; up to 3.12.x, on such a Docker, a guard whose container was removed while it watched went on until it was killed.
- `cluster.sh` hands each serve argument after the label to `serve.sh` whole, one with a space or a quote included ([engine flags](docs/configuration.md#engine-flags)); up to 3.12.x they went through SSH and `bash -c` unquoted, so such an argument did not arrive whole.
- `long-input` stops with exit 2 when `--tokens` is below the prompt without ledger lines, naming that prompt's size; up to 3.12.x it looked for a ledger length without end.
- `decode-check` and `bench` stop with exit 1 when a streamed reply carries no text or no usage, saying which, and `decode-check` with a `PROMPT_KIND` other than `count`, `prose` and `code` stops with exit 2, naming the three; up to 3.12.x each ended in a Python traceback.

### Documentation

- The [setup](SETUP.md)'s first step stops a 1.x or 2.x server and 2.x's container first (`docker stop glm53-tf` on every host), since that container claims every GPU, and points to the ring of four's addresses in the [TP=4 examples](examples/tp4-rank0.env). Its list of the runtime image names `python3` with `tokenizers`, the defaults by TP size and the wire's kernels beside `serve.sh`, where it named `serve.sh` alone.
- The setup says that a host that received a copy of the Hugging Face cache runs `download` with the same `--tp` once and then `verify-download`, and that after `docker stop glm53-tf3` the containers are started again before the next `cluster.sh start`. It says what a start's seconds hold and leaves the release's start times to [measured on the release](README.md#measured-on-the-release), where it gave 3.9.0's, and TC-67's and TC-69's known behaviour links [3.10.0's measurements](docs/measurements.md#3100). The TP=2 pairs of the four hosts no longer say "yet".
- The [README](README.md)'s serving defaults say that at TP=2 the main stream's small all-gathers take the engine's two-rank RoCE path up to `TF_ROCE_MAX_KB` a rank (4 MiB) and NCCL past it, where they said NCCL. The README and the [configuration](docs/configuration.md) say that on a ring of four `split` does not start, because NCCL fails its peer warm-up before split's own check can name the pair, where they said split's check refuses. The [differences from 2.x](README.md#differences-from-2x) count TP=4 with the other sizes, the limit on spinning cores states its point and links the figures, and the link to upstream's runbook names the engine's version, 1.2.7, where it named 1.2.4.
- [Operations](docs/operations.md) says that when one rank stops, the others stop within about 20 s, when their liveness lines notice the host gone, where it said they wait in a collective as under 2.x; the section is now [a rank that stops](docs/operations.md#a-rank-that-stops), and the [host tools' README](../host/README.md) links it there. Moving to an image that changes a TP size's default checkpoint gets a step of its own. The outcomes of a start list `cluster.sh`'s refusals before any rank starts, a count it cannot take among them, and `stop`'s last lines say what `?` and 0 mean.
- [Configuration](docs/configuration.md) says it lists the settings a 3.x deployment sets and the engine's that this line names or measured, and that the engine reads more, which its source at the pinned commit has, where it said every setting a deployment reads. It says `cluster.sh` quotes each serve argument, where it said they arrive unquoted.
- The [cheatsheet](docs/cheatsheet.md) says which engines read `csf0_v1` (this line's from 3.10.0 and upstream's releases from 1.2.3), that from 3.11.0 the tool-argument gate also asks the engine for one tool call a turn unless `--parallel-tool-calls client`, and that `VISION=0`'s memory on rank 0 goes to the KV pool as far as the other ranks' room allows before the prompt cache, where it said the prompt cache. It gives a million-token prompt's first token in minutes and leaves the seconds to the README. Its TP=2 pairs link the setup for which have served. Its `score-nll` line runs in the container, as validation's does.
- The [decisions](docs/decisions.md) point to the serving defaults' table instead of counting the settings the sizes part on, and the [benchmark method](docs/benchmarks.md) names TP=4's ring of four among its hosts and defaults.
- The README's [disclaimer](README.md#disclaimer) leaves the list of the pull requests upstream took to the [decisions](docs/decisions.md#engine), whose row now names them all, each in the release whose upstream changelog names it; the two lists had differed.
- [Validation](docs/validation.md) names each reference value's source: 3.12.0's acceptance lengths and XSFP4's edit reply in 64 rounds at TP=2; the multibyte answers at TP=2 from 3.9.0's image and at TP=3 from 3.12.0's, which gave 3.9.0's word for word; the tool-eval-bench version behind each tools figure; TP=3's tools figures from 3.12.0, through the gate before 3.11.0's (93, where 3.9.0's gave 92) and without a gate (91); the XSFP4 section's TP=2 decode check and `bench` from 3.12.0; and one release's count of balanced idle-pool lines. It says TP=4 has no reference values on the page, and its `score-nll` example runs in the container, where `tokenizers` is, with the cache at `/hub` and the revision in the lock, where it ran on the host at a fixed snapshot. Its opening points to the XSFP4 section for which acceptance gave each value, and that section names the upstream versions. Its memory-and-heat reference says it was rank 0's hottest zone that came during the 1M-token prompt, at both TP sizes.
- The [document map](../docs/README.md) keeps an English/Japanese pair in step when user-visible content changes, as [Contributing](../CONTRIBUTING.md) says, where it said instructions; the document map and [AGENTS.md](../AGENTS.md) no longer describe how the maintainer keeps private plans.

### Repository

- The tools send their requests, and read streamed replies and cached tokens, through one module, `glm53_tf/client.py`; `bench` builds its decode and edit rows in one place, `verify-download`'s main reads as its stages, `download` takes its state folder's lock in one place, the tool gate's request handler is a module-level class, and `--tp`'s help is built from the TP-to-checkpoint table. The rearrangement changes nothing they print or send.
- `verify-download` reads the download status as UTF-8, as `download` writes it, rather than in the platform's encoding.
- Tests run `cluster.sh` against stand-ins for `ssh` and `docker`, the tool gate's `main()`, and `serve.sh`'s name, address, reply cap and extra arguments; `bench`'s row tests pin the order of a row's keys, and the tool gate's stream tests check each stream's record. The tool tests share one module of reply stand-ins, `serve.sh`'s text tests sit beside the tests that run it, and the TP sizes come from `config.TP_CHECKPOINTS`.
- The host tools' comments on their provisional values drop the `cc-defer` tag and keep what they say.

### Accepted

On two reference hosts on 2026-11-13, at TP=2 on Jammed XSFP4 with 3.12.0's image (`glm53-tf3:3x-54ccb94`, the same image as `glm53-tf3:3.12.0`) and the examples' rank files, this release's `cluster.sh` as it stood before its lower-case reading ran `status`, then `start` with one serve argument holding spaces (`--alias "GLM e15 check"`), then `stop`. The argument arrived whole: the engine listed `GLM e15 check` as one model id. `status` counted 0 with the containers running and no engine, 1 a rank while serving, and 0 after `stop` and after `docker stop`; `stop` printed each host's `MemAvailable`, and both memory guards ended with `done`. With the containers removed, Docker answered "error: no such object", which that `cluster.sh` read as `?`; a copy that reads either case counted 0, and with one rank unreachable refused the start naming that rank. 3.12.0's memory guard on a removed container ran until a 10 s timeout, and a copy that reads either case ended at once. Docker 29.6.2's answer when it cannot reach its daemon names "no such file or directory", which the released counts read as a failure, as their tests pin. An argument holding a quote was not run on the hosts, and the released `cluster.sh` did not start an engine there.

## 3.12.1 — 2026-11-12

Documents, example comments and tests only. No file of the image changes; it stays 3.12.0's (`glm53-tf3:3.12.0`, `sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Documentation

- The default checkpoint follows the TP size, as 3.12.0 set it: the [repository README](../README.md), the [licensing guide](../docs/licensing.md) and this README's [what it is](README.md#what-it-is) and [differences from 2.x](README.md#differences-from-2x) say Jammed XSFP4 at TP=2 and XSFP4 at TP=3 and TP=4, where they still called XSFP4 the default and Jammed XSFP4 a choice. `THIRD_PARTY_NOTICES.md`, which the image carries, keeps the old words until the next image.
- [Host preparation](../docs/hosts.md) and the README's requirements say 3.12.0 is the first release measured on the reference hosts' state from 2026-11-07 (kernel `7.0.0-1025-nvidia`, display memory at Auto), and that figures carried from earlier releases were measured on the state before it, where they said nothing had been measured on it yet.
- The README's [disclaimer](README.md#disclaimer) and the [decisions](docs/decisions.md#engine) say 3.12.0's engine is upstream 1.2.7 itself, where the README said 1.2.4 and the decisions' versions stopped at 1.2.1.
- TP=4 has run: the decisions no longer say it never did, and the [configuration](docs/configuration.md) says the TP=4 examples set two of the engine's NCCL connection settings to 1 and that `cluster.sh` starts TP=4's ranks 3 s apart, as it does TP=2's.
- An empty value in a rank file reads as unset for nearly every setting: the README's [configuration](README.md#configuration) and the configuration's heat row no longer say it turns a setting off or that `serve.sh` unsets it. The image's `serve.sh` and `config/tp*.env` comments keep the old words until the next image.
- The [setup](SETUP.md#5-start) and the [cheatsheet](docs/cheatsheet.md) make `state/` before copying a cluster file into it, as the README's Quick Start does, and the cheatsheet runs the tool-argument gate from `v3/`.
- The [document map](../docs/README.md) gives the release check as `release_notes.py X.Y.Z --match-project`, as `release.yml` runs it, and lists host preparation's section on updating a host; [AGENTS.md](../AGENTS.md) says the root's document map and CI file are at the checkout root. The Japanese [NCCL diagnostics](../docs/nccl-validation.ja.md) keep the container command's line breaks, the Japanese decisions say 2.x serves images without "by default", and the example rank files' `CONTEXT` comment names `config/tpN.env`.

### Repository

- `serve.sh`'s tests pin that an empty value reaches the engine empty: they read the key itself, where an unset key passed as well. A test's name says every TP size, and `.gitignore` names `docs/plans` once.

## 3.12.0 — 2026-11-12

The engine moves onto upstream TensorFold v1.2.7 itself (`93a2e93e`), with no commit of this line's: upstream carries Jammed XSFP4's `csf0_v1` commits from 1.2.3. The default checkpoint follows the TP size: Jammed XSFP4 at TP=2, XSFP4 at TP=3 as before, and XSFP4 at TP=4, new and experimental. The image is `glm53-tf3:3.12.0` (`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`).

### Engine

- The fork's branch `release/3.12.0` is upstream v1.2.7 (`93a2e93e`) itself; `config/engine.lock.json` and the Dockerfile's `ENGINE_REF` pin that commit. 3.10.0's branch (upstream 1.2.1 with six commits of this line's) is retired: upstream's releases carry the six from 1.2.3 ([TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)).
- An empty value in a rank file (`NAME=`) reads as unset for nearly every setting from upstream 1.2.6, and `serve.sh` passes empty values on as they are, where 3.11.x's unset six of them itself. Two still refuse an empty value, `TF_ROCE_MAX_KB` and `TF_NVFP4_DECODE_WARPS`, and empty `TF_HEAT_HIGH` and `TF_HEAT_LOW` together turn the heat wait off ([configuration](docs/configuration.md#rank-0s-server)).
- `TF_GLM_PDL`, `TF_GLM_PROMPT_STEPS`, `TF_GLM_SHARED`, `TF_GLM_LINK_WAIT` and `TF_GLM_PROF` take `0` or `1` alone, and `TF_GLM_DRAFT_CONFIDENCE` a number from 0 to 1 ([TensorFold #2578](https://github.com/ashhart/TensorFold/pull/2578), upstream 1.2.6). **A rank file that sets one of them to a word** (`off`, `yes`) stops the start by name; write `0` or `1`.
- Each kept prompt state takes a slot of the startup plan, and the prompt cache's rest becomes the pool's pages (upstream 1.2.5, #2358): at TP=3 the pool takes two windows and that rest at 16 GiB left to the system ([why 16 GiB at TP=3](README.md#serving-defaults)). On Jammed XSFP4 at TP=3 the room holds a third window, which the plan sets aside before the slots, so 8 of `TF_KV_SHARE=32`'s states are kept and the engine warns; `--prompt-cache-gib 6` after `cluster.sh`'s label keeps all 32 and two windows ([engine flags](docs/configuration.md#engine-flags)). `TF_KV_SHARE` over 64 stops the start ([configuration](docs/configuration.md#rank-file)).
- At TP=3 decode with drafts is slower than 3.10.0's, with the same tokens: the decode check's `count` gave 57.94 tok/s against 65.67, and `bench --kinds decode` 63.23 against 68.52. Under `--mtp-confidence` a temperature-0 stream drafts to the chain's end every round, and the window verifies only the head above the confidence floor. Upstream's fix ([TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)) comes with the first release that carries it.

### Serving defaults

- TP=4, experimental: four hosts in a switchless ring serve at TP=4. `serve.sh` takes TP 4 and ranks 0 to 3, with [`config/tp4.env`](config/tp4.env) beside the other two in the image: TP=3's values with the wire off and 14 GiB left to the system, the settings the reference ring of four was served with on upstream's main from 2026-11-07, none tuned at four hosts. The examples hold that ring's rank files, a NCCL graph for each rank and `cluster.tp4.env`; each rank file adds the ring's NCCL lines and `TF_GLM_PREFILL_REDUCE=gather`, since the engine's `split` sends to every rank and does not start on a ring of four: NCCL fails its peer warm-up with `ncclGroupEnd: unhandled system error`, before split's own check can name the pair ([serving defaults](README.md#serving-defaults), [cheatsheet](docs/cheatsheet.md)). Other examples serve the same four hosts as two pairs at TP=2: 04-05 and 06-07, each served at TP=2, or 04-06 and 05-07, not started yet; no two pairs have served at once yet.
- The default checkpoint follows the TP size: Jammed XSFP4 at TP=2, and XSFP4 at TP=3 and TP=4 as before. Each release file names its folder at its lock's revision, a rank file's `CHECKPOINT` line serves the other one, and an empty line keeps the TP's. `serve.sh`'s start line ends with the folder it serves, and a folder the host lacks stops the start by name. **A pair that holds only XSFP4** downloads Jammed XSFP4 (`download --tp 2`, `verify-download --tp 2`) or adds XSFP4's `CHECKPOINT` line to every rank file ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

### Image and launch

- The memory guard (`hostwatch.sh`, which `cluster.sh` starts on every host) keeps watching when a check fails or does not return. Every docker call is bounded by the round's 2 s; a check that fails or stalls writes `check-failed` and the watch goes on, and the watch ends only when the engine is gone or `docker inspect` says the container is stopped or gone. A stop that fails writes `KILL-FAILED`, and the next round stops the engine again while memory stays short; `KILLED` comes only after a stop that worked ([configuration](docs/configuration.md#memory-guard)). Up to 3.11.x a `docker exec` that failed read as no engine and ended the watch.

### Tools

- `download` and `verify-download` need `--tp 2`, `3` or `4`, for the checkpoint that TP serves, or `--checkpoint`, and stop with their usage when given neither; up to 3.11.x they fetched and verified XSFP4 without either. **A script that runs them with neither** adds `--tp` or `--checkpoint xsfp4` ([setup §2](SETUP.md#2-checkout-and-checkpoint)).

### Documentation

- The README's [status](README.md#summary), [checkpoints](README.md#checkpoints), [serving defaults](README.md#serving-defaults) and [measured on the release](README.md#measured-on-the-release), [validation](docs/validation.md), [configuration](docs/configuration.md) (empty values, the strict GLM flags, `TF_KV_PAGES`, `TF_QMMF_HALF_BELOW` and the kept states' slots), [decisions](docs/decisions.md) and the [cheatsheet](docs/cheatsheet.md) name 3.12.0's engine and defaults. A non-number `TF_QMMF_HALF_BELOW` stops the load, and an empty `TF_KV_PAGES` is `auto`, where configuration said otherwise. 3.10.0's table moves to [measurements](docs/measurements.md#3100), where XSFP4's repeated numbers read as the replies wrote them: 37 four times at TP=2, and 37 and 86 twice each at TP=3.
- The commands in the README, setup and operations build and name `glm53-tf3:3.12.0`.

### Accepted

On the reference hosts on 2026-11-12, with the release image (`glm53-tf3:3x-54ccb94`, the same image as `glm53-tf3:3.12.0`) started by its own `serve.sh` and `cluster.sh` and every container on the efficiency cores. TP=3 on XSFP4 and TP=2 on Jammed XSFP4, the defaults, with no `CHECKPOINT` or `CONTEXT` in the rank files: two launches at each size gave 3.9.0's decode-check hashes, `bench --kinds edit` reply and NLL at TP=3 and 3.10.0's at TP=2, the first found every passphrase of the 199,307, 499,254 and 1,035,295-token prompts, and `mojibake` found no broken character. On XSFP4 at TP=2, with its `CHECKPOINT` line in the rank files, one launch gave 3.9.0's decode-check hashes and `bench --kinds edit` reply. Through 3.11.0's tool-argument gate tool-eval-bench gave 93 at TP=2 on Jammed XSFP4 and at TP=3 on XSFP4, the Safety Gate passed. At TP=3 on Jammed XSFP4, with its `CHECKPOINT` line, a launch gave 3.10.0's decode-check hashes and `bench --kinds edit` reply, and one with `--prompt-cache-gib 6` the same hashes. In these launches and XSFP4's at TP=2 the memory guard, this release's `hostwatch.sh`, logged a line every 2 to 3 s and ended with `done`. At TP=4, on four other hosts, two launches gave their decode-check hashes and edit reply again and found every passphrase. A rank file with `TF_KV_SHARE`, `TENSORFOLD_PREFILL_SHARE`, `TF_HEAT_HIGH` and `TF_HEAT_LOW` empty started with the prompt cache in copies and no heat wait, and one with `TENSORFOLD_MEMORY_RESERVE_GIB` empty with the engine's own 12.3 GiB reserve. No watcher stopped a launch ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.12.0

Upstream's fix for TP=3's drafted decode (#2864), with the first release that carries it. A prompt chunk's indexer on its own kernels by default (`TF_GLM_INDEX_CUDA=1`, upstream's #1449): measured beside the engine's own path at every TP size, with the same tokens and a sooner first token on long prompts, it goes with the next release after its memory is measured again.

## 3.11.7 — 2026-11-07

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- Upstream's releases carry the `csf0_v1` commits from 1.2.3 (2026-11-05, [TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)): the README's [limit](README.md#limits) on Jammed XSFP4, its disclaimer on the engine, its [Next Action](README.md#next-action) and the [decisions](docs/decisions.md#engine) say so, where 3.11.3 wrote that no upstream release carried them. This line's release branch stays on 3.10.0's engine until it goes back to an upstream release.

## 3.11.6 — 2026-11-07

Documents, tool help and tests only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- [Validation](docs/validation.md) says to make the run's records folder first (`mkdir -p ../records/<run>`): none of the tools creates it, so a fresh checkout lost the first check's file.
- [Validation](docs/validation.md) says the container runs the tools as `python3 -m glm53_tf` (the image has no `python`), and that `tokenizers`, which `score-nll` needs, is the container's and not the virtual environment's.
- Validation says the engine keeps prompts as states on the KV pool's pages (`TF_GLM_KV_SHARE`), as it has since 3.9.0, not in a cache sized in GiB.
- The [method](docs/benchmarks.md#requests-at-once) says the three decodes beside a prompt shared one prompt up to 3.11.3, and the [README](README.md#requirements) names `initcall_blacklist` for the reference hosts' boot setting. The Japanese cheatsheet and method now say what the English ones say about the tool-argument gate's checks and the TP=2 pair's cooling gate.

### Tools

- `decode-check --help` and `long-input --help` say the same about kept prompts, and `tool-gate --help` says it relays `GET`, `POST` and `DELETE` (other methods are answered 501, as before).

### Repository

- New tests tie what two files each write: `serve.sh`'s name, host, port and reply cap to the tools' defaults and to `tool-gate`'s `--upstream`; `Dockerfile.build`'s base and its NCCL and tokenizers versions to `Dockerfile`'s; the paths `cluster.sh` and `serve.sh` use in the image to `Dockerfile`'s; and the container's name across the scripts and the examples.
- `mojibake`'s and `decode-check`'s tests pass with `TENSORFOLD_API_KEY` or `PROMPT_KIND` set where they run, and `decode-divergence`'s tests no longer hold an assertion that could not fail.

## 3.11.5 — 2026-11-07

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- The reference hosts moved on 2026-11-07 to kernel `7.0.0-1025-nvidia`, booted with `kho=off` and with `power_wrap_init` in `initcall_blacklist`, to ConnectX-7 firmware 28.50.1002, and to MSI's UEFI 5.36_1.9.0 with the display memory at Auto, which leaves the operating system 1.5 GiB more. [Host preparation](../docs/hosts.md#host-kernel-and-multi-node-roce) now keeps that state apart from the one every 3.x figure through 3.11.4 was measured on (`7.0.0-1019-nvidia`, ConnectX-7 28.45.4028, the 2 GiB display default); no 3.x figure has been measured on the new state yet.
- A new section, [updating a host](../docs/hosts.md#updating-a-host), gives the steps the reference hosts took and how each was checked: on DGX OS 7.6, let `nvidia-spark-mlnx-firmware-manager` finish writing the ConnectX-7 firmware before rebooting (a reboot during the write stops it, and after three stopped attempts it disabled itself on two reference hosts and left the old firmware); both boot settings in `/proc/cmdline`; the board firmware and the display memory setting they took from `lvfs-testing`; and the NCCL validation they passed on four pairs.
- [NCCL diagnostics](../docs/nccl-validation.md): a host that got the base image through `docker save | docker load` refers to it by its ID.
- The [requirements](README.md#requirements) and [setup step 1](SETUP.md#1-hosts-and-fabric) link the new section.

## 3.11.4 — 2026-11-05

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- The gap between the tokens of three decodes beside a 32K prompt is now taken from three decodes of different prompts: 62 ms at TP=2 and 47 ms at TP=3 on XSFP4, 61 and 47 ms on Jammed XSFP4. Until now the three shared `bench`'s count prompt, so they wrote the same tokens and their rounds came lighter (45, 46, 37 and 36 ms, which the same image gave again within 1 ms). The [README](README.md#serving-defaults)'s measurements and the reason for a prompt's share of 0.7, [measurements](docs/measurements.md), the [method](docs/benchmarks.md#requests-at-once) and the [decisions](docs/decisions.md) say so. The share stays 0.7: at the engine's `1` the gap was 1,484 ms at TP=2 and 1,221 ms at TP=3.

## 3.11.3 — 2026-11-04

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- Upstream took the `csf0_v1` commits into its main on 2026-11-04 ([TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)), and no release of upstream's carries them yet. The [README](README.md#limits) and the [decisions](docs/decisions.md#engine) say so where they said the commits go upstream next, and the README's limit on Jammed XSFP4 says that of the released engines only this line's reads it. An upstream release that carries the commits is now what takes the release branch back to an upstream release and reopens [Jammed XSFP4's row](docs/decisions.md#checkpoint) ([Next Action](README.md#next-action)).

### Not in 3.11.3

The release branch back on an upstream release, which waits for one that carries the commits, and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.11.2 — 2026-11-04

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- [Decisions](docs/decisions.md#window-and-streams)' row on wider prompt passes gives a later upstream run at TP=3's defaults on the wire ([TensorFold #1994](https://github.com/ashhart/TensorFold/issues/1994)): `TF_GLM_OVERLAP_PIECES=8` on every rank took solo from 1.7 to 3.6% sooner at the default 3 pieces to 6.1 to 7.8% sooner, with the same tokens, and 8 pieces without solo stayed within 1% of 3. TP=3 keeps no solo, since other streams decode most of the time there; the row names what reopens it, solo beside eight pieces measured under the load of several people.
- [Benchmark method](docs/benchmarks.md#decode-check) says how the README's other two counts in Jammed XSFP4's known behaviours were taken: copies of the decode check with `ignore_eos` false, and with the numbers from 1 to 100 asked for with thinking off.
- The Japanese [decisions](docs/decisions.ja.md) and 3.9.0's section of the Japanese changelog give TP=2's use as the README has since 3.10.1, one person's long conversation with an agent.

### Not in 3.11.2

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.11.1 — 2026-11-04

Two fixes, to `download --background` and to the publication audit. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Tools

- `download --background` writes the job's status before it returns, so the `verify-download --wait` that the [setup](SETUP.md#2-checkout-and-checkpoint) runs right after it follows this job. Before, it could find no status yet and exit 1 ("run download first"), or find the last job's status and end on it. A start while another download owns the checkpoint's folder is refused, as a foreground run is, instead of starting a job that fails into `download.log`, and a job that cannot be started leaves a failed status ([tools](docs/configuration.md#tools)).

### Repository

- The publication audit (`tools/check_publication.py`) requires Jammed XSFP4's lock beside XSFP4's and checks that it pins a model and a full revision; its message names the lock that does not.

### Not in 3.11.1

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.11.0 — 2026-11-04

The tool-argument gate and documents. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Tools

- The [tool-argument gate](SETUP.md#6-tool-argument-gate-optional) asks the engine for one tool call a turn and tells the model so: a request that declares tools goes on with `parallel_tool_calls` false, whatever the client sent, and with one sentence at the end of its first system message, "Make one tool call a turn, and the next one after its result has come back." At TP=3 Jammed XSFP4 had called `send_email` in the same turn as `create_calendar_event` in tool-eval-bench's TC-51, and the Safety Gate failed on it. `--parallel-tool-calls client` sends requests as the client wrote them, as before ([configuration](docs/configuration.md#tools)).

### Accepted

- tool-eval-bench 2.8.0 through the gate on 3.10.0's image, one launch of each checkpoint at each TP size: XSFP4 93 at TP=2 and 93 at TP=3, Jammed XSFP4 93 and 92, the Safety Gate passed in all four ([validation](docs/validation.md#tools-through-the-tool-argument-gate)). Through the gate before it the four were 95, 92, 93 and 92, and Jammed XSFP4's Safety Gate failed at TP=3. TC-69 failed and TC-67 was partial in all four: they ask for two lookups, and the model answered after the first one's result without the second. Jammed XSFP4's TC-49 was partial at TP=2. These are known behaviours ([measured on the release](README.md#measured-on-the-release)).

### Documentation

- The README's [measured on the release](README.md#measured-on-the-release), [validation](docs/validation.md)'s tools and Jammed XSFP4's reference, [setup](SETUP.md) §6 and [configuration](docs/configuration.md#tools)'s tools give 3.11.0's gate, its scores and its known behaviours. Without the gate, Jammed XSFP4's TC-51 at TP=3 stays a known behaviour.
- The README's [Next Action](README.md#next-action) names upstream's pull request for the `csf0_v1` commits, [TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041).

### Not in 3.11.0

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.10.2 — 2026-11-03

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- The README's [measured on the release](README.md#measured-on-the-release) says what the table's TP=3 start of Jammed XSFP4 is: the acceptance script stopped its first try after the load, at a free-memory line set for XSFP4's two windows of pages, so the 46 s is a second load of the same weights, not a first one like XSFP4's 93 s. No watcher stopped a launch.
- Jammed XSFP4's slower `count` names what it was compared with, 3.10.0's XSFP4 launches on the same image, not the table's XSFP4 columns, which are 3.9.0's acceptance.

### Not in 3.10.2

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.10.1 — 2026-11-03

Documents only. No file of the image changes; it stays 3.10.0's (`glm53-tf3:3.10.0`, `sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`).

### Documentation

- The README's [measured on the release](README.md#measured-on-the-release) gives XSFP4 and Jammed XSFP4 in one table at each TP size: Jammed XSFP4's columns are 3.10.0's launches', and XSFP4's are 3.9.0's acceptance, as the column headers say. The README keeps the current release's part alone, so 3.9.0's part moves word for word to [measurements of earlier releases](docs/measurements.md#390).
- [Configuration](docs/configuration.md) follows 3.10.0's engine and defaults: GLM on CUDA takes `--mtp-confidence` and refuses `--mtp-drafts`, or `--mtp-confidence` beside `--drafter`; `TF_KV_PAGES=off` needs an empty `TF_GLM_KV_SHARE=` beside it; the TP=3 prompt cache is the pool's pages; the TP=3 reserve's two windows are XSFP4's; the locks table names `config/jammed.lock.json`. The TP=3 examples' commented KV-pages line names the empty `TF_GLM_KV_SHARE=` too, and [setup](SETUP.md) §4 lists it.
- The [benchmark method](docs/benchmarks.md) says how 3.10.0's launches were taken, and the [cheatsheet](docs/cheatsheet.md) gives the 1,035,295-token prompt's first token of 3.9.0 and 3.10.0 at both TP sizes.
- The [licensing guide](../docs/licensing.md) and the repository README name Jammed XSFP4 beside XSFP4. The README's Japanese page has the person in TP=2's long conversation with an agent, and its Quick Start builds the image from the checkout root.

### Not in 3.10.1

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)).

## 3.10.0 — 2026-11-03

Adds Jammed XSFP4, a checkpoint whose routed experts take 6.58 GiB less on each host at TP=2 and 4.50 GiB less on rank 0 at TP=3, where the KV pool takes a third window of pages, served by one `CHECKPOINT` line in the rank files. XSFP4 stays the default and gives 3.9.0's tokens. The engine's release branch gains the six commits that read the new form.

### Checkpoint

- [Jammed XSFP4](README.md#checkpoints), `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4` at the revision in [`config/jammed.lock.json`](config/jammed.lock.json): the routed experts of layers 3 to 44 fitted again at a block scale every 32 inputs, with XSFP4's smoothing, and those scales held as one base a row and a 4-bit offset a block (`csf0_v1`), in the file as on the GPU. The MTP layer's experts are FP4-Local's.
- `download` and `verify-download` take `--checkpoint jammed`, with the status under `state/jammed`, and `serve.sh` serves the folder `CHECKPOINT` names. Nothing else changes ([setup §2](SETUP.md#2-checkout-and-checkpoint)).
- At TP=2 what it frees stays free: rank 0 keeps 14.16 GiB after load against XSFP4's 8.33. At TP=3 the same 14 GiB reserve leaves room for a third window of pages, 6,147 (38.27 GiB) against 4,098, and rank 0 keeps 12.15 GiB against 20.69.
- Its replies are its own, so it has reference values of its own ([validation](docs/validation.md#jammed-xsfp4)). At TP=3 tool-eval-bench's Safety Gate fails on TC-51, and its decode check's `count` is slower than XSFP4's: known behaviours ([measured on the release](README.md#measured-on-the-release)). Only this line's engine reads the form ([limits](README.md#limits)).

### Engine

- The fork's branch `release/3.10.0` (`a9642aef`) is upstream v1.2.1 (`1db3edbe`) with six commits of this line's: the form, its packer, five kernels and the loader's path to them. A checkpoint without `csf0_v1` takes upstream's path as it was. On a GB10 the five kernels pass all four gates of upstream's kernel contract, and the commits go to upstream next.
- `config/engine.lock.json` and the Dockerfile's `ENGINE_REF` pin that commit.

### Documentation

- The README's [checkpoints](README.md#checkpoints), [limits](README.md#limits) and [measured on the release](README.md#measured-on-the-release), [validation](docs/validation.md#jammed-xsfp4), [decisions](docs/decisions.md#checkpoint), [configuration](docs/configuration.md), the [cheatsheet](docs/cheatsheet.md) and the setup runbook name Jammed XSFP4. XSFP4's reference values stay 3.9.0's.
- The commands in the README, setup and operations build and name `glm53-tf3:3.10.0`.

### Accepted

On the reference hosts on 2026-11-03, with the release image (`glm53-tf3:3.10.0`) started by its own `serve.sh` and `cluster.sh` and every container on the efficiency cores: with no `CHECKPOINT` or `CONTEXT` in the rank files a launch at each TP size gave 3.9.0's XSFP4 decode-check hashes and `bench --kinds edit` reply. With Jammed XSFP4's `CHECKPOINT` line and nothing else in the rank files, two launches at each TP size repeated their hashes and reply, and the first found all the passphrases of the 199,307, 499,254 and 1,035,295-token prompts. With `PARALLEL=` empty the engine took 8 streams at TP=2 and 8 at TP=3, each giving the count hash. At one stream and four, and eight at TP=3, 20 replies at TP=2 and 52 at TP=3 equalled the same request alone. tool-eval-bench 2.8.0 gave 93 at TP=2 and 92 at TP=3 through the gate and 92 and 91 without it, the Safety Gate passed at TP=2 and failed at TP=3 on TC-51 (a known behaviour), and `mojibake` found no broken character ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.10.0

The six commits upstream and a Jammed XSFP4 made from the BF16 weights with nothing borrowed from XSFP4 ([Next Action](README.md#next-action)). The serving defaults are 3.9.0's.

## 3.9.0 — 2026-11-03

The engine moves onto upstream TensorFold 1.2.1 itself, TP=2 opens the model's whole 1,048,576-token window, as TP=3 does, and the serving defaults are set by TP size: TP=2 for one person's long conversation with an agent, TP=3 for several people at once. Four streams at TP=2 and eight at TP=3 share the KV pool, and kept prompts stay on the pool's pages. The documents' measured values are 3.9.0's acceptance's.

### Engine

- The fork's branch `release/3.9.0` is upstream v1.2.1 (`1db3edbe`) with no commit added. Since 1.1.5 upstream has taken this line's #1352, #1404 and #1424 (1.1.9), #1516, #1524, #1616 and #1636 (1.2.0) and #1823 (1.2.1).
- TP=2's KV cache moves onto pages, upstream's default from two ranks since 1.1.6 (#1322): every stream's cache and the engine's own sequence take pages of one pool. The FP8 latent cache keeps a window per stream, so `--kv-cache fp8` now takes an empty `TF_GLM_KV_SHARE=` and one stream ([cheatsheet](docs/cheatsheet.md#the-fp8-latent-cache-at-tp2)).
- A start is shorter: #1616 and #1636 read and pack the weights on several threads ([measured on the release](README.md#measured-on-the-release)).

### Serving defaults

- [`config/tp2.env`](config/tp2.env) and [`config/tp3.env`](config/tp3.env) hold what differs by TP size. `serve.sh` reads its size's file from the image before the rank file, so a new image moves the defaults, a rank file's line still wins and an empty value turns a setting off.
- TP=2: `CONTEXT=1048576`, the model's limit (524,288 up to 3.8.x), `PARALLEL=4`, `TF_GLM_KV_SHARE=16`, `TENSORFOLD_PREFILL_SHARE=0.7` and `TENSORFOLD_MEMORY_RESERVE_GIB=9`.
- TP=3: `PARALLEL=8`, `TF_GLM_KV_SHARE=32`, `TENSORFOLD_PREFILL_SHARE=0.7`, `MTP_CONFIDENCE=0.5` (`--mtp-confidence`), `TF_GLM_ROCE_MULTI=1` (the wire) and `TENSORFOLD_MEMORY_RESERVE_GIB=14`.
- The reasons are the README's [serving defaults](README.md#serving-defaults) and [decisions](docs/decisions.md#window-and-streams), where `PARALLEL=1` closes.

### Image and launch

- The image holds `tp2.env`, `tp3.env` and the wire's kernels, `tp_mailbox.fatbin`, beside `serve.sh`, and `/usr/share/doc/tf3/ENGINE` names the kernels' SHA-256.
- While `TF_GLM_ROCE_MULTI` is on, `serve.sh` gives the wire `TF_TP_MASTER` from `MASTER`, `TF_TP_PORT`, `TF_TP_PLAN_TIMEOUT`, `TF_TP_KERNEL_IMAGE` and `TF_TP_ROCE_FALLBACK=error`, so a setup that fails stops the start ([operations](docs/operations.md)).
- `[serve.sh]`'s line gives the resolved `kept`, `prefill-share`, `solo`, `mtp-confidence`, `wire` and `reserve`, and the acceptance reads it against the file.
- `config/engine.lock.json` and the Dockerfile's `ENGINE_REF` pin `release/3.9.0` at `1db3edbe`, upstream 1.2.1.

### Documentation

- The documents' measured values are 3.9.0's acceptance's: [validation](docs/validation.md)'s reference values, whose decode-check hashes, edit reply and NLL stay those 3.3.0's acceptance set, and the README's checkpoints, serving defaults, limits and [measured on the release](README.md#measured-on-the-release). 3.8.0's part moves word for word to [measurements of earlier releases](docs/measurements.md#380).
- [Validation](docs/validation.md#requests-at-once) gains requests at once, upstream's `bench_concurrent.py` against the same requests alone, and [benchmarks](docs/benchmarks.md#requests-at-once) how the rows of requests at once are taken.
- [Configuration](docs/configuration.md) lists the settings of `config/tp*.env` and the wire's, setup and operations describe the four and eight streams and the wire, and the [cheatsheet](docs/cheatsheet.md) gains what the engine does with a request's model name.
- The commands in the README, setup and operations build and name `glm53-tf3:3.9.0`.

### Accepted

On the reference hosts on 2026-11-03, with the release image (`glm53-tf3:3.9.0`) started by its own `serve.sh` and `cluster.sh`, no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores: in two launches at each TP size XSFP4's decode-check hashes and `bench --kinds edit` reply were 3.3.0's, and in the first its NLL and 3.3.0's reply to the 199,307-token prompt, with all three passphrases found in the 499,254 and 1,035,295-token prompts. With `PARALLEL=` empty the engine took eight streams at TP=2 and eight at TP=3, each giving the count hash. At one stream and four, and eight at TP=3, 20 replies at TP=2 and 52 at TP=3 equalled the same request alone. tool-eval-bench 2.8.0 gave 95 at TP=2 and 92 at TP=3 through the gate and 93 and 91 without it, 3.8.0's scores with the same scenarios left partial or failed, the Safety Gate passed, and `mojibake` found no broken character. XSFP4's next-token scores over the 128 documents equalled 3.8.0's to the byte at both TP sizes ([measured on the release](README.md#measured-on-the-release)).

### Not in 3.9.0

#1423 and #1580, open upstream ([Next Action](README.md#next-action)); NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them) and log-probabilities of generated tokens ([limits](README.md#limits)).

## 3.8.1 — 2026-10-26

Documents only. No file of the image changes; it stays 3.8.0's (`glm53-tf3:3.8.0`, `sha256:1055b9feee2ef704c8dd736495bfc8d231df5a59406b17eb0655eefdd830b7a2`).

### Documentation

- The README keeps the current release's [measured on the release](README.md#measured-on-the-release), 3.8.0's. 3.6.0's back to 3.0.0's move word for word to a new page, [measurements of earlier releases](docs/measurements.md), under a heading for each release; a release's part goes there when the next one replaces it. The pages that pointed at a moved release link it there, and the document map and the README's layout list the page. The README's opening paragraph no longer lists what each release changed; it links this changelog.
- Corrections for 3.8.0's engine, checked against its source and 3.8.0's acceptance: [setup](SETUP.md) §5 no longer has the operator read each rank's `NCCL_COMM_ID … leaves NCCL's environment`, a line of the id-file commit that the release branches up to 3.7.0 carried and that 1.1.5 does not log, and describes rank 0's load line at TP=3 by its KV pages; the README's disclaimer says that 3.8.0's release branch is upstream v1.1.5 with no commit of this line's; the [benchmark method](docs/benchmarks.md) no longer says that one TP=2 launch on each checkpoint ran with `PARALLEL=` empty, and gives its cooling caps as 3.8.0's too; [operations](docs/operations.md) says that no watcher stopped an engine in the acceptance of any release whose measurements are published, 3.8.0's included, and counts 3.8.0's among the acceptances where every stop left no engine.

### Not in 3.8.1

NVIDIA's NVFP4 and the published AXL weights on 3.x (1.x and 2.x serve them) and log-probabilities of generated tokens ([limits](README.md#limits)).

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
