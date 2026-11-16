#!/usr/bin/env python3
"""Unit tests for imgshrink.py — sizing, resampling, PNG/BMP round-trips,
format detection, clash safety and the shrink_file driver.

Run from the repo root:

    python -m unittest discover -s tests -v
"""
import argparse
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imgshrink import (
    collect, decode_bmp, decode_png, detect_format, encode_bmp, encode_png,
    human_size, imgshrink, paeth, png_chunk, resize_pixels, shrink_file,
    target_size, unique_dest,
)


def _args(**over):
    """An argparse namespace like main() builds, with the sizing flags."""
    base = dict(scale=None, width=None, height=None, max=None,
                in_place=False, out=None, suffix="-small", force=False,
                dry_run=False, recursive=False)
    base.update(over)
    return argparse.Namespace(**base)


def _png_bytes(width, height, rows, colour=2, depth=8, palette=None,
               filter_rows=None):
    """Build a small PNG by hand (lets tests use filters the encoder
    never writes, e.g. Sub / Up / Average)."""
    ihdr = struct.pack(">IIBBBBB", width, height, depth, colour, 0, 0, 0)
    if filter_rows is None:
        raw = bytearray()
        for row in rows:
            raw.append(0)
            for px in row:
                raw.extend(px if isinstance(px, (bytes, bytearray)) else bytes(px))
    else:
        raw = filter_rows
    out = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
    if palette is not None:
        plte = b"".join(bytes(c) for c in palette)
        out += png_chunk(b"PLTE", plte)
    out += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += png_chunk(b"IEND", b"")
    return out


class TestHumanSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(500), "500 B")
        self.assertEqual(human_size(1023), "1023 B")

    def test_kilobytes(self):
        self.assertEqual(human_size(1024), "1.0 KB")
        self.assertEqual(human_size(1536), "1.5 KB")

    def test_megabytes(self):
        self.assertEqual(human_size(1024 * 1024), "1.0 MB")
        self.assertEqual(human_size(5 * 1024 * 1024 + 512 * 1024), "5.5 MB")


class TestTargetSize(unittest.TestCase):
    def test_scale_halves(self):
        self.assertEqual(target_size(800, 600, _args(scale=0.5)), (400, 300))

    def test_scale_one_is_noop(self):
        self.assertIsNone(target_size(800, 600, _args(scale=1.0)))

    def test_scale_can_enlarge(self):
        self.assertEqual(target_size(100, 50, _args(scale=2.0)), (200, 100))

    def test_scale_never_below_one_pixel(self):
        self.assertEqual(target_size(3, 2, _args(scale=0.1)), (1, 1))

    def test_width_keeps_aspect(self):
        self.assertEqual(target_size(800, 600, _args(width=400)), (400, 300))

    def test_width_already_small_is_noop(self):
        self.assertIsNone(target_size(300, 200, _args(width=400)))

    def test_height_keeps_aspect(self):
        self.assertEqual(target_size(800, 600, _args(height=300)), (400, 300))

    def test_height_already_small_is_noop(self):
        self.assertIsNone(target_size(800, 200, _args(height=300)))

    def test_max_fits_longest_side(self):
        # 800x600 inside a 400 box -> 400x300.
        self.assertEqual(target_size(800, 600, _args(max=400)), (400, 300))
        # Tall image: the height is the limiting side.
        self.assertEqual(target_size(600, 800, _args(max=400)), (300, 400))

    def test_max_already_fits_is_noop(self):
        self.assertIsNone(target_size(300, 200, _args(max=400)))


