"""Standard (non-AI) engine: pemilihan filter resize + geometri output.

Enhancement konservatif (noise/detail/sharpen) serta color management dan
ekspor diterapkan oleh core.image_pipeline agar konsisten untuk
Standard dan AI Engine (spec §5).
"""
from PIL import Image

from core.image_ops import apply_geometry, target_dimensions, DEFAULT_CANVAS_FILL


def standard_resample(settings):
    method = settings.get("standard_filter", "Lanczos")
    return Image.Resampling.LANCZOS if method == "Lanczos" else Image.Resampling.BICUBIC


def standard_method_label(settings):
    return "Standard Lanczos" if standard_resample(settings) == Image.Resampling.LANCZOS else "Standard Bicubic"


def process_standard(image, settings):
    """Resize sumber ke dimensi/geometri target memakai filter standar."""
    return apply_geometry(
        image,
        target_dimensions(settings),
        settings.get("resize_mode", "Exact Canvas"),
        settings.get("background", "#FFFFFF"),
        standard_resample(settings),
        settings.get("canvas_fill", DEFAULT_CANVAS_FILL),
    )
