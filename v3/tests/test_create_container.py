import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from glm53_tf import config

LINE = Path(__file__).resolve().parents[1]
SCRIPTS = LINE / "scripts"
GB10 = {n: 2808000 if n % 10 < 5 else 3900000 for n in range(20)}


@unittest.skipIf(os.name == "nt", "runs bash")
class CpusetTests(unittest.TestCase):
    def cpuset(self, freqs, **env):
        with tempfile.TemporaryDirectory() as tmp:
            for n, khz in freqs.items():
                path = Path(tmp) / f"cpu{n}/cpufreq/cpuinfo_max_freq"
                path.parent.mkdir(parents=True)
                path.write_text(f"{khz}\n", encoding="utf-8")
            (Path(tmp) / "cpuidle").mkdir()
            base = {k: v for k, v in os.environ.items() if k != "CPUSET"}
            run = subprocess.run(
                ["bash", str(SCRIPTS / "cpuset.sh"), tmp],
                env={**base, **env},
                capture_output=True,
                text=True,
                check=True,
            )
            return run.stdout.strip()

    def test_unset_gives_the_cores_with_the_lowest_maximum(self):
        self.assertEqual(self.cpuset(GB10), "0-4,10-14")
        self.assertEqual(self.cpuset(GB10, CPUSET="auto"), "0-4,10-14")

    def test_lone_cores_are_listed_without_a_range(self):
        self.assertEqual(self.cpuset({0: 2, 1: 3, 2: 2, 3: 2}), "0,2-3")
        self.assertEqual(self.cpuset({0: 3, 1: 2}), "1")

    def test_one_maximum_or_none_leaves_every_core(self):
        self.assertEqual(self.cpuset({n: 3900000 for n in range(20)}), "")
        self.assertEqual(self.cpuset({}), "")

    def test_empty_means_every_core(self):
        self.assertEqual(self.cpuset(GB10, CPUSET=""), "")

    def test_a_list_is_kept_as_given(self):
        self.assertEqual(self.cpuset(GB10, CPUSET="5-9,15-19"), "5-9,15-19")


class CreateContainerTests(unittest.TestCase):
    def test_the_cores_reach_docker_only_when_some_are_picked(self):
        script = (SCRIPTS / "create_container.sh").read_text(encoding="utf-8")
        self.assertIn('cpuset=$(bash "$(dirname "$0")/cpuset.sh")\n', script)
        self.assertIn('  cpus=(--cpuset-cpus "$cpuset")\n', script)
        self.assertIn('"${cpus[@]}"', script)


class ContainerNameTests(unittest.TestCase):
    """The scripts that reach the container, and the examples, name create_container.sh's."""

    def test_every_script_and_example_defaults_to_the_same_container(self):
        create = (SCRIPTS / "create_container.sh").read_text(encoding="utf-8")
        name = re.search(r'--name "\$\{CONTAINER:-([^}]+)\}"', create)[1]
        cluster = (SCRIPTS / "cluster.sh").read_text(encoding="utf-8")
        self.assertIn(f"CONTAINER=${{CONTAINER:-{name}}}\n", cluster)
        watch = (SCRIPTS / "hostwatch.sh").read_text(encoding="utf-8")
        self.assertIn(f"container=${{2:-{name}}}\n", watch)
        paths = sorted((LINE / "examples").glob("cluster.*.env"))
        self.assertLessEqual(
            {f"cluster.tp{tp}.env" for tp in config.TP_CHECKPOINTS},
            {p.name for p in paths},
        )
        for path in paths:
            with self.subTest(example=path.name):
                self.assertIn(f"# CONTAINER={name} ", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
