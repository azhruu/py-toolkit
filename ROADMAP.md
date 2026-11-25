# py-toolkit — Build Roadmap

Each item lands as one complete, tested change.

- [x] organize.py — sort a folder by file type, with --dry-run and clash-safe names
 - [x] dupfinder.py — find duplicate files by content hash
- [x] rename.py — batch rename with patterns (prefix, numbering, replace)
- [x] dirsize.py — biggest folders/files report for a directory tree
- [x] imgshrink.py — batch-resize images (Pillow-free: use stdlib where possible, note limits)
- [x] textstats.py — word/line/reading-time stats for text & markdown files
- [x] Unified `toolkit.py` menu launcher for all tools
- [x] Unit tests (unittest) for organize + dupfinder
- [x] README demos with real before/after terminal output
- [x] Launcher "did you mean?" hint for mistyped tool names (+ tests)

## Polish (after the roadmap above)

- [x] `toolkit.py --version` / `-V` flag (+ tests)
- [x] Unit tests (unittest) for rename.py — patterns, numbering, dry-run, clash safety
- [x] Unit tests (unittest) for dirsize.py — size formatting/parsing, bars, tree walk (hidden files, symlinks), report filtering
- [x] Unit tests (unittest) for textstats.py — markdown stripping, sentence/paragraph counts, reading time, top words, per-file stats, totals, file collection
- [x] Unit tests (unittest) for imgshrink.py — sizing, resampling, PNG/BMP round-trips (incl. filters, palette, 16-bit, top-down BMP), format detection, clash safety, dry-run/in-place
- [x] Interactive menu: a blank answer to a required folder/file prompt cancels back to the menu instead of running the tool with no arguments (+ tests)
- [x] Interactive menu asks textstats how many top words to show — blank keeps the default 5, a number passes `--top N` through (+ tests)
- [x] Direct mode accepts a tool's menu number — `toolkit.py 1 …` runs the same tool as picking 1 in the interactive menu (+ tests)
- [x] Interactive menu: a blank answer at the tool prompt quits cleanly instead of printing "no tool called ''" (+ tests)
- [x] Interactive prompts accept quoted paths with spaces — `"My Photos"` stays one argument instead of splitting on the space, with a plain-split fallback for unbalanced quotes (+ tests)
- [x] organize.py `--recursive` — tidy nested folders too, into the same top-level category folders; hidden files/folders skipped, files already in a category folder left alone, name clashes get a suffix (+ tests, launcher prompt)
- [x] dupfinder.py `--min-size` takes human sizes — `10KB` / `1.5MB` like dirsize.py (same parsing, so the tools agree), plain bytes still work, bad sizes fail with a clear error (+ tests, launcher prompt)
- [x] `toolkit.py --help` / `-h` prints the full usage — direct-mode examples, interactive-menu notes and the tool list from the module docstring — instead of just the menu and two lines (+ tests)
- [x] Interactive menu: Ctrl-C / Ctrl-D at a tool prompt cancels back to the menu instead of quitting the whole launcher (the menu prompt still quits cleanly) (+ tests)
