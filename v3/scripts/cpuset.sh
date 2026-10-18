#!/bin/bash
# cpuset.sh [CPU_DIR]: the cores create_container.sh gives the container, from CPUSET; empty means every core.
# Unset or auto: the cores whose cpuinfo_max_freq is the lowest (on a GB10, the efficiency cores 0-4,10-14), or none
# when every core reports the same maximum or none reports one. Empty: none. Anything else is printed as given.
# CPU_DIR is /sys/devices/system/cpu; the tests give their own.
set -eu
cpuset=${CPUSET-auto}
if [ "$cpuset" != auto ]; then
  echo "$cpuset"
  exit 0
fi
dir=${1:-/sys/devices/system/cpu}
declare -A freq
lo= hi=
for f in "$dir"/cpu[0-9]*/cpufreq/cpuinfo_max_freq; do
  [ -r "$f" ] || continue
  n=${f#"$dir"/cpu}
  n=${n%%/*}
  v=$(<"$f")
  freq[$n]=$v
  if [ -z "$lo" ] || [ "$v" -lt "$lo" ]; then lo=$v; fi
  if [ -z "$hi" ] || [ "$v" -gt "$hi" ]; then hi=$v; fi
done
if [ -z "$lo" ] || [ "$lo" = "$hi" ]; then
  echo ""
  exit 0
fi
list=()
for n in $(printf '%s\n' "${!freq[@]}" | sort -n); do
  if [ "${freq[$n]}" = "$lo" ]; then list+=("$n"); fi
done
out=
start=${list[0]}
prev=$start
for n in "${list[@]:1}" ""; do
  if [ -n "$n" ] && [ "$n" -eq $((prev + 1)) ]; then
    prev=$n
    continue
  fi
  if [ "$start" = "$prev" ]; then out+=${out:+,}$start; else out+=${out:+,}$start-$prev; fi
  start=$n
  prev=$n
done
echo "$out"
