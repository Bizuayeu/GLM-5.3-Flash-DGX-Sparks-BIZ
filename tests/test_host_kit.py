"""The host tools in host/: telemetry reading, the cooling gate and the thermal watch."""

import datetime
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

HOST = Path(__file__).resolve().parents[1] / "host"


def load(name, log_dir):
    """Import an extensionless script of host/ with GB10_TELEMETRY_DIR set to log_dir."""
    path = str(HOST / name)
    module = name.replace("-", "_")
    loader = SourceFileLoader(module, path)
    spec = importlib.util.spec_from_file_location(module, path, loader=loader)
    script = importlib.util.module_from_spec(spec)
    environment = {"GB10_TELEMETRY_DIR": str(log_dir)}
    with (
        patch.dict(os.environ, environment),
        patch.object(sys, "dont_write_bytecode", True),
    ):
        loader.exec_module(script)
    return script


def write_rows(log_dir, *rows):
    day = datetime.datetime.now(datetime.UTC).date().isoformat()
    with open(Path(log_dir) / f"{day}.jsonl", "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def row(acpi, epoch=None):
    return {
        "epoch": time.time() if epoch is None else epoch,
        "acpi_c": acpi,
        "gpu_c": 50.0,
        "power_w": 30.0,
        "clock_mhz": 2200.0,
    }


def day_change(log_dir, *rows, new_day=""):
    """The record just after the UTC day changes: rows end the previous day's file, and
    the new day's file holds only new_day (nothing yet, or a torn first line)."""
    lines = "".join(json.dumps(r) + "\n" for r in rows)
    Path(log_dir, "2026-11-12.jsonl").write_text(lines, encoding="utf-8")
    Path(log_dir, "2026-11-13.jsonl").write_text(new_day, encoding="utf-8")


class CoolGateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.gate = load("cool-gate", self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def run_gate(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = self.gate.main(list(argv))
        return code, json.loads(out.getvalue())

    def test_log_dir_comes_from_the_environment(self):
        self.assertEqual(self.gate.LOG_DIR, self.dir.name)

    def test_cool_at_or_below_the_band(self):
        write_rows(self.dir.name, row([70.0, None, 60.0]))
        code, result = self.run_gate("--band", "70", "--label", "t")
        self.assertEqual((code, result["result"]), (0, "cool"))
        self.assertEqual(result["end"]["acpi_max_c"], 70.0)

    def test_cap_when_above_the_band(self):
        write_rows(self.dir.name, row([75.0]))
        code, result = self.run_gate("--band", "60", "--cap", "0")
        self.assertEqual((code, result["result"]), (0, "cap"))

    def test_defaults_are_60_c_and_600_s(self):
        write_rows(self.dir.name, row([40.0]))
        _, result = self.run_gate()
        self.assertEqual((result["band_c"], result["cap_s"]), (60.0, 600.0))

    def test_missing_telemetry_exits_2(self):
        code, result = self.run_gate("--cap", "0")
        self.assertEqual((code, result["result"]), (2, "telemetry stale"))

    def test_stale_telemetry_exits_2(self):
        write_rows(self.dir.name, row([40.0], epoch=time.time() - 60))
        code, result = self.run_gate("--cap", "0")
        self.assertEqual((code, result["result"]), (2, "telemetry stale"))

    def test_latest_row_wins_and_a_torn_line_is_skipped(self):
        write_rows(self.dir.name, row([90.0]), row([45.0]))
        with open(next(Path(self.dir.name).glob("*.jsonl")), "a") as f:
            f.write('{"epoch": 1')
        self.assertEqual(self.gate.last_row()["acpi_c"], [45.0])

    def test_just_after_the_day_changes_the_previous_day_is_read(self):
        day_change(self.dir.name, row([90.0]), row([55.0]))
        code, result = self.run_gate("--band", "60", "--cap", "0")
        self.assertEqual((code, result["result"]), (0, "cool"))
        self.assertEqual(result["end"]["acpi_max_c"], 55.0)

    def test_a_torn_first_line_of_the_new_day_reads_the_previous_day(self):
        day_change(self.dir.name, row([55.0]), new_day='{"epoch": 1')
        self.assertEqual(self.gate.last_row()["acpi_c"], [55.0])

    def test_the_new_day_wins_once_it_has_a_row(self):
        day_change(self.dir.name, row([55.0]), new_day=json.dumps(row([65.0])) + "\n")
        self.assertEqual(self.gate.last_row()["acpi_c"], [65.0])

    def test_view_takes_the_hottest_non_null_zone(self):
        self.assertEqual(self.gate.view(row([None, 61.5, 58.0]))["acpi_max_c"], 61.5)
        self.assertIsNone(self.gate.view(row([None]))["acpi_max_c"])


class ThermalWatchTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.watch = load("thermal-watch", self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def count(self, readings, threshold=94.0):
        hot, counts = 0, []
        for acpi in readings:
            hot = self.watch.step(hot, acpi, threshold)
            counts.append(hot)
        return counts

    def test_defaults_match_the_reference_rule(self):
        self.assertEqual(self.watch.THRESHOLD_C, 94.0)
        self.assertEqual(self.watch.READINGS, 2)

    def test_two_readings_in_a_row_reach_the_stop_count(self):
        self.assertEqual(self.count([93.9, 94.0, 94.5]), [0, 1, 2])

    def test_a_cool_reading_resets(self):
        self.assertEqual(self.count([95.0, 93.7, 95.0]), [1, 0, 1])

    def test_a_missing_reading_resets(self):
        self.assertEqual(self.count([95.0, None, 95.0]), [1, 0, 1])

    def test_hottest_takes_the_max_non_null_zone(self):
        self.assertEqual(self.watch.hottest(row([None, 91.2, 94.1])), 94.1)
        self.assertIsNone(self.watch.hottest(row([None, None])))
        self.assertIsNone(self.watch.hottest(None))

    def test_stop_file_sits_beside_the_log(self):
        log = os.path.join(self.dir.name, "therm-run.log")
        self.assertEqual(
            self.watch.stop_file(log), os.path.join(self.dir.name, "therm-run.stop")
        )

    def test_reads_the_latest_row(self):
        write_rows(self.dir.name, row([80.0]), row([93.0, None]))
        self.assertEqual(self.watch.hottest(self.watch.last_row()), 93.0)

    def test_no_telemetry_reads_as_none(self):
        self.assertIsNone(self.watch.last_row())

    def test_just_after_the_day_changes_the_previous_day_is_read(self):
        day_change(self.dir.name, row([93.0]))
        self.assertEqual(self.watch.hottest(self.watch.last_row()), 93.0)

    def run_watch(self, *argv):
        log = os.path.join(self.dir.name, "therm-run.log")
        calls = []

        def docker(cmd, **kwargs):
            calls.append(cmd)
            ps = "ps -eo args\ntensorfold serve --x\np q --y\n"
            return subprocess.CompletedProcess(cmd, 0, ps, "")

        with (
            patch.object(self.watch.subprocess, "run", docker),
            patch.object(self.watch.time, "sleep"),
        ):
            self.watch.main([log, *argv])
        return calls, Path(log).read_text(encoding="utf-8").splitlines()

    def test_main_stops_the_engine_on_the_second_hot_reading(self):
        write_rows(self.dir.name, row([95.0, None]))
        calls, lines = self.run_watch()
        self.assertEqual(
            calls[-1], ["docker", "exec", "glm53-tf", "pkill", "-f", "tensorfold serve"]
        )
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[2].endswith("ABORT acpi 95.0"))
        self.assertTrue(lines[3].endswith(" end"))

    def test_main_passes_its_container_and_process(self):
        write_rows(self.dir.name, row([95.0]))
        calls, _ = self.run_watch("--container", "c", "--process", "p q")
        self.assertEqual(calls[0], ["docker", "exec", "c", "ps", "-eo", "args"])
        self.assertEqual(calls[-1], ["docker", "exec", "c", "pkill", "-f", "p q"])

    def test_process_is_a_regex_as_for_pkill(self):
        write_rows(self.dir.name, row([95.0]))
        calls, _ = self.run_watch("--process", "p.*q")
        self.assertEqual(
            calls[-1], ["docker", "exec", "glm53-tf", "pkill", "-f", "p.*q"]
        )

    def test_main_ends_on_the_stop_file_without_stopping_the_engine(self):
        write_rows(self.dir.name, row([95.0]))
        Path(self.dir.name, "therm-run.stop").write_text("")
        calls, lines = self.run_watch()
        self.assertEqual(calls, [])
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].endswith(" end"))


class TelemetryTests(unittest.TestCase):
    def test_log_dir_comes_from_the_environment_and_prune_keeps_recent_days(self):
        with tempfile.TemporaryDirectory() as log_dir:
            telemetry = load("gb10-telemetry", log_dir)
            self.assertEqual(telemetry.OUT, log_dir)
            today = datetime.date(2026, 10, 4)
            old = today - datetime.timedelta(days=telemetry.KEEP_DAYS + 1)
            recent = today - datetime.timedelta(days=telemetry.KEEP_DAYS)
            for day in (old, recent):
                (Path(log_dir) / f"{day.isoformat()}.jsonl").write_text("")
            telemetry.prune(today)
            self.assertEqual(
                sorted(p.name for p in Path(log_dir).glob("*.jsonl")),
                [f"{recent.isoformat()}.jsonl"],
            )

    def test_counters_read_microseconds_and_not_available_as_null(self):
        with tempfile.TemporaryDirectory() as log_dir:
            telemetry = load("gb10-telemetry", log_dir)
        # "us" in case nounits leaves the counters' unit, as csv prints it.
        counters = telemetry.counters(["55157801736", "0", "[N/A]", "N/A", "470 us"])
        self.assertEqual(
            counters,
            {
                "sw_power_cap": 55157801736,
                "sync_boost": 0,
                "sw_thermal_slowdown": None,
                "hw_thermal_slowdown": None,
                "hw_power_brake_slowdown": 470,
            },
        )

    def test_a_record_keeps_its_fields_and_appends_the_counters(self):
        # A line of nvidia-smi's at nounits (a GB10 host, 2026-10-06),
        # and a line of the old five fields, which is skipped.
        lines = [
            "53, 10.14, 2190, 0, 0x0000000000000004, 55157801736, 0, 0, 0, 0\n",
            "53, 10.14, 2190, 0, 0x0000000000000000\n",
        ]

        class Smi:
            stdout = lines

            def wait(self):
                return 0

        # The logger keeps its day's file open; Windows cannot remove an open file.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as log_dir:
            telemetry = load("gb10-telemetry", log_dir)
            with (
                patch.object(
                    telemetry.subprocess, "Popen", return_value=Smi()
                ) as popen,
                patch.object(telemetry, "acpi_c", return_value=[50.0]),
                patch.object(telemetry, "mem_available_gib", return_value=100.0),
                patch.object(telemetry.os, "getloadavg", create=True) as load1,
                self.assertRaises(SystemExit),
            ):
                load1.return_value = (0.5, 0.0, 0.0)
                telemetry.main()
            query = popen.call_args[0][0][1]
            records = [
                json.loads(line)
                for path in Path(log_dir).glob("*.jsonl")
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertIn("clocks_event_reasons_counters.sw_power_cap", query)
        self.assertEqual(len(records), 1)
        self.assertEqual(
            list(records[0]),
            [
                "epoch",
                "acpi_c",
                "gpu_c",
                "power_w",
                "clock_mhz",
                "util_pct",
                "event_reasons",
                "load1",
                "mem_available_gib",
                "event_counters_us",
            ],
        )
        self.assertEqual(records[0]["event_reasons"], "0x0000000000000004")
        self.assertEqual(records[0]["event_counters_us"]["sw_power_cap"], 55157801736)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.install = (HOST / "install.sh").read_text(encoding="utf-8")

    def test_owners_are_root_or_the_service_user(self):
        owners = re.findall(r"-[og] (\S+)", self.install)
        self.assertTrue(owners)
        for owner in owners:
            self.assertRegex(owner, r'^(root|"\$\w+")$')

    def test_service_user_comes_from_the_argument_or_sudo(self):
        self.assertIn("${1:-${SUDO_USER:-}}", self.install)

    def test_refuses_without_root(self):
        self.assertIn('[ "$(id -u)" = 0 ]', self.install)

    def test_restarts_the_logger_so_a_reinstall_runs_the_new_program(self):
        # enable --now leaves a running logger on the old program (2026-10-06)
        self.assertIn("systemctl restart gb10-telemetry.service", self.install)
        self.assertNotIn("restart gb10-clock-cap", self.install)

    def test_last_record_is_read_from_one_file(self):
        # GNU tail refuses -1 with several files, and set -e ends the script there
        self.assertNotRegex(self.install, r"tail -\d")
        self.assertIn(
            'tail -n 1 "$(ls -t /var/log/gb10-telemetry/*.jsonl | head -n 1)"',
            self.install,
        )

    def test_logger_unit_has_a_substitutable_user_line(self):
        unit = (HOST / "gb10-telemetry.service").read_text(encoding="utf-8")
        self.assertRegex(unit, r"(?m)^User=@SERVICE_USER@$")
        self.assertIn("@SERVICE_USER@", self.install)

    def installed(self, text):
        """The files a part of install.sh installs, as {destination: source}."""
        files = dict(
            (dest, src)
            for src, dest in re.findall(
                r'(?m)^\s*install (?:-[ogm] \S+ )+"\$here/(\S+)" (\S+)$', text
            )
        )
        files.update(
            (dest, src)
            for src, dest in re.findall(r'"\$here/(\S+)" >(/etc/\S+)$', text, re.M)
        )
        return files

    def test_only_the_heat_cap_mark_installs_the_heat_cap(self):
        # The default installs stay byte for byte what the hosts run (2026-11-11).
        opted = re.compile(r'(?ms)^if \[ "\$heat_cap" = yes \]; then\n(.*?)^fi$')
        default = opted.sub("", self.install)
        self.assertEqual(
            self.installed(default),
            {
                "/usr/local/sbin/gb10-telemetry": "gb10-telemetry",
                "/etc/systemd/system/gb10-telemetry.service": "gb10-telemetry.service",
                "/etc/systemd/system/gb10-clock-cap.service": "gb10-clock-cap.service",
            },
        )
        self.assertNotIn("gb10-heat-cap.service", default)
        self.assertIn('units="gb10-clock-cap.service gb10-telemetry.service"', default)
        self.assertEqual(
            self.installed("".join(opted.findall(self.install))),
            {
                "/usr/local/sbin/gb10-heat-cap": "gb10-heat-cap",
                "/etc/systemd/system/gb10-heat-cap.service": "gb10-heat-cap.service",
            },
        )
        self.assertIn("--heat-cap) heat_cap=yes ;;", self.install)
        self.assertIn("heat_cap=no\n", self.install)

    def test_clock_cap_unit_keeps_its_commands(self):
        unit = (HOST / "gb10-clock-cap.service").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/usr/bin/nvidia-smi -lgc 300,2200", unit)
        self.assertIn("ExecStop=/usr/bin/nvidia-smi -rgc", unit)


if __name__ == "__main__":
    unittest.main()
