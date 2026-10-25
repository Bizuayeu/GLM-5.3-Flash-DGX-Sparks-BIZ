#!/bin/bash
# Inside the container, on every rank: serve.sh TP RANK RANK_ENV [more `tensorfold-native serve` arguments]
# The 3.x serving defaults: the MTP head's drafts (the engine's default), replies of up to 32,768 tokens when a request
# names no limit, high reasoning effort, and the window by TP: 524,288 tokens at TP=2, one stream and a prompt cache
# beside XSFP4, and 1,048,576 at TP=3, the model's limit; one stream (PARALLEL=1). An empty PARALLEL leaves it to the
# engine, which sizes the streams and the prompt cache from the memory free at start, so they can differ between
# starts. CONTEXT in the rank file sets another window, every rank the same.
# RANK_ENV is this host's file (examples/tp*-rank*.env): its NCCL settings and MASTER, rank 0's address on the link
# between the hosts (at TP=3, whose hosts are linked point to point, a /32 address the ring's routes reach). Rank 0
# makes its NCCL id at NCCL_COMM_ID (MASTER:NCCL_PORT), and the ranks' liveness lines meet it at the next port; the
# other ranks take the id over their lines, and where the rank file names NCCL_SOCKET_IFNAME, as every example's
# does, the engine drops NCCL_COMM_ID before NCCL's first call, so NCCL's bootstrap uses that interface (#1178).
# A prefill waits between chunks while any rank's hottest zone is above TF_HEAT_HIGH (92), until all are at or below
# TF_HEAT_LOW (88). The rank file may set other values, the same on every rank, or empty ones for none (an empty
# value is left unset: the engine refuses one). Without the bands a 1M prefill held one host at 94-97.7 C.
set -eu
if [ $# -lt 3 ]; then
  echo "usage: serve.sh TP RANK RANK_ENV [tensorfold-native serve arguments...]" >&2
  exit 2
fi
tp=$1 rank=$2 rank_env=$3
shift 3
case $tp in
  2 | 3) ;;
  *) echo "TP is 2 or 3, not '$tp'" >&2; exit 2 ;;
esac
case $rank in
  [0-2]) [ "$rank" -lt "$tp" ] || { echo "rank $rank is outside TP=$tp" >&2; exit 2; } ;;
  *) echo "rank is 0, 1 or 2, not '$rank'" >&2; exit 2 ;;
esac
set -a
. "$rank_env"
set +a
: "${MASTER:?$rank_env must set MASTER, rank 0 address on the link between the hosts}"
export TF_GLM_RANK=$rank TF_GLM_WORLD=$tp
export NCCL_COMM_ID="$MASTER:${NCCL_PORT:-29583}"
if [ "$tp" = 2 ]; then
  context=${CONTEXT:-524288}
else
  context=${CONTEXT:-1048576}
fi
TF_HEAT_HIGH=${TF_HEAT_HIGH-92} TF_HEAT_LOW=${TF_HEAT_LOW-88}
for v in TF_HEAT_HIGH TF_HEAT_LOW; do
  if [ -n "${!v}" ]; then export "$v"; else unset "$v"; fi
done
# XSFP4 at its lock's revision (config/xsfp4.lock.json) as the Hugging Face cache holds it, mounted read-only at /hub
# (create_container.sh); CHECKPOINT in the rank files names another folder (3.x's acceptance covers XSFP4 alone)
CHECKPOINT=${CHECKPOINT:-/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/88736f916f8939607fde8a4b881dcae749f7551d}
# Every rank takes the same arguments (the ranks compare their settings at start); only rank 0 serves HTTP.
# REASONING_EFFORT: what a request that names none gets (default high; empty: the chat template's own).
# PARALLEL: how many requests share the rounds (default 1; empty: the engine's auto). API_KEY_FILE: serving beyond
# loopback, requests without the key are refused.
args=(--name "${MODEL_NAME:-glm-tf}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8095}")
args+=(--context "$context" --max-tokens 32768 --no-update-check)
effort=${REASONING_EFFORT-high}
[ -n "$effort" ] && args+=(--reasoning-effort "$effort")
parallel=${PARALLEL-1}
[ -n "$parallel" ] && args+=(--parallel "$parallel")
[ -n "${API_KEY_FILE:-}" ] && args+=(--api-key-file "$API_KEY_FILE")
# VISION: image and video parts (default 1: the checkpoint's tower on rank 0, PNG, JPEG and WebP data URLs, videos;
# empty: text alone), every rank the same
vision=${VISION-1}
[ -n "$vision" ] && args+=(--vision)
echo "[serve.sh] $(date -Is) TP=$tp rank $rank master $MASTER context $context parallel ${parallel:-auto}" \
  "vision ${vision:-off}" \
  "heat ${TF_HEAT_HIGH:-unset}/${TF_HEAT_LOW:-unset}" \
  "engine $(sed -n 's/^ref //p' /usr/share/doc/tf3/ENGINE 2>/dev/null || echo '?')" "TF_GLM_MM ${TF_GLM_MM-unset}"
exec tensorfold-native serve "$CHECKPOINT" "${args[@]}" "$@"
