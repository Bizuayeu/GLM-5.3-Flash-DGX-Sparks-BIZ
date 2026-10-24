# GLM-5.3-Flash-DGX-Sparks-BIZ

![GLM-5.3-Flash BIZ: local AI on DGX Spark-compatible GB10 systems, two or three nodes](assets/banner.png)

[日本語](README.ja.md)

**GLM-5.3-Flash BIZ** serves GLM-5.3-Flash on DGX Spark or compatible GB10 systems: in the 1.x and 2.x lines NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, and in the 3.x line the XSFP4 checkpoint, a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local whose experts this repository's maintainer requantized. This repository carries one directory per serving line:

| Line | Engine | Directory | Changelog |
|---|---|---|---|
| 1.x | vLLM | [v1/](v1/README.md) | [v1/CHANGELOG.md](v1/CHANGELOG.md) |
| 2.x | TensorFold | [v2/](v2/README.md): TP=2 and TP=3, FP8 KV, text, tool calls and images ([setup](v2/SETUP.md)) | [v2/CHANGELOG.md](v2/CHANGELOG.md) |
| 3.x | TensorFold, native engine | [v3/](v3/README.md): XSFP4, TP=2 and TP=3, BF16 KV, text, images and videos, tool calls and structured output ([setup](v3/SETUP.md)) | [v3/CHANGELOG.md](v3/CHANGELOG.md) |

Each line has its own README, version and changelog; a release tag `v1.*`, `v2.*` or `v3.*` publishes the section of that line's changelog. Each line holds what is specific to its engine: 1.x's commands run from `v1/`; 2.x's and 3.x's tools from `v2/` and `v3/`, and their image builds and scripts from the checkout root ([2.x setup](v2/SETUP.md), [3.x setup](v3/SETUP.md)). The checkout root holds what every line shares: the host and fabric pages and the repository's document map in [`docs/`](docs/README.md), the host tools in [`host/`](host/README.md), licensing, and in `tools/` the repository's publication audit and release notes. `state/` and `records/` are untracked and stay at the checkout root.

## On a Mac

The lines here serve GLM-5.3-Flash on NVIDIA GB10 systems; their checkpoints, images and scripts do not run on Apple silicon. A Mac takes other weights (MLX) and TensorFold's Metal engine, and this repository has no Mac to build or check them on. TensorFold itself serves GLM-5.3-Flash on Macs from checkpoints of its own (MIT), none of them run here:

- **Two Macs.** [TensorFold/GLM-5.3-Flash-MLX-4bit-MTP](https://huggingface.co/TensorFold/GLM-5.3-Flash-MLX-4bit-MTP), the setup its [model table](https://github.com/ashhart/TensorFold#pick-a-model) qualifies (on 2026-10-24, two M5 Ultras), with the commands in its [paired Metal runbook](https://github.com/ashhart/TensorFold/blob/main/RUNBOOK.md#flash-next-and-paired-metal-serving). By TensorFold's [changelog](https://github.com/ashhart/TensorFold/blob/main/CHANGELOG.md#1010), no uniform checkpoint of the model fits one 256 GB Mac within its load limit.
- **One Mac.** Mixed-width checkpoints such as [TensorFold/GLM-5.3-Flash-MLX-oQ2-MTP](https://huggingface.co/TensorFold/GLM-5.3-Flash-MLX-oQ2-MTP) (about 110 GB), which TensorFold serves on one Mac from 1.0.10, on contributors' runs on an M3 Ultra and an M5 Ultra ([changelog](https://github.com/ashhart/TensorFold/blob/main/CHANGELOG.md#1010)); the model table does not list them. Both checkpoints' cards also give runs in oMLX on one Mac Studio with an M3 Ultra.

## BIZ

**BIZ** is the maintainer's mark (Bizuayeu) and states the intent: a business-use setup with commercially usable licensing, pinned assets, recorded checks and reversible operation.

BIZ is an intent, not a promise. It is not a product tier, a support commitment, a warranty or a certification. Business-use readiness is an acceptance outcome for the scope each line declares, not implied by the suffix. Each line's README states its own limits in its disclaimer.

## Licensing at a glance

Each artifact keeps its own terms; obligations and the rationale are in the [licensing guide](docs/licensing.md), provenance in the [third-party notices](THIRD_PARTY_NOTICES.md).

| Artifact | License | Where it comes from |
|---|---|---|
| Original setup code and documents | **Apache-2.0** | This repository |
| GLM-5.3-Flash NVFP4 weights (1.x and 2.x) | **MIT** (stated in the pinned NVIDIA model card; upstream Z.ai model is MIT) | Downloaded by the operator; not bundled |
| Attention and `lm_head` W4A16 repack (the published option of 1.x and 2.x) | **MIT**, with NVIDIA's model card beside it | Optional [Hugging Face weights](docs/licensing.md#weight-notices); outside Git |
| XSFP4 checkpoint (3.x) | **NVIDIA Open Model Agreement** (a derivative of NVIDIA's GLM-5.3-Flash-FP4-Local; commercially usable); upstream Z.ai model is MIT | [Hugging Face weights](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4) with the agreement and its notice; downloaded by the operator, outside Git |
| LPA cut32 auxiliary projector (1.x) | **Apache-2.0**; training-data notices retained separately | Optional [Release asset](v1/docs/lpa.md#download-the-trained-projector); outside Git |
| TensorFold, the BIZ release (2.x) | **Apache-2.0** (code from before 0.6.0 keeps its MIT notice) | Cloned into the image from [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `TENSORFOLD_REF`, with the engine's own notices under `/opt/tensorfold`; not vendored here |
| TensorFold's native engine, the BIZ release (3.x) | **Apache-2.0** | Compiled into the image from [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) at `ENGINE_REF`, with the engine's own notices under `/usr/share/doc/tf3/engine/`, and under `/usr/share/doc/tf3/LICENSES/` those of xgrammar (structured output, Apache-2.0), libjpeg-turbo and libwebp (images, BSD-style) and FFmpeg's decoders (videos, LGPL-2.1-or-later: [what that asks of a redistributor](docs/licensing.md#images-and-harnesses)); not vendored here |
| Built container image | Per bundled component (CUDA, Torch, NCCL and others; 2.x's NVIDIA PyTorch container and 3.x's NVIDIA CUDA image under NVIDIA's terms); not treated as one blanket license | Built by the operator from the pinned official base image |
| ZCode / Claude Code harnesses (1.x) | Each product's own terms | Installed separately; nothing is relicensed here |

Distributing this repository as source, pinned references and build steps requires Apache-2.0 compliance plus retention of the copyright and license notices of the adapted third-party code (MIT and Apache). Redistributing weights or built images adds those artifacts' conditions. The serving paths have no non-commercial or no-derivatives terms in them: 1.x does not require EXL3/TR3 weights, DFlash2 weights or Mia's current AGPL distribution, 2.x does not load the DFlash2 draft weights (CC BY-NC-ND 4.0; `--drafter none`) or use EXL3 or other requantized weights, and 3.x drafts with the checkpoint's own MTP head and loads no other weights; its default XSFP4 checkpoint is under an agreement that permits commercial use and derivatives. See [commercial use, modification and redistribution](docs/licensing.md) for permissions and obligations by artifact.

## Local data and contribution

`state/`, `records/`, credentials, site-specific configuration (2.x's and 3.x's rank and cluster files with your site's values included) and weights are excluded from Git and the Docker build context. Publish reviewed summaries, not raw local logs.

Licensing: [LICENSE](LICENSE) (Apache-2.0), [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md), which describes the CPU checks and the publication audit.
