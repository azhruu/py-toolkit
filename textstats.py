#!/usr/bin/env python3
"""textstats.py — word/line/reading-time stats for text & markdown files.

Usage:
    python textstats.py notes.md
    python textstats.py docs/ --recursive
    python textstats.py a.txt b.md --top 10 --wpm 250 --json

For each file it reports lines, words, characters (with and without
spaces), sentences, paragraphs, estimated reading time and the most
common words. Markdown is understood by default: fenced code blocks,
headings, links, images, emphasis and inline code are stripped before
counting, so the numbers describe the prose, not the markup
(--raw counts the file exactly as written). A folder target scans
.txt/.md/.markdown/.rst files inside it; --recursive descends into
subfolders. Read-only: nothing is ever written.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_WPM = 200
DEFAULT_EXTS = (".txt", ".md", ".markdown", ".rst")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")
SENTENCE_END_RE = re.compile(r"[.!?]+")
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
UNCLOSED_FENCE_RE = re.compile(r"```.*$", re.DOTALL)
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
EMPHASIS_RE = re.compile(r"(\*\*|__)(.*?)\1|(\*|_)(.*?)\3")
HTML_TAG_RE = re.compile(r"<[^>]+>")
STOPWORDS = frozenset("""
a an the and or but if then else when at by for with about into
through after over between out against during without before under
around among of to in on is are was were be been being have has had
do does did will would shall should can could may might must i you
he she it we they this that these those am as from not no yes so
""".split())


def strip_markdown(text: str) -> str:
    """Remove markdown markup, keeping the readable prose.

    Fenced code blocks are dropped entirely (they are code, not
    prose); links keep their visible text, images keep their alt
    text, and headings/emphasis/inline code keep their content.
    """
    text = FENCED_BLOCK_RE.sub("", text)
    text = UNCLOSED_FENCE_RE.sub("", text)
    text = IMAGE_RE.sub(r"\1", text)
    text = LINK_RE.sub(r"\1", text)
    text = INLINE_CODE_RE.sub(r"\1", text)
    text = HEADING_RE.sub("", text)
    text = EMPHASIS_RE.sub(lambda m: m.group(2) or m.group(4) or "", text)
    text = HTML_TAG_RE.sub("", text)
    return text


def count_sentences(text: str) -> int:
    """Count sentence-like fragments (text ending in . ! or ?)."""
    return sum(1 for part in SENTENCE_END_RE.split(text)
               if re.search(r"\w", part))


def count_paragraphs(text: str) -> int:
    """Count blocks of non-blank lines separated by blank lines."""
    return sum(1 for block in re.split(r"\n\s*\n", text.strip())
               if block.strip())


def reading_time(words: int, wpm: int = DEFAULT_WPM) -> str:
    """Format an estimated reading time, e.g. '3 min 20 sec'."""
    if words <= 0:
        return "0 sec"
    total_seconds = round(words / wpm * 60)
    minutes, seconds = divmod(total_seconds, 60)
    if minutes == 0:
        return f"{seconds} sec"
    if seconds == 0:
        return f"{minutes} min"
    return f"{minutes} min {seconds} sec"


def top_words(text: str, n: int = 5, keep_stopwords: bool = False):
    """Most common words, lowercased, stopwords excluded by default."""
    words = [w.lower() for w in WORD_RE.findall(text)]
    if not keep_stopwords:
        words = [w for w in words if w not in STOPWORDS]
    return Counter(words).most_common(n)


def analyze_text(text: str, name: str, wpm: int = DEFAULT_WPM,
                 top_n: int = 5, keep_stopwords: bool = False) -> dict:
    """All stats for one chunk of text. Pure: easy to unit-test."""
    words = WORD_RE.findall(text)
    return {
        "file": name,
        "lines": text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "sentences": count_sentences(text),
        "paragraphs": count_paragraphs(text),
        "reading_time": reading_time(len(words), wpm),
        "longest_word": max((w for w in words), key=len, default=""),
        "top_words": [[w, c] for w, c in top_words(text, top_n, keep_stopwords)],
    }


def analyze_file(path: Path, wpm: int = DEFAULT_WPM, top_n: int = 5,
                 keep_stopwords: bool = False, raw: bool = False) -> dict:
    """Read a file (UTF-8, errors replaced) and return its stats."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not raw:
        text = strip_markdown(text)
    return analyze_text(text, str(path), wpm, top_n, keep_stopwords)


