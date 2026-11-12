import re
import unittest
from pathlib import Path

LINE = Path(__file__).resolve().parents[1]
EXAMPLES = LINE / "examples"
SETTING = re.compile(r"^(\w+)=(\S*)", re.MULTILINE)
# The host a rank file is for, as its first line names it.
FOR_HOST = re.compile(r"\((edgexpert\d+)\)")


def settings(name):
    return dict(SETTING.findall((EXAMPLES / name).read_text(encoding="utf-8")))


def cluster_hosts(name):
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    return re.search(r'^HOSTS="([^"]*)"', text, re.MULTILINE)[1].split()


def for_host(name):
    first = (EXAMPLES / name).read_text(encoding="utf-8").splitlines()[0]
    return FOR_HOST.search(first)[1]


class ExampleFileTests(unittest.TestCase):
    def test_every_example_is_lf_for_bash_and_nccl(self):
        for path in sorted(EXAMPLES.iterdir()):
            with self.subTest(example=path.name):
                self.assertNotIn(b"\r", path.read_bytes())

    def test_the_examples_name_no_other_checkpoint(self):
        # The TP's checkpoint is config/tp*.env's (from 3.12.0); the other one is a
        # line the operator adds.
        for path in sorted(EXAMPLES.glob("tp*-rank*.env")):
            with self.subTest(example=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("CHECKPOINT=", text)
                self.assertNotIn("nvidia", text.lower())


class RingOfFourTests(unittest.TestCase):
    """The reference ring of four at TP=4: 04 -> 05 -> 07 -> 06 -> 04, with no cable across."""

    def test_the_cluster_file_starts_each_rank_on_its_files_host(self):
        self.assertEqual(settings("cluster.tp4.env")["TP"], "4")
        hosts = cluster_hosts("cluster.tp4.env")
        self.assertEqual(len(hosts), 4)
        for rank, host in enumerate(hosts):
            self.assertEqual(for_host(f"tp4-rank{rank}.env"), host, rank)

    def test_every_rank_takes_the_rings_lines(self):
        # gather, since split sends to every rank; the ring and its graph; connections on first use, which NCCL takes
        # only with cuMem, which the engine turns off unless the rank file sets it.
        masters = set()
        for rank in range(4):
            with self.subTest(rank=rank):
                values = settings(f"tp4-rank{rank}.env")
                masters.add(values["MASTER"])
                self.assertEqual(values["TF_GLM_PREFILL_REDUCE"], "gather")
                self.assertEqual(values["NCCL_ALGO"], "Ring")
                self.assertEqual(values["NCCL_GRAPH_FILE"], "/work/graph.xml")
                self.assertEqual(values["NCCL_RUNTIME_CONNECT"], "1")
                self.assertEqual(values["NCCL_CUMEM_ENABLE"], "1")
                text = (EXAMPLES / f"tp4-rank{rank}.env").read_text(encoding="utf-8")
                self.assertIn(
                    f"examples/tp4-rank{rank}.graph.xml to /work/graph.xml", text
                )
        self.assertEqual(len(masters), 1)

    def test_each_graph_names_its_rank_alone_on_four_channels(self):
        for rank in range(4):
            with self.subTest(rank=rank):
                graph = (EXAMPLES / f"tp4-rank{rank}.graph.xml").read_text(
                    encoding="utf-8"
                )
                self.assertIn('nchannels="4"', graph)
                self.assertEqual(graph.count("<channel>"), 4)
                self.assertEqual(
                    re.findall(r'<gpu dev="0" rank="(\d+)"/>', graph), [str(rank)] * 4
                )
                self.assertNotIn("<!--", graph)


class PairsOfTheRingTests(unittest.TestCase):
    """The ring of four as two pairs at TP=2: 04-05 and 06-07, or 04-06 and 05-07."""

    def test_each_pair_has_a_cluster_file_and_two_rank_files_with_one_master(self):
        pairs = sorted(EXAMPLES.glob("cluster.tp2-*.env"))
        self.assertEqual(
            [p.name for p in pairs],
            [f"cluster.tp2-{p}.env" for p in ("04-05", "04-06", "05-07", "06-07")],
        )
        for path in pairs:
            pair = path.name[len("cluster.tp2-") : -len(".env")]
            with self.subTest(pair=pair):
                self.assertEqual(settings(path.name)["TP"], "2")
                hosts = cluster_hosts(path.name)
                self.assertEqual(hosts, [f"edgexpert{n}" for n in pair.split("-")])
                ranks = [f"tp2-{pair}-rank{r}.env" for r in (0, 1)]
                self.assertEqual([for_host(r) for r in ranks], hosts)
                self.assertEqual(len({settings(r)["MASTER"] for r in ranks}), 1)


if __name__ == "__main__":
    unittest.main()
