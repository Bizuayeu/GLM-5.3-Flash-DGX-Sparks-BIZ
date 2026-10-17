#!/bin/bash
# From a control machine with SSH to every host: cluster.sh CLUSTER_ENV start LABEL [more serve arguments]
#                                                 cluster.sh CLUSTER_ENV stop
#                                                 cluster.sh CLUSTER_ENV status
# CLUSTER_ENV (examples/cluster.tp*.env) sets TP, HOSTS (SSH names in rank order), CHECKOUT (this repository on
# each host, for the memory guard) and optionally SSH, CONTAINER and WORK (each host's directory at /work).
# start: every rank runs `serve.sh TP RANK /work/rank.env` in its container. TP=2: the highest rank first, rank 0
#        last. TP=3: rank 0 first; its NCCL id (/work/nccl-id, 256 hex characters) is copied to the other hosts, then
#        the others start. Then the memory guard (hostwatch.sh) on every host; waits for rank 0's "serving" line and
#        stops at the first rank that refuses or whose engine is gone. Logs: WORK/logs/serve-rRANK-LABEL.log,
#        hostwatch-LABEL.log.
# stop:  rank 0 first (the others leave when it does), then any rank left; prints each host's MemAvailable.
set -u
if [ $# -lt 2 ]; then
  echo "usage: cluster.sh CLUSTER_ENV start LABEL [serve args...] | stop | status" >&2
  exit 2
fi
. "$1"
cmd=$2
shift 2
: "${TP:?CLUSTER_ENV must set TP}" "${HOSTS:?CLUSTER_ENV must set HOSTS}" "${CHECKOUT:?CLUSTER_ENV must set CHECKOUT}"
SSH=${SSH:-ssh -o ConnectTimeout=20}
CONTAINER=${CONTAINER:-glm53-tf3}
WORK=${WORK:-'$HOME/glm53-tf3'}
read -r -a H <<<"$HOSTS"
if [ "${#H[@]}" != "$TP" ]; then
  echo "HOSTS names ${#H[@]} hosts for TP=$TP" >&2
  exit 2
fi
count() { $SSH "${H[$1]}" "docker exec $CONTAINER ps -eo args | grep -c '[t]ensorfold-native serve'" 2>/dev/null; }
launch() {   # $1 rank, $2 label, $3 more serve arguments
  $SSH "${H[$1]}" "docker exec -d $CONTAINER bash -c 'bash /opt/glm53-tf3/serve.sh $TP $1 /work/rank.env $3 \
    > /work/logs/serve-r$1-$2.log 2>&1'"
}
dump() {
  local q
  for q in "${!H[@]}"; do
    echo "== rank $q"
    $SSH "${H[$q]}" "grep -av 'NCCL INFO' $WORK/logs/serve-r$q-$1.log | tail -n 25"
  done
}

case $cmd in
status)
  for r in "${!H[@]}"; do echo "rank $r ${H[$r]}: $(count "$r") engine process(es)"; done ;;
start)
  label=${1:?start needs a LABEL for the logs}
  shift
  for r in "${!H[@]}"; do
    [ "$(count "$r")" = 0 ] || { echo "rank $r ${H[$r]} already runs an engine"; exit 1; }
    $SSH "${H[$r]}" "mkdir -p $WORK/logs && rm -f $WORK/nccl-id $WORK/nccl-id.tmp" || exit 1
  done
  if [ "$TP" = 3 ]; then
    launch 0 "$label" "$*"
    for _ in $(seq 1 60); do
      [ "$($SSH "${H[0]}" "stat -c %s $WORK/nccl-id 2>/dev/null")" = 256 ] && break
      [ "$(count 0)" = 0 ] && break
      sleep 2
    done
    id=$($SSH "${H[0]}" "cat $WORK/nccl-id 2>/dev/null")
    if [ "${#id}" != 256 ]; then
      echo "FAILED: rank 0 wrote no NCCL id"
      dump "$label"
      exit 1
    fi
    for r in 1 2; do
      printf '%s' "$id" | $SSH "${H[$r]}" "cat > $WORK/nccl-id.tmp && mv $WORK/nccl-id.tmp $WORK/nccl-id" || exit 1
      launch "$r" "$label" "$*"
    done
  else
    for ((r = TP - 1; r >= 0; r--)); do
      launch "$r" "$label" "$*"
      sleep 3
    done
  fi
  for r in "${!H[@]}"; do
    $SSH "${H[$r]}" "(setsid nohup bash $CHECKOUT/v3/scripts/hostwatch.sh $WORK/logs/hostwatch-$label.log $CONTAINER \
      >/dev/null 2>&1 </dev/null &)"
  done
  t0=$(date +%s)
  for _ in $(seq 1 90); do
    sleep 10
    if $SSH "${H[0]}" "grep -aq '^\[tensorfold\] serving ' $WORK/logs/serve-r0-$label.log"; then
      echo "READY after $(($(date +%s) - t0)) s"
      $SSH "${H[0]}" "grep -a '^\[tensorfold\]\|^\[serve.sh\]' $WORK/logs/serve-r0-$label.log | tail -n 8"
      exit 0
    fi
    for r in "${!H[@]}"; do
      if $SSH "${H[$r]}" "grep -aq REFUSE $WORK/logs/serve-r$r-$label.log" || [ "$(count "$r")" = 0 ]; then
        echo "FAILED on rank $r"
        dump "$label"
        exit 1
      fi
    done
  done
  echo "TIMEOUT: no serving line after 15 minutes"
  exit 1 ;;
stop)
  $SSH "${H[0]}" "docker exec $CONTAINER pkill -TERM -f 'tensorfold-native serve'"
  for r in "${!H[@]}"; do
    for _ in $(seq 1 30); do [ "$(count "$r")" = 0 ] && break; sleep 2; done
    [ "$(count "$r")" = 0 ] || $SSH "${H[$r]}" "docker exec $CONTAINER pkill -TERM -f 'tensorfold-native serve'"
  done
  for r in "${!H[@]}"; do
    for _ in $(seq 1 15); do [ "$(count "$r")" = 0 ] && break; sleep 2; done
    m=$($SSH "${H[$r]}" "awk '/MemAvailable/{print int(\$2/1048576)}' /proc/meminfo")
    echo "rank $r ${H[$r]}: $(count "$r") engine process(es), MemAvailable $m GiB"
  done ;;
*)
  echo "unknown command '$cmd': start, stop or status" >&2
  exit 2 ;;
esac
