"""Deteksi status GPU/CUDA tanpa memaksa impor PyTorch pada jalur Standard."""


def status():
    """
    Kembalikan dict status GPU:
    {"available": bool, "name": str, "reason": str}
    """
    try:
        import torch
    except Exception as exc:
        return {"available": False, "name": "-", "reason": f"PyTorch tidak terpasang ({exc})"}
    try:
        if not torch.cuda.is_available():
            return {"available": False, "name": "-", "reason": "CUDA tidak terdeteksi oleh PyTorch"}
        return {"available": True, "name": torch.cuda.get_device_name(0), "reason": ""}
    except Exception as exc:
        return {"available": False, "name": "-", "reason": f"Pemeriksaan CUDA gagal ({exc})"}


def empty_cache():
    """Bersihkan cache VRAM bila CUDA tersedia. Aman dipanggil kapan saja."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
