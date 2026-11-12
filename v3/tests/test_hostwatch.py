import os
import subprocess
import tempfile
import unittest
from pathlib import Path

LINE = Path(__file__).resolve().parents[1]
SCRIPT = LINE / "scripts" / "hostwatch.sh"
GIB_KB = 1048576

# A stand-in for docker. `exec C ps` answers one step of ps.plan per call (fail, stall, engine, none; none past the
# end), `exec C pkill` exits with pkill.rc (or stalls on "stall"), `inspect` prints inspect.out and inspect.err and
# exits with inspect.rc. A stall is /bin/sleep, past the fake sleep on PATH. Every call is appended to calls.log.
DOCKER = r"""#!/bin/bash
here=$(dirname "$0")
echo "$*" >>"$here/calls.log"
case "$1" in
  exec)
    if [ "$3" = ps ]; then
      n=$(($(cat "$here/ps.count" 2>/dev/null || echo 0) + 1))
      echo "$n" >"$here/ps.count"
      case "$(sed -n "${n}p" "$here/ps.plan")" in
        fail) echo "Error response from daemon: context deadline exceeded" >&2; exit 1 ;;
        stall) /bin/sleep 10; exit 0 ;;
        engine) printf '%s\n' COMMAND "tensorfold-native serve --model /models/glm" ;;
        *) printf '%s\n' COMMAND bash ;;
      esac
      exit 0
    fi
    rc=$(cat "$here/pkill.rc")
    if [ "$rc" = stall ]; then /bin/sleep 10; exit 0; fi
    exit "$rc" ;;
  inspect)
    cat "$here/inspect.out"
    cat "$here/inspect.err" >&2
    exit "$(cat "$here/inspect.rc")" ;;
esac
exit 0
"""


@unittest.skipIf(os.name == "nt", "runs bash")
class HostwatchTests(unittest.TestCase):
    def watch(self, plan, gib=16, inspect=("true", "", 0), pkill_rc=0):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            for name, body in (("docker", DOCKER), ("sleep", "#!/bin/bash\nexit 0\n")):
                path = bin_dir / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)
            out, err, rc = inspect
            files = {
                "ps.plan": "".join(f"{step}\n" for step in plan),
                "inspect.out": f"{out}\n" if out else "",
                "inspect.err": f"{err}\n" if err else "",
                "inspect.rc": f"{rc}\n",
                "pkill.rc": f"{pkill_rc}\n",
            }
            for name, text in files.items():
                (bin_dir / name).write_text(text, encoding="utf-8")
            meminfo = Path(tmp) / "meminfo"
            meminfo.write_text(
                f"MemTotal: {128 * GIB_KB} kB\nMemAvailable: {gib * GIB_KB} kB\n",
                encoding="utf-8",
            )
            log = Path(tmp) / "hostwatch.log"
            subprocess.run(
                ["bash", str(SCRIPT), str(log), "glm53-tf3", str(meminfo)],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            calls_log = bin_dir / "calls.log"
            calls = (
                calls_log.read_text(encoding="utf-8").splitlines()
                if calls_log.exists()
                else []
            )
            return log.read_text(encoding="utf-8").splitlines(), calls

    def test_the_watch_ends_when_the_engine_is_gone(self):
        lines, _ = self.watch(["none"])
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].endswith(" done"))

    def test_a_failed_check_does_not_end_the_watch(self):
        lines, calls = self.watch(["fail", "fail", "engine", "none"])
        self.assertEqual(sum(line.endswith(" check-failed") for line in lines), 2)
        self.assertEqual(sum(line.endswith(" 16") for line in lines), 3)
        self.assertTrue(lines[-1].endswith(" done"))
        self.assertEqual(sum(call.startswith("inspect ") for call in calls), 2)

    def test_a_stalled_check_counts_as_failed(self):
        lines, _ = self.watch(["stall", "none"])
        self.assertEqual(sum(line.endswith(" check-failed") for line in lines), 1)
        self.assertTrue(lines[-1].endswith(" done"))

    def test_a_stalled_stop_is_logged(self):
        lines, _ = self.watch(["engine", "none"], gib=4, pkill_rc="stall")
        self.assertEqual(lines.count("KILL-FAILED"), 1)
        self.assertTrue(lines[-1].endswith(" done"))

    def test_a_docker_error_keeps_watching(self):
        for error in (
            "Cannot connect to the Docker daemon at unix:///var/run/docker.sock.",
            "failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory",
        ):
            with self.subTest(error=error):
                lines, _ = self.watch(["fail", "none"], inspect=("", error, 1))
                self.assertEqual(
                    sum(line.endswith(" check-failed") for line in lines), 1
                )
                self.assertTrue(lines[-1].endswith(" done"))

    def test_a_stopped_or_missing_container_ends_the_watch(self):
        for inspect in (
            ("false", "", 0),
            ("", "Error: No such object: glm53-tf3", 1),
            ("", "error: no such object: glm53-tf3", 1),
        ):
            with self.subTest(inspect=inspect):
                lines, _ = self.watch(["fail"], inspect=inspect)
                self.assertEqual(len(lines), 1)
                self.assertTrue(lines[0].endswith(" done"))

    def test_low_memory_stops_the_engine(self):
        lines, calls = self.watch(["engine", "none"], gib=4)
        self.assertIn("KILLED", lines)
        self.assertIn("exec glm53-tf3 pkill -9 -f tensorfold-native serve", calls)
        self.assertTrue(lines[-1].endswith(" done"))

    def test_a_failed_stop_is_logged_and_tried_again(self):
        lines, calls = self.watch(["engine", "engine", "none"], gib=4, pkill_rc=1)
        self.assertEqual(lines.count("KILL-FAILED"), 2)
        self.assertNotIn("KILLED", lines)
        self.assertEqual(sum(" pkill " in call for call in calls), 2)


if __name__ == "__main__":
    unittest.main()
