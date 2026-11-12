import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

LINE = Path(__file__).resolve().parents[1]
SCRIPT = LINE / "scripts" / "cluster.sh"

# Stand-ins for the control machine's ssh and every host's docker, all run on this machine. ssh drops its -o
# options, appends "HOST<TAB>COMMAND" to calls.log and runs the command with STUB_HOST=HOST. docker answers
# `exec C ps` with an engine line while engine.HOST exists. `exec -d` is a rank's start: it appends to the rank's
# log under STUB_WORK/logs and makes engine.HOST, but for refuse.HOST (a REFUSE line, the engine left running) and
# dies.HOST (no engine); rank 0's log gets the serving line while serves exists. `exec C pkill` on rank 0's host
# ends every engine not named in stays, on another host its own. sleep appends its argument to sleeps.log, and the
# memory guard appends "HOST ARGUMENTS" to hostwatch.log.
SSH = r"""#!/bin/bash
while [ "${1:-}" = -o ]; do shift 2; done
host=$1
shift
printf '%s\t%s\n' "$host" "$*" >>"$STUB_DIR/calls.log"
STUB_HOST=$host exec bash -c "$*"
"""
DOCKER = r"""#!/bin/bash
d=$STUB_DIR
if [ "$1" = exec ] && [ "$2" = -d ]; then
  re='serve\.sh ([0-9]+) ([0-9]+) .*serve-r[0-9]+-([^ ]+)\.log'
  [[ "$*" =~ $re ]] || exit 1
  rank=${BASH_REMATCH[2]}
  log=$STUB_WORK/logs/serve-r$rank-${BASH_REMATCH[3]}.log
  [ -e "$d/dies.$STUB_HOST" ] && { echo "[serve.sh] rank $rank" >>"$log"; exit 0; }
  touch "$d/engine.$STUB_HOST"
  [ -e "$d/refuse.$STUB_HOST" ] && { echo "[serve.sh] REFUSE: stub" >>"$log"; exit 0; }
  if [ "$rank" = 0 ] && [ -e "$d/serves" ]; then
    echo "[tensorfold] serving glm-tf at 127.0.0.1:8095" >>"$log"
  else
    echo "[tensorfold] rank $rank waiting" >>"$log"
  fi
  exit 0
fi
case "$3" in
  ps)
    echo COMMAND
    [ -e "$d/engine.$STUB_HOST" ] && echo "tensorfold-native serve /hub/x --name glm-tf"
    exit 0 ;;
  pkill)
    if [ "$STUB_HOST" = "$(cat "$d/rank0")" ]; then
      for f in "$d"/engine.*; do
        [ -e "$f" ] || continue
        grep -qx "${f##*/engine.}" "$d/stays" || rm -f "$f"
      done
    else
      rm -f "$d/engine.$STUB_HOST"
    fi
    exit 0 ;;
esac
exit 0
"""
SLEEP = '#!/bin/bash\necho "$1" >>"$STUB_DIR/sleeps.log"\n'
HOSTWATCH = 'printf "%s %s\\n" "$STUB_HOST" "$*" >>"$STUB_DIR/hostwatch.log"\n'


