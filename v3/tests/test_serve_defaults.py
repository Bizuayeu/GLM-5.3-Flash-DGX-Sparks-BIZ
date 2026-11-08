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
SETTING = re.compile(r"^(\w+)=(\S*)", re.MULTILINE)
WIRE = (
    "TF_TP_MASTER",
    "TF_TP_PORT",
    "TF_TP_PLAN_TIMEOUT",
    "TF_TP_KERNEL_IMAGE",
    "TF_TP_ROCE_FALLBACK",
)


def defaults(tp):
    """A TP's defaults as tp2.env and tp3.env write them."""
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
    def test_both_tp_sizes_name_the_same_settings(self):
        self.assertEqual(list(defaults(2)), list(defaults(3)))

    def test_every_setting_is_in_the_configuration_documents(self):
        for name in ("configuration.md", "configuration.ja.md"):
            text = (LINE / "docs" / name).read_text(encoding="utf-8")
            for key in defaults(2):
                self.assertIn(f"`{key}`", text, name)

    def test_the_kept_prompts_clear_the_engines_warning(self):
        # The engine warns below four kept states a stream (fewStates).
        for tp in (2, 3):
            values = defaults(tp)
            self.assertGreaterEqual(
                int(values["TF_KV_SHARE"]), 4 * int(values["PARALLEL"])
            )

    def test_the_files_are_lf_for_bash(self):
        for tp in (2, 3):
            self.assertNotIn(b"\r", (LINE / f"config/tp{tp}.env").read_bytes())

    def test_the_image_puts_the_defaults_and_the_kernels_beside_serve_sh(self):
        image = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY v3/config/tp2.env v3/config/tp3.env /opt/glm53-tf3/\n", image
        )
        self.assertIn(
            "COPY --from=build /out/tp_mailbox.fatbin /opt/glm53-tf3/\n", image
        )
        context = (LINE.parent / ".dockerignore").read_text(encoding="utf-8")
        for tp in (2, 3):
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
    def run_serve(self, tp, rank_file=""):
        """serve.sh beside the release's files with the engine stubbed: its exit code, output (the temporary
        folder as ROOT) and errors."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(LINE / "scripts/serve.sh", root)
            for n in (2, 3):
                shutil.copy(LINE / f"config/tp{n}.env", root)
            rank = root / "rank.env"
            rank.write_text("MASTER=10.0.0.1\n" + rank_file, encoding="utf-8")
            engine = root / "tensorfold-native"
            engine.write_text(
                '#!/bin/bash\nprintf "arg %s\\n" "$@"\nprintenv\n', encoding="utf-8"
            )
            engine.chmod(0o755)
            run = subprocess.run(
                ["bash", str(root / "serve.sh"), str(tp), "0", str(rank)],
                env={"PATH": f"{root}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=False,
            )
            return run.returncode, run.stdout.replace(str(root), "ROOT"), run.stderr

    def serve(self, tp, rank_file=""):
        """serve.sh with the engine stubbed: its arguments, environment and start line."""
        code, out, err = self.run_serve(tp, rank_file)
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
        self.assertNotIn("TF_GLM_CHUNK_SOLO", env)
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
        self.assertEqual(env["TENSORFOLD_MEMORY_RESERVE_GIB"], "14")

    def test_the_rank_file_wins(self):
        args, env, _ = self.serve(
            2, "PARALLEL=2\nTF_KV_SHARE=8\nCONTEXT=262144\nMTP_CONFIDENCE=0.6\n"
        )
        self.assertEqual(self.flag(args, "--parallel"), "2")
        self.assertEqual(self.flag(args, "--context"), "262144")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.6")
        self.assertEqual(env["TF_KV_SHARE"], "8")

    def test_one_rank_file_line_serves_jammed_and_changes_nothing_else(self):
        # 3.10.0: XSFP4 stays the default; Jammed XSFP4 is its lock's folder in CHECKPOINT.
        model, revision, _ = config.checkpoint("jammed", Path("state"))
        folder = f"/hub/models--{model.replace('/', '--')}/snapshots/{revision}"
        for tp in (2, 3):
            with self.subTest(tp=tp):
                base = self.serve(tp)[0]
                args = self.serve(tp, f"CHECKPOINT={folder}\n")[0]
                self.assertEqual(args[:2], ["serve", folder])
                self.assertEqual(args[2:], base[2:])

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
        for key in off + ("TENSORFOLD_MEMORY_RESERVE_GIB",) + WIRE:
            self.assertNotIn(key, env)

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
            "reserve 14",
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
