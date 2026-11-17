#!/usr/bin/env python3
"""Unit tests for toolkit.py — name resolving and "did you mean" hints.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import toolkit


class TestResolve(unittest.TestCase):
    def test_exact_and_case_insensitive(self):
        self.assertEqual(toolkit.resolve("organize"), "organize")
        self.assertEqual(toolkit.resolve("DirSize"), "dirsize")

    def test_py_suffix(self):
        self.assertEqual(toolkit.resolve("rename.py"), "rename")

    def test_unknown_is_none(self):
        self.assertIsNone(toolkit.resolve("organise"))
        self.assertIsNone(toolkit.resolve(""))


class TestSuggest(unittest.TestCase):
    def test_close_typo(self):
        self.assertEqual(toolkit.suggest("organise"), "organize")
        self.assertEqual(toolkit.suggest("dirsiz"), "dirsize")
        self.assertEqual(toolkit.suggest("TEXTSTATS.py"), "textstats")

    def test_no_match(self):
        self.assertIsNone(toolkit.suggest("xyzzy"))
        self.assertIsNone(toolkit.suggest(""))


class TestMain(unittest.TestCase):
    def test_list_exits_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(toolkit.main(["--list"]), 0)
        self.assertIn("organize", out.getvalue())

    def test_unknown_tool_exits_two_with_hint(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(toolkit.main(["organise"]), 2)
        self.assertIn("did you mean 'organize'", err.getvalue())

    def test_unknown_tool_without_hint(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(toolkit.main(["xyzzy"]), 2)
        self.assertNotIn("did you mean", err.getvalue())


class TestBuildArgs(unittest.TestCase):
    def test_blank_positional_cancels_to_menu(self):
        with mock.patch.object(toolkit, "ask", return_value=""):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertIsNone(toolkit.build_args("organize"))
            self.assertIn("cancelled", out.getvalue())

    def test_positional_and_yes_no_flags(self):
        answers = iter(["/tmp/downloads", "y"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("organize"),
                             ["/tmp/downloads", "--dry-run"])

    def test_blank_optional_flags_are_skipped(self):
        answers = iter(["notes.md", "n", "y"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("textstats"),
                             ["notes.md", "--json"])


class TestVersion(unittest.TestCase):
    def test_version_flag(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(toolkit.main(["--version"]), 0)
        self.assertEqual(out.getvalue().strip(), f"py-toolkit {toolkit.__version__}")

    def test_version_short_flag(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(toolkit.main(["-V"]), 0)
        self.assertIn(toolkit.__version__, out.getvalue())

    def test_version_looks_like_semver(self):
        parts = toolkit.__version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))


if __name__ == "__main__":
    unittest.main()
