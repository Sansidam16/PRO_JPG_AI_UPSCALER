"""Color management: konversi ke ruang kerja sRGB dan penyediaan profil output.

Profil output adalah sRGB standar dengan deskripsi persis "sRGB IEC61966-2.1"
(file ICC dibundel di folder `assets`, disalin dari profil sistem Windows).
Bila file tersebut tidak tersedia, aplikasi membuat profil sRGB bawaan Pillow
sebagai cadangan.
"""
import io
from pathlib import Path

from PIL import Image, ImageCms

from app.settings import ASSETS_DIR

PROFILE_NAME = "sRGB IEC61966-2.1"
_ICC_PATH = Path(ASSETS_DIR) / "sRGB_IEC61966-2.1.icc"


def _profile_file_bytes():
    try:
        if _ICC_PATH.exists():
            data = _ICC_PATH.read_bytes()
            if data:
                return data
    except Exception:
        pass
    return None


_PROFILE_BYTES = _profile_file_bytes()

if _PROFILE_BYTES:
    _SRGB_PROFILE = ImageCms.ImageCmsProfile(io.BytesIO(_PROFILE_BYTES))
else:
    _SRGB_PROFILE = ImageCms.createProfile("sRGB")
    _PROFILE_BYTES = ImageCms.ImageCmsProfile(_SRGB_PROFILE).tobytes()


def profile_description():
    """Deskripsi profil sRGB yang akan disematkan ke file output."""
    try:
        return ImageCms.getProfileDescription(_SRGB_PROFILE).strip()
    except Exception:
        return PROFILE_NAME


def to_srgb(image):
    """
    Konversi gambar ke ruang kerja sRGB.

    Mengembalikan tuple (image_rgb, converted):
    - converted True bila gambar sumber memiliki ICC profile dan berhasil dikonversi.
    - converted False bila sumber tanpa ICC (dianggap sudah sRGB) atau konversi gagal.

    Nilai piksel tidak diubah bila tidak ada profil, sehingga brightness/contrast
    tidak bergeser tanpa alasan teknis.
    """
    rgb = image.convert("RGB")
    icc = image.info.get("icc_profile")
    if not icc:
        return rgb, False
    try:
        src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        result = ImageCms.profileToProfile(
            rgb,
            src_profile,
            _SRGB_PROFILE,
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
            outputMode="RGB",
        )
        return result.convert("RGB"), True
    except Exception:
        # Profil tidak terbaca / konversi gagal: pertahankan piksel apa adanya.
        return rgb, False


def srgb_icc_bytes():
    """Byte ICC profile sRGB (IEC61966-2.1) untuk disematkan pada file output."""
    return _PROFILE_BYTES
