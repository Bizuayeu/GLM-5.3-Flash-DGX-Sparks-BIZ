# Image input (vision)

[日本語](vision.ja.md) · [Server configuration](server-configuration.md) · [Document map](README.md)

Every template accepts **text, tool calls and images** at 262,144 input-plus-output tokens (256K). **Video input is disabled and rejected.** This page records how the image profile was reached at 204,800 tokens on 2026-09-15 and extended to 256K on 2026-09-17, what was measured on the reference hosts (MSI EdgeXpert MS-C931, about 121 GiB usable memory each), and what remains unmeasured. Routine-use acceptance and its scope are owned by [SETUP step 6](../SETUP.md#6-qualify-the-full-model); this page holds the image-specific evidence.

## Settings

[Server configuration](server-configuration.md#distributed-defaults) owns the keys; this is the image-related subset of the template.

| Key | Value | Effect |
|---|---|---|
| `runtime.vision` | `true` | Removes `--language-model-only` on every rank, so the vision tower loads; adds `--limit-mm-per-prompt '{"video": 0}'` |
| `cache.mm_processor_cache_gb` | 0.1 | `--mm-processor-cache-gb 0.1` instead of vLLM's 4 GiB |

The context length (the same as the text-only alternative's), the KV bytes per rank and the reserve are the template's ([distributed defaults](server-configuration.md#distributed-defaults); the [published option](server-configuration.md#the-published-option-against-the-defaults) sets its own KV). The KV pool's boot-line figure is the pool's maximum concurrency in token units, not a cached-conversation capacity, and the reserve's guard arithmetic is in the same place ([KV capacity and RAM requirements](server-configuration.md#kv-capacity-and-ram-requirements)); the defaults' figure at 256K is in [startup at 256K](benchmarks.md#startup-at-256k).

A client must declare image input and must not declare video. For ZCode, set the model's `limit.context` to 262144 and `modalities.input` to `["text", "image"]` ([ZCode model limits](harnesses.md#zcode-permission-modes-model-limits-and-the-existing-file-guard)). The text-only alternative is described in [server configuration](server-configuration.md#distributed-defaults).

## How the settings were chosen

1. **The vision tower loads unquantized.** The checkpoint ships 347 BF16 vision tensors (1.05 GiB). Both quantization exclusion lists name `model.visual*`, and the pinned vLLM builds the tower without a quantization config, so NVFP4 is not misapplied. The MTP metadata view keeps the tower unchanged. At TP=2 the tower is split across the two ranks; at TP=3 it runs data-parallel, because its 16 heads do not divide by three ([server configuration](server-configuration.md#three-nodes)).
2. **Video is disabled.** At startup vLLM profiles memory by encoding the largest multimodal item once. This checkpoint's video budget is capped at 30,000 tokens (120,000 patches), against at most 8,000 tokens for one image, so a video would set the startup peak. With the video limit at zero, profiling uses one image and a video request returns HTTP 400. The number of images per prompt keeps the vLLM default, because chat harnesses resend earlier images every turn.
3. **The image preprocessing cache is capped at 0.1 GiB.** vLLM keeps one copy in the API server and one in the engine core. Both run only on rank 0, so the 4 GiB default could take up to 8 GiB of the head's memory. An image larger than the cap is processed uncached, with a warning.
4. **The head carries more than the other ranks, and that cannot be rebalanced.** Rank 0 alone runs the API server and the engine core. Measured proportional set size (Pss) at idle was 2,165 MiB for the API server and 999 MiB for the engine core, against 1,056 MiB for rank 1's headless process; nearly all of it is private anonymous memory. Tensor parallelism has no setting that shifts GPU memory between ranks, vLLM aligns every rank's KV blocks to the smallest rank, the API server and engine core cannot share one process under `vllm serve`, and moving the head to another host only moves the load.
5. **JIT caches persist** in the mounted runtime cache (`TRITON_CACHE_DIR`, `TILELANG_CACHE_DIR`, `TORCHINDUCTOR_CACHE_DIR`; [storage paths](operations.md#artifact-storage-and-paths)). Written inside the container layer, they were rebuilt at every start (about 2,000 entries), and compiling while serving once took the head from 4.11 to 2.88 GiB available in about 26 seconds and triggered a supervised stop of rank 0. With the caches kept, the head's lowest available memory during startup rose from 3.34 to 4.18 GiB (one start each).
6. **The template's reserve, KV and context length** since 1.5.0 ([values](server-configuration.md#distributed-defaults)). The first image profile (2026-09-15) had shrunk context to 204,800 and KV and reserve by 0.5 GiB each for the tower and preprocessing. Eight NCCL channels (1.3.1, [numbers](../../docs/nccl-validation.md#channel-count)) and tracing the peer's supervised stop of 2026-09-16 to a host daemon ([host preparation](../../docs/hosts.md#host-daemons)) then raised the head's floor during 200K requests ([on 1.4.0](benchmarks.md#200k-real-input-on-140)) and during startup at 256K ([startup at 256K](benchmarks.md#startup-at-256k)), which met a proceed condition of the reserve plus 1.6 GiB. A 300K profile with 4 GiB KV left 0.3 GiB of margin by the same estimate and was set aside. The reserve is a margin for one transient, not a floor: no kernel or container OOM kill was recorded, the risk below it is a GPU allocation failing inside a worker, and the supervisor samples every 2 seconds and needs about 9 seconds to stop a container, so a slide of 0.15 GiB/s (measured during a runtime compile burst) can carry the host about 1.6 GiB below the reserve.

## Measurements

### Function and regression (final profile)

| Check | HTTP | Seconds | Result |
|---|---|---:|---|
| Synthetic image (number and background colour) | 200 | 3.74 | Correct; 323 prompt tokens, 288 of them image |
| Same image again | 200 | 2.28 | Correct |
| Same question without the image | 200 | 3.43 | Says no image is present; does not guess the number |
| Text of the same length | 200 | 1.71 | Correct |
| Short arithmetic | 200 | 2.62 | Correct |
| Tool call, then tool result | 200 / 200 | 2.07 / 3.21 | Tool call emitted; answer uses the tool result |
| Video | 400 | 0.58 | `At most 0 video(s) may be provided in one prompt` |

Times are single runs measured from a remote client and include SSH overhead. An earlier start of the same profile with the 4 GiB image cache default also passed the image and tool checks, and the [prefix cache check](harnesses.md#zcode-permission-modes-model-limits-and-the-existing-file-guard) restored 13,824 tokens.

### 200K text request

One request built to 199,652 prompt tokens, with a passphrase in the middle, returned the passphrase with `finish_reason: stop` (one run). It ran on the image profile before the reserve and JIT cache changes, and no supervised stop occurred. Its whole-request time, including prefill, and the head's lowest available memory during it are in [200K real input on 1.3.1](benchmarks.md#200k-real-input-on-131), which compares them with 1.3.1. The ZCode stream idle timeout of 700,000 ms covers this time.

### Memory (final profile)

| | Idle after startup | After one image | During 200K `/tokenize` | After the regression checks |
|---|---:|---:|---:|---:|
| Rank 0 API server Pss (MiB) | 2,165 | 2,201 | 2,220 | 2,329 |
| Rank 0 engine core Pss (MiB) | 999 | 1,005 | 1,005 | 1,007 |
| Rank 0 worker Pss (MiB) | 6,292 | 6,297 | — | 6,300 |
| Rank 1 headless process Pss (MiB) | 1,056 | 1,056 | — | 1,056 |
| Rank 0 available (GiB) | 4.19 | 4.16 | 4.06 | 4.01 |
| Rank 1 available (GiB) | 5.56 | 5.51 | — | 5.53 |

- The image profile kept about 4.0–4.2 GiB available on the head while serving with NCCL's 64 channels.
- Lowest available during startup: 4.18 GiB (rank 0) and 5.36 GiB (rank 1). Over the first half hour of serving, including diagnostic sampling, rank 0's lowest was 3.84 GiB, 1.34 GiB above the reserve.
- One 200K `/tokenize` call took 0.22–0.31 seconds and caused no visible peak (one sample).
- The first image request compiled six Triton kernels while serving; the caches kept them. The resulting dip on rank 0 was below 0.1 GiB.
- The API server's anonymous memory grows with use (+164 MiB over these checks). Of its 2.3 GiB, about 1.26 GiB exceeds rank 1's headless process: the heap (+126 MiB), glibc malloc arenas (+255 MiB), other mappings (+138 MiB) and one anonymous mapping of about 624 MiB whose owner was not identified.

### 256K profile (1.5.0, 2026-09-17)

After the switch the same checks passed on the 256K profile: the synthetic image correct, the same question without the image not guessed, text of the same length, the same image again, short arithmetic, a tool call answered from its result, and video rejected with HTTP 400. Both ranks ran with `--max-model-len 262144` and `--kv-cache-memory-bytes 3221225472`, and the warmup ladder's image rung took 1.24 s. The 256K long-context requests and the memory during them are in [measurements on 1.5.0](benchmarks.md#measurements-on-150); the head's lowest available memory there was 5.82 GiB.

### 1.19.0 (2026-09-27 to 28)

Both profiles were checked on the 1.19.0 image (the published option on 2026-09-27, the defaults on 2026-09-28 inside the window with the GPU clock cap, [benchmarks](benchmarks.md#both-profiles-in-one-window-with-a-gpu-clock-cap-2026-09-28)).

| Check | Published option | Distribution defaults |
|---|---|---|
| The seven regression checks (the table above) | All seven passed | All seven passed |
| Large images (448 / 1,232 / 2,464 px square, reading twelve items present only in the image) | 12/12, 12/12, 12/12 (prompts of 288, 1,968 and 7,776 tokens; 2.8, 4.0 and 12.4 s) | 12/12, 12/12, 12/12 (the same token counts; 2.4, 4.1 and 10.6 s) |
| Several images (two, four and eight 448 px images, one number each, read in order) | All in order | All in order |
| MTP acceptance on a 512-token description (with an image / text of the same length) | 0.681 / 0.615 | 0.718 / 0.593 |
| An image request and a prose request together | Image answered correctly | Not applicable (one sequence) |
| Lowest head free memory | 7.07 GiB | 5.53 GiB |

- One run each; times include the SSH round trip. Acceptance on image descriptions was expected to be lower than on text and came out higher on both profiles (one run each, so the spread is unknown).

### 1.29.0 (2026-10-04)

The 1.29.0 reference image carries [vLLM #59565](https://github.com/vllm-project/vllm/pull/59565) on the pinned source (`patch_image_budget`). On the reference pair at TP=2, both ranks of both profiles logged `Encoder cache will be initialized with a budget of 8000 tokens` (`budget of 7921 tokens` before). Each image below was sent with the one-line request of [#59539](https://github.com/vllm-project/vllm/issues/59539) and with a request to read the size written on it.

| Image | Prompt tokens of the one-line request | Before 1.29.0 | Published option | Distribution defaults |
|---|---:|---|---|---|
| 2560×1440 | 4,802 | answered | 200, read correctly | 200, read correctly |
| 3000×3000 (resized to 2492×2492) | 7,939 | answered | 200, read correctly | 200, read correctly |
| 5000×2000 | 7,858 | answered | 200, read correctly | 200, read correctly |
| 4032×3024 | 7,949 | refused | 200, read correctly | 200, read correctly |
| 3840×2160 | 7,991 | refused | 200, read correctly | 200, read correctly |
| 3508×2480 | 7,968 | refused | 200, read correctly | 200, read correctly |
| 2600×2400 | 8,016 | refused | 200, read correctly | 200, read correctly |
| 2240×2800 and 2800×2240 (8,000 image tokens) | 8,018 | refused | 200, read correctly | 200, read correctly |

The seven regression checks passed on both profiles, and the decode-check completions were the earlier image's on both. One run each.

### 1.29.9 (2026-10-06)

The pinned processor bounds an image by its token budget only, and the pinned vision tower's rope table has 8,192 rows, so a slim image within the 8,000-token ceiling can have a grid side past the table ([vLLM #59126](https://github.com/vllm-project/vllm/pull/59126)). On the reference pair (TP=2, distributed defaults), with one request "Reply with OK." per image:

| Image | Patches across | 1.29.8 | 1.29.9 |
| --- | ---: | --- | --- |
| 114000×28 | 8,143 | 200, 4,090 prompt tokens | 200, 4,090 prompt tokens |
| 200000×20 | 14,286 | HTTP 500 after 63 s; rank 0 logged `vectorized gather kernel index out of bounds` and the server stopped answering `/health` | 200, 7,161 prompt tokens (7,143 image tokens), `/health` 200 |

1.29.9 carries the fix on the pinned source (`patch_vision_rope`): the table has `max_position_embeddings` rows (1,048,576, about 64 MiB per GPU in bf16). The nine images of the 1.29.0 check above gave the same HTTP status, prompt tokens and replies on 1.29.8 and 1.29.9, and the decode check gave 1.29.8's token ids and completions on both profiles. One run each.

### Three hosts at TP=3

On three hosts at TP=3, at 262,144 tokens, a 672×336 single-colour image check passed on the distributed defaults on 2026-09-29 and on the published option on 2026-10-01: blue and orange named correctly, and without an image the model said that none was attached ([measurements on 1.24.0](benchmarks.md#measurements-on-1240) has the launches). The large-image, several-image and two-sequence checks above were not run at TP=3.

## Limits and open items

- The checks use synthetic images. Images of up to 8,000 tokens, the model's own limit, and up to eight images were read correctly (1.29.0 and 1.19.0 above); image understanding in general is unmeasured. Before 1.29.0 the server's encoder cache was sized from a square image (7,921 = 89×89 tokens) instead of the processor's exact ceiling (8,000 = 80 × 100 tokens for the default budget), so images whose processed size is 7,922 to 8,000 tokens, among them a 4:3 phone photo, a 4K frame and an A4 scan at 300 dpi, were refused with HTTP 400 ([vLLM #59539](https://github.com/vllm-project/vllm/issues/59539)); 1.29.0 carries the fix, [vLLM #59565](https://github.com/vllm-project/vllm/pull/59565), on the pinned source. A larger image is resized by the processor to fit the limit. Before 1.29.9 a slim image within the limit, one whose grid is more than 8,192 patches on a side (200000×20 px, for one), took the server down ([1.29.9](#1299-2026-10-06)); 1.29.9 carries [vLLM #59126](https://github.com/vllm-project/vllm/pull/59126) on the pinned source. The aspect ratio itself is still not capped.
- Images at TP=3 beyond 262,144 tokens are not measured.
- The MTP draft is text-only; its acceptance rate on image requests was measured once per profile on 1.19.0 (above). LPA with images is not validated (LPA ships disabled).
- In one ZCode terminal session (2026-09-15, one run), the model downloaded a screenshot with a shell command, read it with the file-read tool and correctly described text that appeared only in the image. Attaching an image directly to a ZCode prompt has not been checked (Claude Code is out of scope, [harnesses](harnesses.md#acceptance-matrix-and-status)); the measurements above used the API directly.
- A request shape seen for the first time can still compile kernels while serving. The [warmup ladder](operations.md#warmup-ladder) sends the shapes that were observed compiling and records, on every start, the kernels loaded or compiled while it runs.
- The API server's unidentified 624 MiB mapping and its slow growth over long sessions are not characterized. `MALLOC_ARENA_MAX` could affect at most the 255 MiB in arenas.
- Images with two sequences: image-plus-prose pairs on the published option only (one pair each on 2026-09-23, 27 and 28) ([concurrency scope](validation.md#concurrency-scope)). Long-term reliability is not characterized.
