import ast
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from glm53_tf import config, mojibake

LINE = Path(__file__).resolve().parents[1]
# The TP sizes serve.sh takes, each with its release file config/tp*.env.
SIZES = (2, 3, 4)
SETTING = re.compile(r"^(\w+)=(\S*)", re.MULTILINE)
WIRE = (
    "TF_TP_MASTER",
    "TF_TP_PORT",
    "TF_TP_PLAN_TIMEOUT",
    "TF_TP_KERNEL_IMAGE",
    "TF_TP_ROCE_FALLBACK",
)


def folder(name):
    """A checkpoint's folder in the container at its lock's revision, as tp*.env and the rank files name it."""
    model, revision, _ = config.checkpoint(name, Path("state"))
    return f"/hub/models--{model.replace('/', '--')}/snapshots/{revision}"


def defaults(tp):
    """A TP's defaults as tp2.env, tp3.env and tp4.env write them."""
    return dict(
        SETTING.findall((LINE / f"config/tp{tp}.env").read_text(encoding="utf-8"))
    )


SERVE_ARG = re.compile(r'--(name|host|port) "\$\{\w+:-([^}]*)\}"')


def serve_defaults():
    """The name, host and port serve.sh serves when the rank file sets none, and its reply cap."""
    script = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
    found = dict(SERVE_ARG.findall(script))
    found["max-tokens"] = int(re.search(r"--max-tokens (\d+)", script)[1])
    return found


