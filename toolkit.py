#!/usr/bin/env python3
"""toolkit.py — one front door for every tool in py-toolkit.

Interactive menu (no arguments):

    python toolkit.py

Pick a tool by number, answer a few prompts, and it runs — with the
same flags the standalone script takes. After a tool finishes you can
run another one or quit (`q` / `0`).

Direct mode (arguments are passed straight through to the tool):

    python toolkit.py organize ~/Downloads --dry-run
    python toolkit.py dupfinder ~/Downloads --min-size 1024
    python toolkit.py rename ~/Photos --prefix vacay- --numbering
    python toolkit.py dirsize ~/Downloads --top 5
    python toolkit.py imgshrink photo.png --width 800
    python toolkit.py textstats notes.md --json

    python toolkit.py --list            # show the menu and exit
    python toolkit.py organize --help   # that tool's own --help

A mistyped tool name gets a "did you mean …?" hint instead of a bare error.

The launcher never changes what a tool does: it just finds the script
next to itself and runs it with your Python, forwarding its exit code.
"""
import difflib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# name -> (script, one-line description)
TOOLS = {
    "organize": ("organize.py", "Sort a messy folder into subfolders by file type"),
    "dupfinder": ("dupfinder.py", "Find duplicate files by content hash, report wasted space"),
    "rename": ("rename.py", "Batch-rename files: --prefix, --replace, --numbering"),
    "dirsize": ("dirsize.py", "Biggest folders & files in a tree, with bars"),
    "imgshrink": ("imgshrink.py", "Batch-resize images (stdlib only: PNG/BMP)"),
    "textstats": ("textstats.py", "Word/line/reading-time stats for text & markdown"),
}

# Interactive prompts per tool: (question, flag or None, default).
# A flag of None means the answer is a positional argument; an empty
# answer skips that prompt. A yes/no prompt adds the flag when "y".
PROMPTS = {
    "organize": [
        ("Folder to organize", None, ""),
        ("Preview only, move nothing? [y/N]", "--dry-run", "n"),
    ],
    "dupfinder": [
        ("Folder to scan (recursively)", None, ""),
        ("Minimum file size in bytes (blank = 1)", "--min-size", ""),
        ("Move duplicates to folder (blank = report only)", "--move-to", ""),
    ],
    "rename": [
        ("Folder whose files to rename", None, ""),
        ("Prefix to add (blank = none)", "--prefix", ""),
        ("Replace OLD:NEW, comma-separated (blank = none)", "--replace", ""),
        ("Add _001, _002 numbering? [y/N]", "--numbering", "n"),
        ("Preview only, rename nothing? [y/N]", "--dry-run", "n"),
    ],
    "dirsize": [
        ("Folder to measure", None, ""),
        ("How many entries to show (blank = 10)", "--top", ""),
        ("Only show entries at least this big, e.g. 10MB (blank = all)", "--min-size", ""),
    ],
    "imgshrink": [
        ("Image file(s) or folder, space-separated", None, ""),
        ("Resize to width in px (blank = none)", "--width", ""),
        ("…or longest side in px (blank = none)", "--max", ""),
        ("…or scale factor, e.g. 0.5 (blank = none)", "--scale", ""),
        ("Folder for resized copies (blank = next to original)", "--out", ""),
        ("Preview only, write nothing? [y/N]", "--dry-run", "n"),
    ],
    "textstats": [
        ("File(s) or folder, space-separated", None, ""),
        ("Scan subfolders too? [y/N]", "--recursive", "n"),
        ("Machine-readable JSON output? [y/N]", "--json", "n"),
    ],
}


def show_menu() -> None:
    print("py-toolkit — pick a tool:")
    for i, (name, (_, desc)) in enumerate(TOOLS.items(), 1):
        print(f"  {i}. {name:<11} {desc}")
    print("  0. Quit")


def resolve(name: str) -> str | None:
    """Tool name (with or without .py, any case) -> key, or None."""
    name = name.lower().removesuffix(".py")
    return name if name in TOOLS else None


def suggest(name: str) -> str | None:
    """Closest real tool name to a mistyped one, or None if nothing is close."""
    matches = difflib.get_close_matches(
        name.lower().removesuffix(".py"), TOOLS, n=1, cutoff=0.6)
    return matches[0] if matches else None


def run_tool(name: str, args: list[str]) -> int:
    script = HERE / TOOLS[name][0]
    if not script.is_file():
        print(f"error: {script} is missing", file=sys.stderr)
        return 1
    try:
        return subprocess.run([sys.executable, str(script), *args]).returncode
    except KeyboardInterrupt:
        print("\ninterrupted.")
        return 130


def ask(prompt: str, default: str = "") -> str:
    try:
        answer = input(f"{prompt}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0)
    return answer or default


def build_args(name: str) -> list[str] | None:
    """Prompt for a tool's arguments; None means the user bailed out."""
    args: list[str] = []
    for question, flag, default in PROMPTS[name]:
        answer = ask(question, default)
        if not answer:
            continue
        if flag is None:
            args.extend(answer.split())
        elif flag in ("--dry-run", "--numbering", "--recursive", "--json"):
            if answer.lower().startswith("y"):
                args.append(flag)
        elif flag == "--replace":
            for spec in answer.split(","):
                spec = spec.strip()
                if spec:
                    args.extend([flag, spec])
        else:
            args.extend([flag, answer])
    return args


def interactive() -> int:
    names = list(TOOLS)
    while True:
        show_menu()
        choice = ask("Tool number or name (0/q to quit)").lower()
        if choice in ("0", "q", "quit", "exit"):
            print("Bye!")
            return 0
        key = resolve(choice)
        if key is None and choice.isdigit() and 1 <= int(choice) <= len(names):
            key = names[int(choice) - 1]
        if key is None:
            hint = suggest(choice)
            msg = f"no tool called {choice!r}"
            if hint:
                msg += f" — did you mean {hint!r}?"
            msg += f" Pick a number 1–{len(names)} or a name.\n"
            print(msg)
            continue
        args = build_args(key)
        if args is None:
            continue
        print(f"\n$ python {TOOLS[key][0]} {' '.join(args)}\n")
        code = run_tool(key, args)
        print(f"\n[{TOOLS[key][0]} finished, exit code {code}]\n")
        again = ask("Run another tool? [Y/n]", "y")
        if again.lower().startswith("n"):
            print("Bye!")
            return 0


def main(argv: list[str]) -> int:
    if not argv:
        return interactive()
    if argv[0] in ("--list", "list"):
        show_menu()
        return 0
    if argv[0] in ("-h", "--help"):
        show_menu()
        print("\nDirect mode: toolkit.py <tool> [args passed to that tool]")
        print("Interactive: toolkit.py")
        return 0
    key = resolve(argv[0])
    if key is None:
        print(f"error: no tool called {argv[0]!r}", file=sys.stderr)
        hint = suggest(argv[0])
        if hint:
            print(f"did you mean {hint!r}?", file=sys.stderr)
        print("Run `python toolkit.py --list` to see the tools.", file=sys.stderr)
        return 2
    return run_tool(key, argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
