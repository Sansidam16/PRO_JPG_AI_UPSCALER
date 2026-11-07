"""Real-ESRGAN adapter.

Arsitektur model DIBACA dari isi file bobot (bukan dari nama file), lalu
divalidasi: bila struktur checkpoint tidak cocok dengan arsitektur yang
dibangun, proses dihentikan dengan pesan yang jelas. Ini mencegah model salah
diinisialisasi dan mencegah label model yang salah.

Metadata model (arsitektur, jumlah blok, skala, device, presisi) dikembalikan
agar dapat dicatat secara transparan pada laporan CSV.
"""
from pathlib import Path

from PIL import Image


class AIEngineError(RuntimeError):
    pass


def _load_state_dict(torch, path):
    """Muat state dict dari file .pth (menangani kunci 'params'/'params_ema')."""
    try:
        ckpt = torch.load(str(path), map_location="cpu", weights_only=True)
    except Exception:
        ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict):
        for key in ("params_ema", "params"):
            if key in ckpt:
                ckpt = ckpt[key]
                break
    return ckpt


def _validate_checkpoint(model, state, model_path, error_cls):
    """Tolak kombinasi arsitektur + bobot yang tidak cocok (strict)."""
    expected = set(model.state_dict().keys())
    found = set(state.keys())
    if expected != found:
        missing = sorted(expected - found)[:5]
        unexpected = sorted(found - expected)[:5]
        raise error_cls(
            "Checkpoint tidak cocok dengan arsitektur yang dideteksi "
            f"({Path(model_path).name}). missing={missing} unexpected={unexpected}"
        )
    return True


def detect_and_build(model_path, torch, RRDBNet, SRVGGNetCompact, error_cls):
    """
    Deteksi arsitektur dari isi file bobot, validasi, lalu bangun model.

    Mengembalikan (model, meta) dengan meta berisi:
    arch, blocks, scale, label.
    """
    state = _load_state_dict(torch, model_path)
    if not isinstance(state, dict) or not state:
        raise error_cls(f"Isi file model tidak dikenali: {model_path}")
    keys = list(state.keys())

    # RRDBNet (RealESRGAN_x4plus = 23 blok; anime_6B = 6 blok)
    if any(k.startswith("conv_first") for k in keys):
        blocks = set()
        for k in keys:
            parts = k.split(".")
            if len(parts) >= 3 and parts[0] == "body" and parts[2].startswith("rdb"):
                try:
                    blocks.add(int(parts[1]))
                except ValueError:
                    pass
        if not blocks:
            raise error_cls(
                "Checkpoint berarsitektur RRDBNet terdeteksi, tetapi jumlah blok "
                f"tidak dapat dibaca: {model_path}"
            )
        num_block = max(blocks) + 1
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=num_block, num_grow_ch=32, scale=4)
        meta = {"arch": "RRDBNet", "blocks": num_block, "scale": 4,
                "label": f"RRDBNet x4 ({num_block} blocks)"}
    else:
        # SRVGGNetCompact (mis. RealESRGAN_x4plus_anime_6B versi baru)
        body_idx = []
        for k in keys:
            parts = k.split(".")
            if len(parts) == 3 and parts[0] == "body" and parts[2] == "weight":
                try:
                    body_idx.append(int(parts[1]))
                except ValueError:
                    pass
        if not body_idx:
            raise error_cls(f"Arsitektur model tidak dikenali pada file: {model_path}")
        num_conv = (max(body_idx) + 1) // 2
        model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64,
                                num_conv=num_conv, upscale=4, act_type="prelu")
        meta = {"arch": "SRVGGNetCompact", "blocks": num_conv, "scale": 4,
                "label": f"SRVGGNetCompact x4 ({num_conv} convs)"}

    _validate_checkpoint(model, state, model_path, error_cls)
    return model, meta


# Label ramah untuk jenis gambar (dipakai GUI/report sebagai keterangan).
MODEL_KIND = {
    "RealESRGAN_x4plus": "General-purpose (foto, background, ornamen)",
    "RealESRGAN_x4plus_anime_6B": "Anime / ilustrasi",
}


