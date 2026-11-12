# Configuration (3.x)

[日本語](configuration.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Operations](operations.md)

Every setting a 3.x deployment reads: where it is set, its default, what it does and which ranks read it. The values a release serves, and why, are the README's [serving defaults](../README.md#serving-defaults); this page is the inventory behind them. The engine's settings are those of the commit the image pins ([`config/engine.lock.json`](../config/engine.lock.json)), read from its source; `tensorfold-native serve --help` in the container lists its flags.

3.x's acceptance ran every setting here at its default; where a row names another value, a release's acceptance or a recorded trial ran it too ([measured on the release](../README.md#measured-on-the-release), [earlier releases](measurements.md), [limits](../README.md#limits)). Any other value is outside what the acceptance covers, and so is what a row says it reads from the source alone.

## Where settings live

| Where | Read by | Takes effect |
|---|---|---|
| [`config/tp2.env`, `config/tp3.env`, `config/tp4.env`](../config/) | `serve.sh`, before the rank file, every variable exported | with a new image |
| Rank file, `/work/rank.env` on each host ([examples](../examples/)) | `serve.sh`, which sources it with every variable exported, so any variable in it reaches the engine and its value wins over the release's file | at the rank's next start |
| `serve.sh` arguments after `TP RANK RANK_ENV`; through `cluster.sh`, the arguments after the label | `tensorfold-native serve`, after `serve.sh`'s own | at the next start, on every rank |
| Cluster file, `state/cluster.env` on the control machine | `cluster.sh` | at its next command |
| `create_container.sh`'s environment | `create_container.sh` and `cpuset.sh` | when the container is created (`docker update` changes its cores later) |
| The tools' options and environment | `python -m glm53_tf <command>`, from `v3/` | at the run |
| [`config/`](../config/) | the image build and the tools | at the next build or run |

`cluster.sh` runs the image's `serve.sh` (`/opt/glm53-tf3/serve.sh`), not the checkout's: a change to [`scripts/serve.sh`](../scripts/serve.sh) or to `config/tp2.env`, `config/tp3.env` and `config/tp4.env`, which the image holds beside it, reaches the ranks with a new image only.

## Rank file

| Setting | Default | Meaning | Ranks |
|---|---|---|---|
| `MASTER` | none, required | rank 0's address on the link between the hosts; `serve.sh` gives the engine `NCCL_COMM_ID=MASTER:NCCL_PORT` | the same on every rank |
| `NCCL_PORT` | `29583` | rank 0's port in `NCCL_COMM_ID`, where rank 0's NCCL bootstrap listens; the ranks' liveness lines take the port after it | the same |
| `CONTEXT` | `1048576`; an empty value takes the default | the window (`--context`) | the same; compared at start |
| `PARALLEL` | `4` at TP=2, `8` at TP=3 and TP=4 | requests decoded at once (`--parallel`); an empty value passes none, and the engine takes up to 8 streams as the memory free at start allows (accepted at both TP sizes); a number that does not fit is refused at start | rank 0, which sizes every rank's streams by the smallest room among them |
| `TF_KV_SHARE` | `16` at TP=2, `32` at TP=3 and TP=4 | the prompt cache over the KV pool's pages: kept prompts stay as pages, with at most this many states past them, each in a slot of the startup plan. Rank 0's load line names the slots; when fewer fit, it says how many and whether a `--prompt-cache-gib` would hold them all. Below four states a stream the engine warns that live streams evict each other's. A value over 64 stops the start. An empty value or `0` goes back to the prompt cache in copies (`--prompt-cache-gib`). Up to 3.11.x it was `TF_GLM_KV_SHARE`, which upstream 1.2.4's engine refuses at start (#2211) | the same |
| `TENSORFOLD_PREFILL_SHARE` | `0.7` | a long prompt's share of the time while other streams decode ([rank 0's server](#rank-0s-server)); an empty value leaves the engine's `1` | rank 0 |
| `TF_GLM_CHUNK_SOLO` | empty | `4096` lets a prompt pass take 4,096 rows while no other stream decodes, so a request that arrives in such a pass waits for its end, and every rank holds wider prompt buffers. An empty value or `2048` keeps passes of 2,048 rows. Not beside `--drafter` | the same; compared at start |
| `MTP_CONFIDENCE` | empty at TP=2, `0.5` at TP=3 and TP=4 | where a chain of MTP drafts stops (`--mtp-confidence`, from 0 to 1): a draft's chance under this ends the chain. An empty value passes none | the same |
| `TF_GLM_ROCE_MULTI` | `0` at TP=2 and TP=4, `1` at TP=3 | the wire: at three ranks the main stream's small all-gathers go over the engine's multirank RoCE, beside NCCL, and `serve.sh` gives it the next row. A ring of four would take upstream's experimental relay for it (`TF_TP_ROCE_RELAY=1`, #2352), outside the acceptance. `0` keeps them on NCCL; another value, an empty one included, stops `serve.sh` at start | the same; compared at start |
| `TENSORFOLD_MEMORY_RESERVE_GIB` | `9` at TP=2, `16` at TP=3, `14` at TP=4 | the memory the engine leaves to the system. At TP=2 it gives Jammed XSFP4, the default, a larger pool, 2,961 to 2,981 pages against 2,451 at the engine's own 12.3 GiB ([below](#read-on-each-rank-not-compared)), either holding the 1,048,576-token window; on XSFP4 it makes room for that window, which the engine's own reserve does not leave. At TP=3 it holds XSFP4's KV pool at two windows of pages and the prompt cache's rest: the room is close to what a third window takes, and the startup plan puts every window the room holds before the kept states' slots. Jammed XSFP4's smaller model took a third at 14 GiB in 3.10.0's acceptance ([checkpoints](../README.md#checkpoints)). At TP=4 it is what the reference ring of four was served with, not tuned there. An empty value takes the engine's own | the same |
| `TF_TP_MASTER`, `TF_TP_PORT`, `TF_TP_PLAN_TIMEOUT`, `TF_TP_KERNEL_IMAGE`, `TF_TP_ROCE_FALLBACK` | `MASTER`, `29640` (and `29647`, seven above), `900` (seconds), the image's `/opt/glm53-tf3/tp_mailbox.fatbin`, `error` | what `serve.sh` gives the wire while `TF_GLM_ROCE_MULTI` is on: rank 0's address, the port the ranks meet at, how long they wait for each other, the mailbox kernels, and what a failed setup or probe does: `error` stops the start, and `nccl` starts without the wire | the same |
| `VISION` | `1` | image and video input (`--vision`), read by the checkpoint's vision tower on rank 0; `0` serves text alone, and another value, an empty one included, stops `serve.sh` at start | the same; compared at start |
| `MODEL_NAME`, `HOST`, `PORT` | `glm-tf`, `127.0.0.1`, `8095` | rank 0's model id and listener (`--name`, `--host`, `--port`) | rank 0 |
| `REASONING_EFFORT` | `high` | the effort for a request that names none (`--reasoning-effort`): `low`, `medium`, `high` or `xhigh`, and another value, `max` among them, stops every rank at start; an empty value passes none and leaves it to the chat template. A request itself may name `none`, `minimal`, `low`, `medium`, `high`, `xhigh` or `max` | rank 0 |
| `API_KEY_FILE` | none | rank 0's key file for serving beyond loopback (`--api-key-file`, [API keys](#api-keys)) | rank 0 |
| `CHECKPOINT` | from 3.12.0 the release file's: Jammed XSFP4's snapshot at its lock's revision under `/hub` at TP=2, XSFP4's at TP=3 and TP=4; an empty value takes the default | the checkpoint folder inside the container; 3.x accepts XSFP4 and Jammed XSFP4, the other one than the TP size's by this line in every rank file with the revision in its lock ([checkpoints](../README.md#checkpoints)). A folder the host lacks stops `serve.sh` at start, naming `download --tp` | the same; compared at start, by its digest |
| `TF_HEAT_HIGH`, `TF_HEAT_LOW` | `92`, `88` (°C) | the prefill heat wait's band ([compared across the ranks](#compared-across-the-ranks)); `serve.sh` passes an empty one on as it is, and the engine refuses one without the other, so empty both for no wait | the same; compared at start |
| any other variable | none | exported to the engine: the [engine environment](#engine-environment) (`TF_GLM_*`, `TF_ROCE*` and the rest) and the [NCCL settings](#nccl) | as each says |

The example files hold the reference hosts' values, with the lines that change a default commented out. The file is sourced by `bash`, so trailing comments are allowed and `docker --env-file` cannot read it. `serve.sh` sets `TF_GLM_RANK` and `TF_GLM_WORLD` from its arguments after it reads the file, so the file cannot change them.

## What serve.sh fixes

- `--max-tokens 32768`: the reply limit, reasoning included, for a request that names no `max_tokens` (the engine's own default is 4,096).
- `--no-update-check`: this engine takes the flag and does nothing with it.
- `NCCL_COMM_ID`, `TF_GLM_RANK` and `TF_GLM_WORLD`, from its arguments and the rank file.
- The window, the effort, the streams, the vision tower, the checkpoint and the wire's settings from the release's file and the rank file, as above. A TP other than 2, 3 or 4, a rank outside it, a release file without `CHECKPOINT` or a checkpoint folder the host lacks stops `serve.sh` before the engine starts.

Arguments after `TP RANK RANK_ENV` (after the label, through `cluster.sh`) follow these, so a value flag given again takes the later value (`--context 131072` over `CONTEXT`), and `--api-key` and `--alias` add to their lists. `cluster.sh` passes them through SSH and `bash -c` unquoted: an argument with a space or a quote does not arrive whole.

## Engine flags

Flags that can follow the label, with the engine's defaults. The ranks compare those marked compared at start, and every rank stops on a difference.

| Flag | Default | Meaning |
|---|---|---|
| `--kv-cache fp8` | `bf16` | the FP8 latent cache, about twice the window per GiB; compared; tried once at TP=2 ([limits](../README.md#limits)) |
| `--prompt-cache-gib N` | unset: 16 GiB, at most what the streams leave | the kept prompt states' budget; `0` keeps none. Under the release's `TF_KV_SHARE` the prompts stay on the KV pool's pages, the states take slots in this budget, and the rest of it becomes the pool's pages ([rank file](#rank-file)) |
| `--vision-max-images N` | `4` (1 to 64) | the images a request may hold, counting every image of the messages it sends; compared |
| `--vision-image-tokens N` | `4096` (16 to 262144) | the tokens a request's images share; compared |
| `--vision-max-videos N` | `2` (1 to 16) | the videos a request may hold; compared |
| `--vision-video-tokens N` | `16384` (64 to 262144) | the tokens a request's videos share; compared |
| `--vision-urls` | off | HTTPS image URLs as well as data URLs; needs `--vision`; not validated |
| `--no-drafts` | drafts on | one token a round, without the MTP head's drafts; compared |
| `--drafter DIR`, `--drafter-bits N` | none, `4` | DFlash2's drafter in place of the MTP head, its weights in 4 bits (`4`) or BF16 (`0`); needs drafts; compared; its weights (`incoai/GLM-5.3-Flash-DFlash2`) are CC BY-NC-ND 4.0, non-commercial; not run on 3.x |
| `--temperature`, `--top-p`, `--top-k`, `--min-p` | the checkpoint's `generation_config.json` | the sampling of a request that names none |
| `--prompt-seed` | off | a request without a seed gets one from its prompt and `TENSORFOLD_SEED_SALT`, not a random one |
| `--no-thinking`, `--thinking-budget`, `--thinking-reserve`, `--loop-guard` | thinking on, `0`, `0`, off | the reasoning's switch and budgets, and the loop guard; not run on 3.x |
| `--keep-warm S` | `900` | the seconds an idle keepalive runs after the last request ends; `0` turns it off |
| `--chat-template FILE` | the checkpoint's | another chat template |
| `--alias NAME`, `--api-key KEY` | none | another model id, another key ([API keys](#api-keys)); both repeatable |
| `--allowed-host`, `--allowed-origin` | none | the hosts and origins a browser may use; repeatable, at most 64 each |
| `--metrics-open` | off | `/metrics` without a key |

The engine's other flags (`--record`, `--compact-*`, `--recall*`, `--cortheon`, `--dashboard` and the rest of `--help`) were not run on 3.x.

The parser stops every rank at start on a flag this build does not serve: `--tp`, `--rank`, `--master` and `--master-port` (the ranks come from `TF_GLM_RANK` and `TF_GLM_WORLD`), `--speed-up`, `--checkpoint-slots`, `--kv-dtype`, `--prefill-fp8`, `--spill-gib`, `--lane-kernels`, `--vision-offload` and the Python engine's other flags. GLM on CUDA refuses at start `--mtp-drafts` (its MTP head drafts at the lanes' depth, and `--mtp-confidence` stops its chains), `--mtp-confidence` together with `--drafter`, `--policy`, `--precision`, `--prompt-cache-over-cap`, `--slide`, `--learn` and `--learn-conversations`, `--segments` above 1, and a `--context` past the model's window (`0` asks for the model's own). `--snapshot-dir` and `--max-snapshots` take only `none` and `0`.

## API keys

- **The key file** (`API_KEY_FILE`, `--api-key-file`): one key a line, `label: key` or the key alone. The engine refuses a file that is not a regular file, that other users may read or write (any group or other read or write bit: `0600` and `0400` pass), or that is larger than 1 MiB.
- **Rereading.** The engine rereads the file when it gets `SIGHUP`, and on a request, at most once a second, after the file changed; a reread that fails (a missing file, another mode, a bad line) closes every route that needs a key until the file reads again. It installs the `SIGHUP` handler only when keys are set. Read from the source alone.
- **More keys.** `TENSORFOLD_API_KEY` in rank 0's environment (its rank file) holds keys separated by commas and turns authentication on as the file does; `--api-key` adds one a flag.
- **Requests.** With keys, every route but `/health` needs `Authorization: Bearer <key>` or `x-api-key: <key>`, and `/health` answers only `{"status": "ok"}`. Without one, a listener beyond loopback is open, and the engine logs a warning at start.
- **This line's tools** send `TENSORFOLD_API_KEY` from where they run as `Authorization: Bearer`, and the tool-argument gate passes a request's key on.

## Engine environment

### Compared across the ranks

The engine compares these at start, before the weights load, and every rank stops on a difference (`REFUSE rank settings: …`).

| Variable | Default | Values |
|---|---|---|
| `TF_HEAT_HIGH`, `TF_HEAT_LOW` | unset: no wait (`serve.sh` sets `92` and `88`) | the prefill heat wait: before each prompt chunk, every rank waits in pauses of 2 s while any rank's hottest zone is above the high mark, until all are at or below the low one; both or neither, low at or under high |
| `TF_GLM_MM` | `1` | `0` runs the BF16 linears on the engine's glue kernels instead of the tiled ones, which gives other tokens ([validation](validation.md)); accepted at TP=3 in 3.1.0 and 3.2.0 |
| `TF_GLM_PREFILL_REDUCE` | `split` | how a prompt chunk's rows are exchanged: `split` sends each rank's rows to every other, after a check at start that every pair of ranks can exchange; `ring` passes them along the ring, for a fabric where some ranks reach only their neighbours; `gather` all-gathers every rank's partial sums and every rank glues every row, which the TP=4 examples name, since on a ring of four `split` does not start: NCCL fails its peer warm-up before split's own check can name the pair |
| `TF_GLM_OVERLAP_PIECES` | `3` | 1 to 8: a prompt chunk's exchanges in this many row pieces |
| `TF_GLM_PROMPT_PAIR` | `1` | `0` turns off the paired steps: while no stream decodes, a prompt step takes two chunks, each one's exchanges running under the other's work, and solo passes (`TF_GLM_CHUNK_SOLO=4096`) take their place; another value, an empty one included, stops the start (`serve.sh`) |
| `TF_GLM_KDA_DECODE_WIDE` | `1` | `0` runs decode windows without KDA's three-kernel chain |
| `TF_GLM_L2PF` | unset: on, on a GB10 at two ranks or more | a decode window's next weights read into L2 on a side stream: `1` on any GPU, `0` off, and another value, an empty one included, stops the start (`serve.sh`); `TF_GLM_L2PF_MB` (`12`, MiB a site), `TF_GLM_L2PF_CTAS` (`2`) and `TF_GLM_L2PF_PACE_GBPS` (`150`, `0` unpaced) tune it and are compared too |
| `TF_GLM_PROMPT_K` | `one` | `shape`: fixed K slices for prompts, an experiment; needs `TF_GLM_MM=1` |
| `TF_GLM_DENSE_BITS`, `TF_GLM_HEAD_BITS` | `16` | `4`, `6` or `8`: the dense linears, or the head, packed at load to that many bits |
| `TF_GLM_LAYERS` | every layer | the first N layers only, a thin model for one-GPU checks |
| `TF_KV_PAGES` | unset: as `auto` | where the streams' KV cache lives: `auto` puts every stream's cache and the engine's own sequence on pages of one pool at two ranks or more; `off` or `0` keeps the windows at any TP, with an empty `TF_KV_SHARE=` beside it, since the engine refuses kept prompts on pages without the pages; `on`, `all` or another word pages at any TP, and an empty value is `auto`. With `--kv-cache fp8`, `auto` and `off` keep the windows and `on` or `all` stops the start |

The ranks also compare the world and their ranks, `--kv-cache`, the drafts and `--drafter`, `--vision` and its four limits, the window, the checkpoint's `config.json`, the engine binary and the checkpoint's digest: its metadata and every shard byte, kept in a cache in the container, so the first start in a new container reads the whole checkpoint.

### Read on each rank, not compared

A rank may differ from the others in these without a refusal.

| Variable | Default | Meaning |
|---|---|---|
| `TF_ROCE` | on | TP=2: the small all-gathers, up to `TF_ROCE_MAX_KB` a rank, go by RoCE writes on the engine's own path instead of NCCL; `0` keeps them on NCCL, and so does a rank pair where either does not bring the path up |
| `TF_ROCE_HCA` | `NCCL_IB_HCA` | the devices that path stripes over, at most two, without `=` prefixes or `:port` suffixes |
| `TF_ROCE_GID_INDEX` | each device's RoCE v2 IPv4 GID | the GID index that path uses |
| `TF_ROCE_MAX_KB` | `4096` | the largest gather a rank sends on that path, in KiB; an empty value, `0` or another word stops the start |
| `TF_GLM_PDL` | on | `0` turns off dependent launches (a matmul's weights stream in while the kernel before it finishes) |
| `TF_NVFP4_DECODE_WARPS` | `4` | the warps of the NVFP4 experts' decode kernel, `1` or `4`; another value, an empty one included, fails the load |
| `TF_QMMF_HALF_BELOW` | `96` | decode's MXFP8 and BF16 matmuls take half tiles while their 64-column blocks are fewer than this, with the same sums; `0` never; an empty value takes the default, and one that is not a whole number fails the load |
| `TF_GLM_PROMPT_STEPS` | on | rank 0 only: `0` runs each prompt pass whole, with no other stream's round between its chunks |
| `TF_GLM_SHARED` | on | rank 0 only: `0` gives each stream's draft window a forward of its own instead of one shared with the other streams |
| `TF_GLM_LINK_WAIT` | off | `1` uploads every step for the other ranks and waits for it, as the engine did before |
| `TF_GLM_PROF` | off | profiling lines in the log |
| `TF_GLM_DRAFT_CONFIDENCE`, `TF_GLM_DFLASH2_LOG`, `TF_GLM_DFLASH2_PROF` | `0.7`, off, off | DFlash2's drafter only (`--drafter`) |
| `TF_HEAT_ROOT` | `/sys/class/thermal` | where the thermal zones are read; an empty value takes the default |
| `TF_CUDA_DEVICE` (`--device`) | `0` | the GPU |
| `TF_CUDA_SEGMENTS` (`--segments`) | `1` | GLM takes only 1 |
| `TF_CUDA_MEMORY_RECEIPTS` | off | `1` prints a `TF_MEMORY` JSON line at load and at cleanup |
| `TENSORFOLD_MEMORY_RESERVE_GIB` | on unified memory, 4 GiB or a tenth of the memory, whichever is more | the memory the engine leaves to the system; a set value is at least 2 |
| `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` | none | a cap on what the engine allocates |
| `TENSORFOLD_LIBTURBOJPEG`, `TENSORFOLD_LIBWEBP` | the image's, in `/usr/local/lib` | the JPEG and WebP decoders' files |

`TF_GLM_PDL`, `TF_GLM_PROMPT_STEPS`, `TF_GLM_SHARED`, `TF_GLM_LINK_WAIT` and `TF_GLM_PROF` take `0` or `1` alone, `TF_GLM_DFLASH2_LOG` a whole number and `TF_GLM_DRAFT_CONFIDENCE` a finite number from 0 to 1. Another value stops the start on every rank before the load reads the ranks, NCCL or the weights, with a line that names the variable and what it takes (from 3.12.0's engine: #2578, upstream's since 1.2.6).

The engine sets `NCCL_RUNTIME_CONNECT=0`, `NCCL_CUMEM_HOST_ENABLE=0` and `NCCL_CUMEM_ENABLE=0` when they are unset: every connection registers at start, while the memory is free, and NCCL's cuMem host buffers, which wore out a GB10's driver pool under load, stay off. A rank file can set them otherwise, as the TP=4 examples do for `NCCL_RUNTIME_CONNECT` and `NCCL_CUMEM_ENABLE`.

### Rank 0's server

| Variable | Default | Meaning |
|---|---|---|
| `TENSORFOLD_API_KEY` | none | API keys, separated by commas ([API keys](#api-keys)) |
| `TF_DRAIN_S` | `20` | the seconds a stopping server drains: new requests get 503 with `Retry-After`, and `/health` says `draining` |
| `TF_SSE_KEEPALIVE_S` | `15` | the seconds between a stream's keepalives |
| `TENSORFOLD_PREFILL_SHARE` | `1` (`serve.sh` gives `0.7`) | a long prompt's steps' share of the time while other streams decode, from `0.01` to `1` (another value takes the default): a step that took t waits until the decoding streams have had t × (1 − share) / share of rounds; a prompt with at most 512 rows left never waits, and only the order of whole steps changes. `1` alternates one step with one round |
| `TF_GLM_CLEAR_THINKING` | `0` | `1` gives GLM-5.3's chat template `clear_thinking` true, which drops the reasoning of the turns before the latest user message; `0`, empty or unset gives false, which keeps it; another value refuses to load. A request's `chat_template_kwargs.clear_thinking` overrides it for that request (from 3.8.0's engine, upstream 1.1.5) |
| `TENSORFOLD_REQUEST_LOG` | none | a file that receives every chat and completion request's body as a JSON line, image URLs redacted and the text kept |
| `TENSORFOLD_SEED_SALT` | `0` | an integer mixed into the seed `--prompt-seed` takes from a prompt |
| `TENSORFOLD_NO_LIVE`, `COLUMNS` | off, the terminal's | `1` turns the live display off; its width |
| `TENSORFOLD_VIDEO_TOKENS` | `16384` | the tokens rank 0 sizes a video's frames to; not compared across the ranks; read from the source alone |
| `HF_HUB_CACHE`, `HF_HOME` | Hugging Face's | where a model given by name is found; `serve.sh` gives a folder |
| `BRAVE_SEARCH_API_KEY` | none | `--cortheon`'s web search only |

Nothing that serves GLM reads `TENSORFOLD_NO_UPDATE_CHECK` or `HF_HUB_OFFLINE`, which the binary lists, `TENSORFOLD_CUDA_KERNELS` (a captured kernel set, which GLM does not use), `TF_GRAPH_CACHE` (other families'), `TF_HEAT_CEILING` (gone since 3.3.0's engine), or 2.x's `TF_GLM_HEAT_*`, `TF_GLM_CACHE_*`, `TF_GLM_KV`, `TF_GLM_COPY_DRAFTS`, `TF_GLM_B16_DECODE_TABLE` and `TF_GLM_LOOP_GUARD`.

**Empty values.** A line `NAME=` in the rank file passes the engine an empty value, and from 3.12.0's engine (upstream 1.2.6) the engine reads an empty or blank value as unset for nearly every setting. GLM's start settings (among them `TF_GLM_MM`, `TF_GLM_PREFILL_REDUCE`, `TF_GLM_OVERLAP_PIECES`, `TF_GLM_KDA_DECODE_WIDE`, `TF_GLM_PROMPT_K`, `TF_GLM_DENSE_BITS`, `TF_GLM_HEAD_BITS`, `TF_GLM_LAYERS` and `TF_GLM_CHUNK_SOLO`), `TF_GLM_PDL`, `TF_GLM_PROMPT_STEPS`, `TF_GLM_SHARED`, `TF_GLM_LINK_WAIT`, `TF_QMMF_HALF_BELOW`, `TF_ROCE`, `TF_KV_SHARE`, `TENSORFOLD_PREFILL_SHARE` and `TENSORFOLD_MEMORY_RESERVE_GIB` take their defaults, and an empty `TF_KV_PAGES` is `auto`. Empty `TF_HEAT_HIGH` and `TF_HEAT_LOW` together turn the heat wait off (`serve.sh`'s 92 and 88 apply only to names the rank file leaves out); one of them empty stops the start, since the two go together or not at all. `TF_ROCE_MAX_KB` and `TF_NVFP4_DECODE_WARPS` still refuse an empty value. `serve.sh` passes empty values on as they are, and stops the start on an empty `VISION`, `TF_GLM_ROCE_MULTI`, `TF_GLM_PROMPT_PAIR` or `TF_GLM_L2PF`: these on/off settings take `1` or `0` alone.

## NCCL

The rank files' NCCL lines. Rank 0's address and port reach NCCL as `NCCL_COMM_ID`, which `serve.sh` builds: rank 0 makes its NCCL id there, and the other ranks take the id over the ranks' liveness lines (upstream's bootstrap since #1178). A rank other than 0 whose file names `NCCL_SOCKET_IFNAME`, as every example's does, drops `NCCL_COMM_ID` before NCCL's first call, so its NCCL bootstrap uses that interface. At TP=3 it has to: with `NCCL_COMM_ID` set, NCCL's bootstrap looks for a local interface in that address's subnet, which the ring's `/32` addresses give rank 0's host alone. An `NCCL_COMM_ID` line in `~/.nccl.conf` or `/etc/nccl.conf` would come back at that call.

| Variable | TP=2 example | TP=3 example | Meaning |
|---|---|---|---|
| `NCCL_IB_HCA` | the rank's two devices on the link | `=` and the four devices, port 1 | the RDMA devices, both rails; this host's |
| `NCCL_IB_GID_INDEX` | `3` | `3` | the ports' RoCE v2 entry; this host's, and it can move after a link drops ([a GID index that moves](../../docs/nccl-validation.md#a-gid-index-that-moves)) |
| `NCCL_SOCKET_IFNAME` | the link's interface | `=` and the host's `/32` interface | NCCL's bootstrap interface, never the management Wi-Fi; on a rank other than 0 it also has the engine drop `NCCL_COMM_ID`; this host's |
| `NCCL_SOCKET_FAMILY`, `NCCL_IB_ADDR_FAMILY` | `AF_INET` | `AF_INET` | IPv4 |
| `NCCL_NET`, `NCCL_IB_DISABLE`, `NCCL_IB_ROCE_VERSION_NUM` | `IB`, `0`, `2` | `IB`, `0`, `2` | NCCL's IB transport over RoCE v2, named |
| `NCCL_NET_PLUGIN` | unset | `none` | NCCL's own IB transport, not the image's plugin |
| `NCCL_IB_SUBNET_AWARE_ROUTING` | unset | `1` | each peer over the port whose `/30` reaches it |
| `NCCL_MIN_NCHANNELS`, `NCCL_MAX_NCHANNELS` | `4` | `4` | four channels |
| `NCCL_DEBUG`, `NCCL_DEBUG_SUBSYS` | `INFO`, `INIT,NET` | `INFO`, `INIT,NET` | each connection's transport logged once at start, which [setup §5](../SETUP.md#5-start) reads |

The TP=4 examples, the reference ring of four's (experimental, from 3.12.0), take TP=3's lines, with rank 0's `/32` on `tp4host0`, and these:

| Variable | TP=4 example | Meaning |
|---|---|---|
| `NCCL_ALGO` | `Ring` | the ring alone |
| `NCCL_GRAPH_FILE` | `/work/graph.xml`, the rank's `examples/tp4-rank*.graph.xml` | the rank's four channels: it receives on the port toward the rank before it and sends on the port toward the next |
| `NCCL_IB_MERGE_NICS` | `0` | each device of a port stays its own, as the graph names them |
| `NCCL_RUNTIME_CONNECT` | `1` | connections on first use: at init NCCL 2.30.7 would also connect trees over the diagonals, which have no cable |
| `NCCL_CUMEM_ENABLE` | `1` | NCCL 2.30.7 connects on first use only with cuMem, which the engine turns off unless the rank file sets it |

The values other than each host's own came from 2.x, where they were measured; what 3.x measured again is in [decisions](decisions.md#fabric), and every 3.x start ran every connection over `NET/IB`. The TP=2 RoCE path of the engine ([above](#read-on-each-rank-not-compared)) reads `NCCL_IB_HCA` too.

## Cluster file

| Setting | Default | Meaning |
|---|---|---|
| `TP` | none, required | 2, 3 or 4; `cluster.sh` starts TP=3's ranks together and any other size's highest rank first, and `serve.sh` refuses a size other than these |
| `HOSTS` | none, required | the hosts' SSH names in rank order, as many as `TP`; rank 0 serves HTTP |
| `CHECKOUT` | none, required | this repository on every host, expanded there; the memory guard runs from it |
| `SSH` | `ssh -o ConnectTimeout=20` | the command that reaches a host |
| `CONTAINER` | `glm53-tf3` | the container on every host |
| `WORK` | `$HOME/glm53-tf3`, expanded on the host | the host directory at `/work` |

`cluster.sh` fixes its timings: at TP=2 and TP=4 the ranks start 3 s apart, the highest first, and at TP=3 together, rank 0 last; `start` waits 15 minutes for rank 0's `serving` line; `stop` waits up to 60 s for each rank, sends `TERM` again to a rank left and waits 30 s more.

## Container

| Setting | Default | Meaning |
|---|---|---|
| `IMAGE WORK_DIR` (arguments) | none, required | the image, and the host directory at `/work`: the rank file and the logs |
| `CONTAINER` | `glm53-tf3` | the container's name |
| `HF_HUB` | `~/.cache/huggingface/hub` | the Hugging Face cache, at `/hub` read-only |
| `HUB_RW` | `0` | `1` mounts the cache writable, for a build host that writes into it |
| `CPUSET` | unset or `auto`: the cores with the lowest maximum frequency (`0-4,10-14` on a GB10), or every core when all report the same maximum or none reports one | the container's cores ([why](../README.md#serving-defaults)); empty for every core, as 3.0.0's and 3.1.0's heat runs had them, or a list for docker's `--cpuset-cpus` |

Fixed in `create_container.sh`: host network and IPC, every GPU, `/dev/infiniband` (it refuses a host without it), `IPC_LOCK` with locked memory unlimited, a 64 MiB `/dev/shm`, `/work` as the working directory and no restart policy; the container sleeps until a rank starts in it. `docker update --cpuset-cpus` moves the cores of a container that exists ([recreate the container](operations.md#recreate-the-container)).

## Memory guard

`hostwatch.sh LOG [CONTAINER]`, which `cluster.sh` starts on every host, reads `MemAvailable` every 2 s from 5 s after the start and stops the engine with `pkill -9` in the container when it falls below 5 GiB (whole GiB); it ends when the engine is gone or its container no longer runs. A round whose check fails or does not return within the round's 2 s (`docker exec` can fail or stall when memory is short) writes `check-failed`, and the watch goes on. The threshold and the interval are fixed in the script.

## Fixed in the engine

No setting changes these (read from the source):

- **The ranks' liveness lines.** Rank 0 waits 300 s for each other rank's line, and the others retry for 300 s; every rank's ready record must arrive within 15 minutes, and a host that vanishes shows within about 20 s.
- **The NCCL id.** The other ranks wait up to 15 minutes for rank 0's id over their lines.
- **Media.** The bytes of an image, of a request's media and of a video, and a video's frames, have limits without a flag ([limits](../README.md#limits)).

## Tools

The commands of `python -m glm53_tf`, run from `v3/`; what each check does is in [validation](validation.md) and [benchmark method](benchmarks.md).

| Command | Options (default) | Environment |
|---|---|---|
| `download` | `--tp` (`2`, `3` or `4`: the checkpoint that TP serves) or `--checkpoint` (`xsfp4` or `jammed`), one of the two required; `--background` (Linux; its log and status under `state/<checkpoint>/`; it writes the job's status before it returns, so `verify-download --wait` can follow at once, and it refuses while a download owns the folder) | sets `HF_XET_NUM_CONCURRENT_RANGE_GETS=4` and `HF_HUB_DOWNLOAD_TIMEOUT=120` when unset, and reads Hugging Face's own variables; a cache moved with `HF_HUB_CACHE` needs `create_container.sh`'s `HF_HUB` there too |
| `verify-download` | `--hf` (the `hf` client) and `--output`, required; `--tp` or `--checkpoint`, one of the two required, as `download`'s; `--wait` (polls every 30 s; exits 2 while the download is paused) | none |
| `tool-gate` | `--port` (8896), `--upstream` (`http://127.0.0.1:8095`, an HTTP origin on loopback only), `--log` (stderr), `--timeout` (2400 s a call to the engine), `--parallel-tool-calls` (`one` by default: a request with tools asks the engine for one call a turn and says so in its system message; `client`: as the client sent it) | listens on 127.0.0.1 only, refuses a request body over 64 MiB with 413 and passes a request's key on |
| `decode-check` | none | `BASE` (`http://127.0.0.1:8095`), `MODEL` (`glm-tf`), `PROMPT_KIND` (`count`, `prose` or `code`), `SAMPLES` (3), `MAX_TOKENS` (512), `PROMPT_TOKENS` (2048), `TOKENS_OUT` (a file for the completions), `TENSORFOLD_API_KEY` |
| `decode-divergence` | two `TOKENS_OUT` files | none |
| `score-nll` | `--url`, `--tokenizer` and `--out`, required; `--set` (`config/nll_set.json`), `--model` (the server's first), `--seed` (42) | `TENSORFOLD_API_KEY`; exits 2 when the tokenizer or a text is not the set's, 3 when the server refuses `prompt_logprobs`, 1 when the set fails |
| `bench` | `--kinds` (`prefill,decode`; `edit` on request), `--runs` (3), `--lines` (3200, the prefill's), `--warmup` (1), `--out` | `BASE`, `MODEL`, `TENSORFOLD_API_KEY` |
| `long-input` | `--passphrases` (1 or 3) and `--lines` or `--tokens`, required; `--out` | `BASE`, `MODEL`, `TENSORFOLD_API_KEY`; exits 1 when a passphrase is missed |
| `mojibake` | `--out`, required; `--repeats` (3 answers a language), `--temperature`, `--top-p` and `--seed`, all three or none (sampled; answer *i* draws with seed + *i*), `--max-tokens` (32768, `serve.sh`'s) | `BASE`, `MODEL`, `TENSORFOLD_API_KEY`; exits 1 when an answer has a broken character, else 2 when one is inconclusive |

## Locks

| File | Pins | Read by |
|---|---|---|
| [`config/xsfp4.lock.json`](../config/xsfp4.lock.json) | XSFP4's repository and revision | `download` and `verify-download` with `--tp 3`, `--tp 4` or `--checkpoint xsfp4`; `config/tp3.env`'s and `config/tp4.env`'s `CHECKPOINT` names the same revision, and a test keeps them equal |
| [`config/jammed.lock.json`](../config/jammed.lock.json) | Jammed XSFP4's repository and revision | `download` and `verify-download` with `--tp 2` or `--checkpoint jammed`; `config/tp2.env`'s `CHECKPOINT` names the same revision, and a test keeps them equal ([checkpoints](../README.md#checkpoints)) |
| [`config/engine.lock.json`](../config/engine.lock.json) | the engine's fork, release branch and commit, the upstream release under it, the Zig compiler (its URL and SHA-256), xgrammar, the media libraries' releases (SHA-256) and the build flags | the image build: [`docker/Dockerfile`](../docker/Dockerfile)'s arguments, which a test keeps equal to the lock |
| [`config/nll_set.json`](../config/nll_set.json) | the NLL set's texts and the tokenizer they were cut with, by its SHA-256 | `score-nll` |
| [`requirements/huggingface.lock.txt`](../requirements/huggingface.lock.txt) | the Hugging Face client | the tools' virtual environment ([setup §2](../SETUP.md#2-checkout-and-checkpoint)) |

`/usr/share/doc/tf3/ENGINE` in the image names the engine commit it was built from and every binary's SHA-256.
