"""The heat cap in host/: its rules, its record, its state and its arguments."""

import csv
import io
import json
import os
import signal
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.test_host_kit import HOST, load, row, write_rows

DATA = Path(__file__).resolve().parent / "data" / "heat-cap-2m-prefill.csv"
DATA_2000 = Path(__file__).resolve().parent / "data" / "heat-cap-2m-prefill-2000.csv"


def read_data(path):
    """(seconds, hottest) rows of a fixture in tests/data; its first line says what it is."""
    with open(path, encoding="utf-8") as f:
        return [
            (float(t), float(c))
            for t, c in csv.reader(line for line in f if not line.startswith("#"))
        ]


def series(start, temps, step=2.0):
    """(epoch, hottest) readings every step seconds from start."""
    return [(start + i * step, t) for i, t in enumerate(temps)]


class Smi:
    """A fake nvidia-smi: records each call and fails while fail is set."""

    def __init__(self):
        self.calls = []
        self.fail = None

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if self.fail:
            return subprocess.CompletedProcess(cmd, 1, "", self.fail)
        return subprocess.CompletedProcess(cmd, 0, "", "")


class HeatCapCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cap = load("gb10-heat-cap", self.dir.name)
        self.lines = self.cap.Lines()
        self.state = os.path.join(self.dir.name, "state.json")

    def tearDown(self):
        self.dir.cleanup()

    def replay(self, readings, cap=2200):
        """Feed readings one by one to decide; the (epoch, from, to, decision) changes."""
        since, seen, changes = readings[0][0], [], []
        for reading in readings:
            seen.append(reading)
            d = self.cap.decide(cap, seen, reading[0], since, self.lines)
            if d.mhz != cap:
                changes.append((reading[0], cap, d.mhz, d))
                cap = d.mhz
                since = reading[0]
        return changes

    def watch(self):
        return self.cap.Watch(self.lines, "nvidia-smi", self.dir.name, self.state)

    def step(self, watch, smi, now=None):
        with (
            patch.object(self.cap.subprocess, "run", smi),
            redirect_stdout(io.StringIO()),
        ):
            watch.step(time.time() if now is None else now)

    def events(self):
        path = Path(self.dir.name, self.cap.EVENTS)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