class RealESRGANEngine:
    """
    Optional Real-ESRGAN adapter. Memuat model sekali per batch.

    Arsitektur dideteksi otomatis dari isi file bobot dan divalidasi terhadap
    checkpoint sebelum dipakai.
    """

    def __init__(self, model_name, model_path, tile=256, tile_pad=10, half=True, gpu_id=0):
        try:
            import torch
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from basicsr.archs.srvgg_arch import SRVGGNetCompact
        except Exception as exc:
            raise AIEngineError(
                "Paket Real-ESRGAN belum siap. Ikuti petunjuk instalasi AI di README.txt. "
                f"Detail: {exc}"
            ) from exc

        if not torch.cuda.is_available():
            raise AIEngineError("CUDA NVIDIA tidak terdeteksi oleh PyTorch. AI Engine memerlukan CUDA.")
        model_path = Path(model_path)
        if not model_path.is_file():
            raise AIEngineError(f"File model tidak ditemukan: {model_path}")

        self.torch = torch
        self.RealESRGANer = RealESRGANer
        self.model_name = model_name
        self.model_file = model_path.name
        self.model_path = str(model_path)
        self.tile = int(tile)
        self.tile_pad = int(tile_pad)
        self.half = bool(half)
        self.gpu_id = int(gpu_id)

        self.model, self.model_meta = detect_and_build(
            model_path, torch, RRDBNet, SRVGGNetCompact, AIEngineError
        )
        self.arch_name = self.model_meta["label"]
        self.ckpt_valid = True
        self.active_tile = self.tile
        self.upsampler = self._make_upsampler(self.tile)
        self.device = str(getattr(self.upsampler, "device", "cuda"))
        try:
            self.device_name = torch.cuda.get_device_name(0)
        except Exception:
            self.device_name = self.device
        self.precision = "FP16" if self.half else "FP32"

    def _make_upsampler(self, tile):
        return self.RealESRGANer(
            scale=4, model_path=self.model_path, model=self.model,
            tile=tile, tile_pad=self.tile_pad, pre_pad=0,
            half=self.half, gpu_id=self.gpu_id,
        )

    def info(self):
        """Metadata model untuk laporan (transparan, tidak mengandalkan label manual)."""
        meta = self.model_meta
        return {
            "model_file": self.model_file,
            "model_arch": meta["arch"],
            "model_blocks": meta["blocks"],
            "model_scale": f"x{meta['scale']}",
            "ckpt_valid": "True" if self.ckpt_valid else "False",
            "device": self.device_name,
            "precision": self.precision,
            "tile": self.active_tile,
        }

    def enhance(self, image, progress_callback=None):
        import numpy as np
        import torch
        rgb = image.convert("RGB")
        arr = np.asarray(rgb)
        bgr = arr[:, :, ::-1].copy()

        candidates = []
        for tile in (self.tile, 192, 128, 96, 64, 0):
            if tile <= self.tile and tile not in candidates:
                candidates.append(tile)

        last_error = None
        for tile in candidates:
            try:
                if self.upsampler is None or getattr(self, "_active_tile", None) != tile:
                    self.upsampler = self._make_upsampler(tile)
                    self._active_tile = tile
                output, _ = self.upsampler.enhance(bgr, outscale=4)
                out_rgb = output[:, :, ::-1].copy()
                self.active_tile = tile
                return Image.fromarray(out_rgb, mode="RGB")
            except torch.cuda.OutOfMemoryError as exc:
                last_error = exc
                torch.cuda.empty_cache()
                self.upsampler = None
                self._active_tile = None
                continue
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    last_error = exc
                    torch.cuda.empty_cache()
                    self.upsampler = None
                    self._active_tile = None
                    continue
                raise
        raise AIEngineError(f"AI gagal setelah mencoba beberapa tile. Detail: {last_error}")
