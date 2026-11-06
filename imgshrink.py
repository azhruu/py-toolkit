#!/usr/bin/env python3
"""imgshrink.py — batch-resize images without installing anything.

Usage:
    python imgshrink.py photo.png --width 800
    python imgshrink.py ~/Photos --max 1200 --out ~/Photos/small --recursive
    python imgshrink.py a.png b.bmp --scale 0.5 --dry-run
    python imgshrink.py photo.png --width 800 --in-place

Pure standard library — no Pillow, no pip install. The resize itself is
real (nearest-neighbour resampling), but the formats it can read are
limited by what the stdlib can decode:

    PNG  — resized (8/16-bit, grey / RGB / palette / with alpha, non-interlaced)
    BMP  — resized (24/32-bit uncompressed)
    JPEG, GIF, WebP, ... — dimensions are reported, but the file is skipped:
           decoding those needs Pillow (`pip install pillow`).

By default a resized copy is written next to the original with a suffix
(`photo-small.png`); `--in-place` overwrites the original instead.
Nothing is ever overwritten by accident — clashing names get a numeric
suffix, like organize.py. Aspect ratio is always kept.
"""
import argparse
import binascii
import struct
import sys
import zlib
from pathlib import Path

SUFFIX = "-small"
IMAGE_EXTS = {".png", ".bmp", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff"}

# PNG colour types: channels per pixel.
PNG_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def human_size(size: int) -> str:
    """Format a byte count, e.g. 1536 -> '1.5 KB', 500 -> '500 B'."""
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"  # pragma: no cover


def target_size(width: int, height: int, args) -> tuple:
    """Target (width, height) from the sizing flags, or None to skip.

    --width/--height/--max only shrink: an image already at or below the
    requested size is left alone. --scale resizes by the given factor
    (up or down) and is the only flag that can enlarge.
    """
    if args.scale is not None:
        w = max(1, round(width * args.scale))
        h = max(1, round(height * args.scale))
        return (w, h) if (w, h) != (width, height) else None
    if args.width is not None:
        if width <= args.width:
            return None
        return (args.width, max(1, round(height * args.width / width)))
    if args.height is not None:
        if height <= args.height:
            return None
        return (max(1, round(width * args.height / height)), args.height)
    factor = min(args.max / width, args.max / height)
    if factor >= 1:
        return None
    return (max(1, round(width * factor)), max(1, round(height * factor)))


def resize_pixels(rows, new_w: int, new_h: int):
    """Nearest-neighbour resample of rows (lists of pixel tuples)."""
    old_h = len(rows)
    old_w = len(rows[0])
    out = []
    for y in range(new_h):
        src_row = rows[min(old_h - 1, y * old_h // new_h)]
        out.append([src_row[min(old_w - 1, x * old_w // new_w)]
                    for x in range(new_w)])
    return out


# ---------------------------------------------------------------- PNG

def png_chunk(kind: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(kind)
    crc = binascii.crc32(data, crc)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc & 0xFFFFFFFF)


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data: bytes):
    """Return (rows, has_alpha) for a PNG, or raise ValueError.

    rows are lists of (r, g, b) or (r, g, b, a) tuples. Only 8/16-bit,
    non-interlaced PNGs are supported; 16-bit samples keep their high
    byte, palette images are expanded through PLTE.
    """
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    pos, idat, palette = 8, bytearray(), None
    width = height = depth = colour = interlace = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"PLTE":
            palette = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif kind == b"IDAT":
            idat.extend(chunk)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if width is None:
        raise ValueError("missing IHDR chunk")
    if interlace:
        raise ValueError("interlaced PNGs are not supported")
    if depth not in (8, 16):
        raise ValueError(f"bit depth {depth} is not supported (need 8 or 16)")
    if colour not in PNG_CHANNELS:
        raise ValueError(f"colour type {colour} is not supported")
    if colour == 3 and palette is None:
        raise ValueError("palette image without a PLTE chunk")
    channels = PNG_CHANNELS[colour]
    sample = 2 if depth == 16 else 1
    stride = width * channels * sample
    raw = zlib.decompress(bytes(idat))
    if len(raw) < (stride + 1) * height:
        raise ValueError("truncated image data")
    rows, prev = [], bytearray(stride)
    for y in range(height):
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        kind = raw[y * (stride + 1)]
        bpp = channels * sample
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + a) & 0xFF
            elif kind == 2:
                line[i] = (line[i] + b) & 0xFF
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif kind == 4:
                line[i] = (line[i] + paeth(a, b, c)) & 0xFF
            elif kind != 0:
                raise ValueError(f"unknown PNG filter {kind}")
        prev = line
        row = []
        for x in range(width):
            vals = [line[(x * channels + ch) * sample] for ch in range(channels)]
            if colour == 0:
                row.append((vals[0], vals[0], vals[0]))
            elif colour == 2:
                row.append(tuple(vals))
            elif colour == 3:
                row.append(palette[vals[0]] if vals[0] < len(palette) else (0, 0, 0))
            elif colour == 4:
                row.append((vals[0], vals[0], vals[0], vals[1]))
            else:
                row.append(tuple(vals))
        rows.append(row)
    return rows, colour in (4, 6)


def encode_png(rows, has_alpha: bool) -> bytes:
    """Encode rows of (r, g, b[, a]) tuples as a PNG (filter 0 rows)."""
    height = len(rows)
    width = len(rows[0])
    colour = 6 if has_alpha else 2
    channels = 4 if has_alpha else 3
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for px in row:
            raw.extend(px[:channels])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))


# ---------------------------------------------------------------- BMP

def decode_bmp(data: bytes):
    """Return (rows, bits) for a BMP, or raise ValueError.

    Only uncompressed (BI_RGB) 24/32-bit BMPs; rows are (r, g, b) or
    (r, g, b, a) tuples, bottom-up or top-down.
    """
    if data[:2] != b"BM" or len(data) < 54:
        raise ValueError("not a BMP file")
    (offset,) = struct.unpack("<I", data[10:14])
    (dib,) = struct.unpack("<I", data[14:18])
    if dib < 40:
        raise ValueError("unsupported BMP header (need BITMAPINFOHEADER)")
    width, height, planes, bits, compression = struct.unpack("<iiHHI", data[18:34])
    if planes != 1 or bits not in (24, 32) or compression != 0:
        raise ValueError(f"unsupported BMP: {bits}-bit, compression {compression}")
    top_down = height < 0
    height = abs(height)
    bytes_per_px = bits // 8
    row_bytes = ((width * bits + 31) // 32) * 4
    rows = []
    for y in range(height):
        src_y = y if top_down else height - 1 - y
        base = offset + src_y * row_bytes
        row = []
        for x in range(width):
            b, g, r = data[base + x * bytes_per_px:base + x * bytes_per_px + 3]
            px = (r, g, b)
            if bits == 32:
                px += (data[base + x * 4 + 3],)
            row.append(px)
        rows.append(row)
    return rows, bits


def encode_bmp(rows, bits: int) -> bytes:
    """Encode rows as an uncompressed BMP (bottom-up, same bit depth)."""
    height = len(rows)
    width = len(rows[0])
    bytes_per_px = bits // 8
    row_bytes = ((width * bits + 31) // 32) * 4
    offset = 14 + 40
    pixel_data = bytearray()
    for row in reversed(rows):
        line = bytearray()
        for px in row:
            r, g, b = px[:3]
            line.extend((b, g, r))
            if bits == 32:
                line.append(px[3] if len(px) > 3 else 255)
        line.extend(b"\x00" * (row_bytes - len(line)))
        pixel_data.extend(line)
    header = struct.pack("<2sIHHI", b"BM", offset + len(pixel_data), 0, 0, offset)
    dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, bits, 0,
                      len(pixel_data), 2835, 2835, 0, 0)
    return header + dib + bytes(pixel_data)


# ------------------------------------------------------------- driver

def detect_format(path: Path) -> str:
    """Image format from magic bytes ('png', 'bmp', 'jpeg', 'gif', 'webp',
    'other'), so a misnamed file is still handled by its real contents."""
    with open(path, "rb") as fh:
        head = fh.read(12)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[:2] == b"BM":
        return "bmp"
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return "other"


UNSUPPORTED_NOTE = "needs Pillow to decode (pip install pillow)"


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


def shrink_file(path: Path, args) -> tuple:
    """Resize one file. Returns (status, message): status is
    'resized', 'skipped' or 'error'."""
    fmt = detect_format(path)
    if fmt in ("jpeg", "gif", "webp"):
        return "skipped", f"{path.name}: {fmt.upper()} {UNSUPPORTED_NOTE}"
    if fmt not in ("png", "bmp"):
        return "skipped", f"{path.name}: not a supported image"
    try:
        data = path.read_bytes()
        if fmt == "png":
            rows, has_alpha = decode_png(data)
        else:
            rows, bits = decode_bmp(data)
            has_alpha = bits == 32
    except (ValueError, zlib.error, struct.error, OSError) as exc:
        return "error", f"{path.name}: cannot read ({exc})"
    old_w, old_h = len(rows[0]), len(rows)
    target = target_size(old_w, old_h, args)
    if target is None:
        return "skipped", (f"{path.name}: already {old_w}x{old_h}, "
                            "no shrinking needed")
    new_w, new_h = target
    resized = resize_pixels(rows, new_w, new_h)
    if fmt == "png":
        out_bytes = encode_png(resized, has_alpha)
    else:
        out_bytes = encode_bmp(resized, bits)
    if args.in_place:
        dest = path
    else:
        out_dir = Path(args.out) if args.out else path.parent
        dest = out_dir / (path.stem + args.suffix + path.suffix)
        if not args.force:
            dest = unique_dest(dest)
    if args.dry_run:
        return "resized", (f"would resize: {path.name} "
                            f"{old_w}x{old_h} -> {new_w}x{new_h}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(out_bytes)
    except OSError as exc:
        return "error", f"{path.name}: cannot write {dest} ({exc})"
    before, after = path.stat().st_size, len(out_bytes)
    where = "in place" if args.in_place else f"-> {dest.name}"
    return "resized", (f"{path.name} {old_w}x{old_h} -> {new_w}x{new_h} "
                       f"({human_size(before)} -> {human_size(after)}) {where}")


def collect(paths, recursive: bool):
    files = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            glob = path.rglob("*") if recursive else path.iterdir()
            files.extend(sorted(p for p in glob
                                if p.is_file() and p.suffix.lower() in IMAGE_EXTS))
        else:
            print(f"error: {path} is not a file or folder", file=sys.stderr)
    return files


def imgshrink(paths, args) -> int:
    files = collect(paths, args.recursive)
    if not files:
        print("No image files found.")
        return 0
    counts = {"resized": 0, "skipped": 0, "error": 0}
    for path in files:
        status, message = shrink_file(path, args)
        counts[status] += 1
        print(message)
    verb = "Would resize" if args.dry_run else "Resized"
    print(f"\n{verb} {counts['resized']} file(s), "
          f"skipped {counts['skipped']}, {counts['error']} error(s).")
    return 1 if counts["error"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch-resize images with the standard library only "
                    "(PNG and BMP; JPEG/GIF/WebP need Pillow).")
    parser.add_argument("paths", nargs="+",
                        help="image file(s) and/or folder(s) to resize")
    size = parser.add_mutually_exclusive_group(required=True)
    size.add_argument("--width", type=int, metavar="N",
                      help="fit to this width, keep aspect ratio")
    size.add_argument("--height", type=int, metavar="N",
                      help="fit to this height, keep aspect ratio")
    size.add_argument("--max", type=int, metavar="N",
                      help="fit inside an NxN box, keep aspect ratio")
    size.add_argument("--scale", type=float, metavar="F",
                      help="resize by this factor, e.g. 0.5")
    parser.add_argument("--out", help="folder for resized copies "
                        "(default: next to the original)")
    parser.add_argument("--suffix", default=SUFFIX,
                        help=f"added to resized copies (default: {SUFFIX})")
    parser.add_argument("--in-place", action="store_true",
                        help="overwrite the originals instead of copying")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing resized copy")
    parser.add_argument("--recursive", action="store_true",
                        help="recurse into subfolders")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview only, write nothing")
    args = parser.parse_args()
    for name in ("width", "height", "max"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name} must be at least 1")
    if args.scale is not None and args.scale <= 0:
        parser.error("--scale must be greater than 0")
    if args.in_place and args.out:
        parser.error("--in-place cannot be combined with --out")
    return imgshrink(args.paths, args)


if __name__ == "__main__":
    raise SystemExit(main())
