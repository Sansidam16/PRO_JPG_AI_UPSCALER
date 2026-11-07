"""Preset dimensi, perhitungan skala, dan geometri output.

Catatan: konversi warna dan ekspor JPEG kini ditangani oleh core.color_manager
dan core.image_exporter (spec §7 & §9).
"""
from PIL import Image

PRESETS = {
    "1920 x 600": (1920, 600),
    "1920 x 700": (1920, 700),
    "1920 x 900": (1920, 900),
    "3543 x 4961": (3543, 4961),
    "4961 x 3543": (4961, 3543),
}

# Mode geometri yang didukung (spec §8 & §11).
RESIZE_MODES = ["Exact Canvas", "Preserve Aspect Ratio", "Fit", "Crop", "Stretch"]

# Cara mengisi sisa kanvas bila rasio sumber != rasio target.
CANVAS_FILL_MODES = ["Edge Extension", "Background Color"]
DEFAULT_CANVAS_FILL = "Edge Extension"


def target_dimensions(settings):
    preset = settings.get("preset", "4961 x 3543")
    if preset == "Custom" or preset not in PRESETS:
        w = max(1, int(settings.get("custom_width", 4961)))
        h = max(1, int(settings.get("custom_height", 3543)))
        return w, h
    return PRESETS[preset]


def required_scale(src_size, target_size, mode):
    sw, sh = src_size
    tw, th = target_size
    if mode in ("Crop", "Stretch"):
        return max(tw / sw, th / sh)
    # Exact Canvas / Fit / Preserve Aspect Ratio: skala agar seluruh gambar masuk.
    return min(tw / sw, th / sh)


def prepare_source_for_ai(image, target_size, mode):
    """AI hanya diperlukan bila target lebih besar dari sumber (enlargement)."""
    return required_scale(image.size, target_size, mode) > 1.00001


def _parse_background(value):
    value = str(value).strip()
    if value.startswith("#") and len(value) == 7:
        try:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            pass
    return (255, 255, 255)


def _edge_extend(resized, size, offset):
    """Isi sisa kanvas dengan mereplikasi piksel tepi (edge extension)."""
    import numpy as np
    tw, th = size
    rw, rh = resized.size
    left, top = offset
    arr = np.asarray(resized.convert("RGB"))
    canvas = np.empty((th, tw, 3), dtype=arr.dtype)
    right = left + rw
    bottom = top + rh
    canvas[top:bottom, left:right] = arr
    if top > 0:
        canvas[:top, left:right] = arr[0:1, :]
    if bottom < th:
        canvas[bottom:, left:right] = arr[-1:, :]
    if left > 0:
        canvas[top:bottom, :left] = arr[:, 0:1]
        canvas[:top, :left] = arr[0, 0]
        canvas[bottom:, :left] = arr[-1, 0]
    if right < tw:
        canvas[top:bottom, right:] = arr[:, -1:]
        canvas[:top, right:] = arr[0, -1]
        canvas[bottom:, right:] = arr[-1, -1]
    return Image.fromarray(canvas, "RGB")


def apply_geometry(image, target_size, mode, background="#FFFFFF",
                   resample=Image.Resampling.LANCZOS, canvas_fill=DEFAULT_CANVAS_FILL):
    """
    Terapkan geometri output tanpa menggunakan thumbnail().

    - Exact Canvas / Fit : seluruh gambar dipertahankan, output tepat target,
                           sisa kanvas diisi dengan Edge Extension (default)
                           atau warna background bila canvas_fill="Background Color".
    - Preserve Aspect Ratio : seluruh gambar dipertahankan, tanpa padding/crop,
                           ukuran output mengikuti rasio asli.
    - Crop : isi penuh target lalu crop bagian tengah.
    - Stretch : paksa tepat ukuran target (mengubah rasio).
    """
    tw, th = target_size
    image = image.convert("RGB")

    if mode == "Stretch":
        return image.resize((tw, th), resample)

    if mode == "Preserve Aspect Ratio":
        scale = min(tw / image.width, th / image.height)
        nw = max(1, round(image.width * scale))
        nh = max(1, round(image.height * scale))
        return image.resize((nw, nh), resample)

    if mode == "Crop":
        scale = max(tw / image.width, th / image.height)
        nw = max(tw, round(image.width * scale))
        nh = max(th, round(image.height * scale))
        resized = image.resize((nw, nh), resample)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        return resized.crop((left, top, left + tw, top + th))

    # Exact Canvas / Fit (default)
    scale = min(tw / image.width, th / image.height)
    nw = min(tw, max(1, round(image.width * scale)))
    nh = min(th, max(1, round(image.height * scale)))
    resized = image.resize((nw, nh), resample)
    offset = ((tw - nw) // 2, (th - nh) // 2)
    if str(canvas_fill) != "Background Color":
        return _edge_extend(resized, (tw, th), offset)
    canvas = Image.new("RGB", (tw, th), _parse_background(background))
    canvas.paste(resized, offset)
    return canvas
