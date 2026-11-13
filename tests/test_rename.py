#!/usr/bin/env python3
"""Unit tests for rename.py — patterns, numbering, dry-run, clash safety.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import argparse
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rename import build_name, parse_replace, rename, unique_dest


class TestParseReplace(unittest.TestCase):
    def test_simple_spec(self):
        self.assertEqual(parse_replace(" :_"), (" ", "_"))

    def test_colon_in_new_part(self):
        # Only the first colon splits; NEW may contain colons.
        self.assertEqual(parse_replace("a:b:c"), ("a", "b:c"))

    def test_missing_colon_raises(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_replace("nocolon")

    def test_empty_old_raises(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_replace(":new")


class TestBuildName(unittest.TestCase):
    def test_replace_only(self):
        self.assertEqual(
            build_name("my photo", "", [(" ", "_")], None, 3), "my_photo")

    def test_prefix_only(self):
        self.assertEqual(
            build_name("IMG_01", "vacay-", [], None, 3), "vacay-IMG_01")

    def test_numbering_padded(self):
        self.assertEqual(
            build_name("IMG_01", "", [], 7, 3), "IMG_01_007")

    def test_numbering_width(self):
        self.assertEqual(
            build_name("IMG_01", "", [], 42, 5), "IMG_01_00042")

    def test_order_replace_then_prefix_then_numbering(self):
        # Replace runs on the stem first, then the prefix, then numbering.
        self.assertEqual(
            build_name("my photo", "vacay-", [(" ", "_")], 1, 3),
            "vacay-my_photo_001")

    def test_noop(self):
        self.assertEqual(build_name("plain", "", [], None, 3), "plain")


class TestUniqueDest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_free_name_returned_as_is(self):
        dest = self.folder / "new.txt"
        self.assertEqual(unique_dest(dest, set(), self.folder / "old.txt"), dest)

    def test_existing_file_gets_suffix(self):
        (self.folder / "new.txt").write_text("x")
        dest = unique_dest(self.folder / "new.txt", set(), self.folder / "old.txt")
        self.assertEqual(dest.name, "new (1).txt")

    def test_suffix_increments_past_taken_names(self):
        (self.folder / "new.txt").write_text("x")
        (self.folder / "new (1).txt").write_text("x")
        dest = unique_dest(self.folder / "new.txt", set(), self.folder / "old.txt")
        self.assertEqual(dest.name, "new (2).txt")

    def test_planned_name_counts_as_clash(self):
        dest = unique_dest(self.folder / "new.txt", {"new.txt"},
                           self.folder / "old.txt")
        self.assertEqual(dest.name, "new (1).txt")

    def test_unchanged_file_is_not_a_clash(self):
        item = self.folder / "same.txt"
        item.write_text("x")
        self.assertEqual(unique_dest(item, set(), item), item)


class TestRenameEndToEnd(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, content="x"):
        (self.folder / name).write_text(content)
        return self.folder / name

    def _names(self):
        return sorted(p.name for p in self.folder.iterdir())

    def test_prefix(self):
        self._write("a.txt")
        self._write("b.txt")
        self.assertEqual(rename(self.folder, "pre-", [], False, 1, 3), 0)
        self.assertEqual(self._names(), ["pre-a.txt", "pre-b.txt"])

    def test_replace(self):
        self._write("my photo.txt")
        self.assertEqual(rename(self.folder, "", [(" ", "_")], False, 1, 3), 0)
        self.assertEqual(self._names(), ["my_photo.txt"])

    def test_numbering_sorted_order_with_start_and_width(self):
        self._write("b.txt")
        self._write("a.txt")
        self.assertEqual(rename(self.folder, "", [], True, 5, 2), 0)
        self.assertEqual(self._names(), ["a_05.txt", "b_06.txt"])

    def test_dry_run_moves_nothing(self):
        self._write("a.txt")
        self.assertEqual(
            rename(self.folder, "pre-", [], False, 1, 3, dry_run=True), 0)
        self.assertEqual(self._names(), ["a.txt"])

    def test_clash_gets_numeric_suffix(self):
        # Both stems map to "b": a.txt via replace, b.txt stays itself.
        self._write("a.txt")
        self._write("b.txt")
        self.assertEqual(rename(self.folder, "", [("a", "b")], False, 1, 3), 0)
        self.assertEqual(self._names(), ["b (1).txt", "b.txt"])

    def test_hidden_files_skipped(self):
        self._write(".hidden.txt")
        self._write("a.txt")
        self.assertEqual(rename(self.folder, "pre-", [], False, 1, 3), 0)
        self.assertEqual(self._names(), [".hidden.txt", "pre-a.txt"])

    def test_unchanged_files_stay_put(self):
        self._write("a.txt")
        self.assertEqual(rename(self.folder, "", [], False, 1, 3), 0)
        self.assertEqual(self._names(), ["a.txt"])

    def test_not_a_folder_returns_1(self):
        self.assertEqual(
            rename(self.folder / "missing", "pre-", [], False, 1, 3), 1)


if __name__ == "__main__":
    unittest.main()
