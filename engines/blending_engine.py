"""AI strength blending.

Final = (1 - alpha) * Lanczos baseline + alpha * AI result

Blending dilakukan pada ruang warna yang sama (sRGB) tanpa konversi gamma
tambahan, sehingga brightness/contrast/color balance tidak bergeser.
"""
from PIL import Image


def _match_geometry(ai_image, base_image):
    if ai_image.size != base_image.size:
        ai_image = ai_image.resize(base_image.size, Image.Resampling.LANCZOS)
    return ai_image.convert("RGB")


def blend(base_image, ai_image, alpha):
    """Gabungkan baseline Lanczos dengan hasil AI sesuai kekuatan AI (0..1)."""
    alpha = max(0.0, min(1.0, float(alpha)))
    if alpha <= 0.0:
        return base_image.convert("RGB")
    ai_image = _match_geometry(ai_image, base_image)
    baseline = base_image.convert("RGB")
    if alpha >= 1.0:
        return ai_image
    return Image.blend(baseline, ai_image, alpha)
