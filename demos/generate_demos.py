#!/usr/bin/env python3
"""Regenerate the "Demos" section of py-toolkit's README from live runs.

Builds throwaway demo folders in a temp dir, runs the real tools on them,
captures the actual terminal output, and rewrites README.md between the
<!-- demos:start --> and <!-- demos:end --> markers. Nothing here is
hand-written output: if a tool changes, re-run this script and the README
follows.

Usage:  python demos/generate_demos.py
"""

import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START = "<!-- demos:start -->"
END = "<!-- demos:end -->"


def run(tool, *args, cwd):
    """Run one tool, return its stdout with trailing blank lines stripped."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / tool), *args],
        capture_output=True, text=True, cwd=cwd,
    )
    out = (proc.stdout + proc.stderr).rstrip("\n")
    if proc.returncode != 0:
        raise SystemExit(f"{tool} {' '.join(args)} failed:\n{out}")
    return out


def tree(path):
    """Sorted, indented listing of a folder, like a tiny `tree`."""
    lines = [path.name + "/"]

    def walk(p, depth):
        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        for e in entries:
            lines.append("  " * depth + e.name + ("/" if e.is_dir() else ""))
            if e.is_dir():
                walk(e, depth + 1)

    walk(path, 1)
    return "\n".join(lines)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode()
    path.write_bytes(data)


def make_png(width, height):
    """Minimal non-interlaced 8-bit RGB PNG, built with the stdlib only."""
    def chunk(kind, data):
        block = kind + data
        return struct.pack(">I", len(data)) + block + struct.pack(
            ">I", zlib.crc32(block) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x10\x80\xff" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def section(title, intro, blocks):
    """One demo: heading, intro line, then (command, output) code blocks."""
    parts = [f"### {title}", ""]
    if intro:
        parts += [intro, ""]
    for command, output in blocks:
        if command:
            parts.append("```bash")
            parts.append(f"$ {command}")
            parts.append("```")
            parts.append("")
        parts.append("```")
        parts.append(output)
        parts.append("```")
        parts.append("")
    return "\n".join(parts).rstrip("\n")


def build(sandbox):
    demos = []

    # --- organize.py: before / dry-run / real run / after -------------------
    downloads = sandbox / "demo-downloads"
    for name, data in [
        ("beach.jpg", b"fake-jpg"), ("photo-copy.jpg", b"fake-jpg"),
        ("notes.md", b"# notes\n\nhello world\n"), ("report.txt", b"x"),
        ("song.mp3", b"audio"), ("clip.mp4", b"video"),
        ("backup.zip", b"zip!"), ("script.py", b"print(1)\n"),
    ]:
        write(downloads / name, data)
    demos.append(section(
        "organize.py — sort a messy folder by file type",
        "Before:",
        [("", tree(downloads)),
         ("python organize.py demo-downloads --dry-run",
          run("organize.py", "demo-downloads", "--dry-run", cwd=sandbox)),
         ("python organize.py demo-downloads",
          run("organize.py", "demo-downloads", cwd=sandbox)),
         ("", "After:\n" + tree(downloads))]))

    # --- dupfinder.py: find the duplicate, then quarantine it --------------
    demos.append(section(
        "dupfinder.py — find duplicates by content hash",
        "`beach.jpg` and `photo-copy.jpg` are byte-identical:",
        [("python dupfinder.py demo-downloads",
          run("dupfinder.py", "demo-downloads", cwd=sandbox)),
         ("python dupfinder.py demo-downloads --move-to dupes",
          run("dupfinder.py", "demo-downloads", "--move-to", "dupes", cwd=sandbox)),
         ("", tree(sandbox / "dupes"))]))

    # --- rename.py: prefix + numbering, preview then real ------------------
    photos = sandbox / "photos"
    for name in ("IMG_20240101.jpg", "IMG_20240102.jpg", "IMG_20240103.jpg"):
        write(photos / name, b"x")
    demos.append(section(
        "rename.py — batch rename with prefix and numbering",
        "",
        [("python rename.py photos --prefix vacay- --numbering --dry-run",
          run("rename.py", "photos", "--prefix", "vacay-", "--numbering",
              "--dry-run", cwd=sandbox)),
         ("python rename.py photos --prefix vacay- --numbering",
          run("rename.py", "photos", "--prefix", "vacay-", "--numbering", cwd=sandbox)),
         ("", tree(photos))]))

    # --- dirsize.py: biggest folders and files -----------------------------
    sizes = sandbox / "sizes"
    write(sizes / "media" / "movie.mp4", b"v" * 2_500_000)
    write(sizes / "media" / "photo.jpg", b"p" * 120_000)
    write(sizes / "docs" / "archive.zip", b"z" * 800_000)
    write(sizes / "docs" / "notes.txt", b"n" * 3_000)
    demos.append(section(
        "dirsize.py — biggest folders and files in a tree",
        "",
        [("python dirsize.py sizes --top 5",
          run("dirsize.py", "sizes", "--top", "5", cwd=sandbox))]))

    # --- textstats.py: word/line/reading-time stats ------------------------
    trip = sandbox / "trip.md"
    write(trip, "# Trip notes\n\nThe quick brown fox jumps over the lazy dog. "
                "The fox was quick and the dog was lazy.\n\n"
                "- pack light\n- pack light\n")
    demos.append(section(
        "textstats.py — word, line and reading-time stats",
        "",
        [("python textstats.py trip.md",
          run("textstats.py", "trip.md", cwd=sandbox))]))

    # --- imgshrink.py: shrink a PNG, preview then real ---------------------
    write(sandbox / "big.png", make_png(800, 600))
    demos.append(section(
        "imgshrink.py — batch-resize images (stdlib only)",
        "An 800×600 PNG, shrunk to fit inside 200×200:",
        [("python imgshrink.py big.png --max 200 --dry-run",
          run("imgshrink.py", "big.png", "--max", "200", "--dry-run", cwd=sandbox)),
         ("python imgshrink.py big.png --max 200",
          run("imgshrink.py", "big.png", "--max", "200", cwd=sandbox))]))

    body = ("## Demos\n\n"
            "Real terminal output from running the tools on throwaway demo "
            "folders — regenerate it any time with:\n\n"
            "```bash\n"
            "python demos/generate_demos.py   # rebuilds this section from live runs\n"
            "```\n\n"
            + "\n\n".join(demos) + "\n")
    return body


def main():
    text = README.read_text()
    if START not in text or END not in text:
        raise SystemExit(f"README.md is missing the {START} / {END} markers")
    sandbox = Path(tempfile.mkdtemp(prefix="py-toolkit-demos-"))
    try:
        body = build(sandbox)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(before + START + "\n\n" + body + "\n" + END + after)
    print(f"Demos section regenerated in {README}")


if __name__ == "__main__":
    main()
