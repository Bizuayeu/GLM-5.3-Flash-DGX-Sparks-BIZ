# Configuration (3.x)

[日本語](configuration.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Operations](operations.md)

Every setting a 3.x deployment reads: where it is set, its default, what it does and which ranks read it. The values a release serves, and why, are the README's [serving defaults](../README.md#serving-defaults); this page is the inventory behind them. The engine's settings are those of the commit the image pins ([`config/engine.lock.json`](../config/engine.lock.json)), read from its source; `tensorfold-native serve --help` in the container lists its flags.

3.x's acceptance ran every setting here at its default; where a row names another value, a release's acceptance or a recorded trial ran it too ([measured on the release](../README.md#measured-on-the-release), [limits](../README.md#limits)). Any other value is outside what the acceptance covers, and so is what a row says it reads from the source alone.

## Where settings live

| Where | Read by | Takes effect |
|---|---|---|
| Rank file, `/work/rank.env` on each host ([examples](../examples/)) | `serve.sh`, which sources it with every variable exported, so any variable in it reaches the engine | at the rank's next start |
| `serve.sh` arguments after `TP RANK RANK_ENV`; through `cluster.sh`, the arguments after the label | `tensorfold-native serve`, after `serve.sh`'s own | at the next start, on every rank |
| Cluster file, `state/cluster.env` on the control machine | `cluster.sh` | at its next command |
| `create_container.sh`'s environment | `create_container.sh` and `cpuset.sh` | when the container is created (`docker update` changes its cores later) |
| The tools' options and environment | `python -m glm53_tf <command>`, from `v3/` | at the run |
| [`config/`](../config/) | the image build and the tools | at the next build or run |

`cluster.sh` runs the image's `serve.sh` (`/opt/glm53-tf3/serve.sh`), not the checkout's: a change to [`scripts/serve.sh`](../scripts/serve.sh) reaches the ranks with a new image only.

## Rank file

| Setting | Default | Meaning | Ranks |
|---|---|---|---|
| `MASTER` | none, required | rank 0's address on the link between the hosts; `serve.sh` gives the engine `NCCL_COMM_ID=MASTER:NCCL_PORT` | the same on every rank |
| `NCCL_PORT` | `29583` | rank 0's port in `NCCL_COMM_ID`, where rank 0's NCCL bootstrap listens; the ranks' liveness lines take the port after it | the same |
| `CONTEXT` | `524288` at TP=2, `1048576` at TP=3; an empty value takes the default | the window (`--context`) | the same; compared at start |
| `PARALLEL` | `1` | requests decoded at once (`--parallel`); an empty value passes none, and the engine takes up to 8 streams as the memory free at start allows (accepted at TP=2); a number that does not fit is refused at start | rank 0, which sizes every rank's streams by the smallest room among them |
| `VISION` | `1` | image and video input (`--vision`), read by the checkpoint's vision tower on rank 0; any value but an empty one passes it, `0` included, so only `VISION=` serves text alone | the same; compared at start |
| `MODEL_NAME`, `HOST`, `PORT` | `glm-tf`, `127.0.0.1`, `8095` | rank 0's model id and listener (`--name`, `--host`, `--port`) | rank 0 |
| `REASONING_EFFORT` | `high` | the effort for a request that names none (`--reasoning-effort`): `low`, `medium`, `high` or `xhigh`, and another value, `max` among them, stops every rank at start; an empty value passes none and leaves it to the chat template. A request itself may name `none`, `minimal`, `low`, `medium`, `high`, `xhigh` or `max` | rank 0 |
| `API_KEY_FILE` | none | rank 0's key file for serving beyond loopback (`--api-key-file`, [API keys](#api-keys)) | rank 0 |
| `CHECKPOINT` | XSFP4's snapshot at its lock's revision under `/hub` | the checkpoint folder inside the container; 3.x accepts XSFP4 alone ([checkpoints](../README.md#checkpoints)) | the same; compared at start, by its digest |
| `TF_HEAT_HIGH`, `TF_HEAT_LOW` | `92`, `88` (°C) | the prefill heat wait's band ([compared across the ranks](#compared-across-the-ranks)); `serve.sh` unsets an empty one, and the engine refuses one without the other, so empty both for no wait | the same; compared at start |
| any other variable | none | exported to the engine: the [engine environment](#engine-environment) (`TF_GLM_*`, `TF_ROCE*` and the rest) and the [NCCL settings](#nccl) | as each says |

The example files hold the reference hosts' values, with the lines that change a default commented out. The file is sourced by `bash`, so trailing comments are allowed and `docker --env-file` cannot read it. `serve.sh` sets `TF_GLM_RANK` and `TF_GLM_WORLD` from its arguments after it reads the file, so the file cannot change them.

## What serve.sh fixes

- `--max-tokens 32768`: the reply limit, reasoning included, for a request that names no `max_tokens` (the engine's own default is 4,096).
- `--no-update-check`: this engine takes the flag and does nothing with it.
- `NCCL_COMM_ID`, `TF_GLM_RANK` and `TF_GLM_WORLD`, from its arguments and the rank file.
- The window, the effort, the streams, the vision tower and the checkpoint from the rank file, as above. A TP other than 2 or 3, or a rank outside it, stops `serve.sh` before the engine starts.

Arguments after `TP RANK RANK_ENV` (after the label, through `cluster.sh`) follow these, so a value flag given again takes the later value (`--context 131072` over `CONTEXT`), and `--api-key` and `--alias` add to their lists. `cluster.sh` passes them through SSH and `bash -c` unquoted: an argument with a space or a quote does not arrive whole.

## Engine flags

Flags that can follow the label, with the engine's defaults. The ranks compare those marked compared at start, and every rank stops on a difference.

| Flag | Default | Meaning |
|---|---|---|
| `--kv-cache fp8` | `bf16` | the FP8 latent cache, about twice the window per GiB; compared; tried once at TP=2 ([limits](../README.md#limits)) |
| `--prompt-cache-gib N` | unset: 16 GiB, at most what the streams leave | the kept prompt states' budget; `0` keeps none. The reference ring's TP=3 cache is this cap |
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

The parser stops every rank at start on a flag this build does not serve: `--tp`, `--rank`, `--master` and `--master-port` (the ranks come from `TF_GLM_RANK` and `TF_GLM_WORLD`), `--speed-up`, `--checkpoint-slots`, `--kv-dtype`, `--prefill-fp8`, `--spill-gib`, `--lane-kernels`, `--vision-offload` and the Python engine's other flags. GLM on CUDA refuses at start `--mtp-drafts` and `--mtp-confidence` (its drafts are not tunable), `--policy`, `--precision`, `--prompt-cache-over-cap`, `--slide`, `--learn` and `--learn-conversations`, `--segments` above 1, and a `--context` past the model's window (`0` asks for the model's own). `--snapshot-dir` and `--max-snapshots` take only `none` and `0`.

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
| `TF_GLM_PREFILL_REDUCE` | `split` | how a prompt chunk's rows are exchanged: `split` sends each rank's rows to every other, after a check at start that every pair of ranks can exchange; `ring` passes them along the ring, for a fabric where some ranks reach only their neighbours; `gather` |
| `TF_GLM_OVERLAP_PIECES` | `3` | 1 to 8: a prompt chunk's exchanges in this many row pieces |
| `TF_GLM_KDA_DECODE_WIDE` | `1` | `0` runs decode windows without KDA's three-kernel chain |
| `TF_GLM_PROMPT_K` | `one` | `shape`: fixed K slices for prompts, an experiment; needs `TF_GLM_MM=1` |
| `TF_GLM_DENSE_BITS`, `TF_GLM_HEAD_BITS` | `16` | `4`, `6` or `8`: the dense linears, or the head, packed at load to that many bits |
| `TF_GLM_LAYERS` | every layer | the first N layers only, a thin model for one-GPU checks |
| `TF_KV_PAGES` | unset: as `auto` | where the streams' KV cache lives: `auto` puts every stream's cache and the engine's own sequence on pages of one pool at three ranks and keeps a window per stream at two; `off` or `0` keeps the windows at any TP; `on`, `all` or another value, an empty one included, pages at any TP. With `--kv-cache fp8`, `auto` and `off` keep the windows and `on` or `all` stops the start |

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
| `TF_QMMF_HALF_BELOW` | `96` | decode's MXFP8 and BF16 matmuls take half tiles while their 64-column blocks are fewer than this, with the same sums; `0` never; a value that is not a number takes the default |
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

The engine sets `NCCL_RUNTIME_CONNECT=0`, `NCCL_CUMEM_HOST_ENABLE=0` and `NCCL_CUMEM_ENABLE=0` when they are unset: every connection registers at start, while the memory is free, and NCCL's cuMem host buffers, which wore out a GB10's driver pool under load, stay off. A rank file can set them otherwise; no 3.x run did.

### Rank 0's server

| Variable | Default | Meaning |
|---|---|---|
| `TENSORFOLD_API_KEY` | none | API keys, separated by commas ([API keys](#api-keys)) |
| `TF_DRAIN_S` | `20` | the seconds a stopping server drains: new requests get 503 with `Retry-After`, and `/health` says `draining` |
| `TF_SSE_KEEPALIVE_S` | `15` | the seconds between a stream's keepalives |
| `TENSORFOLD_PREFILL_SHARE` | `1` | a long prompt's steps' share of the time while other streams decode, from `0.01` to `1` (another value takes the default): a step that took t waits until the decoding streams have had t × (1 − share) / share of rounds; a prompt with at most 512 rows left never waits, and only the order of whole steps changes. `1` alternates one step with one round |
| `TENSORFOLD_REQUEST_LOG` | none | a file that receives every chat and completion request's body as a JSON line, image URLs redacted and the text kept |
| `TENSORFOLD_SEED_SALT` | `0` | an integer mixed into the seed `--prompt-seed` takes from a prompt |
| `TENSORFOLD_NO_LIVE`, `COLUMNS` | off, the terminal's | `1` turns the live display off; its width |
| `TENSORFOLD_VIDEO_TOKENS` | `16384` | the tokens rank 0 sizes a video's frames to; not compared across the ranks; read from the source alone |
| `HF_HUB_CACHE`, `HF_HOME` | Hugging Face's | where a model given by name is found; `serve.sh` gives a folder |
| `BRAVE_SEARCH_API_KEY` | none | `--cortheon`'s web search only |

Nothing that serves GLM reads `TENSORFOLD_NO_UPDATE_CHECK` or `HF_HUB_OFFLINE`, which the binary lists, `TENSORFOLD_CUDA_KERNELS` (a captured kernel set, which GLM does not use), `TF_GRAPH_CACHE` (other families'), `TF_HEAT_CEILING` (gone since 3.3.0's engine), or 2.x's `TF_GLM_HEAT_*`, `TF_GLM_CACHE_*`, `TF_GLM_KV`, `TF_GLM_COPY_DRAFTS`, `TF_GLM_B16_DECODE_TABLE` and `TF_GLM_LOOP_GUARD`.

**Empty values.** A line `NAME=` in the rank file gives the engine an empty value, not an unset one. The engine refuses an empty `TF_GLM_MM`, `TF_GLM_PREFILL_REDUCE`, `TF_GLM_OVERLAP_PIECES`, `TF_GLM_KDA_DECODE_WIDE`, `TF_GLM_PROMPT_K`, `TF_GLM_DENSE_BITS`, `TF_GLM_HEAD_BITS`, `TF_GLM_LAYERS`, `TF_ROCE_MAX_KB` or `TF_NVFP4_DECODE_WARPS`; an empty `TF_GLM_PDL`, `TF_ROCE`, `TF_GLM_PROMPT_STEPS`, `TF_GLM_SHARED`, `TF_GLM_LINK_WAIT`, `TF_QMMF_HALF_BELOW` or `TENSORFOLD_PREFILL_SHARE` acts as unset, and an empty `TF_KV_PAGES` pages as `on` does. `serve.sh` itself unsets an empty `TF_HEAT_HIGH` or `TF_HEAT_LOW`.

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

The values other than each host's own came from 2.x, where they were measured; what 3.x measured again is in [decisions](decisions.md#fabric), and every 3.x start ran every connection over `NET/IB`. The TP=2 RoCE path of the engine ([above](#read-on-each-rank-not-compared)) reads `NCCL_IB_HCA` too.

## Cluster file

| Setting | Default | Meaning |
|---|---|---|
| `TP` | none, required | 2 or 3; `cluster.sh` starts any other value in TP=2's order, and `serve.sh` refuses it |
| `HOSTS` | none, required | the hosts' SSH names in rank order, as many as `TP`; rank 0 serves HTTP |
| `CHECKOUT` | none, required | this repository on every host, expanded there; the memory guard runs from it |
| `SSH` | `ssh -o ConnectTimeout=20` | the command that reaches a host |
| `CONTAINER` | `glm53-tf3` | the container on every host |
| `WORK` | `$HOME/glm53-tf3`, expanded on the host | the host directory at `/work` |

`cluster.sh` fixes its timings: at TP=2 the ranks start 3 s apart, the highest first, and at TP=3 together, rank 0 last; `start` waits 15 minutes for rank 0's `serving` line; `stop` waits up to 60 s for each rank, sends `TERM` again to a rank left and waits 30 s more.

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

`hostwatch.sh LOG [CONTAINER]`, which `cluster.sh` starts on every host, reads `MemAvailable` every 2 s from 5 s after the start and stops the engine with `pkill -9` in the container when it falls below 5 GiB (whole GiB); it ends when the engine does. The threshold and the interval are fixed in the script.

## Fixed in the engine

No setting changes these (read from the source):

- **The ranks' liveness lines.** Rank 0 waits 300 s for each other rank's line, and the others retry for 300 s; every rank's ready record must arrive within 15 minutes, and a host that vanishes shows within about 20 s.
- **The NCCL id.** The other ranks wait up to 15 minutes for rank 0's id over their lines.
- **Media.** The bytes of an image, of a request's media and of a video, and a video's frames, have limits without a flag ([limits](../README.md#limits)).

## Tools

The commands of `python -m glm53_tf`, run from `v3/`; what each check does is in [validation](validation.md) and [benchmark method](benchmarks.md).

| Command | Options (default) | Environment |
|---|---|---|
| `download` | `--background` (Linux; its log and status under `state/xsfp4/`), `--checkpoint` (`xsfp4`, the only choice) | sets `HF_XET_NUM_CONCURRENT_RANGE_GETS=4` and `HF_HUB_DOWNLOAD_TIMEOUT=120` when unset, and reads Hugging Face's own variables; a cache moved with `HF_HUB_CACHE` needs `create_container.sh`'s `HF_HUB` there too |
| `verify-download` | `--hf` (the `hf` client) and `--output`, required; `--wait` (polls every 30 s; exits 2 while the download is paused); `--checkpoint` (`xsfp4`) | none |
| `tool-gate` | `--port` (8896), `--upstream` (`http://127.0.0.1:8095`, an HTTP origin on loopback only), `--log` (stderr), `--timeout` (2400 s a call to the engine) | listens on 127.0.0.1 only, refuses a request body over 64 MiB with 413 and passes a request's key on |
| `decode-check` | none | `BASE` (`http://127.0.0.1:8095`), `MODEL` (`glm-tf`), `PROMPT_KIND` (`count`, `prose` or `code`), `SAMPLES` (3), `MAX_TOKENS` (512), `PROMPT_TOKENS` (2048), `TOKENS_OUT` (a file for the completions), `TENSORFOLD_API_KEY` |
| `decode-divergence` | two `TOKENS_OUT` files | none |
| `score-nll` | `--url`, `--tokenizer` and `--out`, required; `--set` (`config/nll_set.json`), `--model` (the server's first), `--seed` (42) | `TENSORFOLD_API_KEY`; exits 2 when the tokenizer or a text is not the set's, 3 when the server refuses `prompt_logprobs`, 1 when the set fails |
| `bench` | `--kinds` (`prefill,decode`; `edit` on request), `--runs` (3), `--lines` (3200, the prefill's), `--warmup` (1), `--out` | `BASE`, `MODEL`, `TENSORFOLD_API_KEY` |
| `long-input` | `--passphrases` (1 or 3) and `--lines` or `--tokens`, required; `--out` | `BASE`, `MODEL`, `TENSORFOLD_API_KEY`; exits 1 when a passphrase is missed |
| `mojibake` | `--out`, required; `--repeats` (3 answers a language), `--temperature`, `--top-p` and `--seed`, all three or none (sampled; answer *i* draws with seed + *i*), `--max-tokens` (32768, `serve.sh`'s) | `BASE`, `MODEL`, `TENSORFOLD_API_KEY`; exits 1 when an answer has a broken character, else 2 when one is inconclusive |

## Locks

| File | Pins | Read by |
|---|---|---|
| [`config/xsfp4.lock.json`](../config/xsfp4.lock.json) | XSFP4's repository and revision | `download` and `verify-download`; `serve.sh`'s default folder names the same revision, and a test keeps them equal |
| [`config/engine.lock.json`](../config/engine.lock.json) | the engine's fork, release branch and commit, the upstream release under it, the Zig compiler (its URL and SHA-256), xgrammar, the media libraries' releases (SHA-256) and the build flags | the image build: [`docker/Dockerfile`](../docker/Dockerfile)'s arguments, which a test keeps equal to the lock |
| [`config/nll_set.json`](../config/nll_set.json) | the NLL set's texts and the tokenizer they were cut with, by its SHA-256 | `score-nll` |
| [`requirements/huggingface.lock.txt`](../requirements/huggingface.lock.txt) | the Hugging Face client | the tools' virtual environment ([setup §2](../SETUP.md#2-checkout-and-checkpoint)) |

`/usr/share/doc/tf3/ENGINE` in the image names the engine commit it was built from and every binary's SHA-256.
