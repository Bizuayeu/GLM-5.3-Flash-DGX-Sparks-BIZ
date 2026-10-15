# Host Tools

[日本語](README.ja.md) · [Repository README](../README.md) · [Host preparation](../docs/hosts.md)

Host-side tools, independent of the serving engine, against the GB10 hard power-off under sustained load: a GPU clock cap, a telemetry logger, a cooling gate to call between long requests and a thermal watch that stops the engine. They are host settings, not part of the engine, and run on the host, outside the container. The cap and the thresholds were chosen on the reference hosts (MSI EdgeXpert GB10); the cap's rationale and its measured cost are in [GPU clock cap](../docs/hosts.md#gpu-clock-cap). Other hosts should check them against their own records.

## Files

| File | What it does |
|---|---|
| `gb10-clock-cap.service` | systemd oneshot: locks the GPU clock range at every boot with `nvidia-smi -lgc`, and releases it with `-rgc` when stopped |
| `gb10-telemetry` | Python logger: one JSON line every 2 s, fsynced line by line so the last samples survive a power-off, into `/var/log/gb10-telemetry/<UTC date>.jsonl`; keeps 14 days |
| `gb10-telemetry.service` | runs the logger as a service user (`Restart=always`) |
| `install.sh` | installs and enables both units, restarts the logger so that a reinstall runs the new program, then prints their state, the locked clocks and the last telemetry line |
| `cool-gate` | waits until the host has cooled down, reading the telemetry |
| `thermal-watch` | stops the engine when the host stays too hot, reading the telemetry |

The Python tools use only the standard library. `cool-gate` and `thermal-watch` read `/var/log/gb10-telemetry`, or the directory in `GB10_TELEMETRY_DIR`; the logger writes there too.

## Telemetry Record

| Field | Meaning |
|---|---|
| `epoch` | Unix time of the sample (s) |
| `acpi_c` | every ACPI thermal zone in zone order (°C), `null` for a zone that could not be read |
| `gpu_c` | GPU temperature (°C) |
| `power_w` | GPU power draw (W) |
| `clock_mhz` | graphics clock (MHz) |
| `util_pct` | GPU utilization (%) |
| `event_reasons` | `clocks_event_reasons.active` as `nvidia-smi` prints it |
| `load1` | 1-minute load average |
| `mem_available_gib` | `MemAvailable` (GiB) |
| `event_counters_us` | cumulative `clocks_event_reasons_counters.*` (µs): `sw_power_cap`, `sync_boost`, `sw_thermal_slowdown`, `hw_thermal_slowdown`, `hw_power_brake_slowdown`; `null` for a counter `nvidia-smi` cannot read |

The tools below judge heat by the hottest non-null value of `acpi_c`. On the reference hosts `nvidia-persistenced` runs with `--no-persistence-mode`, so the logger's long-running `nvidia-smi` also keeps a client attached to the GPU. Whether the cap holds shows in `clock_mhz` under load. The counters are recorded because GB10 reads N/A for the power limit and the memory clock, and an SW power cap that comes and goes between two samples shows only in the counter: on 2026-10-06 the reference hosts' `sw_power_cap` grew only while no engine ran (208-305 MHz, about 5.5 W), never during prefills.

## Install

On each host, from this directory:

```bash
sudo sh install.sh          # the logger runs as the user who called sudo
sudo sh install.sh <user>   # or as another existing user
```

The script refuses to run without root. It writes the user into the logger's unit, creates `/var/log/gb10-telemetry` owned by that user, and ends with `installed for <user>`.

To remove: `sudo systemctl disable --now gb10-clock-cap.service gb10-telemetry.service` (stopping the cap unit releases the cap), delete the two units from `/etc/systemd/system/` and `/usr/local/sbin/gb10-telemetry`, then `sudo systemctl daemon-reload`.

## During Long Runs

2.x's engine also waits for heat inside a request, between prompt chunks (`TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`; [2.x README](../v2/README.md)). These two tools act outside it.

**Cooling gate.** Before each long request, from the checkout root on each host:

```bash
python3 host/cool-gate --label <text>
```

It returns once the hottest ACPI zone is at or below `--band` (default 60 °C) or after `--cap` seconds (default 600), and prints one JSON line: why it returned (`cool` or `cap`), the seconds waited, and the temperatures at the start and the end. Exit 0 means go on. Exit 2 means the telemetry is missing or older than 30 s: the run should not continue unrecorded. The defaults come from the reference hosts' records: 60 °C sits just above the idle band measured there, and 600 s is longer than the slowest return to it they measured.

**Thermal watch.** While the engine serves, on each host:

```bash
python3 host/thermal-watch ~/glm53-tf/logs/therm-<label>.log &
```

Every 2 s it appends the time, the telemetry row's epoch, the hottest ACPI zone, GPU temperature, power and clock to the log. Two readings in a row at or above 94.0 °C stop the engine with `pkill -f` inside the container. The rule comes from the reference hosts' records: 93.7 °C was the highest reading that ended without a power-off when it was set, and on a warm afternoon of 2026-10-15 a host read up to 95.0 °C, at or above 94 °C twice but never twice in a row, without one; `--threshold` and `--readings` change it. The engine's own heat wait acts only between prefill chunks, so heat from a long run of decoding (tool-eval-bench's runs, for example) is the watch's alone. The engine runs as root in its container, so the watch finds and stops it through `docker exec`. It stops a process started inside the container, as `cluster.sh` starts the engine with `docker exec`; a container's PID 1 is not stopped, because PID 1 ignores the signal by default. It ends when `therm-<label>.stop` (the log's name with `.stop`) exists or the engine is gone.

The watch was verified with the 2.x engine: container `glm53-tf` and process `tensorfold serve`, its defaults. `--container` and `--process` name another container and process, for example a container created with a different `CONTAINER`.

**Verified.** On 2026-10-04 on a reference host (GB10), without sudo: the logger wrote a row every 2 s into a temporary directory; `cool-gate` returned `cool` with exit 0 on the live record and `telemetry stale` with exit 2 without one; `thermal-watch` with `--threshold 0` stopped a process started with `docker exec` on its second reading and ended at once when the container was absent. `install.sh` was not run (it refuses without root).
