# py-toolkit

**Small, sharp Python command-line tools for everyday file chores.** Pure standard library — no `pip install` needed, ever.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/status-actively%20building-brightgreen?style=for-the-badge)

## Tools

| Tool | What it does |
|---|---|
| `organize.py` | Sorts a messy folder into subfolders by file type (Images, Documents, Audio, Video, Archives, Code, Other). `--dry-run` previews safely; name clashes never overwrite. |

## Usage

```bash
python organize.py ~/Downloads            # organize for real
python organize.py ~/Downloads --dry-run  # preview first
```

## Coming next

Duplicate-file finder (hash-based) → batch renamer → folder size analyzer → image resizer. Full plan: [ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).
