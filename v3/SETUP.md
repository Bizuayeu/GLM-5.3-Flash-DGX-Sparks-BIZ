# Deployment runbook (3.x)

[日本語](SETUP.ja.md) · [3.x overview](README.md) · [Validation](docs/validation.md)

The ordered steps for serving the 3.x line on two hosts at TP=2 or three hosts at TP=3, on TensorFold's native engine. The hosts, cables, kernel and checkpoint are prepared as for 2.x, and those steps link to the [2.x runbook](../v2/SETUP.md). Every host has the same checkout; the commands below run from its root, where the image's build context is; the line's Python tools run from `v3/`. Every command that changes a host (stopping another server, starting this one) belongs inside a window the operator has authorized.

## 1. Hosts and fabric

As in [2.x step 1](../v2/SETUP.md#1-hosts-and-fabric): two or three DGX Spark or compatible GB10 systems with ConnectX-7 links, a direct link for the pair, a ring for three hosts, the RDMA device names, the RoCE v2 GID index and the address the ranks meet on recorded for each host, and the GPU clock capped before long runs. On the reference ring each host's address for TP=3 is a `/32` on a dummy interface, routed over the links ([three hosts in a ring](../docs/qsfp-network.md#8-three-hosts-in-a-ring)); NCCL's `NCCL_COMM_ID` cannot bootstrap there, so at TP=3 rank 0 writes its NCCL id to a file that the other ranks read (step 6).

## 2. Checkout and checkpoint

Check out the same reviewed commit on every host (a `v3.*` release tag). The checkpoint is the one 1.x and 2.x serve, at the revision in [`config/model.lock.json`](config/model.lock.json); a host that already holds it for 2.x has it. Otherwise prepare the tools' virtual environment from `v3/` and download and verify it as in [2.x step 2](../v2/SETUP.md#2-checkout-and-checkpoint):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/huggingface.lock.txt
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait
```

The engine reads the checkpoint from each host's Hugging Face cache, by default `~/.cache/huggingface/hub`, mounted read-only into the container.

## 3. Image

Build on one of the GB10 hosts (linux/arm64), from the checkout root:

```sh
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.0.0 .
docker image inspect --format '{{.Id}}' glm53-tf3:3.0.0
```

The build compiles the engine from the BIZ release of TensorFold at the commit in [`config/engine.lock.json`](config/engine.lock.json) (`ENGINE_REF`), with the Zig compiler the lock names and checks by SHA-256, and builds `libtfgrammar` (structured output) from the xgrammar release the lock pins, checked by commit. The runtime image holds `tensorfold-native` and `tf-cuda-test` in `/usr/local/bin`, `libtfgrammar.so` in `/usr/local/lib`, NCCL 2.30.7 and the RDMA userspace, `serve.sh` in `/opt/glm53-tf3/`, and `/usr/share/doc/tf3/ENGINE`, which names the engine commit and every binary's SHA-256. Both base images are pinned by digest. The build took about 7 minutes on a reference host. Copy the image to the other hosts (`docker save glm53-tf3:3.0.0 | ssh <host> docker load`, over the link) and compare the image IDs of every host; they must be equal.

## 4. Container and rank file on each host

```sh
v3/scripts/create_container.sh glm53-tf3:3.0.0 ~/glm53-tf3   # container glm53-tf3, ~/glm53-tf3 at /work
cp v3/examples/tp3-rank0.env ~/glm53-tf3/rank.env             # this host's rank: tp2-rank0/1 or tp3-rank0/1/2
```

`create_container.sh` prints the cores it gives the container: unless `CPUSET` is set, the cores with the lowest maximum frequency, `cpuset 0-4,10-14` on a GB10, whose efficiency cores keep the CPU cooler while the engine's threads spin ([serving defaults](README.md#serving-defaults)). `CPUSET=` before it gives every core, and `CPUSET=<list>` the cores listed.

Edit `~/glm53-tf3/rank.env` with this host's values: `MASTER` (rank 0's address on the link, the same on every rank), `NCCL_IB_HCA` (the RDMA devices on the links, both rails), `NCCL_IB_GID_INDEX` and `NCCL_SOCKET_IFNAME`; at TP=2 also `NCCL_PORT` if 29583 is taken. The examples are the reference hosts' files and say what each line was measured as. The file is sourced by `bash`, not passed to `docker --env-file`. Lines the examples leave commented out change a default for every rank alike: `PARALLEL`, `CONTEXT`, the heat bands and `API_KEY_FILE` ([configuration](README.md#configuration)).

The engine needs no build step on the host: its kernels are in the binary.

## 5. Start

From a machine with SSH to every host, after copying [`examples/cluster.tp2.env`](examples/cluster.tp2.env) or [`cluster.tp3.env`](examples/cluster.tp3.env) to `state/cluster.env` (untracked, so your site's values stay out of Git) and setting `HOSTS` (SSH names in rank order), `CHECKOUT` (this repository on the hosts) and, if they differ from the defaults, `CONTAINER`, `WORK` and `SSH`:

```sh
v3/scripts/cluster.sh state/cluster.env start first
```

At TP=2 it starts the highest rank first and rank 0 last. At TP=3 it starts rank 0 first, waits for the NCCL id it writes to `/work/nccl-id` (256 hex characters), copies the file to the other hosts and then starts them. Each rank runs `serve.sh TP RANK /work/rank.env` in its container. It starts the memory guard on every host (`hostwatch.sh`: stops the engine below 5 GiB `MemAvailable`) and waits for rank 0's `[tensorfold] serving` line. It ends with `READY` and the seconds it took; with `FAILED` and every rank's log tail when a rank refuses, an engine is gone or rank 0 writes no id; or with `TIMEOUT` after 15 minutes. Each rank logs to `<WORK>/logs/serve-r<RANK>-<LABEL>.log` and the guard to `hostwatch-<LABEL>.log`; arguments after the label go to every rank's `tensorfold-native serve`, and `cluster.sh state/cluster.env status` counts each rank's engine processes. After `FAILED` or `TIMEOUT`, see [operations](docs/operations.md#start-outcomes).

Read each rank's startup lines:

- `[serve.sh]`: TP, rank, `MASTER`, the window (`context`: 245760 at TP=2, 1048576 at TP=3), `parallel` (1 unless the rank file sets another, `auto` for an empty `PARALLEL=`), the heat bands and the engine commit of the image
- rank 0's load line, `[tensorfold] CUDA sm_121 …`: the model's GiB, `1 stream at once` and its GiB at the window, the GiB left, and the prompt cache's GiB
- each rank's NCCL lines (`via NET/IB`, logged once at start by the rank file's `NCCL_DEBUG` lines) name `NET/IB` for every connection, none over sockets
- the `serving` line: the model name (`glm-tf` unless `MODEL_NAME` is set in the rank file), `127.0.0.1:8095` unless `HOST` and `PORT` are, and the window

Rank 0 serves the OpenAI-compatible API on loopback. A start took about 200 s at TP=3 and about 235 s at TP=2 on the reference hosts.

## 6. Tool-argument gate (optional)

The gate is 2.x's relay that checks each tool call's arguments against the tool's required fields and asks the model once more when one fails ([2.x step 7](../v2/SETUP.md#7-tool-argument-gate-optional)). It does not depend on the engine. On rank 0, from `v3/` with its virtual environment, or in the container from the checkout:

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

Clients that use tools then talk to port 8896.

## 7. Accept

Run the checks of [validation](docs/validation.md) in its order and compare them with its reference values before routine use. Let the hosts cool between long requests.

What 3.x is accepted for, image by image, is the README's [status](README.md#summary), and each item's evidence is in [measured on the release](README.md#measured-on-the-release); nothing outside that scope is qualified.

## 8. Stop

```sh
v3/scripts/cluster.sh state/cluster.env stop
```

It stops rank 0 first (the others leave when it does), then any rank left, and prints each host's engine-process count and `MemAvailable`; a count above 0 means that rank is still running. The containers stay; `docker stop glm53-tf3` frees their GPU claim. A rank that stops alone, a stop that leaves an engine and a new image are in [operations](docs/operations.md).
