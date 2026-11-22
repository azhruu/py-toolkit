#!/usr/bin/env python3
"""organize.py — tidy a folder by moving files into subfolders by type.

Usage:
    python organize.py <folder> [--dry-run] [--recursive]

Categories: Images, Documents, Audio, Video, Archives, Code, Other.
Safe by default: never overwrites — name clashes get a numeric suffix.
With --recursive, files in subfolders are tidied too, into the same
top-level category folders (files already sitting in a category folder
are left alone); without it, only the top level is touched.
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


def collect_files(folder: Path, recursive: bool) -> list[Path]:
    """Files to organize, in a stable order. Top level only by default;
    with `recursive`, the whole tree. Hidden files — and, when recursing,
    files inside hidden folders — are skipped, as are files already
    sitting in one of the category folders (re-running organize must not
    churn them)."""
    if not recursive:
        return [p for p in sorted(folder.iterdir())
                if p.is_file() and not p.name.startswith(".")]
    files = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(folder)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts[0] in CATEGORIES:
            continue  # already organized — leave it where it is
        files.append(p)
    return files


def organize(folder: Path, dry_run: bool = False, recursive: bool = False) -> int:
    if not folder.is_dir():
        print(f"error: {folder} is not a folder", file=sys.stderr)
        return 1
    moved = 0
    for item in collect_files(folder, recursive):
        cat = category_for(item)
        target_dir = folder / cat
        dest = unique_dest(target_dir / item.name)
        action = "would move" if dry_run else "moved"
        print(f"{action}: {item.relative_to(folder)}  ->  {cat}/{dest.name}")
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
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="organize files in subfolders too, into the top-level category folders")
    args = parser.parse_args()
    return organize(Path(args.folder).expanduser(), dry_run=args.dry_run,
                    recursive=args.recursive)


if __name__ == "__main__":
    raise SystemExit(main())
