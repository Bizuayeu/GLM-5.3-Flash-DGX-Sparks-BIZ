# Host Tools

[日本語](README.ja.md) · [Repository README](../README.md) · [Host preparation](../docs/hosts.md)

Host-side tools, independent of the serving engine, against the GB10 hard power-off under sustained load: a GPU clock cap, a telemetry logger, a cooling gate to call between long requests, a thermal watch that stops the engine, and an opt-in heat cap that lowers the clock cap while the host stays hot. They are host settings, not part of the engine, and run on the host, outside the container. The cap and the thresholds were chosen on the reference hosts (MSI EdgeXpert GB10); the cap's rationale and its measured cost are in [GPU clock cap](../docs/hosts.md#gpu-clock-cap). Other hosts should check them against their own records.

## Files

| File | What it does |
|---|---|
| `gb10-clock-cap.service` | systemd oneshot: locks the GPU clock range at every boot with `nvidia-smi -lgc`, and releases it with `-rgc` when stopped |
| `gb10-telemetry` | Python logger: one JSON line every 2 s, fsynced line by line so the last samples survive a power-off, into `/var/log/gb10-telemetry/<UTC date>.jsonl`; keeps 14 days |
| `gb10-telemetry.service` | runs the logger as a service user (`Restart=always`) |
| `install.sh` | installs and enables both units, restarts the logger so that a reinstall runs the new program, then prints their state, the locked clocks and the last telemetry line; with `--heat-cap`, the heat cap too |
| `cool-gate` | waits until the host has cooled down, reading the telemetry |
| `thermal-watch` | stops the engine when the host stays too hot, reading the telemetry |
| `gb10-heat-cap` | lowers the clock cap to 2,000 MHz while the host stays hot and raises it back once cool, reading the telemetry ([heat cap](#heat-cap)) |
| `gb10-heat-cap.service` | runs the heat cap as root after the cap unit and the logger (`Restart=on-failure`), and stops or restarts with the cap unit (`PartOf=`); installed only with `--heat-cap` |
| `nccl_probe.py` | checks NCCL across two or three ranks without model weights; needs PyTorch with NCCL ([NCCL diagnostics](../docs/nccl-validation.md)) |

`gb10-telemetry`, `cool-gate`, `thermal-watch` and `gb10-heat-cap` use only Python's standard library. `cool-gate`, `thermal-watch` and `gb10-heat-cap` read `/var/log/gb10-telemetry`, or the directory in `GB10_TELEMETRY_DIR`; the logger writes there too.

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
sudo sh install.sh [<user>] --heat-cap   # also the heat cap
```

The script refuses to run without root. It writes the user into the logger's unit, creates `/var/log/gb10-telemetry` owned by that user, and ends with `installed for <user>`. Without `--heat-cap` it installs the logger and the two units above and nothing else; with it, also the [heat cap](#heat-cap), whose state it prints before the last line.

To remove: `sudo systemctl disable --now gb10-clock-cap.service gb10-telemetry.service` (stopping the cap unit releases the cap), delete the two units from `/etc/systemd/system/` and `/usr/local/sbin/gb10-telemetry`, then `sudo systemctl daemon-reload`. The heat cap goes first, the same way: `sudo systemctl disable --now gb10-heat-cap.service` (stopping it locks 2,200 MHz), then delete its unit and `/usr/local/sbin/gb10-heat-cap`.

## Heat Cap

`gb10-heat-cap` is a root service that lowers the boot cap from 2,200 to 2,000 MHz while the host stays hot, and raises it back once the host is cool. The engine runs in its container and cannot change the clock, so this runs on the host. Every 2 s it reads the newest rows of the telemetry (and the previous day's file just after the UTC day changes) and judges by the hottest non-null ACPI zone:

- At 2,200 MHz: once the zone has read at or above 90 °C for more than half of the last 300 s (150 s, counted from the rows' epochs), it locks `nvidia-smi -lgc 300,2000`. The time counts only from the moment the cap became 2,200, so neither the few readings after a start nor the hot readings before a return switch it early.
- At 2,000 MHz: after the readings stay at or below 75 °C for 120 s, it locks `-lgc 300,2200` again. A warmer reading, a reading without a zone or a gap in the record starts the hold over.
- A missing record, or one older than 30 s (`cool-gate`'s limit), locks 2,000 MHz and records why. When the record comes back, the return still needs the 120 s at or below 75 °C, so a boot whose logger has not written yet starts at 2,000 MHz for at least that long.
- It starts at 2,200 MHz, or at 2,000 when the record is stale, and locks 2,200 before it ends on SIGTERM. It never resets the clocks with `-rgc` and never locks above 2,200 (`--top-mhz` takes no more). A failed `nvidia-smi`, or one that has not answered in 30 s (the stale limit), is recorded and tried again on the next reading; the service does not end on it.

**Where the lines come from.** The reference hosts' long prefills. On 2026-11-11 a 2M-token one at 2,200 MHz reached 90 °C 2 to 4 minutes after it began and stayed at 88 to 92 °C nearly to its end, and the driver's software thermal slowdown acted once, for 0.1 s. On 2026-11-12, at 2,000 MHz, the 2M-token prefills at TP=3 and the 1M-token ones at TP=2 stayed below 90 °C: on rank 0 the zone moved between 79 and 89 °C once warm and fell below 75 °C within 12 s of each load's end. A return line inside that band raises the cap while the prefill still runs: replayed on that day's 2,000 MHz records, 85 °C, the first proposal, did so seven times while rank 0 was loaded (four in the 2M-token prefills, three in the 1M-token ones), and 75 °C returned only after the loads. Replayed on rank 0's 2,200 MHz record ([`tests/data/heat-cap-2m-prefill.csv`](../tests/data/heat-cap-2m-prefill.csv)), the rules lock 2,000 MHz 408 s after the GPU began the prefill and 2,200 again 124 s after it ended; that record stays at 2,200 MHz, so the return is that host's at 2,200. On its 2,000 MHz record ([`tests/data/heat-cap-2m-prefill-2000.csv`](../tests/data/heat-cap-2m-prefill-2000.csv)), from the prefill's first reading at 88 °C, the cap holds 2,000 MHz to the end of the load and returns 124 s after it. Every line is an argument (`--high`, `--low`, `--window`, `--share`, `--hold`, `--hot-mhz`, `--top-mhz`, `--stale`), read strictly at start: a value that cannot be read or is out of range exits 2 with its name, the value and the form it takes.

**Beside the other guards.** The engines' heat wait holds prefill chunks above 92 °C until 88 °C, and `thermal-watch` stops the engine after two readings in a row at or above 94 °C. The heat cap lowers the clock before either acts; both stay as the nets below it.

**What it records.** Each change is one fsynced JSON line in `heat-cap.log` in the telemetry's directory (not a `*.jsonl` name, which the other tools read as the record): the time, the MHz before and after, why, the seconds at or above 90 °C in the window, the seconds at or below 75 °C, and the newest row's values. A failed `nvidia-smi` adds one line per cause, and a record that goes stale while the cap is already 2,000 MHz adds one (`kept`) until it is fresh again. `/run/gb10-heat-cap.json` holds the cap in force and when and why it was set; it is replaced in one step at each change and readable by every user, and `gb10-heat-cap --status` prints it as one JSON line (exit 1 when it is absent). A receipt counts each cell's seconds at 2,000 MHz from these lines and the record's `clock_mhz`, and a run's preflight reads the cap in force from `--status`.

**Not installed by default.** It changes the conditions of every measurement on the host, so only `sudo sh install.sh [<user>] --heat-cap` installs and enables it. Stopping or restarting `gb10-clock-cap.service` stops or restarts the heat cap too (`PartOf=`): the heat cap locks 2,200 MHz and ends first, the cap unit then resets the clocks with `-rgc` or locks 2,200 again, and a restarted heat cap starts as at boot. A stopped heat cap stays stopped: restarting the cap unit restarts only a running one (seen on a reference host on 2026-11-13), and `sudo systemctl start gb10-heat-cap.service` brings it back. A run that locks its own cap with `nvidia-smi -lgc` stops the heat cap first: a running one locks 2,200 MHz over that cap when it returns from 2,000 after the host cools, and whenever it stops or starts.

## During Long Runs

The 2.x and 3.x engines also wait for heat inside a request, between prompt chunks (2.x: `TF_GLM_HEAT_HIGH`, `TF_GLM_HEAT_LOW`, [2.x README](../v2/README.md); 3.x: `TF_HEAT_HIGH`, `TF_HEAT_LOW`, [3.x README](../v3/README.md#serving-defaults)). These two tools act outside it.

**Cooling gate.** Before each long request, from the checkout root on each host:

```bash
python3 host/cool-gate --label <text>
```

It returns once the hottest ACPI zone is at or below `--band` (default 60 °C) or after `--cap` seconds (default 600), and prints one JSON line: why it returned (`cool` or `cap`), the seconds waited, and the temperatures at the start and the end. Exit 0 means go on. Exit 2 means the telemetry is missing or older than 30 s: the run should not continue unrecorded. The defaults come from the reference hosts' records: 60 °C sits just above the idle band measured there, and 600 s is longer than the slowest return to it they measured.

**Thermal watch.** While the engine serves, on each host:

```bash
python3 host/thermal-watch ~/glm53-tf/logs/therm-<label>.log &      # 2.x: its container and process are the defaults
python3 host/thermal-watch ~/glm53-tf3/logs/therm-<label>.log \
  --container glm53-tf3 --process 'tensorfold-native serve' &       # 3.x
```

Every 2 s it appends the time, the telemetry row's epoch, the hottest ACPI zone, GPU temperature, power and clock to the log. Two readings in a row at or above 94.0 °C stop the engine with `pkill -f` inside the container. The rule comes from the reference hosts' records: 93.7 °C was the highest reading that ended without a power-off when it was set, and on a warm afternoon of 2026-10-15 a host read up to 95.0 °C, at or above 94 °C twice but never twice in a row, without one; `--threshold` and `--readings` change it. The engine's own heat wait acts only between prefill chunks, so heat from a long run of decoding (tool-eval-bench's runs, for example) is the watch's alone. The engine runs as root in its container, so the watch finds and stops it through `docker exec`. It stops a process started inside the container, as `cluster.sh` starts the engine with `docker exec`; a container's PID 1 is not stopped, because PID 1 ignores the signal by default. It ends when `therm-<label>.stop` (the log's name with `.stop`) exists or the engine is gone.

The defaults are 2.x's container `glm53-tf` and process `tensorfold serve`, with which the watch was verified (below). On a 3.x host they find no engine, and the watch ends at once without a reading: give it 3.x's container and process, as above ([3.x operations](../v3/docs/operations.md#a-rank-that-stops)). `--container` and `--process` also name another container and process, for example a container created with a different `CONTAINER`.

**Verified.** On 2026-10-04 on a reference host (GB10), without sudo: the logger wrote a row every 2 s into a temporary directory; `cool-gate` returned `cool` with exit 0 on the live record and `telemetry stale` with exit 2 without one; `thermal-watch` with `--threshold 0` stopped a process started with `docker exec` on its second reading and ended at once when the container was absent. `install.sh` was not run (it refuses without root).
