#!/bin/bash
# Inside the container, on every rank: serve.sh TP RANK RANK_ENV [more `tensorfold serve` arguments]
# The 2.x serving defaults (README.md#serving-defaults): FP8 latent KV, MTP drafts, replies of up to 32,768 tokens
# when a request names no limit, and the window by TP: 300,000 tokens at TP=2, the largest that fits at TP=3
# (--context 0; 1,048,576 on the reference ring). The prefill exchange takes the engine's default (split).
# A prefill waits between chunks while any rank's hottest ACPI zone is above 92 C, or would pass 93 C if the next
# chunk rose as much as the last one run straight after another, until all are at or below 88 C and the larger
# of that rise and the last chunk's own would stay within 93 C
# (TF_GLM_HEAT_HIGH/LOW/CEILING; the rank file may set other values, the same on every rank, or empty ones for none).
# A request that names no reasoning effort gets high (REASONING_EFFORT in rank 0's file).
# RANK_ENV is this host's file (examples/tp*-rank*.env): its NCCL settings and MASTER, rank 0's address on the link
# between the hosts. Start the other ranks first and rank 0 last (cluster.sh does).
set -eu
if [ $# -lt 3 ]; then
  echo "usage: serve.sh TP RANK RANK_ENV [tensorfold serve arguments...]" >&2
  exit 2
fi
tp=$1 rank=$2 rank_env=$3
shift 3
case $tp in
  2) context=300000 ;;
  3) context=0 ;;
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
export TF_GLM_KV=fp8
# 94 C is where the hosts' thermal watch stops the engine; 88 C sits below the 88.8-89.6 C a 1M prefill held
# at TP=3 before the faster prefill work. Near the end of a 1M prefill one chunk adds about 7 C after the check
# between chunks, so the wait also looks one chunk ahead, by the rise of the last chunk run straight after
# another (a chunk begun after a rest also climbs back the few seconds' cooling; README.md).
export TF_GLM_HEAT_HIGH=${TF_GLM_HEAT_HIGH-92} TF_GLM_HEAT_LOW=${TF_GLM_HEAT_LOW-88}
export TF_GLM_HEAT_CEILING=${TF_GLM_HEAT_CEILING-93}
# The pinned checkpoint as the Hugging Face cache holds it, mounted read-only at /hub (create_container.sh)
CHECKPOINT=${CHECKPOINT:-/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93}
# VISION=1 in the rank file: image input (--vision; rank 0 holds the image tower), the same on every rank
vision=()
if [ "${VISION:-0}" = 1 ]; then
  vision=(--vision)
fi
# A request that names no reasoning effort gets REASONING_EFFORT from rank 0's file (default high, as 1.x's
# api.default_reasoning_effort; empty: none, the chat template's own). The pinned template renders any effort but
# low and high, an unnamed one included, as max.
endpoint=()
if [ "$rank" = 0 ]; then
  endpoint=(--name "${MODEL_NAME:-glm-tf}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8095}")
  if [ -n "${REASONING_EFFORT-high}" ]; then
    endpoint+=(--reasoning-effort "${REASONING_EFFORT-high}")
  fi
fi
echo "[serve.sh] $(date -Is) TP=$tp rank $rank master $MASTER NCCL_IB_HCA=${NCCL_IB_HCA:-} VISION=${VISION:-0} tensorfold $(git -C /opt/tensorfold rev-parse HEAD 2>/dev/null || echo '?')"
# --drafter none: the MTP head drafts; DFlash2 is not used (its weights' terms) and TP=3 refuses it.
# --no-update-check: the engine is pinned here; its update check asks about upstream releases.
exec tensorfold serve "$CHECKPOINT" --tp "$tp" --rank "$rank" --master "$MASTER" "${endpoint[@]}" \
  --context "$context" --max-tokens 32768 --drafter none --no-update-check "${vision[@]}" "$@"
