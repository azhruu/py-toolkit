#!/usr/bin/env python3
"""dirsize.py — biggest folders/files report for a directory tree.

Usage:
    python dirsize.py <folder> [--top N] [--depth N]
    python dirsize.py <folder> --files-only [--top 20]
    python dirsize.py <folder> --min-size 10MB --all

Walks the tree once, then prints the total size plus the biggest
folders and the biggest files, each with a bar scaled to the largest
entry so the worst offenders jump out. Read-only: nothing is moved
or deleted. Hidden files and folders are skipped unless --all is
given; symlinks are never followed, and unreadable entries are
skipped with a count instead of crashing the run.
"""
import argparse
import os
import sys
from pathlib import Path

UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
SIZE_SUFFIXES = {"b": 1, "k": 1024, "kb": 1024, "m": 1024 ** 2,
                 "mb": 1024 ** 2, "g": 1024 ** 3, "gb": 1024 ** 3,
                 "t": 1024 ** 4, "tb": 1024 ** 4}


def human_size(size: int) -> str:
    """Format a byte count, e.g. 1536 -> '1.5 KB', 500 -> '500 B'."""
    value = float(size)
    for unit in UNITS:
        if value < 1024 or unit == UNITS[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"  # pragma: no cover


def parse_size(text: str) -> int:
    """Parse '10MB', '500K', '1024' into bytes; raises ValueError."""
    raw = text.strip().lower()
    digits = ""
    for ch in raw:
        if ch.isdigit() or ch == ".":
            digits += ch
        else:
            break
    suffix = raw[len(digits):].strip()
    if not digits:
        raise ValueError(f"bad size {text!r}: expected a number")
    if suffix and suffix not in SIZE_SUFFIXES:
        raise ValueError(f"bad size {text!r}: unknown suffix {suffix!r}")
    return int(float(digits) * SIZE_SUFFIXES.get(suffix, 1))


def walk_tree(root: Path, include_hidden: bool):
    """Walk root once. Returns (dir_sizes, file_sizes, skipped).

    dir_sizes maps every directory to the total bytes under it
    (including nested subfolders); file_sizes maps each file to its
    own size; skipped counts entries unreadable or unstatable.
    """
    dir_sizes: dict[Path, int] = {root: 0}
    file_sizes: dict[Path, int] = {}
    skipped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dir_sizes.setdefault(current, 0)
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if not include_hidden and name.startswith("."):
                continue
            path = current / name
            try:
                if path.is_symlink():
                    continue
                size = path.stat().st_size
            except OSError:
                skipped += 1
                continue
            file_sizes[path] = size
            parent = current
            while True:
                dir_sizes[parent] = dir_sizes.get(parent, 0) + size
                if parent == root:
                    break
                parent = parent.parent
    return dir_sizes, file_sizes, skipped


def bar(size: int, largest: int, width: int = 30) -> str:
    filled = round(size / largest * width) if largest else 0
    return "#" * filled + "-" * (width - filled)


def report_rows(entries, root: Path, largest: int):
    for path, size in entries:
        label = str(path.relative_to(root)) if path != root else "."
        print(f"  {human_size(size):>10}  |{bar(size, largest)}|  {label}")


def dirsize(root: Path, top: int = 10, depth: int = 2,
            min_size: int = 0, include_hidden: bool = False,
            files_only: bool = False, dirs_only: bool = False) -> int:
    if not root.is_dir():
        print(f"error: {root} is not a folder", file=sys.stderr)
        return 1
    dir_sizes, file_sizes, skipped = walk_tree(root, include_hidden)

    total = dir_sizes.get(root, 0)
    print(f"{root}")
    print(f"Total: {human_size(total)}"
          f"  ({len(file_sizes)} file(s), {len(dir_sizes)} folder(s))")
    if skipped:
        print(f"Skipped {skipped} unreadable entr"
              f"{'y' if skipped == 1 else 'ies'}.")

    if not dirs_only:
        files = [(p, s) for p, s in file_sizes.items() if s >= min_size]
        files.sort(key=lambda item: item[1], reverse=True)
        print(f"\nBiggest files (top {min(top, len(files))}):")
        if files:
            report_rows(files[:top], root, files[0][1])
        else:
            print("  (none)")

    if not files_only:
        def rel_depth(path: Path) -> int:
            return len(path.relative_to(root).parts)

        dirs = [(p, s) for p, s in dir_sizes.items()
                if p != root and rel_depth(p) <= depth and s >= min_size]
        dirs.sort(key=lambda item: item[1], reverse=True)
        print(f"\nBiggest folders (top {min(top, len(dirs))},"
              f" depth {depth}):")
        if dirs:
            report_rows(dirs[:top], root, dirs[0][1])
        else:
            print("  (none)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report the biggest folders and files in a tree.")
    parser.add_argument("folder", help="folder to measure")
    parser.add_argument("--top", type=int, default=10,
                        help="entries per list (default 10)")
    parser.add_argument("--depth", type=int, default=2,
                        help="how deep to list folders (default 2)")
    parser.add_argument("--min-size", default="0",
                        help="ignore entries smaller than this, e.g. 10MB")
    parser.add_argument("--all", action="store_true",
                        help="include hidden files and folders")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--files-only", action="store_true",
                       help="list files, skip folders")
    group.add_argument("--dirs-only", action="store_true",
                       help="list folders, skip files")
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.depth < 1:
        parser.error("--depth must be at least 1")
    try:
        min_size = parse_size(args.min_size)
    except ValueError as exc:
        parser.error(str(exc))
    return dirsize(Path(args.folder).expanduser(), top=args.top,
                   depth=args.depth, min_size=min_size,
                   include_hidden=args.all, files_only=args.files_only,
                   dirs_only=args.dirs_only)


if __name__ == "__main__":
    raise SystemExit(main())
