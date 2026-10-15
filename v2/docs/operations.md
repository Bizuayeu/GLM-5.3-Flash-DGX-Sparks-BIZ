# Operations (2.x)

[日本語](operations.ja.md) · [2.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Validation](validation.md)

What to do when a 2.x launch goes wrong, and the routine changes around it: a new container, a new image, a host that powered off, handing the hosts to 1.x. Each section says what the scripts do and which cases the reference hosts met; a case they did not meet is marked as such. Commands run from the checkout root with the cluster file at `state/cluster.env` ([setup §6](../SETUP.md#6-start)), and like every command that changes a host, inside a window the operator has authorized.

## Start outcomes

`cluster.sh state/cluster.env start <label>` ends in one of three ways:

- **`READY after N s`** and rank 0's last eight `[tensorfold]` lines. Read the startup lines, and how long a start took on the reference hosts, in [setup §6](../SETUP.md#6-start).
- **`FAILED on rank R`**: a rank's log has a `Traceback`, or a rank's container runs no engine. The script prints the last 25 lines of every rank's log and exits; it stops nothing. The other ranks and the memory guards may still be running, so run `cluster.sh state/cluster.env status`, then `stop`, before the next start.
- **`TIMEOUT`**: no `serving` line from rank 0 within 15 minutes. Read every rank's log, then `stop` as above.

Each rank logs to `~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log`, which a start with the same label overwrites; give every start its own label to keep the earlier logs. The memory guard appends to `hostwatch-<LABEL>.log`: the time and `MemAvailable` in GiB every 2 s, `KILLED` when it stopped the engine, `done` when the engine is gone.

A start can also stop at once with `CUDA startup memory budget cannot fit requested context 300000`, right after a new image was loaded or another engine read the weights. On GB10's unified memory the free memory CUDA reports leaves the page cache out, and the cached weights take the window's margin (on 2026-10-06, 9 GiB of cache left 108.8 GiB free and the TP=2 window did not fit). Ask the kernel to drop the cache of the Hugging Face cache's files on every host (`os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)` on each file; no root needed), then start again; `python3 -c "import torch; print(torch.cuda.mem_get_info())"` in the container shows the free memory the start will see.

Which weights serve is the rank file's `CHECKPOINT`: the pinned snapshot unless it is set, the published AXL weights' snapshot as the option ([configuration](../README.md#configuration)). To change them, stop, set the same `CHECKPOINT` in every rank's file and start again; ranks started on different checkpoints refuse to start.

## A rank stops and the others wait

Two watchers stop one host's engine, each on its own host only:

- **The memory guard** (`hostwatch.sh`, started by `cluster.sh`) stops the engine with `pkill -9` inside the container when `MemAvailable` falls below 5 GiB, and writes `KILLED`.
- **The thermal watch** ([`host/thermal-watch`](../../host/README.md#during-long-runs), started by the operator) stops it after two readings in a row at or above 94 °C, and writes `ABORT`.

The other ranks do not end with it. On 2026-10-04 a thermal watch with the same rule stopped rank 0 six and a half minutes into a 1M-token prefill at TP=3, on an engine without the heat wait. Ranks 1 and 2 logged nothing more: they waited in a collective, and their memory guards kept running, until `cluster.sh state/cluster.env stop` ended them. After any rank stops, stop every rank, find the cause in the guard's or the watch's log, and start every rank again; the records always restarted all ranks together, and starting one rank alone was not tried.

The memory guard never stopped a serving engine on the reference hosts; the lowest `MemAvailable` they reached is in [validation](validation.md#memory-and-temperature). Its way of stopping was verified on a root process in a container: a `pkill` from the host user fails on it with "Operation not permitted" and still returns 0, which is why the guard goes through `docker exec`.

The engine's own heat wait keeps a long prefill below the thermal watch's two readings in a row at 94 °C ([serving defaults](../README.md#serving-defaults)); near the end of a 1M-token prompt a chunk adds about 7 °C after the check between chunks, so the wait also looks one chunk ahead and holds the next reading within 93 °C as far as the last chunk's rise predicts it (in 2.4.0's acceptance a chunk after one with almost no rise passed it once, and the next check started a wait; [measured on the release](../README.md#measured-on-the-release)). A wait has no time limit: once it starts, the request waits until every host is at or below the lower band, and every rank prints `[tensorfold] heat: waiting <s> s, hottest zone <°C> C` once a minute while it lasts. Those lines mean the room is hot, not that the engine hangs.

## A stop that leaves an engine

`cluster.sh state/cluster.env stop` sends `pkill -f 'tensorfold serve'` inside each container, rank 0 first, waits up to 60 s for each rank's engine to end, and then prints each host's engine-process count and `MemAvailable`. A count above 0 means that rank still runs. `MemAvailable` read right after a stop can be low while the memory is still being freed: 16 GiB right after one stop on the reference pair, 117 GiB 20 s later.

Every stop in the reference records ended with 0 on every rank, so the next steps were never needed there. They would be, on the host whose count stays above 0: the guard's form, `docker exec glm53-tf pkill -9 -f 'tensorfold serve'`, or `docker stop glm53-tf`, which ends every process in the container. Then `cluster.sh state/cluster.env status` again.

## NCCL over sockets

The ranks must talk over RoCE, not TCP sockets:

- `create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets.
- The rank files' `NCCL_DEBUG=INFO` and `NCCL_DEBUG_SUBSYS=INIT,NET` make NCCL log each connection's transport once at start. `grep 'via NET' ~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log` lists them; each must name `NET/IB`. At TP=2 the lines name both rails, `NET/IB/0` and `NET/IB/1`, in equal numbers; with one rail named, check `NCCL_IB_HCA`.
- When a connection is not `NET/IB`, check the rank file against the host: `NCCL_IB_HCA` (the RDMA devices on the links, both rails), `NCCL_IB_GID_INDEX` (the RoCE v2 entry on the link's IPv4 address) and `NCCL_SOCKET_IFNAME` (the interface the ranks meet on), recorded in [setup §1](../SETUP.md#1-hosts-and-fabric). A GID index can move after a link drops or a host loses power ([a GID index that moves](../../docs/nccl-validation.md#a-gid-index-that-moves)). The [NCCL diagnostic](../../docs/nccl-validation.md) tests the fabric without the engine.

Every recorded 2.x start ran every connection over `NET/IB`.

## Recreate the container

After `cluster.sh state/cluster.env stop`, on each host:

```sh
docker rm -f glm53-tf                                  # the container only sleeps between starts
v2/scripts/create_container.sh glm53-tf:2.9.1
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh
```

`create_container.sh` names the container, so the old one must go first. The host directory `~/glm53-tf` stays: the rank file, the compiled extensions (`ext/`) and the logs. `build_ext.sh` builds the extensions that are missing for the image and finds the others already built; run it before every first start in a new container.

## Move to a new image

A new image is a new engine build: accept it again before routine use.

1. Build it on one host ([setup §3](../SETUP.md#3-image)). On every host, keep the image in use under a second tag first (`docker tag glm53-tf:<current> glm53-tf:<current>-<engine>`, as the records did), so that going back is a container away.
2. Load it on the other hosts and compare the image IDs of every host; they must be equal. The ID that `docker images` shows also covers the build's provenance and changes with each checkout the image is built from ([changelog 2.0.0](../CHANGELOG.md)).
3. Stop, then recreate the container on every host from the new image and run `build_ext.sh` ([above](#recreate-the-container)). For each new engine on the reference hosts it rebuilt all seven extensions, about 155-160 s a host.
4. Start, and run [validation](validation.md) from the decode check on. A new engine must give the reference hashes; one that does not is a finding to explain, not a value to replace.

To go back, recreate the containers from the kept tag.

## A host that powered off

GB10 hosts can power off under sustained load ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)); the reference hosts did not under 2.x, so this section is the scripts' reading, not a recorded recovery. The clock cap, the cooling gate between long requests and the thermal watch ([host tools](../../host/README.md#during-long-runs)) are the prevention.

- The ranks on the other hosts wait in a collective, as above: stop them.
- `create_container.sh` sets no restart policy, so after the host boots its `glm53-tf` container is not running: `docker start glm53-tf`, or recreate it.
- Before starting, check the host as [host preparation](../../docs/hosts.md) says after an unclean restart (loaded clocks and power) and its GID index ([a GID index that moves](../../docs/nccl-validation.md#a-gid-index-that-moves)); the reference pair's peer moved one rail's index after its head lost power under 1.x.
- Start every rank together and run the decode check before routine use.

## Hand the hosts to 1.x

```sh
v2/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf          # on every host
```

A stopped engine is not enough. The container was created with every GPU, and 1.x's `server preflight` refuses a launch while another running container requests a GPU: on 2026-10-04 it refused with `exclusive_gpu` false while `glm53-tf` containers that only slept, with no GPU process, ran on the hosts ([1.x launch checks](../../v1/docs/operations.md#full-model-launch-checks)). `docker start glm53-tf` gives the hosts back to 2.x, with the same container and `~/glm53-tf`; stop the 1.x server first, as the [requirements](../README.md#requirements) say.
