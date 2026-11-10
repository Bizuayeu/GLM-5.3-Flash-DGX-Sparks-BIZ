#!/bin/bash
# Inside the container, on every rank: serve.sh TP RANK RANK_ENV [more `tensorfold-native serve` arguments]
# The 3.x serving defaults: the MTP head's drafts (the engine's default), replies of up to 32,768 tokens when a request
# names no limit, high reasoning effort, and what differs by TP from the release's tp2.env, tp3.env and tp4.env, which
# sit beside this script: the window, the streams, the kept prompts, a prompt's share beside a decode, the solo passes,
# the drafts' confidence, the wire and the memory reserve. The rank file follows them, so its value wins, every rank the
# same. An empty value turns a number or word setting off; the on/off settings (VISION, TF_GLM_ROCE_MULTI,
# TF_GLM_PROMPT_PAIR, TF_GLM_L2PF) take 1 or 0, and another value, an empty one included, stops the start. An empty
# PARALLEL leaves the streams to the engine, which sizes them and the prompt cache from the memory free at start, so
# they can differ between starts; an empty CONTEXT keeps the release's window.
# RANK_ENV is this host's file (examples/tp*-rank*.env): its NCCL settings and MASTER, rank 0's address on the link
# between the hosts (at TP=3 and TP=4, where the hosts form a ring, a /32 address the ring's routes reach). Rank 0
# makes its NCCL id at NCCL_COMM_ID (MASTER:NCCL_PORT), and the ranks' liveness lines meet it at the next port; the
# other ranks take the id over their lines, and where the rank file names NCCL_SOCKET_IFNAME, as every example's
# does, the engine drops NCCL_COMM_ID before NCCL's first call, so NCCL's bootstrap uses that interface (#1178).
# A prefill waits between chunks while any rank's hottest zone is above TF_HEAT_HIGH (92), until all are at or below
# TF_HEAT_LOW (88). The rank file may set other values, the same on every rank, or empty ones for none (from upstream
# 1.2.6 the engine reads an empty value as unset). Without the bands a 1M prefill held one host at 94-97.7 C.
set -eu
if [ $# -lt 3 ]; then
  echo "usage: serve.sh TP RANK RANK_ENV [tensorfold-native serve arguments...]" >&2
  exit 2
fi
tp=$1 rank=$2 rank_env=$3
shift 3
case $tp in
  2 | 3 | 4) ;;
  *) echo "TP is 2, 3 or 4, not '$tp'" >&2; exit 2 ;;
esac
case $rank in
  [0-3]) [ "$rank" -lt "$tp" ] || { echo "rank $rank is outside TP=$tp" >&2; exit 2; } ;;
  *) echo "rank is 0, 1, 2 or 3, not '$rank'" >&2; exit 2 ;;
esac
set -a
. "$(dirname "$0")/tp$tp.env"
release_context=$CONTEXT
. "$rank_env"
set +a
: "${MASTER:?$rank_env must set MASTER, rank 0 address on the link between the hosts}"
# The on/off settings take 1 or 0, as the engine's own switches do: an empty value or a word would otherwise be read as
# one of them unseen (VISION= turned images off and VISION=0 turned them on)
for v in VISION TF_GLM_ROCE_MULTI TF_GLM_PROMPT_PAIR TF_GLM_L2PF; do
  [ -n "${!v+x}" ] || continue
  case ${!v} in
    0 | 1) ;;
    '') echo "$v: 0 or 1; an empty value no longer turns it off, so write $v=0" >&2; exit 2 ;;
    *) echo "$v: 0 or 1, not '${!v}'" >&2; exit 2 ;;
  esac
done
export TF_GLM_RANK=$rank TF_GLM_WORLD=$tp
export NCCL_COMM_ID="$MASTER:${NCCL_PORT:-29583}"
context=${CONTEXT:-$release_context}
export TF_HEAT_HIGH=${TF_HEAT_HIGH-92} TF_HEAT_LOW=${TF_HEAT_LOW-88}
# The wire takes the main stream's small all-gathers to the engine's multirank RoCE, beside NCCL. It needs rank 0's
# address and the mailbox kernels, and a failed setup or probe stops the start rather than falling back to NCCL unseen.
if [ "${TF_GLM_ROCE_MULTI:-0}" != 0 ]; then
  export TF_TP_MASTER=${TF_TP_MASTER:-$MASTER} TF_TP_PORT=${TF_TP_PORT:-29640} TF_TP_PLAN_TIMEOUT=${TF_TP_PLAN_TIMEOUT:-900}
  export TF_TP_KERNEL_IMAGE=${TF_TP_KERNEL_IMAGE:-$(dirname "$0")/tp_mailbox.fatbin}
  export TF_TP_ROCE_FALLBACK=${TF_TP_ROCE_FALLBACK:-error}
fi
# XSFP4 at its lock's revision (config/xsfp4.lock.json) as the Hugging Face cache holds it, mounted read-only at /hub
# (create_container.sh). CHECKPOINT in the rank files names another folder: Jammed XSFP4's at its lock's revision
# (config/jammed.lock.json), the one other checkpoint 3.x's acceptance covers
CHECKPOINT=${CHECKPOINT:-/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/88736f916f8939607fde8a4b881dcae749f7551d}
# Every rank takes the same arguments (the ranks compare their settings at start); only rank 0 serves HTTP.
# REASONING_EFFORT: what a request that names none gets (default high; empty: the chat template's own).
# PARALLEL: how many requests share the rounds (empty: the engine's auto). MTP_CONFIDENCE: the drafts' confidence
# (empty: none). API_KEY_FILE: serving beyond loopback, requests without the key are refused.
args=(--name "${MODEL_NAME:-glm-tf}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8095}")
args+=(--context "$context" --max-tokens 32768 --no-update-check)
effort=${REASONING_EFFORT-high}
[ -n "$effort" ] && args+=(--reasoning-effort "$effort")
parallel=${PARALLEL-}
[ -n "$parallel" ] && args+=(--parallel "$parallel")
[ -n "${MTP_CONFIDENCE:-}" ] && args+=(--mtp-confidence "$MTP_CONFIDENCE")
[ -n "${API_KEY_FILE:-}" ] && args+=(--api-key-file "$API_KEY_FILE")
# VISION: image and video parts (default 1: the checkpoint's tower on rank 0, PNG, JPEG and WebP data URLs, videos;
# 0: text alone), every rank the same
vision=${VISION-1}
[ "$vision" = 1 ] && args+=(--vision)
echo "[serve.sh] $(date -Is) TP=$tp rank $rank master $MASTER context $context parallel ${parallel:-auto}" \
  "kept ${TF_KV_SHARE:-unset} prefill-share ${TENSORFOLD_PREFILL_SHARE:-unset} solo ${TF_GLM_CHUNK_SOLO:-unset}" \
  "mtp-confidence ${MTP_CONFIDENCE:-unset} wire ${TF_GLM_ROCE_MULTI:-unset}" \
  "reserve ${TENSORFOLD_MEMORY_RESERVE_GIB:-unset} vision $vision" \
  "heat ${TF_HEAT_HIGH:-unset}/${TF_HEAT_LOW:-unset}" \
  "engine $(sed -n 's/^ref //p' /usr/share/doc/tf3/ENGINE 2>/dev/null || echo '?')" "TF_GLM_MM ${TF_GLM_MM-unset}"
exec tensorfold-native serve "$CHECKPOINT" "${args[@]}" "$@"
