#!/bin/bash
# From a control machine with SSH to every host: cluster.sh CLUSTER_ENV start LABEL [more serve arguments]
#                                                 cluster.sh CLUSTER_ENV stop
#                                                 cluster.sh CLUSTER_ENV status
# CLUSTER_ENV (examples/cluster.tp*.env) sets TP, HOSTS (SSH names in rank order), CHECKOUT (this repository on
# each host, for the memory guard) and optionally SSH, CONTAINER and WORK (each host's directory at /work).
# start: every rank runs `serve.sh TP RANK /work/rank.env` in its container. TP=2 and TP=4: the highest rank first,
#        rank 0 last. TP=3: the three ranks together, rank 0 last. Then the memory guard (hostwatch.sh) on every host;
#        waits for rank 0's "serving" line and stops at the first rank that refuses or whose engine is gone. Logs:
#        WORK/logs/serve-rRANK-LABEL.log, hostwatch-LABEL.log.
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
# A rank's engine count on stdout; a non-zero status when ssh or docker fails, which is not a count of 0. A stopped
# or missing container runs no engine, so it counts 0 (hostwatch.sh reads its checks the same way). stopped: the
# count is 0. Docker names a missing container "No such object" or "No such container", or in lower case as
# 29.6.2 does; "no such file or directory" is a docker that cannot reach its daemon, not a missing container.
count() {
  $SSH "${H[$1]}" "out=\$(docker exec $CONTAINER ps -eo args 2>/dev/null) || { case \$(docker inspect -f \
'{{.State.Running}}' $CONTAINER 2>&1) in false | *[Nn]'o such object'* | *[Nn]'o such container'*) echo 0; exit 0 ;; esac; exit 1; }; \
printf '%s\n' \"\$out\" | grep -c '[t]ensorfold-native serve' || true" 2>/dev/null
}
stopped() { local n; n=$(count "$1") && [ "$n" = 0 ]; }
launch() {   # $1 rank, $2 label, then the more serve arguments
  local more= run
  [ $# -gt 2 ] && more=$(printf ' %q' "${@:3}")
  # The rank's command for the container's bash, each argument quoted; ssh hands the whole command to the
  # host's shell, so it is quoted once more
  run="bash /opt/glm53-tf3/serve.sh $TP $1 /work/rank.env$more > /work/logs/serve-r$1-$2.log 2>&1"
  $SSH "${H[$1]}" "docker exec -d $CONTAINER bash -c $(printf '%q' "$run")"
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
  for r in "${!H[@]}"; do
    n=$(count "$r") || n="?"
    echo "rank $r ${H[$r]}: $n engine process(es)"
  done ;;
start)
  label=${1:?start needs a LABEL for the logs}
  shift
  for r in "${!H[@]}"; do
    n=$(count "$r") || { echo "rank $r ${H[$r]}: its engines cannot be counted (ssh or docker failed)"; exit 1; }
    [ "$n" = 0 ] || { echo "rank $r ${H[$r]} already runs an engine"; exit 1; }
    $SSH "${H[$r]}" "mkdir -p $WORK/logs" || exit 1
  done
  if [ "$TP" = 3 ]; then
    for r in 2 1 0; do launch "$r" "$label" "$@"; done
  else
    for ((r = TP - 1; r >= 0; r--)); do
      launch "$r" "$label" "$@"
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
      if $SSH "${H[$r]}" "grep -aq REFUSE $WORK/logs/serve-r$r-$label.log" || stopped "$r"; then
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
    for _ in $(seq 1 30); do stopped "$r" && break; sleep 2; done
    stopped "$r" || $SSH "${H[$r]}" "docker exec $CONTAINER pkill -TERM -f 'tensorfold-native serve'"
  done
  for r in "${!H[@]}"; do
    for _ in $(seq 1 15); do stopped "$r" && break; sleep 2; done
    m=$($SSH "${H[$r]}" "awk '/MemAvailable/{print int(\$2/1048576)}' /proc/meminfo")
    n=$(count "$r") || n="?"
    echo "rank $r ${H[$r]}: $n engine process(es), MemAvailable $m GiB"
  done ;;
*)
  echo "unknown command '$cmd': start, stop or status" >&2
  exit 2 ;;
esac
