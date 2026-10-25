# Decisions (3.x)

[日本語](decisions.ja.md) · [3.x overview](../README.md) · [Configuration](configuration.md) · [Validation](validation.md)

What the 3.x line chose, what it did not, when, with the measured effect and what would reopen each: the 3.x counterpart of [2.x's decisions](../../v2/docs/decisions.md). The README keeps the reasons for its serving defaults in its "Why …" paragraphs ([serving defaults](../README.md#serving-defaults)), which the rows link to rather than repeat. The effects were measured on the reference hosts under the GPU clock cap, on the build the row names; the release figures are in [measured on the release](../README.md#measured-on-the-release). "—" means nothing is recorded: no measured effect, or nothing that would reopen the decision.

## Engine

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| Serve with TensorFold's native engine (Zig and CUDA), the kernels in the binary, beside 2.x on the Python engine | 2026-10-18 (3.0.0) | Upstream froze its Python engine (issue #286) and serves GLM from the native one. The tokens are the native engine's own (other kernels, BF16 KV), so the lines compare by NLL: 3.0.0's was within 0.021 of 2.x's reference values per domain ([differences from 2.x](../README.md#differences-from-2x)) | — |
| Follow upstream's releases; what serves other users goes upstream as pull requests, and the release branch keeps the rest | 3.0.0 to 3.8.0 | Upstream 1.0.12 (3.0.0), 1.1.1 (3.1.0), 1.1.2 (3.3.0), 1.1.3 (3.6.0) and 1.1.5 (3.8.0). This line's #1016, #1017 and #1018 became upstream's own in 1.1.1; #1179's patch rode 3.3.0 to 3.5.x and is upstream's own from 1.1.3; #1050 (FP4-Local's loader) rode 3.6.0's release branch and, with #1163, #1211 and #1178, is upstream's own from 1.1.5, so 3.8.0's release branch is the tag itself | — |
| TP=3 on the switchless ring, its bootstrap off the management Wi-Fi: rank 0's NCCL id over the ranks' liveness lines, upstream's from this line's #1178 | 2026-10-18 (3.0.0); upstream's bootstrap from 3.8.0 | With `NCCL_COMM_ID` set, NCCL's bootstrap looks for an interface in rank 0's subnet, which the ring's point-to-point `/32` addresses give rank 0's host alone. The bootstrap stays off the management Wi-Fi, which carried it unstably before the `/32` addresses ([three hosts in a ring](../../docs/qsfp-network.md#8-three-hosts-in-a-ring)). 3.0.0 to 3.7.0 handed the id over in a file (`TF_GLM_NCCL_ID_FILE`, a commit of this line's), each rank taking `NCCL_COMM_ID` out of NCCL's environment once the lines were up; upstream took #1178 on 2026-10-25, so the other ranks take the id over their lines and, naming `NCCL_SOCKET_IFNAME`, drop `NCCL_COMM_ID` before NCCL's first call | — |

## Checkpoint

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| XSFP4, the maintainer's derivative of NVIDIA's FP4-Local: a second choice in 3.3.0 and the default from 3.4.0. The line's aim beside upstream, which puts accuracy first: to study what quantization can do, FP4-Local's memory size and decode speed among it | 2026-10-23 (3.3.0, 3.4.0) | On this engine and the same documents XSFP4 is the closer to BF16 than NVIDIA's NVFP4 by top-1 agreement, NLL and KL at both TP sizes, and takes about 3.9 GiB less on rank 0 ([checkpoints](../README.md#checkpoints)) | — |
| XSFP4 alone: NVIDIA's NVFP4 and the published AXL weights, a rearrangement of it never accepted on 3.x, leave 3.x's choices; 1.x and 2.x keep them | 2026-10-24 (3.6.0) | With FP4-Local published, NVIDIA's NVFP4 was judged to have few users left on this line; each acceptance now covers one checkpoint. `CHECKPOINT` in the rank files still names another folder, outside the acceptance | — |

## Window and streams

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| TP=2 window 245,760 tokens until 3.4.0, 524,288 from 3.5.0 | 2026-10-18 (3.0.0), 2026-10-23 (3.5.0) | [Why 524,288 at TP=2](../README.md#serving-defaults): 245,760 was about the most that fit one stream beside NVIDIA's NVFP4 with BF16 KV; on XSFP4 524,288 holds one stream and a prompt cache, and the 499,254-token prompt fits. An A/B on 3.5.0's image gave the same edit speed at both windows (3.5.0 in [measured on the release](../README.md#measured-on-the-release)) | The engine sizes GLM's window from the memory free at start, as the Python engine's family did → let it choose |
| TP=3 window 1,048,576 tokens | 2026-10-18 (3.0.0) | The model's limit, as in 2.x | — |
| One request at a time (`PARALLEL=1`), not the engine's own choice | 2026-10-18 (3.0.0) | [Why one request at a time](../README.md#serving-defaults): with `--parallel` unset the streams and the prompt cache change from one start to the next; at TP=3 one start took two streams and a 0.1 GiB prompt cache, where one stream keeps 16 GiB. No comparison of throughput or latency between one stream and several is recorded | — |
| Replies of up to 32,768 tokens and effort `high` when a request names none | 2026-10-18 (3.0.0) | Carried from 2.x ([2.x decisions](../../v2/docs/decisions.md#window-limits-and-scope)); not measured again on 3.x. Whether XSFP4's chat template renders an unnamed effort as `max`, as NVIDIA's does, is not recorded | — |

## KV cache

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| BF16 latent and index keys, the engine's default, as the reference | 2026-10-18 (3.0.0) | Upstream declined lossy caches for the native engine (issues #309 and #401, 2026-10-06: bf16 caches with fp32 sums), so BF16 keeps upstream's kernels and its tokens. A token takes about twice 2.x's FP8 cache, so TP=2's window was shorter than 2.x's until XSFP4 ([why 524,288 at TP=2](../README.md#serving-defaults)) | — |
| The engine's opt-in FP8 latent cache (`--kv-cache fp8`) tried once at TP=2 with a 1M-token window, and not made the default | 2026-10-23 | One stream fit the 1,048,576-token window beside a prompt cache, and the 1,035,295-token prompt found its passphrases; prefill took about 5% longer, the NLL moved within its per-text interval, and the decode check's tokens differ from BF16's ([limits](../README.md#limits)). Not tried at TP=3 | Upstream finishes the cache's quality and device qualification, which it calls pending |

## Heat

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| A prefill waits between chunks while any rank's hottest zone is above 92 °C, until every rank is at or below 88 °C, on by default (2.x's band) | 2026-10-18 (3.0.0) | 2.x's derivation ([2.x decisions](../../v2/docs/decisions.md#heat)); not derived again on 3.x. On the native engine at TP=3, before 3.0.0, a 1,035,295-token prompt without a wait held one host at 94 to 97.7 °C (478 readings of 2 s at 94 °C or above), and the band cost 10.1% of its first token (1,119.6 s against 1,017.1). Lower bands (86/82/87) made the prompts that waited 26 to 89% slower without lowering that prompt's peak ([why the efficiency cores](../README.md#serving-defaults)) | The band alone ever reads 94 °C or more (a warm room, prompts back to back) → compare it with a ceiling on one binary |
| A look-ahead to a 93 °C ceiling (`TF_HEAT_CEILING`), a commit of this line's, in 3.0.0 to 3.2.0, removed in 3.3.0 | 2026-10-18 (3.0.0), removed 2026-10-23 (3.3.0) | In the same TP=3 trial, with and without it the prompt's first token came at 1,121.0 and 1,119.6 s, the hottest reading 93.3 and 93.0 °C and neither at 94 °C: its 10 waits replaced 9 of the band's. In 3.2.0's TP=3 acceptance it waited 7 times at 91.3 to 91.9 °C beside the band's 10. Keeping it meant a fork commit and a settings layout apart from upstream's at every rebase; upstream took this line's runbook pull request on the bands (#988) in place of a ceiling | As above |

## Cores

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| Every container on the efficiency cores (`CPUSET` unset: the cores with the lowest maximum frequency) | 2026-10-18 (3.0.0), kept in 3.1.0 | [Why the efficiency cores](../README.md#serving-defaults): the engine's two spinning threads a rank heat the CPU's zones; on every core long runs of replies reached the thermal watch's stop on 3.0.0's engine and came within 1 °C of it on 3.1.0's. Upstream's runbook gives the same cores for each GB10 rank since 1.1.1 | #1053 (the waiting ranks sleep while rank 0 has no stream), in since 1.1.2 → measure again whether the containers still need them: the forty replies and two requests at once on every core ([Next Action](../README.md#next-action)) |

## Drafts

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| The checkpoint's MTP head drafts at the engine's own depth policy; no DFlash2 drafter, no fixed depth | 2026-10-18 (3.0.0) | DFlash2's drafter weights are CC BY-NC-ND 4.0 (non-commercial), as 2.x found ([2.x decisions](../../v2/docs/decisions.md#drafts)). The depth policy is the engine core's, not 2.x's, so 2.x's depth measurements do not carry over; no depth comparison on 3.x is recorded | — |

## Fabric

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| NCCL's settings from 2.x: two rails a link, four channels, the IB transport named, and at TP=3 subnet-aware routing and NCCL's own IB transport ([NCCL](configuration.md#nccl)) | 2026-10-18 (3.0.0) | Measured on 2.x ([2.x decisions](../../v2/docs/decisions.md#fabric)). On the native engine only the memory was measured again: at TP=2 on upstream 1.1.0 with the 245,760-token window, NCCL's own 64 channels left 4.0 GiB at start against 5.3 to 5.8 GiB with four, 1.3 to 1.8 GiB more, in line with 2.x's 1.5 GiB. The speed at four channels against 64, the rails, the routing and the plugin were not measured again; every 3.x start ran every connection over `NET/IB` | — |

## Image and video input

| Decision | Date | Measured effect | Reopens when |
|---|---|---|---|
| Images and videos on by default (`VISION=1`, the engine's `--vision`), as 2.x serves images, on the condition that the tower did not cut the window or the prompt cache much | 2026-10-20 (3.2.0) | Measured before the image was built, at TP=2 with the 245,760-token window: the tower took 1.27 GiB on rank 0, the window held and the prompt cache was 4.4 to 5.4 GiB (5.2 to 6.3 GiB for text alone), so the default stayed on (3.2.0 in the [changelog](../CHANGELOG.md)). The condition was not stated again when the window moved to 524,288 | The tower cuts the window or the prompt cache much |

## Measures not evaluated on 3.x

Open items: no 3.x result either way.

- **Requests and inputs.** More than one request at a time, image and video URLs (`--vision-urls`), `/v1/responses` and `/v1/messages`, and harness integration ([limits](../README.md#limits)).
- **Engine settings.** Every engine setting but those [configuration](configuration.md) names as run: `TF_ROCE*`, `TF_GLM_PREFILL_REDUCE` and the other knobs ran at their defaults, `TF_GLM_PROMPT_K=shape` was not tried, and neither was DFlash2's drafter.
- **The FP8 latent cache at TP=3**, and at TP=2 beyond its one trial.
- **Every core since #1053**, which upstream 1.1.2 brought ([Next Action](../README.md#next-action)).
- **Other world sizes and hardware**: TP=4 and other GPUs were never run.
- **2.x's open items**, MTU and LPA ([2.x decisions](../../v2/docs/decisions.md#measures-from-1x-not-yet-evaluated-on-2x)), and its loop guard, which the native engine has as `--loop-guard`.
