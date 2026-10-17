#!/bin/bash
# On each host, while the engine serves: hostwatch.sh LOG [CONTAINER]
# Reads MemAvailable every 2 s and stops `tensorfold-native serve` when it falls below 5 GiB, before the unified memory
# runs out (the guard 1.x and 2.x used); exits when the engine is gone. cluster.sh starts it.
# The engine runs as root inside CONTAINER (default glm53-tf3), so it is found and stopped through `docker exec`:
# a `pkill` from the host user fails on it with "Operation not permitted" and still returns 0.
log=$1
container=${2:-glm53-tf3}
engines() { docker exec "$container" ps -eo args 2>/dev/null | grep -c '[t]ensorfold-native serve'; }
sleep 5
while [ "$(engines)" -gt 0 ]; do
  available=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  echo "$(date +%T) $available" >>"$log"
  if [ "$available" -lt 5 ]; then
    docker exec "$container" pkill -9 -f "tensorfold-native serve"
    echo KILLED >>"$log"
  fi
  sleep 2
done
echo "$(date +%T) done" >>"$log"
