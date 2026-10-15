# Deployment runbook (2.x)

[日本語](SETUP.ja.md) · [2.x overview](README.md) · [Validation](docs/validation.md)

The ordered steps for serving the 2.x line on two hosts at TP=2 or three hosts at TP=3. The hosts, cables, kernel and checkpoint are prepared as for 1.x, and those steps link to the [1.x runbook](../v1/SETUP.md). Every host has the same checkout; the commands below run from its root, where the image's build context is; the line's Python tools run from `v2/`. Every command that changes a host (stopping another server, starting this one) belongs inside a window the operator has authorized.

## 1. Hosts and fabric

Two or three DGX Spark or compatible GB10 systems with ConnectX-7 links, prepared and inspected as in [1.x step 1](../v1/SETUP.md#1-collect-inputs-and-inspect-both-hosts) (inventory, kernel, other workloads). Cable and qualify the fabric as in [1.x step 5](../v1/SETUP.md#5-connect-and-qualify-the-fabric--cable-required): a direct link for the pair, a ring for three hosts ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)). Record for each host the RDMA device names on its links (`ibdev2netdev`), the GID index that is RoCE v2 on the link's IPv4 address, and the interface or address the ranks meet on.

Cap the GPU clock on every host before long runs ([GPU clock cap](../docs/hosts.md#gpu-clock-cap)); the [host tools](../host/README.md#install) install the cap as a boot unit.

## 2. Checkout and checkpoint

Check out the same reviewed commit on every host (a `v2.*` release tag). On every host, prepare the tools' virtual environment from `v2/`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/huggingface.lock.txt
python -m glm53_tf --version
```

Download the pinned checkpoint once, from `v2/` on one host, and verify it; the revision is in [`config/model.lock.json`](config/model.lock.json):

```sh
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait
```

To serve the published AXL weights instead (an option; [configuration](README.md#configuration)), download and verify them the same way; their revision is in [`config/axl.lock.json`](config/axl.lock.json), and their download state is kept under `state/axl/`, apart from the pinned one's:

```sh
python -m glm53_tf download --checkpoint axl --background
python -m glm53_tf verify-download --checkpoint axl --hf .venv/bin/hf --output ../records/checksum-axl --wait
```

Then copy the cache to the other hosts and verify each copy with the same `verify-download`: on each, run `download` once (with `--checkpoint axl` for AXL) so that its `state/` records the snapshot, which reuses the copied files and fetches only a missing one, then `verify-download` without `--wait`; how to copy, and why to verify before loading, are as in [1.x step 3](../v1/SETUP.md#3-acquire-the-checkpoint-once-and-verify-each-copy). The engine reads the checkpoint from each host's Hugging Face cache, by default `~/.cache/huggingface/hub`.

Before copying, check that the model's folder holds the files, for example by its size (`du -sh ~/.cache/huggingface/hub/models--<owner>--<name>`). Newer Hugging Face hub clients can keep a model's files in a store shared by the whole cache (`hub/blobs/xx/…`) and leave only links in the model's folder: huggingface_hub 1.32.0 did on one reference host, while 1.30.0, the version the lock installs, kept them under the model's own `blobs/` on the others. Copying such a folder copies the links only, and the next `download` on the receiving host fetches everything from the Internet again. Copy the shared `hub/blobs/` entries too, or use the same client version on every host.

## 3. Image

Build on one of the GB10 hosts (linux/arm64), from the checkout root:

```sh
docker build -f v2/docker/Dockerfile -t glm53-tf:2.9.2 .
docker image inspect --format '{{.Id}}' glm53-tf:2.9.2
```

The Dockerfile pins the engine by one commit (`TENSORFOLD_REF`) and refuses to build without a full SHA. Copy the image to the other hosts (`docker save glm53-tf:2.9.2 | ssh <host> docker load`, over the link) or build it there, then compare the image IDs of every host; they must be equal. The base image is pinned by digest, `nvcr.io/nvidia/pytorch@sha256:6e8ccc607fc2a51e3741667b86316a0889418ba8b78ed0ba96e8d282b648a7a6` (the index of `nvcr.io/nvidia/pytorch:26.09-py3` when it was measured), so a moved tag cannot change it. Triton is pinned at 3.7.1 over the base's 3.8.0, which changes the engine's sums. The image's tag names the last version that changed a file the image copies (the Dockerfile, `serve.sh`, `build_ext.sh` and the licence files): a version that changes none of them, such as one for documents or the host-side tools, keeps that tag.

## 4. Container and rank file on each host

```sh
v2/scripts/create_container.sh glm53-tf:2.9.2        # container glm53-tf, ~/glm53-tf at /work
cp v2/examples/tp3-rank0.env ~/glm53-tf/rank.env      # this host's rank: tp2-rank0/1 or tp3-rank0/1/2
```

Edit `~/glm53-tf/rank.env` with this host's values: `MASTER` (rank 0's address on the link, the same on every rank), `NCCL_IB_HCA` (the RDMA devices on the links, both rails), `NCCL_IB_GID_INDEX`, and `NCCL_SOCKET_IFNAME`. The examples are the reference hosts' files and say what each line was measured as. The file is sourced by `bash`, not passed to `docker --env-file`. To serve the published AXL weights, add `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16/snapshots/bbad98c8f380588c16a2326bf5a2ab7344190b07` to the file of every rank; without it a rank serves the pinned snapshot, and ranks started on different checkpoints refuse to start.

## 5. Build the engine's extensions

On each host, once per image:

```sh
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh
```

It compiles the CUDA extensions the GLM NVFP4 path loads into `~/glm53-tf/ext` before any weight is read. Without it the first start compiles them while loading, and on the reference pair that took rank 0's free memory down to 6-7 GiB, near the guard's 5 GiB.

## 6. Start

From a machine with SSH to every host, after copying [`examples/cluster.tp2.env`](examples/cluster.tp2.env) or [`cluster.tp3.env`](examples/cluster.tp3.env) to `state/cluster.env` (untracked, so your site's values stay out of Git) and setting `HOSTS` (SSH names in rank order) and `CHECKOUT` (this repository on the hosts):

```sh
v2/scripts/cluster.sh state/cluster.env start first
```

It starts the highest rank first and rank 0 last, each `serve.sh TP RANK /work/rank.env` in its container, starts the memory guard on every host (`hostwatch.sh`: stops the engine below 5 GiB `MemAvailable`) and waits for rank 0's `[tensorfold] serving` line. It ends with `READY` and rank 0's last `[tensorfold]` lines; with `FAILED` and every rank's log tail at the first `Traceback` or a rank whose engine is gone; or with `TIMEOUT` after 15 minutes. Each rank logs to `~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log` and the guard to `hostwatch-<LABEL>.log`; arguments after the label go to every rank's `tensorfold serve`, and `cluster.sh state/cluster.env status` counts each rank's engine processes. Without the script, run the same `docker exec -d glm53-tf bash /opt/glm53-tf/serve.sh <TP> <RANK> /work/rank.env` on each host in that order. After `FAILED` or `TIMEOUT`, see [operations](docs/operations.md#start-outcomes).

Read rank 0's startup lines:

- `allocated prompt/reply window`: 300000 at TP=2; at TP=3 the largest that fits (1048576 on the reference ring)
- no line `other conversations' prompts are kept in …`: the default 3 GiB of kept prompts fit beside the window
- each rank's NCCL lines in its log (`via NET/IB`, logged once at start by the rank file's `NCCL_DEBUG` lines) name `NET/IB` for every connection, none over sockets
- the `serving` line: the model name (`glm-tf` unless `MODEL_NAME` is set in the rank file), `127.0.0.1:8095` unless `HOST` and `PORT` are, `context`

Rank 0 serves the OpenAI-compatible API on loopback. A loading start takes about 100-120 s at TP=3 and about 130 s at TP=2 on the reference hosts.

## 7. Tool-argument gate (optional)

The gate, a copy of 1.x's, is a relay that checks each tool call's arguments against the tool's required fields and asks the model once more when one fails ([tool-argument gate](../v1/docs/harnesses.md#tool-argument-gate)). It does not depend on the engine. On rank 0, from `v2/` with its virtual environment:

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

Clients that use tools then talk to port 8896.

## 8. Accept

Run the checks of [validation](docs/validation.md) in its order and compare them with its reference values before routine use, from the decode check (with `bench --kinds edit`'s reply) to memory and temperature. On the published AXL weights the references are their own, where validation gives them. Let the hosts cool between long requests.

What 2.x is accepted for, image by image, is the README's [status](README.md#summary), and each item's evidence is in [measured on the release](README.md#measured-on-the-release); nothing outside that scope is qualified.

## 9. Stop

```sh
v2/scripts/cluster.sh state/cluster.env stop
```

It stops rank 0 first, then the others, waiting up to 60 s for each rank's engine to end, and prints each host's engine-process count and `MemAvailable`; a count above 0 means that rank is still running. The containers stay; `docker stop glm53-tf` frees their GPU claim, which 1.x's `server preflight` checks before a 1.x launch. A rank that stops alone, a stop that leaves an engine and a new image are in [operations](docs/operations.md).
