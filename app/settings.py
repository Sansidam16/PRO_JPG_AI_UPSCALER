from pathlib import Path
import json
import sys

APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
if getattr(sys, "frozen", False):
    # Portable onedir: use directory beside the executable for writable data.
    APP_DIR = Path(sys.executable).resolve().parent
ROOT_DIR = APP_DIR
CONFIG_DIR = ROOT_DIR / "config"
MODELS_DIR = ROOT_DIR / "models"
LOG_DIR = ROOT_DIR / "logs"
ASSETS_DIR = ROOT_DIR / "assets"
for folder in (CONFIG_DIR, MODELS_DIR, LOG_DIR, ASSETS_DIR):
    folder.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULTS = {
    "engine": "AI",
    "model": "RealESRGAN_x4plus",
    "preset": "4961 x 3543",
    "custom_width": 4961,
    "custom_height": 3543,
    "resize_mode": "Exact Canvas",
    "canvas_fill": "Edge Extension",
    "background": "#FFFFFF",
    "standard_filter": "Lanczos",
    "ai_strength": 30,
    "ai_preset": "Balanced",
    "detail_enhancement": "Low",
    "noise_reduction": "Off",
    # Selective edge sharpening: sangat ringan, radius relatif thd 2048 px.
    "sharpen_amount": 8,
    "sharpen_radius": 0.6,
    "sharpen_threshold": 4,
    "color_preservation": True,
    "gradient_preservation": True,
    "jpeg_quality": 98,
    "subsampling": "4:4:4",
    "dpi": 300,
    "tile": 256,
    "tile_pad": 10,
    "skip_existing": False,
    "output_naming": "suffix",
    "save_psd": True,
    "sound_on_done": True,
    "output_suffix": "_PRO_UPSCALED"
}

def load_settings():
    data = DEFAULTS.copy()
    try:
        if CONFIG_FILE.exists():
            data.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return data

def save_settings(data):
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
