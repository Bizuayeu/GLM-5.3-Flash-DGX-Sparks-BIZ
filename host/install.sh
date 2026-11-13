#!/bin/sh
# One-time install on each host: the GPU clock cap and the telemetry logger.
#   sudo sh install.sh [USER] [--heat-cap]
# USER runs the logger and owns /var/log/gb10-telemetry; it defaults to the user who ran sudo.
# --heat-cap also installs and enables the heat cap (gb10-heat-cap), which changes the
# conditions of every measurement on the host; without it nothing else is installed.
# Files come from the directory of this script.
set -eu
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
heat_cap=no
for arg do
  shift
  case $arg in
    --heat-cap) heat_cap=yes ;;
    -*) echo "unknown option: $arg" >&2; exit 1 ;;
    *) set -- "$@" "$arg" ;;
  esac
done
[ $# -le 1 ] || { echo "usage: sudo sh install.sh [USER] [--heat-cap]" >&2; exit 1; }
user=${1:-${SUDO_USER:-}}
[ -n "$user" ] || { echo "usage: sudo sh install.sh USER (no SUDO_USER to default to)" >&2; exit 1; }
case $user in
  *[!A-Za-z0-9._-]*) echo "not a user name: $user" >&2; exit 1 ;;
esac
id -u "$user" >/dev/null || { echo "no such user: $user" >&2; exit 1; }
group=$(id -gn "$user")
here=$(cd "$(dirname "$0")" && pwd)
install -o root -g root -m 0755 "$here/gb10-telemetry" /usr/local/sbin/gb10-telemetry
sed "s/@SERVICE_USER@/$user/" "$here/gb10-telemetry.service" >/etc/systemd/system/gb10-telemetry.service
chown root:root /etc/systemd/system/gb10-telemetry.service
chmod 0644 /etc/systemd/system/gb10-telemetry.service
install -o root -g root -m 0644 "$here/gb10-clock-cap.service" /etc/systemd/system/gb10-clock-cap.service
install -d -o "$user" -g "$group" -m 0755 /var/log/gb10-telemetry
units="gb10-clock-cap.service gb10-telemetry.service"
if [ "$heat_cap" = yes ]; then
  install -o root -g root -m 0755 "$here/gb10-heat-cap" /usr/local/sbin/gb10-heat-cap
  install -o root -g root -m 0644 "$here/gb10-heat-cap.service" /etc/systemd/system/gb10-heat-cap.service
  units="$units gb10-heat-cap.service"
fi
systemctl daemon-reload
systemctl enable --now $units
systemctl restart gb10-telemetry.service  # enable --now leaves a running logger on the old program
if [ "$heat_cap" = yes ]; then
  systemctl restart gb10-heat-cap.service  # likewise for the heat cap
fi
sleep 5
systemctl is-active $units
nvidia-smi -q -d CLOCK | sed -n '/Locked/,+3p;/Max Clocks/,+2p' | head -8
tail -n 1 "$(ls -t /var/log/gb10-telemetry/*.jsonl | head -n 1)"  # the newest day's file
if [ "$heat_cap" = yes ]; then
  /usr/local/sbin/gb10-heat-cap --status
fi
echo "$(hostname): installed for $user"
