"""
File Organizer in Python
=========================
Scans a directory, categorizes files by type, and moves them
into organized subfolders automatically.

Author : Debasish Parida
Project: Python Internship — File Organizer

Usage:
    python file_organizer.py                    # interactive menu
    python file_organizer.py --demo             # demo with temp files
    python file_organizer.py --path /your/dir   # organize directly
"""

import os
import shutil
import sys
import time
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────────────────────
# FILE CATEGORY MAP
# extension (lowercase) → folder name
# ─────────────────────────────────────────────────────────────
CATEGORIES: dict[str, str] = {
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
    ".gif": "Images", ".bmp": "Images", ".svg": "Images",
    ".webp": "Images", ".ico": "Images", ".tiff": "Images",
    ".heic": "Images",

    # Videos
    ".mp4": "Videos", ".mkv": "Videos", ".avi": "Videos",
    ".mov": "Videos", ".wmv": "Videos", ".flv": "Videos",
    ".webm": "Videos", ".m4v": "Videos",

    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".aac": "Audio",
    ".flac": "Audio", ".ogg": "Audio", ".m4a": "Audio",
    ".wma": "Audio",

    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".odt": "Documents", ".rtf": "Documents",
    ".md": "Documents",

    # Spreadsheets
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets",
    ".csv": "Spreadsheets", ".ods": "Spreadsheets",

    # Presentations
    ".ppt": "Presentations", ".pptx": "Presentations",
    ".odp": "Presentations",

    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".html": "Code",
    ".css": "Code", ".java": "Code", ".c": "Code", ".cpp": "Code",
    ".cs": "Code", ".go": "Code", ".rb": "Code", ".php": "Code",
    ".swift": "Code", ".kt": "Code", ".r": "Code", ".sh": "Code",
    ".json": "Code", ".xml": "Code", ".yaml": "Code", ".yml": "Code",
    ".toml": "Code", ".env": "Code",

    # Archives
    ".zip": "Archives", ".rar": "Archives", ".tar": "Archives",
    ".gz": "Archives", ".7z": "Archives", ".bz2": "Archives",
    ".xz": "Archives",

    # Executables / Installers
    ".exe": "Executables", ".msi": "Executables", ".dmg": "Executables",
    ".deb": "Executables", ".rpm": "Executables", ".apk": "Executables",

    # Fonts
    ".ttf": "Fonts", ".otf": "Fonts", ".woff": "Fonts", ".woff2": "Fonts",
}

UNKNOWN_FOLDER = "Others"


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_category(file_path: Path) -> str:
    """Return the category folder name for a given file."""
    ext = file_path.suffix.lower()
    return CATEGORIES.get(ext, UNKNOWN_FOLDER)


def scan_directory(directory: Path) -> list[Path]:
    """Return a list of all files (not folders) in the top-level directory."""
    return [f for f in directory.iterdir() if f.is_file()]


def create_folder(folder_path: Path) -> None:
    """Create a folder if it doesn't exist."""
    folder_path.mkdir(parents=True, exist_ok=True)


def resolve_duplicate(dest_path: Path) -> Path:
    """
    If a file already exists at dest_path, append (1), (2), etc.
    until a free name is found.
    """
    if not dest_path.exists():
        return dest_path
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def move_file(file_path: Path, dest_folder: Path) -> tuple[bool, str]:
    """
    Move a single file into dest_folder.
    Returns (success, message).
    """
    try:
        create_folder(dest_folder)
        dest_path = resolve_duplicate(dest_folder / file_path.name)
        shutil.move(str(file_path), str(dest_path))
        return True, f"  ✅  {file_path.name:<40} → {dest_folder.name}/"
    except PermissionError:
        return False, f"  ❌  {file_path.name:<40} — Permission denied"
    except Exception as e:
        return False, f"  ❌  {file_path.name:<40} — {e}"


# ─────────────────────────────────────────────────────────────
# PREVIEW (dry-run)
# ─────────────────────────────────────────────────────────────

def preview(directory: Path) -> dict[str, list[str]]:
    """Show what WILL happen without moving any files."""
    files = scan_directory(directory)
    if not files:
        print("\n  ⚠️  No files found in this directory.\n")
        return {}

    plan: dict[str, list[str]] = defaultdict(list)
    for f in files:
        cat = get_category(f)
        plan[cat].append(f.name)

    print(f"\n  📂 Preview for: {directory}")
    print(f"  {'─' * 55}")
    total = 0
    for cat in sorted(plan):
        count = len(plan[cat])
        total += count
        print(f"  📁 {cat:<20} — {count} file(s)")
        for fname in sorted(plan[cat])[:5]:
            print(f"       • {fname}")
        if count > 5:
            print(f"       … and {count - 5} more")
    print(f"  {'─' * 55}")
    print(f"  Total: {total} file(s) across {len(plan)} folder(s)\n")
    return plan


# ─────────────────────────────────────────────────────────────
# ORGANIZE (actual move)
# ─────────────────────────────────────────────────────────────

