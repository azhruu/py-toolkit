#!/usr/bin/env python3
"""Unit tests for dirsize.py — size formatting/parsing, the bar,
tree walking (hidden files, symlinks, nested folders) and the report.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dirsize import bar, dirsize, human_size, parse_size, walk_tree


def write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


class TestHumanSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(500), "500 B")
        self.assertEqual(human_size(1023), "1023 B")

    def test_kilobytes_and_up(self):
        self.assertEqual(human_size(1024), "1.0 KB")
        self.assertEqual(human_size(1536), "1.5 KB")
        self.assertEqual(human_size(1024 ** 2), "1.0 MB")
        self.assertEqual(human_size(5 * 1024 ** 3), "5.0 GB")


class TestParseSize(unittest.TestCase):
    def test_plain_bytes(self):
        self.assertEqual(parse_size("1024"), 1024)
        self.assertEqual(parse_size("0"), 0)

    def test_suffixes_case_insensitive(self):
        self.assertEqual(parse_size("10MB"), 10 * 1024 ** 2)
        self.assertEqual(parse_size("500k"), 500 * 1024)
        self.assertEqual(parse_size("1.5g"), int(1.5 * 1024 ** 3))
        self.assertEqual(parse_size("2T"), 2 * 1024 ** 4)

    def test_whitespace_and_bare_suffix(self):
        self.assertEqual(parse_size("  10 mb  "), 10 * 1024 ** 2)
        self.assertEqual(parse_size("10m"), 10 * 1024 ** 2)

    def test_bad_input_raises(self):
        for bad in ("", "abc", "10XB", "MB", "10.5.2MB"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_size(bad)


class TestBar(unittest.TestCase):
    def test_full_and_empty(self):
        self.assertEqual(bar(100, 100), "#" * 30)
        self.assertEqual(bar(0, 100), "-" * 30)

    def test_half_and_zero_largest(self):
        self.assertEqual(bar(50, 100), "#" * 15 + "-" * 15)
        self.assertEqual(bar(10, 0), "-" * 30)

    def test_custom_width(self):
        self.assertEqual(bar(25, 100, width=10), "##--------")


class TestWalkTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root / "a.txt", 10)
        write(self.root / "sub" / "b.txt", 20)
        write(self.root / "sub" / "deep" / "c.txt", 30)
        write(self.root / ".hidden.txt", 5)
        write(self.root / ".hiddendir" / "d.txt", 7)
        os.symlink(self.root / "a.txt", self.root / "link.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def test_visible_only_by_default(self):
        dir_sizes, file_sizes, skipped = walk_tree(self.root, False)
        self.assertEqual(set(file_sizes), {
            self.root / "a.txt",
            self.root / "sub" / "b.txt",
            self.root / "sub" / "deep" / "c.txt",
        })
        self.assertEqual(file_sizes[self.root / "a.txt"], 10)
        # Symlinks are never followed or counted.
        self.assertNotIn(self.root / "link.txt", file_sizes)
        self.assertEqual(dir_sizes[self.root], 60)
        self.assertEqual(dir_sizes[self.root / "sub"], 50)
        self.assertEqual(dir_sizes[self.root / "sub" / "deep"], 30)
        self.assertEqual(skipped, 0)

    def test_hidden_included_with_flag(self):
        dir_sizes, file_sizes, skipped = walk_tree(self.root, True)
        self.assertIn(self.root / ".hidden.txt", file_sizes)
        self.assertIn(self.root / ".hiddendir" / "d.txt", file_sizes)
        self.assertEqual(dir_sizes[self.root], 72)
        self.assertEqual(dir_sizes[self.root / ".hiddendir"], 7)
        self.assertEqual(skipped, 0)

    def test_empty_folder(self):
        empty = self.root / "empty"
        empty.mkdir()
        dir_sizes, file_sizes, skipped = walk_tree(empty, False)
        self.assertEqual(dir_sizes, {empty: 0})
        self.assertEqual(file_sizes, {})
        self.assertEqual(skipped, 0)


class TestDirsizeReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root / "big.bin", 3000)
        write(self.root / "small.bin", 100)
        write(self.root / "sub" / "mid.bin", 500)

    def tearDown(self):
        self.tmp.cleanup()

    def run_report(self, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            code = dirsize(self.root, **kwargs)
        return code, out.getvalue()

    def test_success_lists_biggest_first(self):
        code, out = self.run_report()
        self.assertEqual(code, 0)
        self.assertIn("Total: 3.5 KB", out)
        self.assertLess(out.index("big.bin"), out.index("mid.bin"))
        self.assertLess(out.index("mid.bin"), out.index("small.bin"))
        self.assertIn("sub", out)

    def test_min_size_filters(self):
        code, out = self.run_report(min_size=1000)
        self.assertEqual(code, 0)
        self.assertIn("big.bin", out)
        self.assertNotIn("small.bin", out)
        self.assertNotIn("mid.bin", out)

    def test_files_only_and_dirs_only(self):
        _, files_out = self.run_report(files_only=True)
        self.assertIn("Biggest files", files_out)
        self.assertNotIn("Biggest folders", files_out)
        _, dirs_out = self.run_report(dirs_only=True)
        self.assertIn("Biggest folders", dirs_out)
        self.assertNotIn("Biggest files", dirs_out)

    def test_not_a_folder_returns_one(self):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dirsize(self.root / "big.bin")
        self.assertEqual(code, 1)
        self.assertIn("not a folder", err.getvalue())


if __name__ == "__main__":
    unittest.main()