def collect_files(targets, recursive: bool, exts) -> list:
    """Expand CLI targets (files or folders) into a sorted file list."""
    found = []
    for target in targets:
        path = Path(target).expanduser()
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(path.glob(pattern)):
                if child.is_file() and child.suffix.lower() in exts:
                    found.append(child)
        else:
            print(f"warning: {target} not found, skipping", file=sys.stderr)
    return sorted(set(found))


def total_stats(results: list) -> dict:
    """Sum the numeric stats of several per-file results."""
    total = {
        "file": f"TOTAL ({len(results)} file(s))",
        "lines": 0, "words": 0, "characters": 0,
        "characters_no_spaces": 0, "sentences": 0, "paragraphs": 0,
        "reading_time": "", "longest_word": "", "top_words": [],
    }
    for r in results:
        for key in ("lines", "words", "characters",
                    "characters_no_spaces", "sentences", "paragraphs"):
            total[key] += r[key]
        if len(r["longest_word"]) > len(total["longest_word"]):
            total["longest_word"] = r["longest_word"]
    return total


def print_report(results: list, wpm: int) -> None:
    for r in results:
        print(f"{r['file']}")
        print(f"  Lines: {r['lines']}   Words: {r['words']}"
              f"   Characters: {r['characters']}"
              f" ({r['characters_no_spaces']} without spaces)")
        print(f"  Sentences: {r['sentences']}"
              f"   Paragraphs: {r['paragraphs']}"
              f"   Reading time: {r['reading_time']} (@ {wpm} wpm)")
        print(f"  Longest word: {r['longest_word'] or '(none)'}")
        if r["top_words"]:
            words = ", ".join(f"{w} ({c})" for w, c in r["top_words"])
            print(f"  Top words: {words}")
    if len(results) > 1:
        t = total_stats(results)
        print(f"\n{t['file']}")
        print(f"  Lines: {t['lines']}   Words: {t['words']}"
              f"   Characters: {t['characters']}"
              f"   Sentences: {t['sentences']}"
              f"   Paragraphs: {t['paragraphs']}")
        print(f"  Reading time: {reading_time(t['words'], wpm)}"
              f"   Longest word: {t['longest_word'] or '(none)'}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Word/line/reading-time stats for text & markdown files.")
    parser.add_argument("target", nargs="+",
                        help="file(s) or folder(s) to measure")
    parser.add_argument("--recursive", action="store_true",
                        help="descend into subfolders of folder targets")
    parser.add_argument("--ext", default=",".join(DEFAULT_EXTS),
                        help="comma-separated extensions for folder targets"
                        " (default: .txt,.md,.markdown,.rst)")
    parser.add_argument("--top", type=int, default=5,
                        help="how many top words to show (default 5)")
    parser.add_argument("--wpm", type=int, default=DEFAULT_WPM,
                        help="reading speed in words per minute"
                        " (default 200)")
    parser.add_argument("--keep-stopwords", action="store_true",
                        help="include common words (the, and, ...) in top words")
    parser.add_argument("--raw", action="store_true",
                        help="count markdown markup as written, do not strip it")
    parser.add_argument("--json", action="store_true",
                        help="print results as JSON instead of a report")
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be 0 or more")
    if args.wpm < 1:
        parser.error("--wpm must be at least 1")
    exts = tuple(e.strip().lower() if e.strip().startswith(".")
                 else "." + e.strip().lower()
                 for e in args.ext.split(",") if e.strip())
    if not exts:
        parser.error("--ext must list at least one extension")
    files = collect_files(args.target, args.recursive, exts)
    if not files:
        print("error: no readable files found", file=sys.stderr)
        return 1
    results = [analyze_file(f, wpm=args.wpm, top_n=args.top,
                            keep_stopwords=args.keep_stopwords, raw=args.raw)
               for f in files]
    if args.json:
        payload = results
        if len(results) > 1:
            total = total_stats(results)
            total["reading_time"] = reading_time(total["words"], args.wpm)
            payload = results + [total]
        print(json.dumps(payload, indent=2))
    else:
        print_report(results, args.wpm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
