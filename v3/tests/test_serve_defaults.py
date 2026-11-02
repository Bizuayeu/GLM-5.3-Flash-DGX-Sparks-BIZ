import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

LINE = Path(__file__).resolve().parents[1]
SETTING = re.compile(r"^(\w+)=(\S*)", re.MULTILINE)
WIRE = ("TF_TP_MASTER", "TF_TP_PORT", "TF_TP_PLAN_TIMEOUT", "TF_TP_KERNEL_IMAGE", "TF_TP_ROCE_FALLBACK")


def defaults(tp):
    """A TP's defaults as tp2.env and tp3.env write them."""
    return dict(SETTING.findall((LINE / f"config/tp{tp}.env").read_text(encoding="utf-8")))


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
            self.assertGreaterEqual(int(values["TF_GLM_KV_SHARE"]), 4 * int(values["PARALLEL"]))

    def test_the_files_are_lf_for_bash(self):
        for tp in (2, 3):
            self.assertNotIn(b"\r", (LINE / f"config/tp{tp}.env").read_bytes())

    def test_the_image_puts_the_defaults_and_the_kernels_beside_serve_sh(self):
        image = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("COPY v3/config/tp2.env v3/config/tp3.env /opt/glm53-tf3/\n", image)
        self.assertIn("COPY --from=build /out/tp_mailbox.fatbin /opt/glm53-tf3/\n", image)
        context = (LINE.parent / ".dockerignore").read_text(encoding="utf-8")
        for tp in (2, 3):
            self.assertIn(f"!v3/config/tp{tp}.env\n", context)


@unittest.skipIf(os.name == "nt", "runs bash")
class ServeTests(unittest.TestCase):
    def serve(self, tp, rank_file=""):
        """serve.sh beside the release's files with the engine stubbed: its arguments, environment and start line."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(LINE / "scripts/serve.sh", root)
            for n in (2, 3):
                shutil.copy(LINE / f"config/tp{n}.env", root)
            rank = root / "rank.env"
            rank.write_text("MASTER=10.0.0.1\n" + rank_file, encoding="utf-8")
            engine = root / "tensorfold-native"
            engine.write_text('#!/bin/bash\nprintf "arg %s\\n" "$@"\nprintenv\n', encoding="utf-8")
            engine.chmod(0o755)
            run = subprocess.run(
                ["bash", str(root / "serve.sh"), str(tp), "0", str(rank)],
                env={"PATH": f"{root}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
                check=True,
            )
            lines = run.stdout.replace(str(root), "ROOT").splitlines()
        args = [x[4:] for x in lines if x.startswith("arg ")]
        env = dict(x.split("=", 1) for x in lines if "=" in x and not x.startswith(("arg ", "[serve.sh]")))
        start = next(x for x in lines if x.startswith("[serve.sh]"))
        return args, env, start

    def flag(self, args, name):
        return args[args.index(name) + 1] if name in args else None

    def test_tp2_serves_one_person_on_the_share_with_solo_passes(self):
        args, env, _ = self.serve(2)
        self.assertEqual(self.flag(args, "--context"), "524288")
        self.assertEqual(self.flag(args, "--parallel"), "4")
        self.assertNotIn("--mtp-confidence", args)
        self.assertEqual(env["TF_GLM_KV_SHARE"], "16")
        self.assertEqual(env["TENSORFOLD_PREFILL_SHARE"], "0.7")
        self.assertEqual(env["TF_GLM_CHUNK_SOLO"], "4096")
        self.assertNotIn("TF_GLM_ROCE_MULTI", env)
        self.assertNotIn("TF_TP_MASTER", env)

    def test_tp3_serves_several_people_on_the_wire(self):
        args, env, _ = self.serve(3)
        self.assertEqual(self.flag(args, "--context"), "1048576")
        self.assertEqual(self.flag(args, "--parallel"), "8")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.5")
        self.assertEqual(env["TF_GLM_KV_SHARE"], "32")
        self.assertEqual(env["TF_GLM_ROCE_MULTI"], "1")
        self.assertEqual(env["TF_TP_MASTER"], "10.0.0.1")
        self.assertEqual(env["TF_TP_KERNEL_IMAGE"], "ROOT/tp_mailbox.fatbin")
        self.assertEqual(env["TF_TP_ROCE_FALLBACK"], "error")

    def test_the_rank_file_wins(self):
        args, env, _ = self.serve(2, "PARALLEL=2\nTF_GLM_KV_SHARE=8\nCONTEXT=262144\nMTP_CONFIDENCE=0.6\n")
        self.assertEqual(self.flag(args, "--parallel"), "2")
        self.assertEqual(self.flag(args, "--context"), "262144")
        self.assertEqual(self.flag(args, "--mtp-confidence"), "0.6")
        self.assertEqual(env["TF_GLM_KV_SHARE"], "8")

    def test_an_empty_value_turns_a_setting_off(self):
        args, env, _ = self.serve(
            3, "PARALLEL=\nTF_GLM_KV_SHARE=\nTENSORFOLD_PREFILL_SHARE=\nMTP_CONFIDENCE=\nTF_GLM_ROCE_MULTI=\n"
        )
        self.assertNotIn("--parallel", args)
        self.assertNotIn("--mtp-confidence", args)
        for key in ("TF_GLM_KV_SHARE", "TENSORFOLD_PREFILL_SHARE", "TF_GLM_ROCE_MULTI", "TF_GLM_CHUNK_SOLO") + WIRE:
            self.assertNotIn(key, env)

    def test_an_empty_context_keeps_the_releases_window(self):
        args, _, _ = self.serve(2, "CONTEXT=\n")
        self.assertEqual(self.flag(args, "--context"), "524288")

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
            "context 524288",
            "parallel 4",
            "kept 16",
            "prefill-share 0.7",
            "solo 4096",
            "mtp-confidence unset",
            "wire unset",
        ):
            self.assertIn(shown, start)
        _, _, start = self.serve(3, "PARALLEL=\n")
        for shown in ("parallel auto", "mtp-confidence 0.5", "wire 1", "solo unset"):
            self.assertIn(shown, start)


if __name__ == "__main__":
    unittest.main()
