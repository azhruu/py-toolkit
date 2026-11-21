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

    def test_menu_number_runs_that_tool(self):
        with mock.patch.object(toolkit, "run_tool", return_value=0) as run:
            self.assertEqual(toolkit.main(["1", "~/Downloads", "--dry-run"]), 0)
        run.assert_called_once_with("organize", ["~/Downloads", "--dry-run"])

    def test_menu_number_last_tool(self):
        with mock.patch.object(toolkit, "run_tool", return_value=0) as run:
            self.assertEqual(toolkit.main(["6", "notes.md"]), 0)
        run.assert_called_once_with("textstats", ["notes.md"])

    def test_menu_number_out_of_range_exits_two(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(toolkit.main(["0"]), 2)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(toolkit.main(["7"]), 2)

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


class TestSplitPositional(unittest.TestCase):
    def test_plain_words_split(self):
        self.assertEqual(toolkit.split_positional("a.md b.txt"),
                         ["a.md", "b.txt"])

    def test_quoted_path_with_spaces_stays_one_arg(self):
        self.assertEqual(toolkit.split_positional('"My Photos"'),
                         ["My Photos"])
        self.assertEqual(toolkit.split_positional("'My Photos' notes.md"),
                         ["My Photos", "notes.md"])

    def test_unbalanced_quote_falls_back_to_plain_split(self):
        self.assertEqual(toolkit.split_positional("o'clock folder"),
                         ["o'clock", "folder"])


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
        answers = iter(["notes.md", "", "n", "y"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("textstats"),
                             ["notes.md", "--json"])

    def test_top_words_prompt_passed_through(self):
        answers = iter(["notes.md", "10", "n", "n"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("textstats"),
                             ["notes.md", "--top", "10"])

    def test_quoted_folder_with_spaces_stays_one_arg(self):
        answers = iter(['"My Downloads"', "n"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("organize"),
                             ["My Downloads"])

    def test_multiple_files_still_split(self):
        answers = iter(["a.md b.txt", "", "n", "n"])
        with mock.patch.object(toolkit, "ask", side_effect=lambda *a: next(answers)):
            self.assertEqual(toolkit.build_args("textstats"),
                             ["a.md", "b.txt"])


class TestInteractive(unittest.TestCase):
    def test_blank_choice_quits_cleanly(self):
        with mock.patch.object(toolkit, "ask", return_value=""):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(toolkit.interactive(), 0)
        self.assertIn("Bye!", out.getvalue())
        self.assertNotIn("no tool called", out.getvalue())

    def test_q_quits(self):
        with mock.patch.object(toolkit, "ask", return_value="q"):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(toolkit.interactive(), 0)
        self.assertIn("Bye!", out.getvalue())

    def test_unknown_choice_then_quit(self):
        answers = iter(["xyzzy", "q"])
        with mock.patch.object(toolkit, "ask",
                               side_effect=lambda *a: next(answers)):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(toolkit.interactive(), 0)
        self.assertIn("no tool called 'xyzzy'", out.getvalue())
        self.assertIn("Bye!", out.getvalue())

    def test_run_tool_then_quit(self):
        answers = iter(["organize", "/tmp", "n", "n"])
        with mock.patch.object(toolkit, "ask",
                               side_effect=lambda *a: next(answers)), \
             mock.patch.object(toolkit, "run_tool", return_value=0) as run:
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(toolkit.interactive(), 0)
        run.assert_called_once_with("organize", ["/tmp"])
        self.assertIn("finished, exit code 0", out.getvalue())

    def test_cancelled_tool_returns_to_menu_then_quit(self):
        answers = iter(["organize", "", "q"])
        with mock.patch.object(toolkit, "ask",
                               side_effect=lambda *a: next(answers)):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(toolkit.interactive(), 0)
        self.assertIn("cancelled", out.getvalue())
        self.assertIn("Bye!", out.getvalue())


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