def organize(directory: Path) -> dict:
    """
    Scan directory, categorize, and move all files.
    Returns a summary dict.
    """
    files = scan_directory(directory)
    if not files:
        print("\n  ⚠️  No files found. Nothing to organize.\n")
        return {}

    summary: dict[str, int] = defaultdict(int)
    errors: list[str] = []

    print(f"\n  🚀 Organizing {len(files)} file(s) in: {directory}\n")

    for file_path in files:
        category = get_category(file_path)
        dest_folder = directory / category
        success, msg = move_file(file_path, dest_folder)
        print(msg)
        if success:
            summary[category] += 1
        else:
            errors.append(msg)

    # Print summary
    print(f"\n  {'═' * 55}")
    print(f"  📊 Summary")
    print(f"  {'─' * 55}")
    for cat in sorted(summary):
        print(f"  📁 {cat:<22} {summary[cat]:>4} file(s) moved")
    print(f"  {'─' * 55}")
    print(f"  ✅ Moved : {sum(summary.values())} file(s)")
    if errors:
        print(f"  ❌ Failed: {len(errors)} file(s)")
    print(f"  {'═' * 55}\n")

    return dict(summary)


# ─────────────────────────────────────────────────────────────
# UNDO — move files back to root
# ─────────────────────────────────────────────────────────────

def undo_organize(directory: Path) -> None:
    """
    Move all files from category subfolders back to the root directory.
    Only touches known category folders + Others.
    """
    known_folders = set(CATEGORIES.values()) | {UNKNOWN_FOLDER}
    moved_back = 0

    for folder_name in known_folders:
        folder_path = directory / folder_name
        if not folder_path.exists():
            continue
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                dest = resolve_duplicate(directory / file_path.name)
                shutil.move(str(file_path), str(dest))
                print(f"  ↩️  {file_path.name}")
                moved_back += 1
        # Remove folder if now empty
        if not any(folder_path.iterdir()):
            folder_path.rmdir()

    if moved_back:
        print(f"\n  ↩️  Restored {moved_back} file(s) to {directory}\n")
    else:
        print("\n  ⚠️  Nothing to undo — no organized folders found.\n")


# ─────────────────────────────────────────────────────────────
# DEMO — creates temp files, organizes, then cleans up
# ─────────────────────────────────────────────────────────────

def run_demo() -> None:
    """Create dummy files in a temp folder, organize, then show result."""
    import tempfile

    demo_files = [
        "photo_vacation.jpg", "selfie.png", "screenshot.webp",
        "report_Q1.pdf", "notes.txt", "assignment.docx",
        "budget.xlsx", "data.csv",
        "presentation.pptx",
        "song.mp3", "podcast.wav",
        "movie.mp4", "clip.avi",
        "script.py", "index.html", "styles.css", "app.js",
        "backup.zip", "archive.tar.gz",
        "random_file.xyz", "unknown_doc.abc",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print(f"\n  📂 Demo directory: {tmp_path}")
        print(f"  Creating {len(demo_files)} dummy files...\n")

        for fname in demo_files:
            (tmp_path / fname).write_text(f"demo content for {fname}")

        preview(tmp_path)
        input("  Press Enter to organize these files...")
        organize(tmp_path)

        print("  📂 Final folder structure:\n")
        for item in sorted(tmp_path.iterdir()):
            if item.is_dir():
                files_in = list(item.iterdir())
                print(f"  📁 {item.name}/  ({len(files_in)} file(s))")
                for f in sorted(files_in):
                    print(f"       • {f.name}")
        print()


# ─────────────────────────────────────────────────────────────
# INTERACTIVE CLI MENU
# ─────────────────────────────────────────────────────────────

def menu() -> None:
    print("\n" + "=" * 55)
    print("        🗂️  Python File Organizer")
    print("=" * 55)

    while True:
        print("\n  Options:")
        print("  [1] Preview — see what will be organized")
        print("  [2] Organize — move files into folders")
        print("  [3] Undo    — restore files to original location")
        print("  [4] Exit")
        choice = input("\n  Choose (1-4): ").strip()

        if choice in ("1", "2", "3"):
            path_str = input("  Enter directory path: ").strip().strip('"').strip("'")
            directory = Path(path_str)

            if not directory.exists():
                print(f"\n  ❌ Path not found: {directory}\n")
                continue
            if not directory.is_dir():
                print(f"\n  ❌ That's a file, not a folder: {directory}\n")
                continue

            if choice == "1":
                preview(directory)
            elif choice == "2":
                preview(directory)
                confirm = input("  Proceed with organizing? (y/n): ").strip().lower()
                if confirm == "y":
                    organize(directory)
                else:
                    print("  Cancelled.\n")
            elif choice == "3":
                confirm = input("  Restore all files to root? (y/n): ").strip().lower()
                if confirm == "y":
                    undo_organize(directory)
                else:
                    print("  Cancelled.\n")

        elif choice == "4":
            print("\n  Goodbye! 👋\n")
            break
        else:
            print("  ⚠️  Enter 1, 2, 3, or 4.")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--demo" in args:
        run_demo()
    elif "--path" in args:
        idx = args.index("--path")
        if idx + 1 < len(args):
            target = Path(args[idx + 1])
            if target.is_dir():
                preview(target)
                organize(target)
            else:
                print(f"❌ Invalid path: {target}")
        else:
            print("❌ Provide a path after --path")
    else:
        menu()