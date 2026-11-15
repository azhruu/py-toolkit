#!/usr/bin/env python3
"""Unit tests for textstats.py — markdown stripping, sentence/paragraph
counts, reading time, top words, per-file stats, totals and file
collection.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textstats import (analyze_file, analyze_text, collect_files,
                       count_paragraphs, count_sentences, reading_time,
                       strip_markdown, top_words, total_stats)


class TestStripMarkdown(unittest.TestCase):
    def test_headings_and_emphasis_keep_text(self):
        self.assertEqual(
            strip_markdown("# Title\n\nSome **bold** and *italic* text."),
            "Title\n\nSome bold and italic text.")

    def test_links_keep_visible_text(self):
        self.assertEqual(
            strip_markdown("See [the docs](https://example.com) for more."),
            "See the docs for more.")

    def test_images_keep_alt_text(self):
        self.assertEqual(
            strip_markdown("![a cat](cat.png) sat here."),
            "a cat sat here.")

    def test_inline_code_keeps_content(self):
        self.assertEqual(
            strip_markdown("Run `print(1)` to test."),
            "Run print(1) to test.")

    def test_fenced_block_dropped_entirely(self):
        self.assertEqual(
            strip_markdown("before\n```python\nprint(1)\n```\nafter"),
            "before\n\nafter")

    def test_unclosed_fence_dropped(self):
        self.assertEqual(
            strip_markdown("prose\n```\ncode that never ends"),
            "prose\n")

    def test_plain_text_untouched(self):
        self.assertEqual(strip_markdown("just plain text"), "just plain text")


class TestCountSentences(unittest.TestCase):
    def test_periods_question_exclamation(self):
        self.assertEqual(count_sentences("Hello world. How are you? Fine!"), 3)

    def test_no_punctuation_is_one_sentence(self):
        self.assertEqual(count_sentences("No punctuation here"), 1)

    def test_empty_is_zero(self):
        self.assertEqual(count_sentences(""), 0)

    def test_abbreviation_runs_together(self):
        # "Mr. Smith" splits on the period, so it counts as two fragments.
        self.assertEqual(count_sentences("Mr. Smith arrived."), 2)


class TestCountParagraphs(unittest.TestCase):
    def test_blank_line_separated_blocks(self):
        self.assertEqual(count_paragraphs("one\n\ntwo\n\nthree"), 3)

    def test_single_block(self):
        self.assertEqual(count_paragraphs("one\ntwo"), 1)

    def test_empty_and_blank_only(self):
        self.assertEqual(count_paragraphs(""), 0)
        self.assertEqual(count_paragraphs("\n\n  \n"), 0)


class TestReadingTime(unittest.TestCase):
    def test_zero_words(self):
        self.assertEqual(reading_time(0), "0 sec")

    def test_seconds_only(self):
        self.assertEqual(reading_time(100), "30 sec")  # 200 wpm default

    def test_whole_minutes(self):
        self.assertEqual(reading_time(400), "2 min")

    def test_minutes_and_seconds(self):
        self.assertEqual(reading_time(450), "2 min 15 sec")

    def test_custom_wpm(self):
        self.assertEqual(reading_time(100, wpm=100), "1 min")
        self.assertEqual(reading_time(50, wpm=100), "30 sec")


class TestTopWords(unittest.TestCase):
    def test_counts_and_case_insensitive(self):
        self.assertEqual(top_words("Cat cat CAT dog", n=5),
                         [("cat", 3), ("dog", 1)])

    def test_stopwords_excluded_by_default(self):
        self.assertEqual(top_words("the cat sat on the mat", n=5),
                         [("cat", 1), ("sat", 1), ("mat", 1)])

    def test_keep_stopwords(self):
        self.assertEqual(top_words("the cat sat on the mat", n=5,
                                   keep_stopwords=True),
                         [("the", 2), ("cat", 1), ("sat", 1),
                          ("on", 1), ("mat", 1)])

    def test_limit(self):
        self.assertEqual(len(top_words("a b c d e f g", n=3)), 3)

    def test_empty(self):
        self.assertEqual(top_words(""), [])


class TestAnalyzeText(unittest.TestCase):
    def test_full_stats(self):
        r = analyze_text("Hello world.\n\nSecond para here.", "notes.md")
        self.assertEqual(r["file"], "notes.md")
        self.assertEqual(r["lines"], 3)
        self.assertEqual(r["words"], 5)
        self.assertEqual(r["characters"], 31)
        self.assertEqual(r["characters_no_spaces"], 26)
        self.assertEqual(r["sentences"], 2)
        self.assertEqual(r["paragraphs"], 2)
        self.assertEqual(r["reading_time"], "2 sec")
        self.assertEqual(r["longest_word"], "Second")
        self.assertEqual(r["top_words"],
                         [["hello", 1], ["world", 1], ["second", 1],
                          ["para", 1], ["here", 1]])

    def test_empty_text(self):
        r = analyze_text("", "empty.txt")
        self.assertEqual(r, {
            "file": "empty.txt", "lines": 0, "words": 0, "characters": 0,
            "characters_no_spaces": 0, "sentences": 0, "paragraphs": 0,
            "reading_time": "0 sec", "longest_word": "", "top_words": [],
        })

    def test_trailing_newline_not_an_extra_line(self):
        self.assertEqual(analyze_text("one\ntwo\n", "x")["lines"], 2)
        self.assertEqual(analyze_text("one\ntwo", "x")["lines"], 2)

    def test_custom_wpm_and_top_n(self):
        r = analyze_text("word " * 200, "x", wpm=100, top_n=1)
        self.assertEqual(r["reading_time"], "2 min")
        self.assertEqual(r["top_words"], [["word", 200]])


class TestTotalStats(unittest.TestCase):
    def test_sums_and_longest_word(self):
        a = analyze_text("short text here", "a.txt")
        b = analyze_text("a much longerword here", "b.txt")
        t = total_stats([a, b])
        self.assertEqual(t["file"], "TOTAL (2 file(s))")
        self.assertEqual(t["words"], a["words"] + b["words"])
        self.assertEqual(t["lines"], a["lines"] + b["lines"])
        self.assertEqual(t["longest_word"], "longerword")
        self.assertEqual(t["top_words"], [])


class TestAnalyzeFile(unittest.TestCase):
    def test_markdown_stripped_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.md"
            p.write_text("# Head\n\nHello world hello.", encoding="utf-8")
            r = analyze_file(p)
            self.assertEqual(r["words"], 4)
            self.assertEqual(r["top_words"],
                             [["hello", 2], ["head", 1], ["world", 1]])

    def test_raw_keeps_markup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.md"
            p.write_text("# Head\n\nHello world hello.", encoding="utf-8")
            raw = analyze_file(p, raw=True)
            stripped = analyze_file(p)
            self.assertGreater(raw["characters"], stripped["characters"])
            self.assertEqual(raw["words"], stripped["words"])


class TestCollectFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.txt").write_text("a")
        (self.root / "b.md").write_text("b")
        (self.root / "c.py").write_text("c")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "d.txt").write_text("d")

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder_non_recursive(self):
        exts = (".txt", ".md", ".markdown", ".rst")
        self.assertEqual(
            collect_files([str(self.root)], False, exts),
            [self.root / "a.txt", self.root / "b.md"])

    def test_folder_recursive(self):
        exts = (".txt", ".md", ".markdown", ".rst")
        self.assertEqual(
            collect_files([str(self.root)], True, exts),
            [self.root / "a.txt", self.root / "b.md",
             self.root / "sub" / "d.txt"])

    def test_single_file_target(self):
        self.assertEqual(
            collect_files([str(self.root / "c.py")], False, (".py",)),
            [self.root / "c.py"])

    def test_missing_target_warns_and_skips(self):
        err = StringIO()
        with redirect_stderr(err):
            found = collect_files([str(self.root / "nope.txt")],
                                  False, (".txt",))
        self.assertEqual(found, [])
        self.assertIn("not found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