class RuleTests(HeatCapCase):
    def test_defaults_are_the_agreed_lines(self):
        self.assertEqual(
            tuple(self.lines), (90.0, 75.0, 300.0, 0.5, 120.0, 2000, 2200, 30.0)
        )

    def test_below_the_lines_stays_at_the_top(self):
        self.assertEqual(self.replay(series(0, [89.9] * 400)), [])

    def test_hot_time_over_half_the_window_lowers_the_cap_at_that_reading(self):
        # Each reading stands for the 2 s since the one before: the 75th hot reading
        # makes 150 s (not over half), the 76th 152 s.
        changes = self.replay(series(0, [60.0] + [90.0] * 100))
        self.assertEqual(len(changes), 1)
        epoch, before, after, decision = changes[0]
        self.assertEqual(
            (epoch, before, after, decision.reason), (152.0, 2200, 2000, "hot")
        )
        self.assertEqual(decision.hot_s, 152.0)

    def test_hot_time_counts_only_the_window(self):
        # 98 s hot, 220 s cool, then 150 s hot: over half only if the first 98 s stayed.
        temps = [90.0] * 50 + [70.0] * 110 + [90.0] * 75
        self.assertEqual(self.replay(series(0, temps)), [])

    def test_cool_for_the_hold_raises_the_cap_and_not_before(self):
        readings = series(0, [92.0] + [75.0] * 61)
        decisions = [
            self.cap.decide(2000, readings[: i + 1], readings[i][0], 0.0, self.lines)
            for i in range(len(readings))
        ]
        self.assertTrue(all(d.mhz == 2000 for d in decisions[:-1]))
        self.assertEqual(decisions[-2].cool_s, 118.0)
        self.assertEqual((decisions[-1].mhz, decisions[-1].reason), (2200, "cool"))
        self.assertEqual(decisions[-1].cool_s, 120.0)

    def test_a_warmer_reading_during_the_hold_starts_it_over(self):
        temps = [70.0] * 59 + [75.1] + [70.0] * 61
        readings = series(0, temps)
        changes = self.replay(readings, cap=2000)
        self.assertEqual(len(changes), 1)
        # Cool from 120 s, after the warm reading at 118 s: 120 s at 240 s.
        self.assertEqual(changes[0][0], 240.0)

    def test_a_reading_without_a_zone_starts_the_hold_over(self):
        self.assertEqual(
            self.cap.cool_seconds(series(0, [80.0, None, 80.0, 80.0]), 85.0, 30.0),
            2.0,
        )
        self.assertEqual(self.cap.hottest(row([None, None])), None)

    def test_a_gap_in_the_record_starts_the_hold_over(self):
        readings = [(0.0, 80.0), (100.0, 80.0), (102.0, 80.0)]
        self.assertEqual(self.cap.cool_seconds(readings, 85.0, 30.0), 2.0)

    def test_a_gap_counts_at_most_the_stale_seconds_as_hot(self):
        readings = [(0.0, 95.0), (100.0, 95.0), (102.0, 95.0)]
        self.assertEqual(self.cap.hot_seconds(readings, -1.0, 90.0, 30.0), 32.0)

    def test_after_a_return_hot_time_counts_from_the_return(self):
        # 300 s hot, 120 s cool: back at the top with 180 s of hot readings still in the
        # window. Counted from the return, the cap stays at the top.
        temps = [60.0] + [95.0] * 150 + [70.0] * 61 + [86.0] * 40
        changes = self.replay(series(0, temps))
        self.assertEqual([(c[1], c[2]) for c in changes], [(2200, 2000), (2000, 2200)])

    def test_stale_or_missing_record_lowers_the_cap(self):
        readings = series(0, [60.0])
        stale = self.cap.decide(2200, readings, 30.1, 0.0, self.lines)
        self.assertEqual((stale.mhz, stale.reason), (2000, "telemetry stale"))
        fresh = self.cap.decide(2200, readings, 30.0, 0.0, self.lines)
        self.assertEqual(fresh.mhz, 2200)
        missing = self.cap.decide(2200, [], 0.0, 0.0, self.lines)
        self.assertEqual((missing.mhz, missing.reason), (2000, "no telemetry"))

    def test_after_a_stale_record_the_return_needs_the_hold(self):
        readings = series(0, [70.0] * 100) + series(300, [70.0] * 2)
        decision = self.cap.decide(2000, readings, 302.0, 0.0, self.lines)
        self.assertEqual((decision.mhz, decision.cool_s), (2000, 2.0))

    def test_start_takes_the_top_unless_stale(self):
        fresh = self.cap.decide(None, series(0, [95.0]), 1.0, None, self.lines)
        self.assertEqual((fresh.mhz, fresh.reason), (2200, "start"))
        stale = self.cap.decide(None, series(0, [60.0]), 60.0, None, self.lines)
        self.assertEqual(stale.mhz, 2000)

    def test_never_locks_above_the_top(self):
        with self.assertRaises(ValueError):
            self.cap.lock("nvidia-smi", 2201, 2200)
        with self.assertRaises(ValueError):
            self.cap.lock("nvidia-smi", 300, 2200)
        # Nor above the boot unit's 2,200 MHz, whatever top it is given.
        with self.assertRaises(ValueError):
            self.cap.lock("nvidia-smi", 2300, 2400)


class RealDataTests(HeatCapCase):
    """2M-token prefills at 2200 MHz (2026-11-11) and 2000 MHz (2026-11-12) in tests/data."""

    def test_the_prefill_lowers_the_cap_in_its_seventh_minute_and_returns_after(self):
        rows = read_data(DATA)
        changes = self.replay(rows)
        self.assertEqual([(c[1], c[2]) for c in changes], [(2200, 2000), (2000, 2200)])
        prefill_start, prefill_end = 449.2, 1851.6
        lowered, raised = changes[0][0], changes[1][0]
        self.assertEqual(lowered, 857.1)
        self.assertTrue(5 * 60 <= lowered - prefill_start <= 7 * 60)
        # The record was taken at 2200 MHz throughout, so the return is that host's.
        self.assertEqual(raised, 1975.9)
        self.assertAlmostEqual(raised - prefill_end, 124.3, places=1)

    def test_at_2000_mhz_the_cap_holds_through_the_prefill_and_returns_after(self):
        # Loaded at 2000 MHz the hottest zone moves between 79 and 89 C, so a return
        # line inside that band would raise the cap in the middle of the prefill.
        rows = read_data(DATA_2000)
        load_end = 4918.0  # its last reading at 40 W or more (the data's first line)
        # From the prefill's first reading at 88 C, as if the cap had just come down.
        first = next(i for i, (_, c) in enumerate(rows) if c >= 88.0)
        self.assertEqual(rows[first][0], 3944.0)
        changes = self.replay(rows[first:], cap=2000)
        self.assertEqual([(c[1], c[2]) for c in changes], [(2000, 2200)])
        self.assertGreater(changes[0][0], load_end)
        # The zone is at or below the line 4 s after the load, so the return is the hold later.
        self.assertEqual(changes[0][0] - load_end, 124.0)


