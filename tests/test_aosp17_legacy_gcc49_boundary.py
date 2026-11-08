#!/usr/bin/env python3
"""Source-only audit of archived PE AArch64 GCC 4.9: no binary execution."""
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "a0c13e0de2201201342fd5c87d77f25105e5c42e"
ARCHIVE_TREE = "e7490667e01ac0301c96915927902e3e654437d0"
BIN_TREE = "b7f6196a9a7b53c4785178d6c4a6cd33ffcf044f"
GCC_PATH = "prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9"
GCC_REPO = "prebuilts_gcc_linux-x86_aarch64_aarch64-linux-android-4.9"
HOST_CLANG_PATH = "prebuilts/clang/host/linux-x86"
HOST_CLANG_OWNER = "platform/prebuilts/clang/host/linux-x86"
EXPECTED_CLANG = "clang-r584948"

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=True).stdout.strip()

def git_tree_entry(tree, name):
    line = git("ls-tree", tree, "--", name)
    if not line:
        raise AssertionError("missing Git tree entry: " + name)
    prefix, actual = line.split("\t", 1)
    mode, kind, sha = prefix.split()
    if actual != name:
        raise AssertionError("unexpected tree entry: " + line)
    return mode, kind, sha

class LegacyGcc49Boundary(unittest.TestCase):
    def test_git_history_preserves_original_archive_commit(self):
        p = subprocess.run(["git", "-C", str(ROOT), "merge-base",
                            "--is-ancestor", ARCHIVE_COMMIT, "HEAD"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_archived_bin_tree_is_unchanged(self):
        # Metadata-only check: old compiler blobs are not downloaded or executed.
        self.assertEqual(git_tree_entry("HEAD", "bin"),
                         ("040000", "tree", BIN_TREE))
        self.assertEqual(git_tree_entry("HEAD", "repo.prop"),
                         ("100644", "blob", "1313a50beba6b8a49eafabcbd07fbb382ad75e05"))
        for dirname in ("aarch64-linux-android", "lib", "libexec"):
            self.assertEqual(git_tree_entry("HEAD", dirname),
                             git_tree_entry(ARCHIVE_COMMIT, dirname))

    def test_compiler_and_gnu_alias_objects_remain_historical(self):
        fixtures = {
            "bin/aarch64-linux-android-gcc":
                ("100755", "54944a2ccbea692fa58d912e74b2514dab7a80f5"),
            "bin/real-aarch64-linux-android-gcc":
                ("100755", "deaa4261af1e3c8629ea3a540617cb921dd02b57"),
            "bin/aarch64-linux-android-gcc-4.9":
                ("120000", "347842f3e903048559d19bc729575bdf62449426"),
            "bin/aarch64-linux-android-as":
                ("100755", "c0e8b8dbd0b40ded3de4feb38ee03f30b4a8dde5"),
            "bin/aarch64-linux-gnu-as":
                ("120000", "73b56ddd9e0b16d38db6ff2803d97bd82f48f6cb"),
            "bin/aarch64-linux-gnu-elfedit":
                ("100755", "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"),
        }
        for name, expected in fixtures.items():
            with self.subTest(name=name):
                mode, kind, sha = git_tree_entry("HEAD", name)
                self.assertEqual((mode, sha), expected)
                self.assertEqual(kind, "blob")
        # The historical gnu-elfedit is a ZERO-BYTE executable, not a working tool.

    def test_legacy_build_provenance_is_not_aosp17(self):
        text = (ROOT / "repo.prop").read_text(encoding="utf-8")
        self.assertIn("toolchain/gcc ", text)
        self.assertIn("toolchain/binutils ", text)
        self.assertNotIn("android-17.0.0", text)
        self.assertFalse((ROOT / "Android.bp").exists())

    def test_official_aosp17_manifest_does_not_include_old_gcc(self):
        path = os.getenv("PE_AOSP17_REFERENCE")
        self.assertTrue(path and Path(path).is_file(), "provide pinned AOSP17 reference")
        root = ET.parse(path).getroot()
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = list(root.iter("project"))
        owners = [p for p in projects if p.get("path") == HOST_CLANG_PATH]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].get("name"), HOST_CLANG_OWNER)
        self.assertFalse(any(
            p.get("path") == GCC_PATH or p.get("name") == GCC_REPO
            for p in projects
        ))
        # Unrelated AOSP17 HOST GCC 4.8 prebuilts are legitimate.
        self.assertTrue(any(
            p.get("path") == "prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8"
            for p in projects
        ))

    def test_staged_entrypoint_keeps_legacy_gcc_out(self):
        path = os.getenv("PE_AOSP17_ACTIVE")
        self.assertTrue(path and Path(path).is_file(), "provide pinned AOSP17 default.xml")
        root = ET.parse(path).getroot()
        self.assertEqual(len(root.findall("include")), 1)
        self.assertEqual(root.find("include").get("name"),
                         "aosp17_pe_p2_kernel_configs.xml")
        self.assertFalse(any(
            p.get("path") == GCC_PATH or p.get("name") == GCC_REPO
            for p in root.iter("project")
        ))

    def test_pinned_soong_uses_clang_not_gcc49(self):
        path = os.getenv("PE_AOSP17_SOONG_GLOBAL")
        self.assertTrue(path and Path(path).is_file(), "provide pinned AOSP17 Soong global.go")
        text = Path(path).read_text(encoding="utf-8")
        versions = re.findall(
            r'(?m)^\s*ClangDefaultVersion\s*=\s*"([^"]+)"', text)
        self.assertEqual(versions, [EXPECTED_CLANG])
        self.assertIn("ReleaseBuildClangVersion(ClangDefaultVersion)", text)
        self.assertNotIn("aarch64-linux-android-4.9", text)

if __name__ == "__main__":
    unittest.main(verbosity=2)
