#!/bin/bash
# On each host: create_container.sh IMAGE WORK_DIR
# A 3.x container as the 2.x one is run (v2/scripts/create_container.sh): host network and IPC, every GPU, the RDMA
# devices with locked memory unlimited, the Hugging Face cache read-only at /hub (HUB_RW=1: writable, for a build host
# that writes synthetic checkpoints there), and WORK_DIR at /work for the binaries, rank.env and logs. It sleeps until
# a rank is started in it. CONTAINER names it (default glm53-tf3); HF_HUB is the cache
# (default ~/.cache/huggingface/hub).
set -eu
if [ $# -lt 2 ]; then
  echo "usage: create_container.sh IMAGE WORK_DIR" >&2
  exit 2
fi
image=$1
work=$2
hub=${HF_HUB:-$HOME/.cache/huggingface/hub}
mode=ro
[ "${HUB_RW:-0}" = 1 ] && mode=rw
if [ ! -e /dev/infiniband ]; then
  echo "/dev/infiniband is missing: NCCL would fall back to sockets" >&2
  exit 1
fi
docker run -d --name "${CONTAINER:-glm53-tf3}" --net=host --ipc=host --gpus all --device /dev/infiniband \
  --cap-add IPC_LOCK --ulimit memlock=-1:-1 --shm-size 64m -v "$hub:/hub:$mode" -v "$work:/work" -w /work \
  "$image" sleep infinity