class TestResizePixels(unittest.TestCase):
    def test_down_to_one_pixel_takes_top_left(self):
        rows = [[(1, 2, 3), (4, 5, 6)], [(7, 8, 9), (10, 11, 12)]]
        self.assertEqual(resize_pixels(rows, 1, 1), [[(1, 2, 3)]])

    def test_upscale_repeats_nearest(self):
        rows = [[(9, 9, 9)]]
        self.assertEqual(resize_pixels(rows, 3, 2),
                         [[(9, 9, 9)] * 3, [(9, 9, 9)] * 3])

    def test_downscale_picks_nearest_source(self):
        rows = [[(1, 0, 0), (2, 0, 0), (3, 0, 0), (4, 0, 0)],
                [(5, 0, 0), (6, 0, 0), (7, 0, 0), (8, 0, 0)]]
        self.assertEqual(resize_pixels(rows, 2, 1),
                         [[(1, 0, 0), (3, 0, 0)]])

    def test_same_size_is_identity(self):
        rows = [[(1, 2, 3), (4, 5, 6)], [(7, 8, 9), (10, 11, 12)]]
        self.assertEqual(resize_pixels(rows, 2, 2), rows)


class TestPaeth(unittest.TestCase):
    def test_left_wins(self):
        self.assertEqual(paeth(10, 5, 5), 10)

    def test_up_wins(self):
        self.assertEqual(paeth(5, 10, 5), 10)

    def test_upper_left_wins(self):
        # p = 100 + 0 - 50 = 50, closest to c (50).
        self.assertEqual(paeth(100, 0, 50), 50)

    def test_tie_prefers_left(self):
        self.assertEqual(paeth(10, 10, 10), 10)


class TestPngRoundTrip(unittest.TestCase):
    def test_rgb_round_trip(self):
        rows = [[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
                [(10, 20, 30), (40, 50, 60), (70, 80, 90)]]
        decoded, has_alpha = decode_png(encode_png(rows, False))
        self.assertEqual(decoded, rows)
        self.assertFalse(has_alpha)

    def test_rgba_round_trip_keeps_alpha(self):
        rows = [[(255, 0, 0, 128), (0, 255, 0, 255)],
                [(0, 0, 255, 0), (1, 2, 3, 200)]]
        decoded, has_alpha = decode_png(encode_png(rows, True))
        self.assertEqual(decoded, rows)
        self.assertTrue(has_alpha)

    def test_grey_expands_to_rgb(self):
        # 1x2 greyscale PNG, filter 0 rows: grey values 0 and 255.
        data = _png_bytes(1, 2, [[(0,)], [(255,)]], colour=0)
        decoded, has_alpha = decode_png(data)
        self.assertEqual(decoded, [[(0, 0, 0)], [(255, 255, 255)]])
        self.assertFalse(has_alpha)

    def test_palette_expands_through_plte(self):
        palette = [(255, 0, 0), (0, 0, 255)]
        data = _png_bytes(2, 1, [[(0,), (1,)]], colour=3, palette=palette)
        decoded, _ = decode_png(data)
        self.assertEqual(decoded, [[(255, 0, 0), (0, 0, 255)]])

    def test_16bit_keeps_high_byte(self):
        # One RGB pixel, 16-bit samples: high bytes 0x12, 0x56, 0x9A.
        raw = b"\x00" + bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])
        data = _png_bytes(1, 1, [], colour=2, depth=16, filter_rows=raw)
        decoded, _ = decode_png(data)
        self.assertEqual(decoded, [[(0x12, 0x56, 0x9A)]])

    def test_sub_filter(self):
        # 2x1 RGB, filter 1 (Sub): second pixel stored as the difference
        # from its left neighbour: (40-10, 50-20, 60-30) = (30, 30, 30).
        raw = b"\x01" + bytes([10, 20, 30, 30, 30, 30])
        data = _png_bytes(2, 1, [], filter_rows=raw)
        decoded, _ = decode_png(data)
        self.assertEqual(decoded, [[(10, 20, 30), (40, 50, 60)]])

    def test_up_filter(self):
        # Two rows, second row filter 2 (Up): stored as the difference
        # from the row above: (5, 5, 5) per pixel.
        raw = (b"\x00" + bytes([10, 20, 30, 40, 50, 60])
               + b"\x02" + bytes([5, 5, 5, 5, 5, 5]))
        data = _png_bytes(2, 2, [], filter_rows=raw)
        decoded, _ = decode_png(data)
        self.assertEqual(decoded, [[(10, 20, 30), (40, 50, 60)],
                                   [(15, 25, 35), (45, 55, 65)]])

    def test_average_filter(self):
        # Row 0 filter 0; row 1 filter 3 (Average): each stored byte is
        # the value minus floor((left + above) / 2).
        # Row 1 pixel 0: 15 - (0 + 10) // 2 = 10. Pixel 1: 45 - (15 + 40) // 2 = 18.
        raw = (b"\x00" + bytes([10, 20, 30, 40, 50, 60])
               + b"\x03" + bytes([10, 15, 20, 18, 18, 18]))
        data = _png_bytes(2, 2, [], filter_rows=raw)
        decoded, _ = decode_png(data)
        self.assertEqual(decoded, [[(10, 20, 30), (40, 50, 60)],
                                   [(15, 25, 35), (45, 55, 65)]])