@unittest.skipIf(os.name == "nt", "runs bash")
class ClusterTests(unittest.TestCase):
    """cluster.sh with every host this machine, through stand-ins for ssh and docker."""

    def cluster(
        self,
        tp,
        *args,
        hosts=None,
        engines=(),
        refuse=(),
        dies=(),
        serves=True,
        stays=(),
    ):
        """Runs ``cluster.sh CLUSTER_ENV ARGS`` against hosts h0 h1 … (rank order) and returns its exit code,
        output and errors, the ssh calls as (host, command), the sleeps, and the memory guard's starts as
        (host, arguments), with the temporary folder written ROOT."""
        hosts = [f"h{r}" for r in range(tp)] if hosts is None else hosts
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name, body in (("ssh", SSH), ("docker", DOCKER), ("sleep", SLEEP)):
                path = bin_dir / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)
            watch = root / "checkout/v3/scripts/hostwatch.sh"
            watch.parent.mkdir(parents=True)
            watch.write_text(HOSTWATCH, encoding="utf-8")
            (root / "work").mkdir()
            (root / "rank0").write_text(
                f"{hosts[0] if hosts else ''}\n", encoding="utf-8"
            )
            (root / "stays").write_text(
                "".join(f"{h}\n" for h in stays), encoding="utf-8"
            )
            for prefix, named in (
                ("engine", engines),
                ("refuse", refuse),
                ("dies", dies),
            ):
                for host in named:
                    (root / f"{prefix}.{host}").touch()
            if serves:
                (root / "serves").touch()
            env_file = root / "cluster.env"
            env_file.write_text(
                f'TP={tp}\nHOSTS="{" ".join(hosts)}"\nCHECKOUT={root}/checkout\nWORK={root}/work\n',
                encoding="utf-8",
            )
            run = subprocess.run(
                ["bash", str(SCRIPT), str(env_file), *args],
                env={
                    **os.environ,
                    "PATH": f"{bin_dir}:{os.environ['PATH']}",
                    "STUB_DIR": str(root),
                    "STUB_WORK": str(root / "work"),
                },
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

            def lines(name):
                path = root / name
                text = path.read_text(encoding="utf-8") if path.exists() else ""
                return text.replace(str(root), "ROOT").splitlines()

            if run.returncode == 0 and args[:1] == ("start",):
                deadline = time.monotonic() + 10
                while (
                    len(lines("hostwatch.log")) < len(hosts)
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.05)
            return SimpleNamespace(
                code=run.returncode,
                out=run.stdout.replace(str(root), "ROOT"),
                err=run.stderr,
                calls=[tuple(x.split("\t", 1)) for x in lines("calls.log")],
                sleeps=lines("sleeps.log"),
                watches=sorted(tuple(x.split(" ", 1)) for x in lines("hostwatch.log")),
            )

    def launches(self, run):
        """The ranks' starts in order, as (host, serve.sh's arguments)."""
        found = []
        for host, command in run.calls:
            m = re.search(
                r"exec -d glm53-tf3 bash -c 'bash /opt/glm53-tf3/serve\.sh (.*?) +> /work/logs/",
                command,
            )
            if m:
                found.append((host, m[1]))
        return found

    def test_tp2_and_tp4_start_the_highest_rank_first_three_seconds_apart(self):
        for tp in (2, 4):
            with self.subTest(tp=tp):
                run = self.cluster(tp, "start", "L")
                self.assertEqual(run.code, 0, run.out + run.err)
                self.assertIn("READY after", run.out)
                self.assertEqual(
                    self.launches(run),
                    [
                        (f"h{r}", f"{tp} {r} /work/rank.env")
                        for r in reversed(range(tp))
                    ],
                )
                self.assertEqual(run.sleeps[: tp + 1], ["3"] * tp + ["10"])

    def test_tp3_starts_the_three_ranks_together_rank_0_last(self):
        run = self.cluster(3, "start", "L")
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual(
            self.launches(run),
            [(f"h{r}", f"3 {r} /work/rank.env") for r in (2, 1, 0)],
        )
        self.assertEqual(run.sleeps[0], "10")
        self.assertNotIn("3", run.sleeps)

    def test_more_serve_arguments_reach_every_rank(self):
        run = self.cluster(2, "start", "L", "--alias", "x")
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual(
            self.launches(run),
            [
                ("h1", "2 1 /work/rank.env --alias x"),
                ("h0", "2 0 /work/rank.env --alias x"),
            ],
        )

    def test_every_host_gets_the_memory_guard_after_the_last_start(self):
        run = self.cluster(3, "start", "L")
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual(
            run.watches,
            [(f"h{r}", "ROOT/work/logs/hostwatch-L.log glm53-tf3") for r in range(3)],
        )
        commands = [command for _, command in run.calls]
        last_start = max(i for i, c in enumerate(commands) if "exec -d" in c)
        first_watch = min(i for i, c in enumerate(commands) if "hostwatch.sh" in c)
        self.assertLess(last_start, first_watch)

    def test_the_wait_ends_at_rank_0s_serving_line(self):
        run = self.cluster(2, "start", "L")
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertIn("[tensorfold] serving glm-tf at 127.0.0.1:8095", run.out)
        self.assertEqual(run.sleeps.count("10"), 1)

    def test_a_rank_that_refuses_or_whose_engine_is_gone_fails_the_start(self):
        for case in ({"refuse": ["h1"]}, {"dies": ["h1"]}):
            with self.subTest(**case):
                run = self.cluster(2, "start", "L", serves=False, **case)
                self.assertEqual(run.code, 1)
                self.assertIn("FAILED on rank 1", run.out)
                self.assertIn("== rank 0\n", run.out)
                self.assertIn("== rank 1\n", run.out)

    def test_no_serving_line_after_ninety_waits_is_a_timeout(self):
        run = self.cluster(2, "start", "L", serves=False)
        self.assertEqual(run.code, 1)
        self.assertIn("TIMEOUT: no serving line after 15 minutes", run.out)
        self.assertEqual(run.sleeps.count("10"), 90)

    def test_hosts_must_name_one_host_a_rank(self):
        run = self.cluster(3, "start", "L", hosts=["h0", "h1"])
        self.assertEqual(run.code, 2)
        self.assertIn("HOSTS names 2 hosts for TP=3", run.err)
        self.assertEqual(run.calls, [])

    def test_a_host_that_runs_an_engine_stops_the_start_before_any_rank_starts(self):
        run = self.cluster(2, "start", "L", engines=["h1"])
        self.assertEqual(run.code, 1)
        self.assertIn("rank 1 h1 already runs an engine", run.out)
        self.assertEqual(self.launches(run), [])

    def test_stop_ends_rank_0_first_and_then_any_rank_left(self):
        for stays, pkills in (((), ["h0"]), (("h2",), ["h0", "h2"])):
            with self.subTest(stays=stays):
                run = self.cluster(3, "stop", engines=["h0", "h1", "h2"], stays=stays)
                self.assertEqual(run.code, 0, run.out + run.err)
                self.assertEqual(
                    [host for host, command in run.calls if "pkill" in command], pkills
                )
                for r in range(3):
                    self.assertRegex(
                        run.out,
                        rf"rank {r} h{r}: 0 engine process\(es\), MemAvailable \d+ GiB",
                    )

    def test_status_counts_each_ranks_engine(self):
        run = self.cluster(2, "status", engines=["h1"])
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(
            run.out.splitlines(),
            ["rank 0 h0: 0 engine process(es)", "rank 1 h1: 1 engine process(es)"],
        )

    def test_a_missing_or_unknown_command_or_label_is_refused(self):
        for args, code, words in (
            ((), 2, "usage: cluster.sh CLUSTER_ENV start LABEL"),
            (("restart",), 2, "unknown command 'restart': start, stop or status"),
            (("start",), 1, "start needs a LABEL for the logs"),
        ):
            with self.subTest(args=args):
                run = self.cluster(2, *args)
                self.assertEqual(run.code, code)
                self.assertIn(words, run.err)
                self.assertEqual(self.launches(run), [])


if __name__ == "__main__":
    unittest.main()
