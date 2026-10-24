import json
import re
import unittest
from pathlib import Path

LINE = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"[0-9a-f]{40}")


def lock():
    return json.loads((LINE / "config/engine.lock.json").read_text(encoding="utf-8"))


def dockerfile_args():
    """The image's ARG defaults, quotes removed."""
    text = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
    return {
        m.group(1): m.group(2).strip('"')
        for m in re.finditer(r"^ARG (\w+)=(.*)$", text, re.MULTILINE)
    }


class EngineLockTests(unittest.TestCase):
    def test_the_engine_and_its_base_are_full_commits(self):
        pinned = lock()
        self.assertRegex(pinned["ref"], HEX40)
        self.assertRegex(pinned["upstream"]["ref"], HEX40)
        self.assertTrue(pinned["branch"].startswith("release/3."))

    def test_the_compiler_is_one_version_with_its_checksum(self):
        zig = lock()["zig"]
        self.assertIn(f"/{zig['version']}/", zig["url"])
        self.assertTrue(zig["url"].endswith(f"-{zig['version']}.tar.xz"))
        self.assertRegex(zig["sha256"], r"^[0-9a-f]{64}$")

    def test_the_image_builds_what_the_lock_pins(self):
        pinned, args = lock(), dockerfile_args()
        self.assertEqual(args["ENGINE_REPO"], pinned["repo"])
        self.assertEqual(args["ENGINE_REF"], pinned["ref"])
        self.assertEqual(args["ZIG_URL"], pinned["zig"]["url"])
        self.assertEqual(args["ZIG_SHA256"], pinned["zig"]["sha256"])
        self.assertEqual(args["BUILD_FLAGS"], " ".join(pinned["build"]))
        grammar = pinned["xgrammar"]
        self.assertEqual(args["XGRAMMAR_REPO"], grammar["repo"])
        self.assertEqual(args["XGRAMMAR_TAG"], grammar["version"])
        self.assertEqual(args["XGRAMMAR_REF"], grammar["ref"])

    def test_the_grammar_library_is_a_release_at_a_full_commit(self):
        grammar = lock()["xgrammar"]
        self.assertRegex(grammar["ref"], HEX40)
        self.assertRegex(grammar["version"], r"^v\d+\.\d+\.\d+$")

    def test_the_media_libraries_are_one_release_each_with_its_checksum(self):
        media = lock()["media"]
        self.assertEqual(sorted(media), ["ffmpeg", "libjpeg_turbo", "libwebp"])
        for name, lib in media.items():
            self.assertIn(lib["version"], lib["url"], name)
            self.assertTrue(lib["url"].startswith("https://"), name)
            self.assertRegex(lib["sha256"], r"^[0-9a-f]{64}$", name)

    def test_the_image_builds_the_media_libraries_the_lock_pins(self):
        media, args = lock()["media"], dockerfile_args()
        for name, arg in (
            ("libjpeg_turbo", "JPEG_TURBO"),
            ("libwebp", "WEBP"),
            ("ffmpeg", "FFMPEG"),
        ):
            self.assertEqual(args[f"{arg}_URL"], media[name]["url"], name)
            self.assertEqual(args[f"{arg}_SHA256"], media[name]["sha256"], name)

    def test_the_image_takes_the_grammar_library_from_where_the_engine_installs_it(
        self,
    ):
        # From upstream 1.1.3 `zig build grammar` installs it beside the native server (zig-out/native/lib).
        text = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("cp zig-out/native/lib/libtfgrammar.so /out/", text)
        self.assertNotIn("zig-out/lib/libtfgrammar.so", text)

    def test_the_image_carries_the_repositorys_notices_and_the_licenses_they_name(self):
        text = (LINE / "docker/Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/doc/tf3/\n", text
        )
        self.assertIn("COPY LICENSES/ /usr/share/doc/tf3/LICENSES/\n", text)

    def test_the_bases_are_pinned_by_digest(self):
        args = dockerfile_args()
        for name in ("BUILD_IMAGE", "RUNTIME_IMAGE"):
            self.assertRegex(args[name], r"@sha256:[0-9a-f]{64}$", name)


if __name__ == "__main__":
    unittest.main()
