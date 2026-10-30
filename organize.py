#!/usr/bin/env python3
"""organize.py — tidy a folder by moving files into subfolders by type.

Usage:
    python organize.py <folder> [--dry-run]

Categories: Images, Documents, Audio, Video, Archives, Code, Other.
Safe by default: never overwrites — name clashes get a numeric suffix.
"""
import argparse
import shutil
import sys
from pathlib import Path

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Audio": {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Code": {".py", ".js", ".java", ".c", ".cpp", ".html", ".css", ".json"},
}


def category_for(path: Path) -> str:
    for name, exts in CATEGORIES.items():
        if path.suffix.lower() in exts:
            return name
    return "Other"


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def organize(folder: Path, dry_run: bool = False) -> int:
    if not folder.is_dir():
        print(f"error: {folder} is not a folder", file=sys.stderr)
        return 1
    moved = 0
    for item in sorted(folder.iterdir()):
        if not item.is_file() or item.name.startswith("."):
            continue
        cat = category_for(item)
        target_dir = folder / cat
        dest = unique_dest(target_dir / item.name)
        action = "would move" if dry_run else "moved"
        print(f"{action}: {item.name}  ->  {cat}/{dest.name}")
        if not dry_run:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest))
        moved += 1
    print(f"\n{'Would move' if dry_run else 'Moved'} {moved} file(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize a folder's files by type.")
    parser.add_argument("folder", help="folder to organize")
    parser.add_argument("--dry-run", action="store_true", help="preview only, move nothing")
    args = parser.parse_args()
    return organize(Path(args.folder).expanduser(), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
