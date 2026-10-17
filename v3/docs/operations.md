# Operations (3.x)

[日本語](operations.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Validation](validation.md)

What to do when a 3.x launch goes wrong, and the routine changes around it: a new container, a new image, a host that powered off, handing the hosts to 2.x. Each section says what the scripts do and which cases the reference hosts met; a case they did not meet is marked as such. Commands run from the checkout root with the cluster file at `state/cluster.env` ([setup §5](../SETUP.md#5-start)), and like every command that changes a host, inside a window the operator has authorized.

## Start outcomes

`cluster.sh state/cluster.env start <label>` ends in one of these ways:

- **`READY after N s`** and rank 0's last eight `[tensorfold]` and `[serve.sh]` lines. Read the startup lines, and how long a start took on the reference hosts, in [setup §5](../SETUP.md#5-start).
- **`FAILED on rank R`**: a rank's log has a `REFUSE` line, or a rank's container runs no engine. The script prints the last 25 lines of every rank's log (without NCCL's `INFO` lines) and exits; it stops nothing. The other ranks and the memory guards may still be running, so run `cluster.sh state/cluster.env status`, then `stop`, before the next start.
- **`FAILED: rank 0 wrote no NCCL id`** (TP=3): rank 0 did not write `/work/nccl-id` within 2 minutes, or its engine ended first. Read rank 0's log.
- **`TIMEOUT`**: no `serving` line from rank 0 within 15 minutes. Read every rank's log, then `stop` as above.

Each rank logs to `<WORK>/logs/serve-r<RANK>-<LABEL>.log`, which a start with the same label overwrites; give every start its own label to keep the earlier logs. The memory guard appends to `hostwatch-<LABEL>.log`: the time and `MemAvailable` in GiB every 2 s, `KILLED` when it stopped the engine, `done` when the engine is gone.

The engine sizes its streams at start from the memory CUDA reports free and refuses a size that does not fit, naming the smallest room among the ranks, for example `--parallel 2 needs 4.55 GiB for its streams at a 245760-token window, and the CUDA memory budget leaves 4.41 GiB on rank 1, the smallest room of the ranks: serve --parallel 1, or lower --context` (TP=2, met on the reference pair). On GB10's unified memory the free memory leaves the page cache out, so weights cached by an earlier load take from that room; the acceptance dropped the Hugging Face cache's files from the page cache on every host before each start (`os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)` on each file; no root needed).

## A rank stops and the others wait

Two watchers stop one host's engine, each on its own host only:

- **The memory guard** (`hostwatch.sh`, started by `cluster.sh`) stops the engine with `pkill -9` inside the container when `MemAvailable` falls below 5 GiB, and writes `KILLED`.
- **The thermal watch** ([`host/thermal-watch`](../../host/README.md#during-long-runs), started by the operator with `--container glm53-tf3 --process 'tensorfold-native serve'`) stops it after two readings in a row at or above 94 °C, and writes `ABORT`.

Neither stopped an engine in the 3.0.0 acceptance. Under 2.x the other ranks did not end when one did: they waited in a collective until `cluster.sh stop` ended them. After any rank stops, stop every rank, find the cause in the guard's or the watch's log, and start every rank again.

The engine's heat wait holds a prompt pass between chunks while any rank's hottest zone is above 92 °C, or would pass 93 °C if the next chunk rose as much as the last one run straight after another, until every rank is at or below 88 °C ([serving defaults](../README.md#serving-defaults)). A wait has no time limit; rank 0's log gives each wait's seconds in a `heat_wait_s` line.

## A stop that leaves an engine

`cluster.sh state/cluster.env stop` sends `pkill -TERM -f 'tensorfold-native serve'` inside rank 0's container (the other ranks leave when rank 0 does), waits up to 60 s for each rank's engine to end and sends the same to a rank still running, then prints each host's engine-process count and `MemAvailable`. A count above 0 means that rank still runs: `docker exec glm53-tf3 pkill -9 -f 'tensorfold-native serve'`, or `docker stop glm53-tf3`, which ends every process in the container, then `status` again. Every stop in the 3.0.0 acceptance ended with 0 on every rank.

## NCCL over sockets

The ranks must talk over RoCE, not TCP sockets:

- `create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets.
- The rank files' `NCCL_DEBUG=INFO` and `NCCL_DEBUG_SUBSYS=INIT,NET` make NCCL log each connection's transport once at start. `grep -c 'via NET/IB' <WORK>/logs/serve-r<RANK>-<LABEL>.log` counts them, and none may be `NET/Socket`.
- When a connection is not `NET/IB`, check the rank file against the host: `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX` and `NCCL_SOCKET_IFNAME`, recorded in [setup §1](../SETUP.md#1-hosts-and-fabric). A GID index can move after a link drops or a host loses power ([a GID index that moves](../../docs/nccl-validation.md#a-gid-index-that-moves)).

Every start in the 3.0.0 acceptance ran every connection over `NET/IB`.

## Recreate the container

After `cluster.sh state/cluster.env stop`, on each host:

```sh
docker rm -f glm53-tf3                                  # the container only sleeps between starts
v3/scripts/create_container.sh glm53-tf3:3.0.0 ~/glm53-tf3
```

`create_container.sh` names the container, so the old one must go first (or be renamed: `docker rename glm53-tf3 glm53-tf3-old`, then `docker stop`). The host directory stays: the rank file and the logs. Nothing is built in the container.

## Move to a new image

A new image is a new engine build: accept it again before routine use.

1. Build it on one host ([setup §3](../SETUP.md#3-image)). On every host, keep the image in use under a second tag first, so that going back is a container away.
2. Load it on the other hosts and compare the image IDs of every host; they must be equal. `/usr/share/doc/tf3/ENGINE` in each container names the engine commit and every binary's SHA-256.
3. Stop, then recreate the container on every host from the new image ([above](#recreate-the-container)).
4. Start, and run [validation](validation.md) from the decode check on. A new engine must give the reference hashes; one that does not is a finding to explain, not a value to replace.

## A host that powered off

GB10 hosts can power off under sustained load ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)); the reference hosts did not under 3.x, so this section is the scripts' reading, not a recorded recovery. The clock cap, the heat wait, the cooling gate between long requests and the thermal watch are the prevention.

- The ranks on the other hosts wait in a collective: stop them.
- `create_container.sh` sets no restart policy, so after the host boots its container is not running: `docker start glm53-tf3`, or recreate it.
- Before starting, check the host as [host preparation](../../docs/hosts.md) says after an unclean restart, and its GID index.
- Start every rank together and run the decode check before routine use.

## Hand the hosts to 2.x

```sh
v3/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf3          # on every host
```

The 3.x and 2.x containers both claim every GPU; run one line's engine at a time. `docker start glm53-tf` and 2.x's `cluster.sh` give the hosts to 2.x ([2.x setup](../../v2/SETUP.md)); `docker start glm53-tf3` gives them back, with the same container and work directory.