class TestPngErrors(unittest.TestCase):
    def test_not_a_png(self):
        with self.assertRaises(ValueError):
            decode_png(b"hello, world")

    def test_missing_ihdr(self):
        data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IEND", b""))
        with self.assertRaises(ValueError):
            decode_png(data)

    def test_interlaced_rejected(self):
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 1)
        data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
                + png_chunk(b"IEND", b""))
        with self.assertRaises(ValueError):
            decode_png(data)

    def test_unsupported_bit_depth(self):
        ihdr = struct.pack(">IIBBBBB", 1, 1, 1, 2, 0, 0, 0)
        data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
                + png_chunk(b"IEND", b""))
        with self.assertRaises(ValueError):
            decode_png(data)

    def test_palette_without_plte(self):
        data = _png_bytes(1, 1, [[(0,)]], colour=3)
        with self.assertRaises(ValueError):
            decode_png(data)

    def test_truncated_idat(self):
        ihdr = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
        data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
                + png_chunk(b"IDAT", zlib.compress(b"\x00\x01\x02\x03"))
                + png_chunk(b"IEND", b""))
        with self.assertRaises(ValueError):
            decode_png(data)


class TestBmpRoundTrip(unittest.TestCase):
    def test_24bit_round_trip(self):
        rows = [[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
                [(1, 2, 3), (4, 5, 6), (7, 8, 9)]]
        decoded, bits = decode_bmp(encode_bmp(rows, 24))
        self.assertEqual(decoded, rows)
        self.assertEqual(bits, 24)

    def test_32bit_round_trip_keeps_alpha(self):
        rows = [[(255, 0, 0, 128), (0, 255, 0, 255)],
                [(0, 0, 255, 0), (9, 8, 7, 64)]]
        decoded, bits = decode_bmp(encode_bmp(rows, 32))
        self.assertEqual(decoded, rows)
        self.assertEqual(bits, 32)

    def test_top_down_bmp(self):
        # Hand-built 2x2, 24-bit, negative height = rows stored top-down.
        width, height = 2, -2
        row_bytes = 8  # 2 px * 3 bytes, padded to a multiple of 4
        pixels = bytes([
            0, 0, 255, 0, 255, 0, 0, 0,      # (255,0,0) (0,255,0)
            255, 0, 0, 255, 255, 255, 0, 0,  # (0,0,255) (255,255,255)
        ])
        offset = 54
        header = struct.pack("<2sIHHI", b"BM", offset + len(pixels), 0, 0, offset)
        dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                          len(pixels), 2835, 2835, 0, 0)
        decoded, bits = decode_bmp(header + dib + pixels)
        self.assertEqual(decoded, [[(255, 0, 0), (0, 255, 0)],
                                   [(0, 0, 255), (255, 255, 255)]])
        self.assertEqual(bits, 24)

    def test_not_a_bmp(self):
        with self.assertRaises(ValueError):
            decode_bmp(b"not a bmp at all, far too short")

    def test_unsupported_bpp(self):
        # A valid-looking header claiming 8-bit.
        header = struct.pack("<2sIHHI", b"BM", 54, 0, 0, 54)
        dib = struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 8, 0, 0, 2835, 2835, 0, 0)
        with self.assertRaises(ValueError):
            decode_bmp(header + dib)


