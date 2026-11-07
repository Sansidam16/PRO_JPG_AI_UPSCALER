"""Orkestrasi pipeline pemrosesan gambar (spec §4 Conservative AI Super Resolution).

Alur:
  1  Load original image
  2  Read EXIF orientation
  3  Read embedded ICC profile
  4  Analyze original image dimensions
  5  Create Lanczos baseline upscale
  6  Execute Real-ESRGAN x4 inference
  7  Resize AI output ke target dimensions (Lanczos)
  8  Samakan ukuran/geometri kedua hasil
  9  AI strength blending
  10 Conservative detail enhancement
  11 Mild sharpening (opsional)
  12 Konversi ke sRGB
  13 Export JPG
  14 Validasi hasil akhir
"""
from pathlib import Path
import time

from PIL import Image

from core.image_analyzer import load_source, analyze
from core.color_manager import to_srgb
from core.image_exporter import export_jpeg, export_psd, validate_jpeg, validate_psd
from core.image_ops import target_dimensions, apply_geometry, required_scale, DEFAULT_CANVAS_FILL
from engines.blending_engine import blend
from engines.enhancement_engine import reduce_noise, sharpen
from engines.standard_engine import process_standard, standard_method_label


def output_stem(source_path, settings):
    """Nama dasar file output: sama dengan file asli atau ditambah suffix."""
    source_path = Path(source_path)
    if settings.get("output_naming", "suffix") == "original":
        return source_path.stem
    return f"{source_path.stem}{settings.get('output_suffix', '_PRO_UPSCALED')}"


def unique_output_stem(folder, stem, extensions=(".jpg", ".psd")):
    """Nama dasar unik agar file output (JPG/PSD) tidak menimpa file yang ada."""
    folder = Path(folder)
    candidate = stem
    index = 2
    while any((folder / f"{candidate}{ext}").exists() for ext in extensions):
        candidate = f"{stem}_{index}"
        index += 1
    return candidate


_EMPTY_MODEL = {
    "model_file": "-", "model_arch": "-", "model_blocks": "-",
    "model_scale": "-", "ckpt_valid": "-", "device": "-",
    "precision": "-", "tile": "-",
}