class WatchTests(HeatCapCase):
    def test_reads_the_previous_day_file_just_after_the_day_changes(self):
        now = time.time()
        Path(self.dir.name, "2026-11-10.jsonl").write_text(
            json.dumps(row([70.0], epoch=now - 4)) + "\n", encoding="utf-8"
        )
        Path(self.dir.name, "2026-11-11.jsonl").write_text(
            json.dumps(row([71.0], epoch=now - 2)) + '\n{"epoch": 1', encoding="utf-8"
        )
        rows = self.cap.tail_rows(self.dir.name)
        self.assertEqual([r["acpi_c"] for r in rows], [[70.0], [71.0]])

    def test_start_locks_the_top_and_records_it(self):
        write_rows(self.dir.name, row([60.0]))
        smi, watch = Smi(), self.watch()
        self.step(watch, smi)
        self.assertEqual(smi.calls, [["nvidia-smi", "-lgc", "300,2200"]])
        (event,) = self.events()
        self.assertEqual(
            (event["from_mhz"], event["to_mhz"], event["reason"], event["result"]),
            (None, 2200, "start", "set"),
        )
        self.assertEqual(event["acpi_max_c"], 60.0)

    def test_start_without_a_record_locks_the_hot_cap(self):
        smi, watch = Smi(), self.watch()
        self.step(watch, smi)
        self.assertEqual(smi.calls, [["nvidia-smi", "-lgc", "300,2000"]])
        self.assertEqual(self.events()[0]["reason"], "no telemetry")

    def test_a_failed_lock_does_not_end_the_watch_and_is_tried_again(self):
        write_rows(self.dir.name, row([60.0]))
        smi, watch = Smi(), self.watch()
        smi.fail = "Unable to set clocks"
        self.step(watch, smi)
        self.step(watch, smi)
        self.assertIsNone(watch.cap)
        smi.fail = None
        self.step(watch, smi)
        self.assertEqual(watch.cap, 2200)
        self.assertEqual(len(smi.calls), 3)
        # One line for the cause, not one per reading, then the lock.
        self.assertEqual(
            [(e["result"], e.get("error")) for e in self.events()],
            [("failed", "exit 1: Unable to set clocks"), ("set", None)],
        )

    def test_a_failed_change_keeps_the_state_of_the_cap_in_force(self):
        now = float(int(time.time()))
        write_rows(self.dir.name, row([60.0], epoch=now))
        smi, watch = Smi(), self.watch()
        self.step(watch, smi, now=now)
        smi.fail = "Unable to set clocks"
        self.step(watch, smi, now=now + 31)  # stale: wants 2000
        state = json.loads(Path(self.state).read_text("utf-8"))
        self.assertEqual(
            (state["mhz"], state["changed_epoch"], state["reason"]),
            (2200, now, "start"),
        )
        self.assertEqual(
            (state["wanted_mhz"], state["error_epoch"], state["error"]),
            (2000, now + 31, "exit 1: Unable to set clocks"),
        )
        smi.fail = None
        self.step(watch, smi, now=now + 33)
        state = json.loads(Path(self.state).read_text("utf-8"))
        self.assertEqual(
            (state["mhz"], state["changed_epoch"], state["reason"]),
            (2000, now + 33, "telemetry stale"),
        )
        self.assertNotIn("error", state)

    @unittest.skipIf(os.name == "nt", "POSIX file modes")
    def test_the_state_file_is_readable_by_every_user(self):
        write_rows(self.dir.name, row([60.0]))
        self.step(self.watch(), Smi())
        self.assertEqual(os.stat(self.state).st_mode & 0o777, 0o644)

    def test_a_hung_nvidia_smi_is_cut_at_the_stale_line_and_tried_again(self):
        write_rows(self.dir.name, row([60.0]))
        watch, waits = self.watch(), []

        def hung(cmd, **kwargs):
            waits.append(kwargs.get("timeout"))
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

        self.step(watch, hung)
        self.assertIsNone(watch.cap)
        self.assertEqual(waits, [30.0])
        (event,) = self.events()
        self.assertEqual(
            (event["result"], event["error"]), ("failed", "no answer in 30 s")
        )
        self.step(watch, Smi())
        self.assertEqual(watch.cap, 2200)

    def test_a_record_that_goes_stale_at_the_hot_cap_is_one_line(self):
        smi, watch = Smi(), self.watch()
        now = float(int(time.time()))
        temps = [95.0] * 80  # 2200 at the start, 2000 once hot for over 150 s
        start = now - 2 * len(temps)
        for epoch, acpi in series(start, temps):
            write_rows(self.dir.name, row([acpi], epoch=epoch))
            self.step(watch, smi, now=epoch)
        self.assertEqual(watch.cap, 2000)
        last = start + 2 * (len(temps) - 1)
        for later in (31, 33, 35):  # stale from 31 s on: one line, not one per reading
            self.step(watch, smi, now=last + later)
        write_rows(self.dir.name, row([95.0], epoch=last + 37))
        self.step(watch, smi, now=last + 37)  # fresh again
        self.step(watch, smi, now=last + 37 + 31)  # stale again: one more line
        self.assertEqual(
            [
                (e["reason"], e["result"], e["from_mhz"], e["to_mhz"])
                for e in self.events()
            ],
            [
                ("start", "set", None, 2200),
                ("hot", "set", 2200, 2000),
                ("telemetry stale", "kept", 2000, 2000),
                ("telemetry stale", "kept", 2000, 2000),
            ],
        )
        self.assertEqual(len(smi.calls), 2)  # keeping the cap calls no nvidia-smi
        state = json.loads(Path(self.state).read_text("utf-8"))
        self.assertEqual((state["mhz"], state["reason"]), (2000, "hot"))

    def test_a_change_for_a_stale_record_is_not_noted_again(self):
        now = float(int(time.time()))
        write_rows(self.dir.name, row([60.0], epoch=now))
        smi, watch = Smi(), self.watch()
        for later in (0, 31, 33, 35):  # start, then stale: 2000 once
            self.step(watch, smi, now=now + later)
        self.assertEqual(
            [(e["reason"], e["result"]) for e in self.events()],
            [("start", "set"), ("telemetry stale", "set")],
        )

    def test_a_missing_nvidia_smi_does_not_end_the_watch(self):
        write_rows(self.dir.name, row([60.0]))
        watch = self.cap.Watch(
            self.lines, os.path.join(self.dir.name, "absent"), self.dir.name, self.state
        )
        with redirect_stdout(io.StringIO()):
            watch.step(time.time())
        self.assertIsNone(watch.cap)
        self.assertEqual(self.events()[0]["result"], "failed")

    def test_the_events_file_is_not_taken_for_the_record(self):
        self.assertFalse(self.cap.EVENTS.endswith(".jsonl"))
        write_rows(self.dir.name, row([60.0]))
        smi, watch = Smi(), self.watch()
        self.step(watch, smi)
        gate = load("cool-gate", self.dir.name)
        self.assertEqual(gate.last_row()["acpi_c"], [60.0])
        self.assertEqual(len(self.cap.tail_rows(self.dir.name)), 1)

    def test_the_state_file_holds_the_cap_and_status_prints_it(self):
        write_rows(self.dir.name, row([60.0]))
        smi, watch = Smi(), self.watch()
        now = float(int(time.time()))
        self.step(watch, smi, now=now)
        state = json.loads(Path(self.state).read_text("utf-8"))
        self.assertEqual(
            (state["mhz"], state["changed_epoch"], state["reason"], state["running"]),
            (2200, now, "start", True),
        )
        self.assertEqual(
            [p.name for p in Path(self.dir.name).iterdir() if p.name.startswith(".")],
            [],
        )
        out = io.StringIO()
        with redirect_stdout(out):
            code = self.cap.main(["--status", "--state-file", self.state])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().count("\n"), 1)
        self.assertEqual(json.loads(out.getvalue()), state)

    def test_status_without_a_state_file_exits_1(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = self.cap.main(["--status", "--state-file", self.state])
        self.assertEqual((code, json.loads(out.getvalue())["result"]), (1, "absent"))

    def test_sigterm_locks_the_top_and_ends(self):
        write_rows(self.dir.name, row([60.0], epoch=time.time() - 60))
        smi = Smi()
        previous = signal.getsignal(signal.SIGTERM)

        def sleep(seconds):
            signal.raise_signal(signal.SIGTERM)

        try:
            with (
                patch.object(self.cap.subprocess, "run", smi),
                patch.object(self.cap.time, "sleep", sleep),
                redirect_stdout(io.StringIO()),
            ):
                code = self.cap.main(
                    ["--log-dir", self.dir.name, "--state-file", self.state]
                )
        finally:
            signal.signal(signal.SIGTERM, previous)
        self.assertEqual(code, 0)
        self.assertEqual(
            smi.calls,
            [["/usr/bin/nvidia-smi", "-lgc", "300,2000"]]
            + [["/usr/bin/nvidia-smi", "-lgc", "300,2200"]],
        )
        self.assertEqual(self.events()[-1]["reason"], "stop")
        state = json.loads(Path(self.state).read_text("utf-8"))
        self.assertEqual((state["mhz"], state["running"]), (2200, False))

    def test_never_resets_the_clocks_and_never_exceeds_the_top(self):
        smi, watch = Smi(), self.watch()
        now = time.time()
        temps = [60.0] + [95.0] * 100 + [70.0] * 70 + [95.0] * 100
        start = now - 2 * len(temps)
        for epoch, acpi in series(start, temps):
            write_rows(self.dir.name, row([acpi], epoch=epoch))
            self.step(watch, smi, now=epoch)
        locked = [int(c[2].split(",")[1]) for c in smi.calls]
        self.assertEqual(locked, [2200, 2000, 2200, 2000])
        self.assertTrue(all(c[1] == "-lgc" for c in smi.calls))
        self.assertLessEqual(max(locked), 2200)
        # No argument list of the script holds the reset (its docstring names it).
        self.assertNotIn('"-rgc"', (HOST / "gb10-heat-cap").read_text("utf-8"))


class ArgumentTests(HeatCapCase):
    def refused(self, *argv):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as stop:
            self.cap.parse(list(argv))
        return stop.exception.code, err.getvalue()

    def test_bad_values_exit_2_naming_the_argument_the_value_and_the_form(self):
        cases = [
            (("--high", "hot"), "--high", "'hot'", "a temperature above 0 C"),
            (("--low", "nan"), "--low", "'nan'", "a temperature"),
            (("--window", "0"), "--window", "'0'", "seconds above 0"),
            (("--share", "1"), "--share", "'1'", "a fraction between 0 and 1"),
            (("--hold", "-5"), "--hold", "'-5'", "seconds above 0"),
            (("--hot-mhz", "1999.5"), "--hot-mhz", "'1999.5'", "whole number of MHz"),
            (("--top-mhz", "300"), "--top-mhz", "'300'", "MHz above 300"),
            (("--top-mhz", "2201"), "--top-mhz", "'2201'", "at most 2200"),
            (("--stale", "2"), "--stale", "'2'", "seconds above 2"),
            (("--high", "inf"), "--high", "'inf'", "a temperature"),
        ]
        for argv, name, value, form in cases:
            with self.subTest(argv=argv):
                code, err = self.refused(*argv)
                self.assertEqual(code, 2)
                for part in (name, value, form):
                    self.assertIn(part, err)

    def test_lines_that_contradict_each_other_exit_2(self):
        for argv, text in [
            (("--low", "90"), "--low 90.0 must be below --high 90.0"),
            (("--hot-mhz", "2300"), "--hot-mhz 2300 must be below --top-mhz 2200"),
            (("--log-dir", " "), "--log-dir must not be empty"),
        ]:
            with self.subTest(argv=argv):
                code, err = self.refused(*argv)
                self.assertEqual(code, 2)
                self.assertIn(text, err)

    def test_every_line_can_be_changed(self):
        args = self.cap.parse(
            "--high 91 --low 84 --window 200 --share 0.6 --hold 60 "
            "--hot-mhz 1900 --top-mhz 2100 --stale 20 --nvidia-smi /x "
            "--log-dir /d --state-file /s".split()
        )
        self.assertEqual(
            (args.high, args.low, args.window, args.share, args.hold),
            (91.0, 84.0, 200.0, 0.6, 60.0),
        )
        self.assertEqual(
            (args.hot_mhz, args.top_mhz, args.stale, args.nvidia_smi),
            (1900, 2100, 20.0, "/x"),
        )
        self.assertEqual((args.log_dir, args.state_file), ("/d", "/s"))

    def test_log_dir_defaults_to_the_environment(self):
        self.assertEqual(self.cap.parse([]).log_dir, self.dir.name)


class UnitTests(unittest.TestCase):
    def test_unit_runs_after_the_cap_and_the_logger_and_restarts_on_failure(self):
        unit = (HOST / "gb10-heat-cap.service").read_text(encoding="utf-8")
        for line in (
            "Type=simple",
            "After=gb10-clock-cap.service gb10-telemetry.service",
            # Stopping the cap unit resets the clocks (-rgc) and restarting it locks 2200:
            # either one stops or restarts the heat cap too, which locks 2200 on its way out.
            "PartOf=gb10-clock-cap.service",
            "ExecStart=/usr/local/sbin/gb10-heat-cap",
            "Restart=on-failure",
        ):
            self.assertRegex(unit, rf"(?m)^{line}$")
        self.assertNotIn("User=", unit)  # nvidia-smi -lgc needs root


if __name__ == "__main__":
    unittest.main()