def source_default(module, name):
    """The default of a module's ``NAME = os.environ.get("NAME", default)``, read from its
    source, so the runner's environment cannot move it."""
    tree = ast.parse((LINE / "glm53_tf" / f"{module}.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value.args[1])
    raise AssertionError(f"{module}.py sets no {name}")


class ReleaseDefaultsTests(unittest.TestCase):
    def test_every_tp_size_names_the_same_settings(self):
        for tp in SIZES[1:]:
            self.assertEqual(list(defaults(tp)), list(defaults(2)), tp)

    def test_every_setting_is_in_the_configuration_documents(self):
        for name in ("configuration.md", "configuration.ja.md"):
            text = (LINE / "docs" / name).read_text(encoding="utf-8")
            for key in defaults(2):
                self.assertIn(f"`{key}`", text, name)

    def test_the_kept_prompts_clear_the_engines_warning(self):
        # The engine warns below four kept states a stream (fewStates).
        for tp in SIZES:
            values = defaults(tp)
            self.assertGreaterEqual(
                int(values["TF_KV_SHARE"]), 4 * int(values["PARALLEL"])
            )

    def test_the_files_are_lf_for_bash(self):
        for tp in SIZES:
            self.assertNotIn(b"\r", (LINE / f"config/tp{tp}.env").read_bytes())

    def test_the_image_puts_the_defaults_and_the_kernels_beside_serve_sh(self):
        image = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY v3/config/tp2.env v3/config/tp3.env v3/config/tp4.env /opt/glm53-tf3/\n",
            image,
        )
        self.assertIn(
            "COPY --from=build /out/tp_mailbox.fatbin /opt/glm53-tf3/\n", image
        )
        context = (LINE.parent / ".dockerignore").read_text(encoding="utf-8")
        for tp in SIZES:
            self.assertIn(f"!v3/config/tp{tp}.env\n", context)

    def test_cluster_sh_starts_the_serve_sh_the_image_copies(self):
        image = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        dest = re.search(r"^COPY v3/scripts/serve\.sh (\S+)$", image, re.MULTILINE)[1]
        cluster = (LINE / "scripts/cluster.sh").read_text(encoding="utf-8")
        self.assertIn(f"bash {dest} $TP $1 /work/rank.env", cluster)

    def test_serve_sh_logs_the_engine_ref_where_the_image_records_it(self):
        image = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        dest = re.search(r"^COPY --from=build /out/ENGINE (\S+)$", image, re.MULTILINE)[
            1
        ]
        self.assertIn('printf "engine %s\\nref %s\\n', image)
        serve = (LINE / "scripts/serve.sh").read_text(encoding="utf-8")
        self.assertIn(f"sed -n 's/^ref //p' {dest}", serve)


class ToolDefaultsTests(unittest.TestCase):
    """The tools default to the address, name and reply cap serve.sh gives rank 0's engine."""

    def test_the_clients_default_to_serve_sh_s_address_and_name(self):
        serve = serve_defaults()
        for module in ("bench", "decode_check", "long_input", "mojibake"):
            self.assertEqual(
                source_default(module, "BASE"),
                f"http://{serve['host']}:{serve['port']}",
                module,
            )
            self.assertEqual(source_default(module, "MODEL"), serve["name"], module)

    def test_the_tool_gate_relays_to_serve_sh_s_address(self):
        serve = serve_defaults()
        proxy = (LINE / "glm53_tf/tool_gate/proxy.py").read_text(encoding="utf-8")
        self.assertIn(
            f'add_argument("--upstream", default="http://{serve["host"]}:{serve["port"]}")',
            proxy,
        )

    def test_mojibake_asks_for_serve_sh_s_reply_cap(self):
        self.assertEqual(mojibake.MAX_TOKENS, serve_defaults()["max-tokens"])


@unittest.skipIf(os.name == "nt", "runs bash")
class ServeTests(unittest.TestCase):
    def run_serve(self, tp, rank_file="", rank="0", release=None):
        """serve.sh beside the release's files with the engine stubbed: its exit code, output (the temporary
        folder as ROOT) and errors. Both checkpoints' folders are made under ROOT/hub, which the release's files
        and the rank file name for /hub; release, if given, rewrites tp{tp}.env's text."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(LINE / "scripts/serve.sh", root)
            for n in SIZES:
                text = (LINE / f"config/tp{n}.env").read_text(encoding="utf-8")
                if n == tp and release:
                    text = release(text)
                hub = text.replace("/hub/", f"{root}/hub/")
                (root / f"tp{n}.env").write_text(hub, encoding="utf-8")
            for name in config.CHECKPOINTS:
                (root / folder(name).lstrip("/")).mkdir(parents=True)
            rank_env = root / "rank.env"
            rank_file = rank_file.replace("/hub/", f"{root}/hub/")
            rank_env.write_text("MASTER=10.0.0.1\n" + rank_file, encoding="utf-8")
            engine = root / "tensorfold-native"
            engine.write_text(
                '#!/bin/bash\nprintf "arg %s\\n" "$@"\nprintenv\n', encoding="utf-8"
            )
            engine.chmod(0o755)
            run = subprocess.run(
                ["bash", str(root / "serve.sh"), str(tp), rank, str(rank_env)],
                env={"PATH": f"{root}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            return run.returncode, run.stdout.replace(str(root), "ROOT"), run.stderr

    def serve(self, tp, rank_file="", rank="0"):
        """serve.sh with the engine stubbed: its arguments, environment and start line."""
        code, out, err = self.run_serve(tp, rank_file, rank)
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        args = [x[4:] for x in lines if x.startswith("arg ")]
        env = dict(
            x.split("=", 1)
            for x in lines
            if "=" in x and not x.startswith(("arg ", "[serve.sh]"))
        )
        start = next(x for x in lines if x.startswith("[serve.sh]"))
        return args, env, start

    def flag(self, args, name):
        return args[args.index(name) + 1] if name in args else None

    def test_tp2_serves_one_person_on_the_share_at_the_whole_window(self):
        args, env, _ = self.serve(2)
        self.assertEqual(self.flag(args, "--context"), "1048576")
        self.assertEqual(self.flag(args, "--parallel"), "4")
        self.assertNotIn("--mtp-confidence", args)
        self.assertEqual(env["TF_KV_SHARE"], "16")
        self.assertEqual(env["TENSORFOLD_PREFILL_SHARE"], "0.7")
        # tp2.env's empty value: off
        self.assertEqual(env.get("TF_GLM_CHUNK_SOLO", ""), "")
        self.assertEqual(env["TF_GLM_ROCE_MULTI"], "0")
        self.assertNotIn("TF_TP_MASTER", env)
        self.assertEqual(env["TENSORFOLD_MEMORY_RESERVE_GIB"], "9")

    def test_tp3_serves_several_people_on_the_wire(self):
        args, env, _ = self.serve(3)
        self.assertEqual(self.flag(args, "--context"), "1048576")
        self.assertEqual(self.flag(args, "--parallel"), "8")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.5")
        self.assertEqual(env["TF_KV_SHARE"], "32")
        self.assertEqual(env["TF_GLM_ROCE_MULTI"], "1")
        self.assertEqual(env["TF_TP_MASTER"], "10.0.0.1")
        self.assertEqual(env["TF_TP_KERNEL_IMAGE"], "ROOT/tp_mailbox.fatbin")
        self.assertEqual(env["TF_TP_ROCE_FALLBACK"], "error")
        self.assertEqual(env["TENSORFOLD_MEMORY_RESERVE_GIB"], "16")

    def test_tp4_serves_tp3s_values_with_the_wire_off(self):
        args, env, _ = self.serve(4)
        self.assertEqual(self.flag(args, "--context"), "1048576")
        self.assertEqual(self.flag(args, "--parallel"), "8")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.5")
        self.assertEqual(env["TF_KV_SHARE"], "32")
        self.assertEqual(env["TENSORFOLD_PREFILL_SHARE"], "0.7")
        self.assertEqual(env["TF_GLM_ROCE_MULTI"], "0")
        for key in WIRE:
            self.assertNotIn(key, env)
        self.assertEqual(env["TENSORFOLD_MEMORY_RESERVE_GIB"], "14")
        self.assertEqual(env["TF_GLM_WORLD"], "4")

    def test_each_rank_of_a_tp_starts_and_no_other(self):
        for tp in SIZES:
            for rank in range(tp):
                with self.subTest(tp=tp, rank=rank):
                    _, env, _ = self.serve(tp, rank=str(rank))
                    self.assertEqual(env["TF_GLM_RANK"], str(rank))
        code, out, err = self.run_serve(3, rank="3")
        self.assertEqual(code, 2, err)
        self.assertIn("rank 3 is outside TP=3", err)
        self.assertNotIn("[serve.sh]", out)
        code, _, err = self.run_serve(4, rank="4")
        self.assertEqual(code, 2, err)
        self.assertIn("rank is 0, 1, 2 or 3, not '4'", err)
        for tp in (1, 5):
            with self.subTest(tp=tp):
                code, _, err = self.run_serve(tp)
                self.assertEqual(code, 2, err)
                self.assertIn(f"TP is 2, 3 or 4, not '{tp}'", err)

    def test_the_rank_file_wins(self):
        args, env, _ = self.serve(
            2, "PARALLEL=2\nTF_KV_SHARE=8\nCONTEXT=262144\nMTP_CONFIDENCE=0.6\n"
        )
        self.assertEqual(self.flag(args, "--parallel"), "2")
        self.assertEqual(self.flag(args, "--context"), "262144")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.6")
        self.assertEqual(env["TF_KV_SHARE"], "8")

    def test_each_tp_serves_its_checkpoint_and_one_line_serves_the_other(self):
        # From 3.12.0 Jammed XSFP4 at TP=2 and XSFP4 at TP=3 and TP=4 (tp*.env); the rank file's CHECKPOINT line
        # changes that and nothing else, and an empty one keeps the TP's.
        for tp in SIZES:
            own = config.TP_CHECKPOINTS[tp]
            other = "xsfp4" if own == "jammed" else "jammed"
            with self.subTest(tp=tp):
                base, _, start = self.serve(tp)
                self.assertEqual(base[:2], ["serve", "ROOT" + folder(own)])
                self.assertTrue(start.endswith(f" checkpoint ROOT{folder(own)}"), start)
                args = self.serve(tp, f"CHECKPOINT={folder(other)}\n")[0]
                self.assertEqual(args[:2], ["serve", "ROOT" + folder(other)])
                self.assertEqual(args[2:], base[2:])
                self.assertEqual(self.serve(tp, "CHECKPOINT=\n")[0], base)
        self.assertEqual(config.TP_CHECKPOINTS[2], "jammed")

    def test_a_folder_the_host_lacks_stops_the_start_and_says_what_to_do(self):
        code, out, err = self.run_serve(2, "CHECKPOINT=/hub/models--a--b/snapshots/0\n")
        self.assertEqual(code, 2, err)
        self.assertIn("CHECKPOINT: no folder", err)
        self.assertIn("download --tp 2", err)
        self.assertNotIn("[serve.sh]", out)

    def test_a_release_file_without_a_checkpoint_stops_the_start(self):
        code, out, err = self.run_serve(
            3, release=lambda text: re.sub(r"(?m)^CHECKPOINT=.*\n", "", text)
        )
        self.assertNotEqual(code, 0)
        self.assertIn("tp3.env names no CHECKPOINT", err)
        self.assertNotIn("[serve.sh]", out)

    def test_an_empty_value_turns_a_number_or_word_setting_off(self):
        args, env, _ = self.serve(
            3,
            "PARALLEL=\nTF_KV_SHARE=\nTENSORFOLD_PREFILL_SHARE=\nMTP_CONFIDENCE=\nTF_GLM_ROCE_MULTI=0\n"
            "TENSORFOLD_MEMORY_RESERVE_GIB=\n",
        )
        self.assertNotIn("--parallel", args)
        self.assertNotIn("--mtp-confidence", args)
        off = (
            "TF_KV_SHARE",
            "TENSORFOLD_PREFILL_SHARE",
            "TF_GLM_CHUNK_SOLO",
        )
        # From upstream 1.2.6 the engine reads an empty value as unset, so serve.sh passes it on as it is.
        for key in off + ("TENSORFOLD_MEMORY_RESERVE_GIB",):
            self.assertEqual(env.get(key, ""), "", key)
        for key in WIRE:
            self.assertNotIn(key, env)

    def test_the_heat_bands_reach_the_engine_and_empty_ones_reach_it_empty(self):
        _, env, start = self.serve(3)
        self.assertEqual((env["TF_HEAT_HIGH"], env["TF_HEAT_LOW"]), ("92", "88"))
        self.assertIn("heat 92/88", start)
        _, env, start = self.serve(3, "TF_HEAT_HIGH=\nTF_HEAT_LOW=\n")
        self.assertEqual((env["TF_HEAT_HIGH"], env["TF_HEAT_LOW"]), ("", ""))
        self.assertIn("heat unset/unset", start)

    def test_an_empty_context_keeps_the_releases_window(self):
        args, _, _ = self.serve(2, "CONTEXT=\n")
        self.assertEqual(self.flag(args, "--context"), "1048576")

    def test_the_on_off_settings_take_one_or_zero(self):
        for name in (
            "VISION",
            "TF_GLM_ROCE_MULTI",
            "TF_GLM_PROMPT_PAIR",
            "TF_GLM_L2PF",
        ):
            for value in ("0", "1"):
                with self.subTest(name=name, value=value):
                    _, env, _ = self.serve(3, f"{name}={value}\n")
                    if name != "VISION":
                        self.assertEqual(env[name], value)
            for value in ("", "yes", "true", "2", "off"):
                with self.subTest(name=name, value=value):
                    code, out, err = self.run_serve(3, f"{name}={value}\n")
                    self.assertEqual(code, 2, err)
                    self.assertIn(f"{name}: 0 or 1", err)
                    self.assertNotIn("[serve.sh]", out)

    def test_an_empty_on_off_value_says_to_write_a_zero(self):
        _, _, err = self.run_serve(2, "VISION=\n")
        self.assertIn("write VISION=0", err)

    def test_vision_is_on_unless_a_zero_turns_it_off(self):
        args, _, start = self.serve(2)
        self.assertIn("--vision", args)
        self.assertIn("vision 1", start)
        args, _, start = self.serve(2, "VISION=0\n")
        self.assertNotIn("--vision", args)
        self.assertIn("vision 0", start)

    def test_the_wire_can_be_turned_off_with_a_zero(self):
        _, env, _ = self.serve(3, "TF_GLM_ROCE_MULTI=0\n")
        self.assertEqual(env["TF_GLM_ROCE_MULTI"], "0")
        for key in WIRE:
            self.assertNotIn(key, env)

    def test_the_wires_settings_can_be_named_in_the_rank_file(self):
        _, env, _ = self.serve(3, "TF_TP_PORT=29700\nTF_TP_ROCE_FALLBACK=nccl\n")
        self.assertEqual(env["TF_TP_PORT"], "29700")
        self.assertEqual(env["TF_TP_ROCE_FALLBACK"], "nccl")

    def test_the_start_line_shows_what_was_resolved(self):
        _, _, start = self.serve(2)
        for shown in (
            "context 1048576",
            "parallel 4",
            "kept 16",
            "prefill-share 0.7",
            "solo unset",
            "mtp-confidence unset",
            "wire 0",
            "reserve 9",
        ):
            self.assertIn(shown, start)
        _, _, start = self.serve(3, "PARALLEL=\n")
        for shown in (
            "parallel auto",
            "mtp-confidence 0.5",
            "wire 1",
            "solo unset",
            "reserve 16",
        ):
            self.assertIn(shown, start)


class ReadmeDefaultsTests(unittest.TestCase):
    """The READMEs' serving defaults say what tp2.env and tp3.env set."""

    def table(self, name):
        text = (LINE / name).read_text(encoding="utf-8")
        start = text.index("| TP=2", text.index("/tp2.env)"))
        return text[start : text.index("\n\n", start)]

    def test_both_tables_give_each_tp_sizes_values(self):
        two, three = defaults(2), defaults(3)
        for name in ("README.md", "README.ja.md"):
            table = self.table(name)
            for tp in (two, three):
                self.assertIn(f"{int(tp['CONTEXT']):,}", table, name)
                self.assertIn(f"TF_KV_SHARE={tp['TF_KV_SHARE']}", table, name)
                self.assertIn(
                    f"TENSORFOLD_PREFILL_SHARE={tp['TENSORFOLD_PREFILL_SHARE']}",
                    table,
                    name,
                )
            self.assertIn(
                f"TF_GLM_ROCE_MULTI={three['TF_GLM_ROCE_MULTI']}", table, name
            )
            self.assertIn(
                f"| {two['TENSORFOLD_MEMORY_RESERVE_GIB']} GiB | {three['TENSORFOLD_MEMORY_RESERVE_GIB']} GiB |",
                table,
                name,
            )
            self.assertIn(
                three["MTP_CONFIDENCE"],
                table.split("MTP_CONFIDENCE")[0].rsplit("|", 1)[1],
                name,
            )
            row = next(x for x in table.splitlines() if "`--parallel`" in x).split("|")
            self.assertRegex(row[2], rf"^ {two['PARALLEL']}\b", name)
            self.assertRegex(row[3], rf"^ {three['PARALLEL']}\b", name)


if __name__ == "__main__":
    unittest.main()
