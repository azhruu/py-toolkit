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
