"""Penulis file PSD (Photoshop) minimal untuk output RGB 8-bit.

Pillow hanya dapat *membaca* PSD, bukan menulisnya, sehingga modul ini menulis
struktur file PSD secara langsung:

  File Header -> Color Mode Data -> Image Resources (ICC + Resolution) ->
  Layer & Mask (kosong) -> Image Data (RLE / raw)

Profil ICC (resource id 1039) dan DPI (resource id 1005) disematkan agar
Photoshop mengenali ruang warna sRGB IEC61966-2.1 dan resolusi 300 PPI.
"""
import struct
from pathlib import Path

try:
    import numpy as np
except Exception:  # numpy bersifat opsional; tanpa itu dipakai kompresi raw.
    np = None

_HEADER_SIG = b"8BPS"


def _packbits_row(row):
    """Encode satu baris piksel (bytes/bytearray) dengan PackBits (RLE PSD)."""
    n = len(row)
    if n == 0:
        return b""
    if n == 1:
        return bytes((0, row[0]))
    out = bytearray()
    if np is not None:
        arr = np.frombuffer(bytes(row), dtype=np.uint8)
        change = np.flatnonzero(arr[1:] != arr[:-1]) + 1
        starts = np.concatenate(([0], change))
        ends = np.concatenate((change, [n]))
        lengths = ends - starts
        is_lit = lengths == 1

        padded = np.concatenate(([False], is_lit, [False]))
        trans = np.diff(padded.astype(np.int8))
        gs = np.flatnonzero(trans == 1)
        ge = np.flatnonzero(trans == -1)
        rep_runs = np.flatnonzero(~is_lit)

        li = 0
        ri = 0
        n_lit = len(gs)
        n_rep = len(rep_runs)
        while li < n_lit or ri < n_rep:
            if ri >= n_rep or (li < n_lit and gs[li] < rep_runs[ri]):
                a = int(starts[gs[li]])
                b = int(ends[ge[li] - 1])
                pos = a
                while pos < b:
                    chunk = 128 if (b - pos) > 128 else (b - pos)
                    out.append(chunk - 1)
                    out += bytes(row[pos:pos + chunk])
                    pos += chunk
                li += 1
            else:
                k = int(rep_runs[ri])
                value = int(row[int(starts[k])])
                remaining = int(lengths[k])
                while remaining > 0:
                    chunk = 128 if remaining > 128 else remaining
                    if chunk == 1:
                        out.append(0)
                        out.append(value)
                    else:
                        out.append(257 - chunk)
                        out.append(value)
                    remaining -= chunk
                ri += 1
        return bytes(out)

    # Fallback tanpa numpy: PackBits sederhana (aman, sedikit lebih lambat).
    i = 0
    while i < n:
        run = 1
        while i + run < n and run < 128 and row[i + run] == row[i]:
            run += 1
        if run >= 2:
            out.append(257 - run)
            out.append(row[i])
            i += run
        else:
            j = i
            while j < n and (j - i) < 128 and (j + 1 >= n or row[j + 1] != row[j]):
                j += 1
            out.append(j - i - 1)
            out += bytes(row[i:j])
            i = j
    return bytes(out)


def _resource(block_id, data, name=b""):
    """Bangun satu image resource block PSD ('8BIM' + id + nama + data)."""
    pascal = bytes((len(name),)) + name
    if len(pascal) % 2:
        pascal += b"\x00"
    payload = data + (b"\x00" if len(data) % 2 else b"")
    return (
        b"8BIM"
        + struct.pack(">H", block_id)
        + pascal
        + struct.pack(">I", len(data))
        + payload
    )


def _resolution_resource(dpi):
    fixed = int(round(float(dpi) * 65536)) & 0xFFFFFFFF
    return _resource(1005, struct.pack(">IHHIHH", fixed, 1, 1, fixed, 1, 1))


def _build_image_resources(dpi, icc_profile):
    blocks = b""
    if icc_profile:
        blocks += _resource(1039, icc_profile, b"ICC Profile")
    if dpi:
        blocks += _resolution_resource(dpi)
    return struct.pack(">I", len(blocks)) + blocks


def _encode_rle(bands, width, height):
    """Encode data gambar planar 3 kanal dengan RLE (return None bila gagal)."""
    try:
        counts = []
        parts = []
        for band in bands:
            data = band.tobytes()
            for y in range(height):
                row = data[y * width:(y + 1) * width]
                enc = _packbits_row(row)
                counts.append(len(enc))
                parts.append(enc)
        table = struct.pack(f">{len(counts)}H", *counts)
        return table + b"".join(parts)
    except Exception:
        return None


def save_psd(image, path, dpi=300, icc_profile=None):
    """Simpan gambar (RGB 8-bit) sebagai PSD dengan ICC profile dan DPI."""
    img = image.convert("RGB")
    width, height = img.size
    bands = list(img.split())

    rle = _encode_rle(bands, width, height)
    if rle is not None:
        image_data = struct.pack(">H", 1) + rle  # compression = RLE
    else:
        raw = b"".join(band.tobytes() for band in bands)
        image_data = struct.pack(">H", 0) + raw  # compression = raw

    header = (
        _HEADER_SIG
        + struct.pack(">H", 1)          # version
        + b"\x00" * 6                    # reserved
        + struct.pack(">H", 3)           # channels (RGB)
        + struct.pack(">I", height)
        + struct.pack(">I", width)
        + struct.pack(">H", 8)           # bits per channel
        + struct.pack(">H", 3)           # color mode = RGB
    )
    color_mode_data = struct.pack(">I", 0)
    resources = _build_image_resources(dpi, icc_profile)
    layer_mask = struct.pack(">I", 0)

    path = Path(path)
    path.write_bytes(header + color_mode_data + resources + layer_mask + image_data)
    return path
