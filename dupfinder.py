#!/usr/bin/env python3
"""dupfinder.py — find duplicate files by content hash.

Usage:
    python dupfinder.py <folder> [--min-size BYTES] [--move-to <folder>]

How it works: files are first grouped by size (cheap), then only
same-size files are hashed (SHA-256, read in chunks), so big folders
stay fast. Zero-byte files are skipped — they waste no space.
Nothing is ever deleted: with --move-to, the extras of each duplicate
group are moved into a quarantine folder, keeping the first file.

Example output:
    Found 1 duplicate group, 2 extra file(s), 1.2 MB wasted.
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

CHUNK = 1024 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(folder: Path, min_size: int = 1) -> list[list[Path]]:
    """Return groups of files with identical content, largest waste first."""
    by_size: dict[int, list[Path]] = {}
    for item in sorted(folder.rglob("*")):
        if not item.is_file() or item.is_symlink():
            continue
        try:
            size = item.stat().st_size
        except OSError:
            continue
        if size >= min_size:
            by_size.setdefault(size, []).append(item)

    groups: list[list[Path]] = []
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for path in candidates:
            try:
                by_hash.setdefault(sha256_of(path), []).append(path)
            except OSError as exc:
                print(f"warning: could not read {path}: {exc}", file=sys.stderr)
        groups.extend(g for g in by_hash.values() if len(g) > 1)
    groups.sort(key=lambda g: g[0].stat().st_size * (len(g) - 1), reverse=True)
    return groups


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Find duplicate files by content hash.")
    parser.add_argument("folder", help="folder to scan (recursively)")
    parser.add_argument("--min-size", type=int, default=1,
                        help="ignore files smaller than this many bytes (default: 1)")
    parser.add_argument("--move-to", metavar="FOLDER",
                        help="move duplicate extras here instead of just listing them")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        print(f"error: {folder} is not a folder", file=sys.stderr)
        return 1

    groups = find_duplicates(folder, args.min_size)
    extras = sum(len(g) - 1 for g in groups)
    wasted = sum(g[0].stat().st_size * (len(g) - 1) for g in groups)

    for i, group in enumerate(groups, 1):
        print(f"\nGroup {i} ({len(group)} copies, {human(group[0].stat().st_size)} each):")
        for j, path in enumerate(group):
            tag = "keep" if j == 0 else "dup "
            print(f"  [{tag}] {path}")

    print(f"\nFound {len(groups)} duplicate group(s), "
          f"{extras} extra file(s), {human(wasted)} wasted.")

    if args.move_to and groups:
        dest_dir = Path(args.move_to).expanduser()
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        for group in groups:
            for path in group[1:]:
                dest = dest_dir / path.name
                k = 1
                while dest.exists():
                    dest = dest_dir / f"{path.stem} ({k}){path.suffix}"
                    k += 1
                shutil.move(str(path), str(dest))
                print(f"moved: {path}  ->  {dest}")
                moved += 1
        print(f"Moved {moved} duplicate file(s) to {dest_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
