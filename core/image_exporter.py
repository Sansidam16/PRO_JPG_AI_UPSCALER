"""Export JPEG/PSD berkualitas tinggi dan validasi hasil akhir."""
import io
from pathlib import Path
from PIL import Image, ImageCms

from core.color_manager import srgb_icc_bytes
from core.psd_writer import save_psd

# 0 = 4:4:4, 1 = 4:2:2, 2 = 4:2:0 (Pillow subsampling)
_SUBSAMPLING = {"4:4:4": 0, "4:2:2": 1, "4:2:0": 2}


def export_jpeg(image, path, quality=98, dpi=300, subsampling="4:4:4", embed_srgb=True):
    """Simpan gambar sebagai JPEG dengan kualitas dan chroma subsampling eksplisit."""
    path = Path(path)
    kwargs = dict(
        format="JPEG",
        quality=max(1, min(100, int(quality))),
        subsampling=_SUBSAMPLING.get(str(subsampling), 0),
        dpi=(int(dpi), int(dpi)),
        optimize=True,
        progressive=True,
    )
    if embed_srgb:
        icc = srgb_icc_bytes()
        if icc:
            kwargs["icc_profile"] = icc
    image.convert("RGB").save(path, **kwargs)
    return path


def export_psd(image, path, dpi=300, embed_srgb=True):
    """Simpan gambar sebagai PSD (RGB 8-bit) dengan profil sRGB disematkan."""
    icc = srgb_icc_bytes() if embed_srgb else None
    return save_psd(image, path, dpi=dpi, icc_profile=icc)


def _icc_description(img, report):
    icc = img.info.get("icc_profile")
    if not icc:
        report["icc"] = "-"
        return
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        report["icc"] = ImageCms.getProfileDescription(profile).strip()
    except Exception:
        report["icc"] = "unknown"


def _base_report(img, path):
    dpi = img.info.get("dpi")
    report = {
        "file": path.name,
        "readable": True,
        "format": img.format,
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "dpi": f"{int(dpi[0])}x{int(dpi[1])}" if dpi else "-",
        "has_icc": "icc_profile" in img.info,
        "bytes": path.stat().st_size,
    }
    _icc_description(img, report)
    return report


def validate_jpeg(path, expected_size=None):
    """
    Baca ulang file hasil dan validasi.

    Mengembalikan (report, ok). ok False bila file tidak terbaca, bukan JPEG,
    bukan RGB, atau dimensi tidak sesuai expected_size.
    """
    path = Path(path)
    report = {"file": path.name, "readable": False}
    try:
        with Image.open(path) as img:
            report.update(_base_report(img, path))
    except Exception as exc:
        report["error"] = str(exc)
        return report, False

    ok = report.get("format") == "JPEG" and report.get("mode") == "RGB"
    if expected_size:
        ok = ok and (report["width"], report["height"]) == tuple(expected_size)
    report["ok"] = ok
    return report, ok


def validate_psd(path, expected_size=None):
    """Baca ulang file PSD hasil dan validasi struktur dasar + ICC."""
    path = Path(path)
    report = {"file": path.name, "readable": False}
    try:
        with Image.open(path) as img:
            report.update(_base_report(img, path))
    except Exception as exc:
        report["error"] = str(exc)
        return report, False

    ok = report.get("format") == "PSD" and report.get("mode") == "RGB"
    if expected_size:
        ok = ok and (report["width"], report["height"]) == tuple(expected_size)
    report["ok"] = ok
    return report, ok
