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
| `toolkit.py` | One front door for all six tools: run it with no arguments for an interactive menu, or `toolkit.py <tool> [args]` to run a tool directly (args pass straight through). |
| `textstats.py` | Word/line/reading-time stats for text & markdown files. Markdown-aware (code blocks, links, headings and emphasis stripped before counting), `--recursive` folder scans, `--top N` most common words, `--wpm`, `--json`, `--raw`. Read-only. |

## Usage

```bash
python -m unittest discover -s tests -v   # run the test suite (22 tests)
python toolkit.py                              # interactive menu for all tools
python toolkit.py organize ~/Downloads --dry-run  # or run a tool directly
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
python textstats.py notes.md                 # words, lines, reading time, top words
python textstats.py docs/ --recursive        # every text/markdown file in a folder
python textstats.py a.md b.txt --json        # machine-readable output
```

<!-- demos:start -->

## Demos

Real terminal output from running the tools on throwaway demo folders — regenerate it any time with:

```bash
python demos/generate_demos.py   # rebuilds this section from live runs
```

### organize.py — sort a messy folder by file type

Before:

```
demo-downloads/
  backup.zip
  beach.jpg
  clip.mp4
  notes.md
  photo-copy.jpg
  report.txt
  script.py
  song.mp3
```

```bash
$ python organize.py demo-downloads --dry-run
```

```
would move: backup.zip  ->  Archives/backup.zip
would move: beach.jpg  ->  Images/beach.jpg
would move: clip.mp4  ->  Video/clip.mp4
would move: notes.md  ->  Documents/notes.md
would move: photo-copy.jpg  ->  Images/photo-copy.jpg
would move: report.txt  ->  Documents/report.txt
would move: script.py  ->  Code/script.py
would move: song.mp3  ->  Audio/song.mp3

Would move 8 file(s).
```

```bash
$ python organize.py demo-downloads
```

```
moved: backup.zip  ->  Archives/backup.zip
moved: beach.jpg  ->  Images/beach.jpg
moved: clip.mp4  ->  Video/clip.mp4
moved: notes.md  ->  Documents/notes.md
moved: photo-copy.jpg  ->  Images/photo-copy.jpg
moved: report.txt  ->  Documents/report.txt
moved: script.py  ->  Code/script.py
moved: song.mp3  ->  Audio/song.mp3

Moved 8 file(s).
```

```
After:
demo-downloads/
  Archives/
    backup.zip
  Audio/
    song.mp3
  Code/
    script.py
  Documents/
    notes.md
    report.txt
  Images/
    beach.jpg
    photo-copy.jpg
  Video/
    clip.mp4
```

### dupfinder.py — find duplicates by content hash

`beach.jpg` and `photo-copy.jpg` are byte-identical:

```bash
$ python dupfinder.py demo-downloads
```

```

Group 1 (2 copies, 8 B each):
  [keep] demo-downloads/Images/beach.jpg
  [dup ] demo-downloads/Images/photo-copy.jpg

Found 1 duplicate group(s), 1 extra file(s), 8 B wasted.
```

```bash
$ python dupfinder.py demo-downloads --move-to dupes
```

```

Group 1 (2 copies, 8 B each):
  [keep] demo-downloads/Images/beach.jpg
  [dup ] demo-downloads/Images/photo-copy.jpg

Found 1 duplicate group(s), 1 extra file(s), 8 B wasted.
moved: demo-downloads/Images/photo-copy.jpg  ->  dupes/photo-copy.jpg
Moved 1 duplicate file(s) to dupes.
```

```
dupes/
  photo-copy.jpg
```

### rename.py — batch rename with prefix and numbering

```bash
$ python rename.py photos --prefix vacay- --numbering --dry-run
```

```
would rename: IMG_20240101.jpg  ->  vacay-IMG_20240101_001.jpg
would rename: IMG_20240102.jpg  ->  vacay-IMG_20240102_002.jpg
would rename: IMG_20240103.jpg  ->  vacay-IMG_20240103_003.jpg

Would rename 3 file(s).
```

```bash
$ python rename.py photos --prefix vacay- --numbering
```

```
renamed: IMG_20240101.jpg  ->  vacay-IMG_20240101_001.jpg
renamed: IMG_20240102.jpg  ->  vacay-IMG_20240102_002.jpg
renamed: IMG_20240103.jpg  ->  vacay-IMG_20240103_003.jpg

Renamed 3 file(s).
```

```
photos/
  vacay-IMG_20240101_001.jpg
  vacay-IMG_20240102_002.jpg
  vacay-IMG_20240103_003.jpg
```

### dirsize.py — biggest folders and files in a tree

```bash
$ python dirsize.py sizes --top 5
```

```
sizes
Total: 3.3 MB  (4 file(s), 3 folder(s))

Biggest files (top 4):
      2.4 MB  |##############################|  media/movie.mp4
    781.2 KB  |##########--------------------|  docs/archive.zip
    117.2 KB  |#-----------------------------|  media/photo.jpg
      2.9 KB  |------------------------------|  docs/notes.txt

Biggest folders (top 2, depth 2):
      2.5 MB  |##############################|  media
    784.2 KB  |#########---------------------|  docs
```

### textstats.py — word, line and reading-time stats

```bash
$ python textstats.py trip.md
```

```
trip.md
  Lines: 6   Words: 24   Characters: 124 (96 without spaces)
  Sentences: 3   Paragraphs: 3   Reading time: 7 sec (@ 200 wpm)
  Longest word: notes
  Top words: quick (2), fox (2), lazy (2), dog (2), pack (2)
```

### imgshrink.py — batch-resize images (stdlib only)

An 800×600 PNG, shrunk to fit inside 200×200:

```bash
$ python imgshrink.py big.png --max 200 --dry-run
```

```
would resize: big.png 800x600 -> 200x150

Would resize 1 file(s), skipped 0, 0 error(s).
```

```bash
$ python imgshrink.py big.png --max 200
```

```
big.png 800x600 -> 200x150 (2.3 KB -> 345 B) -> big-small.png

Resized 1 file(s), skipped 0, 0 error(s).
```

<!-- demos:end -->

## Coming next

Every roadmap item is done — see [ROADMAP.md](ROADMAP.md). The demos above are regenerated from live runs with `python demos/generate_demos.py`.

## License

MIT — see [LICENSE](LICENSE).
