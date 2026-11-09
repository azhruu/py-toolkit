#!/usr/bin/env python3
"""Unit tests for organize.py — categories, dry-run, clash-safe moves.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from organize import category_for, organize, unique_dest


class TestCategoryFor(unittest.TestCase):
    def test_known_extensions(self):
        cases = {
            "photo.jpg": "Images", "shot.PNG": "Images", "icon.svg": "Images",
            "report.pdf": "Documents", "notes.md": "Documents", "data.csv": "Documents",
            "song.mp3": "Audio", "clip.wav": "Audio",
            "movie.mp4": "Video", "recording.mkv": "Video",
            "backup.zip": "Archives", "archive.tar": "Archives",
            "script.py": "Code", "page.html": "Code", "config.json": "Code",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(category_for(Path(name)), expected)

    def test_extension_match_is_case_insensitive(self):
        self.assertEqual(category_for(Path("PHOTO.JPEG")), "Images")
        self.assertEqual(category_for(Path("Doc.PDF")), "Documents")

    def test_unknown_and_missing_extension_is_other(self):
        self.assertEqual(category_for(Path("mystery.xyz")), "Other")
        self.assertEqual(category_for(Path("README")), "Other")
        self.assertEqual(category_for(Path(".gitignore")), "Other")


class TestUniqueDest(unittest.TestCase):
    def test_no_clash_returns_same_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "photo.jpg"
            self.assertEqual(unique_dest(dest), dest)

    def test_clash_gets_numeric_suffix(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            dest = folder / "photo.jpg"
            dest.write_bytes(b"x")
            self.assertEqual(unique_dest(dest), folder / "photo (1).jpg")
            (folder / "photo (1).jpg").write_bytes(b"x")
            self.assertEqual(unique_dest(dest), folder / "photo (2).jpg")


class TestOrganize(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        for name, content in {
            "photo.jpg": b"img", "notes.txt": b"hi", "song.mp3": b"au",
            "movie.mp4": b"vid", "data.zip": b"zip", "script.py": b"py",
            "mystery.xyz": b"?",
        }.items():
            (self.folder / name).write_bytes(content)

    def tearDown(self):
        self._tmp.cleanup()

    def test_moves_files_into_category_folders(self):
        self.assertEqual(organize(self.folder), 0)
        self.assertTrue((self.folder / "Images" / "photo.jpg").exists())
        self.assertTrue((self.folder / "Documents" / "notes.txt").exists())
        self.assertTrue((self.folder / "Audio" / "song.mp3").exists())
        self.assertTrue((self.folder / "Video" / "movie.mp4").exists())
        self.assertTrue((self.folder / "Archives" / "data.zip").exists())
        self.assertTrue((self.folder / "Code" / "script.py").exists())
        self.assertTrue((self.folder / "Other" / "mystery.xyz").exists())
        left = [p for p in self.folder.iterdir() if p.is_file()]
        self.assertEqual(left, [])

    def test_dry_run_moves_nothing(self):
        self.assertEqual(organize(self.folder, dry_run=True), 0)
        self.assertTrue((self.folder / "photo.jpg").exists())
        self.assertFalse((self.folder / "Images").exists())

    def test_name_clash_never_overwrites(self):
        images = self.folder / "Images"
        images.mkdir()
        (images / "photo.jpg").write_bytes(b"existing")
        self.assertEqual(organize(self.folder), 0)
        self.assertEqual((images / "photo.jpg").read_bytes(), b"existing")
        self.assertEqual((images / "photo (1).jpg").read_bytes(), b"img")

    def test_hidden_files_and_subfolders_are_left_alone(self):
        (self.folder / ".hidden").write_bytes(b"secret")
        sub = self.folder / "keepme"
        sub.mkdir()
        (sub / "inner.txt").write_bytes(b"stay")
        self.assertEqual(organize(self.folder), 0)
        self.assertTrue((self.folder / ".hidden").exists())
        self.assertTrue((sub / "inner.txt").exists())

    def test_missing_folder_returns_error(self):
        self.assertEqual(organize(self.folder / "no-such-folder"), 1)


if __name__ == "__main__":
    unittest.main()
