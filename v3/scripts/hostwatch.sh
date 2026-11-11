#!/bin/bash
# On each host, while the engine serves: hostwatch.sh LOG [CONTAINER] [MEMINFO]
# Reads MemAvailable every 2 s and stops `tensorfold-native serve` when it falls below 5 GiB, before the unified memory
# runs out (the guard 1.x and 2.x used); exits when the engine is gone or its container no longer runs. cluster.sh
# starts it.
# The engine runs as root inside CONTAINER (default glm53-tf3), so it is found and stopped through `docker exec`:
# a `pkill` from the host user fails on it with "Operation not permitted" and still returns 0.
# A check that fails is not an engine gone: `docker exec` can fail or stall when memory is short, which is when the
# guard is needed. Such a round writes `check-failed` and the watch goes on; it ends only when `docker inspect` says
# the container is stopped or gone. Every docker call is bounded by the round's 2 s, so a call that stalls counts as
# failed and the next round still reads MemAvailable (`--kill-after=1`: a CLI that ignores the TERM is killed 1 s
# later). MemAvailable is read with shell builtins. MEMINFO (default /proc/meminfo) is for the tests.
log=$1
container=${2:-glm53-tf3}
meminfo=${3:-/proc/meminfo}

dock() { timeout --kill-after=1 2 docker "$@"; }

# The engine count on stdout; a non-zero status when `docker exec` itself fails or stalls.
engines() {
  local out
  out=$(dock exec "$container" ps -eo args 2>/dev/null) || return 1
  grep -c '[t]ensorfold-native serve' <<<"$out" || true
}

# Status 0 (stop watching) when the container is stopped or gone; 1 while it runs or docker cannot say.
container_gone() {
  local state
  state=$(dock inspect -f '{{.State.Running}}' "$container" 2>&1)
  case $state in
    false | *"No such"*) return 0 ;;
  esac
  return 1
}

# MemAvailable in whole GiB into `available`, empty when it cannot be read.
read_available() {
  available=
  local key value rest
  while read -r key value rest; do
    if [ "$key" = "MemAvailable:" ]; then
      available=$((value / 1048576))
      return
    fi
  done 2>/dev/null <"$meminfo"
}

sleep 5
while :; do
  if count=$(engines); then
    [ "$count" -gt 0 ] || break
  else
    container_gone && break
    echo "$(date +%T) check-failed" >>"$log"
  fi
  read_available
  echo "$(date +%T) ${available:-?}" >>"$log"
  if [ -n "$available" ] && [ "$available" -lt 5 ]; then
    if dock exec "$container" pkill -9 -f "tensorfold-native serve"; then
      echo KILLED >>"$log"
    else
      echo KILL-FAILED >>"$log"
    fi
  fi
  sleep 2
done
echo "$(date +%T) done" >>"$log"