class TestDetectFormat(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _detect(self, name, head):
        path = self.folder / name
        path.write_bytes(head + b"\x00" * 32)
        return detect_format(path)

    def test_png_by_magic_not_extension(self):
        sig = b"\x89PNG\r\n\x1a\n"
        self.assertEqual(self._detect("photo.jpg", sig), "png")

    def test_bmp(self):
        self.assertEqual(self._detect("x.bin", b"BM"), "bmp")

    def test_jpeg(self):
        self.assertEqual(self._detect("x.png", b"\xff\xd8\xff"), "jpeg")

    def test_gif89a(self):
        self.assertEqual(self._detect("x.png", b"GIF89a"), "gif")

    def test_webp(self):
        self.assertEqual(self._detect("x.png", b"RIFF\x00\x00\x00\x00WEBP"), "webp")

    def test_other(self):
        self.assertEqual(self._detect("x.png", b"plain text here"), "other")


class TestUniqueDest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_free_name_returned_as_is(self):
        dest = self.folder / "photo-small.png"
        self.assertEqual(unique_dest(dest), dest)

    def test_clash_gets_numeric_suffix(self):
        (self.folder / "photo-small.png").write_bytes(b"x")
        self.assertEqual(unique_dest(self.folder / "photo-small.png").name,
                         "photo-small (1).png")

    def test_suffix_increments(self):
        (self.folder / "photo-small.png").write_bytes(b"x")
        (self.folder / "photo-small (1).png").write_bytes(b"x")
        self.assertEqual(unique_dest(self.folder / "photo-small.png").name,
                         "photo-small (2).png")


class TestShrinkFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        self.rows = [[(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)],
                     [(40, 50, 60), (70, 80, 90), (100, 110, 120), (130, 140, 150)]]
        self.png = self.folder / "photo.png"
        self.png.write_bytes(encode_png(self.rows, False))
        self.bmp = self.folder / "scan.bmp"
        self.bmp.write_bytes(encode_bmp(self.rows, 24))

    def tearDown(self):
        self._tmp.cleanup()

    def _dims(self, path):
        rows, _ = decode_png(path.read_bytes())
        return len(rows[0]), len(rows)

    def test_png_resize_writes_copy(self):
        status, msg = shrink_file(self.png, _args(width=2))
        self.assertEqual(status, "resized")
        out = self.folder / "photo-small.png"
        self.assertTrue(out.exists())
        self.assertEqual(self._dims(out), (2, 1))
        self.assertIn("4x2 -> 2x1", msg)
        # Original untouched.
        self.assertEqual(self._dims(self.png), (4, 2))

    def test_bmp_resize(self):
        status, _ = shrink_file(self.bmp, _args(scale=0.5))
        self.assertEqual(status, "resized")
        out = self.folder / "scan-small.bmp"
        self.assertTrue(out.exists())
        rows, bits = decode_bmp(out.read_bytes())
        self.assertEqual((len(rows[0]), len(rows)), (2, 1))
        self.assertEqual(bits, 24)

    def test_already_small_is_skipped(self):
        status, msg = shrink_file(self.png, _args(width=100))
        self.assertEqual(status, "skipped")
        self.assertIn("no shrinking needed", msg)
        self.assertFalse((self.folder / "photo-small.png").exists())

    def test_jpeg_skipped_with_pillow_note(self):
        jpg = self.folder / "snap.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 32)
        status, msg = shrink_file(jpg, _args(width=100))
        self.assertEqual(status, "skipped")
        self.assertIn("needs Pillow", msg)

    def test_non_image_skipped(self):
        txt = self.folder / "notes.txt"
        txt.write_text("hello")
        status, _ = shrink_file(txt, _args(width=100))
        self.assertEqual(status, "skipped")

    def test_corrupt_png_is_error(self):
        bad = self.folder / "broken.png"
        bad.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbagegarbage")
        status, msg = shrink_file(bad, _args(width=100))
        self.assertEqual(status, "error")
        self.assertIn("cannot read", msg)

    def test_dry_run_writes_nothing(self):
        status, msg = shrink_file(self.png, _args(width=2, dry_run=True))
        self.assertEqual(status, "resized")
        self.assertIn("would resize", msg)
        self.assertFalse((self.folder / "photo-small.png").exists())

    def test_in_place_overwrites_original(self):
        status, _ = shrink_file(self.png, _args(width=2, in_place=True))
        self.assertEqual(status, "resized")
        self.assertEqual(self._dims(self.png), (2, 1))
        self.assertFalse((self.folder / "photo-small.png").exists())

    def test_clash_gets_numeric_suffix(self):
        (self.folder / "photo-small.png").write_bytes(b"existing")
        status, _ = shrink_file(self.png, _args(width=2))
        self.assertEqual(status, "resized")
        out = self.folder / "photo-small (1).png"
        self.assertTrue(out.exists())
        self.assertEqual(self._dims(out), (2, 1))

    def test_force_overwrites_existing_copy(self):
        dest = self.folder / "photo-small.png"
        dest.write_bytes(b"old")
        status, _ = shrink_file(self.png, _args(width=2, force=True))
        self.assertEqual(status, "resized")
        self.assertEqual(self._dims(dest), (2, 1))

    def test_out_folder(self):
        small = self.folder / "small"
        status, _ = shrink_file(self.png, _args(width=2, out=str(small)))
        self.assertEqual(status, "resized")
        self.assertTrue((small / "photo-small.png").exists())
        self.assertFalse((self.folder / "photo-small.png").exists())


class TestCollect(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        (self.folder / "a.png").write_bytes(b"x")
        (self.folder / "b.jpg").write_bytes(b"x")
        (self.folder / "c.txt").write_text("x")
        sub = self.folder / "sub"
        sub.mkdir()
        (sub / "d.png").write_bytes(b"x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_single_file(self):
        self.assertEqual(collect([str(self.folder / "a.png")], False),
                         [self.folder / "a.png"])

    def test_folder_non_recursive(self):
        found = collect([str(self.folder)], False)
        self.assertEqual(sorted(p.name for p in found), ["a.png", "b.jpg"])

    def test_folder_recursive_finds_subfolder(self):
        found = collect([str(self.folder)], True)
        self.assertEqual(sorted(p.name for p in found),
                         ["a.png", "b.jpg", "d.png"])

    def test_missing_path_is_ignored(self):
        self.assertEqual(collect([str(self.folder / "nope.png")], False), [])


class TestImgshrinkDriver(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_folder_returns_zero(self):
        self.assertEqual(imgshrink([str(self.folder)], _args(width=100)), 0)

    def test_mixed_folder_counts(self):
        rows = [[(1, 2, 3), (4, 5, 6)], [(7, 8, 9), (10, 11, 12)]]
        (self.folder / "ok.png").write_bytes(encode_png(rows, False))
        (self.folder / "snap.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 8)
        self.assertEqual(imgshrink([str(self.folder)], _args(width=1)), 0)
        self.assertTrue((self.folder / "ok-small.png").exists())

    def test_error_returns_one(self):
        bad = self.folder / "broken.png"
        bad.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbagegarbage")
        self.assertEqual(imgshrink([str(self.folder)], _args(width=100)), 1)


if __name__ == "__main__":
    unittest.main()
