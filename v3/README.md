# NVFP4 BIZ 3.x (TensorFold native)

[日本語](README.ja.md) · [Repository index](../README.md) · [Setup runbook](SETUP.md) · [Changelog](CHANGELOG.md)

The 3.x line serves the same pinned NVIDIA GLM-5.3-Flash NVFP4 checkpoint as 1.x and 2.x on TensorFold's native engine, the Zig and CUDA engine that took the place of TensorFold's Python engine, built from the BIZ release of [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold). It is being prepared for 3.0.0 and has no release yet; until then the [2.x line](../v2/README.md) is the one to run.

## Contents (filled in for 3.0.0)

- Engine: the BIZ release of TensorFold's native engine, built from one pinned commit into the image. What serves users beyond this repository goes to upstream TensorFold as pull requests; the BIZ release carries what is specific to this serving
- Scope: what 2.x serves at TP=2 on two hosts and TP=3 on three (text, tool calls, MTP drafts, the 2.x context windows), and more than one request at a time; image input and the published AXL weights come after 3.0.0
- Setup: the image, the launch scripts and one environment file per rank, as in 2.x ([setup runbook](SETUP.md))
- Validation: the checks 2.x is accepted with, against reference values taken with BF16 KV
- Moving from 2.x: the settings and metrics whose names change, and what 3.0.0 does not have yet
- Licensing: [LICENSE](../LICENSE), [NOTICE](../NOTICE) and [third-party notices](../THIRD_PARTY_NOTICES.md) at the repository root
