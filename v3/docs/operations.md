# Operations (3.x)

[日本語](operations.ja.md) · [3.x overview](../README.md) · [Setup runbook](../SETUP.md) · [Validation](validation.md)

What to do when a 3.x launch goes wrong, and the routine changes around it: a new container, a new image, a host that powered off, a host that was moved, handing the hosts to 2.x or 1.x. Each section says what the scripts do and which cases the reference hosts met; a case they did not meet is marked as such. Commands run from the checkout root with the cluster file at `state/cluster.env` ([setup §5](../SETUP.md#5-start)), and like every command that changes a host, inside a window the operator has authorized.

## Start outcomes

`cluster.sh state/cluster.env start <label>` ends in one of these ways:

- **`READY after N s`** and rank 0's last eight `[tensorfold]` and `[serve.sh]` lines. Read the startup lines, and how long a start took on the reference hosts, in [setup §5](../SETUP.md#5-start).
- **`FAILED on rank R`**: a rank's log has a `REFUSE` line, or a rank's container runs no engine. The script prints the last 25 lines of every rank's log (without NCCL's `INFO` lines) and exits; it stops nothing. The other ranks and the memory guards may still be running, so run `cluster.sh state/cluster.env status`, then `stop`, before the next start.
- **`TIMEOUT`**: no `serving` line from rank 0 within 15 minutes. Read every rank's log, then `stop` as above.
- **Before any rank starts**: `HOSTS names N hosts for TP=T` (exit 2) when the cluster file's `HOSTS` does not name one host per rank, and `rank R HOST already runs an engine` (exit 1) when a host's container already runs one; stop it first.

Each rank logs to `<WORK>/logs/serve-r<RANK>-<LABEL>.log`, which a start with the same label overwrites; give every start its own label to keep the earlier logs. The memory guard appends to `hostwatch-<LABEL>.log`: the time and `MemAvailable` in GiB every 2 s, `check-failed` when a round's check failed or did not return in time, `KILLED` when it stopped the engine, `KILL-FAILED` when the stop failed or did not return in time (the next round stops it again while memory stays short), `done` when the engine or its container is gone.

The engine sizes its streams at start from the free memory and refuses a size that does not fit, naming the smallest room among the ranks, for example `--parallel 2 needs 4.55 GiB for its streams at a 245760-token window, and the CUDA memory budget leaves 4.41 GiB on rank 1, the smallest room of the ranks: serve --parallel 1, or lower --context` (TP=2, met on the reference pair with 3.0.0's engine). On GB10's unified memory the engine takes the free memory from `MemAvailable` in `/proc/meminfo`, which counts the page cache as free, so files cached by an earlier load do not take from that room: with 28 GiB of another checkpoint's files held in the page cache, a TP=2 start of 3.0.0 left 5.2 GiB, against 4.4 GiB with the cache dropped. The acceptance windows still dropped the Hugging Face cache's files from the page cache before each start (`os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)` on each file), a step kept from 2.x that the engine does not need.

At TP=3 the wire is set up and checked against NCCL at load, one gather byte for byte, and with `serve.sh`'s `TF_TP_ROCE_FALLBACK=error` a failure stops the start on every rank, its reason in the log. `TF_GLM_ROCE_MULTI=0` in every rank file serves without the wire; `TF_TP_ROCE_FALLBACK=nccl` starts without it and logs a warning on rank 0 ([configuration](configuration.md#rank-file)).

## A rank that stops

Two watchers stop one host's engine, each on its own host only:

- **The memory guard** (`hostwatch.sh`, started by `cluster.sh`) stops the engine with `pkill -9` inside the container when `MemAvailable` falls below 5 GiB, and writes `KILLED`.
- **The thermal watch** ([`host/thermal-watch`](../../host/README.md#during-long-runs), started by the operator with `--container glm53-tf3 --process 'tensorfold-native serve'`) stops it after two readings in a row at or above 94 °C, and writes `ABORT`.

Neither stopped an engine in the acceptance of any release that [measured on the release](../README.md#measured-on-the-release) or the [measurements of earlier releases](measurements.md) record. Under 2.x the other ranks did not end when one did: they waited in a collective until `cluster.sh stop` ended them. At 3.x they end too: a rank whose liveness line to rank 0 closes stops at once (read from the engine's source). After any rank stops, stop every rank, find the cause in the guard's or the watch's log, and start every rank again.

The engine's heat wait holds a prompt pass between chunks while any rank's hottest zone is above 92 °C, until every rank is at or below 88 °C ([serving defaults](../README.md#serving-defaults)). A wait has no time limit; rank 0's log gives each wait's seconds in a `heat_wait_s` line.

The thermal watch reads every ACPI zone, and five of a GB10's seven are the CPU's. The engine's spinning threads heat them through long runs of replies, which the heat wait does not hold; the container's default cores keep them lower ([why the efficiency cores](../README.md#serving-defaults)). A container created with every core moves to them with `docker update` ([recreate the container](#recreate-the-container)).

The host's own users of memory, swap and a peer that stops answering are in [host preparation](../../docs/hosts.md#swap-host-daemons-and-a-lost-peer). At 3.x each rank's liveness line to rank 0 notices a host that vanishes within about 20 s, also while no request runs, and every rank then stops; this is read from the engine's source, and the reference hosts did not meet it.

## A stop that leaves an engine

`cluster.sh state/cluster.env stop` sends `pkill -TERM -f 'tensorfold-native serve'` inside rank 0's container (the other ranks leave when rank 0 does), waits up to 60 s for each rank's engine to end and sends the same to a rank still running, then prints each host's engine-process count and `MemAvailable`. A count above 0 means that rank still runs: `docker exec glm53-tf3 pkill -9 -f 'tensorfold-native serve'`, or `docker stop glm53-tf3`, which ends every process in the container, then `status` again. Every stop in the 3.0.0, 3.1.0 and 3.8.0 acceptances ended with 0 on every rank.

## NCCL over sockets

The ranks must talk over RoCE, not TCP sockets:

- `create_container.sh` refuses a host without `/dev/infiniband`, where NCCL would fall back to sockets.
- The rank files' `NCCL_DEBUG=INFO` and `NCCL_DEBUG_SUBSYS=INIT,NET` make NCCL log each connection's transport once at start. `grep -c 'via NET/IB' <WORK>/logs/serve-r<RANK>-<LABEL>.log` counts them, and none may be `NET/Socket`.
- When a connection is not `NET/IB`, check the rank file against the host: `NCCL_IB_HCA`, `NCCL_IB_GID_INDEX` and `NCCL_SOCKET_IFNAME`, recorded in [setup §1](../SETUP.md#1-hosts-and-fabric). A GID index can move after a link drops or a host loses power ([a GID index that moves](../../docs/nccl-validation.md#a-gid-index-that-moves)).

Every start in the 3.0.0 to 3.3.0 acceptances ran every connection over `NET/IB`.

## Recreate the container

After `cluster.sh state/cluster.env stop`, on each host:

```sh
docker rm -f glm53-tf3                                  # the container only sleeps between starts
v3/scripts/create_container.sh glm53-tf3:3.12.0 ~/glm53-tf3
```

`create_container.sh` names the container, so the old one must go first (or be renamed: `docker rename glm53-tf3 glm53-tf3-old`, then `docker stop`). The host directory stays: the rank file and the logs. Nothing is built in the container.

It prints the container's cores ([setup §4](../SETUP.md#4-container-and-rank-file-on-each-host)); `docker inspect -f '{{.HostConfig.CpusetCpus}}' glm53-tf3` shows them later, empty for every core. Other cores need no new container: `docker update --cpuset-cpus 0-4,10-14 glm53-tf3` moves it, before the next start.

## Move to a new image

A new image is a new engine build: accept it again before routine use.

1. Build it on one host ([setup §3](../SETUP.md#3-image)). On every host, keep the image in use under a second tag first, so that going back is a container away.
2. Load it on the other hosts and compare the image IDs of every host; they must be equal. `/usr/share/doc/tf3/ENGINE` in each container names the engine commit and every binary's SHA-256.
3. If the release moves a TP size's default checkpoint (3.12.0 at TP=2, to Jammed XSFP4), download and verify it on every host first (`download --tp 2`, `verify-download --tp 2`), or add the old one's `CHECKPOINT` line to every rank file ([setup §2](../SETUP.md#2-checkout-and-checkpoint)); a start without either stops in `serve.sh`, naming the download.
4. Stop, then recreate the container on every host from the new image ([above](#recreate-the-container)).
5. Start, and run [validation](validation.md) from the decode check on. An image of the same engine commit must give the reference hashes. A release that moves the engine states in its validation which hashes change and why (3.1.0: TP=2 on upstream's tiled kernels; 3.3.0: TP=3 on them too, upstream 1.1.2); any other difference is a finding to explain, not a value to replace.

## A host that powered off

GB10 hosts can power off under sustained load ([GPU clock cap](../../docs/hosts.md#gpu-clock-cap)); the reference hosts did not under 3.x, so this section is the scripts' reading, not a recorded recovery. The clock cap, the heat wait, the cooling gate between long requests and the thermal watch are the prevention.

- The ranks on the other hosts stop within about 20 s, when their liveness lines notice the host gone ([a rank that stops](#a-rank-that-stops)); `cluster.sh state/cluster.env status` shows any still running.
- `create_container.sh` sets no restart policy, so after the host boots its container is not running: `docker start glm53-tf3`, or recreate it.
- Before starting, check the host as [host preparation](../../docs/hosts.md) says after an unclean restart, and its GID index.
- Start every rank together and run the decode check before routine use.

## A host that was moved

One reference host came back from a move on 2026-11-02 with its QSFP cable leaving and returning seconds after boot, and its NIC then sent at an eighth of the speed: 13 Gb/s where the same NIC gives 106. TP=2's prompts ran about a quarter slower and every hash stayed the same. Link speed, FEC, GID, PCIe width, retransmissions and the settings in sysfs read as on a healthy host, so comparing them finds nothing. This is one case, and its mechanism is not known.

- Plug the QSFP cables in before power-on. A reboot with the cable in brought that host back to 106 Gb/s.
- After moving a host or reseating a cable, and before measuring, have each active RDMA device write to itself. The traffic does not leave the NIC, so the number is this host's alone; a healthy NIC gives about 106 Gb/s:

  ```sh
  ib_write_bw -d DEVICE -x GID_INDEX -F --report_gbits -D 3 -s 1048576 &
  sleep 2; ib_write_bw -d DEVICE -x GID_INDEX -F --report_gbits -D 3 -s 1048576 127.0.0.1
  ```

  `ib_write_bw` is in Ubuntu's `perftest` package; `DEVICE` and `GID_INDEX` are the rank file's `NCCL_IB_HCA` and `NCCL_IB_GID_INDEX`, one device at a time.
- The kernel log of that boot showed the cable leave and return (`journalctl -k -b | grep cx7-pcie-hotplug`) and `mlx5_core` probe the NIC twice, where a healthy boot probes it once.

## Hand the hosts to 2.x

```sh
v3/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf3          # on every host
```

The 3.x and 2.x containers both claim every GPU; run one line's engine at a time. `docker start glm53-tf` and 2.x's `cluster.sh` give the hosts to 2.x ([2.x setup](../../v2/SETUP.md)); `docker start glm53-tf3` gives them back, with the same container and work directory.

## Hand the hosts to 1.x

```sh
v3/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf3          # on every host
```

A stopped engine is not enough. The container was created with every GPU, and 1.x's `server preflight` refuses a launch while another running container requests a GPU (`exclusive_gpu`), as it refused on 2026-10-04 while 2.x's containers only slept, with no GPU process ([1.x launch checks](../../v1/docs/operations.md#full-model-launch-checks)). 1.x's [setup](../../v1/SETUP.md) then starts its server; stop it before `docker start glm53-tf3` gives the hosts back, with the same container and work directory ([requirements](../README.md#requirements)).
