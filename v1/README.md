# GLM-5.3-Flash-DGX-Sparks-BIZ

**Short name: GLM-5.3-Flash BIZ** (cite as "GLM-5.3-Flash BIZ 1.31.2"). It names this serving stack, which serves NVIDIA's pinned checkpoint as distributed. The published option's weights are **NVFP4 BIZ AXL** (AXL: the attention projections and `lm_head` in W4A16; on Hugging Face as [Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16), whose repository name describes the contents).

**BIZ** is the maintainer's mark and states the repository's intent; what it means and does not mean is in the [repository README](../README.md#biz).

[日本語](README.ja.md) · [Setup runbook](SETUP.md) · [Operations](docs/operations.md) · [Validation](docs/validation.md) · [Architecture](docs/architecture.md) · [Document map](docs/README.md)

## Summary

- **What it is.** A community setup and validation toolkit that serves NVIDIA's GLM-5.3-Flash NVFP4 checkpoint on **DGX Spark or compatible GB10 systems** through a pinned vLLM built into a reference image. It serves two hosts partitioned TP=2 over a QSFP/RoCE link, or three hosts at TP=3 cabled as a ring without a switch ([measurements on 1.24.0](docs/benchmarks.md#measurements-on-1240)). Published measurements come from MSI EdgeXpert (MS-C931) systems, two for TP=2 and three for TP=3. The focus is commercially usable licensing, pinned artifacts, observable checks and reversible operation.
- **Status.** **Accepted for routine use** for both profiles on two hosts at TP=2 and on three hosts at TP=3, within the scopes that [SETUP step 6](SETUP.md#6-qualify-the-full-model) records with what each acceptance rests on; harness acceptance is recorded per case in [harnesses](docs/harnesses.md#acceptance-matrix-and-status). Other hardware, more sequences than step 6 states and video input are outside the accepted scope ([status by scope](#status-by-scope)).
- **Two served profiles.** The **distributed defaults** serve the pinned weights exactly as NVIDIA distributes them. The **published option (NVFP4 BIZ AXL)** repacks the attention projections and `lm_head` to W4A16 for faster decode at a measured quality cost, and is an operator opt-in. [What has been verified](#what-has-been-verified) compares them and lists the status of every scope.
- **Precision.** Serving runs Marlin W4A16 on GB10. NVIDIA's model card evaluated its checkpoint under a different recipe on different hardware, so its accuracy table does not describe this stack; [validation](docs/validation.md#evidence-not-production-qualification) says which numbers do.
- **Licensing.** Apache-2.0 code; MIT weights that the operator downloads, not bundled; each artifact keeps its own terms ([licensing at a glance](../README.md#licensing-at-a-glance)).
- **Not validated.** Concurrent serving beyond the accepted scopes ([SETUP step 6](SETUP.md#6-qualify-the-full-model)), video input, full application quality, production reliability and maximum performance ([status by scope](#status-by-scope)).

## What you deploy and supported hardware

The stack is **Z.ai's original model → NVIDIA's distributed NVFP4 checkpoint → this repository's GB10 runtime adaptation and validation tools**.

| Item | Deployment information |
|---|---|
| Original model | [Z.ai GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) |
| Checkpoint and download source | [nvidia/GLM-5.3-Flash-NVFP4](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4); [runtime.lock.json](config/runtime.lock.json) owns the fixed revision |
| This distribution's role | Acquire and verify weights, adapt the runtime for GB10, launch and evaluate performance/quality. The distributed defaults serve NVIDIA's base checkpoint as it is, without project-specific requantization or fine-tuning. Serving a requantized copy is an [optional setting](docs/server-configuration.md#distributed-defaults) that an operator enables; nothing requantized is bundled in this repository |
| Hardware | Linux ARM64 systems, each with GB10, 128 GB-class unified memory and NVIDIA GPU-enabled Docker: two at TP=2, where the model is partitioned over a QSFP/RoCE connection, or three at TP=3 in a switchless QSFP ring ([setup](SETUP.md#three-hosts-at-tp3)) |
| Tested scope | Published measurements are from MSI EdgeXpert. Other DGX Spark-compatible systems require driver/GPU/memory/fabric checks in the [setup runbook](SETUP.md#1-collect-inputs-and-inspect-both-hosts); a product name alone does not qualify them. Windows supports management/CPU checks; inference runs on the Linux hosts |
| Storage | Weights live in each Linux host's Hugging Face cache. Reserve approximately 205 GB of disk per host plus images and working space. Each host stores the complete checkpoint even under tensor parallelism; partitioning happens at load time. [Paths and verification](docs/operations.md#artifact-storage-and-paths) |
| Server configuration | [One server TOML](docs/server-configuration.md) groups context, cache, MTP, LPA, generation and per-node settings for the launcher and client. The distributed template enables the serial optimized profile on the pinned weights, the published option's template adds the repacked weights at two sequences, and the three-node template serves the defaults on a ring; [server defaults and required assets](docs/server-configuration.md#distributed-defaults) |

The source checkout contains code, pinned references and build instructions. The base checkpoint and built Docker images are acquired/built separately. MTP uses checkpoint-provided tensors through a separate metadata view; the trained LPA auxiliary projector is available as a separate [GitHub Release asset](docs/lpa.md#download-the-trained-projector). See [artifact roles, package contents and storage](docs/operations.md#artifact-storage-and-paths).

NVFP4 names the downloaded weight format. The tested reference profile executes with Marlin **W4A16**, which differs from NVIDIA's W4A4 recipe; the accuracy table on NVIDIA's model card was measured under that recipe, on other hardware and another engine path, and is not a quality claim for this serving. See [precision and validation scope](docs/validation.md#evidence-not-production-qualification) for what the card's figures describe and which numbers describe this stack.

[LPA (late-prefill approximation)](docs/lpa.md) ships disabled in the distributed server template and is a batch opt-in ([why](docs/lpa.md#operating-scope)). Teacher replay, corpus sampling and projector fitting tools are included for that path; its quality/speed acceptance is separate from the verified scope below.

## Prerequisites

- Python 3.11+ for checkout-local tools. CPU checks run on Windows and Linux.
- Linux ARM64, NVIDIA GPU-enabled Docker and a GB10 GPU for GPU validation.
- Two suitable systems with a verified QSFP/RoCE path (TP=2), or three in a switchless QSFP ring (TP=3; [three hosts at TP=3](SETUP.md#three-hosts-at-tp3)).
- Host kernel: current DGX OS updates can break two-host RoCE; see [host kernel and multi-node RoCE](../docs/hosts.md#host-kernel-and-multi-node-roce) before updating.
- Storage on each deployment node for the model files ([size](#what-you-deploy-and-supported-hardware)), plus images, caches and optional fixtures. A full checkpoint does not fit one 128 GB node.

## Start from a checkout

Run these commands from the `v1/` directory of a checkout on the target Linux host. `state/` and `records/` stay at the checkout root, beside `v1/`, so commands reach them as `../state/` and `../records/`:

~~~sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/huggingface.lock.txt
python -m glm53_setup --help
python -m glm53_setup --version
~~~

This repository is a checkout-based operator toolkit, not a published PyPI package. The ordered deployment gates, from host inspection to acceptance, are in the [setup runbook](SETUP.md).

### Prepare assets

~~~sh
python -m glm53_setup download --background
python -m glm53_setup verify-download --hf .venv/bin/hf --output ../records/checksum --wait
python -m glm53_setup prepare-image --background
python -m glm53_setup build-reference
~~~

Downloads reuse the Hugging Face cache. A process lock prevents overlapping downloads; status is written atomically. A paused download causes the verification wait to exit instead of resuming it. These commands explicitly start work: do not run another download while transferring the same cache.

The fixed model revision, base-image digest and local reference tag are in [config/runtime.lock.json](config/runtime.lock.json). Building the reference image does not start inference or qualify a deployment. [Canonical sparse candidate ordering](docs/candidate-order.md) and the other runtime patches live in the image: updating source requires a rebuild, and a runtime rebuilt at another site still needs qualification.

### Validate before serving

Follow the [single-GPU fixture procedure](docs/component-validation.md#reproduce-the-single-gpu-fixture). Its results distinguish completed execution, repeatability, and numerical differences.

Routine-use acceptance is a record, not a command: [SETUP step 6](SETUP.md#6-qualify-the-full-model) states its scope and where each item's evidence is. What `server preflight` checks before a start, and what it does not certify, are in the [launch checks](docs/operations.md#full-model-launch-checks).

## What has been verified

**Distributed defaults select the serial optimized profile with image input and no lifetime deadline; video input is rejected.** Their context, KV and reserve are in [server defaults](docs/server-configuration.md#distributed-defaults); the checks behind them are [image input](docs/vision.md) and [measurements on 1.6.0](docs/benchmarks.md#measurements-on-160); [256K capacity checks](docs/benchmarks.md#real-input-checks-at-256k) cover the text-only alternative.

### Headline measurements (1.29.9)

The TP=2 rows were measured on 1.19.0 to 1.22.0; TP=3 follows the tables. Two GB10 systems, TP=2, FA2 prefill, one token order inside each expert, indexer top-k ties settled, MTP k=3. Two profiles: the **distributed defaults** (the pinned NVIDIA weights, exactly what the template serves) and the **published option** (the attention projections and `lm_head` repacked to W4A16 NVFP4, served through `runtime.derived_checkpoint` with the KDA input projection declared split; weights at [Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16)). The option's column is the profile the reference pair serves, the [two-sequence AXL profile](examples/server.axl.example.toml). **Both columns were measured on 1.19.0 on 2026-09-28, in one window**: the pair switched from the served option to the defaults, then to the option at one sequence (for repeatability), then back to the served option, with the same drivers and both ranks of both profiles on performance cores ([measurements on 1.19.0](docs/benchmarks.md#both-profiles-in-one-window-with-a-gpu-clock-cap-2026-09-28)). The tool-argument gate row alone was measured on 1.22.0 on 2026-09-29. The images measured since, up to 1.29.9, reproduced both profiles' decode-check token ids ([measurements on 1.29.9](docs/benchmarks.md#measurements-on-1299)); the shared-memory reader spin that every template sets costs the option 1.4% of counting decode. **The pair and its neighbor ran with the GPU clock capped at 2,200 MHz**, and each stage waited for temperatures to come down first. GB10 machines can power off under sustained load; the cap cost about 2% of prefill and 1–5% on long inputs ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)). Medians of three or nine runs; ranges, conditions and every earlier version are in [benchmarks](docs/benchmarks.md). Task types are always listed counting / prose / code.

| Category | Measure | Distributed defaults (GLM-5.3-Flash BIZ on the pinned weights) | Published option (NVFP4 BIZ AXL, the served two-sequence profile) |
|---|---|---|---|
| Prefill | Prefill, 38,962-token prompt | 1,233.4 tok/s | **1,259.1 tok/s** |
| Decode | Decode after a 2,048-token prompt: counting / prose / code | 32.59 / 21.12 / 28.21 tok/s | **46.73 / 30.06 / 39.48 tok/s** (32.87 / 22.43 for counting and prose while the other runs) |
| Decode | Decode, 512 tokens after a fixed short prompt | 27.18 tok/s | **42.63 tok/s** |
| Decode | sparkDash DecodeBench, 128 tokens: structured / prose / code / json | 33.24 / 25.45 / 27.53 / 26.32 tok/s | **48.04 / 31.28 / 37.34 / 34.72 tok/s** |
| Startup | Weight loading, rank 0 (`Loading weights took`, main model) | 122.6 s (`Model loading took` 265.6 s; 787–811 s before the clone) | **120.7 s** |
| Long input | ~200K-token input, one passphrase at the midpoint | 178.9 and 176.6 s, correct (199,652 tokens) | **170.1 s, correct** (199,649 tokens); two such requests together: 336.0 s, both correct, no preemption |
| Long input | 255,950-token input, one passphrase at the midpoint | 229.5 s, correct | **220.9 s, correct** |
| Long input | 261,573-token three-position reference, fenced prompt (the canonical form) | 239.8 s, correct 3 of 3 | **235.0 s, correct 3 of 3** |
| Long input | Maximum capacity, 262,080 input + 64 output tokens | 253.0 and 252.7 s, finite logprobs | **244.8 and 244.7 s, finite logprobs** |
| Quality | Teacher-forced NLL on `server agreement`'s four texts: Japanese / English / code / mathematics | 1.5963 / 2.0241 / 0.9479 / 0.5931 | 1.6270 / 1.9946 / 0.9601 / 0.6275 (1.6645 / 2.0024 / 1.0031 / 0.6279 on the one-sequence profile, 2026-09-21) |
| Quality | tool-eval-bench, 69 standard scenarios | 91/100, three failures, Safety Gate not passed | 88/100, the same three failures, Safety Gate not passed |
| Quality | tool-eval-bench through the optional [tool-argument gate](docs/harnesses.md#tool-argument-gate) (2026-09-29) | Not measured | **90/100, two failures, Safety Gate passed** (the same day on the model API: 88/100, Safety Gate not passed; [measurements](docs/benchmarks.md#tool-eval-bench-through-the-tool-argument-gate-2026-09-29)) |
| Repeatability | Identical requests at temperature 0 (`max_num_seqs = 1`) | Same completion nine times of nine (the decode check, three task types three times each); two sent together queue and each repeats its lone completion (18 of 18) | The same when served with `max_num_seqs = 1` (two sent together: 18 of 18); the decode check's completions were the same on all eight 1.19.0 launches. Not claimed for the served two-sequence profile while two requests are in flight |
| Memory | Lowest available memory on the head during the bench | 6.2 GiB (3 GiB of KV) | 7.56 GiB, 7.34 GiB during two 200K requests (6 GiB of KV) |

| | Distributed defaults | Published option |
|---|---|---|
| **Pros** | Lossless with respect to the pinned NVIDIA weights. Ships in the template with no extra download | Decode about 1.4 times the defaults' on counting, prose and code in the table above. Prefill 2% faster than the defaults in the same window, the split projection having removed the earlier penalty. Identical requests still repeat bit for bit when served with `max_num_seqs = 1`. At the same 3 GiB of KV and one sequence the head kept about 4 GiB more available at 256K ([1.7.0](docs/benchmarks.md#the-reference-pairs-serving-profile-attention-and-lm_head-repacked-depth-3)) |
| **Cons** | The slower decode of the two on every task type | Not lossless: NLL 1 to 6% higher on three of four texts. Outside the template: a second checkpoint to acquire and place. Above about 250K tokens it needs the slot-mapping guard that images built from 1.7.0 carry. In a long-context lookup it twice read the record just before the one asked, where the defaults were right ([prefix-cache gate](docs/correctness-gates.md#prefix-cache-correctness-gate)) |
| **Choose it for** | Code and tool use, and any workload that must match the pinned weights | Japanese prose and other generation-heavy serial work where the NLL cost is acceptable |

How fast MTP decodes depends on how predictable the text is: in the table above, either profile decodes counting about 1.5 times as fast as prose, because more of each draft is accepted. [Depth three for both checkpoints](docs/speculative-decoding.md#depth-three-for-both-checkpoints-2026-09-21) has the acceptance lengths, and [profiles by workload](docs/optimization-overview.md#profiles-by-workload) the choice. Every decode figure has both ranks' workers on performance cores; with either rank on efficiency cores decode falls to about a third, which [`nodes[].cpuset_cpus`](docs/server-configuration.md#optional-cpu-placement) prevents ([measurements on 1.15.0](docs/benchmarks.md#measurements-on-1150)).

**Three hosts at TP=3 (1.24.0, 2026-09-29 and 10-01).** 30 GiB of KV per rank holds twelve 262,144-token requests (3,258,809 tokens). Decode on counting / prose / code: 41.04 / 26.47 / 34.99 tok/s with the distributed defaults, 51.00 / 30.10 / 39.48 with the published option. Teacher-forced NLL against TP=2, compared position by position, stays within the spread of TP=2 launches that differ only in numerical state. The published option answered three passphrases in a 1,038,423-token prompt (first token at 1,058 s). Details in [measurements on 1.24.0](docs/benchmarks.md#measurements-on-1240).

### Status by scope

Each row states the status and the document that owns the evidence; the narrative lives there. One active sequence unless stated otherwise.

| Group | Scope | Status |
|---|---|---|
| Tooling | Pinned checkpoint download and official checksum verification; official ARM64 image preparation and reference-image build | Implemented |
| Fixture | Candidate-preserving NoPE reference attention | GPU-tested |
| Fixture | Four-layer, single-GB10 fixture with Marlin W4A16 | Generation and state comparisons passed; [validation](docs/validation.md) |
| Fixture | Batch-invariant mode with the pinned SM120 sparse MLA backend | Unsupported |
| Full model | Two- and three-rank NCCL collectives on the pinned base | Tested patterns passed over RoCE, the pair and the three-host ring; [conditions and limits](../docs/nccl-validation.md) |
| Full model | 45-layer TP=2 reference profile | Accepted for routine use within the scope in [SETUP step 6](SETUP.md#6-qualify-the-full-model); [benchmarks](docs/benchmarks.md) |
| Full model | TP=3 on three hosts in a switchless QSFP ring | Accepted for routine use within the scope in [SETUP step 6](SETUP.md#6-qualify-the-full-model); [measurements on 1.24.0](docs/benchmarks.md#measurements-on-1240) |
| Full model | Identical requests at temperature 0 | With `max_num_seqs = 1`, repeat bit for bit within a launch and across launches, through the [repeatability switches](docs/server-configuration.md#repeatability-switches) that every template turns on; every launch after a switch is still checked (weight digest, decode check, kernel hashes). Not claimed while more than one sequence is in flight ([concurrency scope](docs/validation.md#concurrency-scope)); [how each cause was found](docs/repeatability.md) |
| Full model | Image input (vision) at 256K | One synthetic image answered correctly, text/tool regressions passed, video rejected; on 1.19.0 both profiles passed the seven regression checks and read large images and several images in order; from 1.29.0 both profiles answer images up to the model's limit; direct attachment in harness user interfaces not checked; [measurements and limits](docs/vision.md) |
| Full model | Long Japanese and Korean output | No broken characters at temperature 0 and sampled, on both profiles and at TP=3; reasoning text not exercised; [check and limits](docs/correctness-gates.md#multibyte-output) |
| Concurrency | More than one active sequence | **Not supported** in the distributed defaults (`max_num_seqs = 1`; requests queue). The published option's example serves two sequences from 6 GiB per rank and is **accepted for routine use** within the scope in [SETUP step 6](SETUP.md#6-qualify-the-full-model). Repetition is not claimed in this scope. More sequences need more ranks: TP=3 is in the row above. [Concurrency scope](docs/validation.md#concurrency-scope) |
| Evaluation | FreedomBench: the English suite, the Japanese translation (FB-04), framing and evidence placement (FB-05) | English and Japanese suites answered on both profiles; FB-05 run on the published option; its LPA part not run; [results and limits](docs/freedombench.md) |
| Evaluation | HLE, a text and an image subset of 100 questions each, on both profiles under a bounded budget | Run 2026-09-28 to 10-03; not comparable with published HLE values; [results and limits](docs/hle.md) |
| Harness | ZCode / Claude Code integration | Basic API group and the shared H cases passed on the accepted route, the npm ZCode CLI; the other routes and per-case status are in the [acceptance matrix](docs/harnesses.md#acceptance-matrix-and-status) |
| In the template | FA2 prefill (`runtime.fa2_attention`) | Adopted: faster prefill, one sequence's decode on the reference path, excludes LPA; [measurements](docs/benchmarks.md#measurements-on-160) |
| In the template | MTP k=3 with the BF16 draft | Depths 1 to 5 measured on ten inputs with the requantized checkpoint, 1, 3 and 4 with the pinned one; k=3 kept for both; [speculative decoding](docs/speculative-decoding.md#depth-three-for-both-checkpoints-2026-09-21) |
| In the template | Prefix caching (APC) | Accepted for the measured serial long-prefix reuse workload (experimental); [measurements](docs/benchmarks.md#independent-full-model-prefix-caching-p19). The cold/warm correctness gate passed on the defaults and found no cache defect on the option; [gate](docs/correctness-gates.md#prefix-cache-correctness-gate) |
| In the template | Checkpoint retention | Adopted for the exact-primed mid-edit workload after history and A/B/A tests at the native interval ([retention A/B/A](docs/benchmarks.md#apc-history-retention-baseline)); the block-independent `dense` setting is equivalent in the measured layout and the final combined integration is qualified separately; [contracts](docs/launch-safety.md) |
| In the template | Fused unpack, async index checks | Independently measured and enabled; [overview](docs/optimization-overview.md) |
| In the template | Shared-memory reader spin 0.002 s (`runtime.shm_spin_seconds`, P29) | Adopted for the head's temperature at a small decode cost, measured on the TP=2 pair; TP=3 by extension, unmeasured; [measurements](docs/benchmarks.md#measurements-on-1250) |
| Optional, off | Requantized attention projections and `lm_head` (`runtime.derived_checkpoint`, P23) | The published option above; adding the shared experts was measured and not adopted; [measurements](docs/benchmarks.md#the-reference-pairs-serving-profile-attention-and-lm_head-repacked-depth-3) / [catalog](docs/optimization-catalog.md) |
| Optional, off | APC-first LPA (P22) | Calibrated, combined with MTP/fusion/async checks and checked on held-out documents; a batch opt-in; [contract](docs/apc-lpa-design.md) |
| Measured, not adopted | Expert Parallel, PP2, decode CUDA Graphs, a draft depth from acceptance history, a confidence gate on the draft, two draft-side settings | Each measured on the full model with its number in the owner document; [overview](docs/optimization-overview.md), [speculative decoding](docs/speculative-decoding.md#beyond-a-fixed-depth-2026-09-21) |
| Measured, not adopted | Cross-layer indexer reuse (CSA2, P16) | Stopped at its cost gate; [design and result](docs/indexer-reuse.md) |
| Not validated | Video input, full application quality, production reliability, maximum performance | **Not validated** |

The fixture keeps the original widths, experts and selected tensor bytes, but is a truncated model. It is not a language-quality benchmark. Marlin W4A16 is a different arithmetic profile from NVIDIA's W4A4 recipe. See [the evidence and limits](docs/validation.md).

## Business-use objectives (BIZ)

This project makes **`nvidia/GLM-5.3-Flash-NVFP4` on DGX Spark-class systems easier to evaluate, adapt and operate for business use**. Its engineering work covers three connected concerns:

- **License and provenance selection:** prefer commercially usable MIT/Apache components, pin their origin and preserve notices. The [licensing guide](../docs/licensing.md) distinguishes the terms for code, weights, containers and harnesses.
- **Evidence about political bias and source fidelity:** use [FreedomBench and business-context extensions](docs/freedombench.md) to examine political-topic answers, refusals and unsupported claims inserted into supplied material. Report the tested scope and failures; a benchmark score is not proof of universal ideological neutrality. Results, and what was not run, are in that document.
- **Measured performance tuning:** investigate MTP, LPA, prefix caching, CUDA fusion, batching and parallel execution while checking task quality, memory and recovery. The [optimization overview](docs/optimization-overview.md) shows where each measure acts and which profile fits which workload; the [performance and quality catalog](docs/optimization-catalog.md) records candidates, evidence and deferred work as a comparison baseline for future GLM versions.

For decode acceleration, we selected **the checkpoint's standard MTP with three speculative tokens (k=3)**, without adding an external draft model, and one depth for both checkpoints; the reasoning is in [depth three for both checkpoints](docs/speculative-decoding.md#depth-three-for-both-checkpoints-2026-09-21).

Completed measurements and remaining gates are identified above and in the linked validation documents; what BIZ does not imply is in the [disclaimer](#disclaimer).

## Related research outside this repository

**Euryale** is a separate, unpublished research project on proposing several draft tokens from a frozen model's intermediate representations, taking GLM-5.3-Flash on two GB10 hosts as its first target. It is not part of this distribution and, beyond the [canonical candidate ordering](docs/candidate-order.md) that came out of it, changes nothing in this repository's checkpoint, runtime or defaults. Its first design, a light auxiliary proposer, was trained in three variants on teacher data captured from the full model and compared with the checkpoint's standard MTP under the same conditions: every candidate was slower than MTP k=3 in every measured condition, so it was not adopted. The project has moved to a DFlash-style draft with its own layers that read the target's features as keys and values, so far trained only as a pilot from stored features. Until a Euryale draft passes a same-condition comparison under the [catalog's acceptance gates](docs/optimization-catalog.md#functional-acceptance-and-defaults), MTP k=3 remains the default speculation path.

### Other GLM-5.3-Flash recipes for DGX Spark systems

Several public recipes serve the same model on the same class of hardware with different engines, quantization and trade-offs. They are worth comparing before choosing one. This table owns their links, their licenses as read between 2026-09-18 and 2026-10-11 and what this repository took from each; other documents cite them by name and pull request only. Code that was adapted carries its notice in [third-party notices](../THIRD_PARTY_NOTICES.md).

| Recipe | License | What this repository took from it |
|---|---|---|
| [amasu/glm53-flash-cluster](https://github.com/amasu/glm53-flash-cluster), preserving the kingjones30 recipe | Apache-2.0 / MIT | **Code adapted:** the NoPE zero-padding patch structure and recipe |
| [tenhkspark/glm53-flash-nvfp4-2node](https://github.com/tenhkspark/glm53-flash-nvfp4-2node) and the [GLM-5.3-Flash-NVFP4-h checkpoint](https://huggingface.co/tenhkspark/GLM-5.3-Flash-NVFP4-h) (formerly Wabi) | Apache-2.0 (code), MIT (weights) | No code, and none of its weights. Its W4A16 NVFP4 requantization of the BF16 attention projections was evaluated as P23 and grew into the published option above (attention and `lm_head`); the measurements are in the [optimization catalog](docs/optimization-catalog.md) |
| [MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks) | AGPL-3.0 | No code. Mechanisms and measurements: warmup ladder and its correctness canary (#268), stall detection, KV capacity readout, the NCCL channel setting, launch-safety requirements, the RoCE GID shift (#277), field runbooks; its note that the KDA `f_b`/`g_b` projections at 22 heads per rank do not pass Marlin when quantized, which the published option met at TP=3 (this stack copies their inputs first) |
| MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold | — | Listed with the other recipes on TensorFold in [2.x's table](../v2/README.md#other-recipes-on-tensorfold), which owns its link and what the 2.x line took from it; 1.x took nothing from it |
| [sfxnz/GLM-5.3-Flash-NVFP4-vLLM-2x-DGX-Spark](https://github.com/sfxnz/GLM-5.3-Flash-NVFP4-vLLM-2x-DGX-Spark) | MIT | No code. The SM90 attention path, and the foreign-container launch guard proposed in its PR #12 (closed unmerged), as reference points |
| [drowzeys/keys-vLLm.0.27.1-GLM-5.3-Flash-NVFP4-NVFP4KV-1M-Context-Abliterated](https://github.com/drowzeys/keys-vLLm.0.27.1-GLM-5.3-Flash-NVFP4-NVFP4KV-1M-Context-Abliterated) | Apache-2.0 | No code. Its zero-RoPE shim and reduced `index_topk` as a comparison for the attention probes |
| [tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark](https://github.com/tonyd2wild/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark) | none | No code. Measurements and field reports: GB10 memory behaviour, power loss during checksums, mean acceptance length, concurrency results. Its 2026-09-20 note on quantizing the attention and MLP projections reached the same tensor set as P23 independently, at TP=4 and with quality unmeasured ([catalog](docs/optimization-catalog.md)). Since 2026-09-29 its default is a TP=2 port of knapcio's stack; its issue #26 carries a third-party TP=3 measurement with NVIDIA's checkpoint on three hosts cabled as a triangle, a reference point for [catalog P28](docs/optimization-catalog.md#performance-initiatives) |
| [FlyCockpit/GLM-5.3-Flash-3x-DGX-Sparks](https://github.com/FlyCockpit/GLM-5.3-Flash-3x-DGX-Sparks) | MIT | No code. Its TP=3 geometry on vLLM with NVFP4 weights (attention and KDA heads, expert width and vocabulary zero-padded, staying tensor-parallel) as the reference for this stack's own load-time padding ([catalog P28](docs/optimization-catalog.md#performance-initiatives)); its measurements use another checkpoint and image |
| [0xSero/GLM-5.3-Flash-EXL3-1x-DGX-Spark](https://github.com/0xSero/GLM-5.3-Flash-EXL3-1x-DGX-Spark) and the [EXL3 Spark mosaic](https://huggingface.co/0xSero/GLM-5.3-Flash-EXL3-Spark) | MIT (repository code), MIT (model card for the separate weights) | No code or weights adopted. Reference for the mosaic quality panel, cold/warm measurements and verification that an overlay was actually loaded. The single-Spark mcg MTP recipe and the mul1 mosaic use different artifacts and runtimes; their speed, quality and MTP results must not be combined |
| [knapcio/GLM-5.3-Flash-4x-DGX-Spark-TP4](https://github.com/knapcio/GLM-5.3-Flash-4x-DGX-Spark-TP4) | MIT for repository-owned material; the Tony-origin material its NOTICE lists is excluded | **Code adapted:** the record format, lookup and quote tasks and their parsing from its prefix-cache correctness scan (`bench/prefix_scan.py`), cold against warm, in [`server prefix-gate`](docs/server-configuration.md#commands) ([the gate's result](docs/correctness-gates.md#prefix-cache-correctness-gate), catalog P19). Its analysis of KDA checkpoints misaligned with the scheduler's chunk ends (issue #2), which this stack does not meet: the pinned vLLM's align mode gives the KDA state the attention block (`block_size` = `mamba_block_size`; see Next Action) |
| [kindlingai/glm-5.3-flash-gx10](https://github.com/kindlingai/glm-5.3-flash-gx10) | none (no license file; some files carry Apache-2.0 headers) | No code. Mechanisms and measurements: the motivation and measurements for RecoverSSM (one KDA recurrent state per request, [catalog P30](docs/optimization-catalog.md#performance-initiatives)), the shm_broadcast spin-wait observation, a three-host measurement at 1M tokens (issue #52), and the long-prefill threshold at a multiple of the KDA block for TP=3 |
| [jetnet/glm53-flash-nvfp4-tp3](https://github.com/jetnet/glm53-flash-nvfp4-tp3) | MIT | No code. Its TP=3 configuration for NVIDIA's checkpoint and its measured KV bytes per token and rank, as a reference for [catalog P28](docs/optimization-catalog.md#performance-initiatives) |
| [coolbho3k/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark](https://github.com/coolbho3k/GLM-5.3-Flash-NVFP4-DFlash2-2x-DGX-Spark) | none | No code. Its decode context parallelism (DCP2: the MLA KV split along the sequence, about 4.6–4.7M logical tokens reported) as the alternative to KV held on every rank under [catalog P28](docs/optimization-catalog.md#performance-initiatives) |
| [Enntity/sparkglm](https://github.com/Enntity/sparkglm), on its own engine [Atlas](https://github.com/Enntity/atlas) | AGPL-3.0 | No code. A recipe on the same NVIDIA checkpoint and the same pair of Sparks with its own engine, speculative decoding (DFlash2) and a prefill its authors state is not row-invariant. Reference points: its persistent MoE decode kernels (one CTA per SM, prefetching the next expert tile, bit-identical to its earlier kernels), the KV split across the two hosts, the prefix cache on disk, the display carveout used as KV cache, and its single-stream decode measured over many prompts in alternating rounds. Its figures come from another engine and another contract and do not compare with this repository's |

## Disclaimer

- **BIZ is an intent, not a promise** ([repository README](../README.md#biz)). This line's business-use readiness is the acceptance for its declared scope ([status by scope](#status-by-scope)).
- **The kpool tail ring fix is partial.** The port of [vLLM #58454](https://github.com/vllm-project/vllm/pull/58454) (`patch_kpool_ring`) is a partial fix by upstream's own account, and follow-up changes are expected ([operations](docs/operations.md#full-model-launch-checks)).
- **The tail ring depends on the MTP depth.** Its block grows with the depth, so the KV-capacity breakdown and the figures recorded from a boot change with it ([KV capacity](docs/server-configuration.md#kv-capacity-and-ram-requirements)).
- **Repeatability references for decodes whose context passes 2,048 tokens were re-baselined on 1.19.0.** Past the indexer's `index_topk` (2,048), the ring fix can change the compressed keys of pools built during decode with MTP, so reference hashes recorded on earlier images are not a baseline for them. For a prompt past that length, the decode check's hashes on both profiles were taken then ([measurements on 1.19.0](docs/benchmarks.md#measurements-on-1190)); a launch is compared with the previous launch of the same profile as [after a switch](docs/launch-safety.md#after-a-switch-the-decode-check) says (`token_ids_sha256` across 1.29.8, whose tool fixed the completion text). No reference was taken for an output that passes it.
- **`runtime.stable_indexer_topk = false` exposes the defect that [vLLM #58785](https://github.com/vllm-project/vllm/pull/58785) fixes**, a pull request still open upstream: the persistent top-k can lose candidates on overflow. Keep the key on (every template sets it).

## Next Action

Each item is a trigger and what this repository then does.

- [vLLM #56868](https://github.com/vllm-project/vllm/issues/56868) / [#56605](https://github.com/vllm-project/vllm/issues/56605) follow-ups to #58454 merge → port them as source-pinned patches.
- [vLLM #57161](https://github.com/vllm-project/vllm/pull/57161) (kpool compress rework) merges → re-read `patch_kpool_seed` and `patch_kpool_ring` against it.
- A fix equivalent to #58785 reaches the pinned vLLM → only then allow `runtime.stable_indexer_topk = false`; when [vLLM #55122](https://github.com/vllm-project/vllm/pull/55122) merges, consider replacing the local stable sort with its kernel.
- [vLLM #58979](https://github.com/vllm-project/vllm/pull/58979) (the indexer key normalised without a rank-local compiled kernel, for [#58636](https://github.com/vllm-project/vllm/issues/58636)) or an equivalent fix reaches the pinned vLLM → check the launch states on both profiles with `runtime.inductor_deterministic` off, and let the templates drop the key only if the ranks agree and the completions repeat ([repeatability](docs/repeatability.md) records the draft's check).
- vLLM 0.31.0 (2026-10-05) contains #58454, #57477 and [#58846](https://github.com/vllm-project/vllm/pull/58846) → **the pin stays (decided 2026-10-06)**. Moving would port five build patches (indexer top-k, APC/LPA, slot mapping, TP padding, samplers), follow the model sources from `glm5next/nvidia/` to `glm5next/common/`, rebuild both overlays of the published option, and take FlashInfer from 0.6.18 to 0.7.0.post1, so every baseline would be measured again, for no speed or correctness the 1.x line lacks today. Revisit when a 1.x user asks for it, when an upstream fix cannot be carried as a source-pinned patch, or when [vLLM #54296](https://github.com/vllm-project/vllm/pull/54296) or [#50843](https://github.com/vllm-project/vllm/pull/50843) merges. The move then drops `patch_kpool_seed` and `patch_kpool_ring`, brings [#55736](https://github.com/vllm-project/vllm/pull/55736) (decode improvements), [#55353](https://github.com/vllm-project/vllm/pull/55353) (retention as a CLI flag) and [#53007](https://github.com/vllm-project/vllm/pull/53007) (KV LCM change), each to be re-measured, and FlashKDA for the KDA prefill on GB10: keep the Triton kernel with `additional_config.kda_prefill_backend = "triton"` or take the decode hashes again.
- The pin moves past [vLLM #59126](https://github.com/vllm-project/vllm/pull/59126) (`0979892992`) and [#59565](https://github.com/vllm-project/vllm/pull/59565) (`5688a4dd4a`) → drop `patch_vision_rope` and `patch_image_budget` (vLLM 0.31.0 has neither).
- [vLLM #57128](https://github.com/vllm-project/vllm/pull/57128) (Mamba prefix-cache hits ignoring the speculative margin, [#53912](https://github.com/vllm-project/vllm/issues/53912)) merges → port it as a source-pinned patch. The serving profiles match the reported conditions (prefix caching, MTP k=3, Mamba cache mode `align`); a field report on another stack describes content from one request appearing in another, which has not been seen here.
- [vLLM #54296](https://github.com/vllm-project/vllm/pull/54296) merges and reaches the pin → drop the slot-mapping guard (`patch_slot_mapping`).
- [vLLM #50843](https://github.com/vllm-project/vllm/pull/50843) merges and reaches the pin → drop the samplers' vocabulary bound (`patch_sampler_nonfinite`).
- [vLLM #58868](https://github.com/vllm-project/vllm/pull/58868) (on GB10, weights copied to the GPU straight from the safetensors file mapping are slow, [#58726](https://github.com/vllm-project/vllm/issues/58726); it touches the pages first) merges and reaches the pin → consider dropping `patch_load_clone`, which works around the same cost by cloning each tensor into anonymous memory.
- [vLLM #59528](https://github.com/vllm-project/vllm/pull/59528) (the kpool tail's slot mapping writes into the null block from rows marked 0: dummy runs, graph capture, padding) merges → port it as a source-pinned patch beside `patch_kpool_ring`.
- To verify: the host CPU's delivered frequency. [knapcio issue #7](https://github.com/knapcio/GLM-5.3-Flash-4x-DGX-Spark-TP4/issues/7) found Grace cores at their lowest performance level under the `performance` governor on DGX OS 7.5 with kernel 6.17 (ASUS GX10), and decode 8–10% faster on the 7.0 kernel. The reference hosts ran 6.17.0-1032 until 2026-10-14 and run 7.0.0-1019 since, booted with the `kho=off` that multi-node RoCE needs on it ([host kernel](../docs/hosts.md#host-kernel-and-multi-node-roce)); the frequency was read on neither → in an authorized window, read each host's CPPC feedback counters around a busy loop on one X925 core. Every line's figures depend on it.
- `mtp.disable_eagle_block_drop` (opt-in from 1.29.0): with the last matched block kept, a 124,272-token cached resend reached its first token in 4.4 s instead of 8.5 s on both TP=2 profiles, with the same replies and decode-check completions ([measurements on 1.29.0](docs/benchmarks.md#measurements-on-1290)); it stays an opt-in that no template sets, because vLLM calls the setting experimental for the draft's acceptance and startup refuses it with LPA → vLLM makes the setting its default or drops the experimental warning → check it against LPA, measure the MTP acceptance length on requests that hit the cache, and reconsider adopting it in the templates.
- The vLLM pin moves past [#56960](https://github.com/vllm-project/vllm/pull/56960) (KDA prefill checkpoints for GLM-5.3-Flash) → make sure the new pin carries [vLLM #59759](https://github.com/vllm-project/vllm/pull/59759) or port it: from #56960 on, a prefill step that saves a linear-attention checkpoint in the middle of a chunk can return garbage under MTP and prefix caching. The pinned vLLM sets no prefill checkpoint blocks for GLM, so 1.29.0 does not reach that path.
- [vLLM #48032](https://github.com/vllm-project/vllm/pull/48032) (deterministic Marlin MoE route alignment, for [#52525](https://github.com/vllm-project/vllm/issues/52525)) merges and reaches the pin → consider replacing the local expert token order (`runtime.canonical_moe_order`, `patch_moe_order`) with it ([repeatability](docs/repeatability.md) records its fixture comparison).
- Sampled `server mojibake` counts (`--temperature`, `--top-p`) find broken characters → plan a UTF-8 guard on its own.
- A user request still compiles a sampling kernel after the warmup ladder → add a rung with that request's sampling settings, as the rung at the checkpoint's sampling was added for the kernels a client's first request used to compile ([warmup ladder](docs/operations.md#warmup-ladder)).
- A draft KV cache group whose block is smaller than the KDA block is added (a DFlash-style draft with its own layers, for example) → re-check that prefix-cache hits stay aligned with the KDA checkpoints (the boot log's `kv cache group sizes` against the workers' `Setting attention block size` line; knapcio issue #2) before serving it with prefix caching. Today they agree at [the aligned block](docs/server-configuration.md#kv-capacity-and-ram-requirements), because the pinned vLLM takes the smallest prefix-cacheable group's block as the scheduler's. Do not read `mamba_block_size` from `/metrics`: the engine process never applies align mode's resize, so it reports the requested 256 while the workers write KDA states at every aligned block.
- A KV pool larger than the 3.7M tokens per rank measured on TP=3 → audit the 32-bit row offsets of the kernels this stack runs first ([catalog P28](docs/optimization-catalog.md#performance-initiatives)); six 1,048,576-token requests at once remain out of reach on three hosts.

## Local data and contribution

What stays out of Git, licensing and contributing are in the [repository README](../README.md#local-data-and-contribution). [CHANGELOG.md](CHANGELOG.md) tracks 1.x changes.
