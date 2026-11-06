# py-toolkit

**Small, sharp Python command-line tools for everyday file chores.** Pure standard library — no `pip install` needed, ever.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/status-actively%20building-brightgreen?style=for-the-badge)

## Tools

| Tool | What it does |
|---|---|
| `organize.py` | Sorts a messy folder into subfolders by file type (Images, Documents, Audio, Video, Archives, Code, Other). `--dry-run` previews safely; name clashes never overwrite. |
| `dupfinder.py` | Finds duplicate files by content hash (size-grouped first, so big folders stay fast). Reports wasted space; `--move-to` quarantines the extras, nothing is ever deleted. |
| `rename.py` | Batch-renames files with `--prefix`, repeatable `--replace OLD:NEW`, and `--numbering` (`_001`, `_002`, …). `--dry-run` previews; clashes never overwrite. |
| `dirsize.py` | Reports the biggest folders and files in a tree with scaled bars. `--top N`, `--depth N`, `--min-size 10MB`, `--files-only` / `--dirs-only`, `--all` for hidden files. Read-only; symlinks never followed. |
| `imgshrink.py` | Batch-resizes images with the standard library only — PNG and BMP are resized for real; JPEG/GIF/WebP are reported and skipped (they need Pillow). `--width` / `--height` / `--max` / `--scale`, `--out`, `--suffix`, `--in-place`, `--dry-run`, `--recursive`. Never overwrites by accident. |

## Usage

```bash
python organize.py ~/Downloads            # organize for real
python organize.py ~/Downloads --dry-run  # preview first
python dupfinder.py ~/Downloads           # find duplicates by content hash
python dupfinder.py ~/Downloads --move-to ~/dupes  # quarantine the extras
python rename.py ~/Photos --prefix vacay- --replace " :_" --numbering  # vacay-IMG_001_01.jpg …
python rename.py ~/Photos --dry-run --prefix vacay-  # preview first
python dirsize.py ~/Downloads               # biggest folders & files
python dirsize.py ~/Downloads --top 5 --min-size 10MB  # worst offenders only
python imgshrink.py ~/Photos --max 1200      # shrink PNG/BMP copies to fit 1200px
python imgshrink.py photo.png --width 800 --in-place  # resize the original
python imgshrink.py ~/Photos --scale 0.5 --dry-run    # preview first
```

## Coming next

Image resizer → text stats. Full plan: [ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).
