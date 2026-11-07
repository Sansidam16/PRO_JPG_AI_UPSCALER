"""Analisis metadata gambar sumber (EXIF, ICC, dimensi)."""
from PIL import Image, ImageOps


def load_source(path):
    """
    Buka gambar sumber, terapkan orientasi EXIF, kembalikan (image, info).

    info berisi metadata dasar sebelum transpos EXIF. ICC profile disalin ulang
    ke image.info karena ImageOps.exif_transpose dapat menghilangkannya,
    sehingga color management (spec §7) tetap berjalan.
    """
    with Image.open(path) as opened:
        icc = opened.info.get("icc_profile")
        info = {
            "width": opened.width,
            "height": opened.height,
            "format": opened.format,
            "mode": opened.mode,
            "has_icc": icc is not None,
        }
        image = ImageOps.exif_transpose(opened)
        image.load()
    if icc:
        image.info["icc_profile"] = icc
    return image, info


def analyze(image, info=None):
    """Ringkasan karakteristik gambar (setelah transpos EXIF)."""
    info = info or {}
    width, height = image.size
    return {
        "width": width,
        "height": height,
        "aspect": (width / height) if height else 0.0,
        "mode": image.mode,
        "has_icc": info.get("has_icc", "icc_profile" in image.info),
    }
