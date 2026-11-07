"""Enhancement konservatif: noise reduction, detail, dan sharpening.

Sharpening bersifat edge-aware: hanya tepi nyata (garis geometris, ornamen
logam, bintang/snowflake) yang dipertajam, sementara area datar (gradasi halus,
background gelap, bokeh, bayangan lembut) dilindungi oleh edge mask +
protection mask (anti-halo). Detail digabung menjadi satu pass agar tidak
menumpuk.

Radius sharpening dinyatakan relatif terhadap RESOLUSI REFERENSI 2048 px lalu
diskalakan ke dimensi output, sehingga kekuatan sharpening konsisten pada
preview maupun pada output 4961 px (tidak oversharpening di resolusi besar dan
tidak hilang di resolusi kecil).
"""
from PIL import Image, ImageFilter

# level detail -> (radius, percent, threshold)
_DETAIL = {
    "Off": None,
    "Low": (1.0, 40, 3),
    "Medium": (1.2, 70, 2),
    "High": (1.4, 110, 2),
}

# Radius referensi: nilai radius di UI berlaku pada sisi terpanjang 2048 px.
REFERENCE_LONG_SIDE = 2048.0
_MIN_RADIUS = 0.3
_MAX_RADIUS = 3.0


def effective_radius(base_radius, image_size=None):
    """Skalakan radius dari resolusi referensi 2048 px ke dimensi output."""
    base = float(base_radius) if base_radius else 1.0
    if not image_size:
        return max(_MIN_RADIUS, min(_MAX_RADIUS, base))
    long_side = float(max(image_size))
    if long_side <= 0:
        return max(_MIN_RADIUS, min(_MAX_RADIUS, base))
    return max(_MIN_RADIUS, min(_MAX_RADIUS, base * (long_side / REFERENCE_LONG_SIDE)))


# level noise reduction -> spec
_NOISE = {
    "Off": None,
    "Low": ("median", 3),
    "Medium": ("median+blur", 3, 0.4),
    "High": ("median+blur", 5, 0.6),
}


def reduce_noise(image, level):
    """Noise reduction diterapkan pada sumber sebelum upscaling."""
    spec = _NOISE.get(level)
    if not spec:
        return image
    if spec[0] == "median":
        return image.filter(ImageFilter.MedianFilter(size=spec[1]))
    _, size, sigma = spec
    out = image.filter(ImageFilter.MedianFilter(size=size))
    return out.filter(ImageFilter.GaussianBlur(radius=sigma))


def _edge_aware_sharpen(image, radius, percent, threshold, protect_gradients):
    """
    Unsharp mask ter-mask oleh kekuatan tepi (edge-aware).

    Hanya piksel pada tepi kuat yang diperkuat; area low-texture (gradasi,
    bokeh, bayangan lembut, background gelap) hampir tidak tersentuh sehingga
    halo dan banding sangat minim.
    """
    import numpy as np

    rgb = image.convert("RGB")
    arr = np.asarray(rgb).astype(np.float32)
    blur = np.asarray(rgb.filter(ImageFilter.GaussianBlur(radius=radius))).astype(np.float32)
    detail = arr - blur

    # Kekuatan tepi dari gradien luminance.
    lum = arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gy, gx = np.gradient(lum)
    mag = np.hypot(gx, gy)
    del gx, gy, lum
    mag_img = Image.fromarray(np.clip(mag, 0, 255).astype(np.uint8), "L")
    del mag
    mag_s = np.asarray(mag_img.filter(ImageFilter.GaussianBlur(radius=1.0))).astype(np.float32)

    hi = float(np.percentile(mag_s, 99.0))
    if hi <= 1e-6:
        return image
    edge = np.clip(mag_s / hi, 0.0, 1.0)
    del mag_s

    # Protection mask: buang tepi lemah (gradasi/bokeh/bayangan tetap aman).
    lo = 0.15 if protect_gradients else 0.05
    edge = np.clip((edge - lo) / (1.0 - lo), 0.0, 1.0)
    edge *= edge  # perkuat hanya tepi yang benar-benar kuat

    gain = edge * (percent / 100.0)
    del edge

    if threshold > 0:
        gain *= (np.abs(detail) >= float(threshold)).any(axis=2)

    out = arr + gain[..., None] * detail
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGB")


def sharpen(image, detail_level, amount, radius, threshold, protect_gradients=True,
            output_size=None):
    """
    Satu pass sharpening gabungan dari Detail Enhancement + Sharpening.

    Menggunakan edge-aware masking (lihat _edge_aware_sharpen) dengan anti-halo
    (edge mask + protection mask). Radius diskalakan ke dimensi output agar
    konsisten pada semua resolusi (lihat effective_radius).
    - protect_gradients (Gradient Preservation): menjaga threshold minimal 3 agar
      gradasi halus tidak ikut dipertajam.
    - Tidak melakukan apa pun bila total kekuatan 0 (default Off).
    """
    detail = _DETAIL.get(detail_level)
    percent = 0
    r_base = float(radius) if radius else 1.0
    t = int(threshold) if threshold is not None else 3

    if detail:
        r_base = max(r_base, detail[0])
        percent += detail[1]

    amt = float(amount or 0)
    if amt > 0:
        percent += int(amt)

    if percent <= 0:
        return image

    percent = min(300, percent)
    if protect_gradients:
        t = max(t, 3)

    r = effective_radius(r_base, output_size or image.size)

    try:
        return _edge_aware_sharpen(image, r, percent, t, protect_gradients)
    except Exception:
        return image.filter(ImageFilter.UnsharpMask(radius=r, percent=percent,
                                                    threshold=max(1, t)))
