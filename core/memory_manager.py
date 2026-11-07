"""Manajemen memori: bersihkan referensi Python dan cache VRAM antar gambar."""
import gc

from core.gpu_manager import empty_cache


def free_memory():
    """Panggil setelah setiap gambar untuk menjaga penggunaan RAM/VRAM tetap rendah."""
    gc.collect()
    empty_cache()