def process_image(path, output_dir, settings, ai_engine=None, log=None):
    """
    Proses satu gambar sesuai pipeline §4.

    Mengembalikan (report, out_path). report selalu memuat kunci 'ok'.
    """
    log = log or (lambda message: None)
    start = time.perf_counter()
    path = Path(path)

    # 1-4, 10(pre), 12(sebagian): load + EXIF + ICC + analisis + sRGB + noise.
    t0 = time.perf_counter()
    image, info = load_source(path)
    meta = analyze(image, info)
    log(f"  Sumber {meta['width']}x{meta['height']} | ICC: {'ya' if meta['has_icc'] else 'tidak'}")

    # 12 (sebagian): normalisasi ke ruang kerja sRGB agar blending konsisten.
    working, color_converted = to_srgb(image)

    # 10 (pre): noise reduction opsional pada sumber sebelum upscaling.
    noise_level = settings.get("noise_reduction", "Off")
    working = reduce_noise(working, noise_level)
    preprocess_time = time.perf_counter() - t0

    target = target_dimensions(settings)
    mode = settings.get("resize_mode", "Exact Canvas")
    background = settings.get("background", "#FFFFFF")
    canvas_fill = settings.get("canvas_fill", DEFAULT_CANVAS_FILL)

    # 5: baseline (Lanczos/Bicubic sesuai filter standar) beserta geometri target.
    resize_time = 0.0
    t0 = time.perf_counter()
    baseline = process_standard(working, settings)
    resize_time += time.perf_counter() - t0
    method = standard_method_label(settings)

    ai_result = None
    ai_intermediate = "-"
    ai_w = ai_h = "-"
    alpha = 0.0
    model_name = "-"
    model_info = dict(_EMPTY_MODEL)
    ai_time = 0.0
    blend_time = 0.0
    enhance_time = 0.0

    # 6-9: AI x4 + resize ke target + AI strength blending.
    if ai_engine is not None and required_scale(working.size, target, mode) > 1.00001:
        model_name = getattr(ai_engine, "arch_name", settings.get("model", "RealESRGAN_x4plus"))
        info_fn = getattr(ai_engine, "info", None)
        if callable(info_fn):
            try:
                model_info = info_fn()
            except Exception:
                model_info = dict(_EMPTY_MODEL)
        t0 = time.perf_counter()
        ai_image = ai_engine.enhance(working)  # output 4x
        ai_time += time.perf_counter() - t0
        ai_w, ai_h = ai_image.size
        ai_intermediate = f"{ai_w}x{ai_h}"
        # 7-8: samakan dimensi/geometri dengan baseline memakai Lanczos.
        t0 = time.perf_counter()
        ai_result = apply_geometry(ai_image, baseline.size, mode, background,
                                   Image.Resampling.LANCZOS, canvas_fill)
        resize_time += time.perf_counter() - t0
        alpha = max(0.0, min(100.0, float(settings.get("ai_strength", 30)))) / 100.0
        method = "AI + Lanczos + Blending"
        # Perbarui tile aktual (bila engine menurunkan tile karena OOM).
        model_info["tile"] = getattr(ai_engine, "active_tile", model_info.get("tile", "-"))
    elif ai_engine is not None:
        log("  Sumber sudah cukup besar; AI dilewati (resize standar).")

    t0 = time.perf_counter()
    if ai_result is not None:
        result = blend(baseline, ai_result, alpha)
    else:
        result = baseline
    blend_time = time.perf_counter() - t0

    # 10-11: conservative detail enhancement + selective edge sharpening (satu pass).
    t0 = time.perf_counter()
    result = sharpen(
        result,
        settings.get("detail_enhancement", "Low"),
        settings.get("sharpen_amount", 0),
        settings.get("sharpen_radius", 1.0),
        settings.get("sharpen_threshold", 3),
        protect_gradients=bool(settings.get("gradient_preservation", True)),
        output_size=result.size,
    )
    enhance_time = time.perf_counter() - t0

    # 13: export JPG (sRGB IEC61966-2.1, DPI, chroma subsampling) + opsi PSD.
    export_time = 0.0
    t0 = time.perf_counter()
    stem = unique_output_stem(output_dir, output_stem(path, settings))
    out_path = Path(output_dir) / f"{stem}.jpg"
    export_jpeg(
        result, out_path,
        quality=settings.get("jpeg_quality", 98),
        dpi=settings.get("dpi", 300),
        subsampling=settings.get("subsampling", "4:4:4"),
        embed_srgb=True,
    )

    psd_path = None
    if settings.get("save_psd", False):
        psd_path = Path(output_dir) / f"{stem}.psd"
        export_psd(result, psd_path, dpi=settings.get("dpi", 300), embed_srgb=True)
    export_time += time.perf_counter() - t0

    # 14: validasi hasil akhir (JPG, plus PSD bila dibuat).
    report, ok = validate_jpeg(out_path, expected_size=result.size)
    if psd_path is not None:
        psd_report, psd_ok = validate_psd(psd_path, expected_size=result.size)
        ok = ok and psd_ok
        report["psd"] = psd_report.get("file", psd_path.name)
    else:
        report["psd"] = "-"
    report.update({
        "source": path.name,
        "src_w": meta["width"],
        "src_h": meta["height"],
        "mode": mode,
        "canvas_fill": canvas_fill,
        "method": method,
        "model": model_name,
        "model_file": model_info.get("model_file", "-"),
        "model_arch": model_info.get("model_arch", "-"),
        "model_blocks": model_info.get("model_blocks", "-"),
        "model_scale": model_info.get("model_scale", "-"),
        "ckpt_valid": model_info.get("ckpt_valid", "-"),
        "device": model_info.get("device", "-"),
        "precision": model_info.get("precision", "-"),
        "tile": model_info.get("tile", "-"),
        "ai_intermediate": ai_intermediate,
        "ai_intermediate_w": ai_w,
        "ai_intermediate_h": ai_h,
        "ai_strength": f"{alpha * 100:.0f}%" if ai_result is not None else "-",
        "detail": settings.get("detail_enhancement", "Low"),
        "noise": noise_level,
        "sharpen_amount": settings.get("sharpen_amount", 0),
        "sharpen_radius": settings.get("sharpen_radius", 1.0),
        "sharpen_threshold": settings.get("sharpen_threshold", 3),
        "color_converted": color_converted,
        "preprocess_s": round(preprocess_time, 2),
        "ai_time_s": round(ai_time, 2),
        "resize_time_s": round(resize_time, 2),
        "blend_s": round(blend_time, 2),
        "enhance_s": round(enhance_time, 2),
        "export_time_s": round(export_time, 2),
        "time_s": round(time.perf_counter() - start, 2),
        "ok": ok,
    })
    return report, out_path
