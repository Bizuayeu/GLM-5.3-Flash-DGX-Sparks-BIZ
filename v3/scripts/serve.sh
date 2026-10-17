#!/bin/bash
# Inside the container, on every rank: serve.sh TP RANK RANK_ENV [more `tensorfold-native serve` arguments]
# The 3.x serving defaults: the MTP head's drafts (the engine's default), replies of up to 32,768 tokens when a request
# names no limit, high reasoning effort, and the window by TP: 245,760 tokens at TP=2 and 1,048,576 at TP=3, about the
# largest one stream fits (measured), one stream (PARALLEL=1). An empty PARALLEL leaves it to the engine, which sizes
# the streams and the prompt cache from the memory free at start, so they can differ between starts. CONTEXT in the
# rank file sets another window, every rank the same.
# RANK_ENV is this host's file (examples/tp*-rank*.env): its NCCL settings and MASTER, rank 0's address on the link
# between the hosts. TP=2 meets at MASTER:NCCL_PORT (NCCL_COMM_ID). TP=3's hosts are linked point to point with /32
# addresses, where NCCL_COMM_ID cannot bootstrap, so rank 0 writes its NCCL id to ID_FILE and the other ranks read it
# there (TF_GLM_NCCL_ID_FILE, the fork's commit until upstream's TP bootstrap): rank 0 starts first and the file is
# copied to the other hosts before their ranks start. cluster.sh does both orders.
# A prefill waits between chunks while any rank's hottest zone is above TF_HEAT_HIGH (92), or would pass
# TF_HEAT_CEILING (93) if the next chunk rose as much as the last one run straight after another, until all are at or
# below TF_HEAT_LOW (88). The rank file may set other values, the same on every rank, or empty ones for none (an empty
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
if [ "$tp" = 2 ]; then
  context=${CONTEXT:-245760}   # cc-defer: measured once at S3 (10-17); the acceptance measurement (Z6, G9) sets it
  export NCCL_COMM_ID="$MASTER:${NCCL_PORT:-29583}"
  unset TF_GLM_NCCL_ID_FILE
else
  context=${CONTEXT:-1048576}
  unset NCCL_COMM_ID
  export TF_GLM_NCCL_ID_FILE=${ID_FILE:-/work/nccl-id}
fi
TF_HEAT_HIGH=${TF_HEAT_HIGH-92} TF_HEAT_LOW=${TF_HEAT_LOW-88}
if [ -n "$TF_HEAT_HIGH" ] && [ -n "$TF_HEAT_LOW" ]; then
  TF_HEAT_CEILING=${TF_HEAT_CEILING-93}
else
  TF_HEAT_CEILING=${TF_HEAT_CEILING-}   # a ceiling comes only with both bands
fi
for v in TF_HEAT_HIGH TF_HEAT_LOW TF_HEAT_CEILING; do
  if [ -n "${!v}" ]; then export "$v"; else unset "$v"; fi
done
# The pinned checkpoint as the Hugging Face cache holds it, mounted read-only at /hub (create_container.sh)
CHECKPOINT=${CHECKPOINT:-/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93}
# Every rank takes the same arguments (the ranks compare their settings at start); only rank 0 serves HTTP.
# REASONING_EFFORT: what a request that names none gets (default high; empty: the chat template's own).
# PARALLEL: how many requests share the rounds (default 1; empty: the engine's auto). API_KEY_FILE: serving beyond
# loopback, requests without the key are refused.
args=(--name "${MODEL_NAME:-glm-tf}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8095}")
args+=(--context "$context" --max-tokens 32768 --no-update-check)
[ -n "${REASONING_EFFORT-high}" ] && args+=(--reasoning-effort "${REASONING_EFFORT-high}")
parallel=${PARALLEL-1}
[ -n "$parallel" ] && args+=(--parallel "$parallel")
[ -n "${API_KEY_FILE:-}" ] && args+=(--api-key-file "$API_KEY_FILE")
echo "[serve.sh] $(date -Is) TP=$tp rank $rank master $MASTER context $context parallel ${parallel:-auto}" \
  "heat ${TF_HEAT_HIGH:-unset}/${TF_HEAT_LOW:-unset}/${TF_HEAT_CEILING:-unset}" \
  "engine $(sed -n 's/^ref //p' /usr/share/doc/tf3/ENGINE 2>/dev/null || echo '?')"
exec tensorfold-native serve "$CHECKPOINT" "${args[@]}" "$@"
