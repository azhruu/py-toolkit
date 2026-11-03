#!/usr/bin/env python3
"""rename.py — batch rename files with patterns.

Usage:
    python rename.py <folder> --prefix TEXT
    python rename.py <folder> --replace OLD:NEW [--replace OLD2:NEW2 ...]
    python rename.py <folder> --numbering [--start N] [--width W]
    python rename.py <folder> --prefix vacay- --replace " :_" --numbering

All three operations compose in one pass, in this order:
replace (on the stem, in the order given), then prefix, then numbering.
Numbering appends _001, _002, ... (zero-padded to --width) in sorted
filename order, starting at --start.

Safe by default: --dry-run previews everything and moves nothing;
real runs never overwrite — a name clash gets a numeric suffix
("name (1).ext"), exactly like organize.py. Files whose new name
equals the old one are skipped. Hidden files are skipped.
"""
import argparse
import sys
from pathlib import Path


def parse_replace(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise argparse.ArgumentTypeError(
            f"--replace expects OLD:NEW, got {spec!r}")
    old, new = spec.split(":", 1)
    if not old:
        raise argparse.ArgumentTypeError("--replace OLD must not be empty")
    return old, new


def build_name(stem: str, prefix: str, replaces: list[tuple[str, str]],
               number: int | None, width: int) -> str:
    for old, new in replaces:
        stem = stem.replace(old, new)
    if prefix:
        stem = prefix + stem
    if number is not None:
        stem = f"{stem}_{number:0{width}d}"
    return stem


def unique_dest(dest: Path, planned: set[str], item: Path) -> Path:
    """Return a non-colliding destination, avoiding existing and planned names.

    A destination equal to the file itself is not a clash (unless an
    earlier file already claimed that name), so unchanged files stay put.
    """
    if dest.name not in planned and (dest == item or not dest.exists()):
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if candidate.name not in planned and not candidate.exists():
            return candidate
        i += 1


def rename(folder: Path, prefix: str, replaces: list[tuple[str, str]],
           numbering: bool, start: int, width: int,
           dry_run: bool = False) -> int:
    if not folder.is_dir():
        print(f"error: {folder} is not a folder", file=sys.stderr)
        return 1
    files = [p for p in sorted(folder.iterdir())
             if p.is_file() and not p.name.startswith(".")]
    planned: set[str] = set()
    renamed = skipped = 0
    number = start if numbering else None
    for item in files:
        stem = build_name(item.stem, prefix, replaces, number, width)
        if number is not None:
            number += 1
        dest = unique_dest(folder / f"{stem}{item.suffix}", planned, item)
        planned.add(dest.name)
        if dest.name == item.name:
            skipped += 1
            continue
        action = "would rename" if dry_run else "renamed"
        print(f"{action}: {item.name}  ->  {dest.name}")
        if not dry_run:
            item.rename(dest)
        renamed += 1
    print(f"\n{'Would rename' if dry_run else 'Renamed'} {renamed} file(s)"
          + (f", {skipped} unchanged." if skipped else "."))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch rename files by prefix, replacement, and/or numbering.")
    parser.add_argument("folder", help="folder whose files to rename (top level only)")
    parser.add_argument("--prefix", default="", help="text to prepend to each stem")
    parser.add_argument("--replace", metavar="OLD:NEW", type=parse_replace,
                        action="append", default=[],
                        help="replace OLD with NEW in each stem (repeatable)")
    parser.add_argument("--numbering", action="store_true",
                        help="append _001, _002, ... in sorted filename order")
    parser.add_argument("--start", type=int, default=1,
                        help="first number when --numbering (default: 1)")
    parser.add_argument("--width", type=int, default=3,
                        help="zero-padding width when --numbering (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview only, rename nothing")
    args = parser.parse_args()
    if not args.prefix and not args.replace and not args.numbering:
        parser.error("nothing to do: give --prefix, --replace, or --numbering")
    if args.start < 0 or args.width < 1:
        parser.error("--start must be >= 0 and --width must be >= 1")
    return rename(Path(args.folder).expanduser(), args.prefix, args.replace,
                  args.numbering, args.start, args.width, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
