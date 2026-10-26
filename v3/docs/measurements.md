# Measurements of earlier releases (3.x)

[日本語](measurements.ja.md) · [3.x overview](../README.md) · [Benchmark method](benchmarks.md) · [Validation](validation.md)

What each 3.x release before the current one measured at its acceptance, newest first. The current release's figures are the README's [measured on the release](../README.md#measured-on-the-release), and a release's part moves here when the next one replaces it. [Benchmark method](benchmarks.md) says how they were taken, and [validation](validation.md) holds the reference values a launch is accepted against.

## 3.6.0

**3.6.0** (2026-10-24, engine `21778b05`, upstream 1.1.3 with pull request #1050, image `glm53-tf3:3.6.0`). The engine moves onto upstream 1.1.3, and 3.x serves XSFP4 alone. Launches of the release image started by its own `serve.sh` and `cluster.sh`, with no `CHECKPOINT` or `CONTEXT` in the rank files and every container on the efficiency cores: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, then one more at each size for tool-eval-bench without the gate (at TP=3 with the prefill again: the first launch's overlapped writing the image out on rank 2's host). Every launch that ran them gave 3.3.0's XSFP4 decode-check hashes and `bench --kinds edit` reply in 190 rounds; the NLL and the reply to the 199,307-token prompt were 3.3.0's, and every passphrase of the 499,254 and 1,035,295-token prompts was found. With `PARALLEL=` empty the engine took one stream at TP=2's 524,288-token window and gave the count hash. Nothing stopped them.

| 3.6.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s): the launch of every check / a second launch | 377 / 334 | 330 / 283 |
| Decode check count / prose / code (tok/s) | 48.83 / 33.74 / 44.86 | 64.28 / 45.24 / 55.33 |
| MTP acceptance length, same tasks | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode` (tok/s, median) | 53.53 | 65.65 |
| `bench --kinds edit` (tok/s, median) | 82.19 | 104.12 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,409.4 | 1,694.3 |
| 199,307-token prompt (s) | 152.8 | 130.4 |
| 499,254 and 1,035,295-token prompts, first token (s) | 434.6 / — | 380.5 / 1,004.1 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.36 against 69.0 | 0.98 against 58.2 |
| Teacher-forced NLL, ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0 through the gate / without it | 95 / 93 | 92 / 91 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone of rank 0's host) | 1,255.9, 75.1 °C | 985.5, 83.3 °C |
| Hottest zone of a launch, by rank (°C) | 86.4 / 88.9 | 92.4 / 89.4 / 87.0 |
| Lowest `MemAvailable`, by rank (GiB) | 12 / 13 | 21 / 22 / 27 |

- **Against 3.3.0.** The same tokens. The speeds are 0.4 to 1.2% lower at TP=2 and 0.7 to 2.2% lower at TP=3, where the long prompts took about 2% longer (the 1,035,295-token prompt 994 s without its waits for heat, against 974 s); TP=3's prefill is that of a launch of its own, as the first launch's 1,669.2 tok/s overlapped writing the image out on rank 2's host. Rank 0's load line read the same model size (96.97 GiB at TP=2's 524,288-token window, 76.36 GiB at TP=3) and, at TP=2, a 4.6 GiB prompt cache (5.5 GiB with `PARALLEL=` empty).
- **Heat.** At TP=3 only the 1,035,295-token prompt waited for heat, 10 s in 5 pauses of 2 s (3.3.0: 42 s in 21); at TP=2 no prompt waited. No zone reached the thermal watch's stop.
- **Tools.** Through the [tool-argument gate](../SETUP.md#6-tool-argument-gate-optional), this repository's relay, the scores and the scenarios left partial or failed are 3.5.3's image's with tool-eval-bench 2.8.0. Without it the engine scored 93 at TP=2 and 91 at TP=3 with the Safety Gate passed; the one more scenario failed at both sizes is TC-43, a `web_search` call with an empty `query`, which through the gate becomes a refusal to call it without one.
- **Known behaviours of XSFP4** are 3.3.0's, below: at TP=3 the stop string's request runs to its limit, and the plain request of the prompt-score and structured-output checks has its own hash.

## 3.5.0

**3.5.0** (2026-10-23, engine `d2d95b11` as in 3.3.0 and 3.4.0, image `glm53-tf3:3.5.0`). TP=2's default window becomes 524,288 tokens. The image differs from 3.4.0's in `serve.sh` alone and its engine binary is 3.4.0's byte for byte (the build reused the layer), so TP=3 was not launched again. At TP=2, the release image started by its own `serve.sh` and `cluster.sh` with no `CHECKPOINT` or `CONTEXT` in the rank files, every container on the efficiency cores: XSFP4's decode check gave 3.3.0's hashes, `bench --kinds edit` its reply in 190 rounds (80.7 to 81.0 tok/s, against 82.8 to 83.0 in 3.4.0's launch; an A/B on the same image afterwards, two launches at each of 245,760 and 524,288 tokens, gave medians of 82.4 to 82.8 tok/s at both windows) and the NLL its values; the 199,307-token prompt gave 3.3.0's reply in 151.7 s, and the 499,254-token prompt found its three passphrases with the first token after 431.5 s. No prompt waited for heat (the hottest zone 87.3 °C on rank 0's host and 89.0 °C on rank 1's), and the lowest `MemAvailable` was 12 GiB on both ranks. Rank 0's load line read a 96.97 GiB model, the first stream's window included, one stream of 6.71 GiB and a 5.5 GiB prompt cache (5.2 GiB in a second launch with `PARALLEL=` empty, where the engine took one stream and gave the count hash). NVIDIA's NVFP4 at the same window read 100.90 GiB and a 1.0 GiB prompt cache, and gave its count hash. Nothing stopped them.

## 3.4.0

**3.4.0** (2026-10-23, engine `d2d95b11` as in 3.3.0, image `glm53-tf3:3.4.0`). XSFP4 becomes the default; the engine and the serving path are 3.3.0's. 3.4.0 re-ran only the checks in this paragraph; for the rest, 3.3.0's XSFP4 figures below are its reference. The image's inputs differ from 3.3.0's only in `serve.sh`'s default checkpoint (XSFP4 at `59c49ac9`, whose files are `dbcb7b65`'s but the model card) and the notices; the engine, built again from the same commit, is another binary byte for byte and gave 3.3.0's answers. The release image, started by its own `serve.sh` and `cluster.sh` with no `CHECKPOINT` in the rank files, every container on the efficiency cores, once at each TP size: the decode check gave 3.3.0's XSFP4 hashes, `bench --kinds edit` its reply and the NLL its values at TP=2 and TP=3, and rank 0's load line read the same model size. Nothing stopped them.

## 3.3.0

**3.3.0** (2026-10-23, engine `d2d95b11`, upstream 1.1.2 with pull requests #1050 and #1179, image `glm53-tf3:3.3.0`). Launches started by the release's own `serve.sh` (the vision tower loaded, its default) and `cluster.sh`, every container on the efficiency cores, `TF_GLM_MM` unset at both TP sizes: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, on each checkpoint. XSFP4's ran the release image and read the revision with plain block scales; the published revision gave the same decode-check hashes, edit reply, NLL and rank 0's model size (the load line) in one more launch at each TP size. NVIDIA's NVFP4's ran the image one engine commit before it (`aa12d8df`, without #1179's patch, which lets an index name a shard in a folder), and in one more launch at each TP size the release image gave NVIDIA's NVFP4 the same decode-check hashes, edit reply and NLL. Nothing stopped them.

| 3.3.0 | NVIDIA TP=2 | NVIDIA TP=3 | XSFP4 TP=2 | XSFP4 TP=3 |
|---|---|---|---|---|
| Start (s): the launch of every check / a second launch | 366 / 301 | 260 / 246 | 377 / 334 | 318 / 258 |
| Decode check count / prose / code (tok/s) | 38.98 / 28.13 / 33.89 | 67.12 / 34.01 / 46.37 | 49.03 / 34.15 / 45.27 | 64.78 / 45.64 / 55.71 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 4.645 / 1.858 / 2.954 | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode` (tok/s, median) | 44.00 | 56.03 | 54.15 | 66.23 |
| `bench --kinds edit` (tok/s, median) | 71.33 | 90.99 | 82.76 | 106.43 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,411.2 | 1,559.7 | 1,415.1 | 1,717.3 |
| 199,307-token prompt (s) | 155.0 | 140.3 | 151.9 | 127.9 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 399.5 / 1,064.9 | — | 373.0 / 1,015.7 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.36 against 68.8 | 1.29 against 62.8 | 0.32 against 68.6 | 0.91 against 56.7 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5285 / 2.9129 / 1.3158 / 0.6262 | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench through the gate | 92 | 95 | 93 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,505, 75.2 °C | 1,233, 85.1 °C | 1,250, 76.5 °C | 981, 85.8 °C |
| Hottest zone of a launch, by rank (°C) | 82.6 / 84.1 | 93.0 / 90.0 / 86.0 | 84.1 / 86.3 | 92.7 / 89.7 / 84.7 |
| Lowest `MemAvailable`, by rank (GiB) | 11 / 13 | 18 / 20 / 26 | 11 / 13 | 21 / 22 / 28 |

- **Against 3.2.0.** At TP=2 NVIDIA's NVFP4's text path is 3.2.0's: 3.1.0's decode-check hashes, edit reply in 190 rounds and NLL, text by text, and the launch with `PARALLEL=` empty the same count hash. Decode, prefill and the edit reply moved by at most 0.7%, and rank 0 keeps a 5.2 GiB prompt cache (4.7). At TP=3 the BF16 linears run on upstream's tiled kernels, which upstream 1.1.2 opened to a TP=3 rank (issue #1067), in place of 3.2.0's glue kernels: the decode-check hashes and the NLL are new ([validation](validation.md#decode-check)); the edit reply is 3.2.0's in 190 rounds, 1.3% faster (90.99 tok/s against 89.83), and the prefill 2.7% faster (1,559.7 against 1,518.2).
- **Images.** Drafted equalled serial on a picture in every launch of every check.
- **XSFP4.** Its decode-check hashes, edit reply and NLL are its own reference values ([validation](validation.md#xsfp4)); a second launch gave the same hashes and edit reply at each TP size. Its speeds belong to its own text (see [checkpoints](../README.md#checkpoints)).
- **Known behaviours of XSFP4.** At TP=3 the stop string's request of [validation](validation.md#stopping-a-reply) (the numbers 1 to 1,000 at temperature 0, stopped at `\n300\n`) falls into a loop before 300 and runs to its 4,000-token limit, as on upstream 1.1.1; it stops at 300 at TP=2, and on NVIDIA's NVFP4 at both sizes. At TP=3 XSFP4's 8-token greedy reply to "The capital of France is" ends "Paris is spelled" where NVIDIA's NVFP4's ends "Paris is pronounced", so the plain request of the prompt-score and structured-output checks has its own hash there ([validation](validation.md#xsfp4)).
- **A number written twice.** Generated token by token, a count like the stop string's sometimes writes one number twice, at a place that moves with the checkpoint, the TP size, the build and where generation starts. NVIDIA's NVFP4 does it too, at TP=2 and TP=3: generated from the start at TP=2 it writes 152 twice, past the 150 numbers the 3.3.0 checks read, and upstream 1.1.1's own binary gives the same tokens. The places belong to the checkpoint, not to this engine: computed in fp32 from the same weights, NVIDIA's NVFP4 itself picks 152 again there, and vLLM on the same checkpoint leaves the count at the same places about as often. Which start leaves where changes with the arithmetic (the TP size, the build, the engine): generation (one token at a time) and prompts (many tokens at once) run on different kernels, and in this MoE model small differences grow each time two experts close in score swap places, so neither side always keeps the count. No single wrong value has been found; the measurements are in [TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214). After 157 NVIDIA's NVFP4, FP4-Local and XSFP4 all write a space and 157 again, and the prefill picks that space too; MTP drafts change nothing.
- **Heat.** With no ceiling, a prompt waits only while the hottest zone is above 92 °C, until 88 °C. Only the 1,035,295-token prompts waited, at TP=3: on NVIDIA's NVFP4, in the afternoon, 38 s in 19 pauses of 2 s, its first token after 1,064.9 s (1,026.9 s without the waits, against 3.2.0's 1,022.9 s), and on XSFP4, at night, 42 s in 21 pauses. No zone reached the thermal watch's stop.

## 3.2.0

**3.2.0** (2026-10-20, engine `1a8f1efd`, upstream 1.1.1, image `glm53-tf3:3.2.0`). Five launches on NVIDIA's NVFP4 with the release image, started by its own `serve.sh` (the vision tower loaded, its default) and this release's `cluster.sh`: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, every container on the efficiency cores, `TF_GLM_MM=0` at TP=3; nothing stopped them.

| 3.2.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 301 / 301 | 246 / 258 |
| Decode check count / prose / code (tok/s) | 38.73 / 27.82 / 33.73 | 51.78 / 33.03 / 44.31 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 3.368 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 43.75 | 55.19 |
| `bench --kinds edit` (tok/s, median) | 70.85 | 89.83 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,408.1 | 1,518.2 |
| 199,307-token prompt (s) | 154.4 | 140.5 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 398.7 / 1,056.9 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.42 against 68.8 | 1.53 against 62.6 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 92 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,548, 75.6 °C | 1,317, 82.5 °C |
| Hottest zone of a launch, by rank (°C) | 81.7 / 84.2 | 92.5 / 89.2 / 86.7 |
| Lowest `MemAvailable`, by rank (GiB) | 13 / 12 | 22 / 24 / 29 |

- **Against 3.1.0.** The text path is 3.1.0's: with the tower loaded both TP sizes gave 3.1.0's decode-check hashes, edit reply in 190 rounds and NLL, text by text, and tool-eval-bench's scores, and the TP=2 launch with `PARALLEL=` empty (two streams) the same count hash. Decode, prefill and the edit reply moved by at most 0.7%. The tower takes 1.27 GiB on rank 0 at both TP sizes, and the lowest `MemAvailable` at TP=2 fell from 15 GiB to 12.
- **Images and videos.** Drafted equalled serial on a picture at both TP sizes in the acceptance; the image and video checks of [validation](validation.md#image-and-video-input) passed in shorter launches the same day, at TP=2 and TP=3.
- **Heat.** The TP=3 launch ran in the afternoon: the 1,035,295-token prompt waited 34 s for heat in 17 pauses of 2 s, 10 while rank 0's hottest zone read 92.1 to 92.5 °C and 7 when it read 91.3 to 91.9 °C and the look-ahead (`TF_HEAT_CEILING`) put the next chunk past 93 °C, and its first token came 34 s later than 3.1.0's, run at night. No other request waited, and no zone reached the thermal watch's stop. The cut prompt at TP=3 let the next request answer in 1.53 s (3.1.0: 0.25 s; 3.0.0: 1.49 s), within the check's bound of half the uncut prompt's first token.

## 3.1.0

**3.1.0** (2026-10-20, engine `1a8f1efd`, upstream 1.1.1, image `glm53-tf3:3.1.0`). Five launches on NVIDIA's NVFP4 with the engine built from `1a8f1efd`, started the way this release's `serve.sh` and `cluster.sh` start it: three at TP=2, one of them with `PARALLEL=` empty, and two at TP=3, every container on the efficiency cores and `serve.sh`'s defaults, `TF_GLM_MM=0` at TP=3; nothing stopped them. Two more at TP=2 on every core recorded the heat. The release image, started by its own `serve.sh` and this release's `cluster.sh`, gave the same decode-check hashes and edit reply in one launch at each TP size.

| 3.1.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 301 / 301 | 540 / 247 |
| Decode check count / prose / code (tok/s) | 38.85 / 27.72 / 33.84 | 51.59 / 32.43 / 44.14 |
| MTP acceptance length, same tasks | 3.066 / 1.882 / 2.621 | 3.368 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 43.80 | 55.05 |
| `bench --kinds edit` (tok/s, median) | 71.26 | 89.53 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,415.7 | 1,507.9 |
| 199,307-token prompt (s) | 153.4 | 140.4 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 398.1 / 1,022.7 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.39 against 68.4 | 0.25 against 62.8 |
| Teacher-forced NLL, ja / en / code / math | 2.5412 / 2.9293 / 1.3145 / 0.6261 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 92 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,536, 74.9 °C | 1,315, 79.8 °C |
| Hottest zone of a launch, by rank (°C) | 81.8 / 83.6 | 90.8 / 89.3 / 85.5 |
| Lowest `MemAvailable`, by rank (GiB) | 15 / 15 | 23 / 11 / 26 |

- **Repeatable.** The two launches at each TP size gave the same decode-check hashes and edit reply, and the TP=2 launch with `PARALLEL=` empty, which took two streams, the same count hash. TP=3 gave 3.0.0's decode-check hashes, edit reply and NLL on the glue kernels; TP=2's are new on the tiled kernels ([validation](validation.md)).
- **Against 3.0.0.** 3.1.0's TP=2 ran on a second pair of the same systems, so its comparison with 3.0.0's TP=2 mixes the engine with the hosts; TP=3 ran on the same three. The same reply of `bench --kinds edit` in 190 rounds instead of 363, so 57% faster at TP=2 and 48% at TP=3; decode 4.3% faster at TP=2 and 1.0% slower at TP=3; prefill 1.2% slower at TP=2 and 3.6% faster at TP=3. At TP=3 the start's load line holds less (model 78.03 GiB and one stream 12.88 GiB, against 84.01 and 18.86), yet the lowest `MemAvailable` was lower; rank 1's 11 GiB was one 2-s reading during tool-eval-bench, with 24 GiB before and after it.
- **Heat.** No request waited for heat, no zone read 92 °C on the efficiency cores, and the GPUs did not slow for heat, the 1M-token prompt included. On every core at TP=2 the forty replies finished in 1,535 s with rank 0's host at 93.0 °C (74.9 °C on the efficiency cores), and two requests at once (`PARALLEL=2`, a 131,072-token window) at 88.5 °C; neither stopped.

## 3.0.0

**3.0.0** (2026-10-18, engine `3d3d61d5`, image `glm53-tf3:3.0.0`). Five launches in one window on NVIDIA's NVFP4, two at each TP size and one at TP=2 with `PARALLEL=` empty, every container on the efficiency cores and `serve.sh`'s defaults; nothing stopped them. The window ran the image `glm53-tf3:3x-bc82bc4`; the release image adds the engine's notices to it with the same binaries (`/usr/share/doc/tf3/ENGINE`), and gave the same count hash and edit reply in a TP=2 launch.

| 3.0.0 | TP=2 | TP=3 |
|---|---|---|
| Start (s, two launches) | 281 / 268 | 235 / 235 |
| Decode check count / prose / code (tok/s) | 38.68 / 26.25 / 32.91 | 47.87 / 33.17 / 44.59 |
| MTP acceptance length, same tasks | 3.34 / 1.879 / 2.747 | 3.048 / 1.787 / 2.839 |
| `bench --kinds decode` (tok/s, median) | 42.01 | 55.61 |
| `bench --kinds edit` (tok/s, median) | 45.40 | 60.69 |
| Prefill of 38,960 tokens (tok/s, median of three) | 1,433.5 | 1,454.9 |
| 199,307-token prompt (s) | 152.7 | 150.2 |
| 499,254 and 1,035,295-token prompts, first token (s) | — | 425.4 / 1,082.9 |
| A prompt of about 93,000 tokens cut 3 s in: the next request answered after (s), against the uncut prompt's first token | 0.32 against 67.8 | 1.49 against 66.6 |
| Teacher-forced NLL, ja / en / code / math | 2.5293 / 2.9109 / 1.3138 / 0.6272 | 2.5246 / 2.9206 / 1.3147 / 0.6241 |
| tool-eval-bench through the gate | 93 | 93 |
| Forty replies of up to 1,024 tokens after 6,000-token prompts (s, hottest zone) | 1,599, 82.6 °C | 1,245, 79.7 °C |
| Hottest zone of a launch, by rank (°C) | 89.0 / 83.0 | 89.0 / 88.8 / 83.3 |
| Lowest `MemAvailable`, by rank (GiB) | 16 / 16 | 30 / 30 / 36 |

- **Repeatable.** The two launches at each TP size gave the same decode-check hashes, and the launch with `PARALLEL=` empty the same count hash (the engine chose one stream at TP=2); drafted equalled serial, and `bench --kinds edit` gave the same reply at both TP sizes ([validation](validation.md)).
- **Heat.** No request waited for heat, no zone read 92 °C and the GPUs did not slow for heat, the 1M-token prompt included. With the containers on every core the same image's earlier window stopped when rank 0's CPU zone reached 96.1 °C during tool-eval-bench, and the forty replies stopped at the seventh at 94.7 °C. Against every core at TP=2, decode was 1.0% slower, prefill 3.2% and the 200K-token prompt 2.7% ([why the efficiency cores](../README.md#serving-defaults)).
- **Against 2.x (information).** The tokens are the native engine's own; NLL differs from 2.x's reference values by at most 0.021 per domain. 2.9.2's `bench --kinds decode` gave 42.96 and 57.25 tok/s at TP=2 and TP=3.
