#!/usr/bin/env python3
"""Unit tests for dupfinder.py — content hashing, grouping, quarantine.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dupfinder import find_duplicates, human, sha256_of


def _names(groups):
    """Groups of Paths -> sorted groups of file names, for easy asserts."""
    return sorted(sorted(p.name for p in g) for g in groups)


class TestSha256Of(unittest.TestCase):
    def test_matches_hashlib(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.txt"
            f.write_bytes(b"hello world")
            expected = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(sha256_of(f), expected)

    def test_empty_file_hashes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "empty.bin"
            f.write_bytes(b"")
            self.assertEqual(sha256_of(f), hashlib.sha256(b"").hexdigest())


class TestFindDuplicates(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, rel, content):
        p = self.folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return p

    def test_identical_files_group_together(self):
        self._write("a.txt", b"same content")
        self._write("sub/b.txt", b"same content")
        self._write("c.txt", b"different")
        self.assertEqual(_names(find_duplicates(self.folder)),
                         [["a.txt", "b.txt"]])

    def test_same_size_different_content_is_not_a_duplicate(self):
        self._write("a.txt", b"aaaa")
        self._write("b.txt", b"bbbb")
        self.assertEqual(find_duplicates(self.folder), [])

    def test_zero_byte_files_are_skipped(self):
        self._write("empty1.txt", b"")
        self._write("empty2.txt", b"")
        self.assertEqual(find_duplicates(self.folder), [])

    def test_min_size_filters_small_files(self):
        self._write("a.txt", b"xx")
        self._write("b.txt", b"xx")
        self.assertEqual(find_duplicates(self.folder, min_size=3), [])
        self.assertEqual(_names(find_duplicates(self.folder, min_size=2)),
                         [["a.txt", "b.txt"]])

    def test_groups_sorted_by_wasted_space_first(self):
        self._write("small1.txt", b"s" * 10)
        self._write("small2.txt", b"s" * 10)
        self._write("big1.bin", b"B" * 1000)
        self._write("big2.bin", b"B" * 1000)
        groups = find_duplicates(self.folder)
        self.assertEqual([g[0].name for g in groups], ["big1.bin", "small1.txt"])

    def test_three_way_group_and_nested_folders(self):
        self._write("x/a.txt", b"triple")
        self._write("y/b.txt", b"triple")
        self._write("z/c.txt", b"triple")
        self._write("lonely.txt", b"alone")
        self.assertEqual(_names(find_duplicates(self.folder)),
                         [["a.txt", "b.txt", "c.txt"]])

    def test_empty_folder_has_no_duplicates(self):
        self.assertEqual(find_duplicates(self.folder), [])

    def test_symlinks_are_skipped(self):
        target = self._write("real.txt", b"data")
        (self.folder / "link.txt").symlink_to(target)
        self.assertEqual(find_duplicates(self.folder), [])


class TestHuman(unittest.TestCase):
    def test_scaling(self):
        self.assertEqual(human(0), "0 B")
        self.assertEqual(human(512), "512 B")
        self.assertEqual(human(1024), "1.0 KB")
        self.assertEqual(human(1536), "1.5 KB")
        self.assertEqual(human(1024 * 1024), "1.0 MB")


class TestMoveToCLI(unittest.TestCase):
    def test_move_to_quarantines_extras_and_keeps_first(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "src"
            folder.mkdir()
            (folder / "a.txt").write_bytes(b"dup")
            (folder / "b.txt").write_bytes(b"dup")
            (folder / "keep.txt").write_bytes(b"unique")
            quarantine = Path(tmp) / "dupes"
            script = Path(__file__).resolve().parent.parent / "dupfinder.py"
            result = subprocess.run(
                [sys.executable, str(script), str(folder), "--move-to", str(quarantine)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            kept = sorted(p.name for p in folder.iterdir())
            self.assertEqual(kept, ["a.txt", "keep.txt"])
            self.assertEqual(sorted(p.name for p in quarantine.iterdir()), ["b.txt"])
            self.assertEqual((quarantine / "b.txt").read_bytes(), b"dup")


if __name__ == "__main__":
    unittest.main()
