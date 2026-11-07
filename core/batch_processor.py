"""Batch processing: proses satu gambar sekaligus, catat laporan, kelola GPU/RAM.

Spec §12 (batch stabil, no overwrite, no collision, catat gagal) dan
§13 (validasi output + upscale_report.csv).
"""
from pathlib import Path
import csv
import threading
import traceback

from app.settings import MODELS_DIR
from core.image_pipeline import process_image, output_stem
from core.memory_manager import free_memory
from core.error_handler import describe
from engines.realesrgan_engine import RealESRGANEngine

REPORT_COLUMNS = [
    "source", "output", "psd",
    "src_w", "src_h", "width", "height", "aspect", "mode", "canvas_fill", "method",
    "model", "model_file", "model_arch", "model_blocks", "model_scale", "ckpt_valid",
    "ai_intermediate", "ai_intermediate_w", "ai_intermediate_h", "ai_strength",
    "detail", "noise",
    "sharpen_amount", "sharpen_radius", "sharpen_threshold",
    "device", "precision", "tile",
    "format", "dpi", "icc", "has_icc", "color_converted", "bytes",
    "preprocess_s", "ai_time_s", "resize_time_s", "blend_s", "enhance_s",
    "export_time_s", "time_s", "ok", "error",
]


def _write_report(output_dir, rows):
    path = Path(output_dir) / "upscale_report.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


class BatchProcessor:
    def __init__(self, settings, source_dir, output_dir, log_callback, progress_callback, done_callback, files=None):
        self.settings = settings
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.files = [Path(p) for p in files] if files else None
        self.log = log_callback
        self.progress = progress_callback
        self.done = done_callback
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        if self.files:
            files = sorted(self.files)
        else:
            files = sorted([p for p in self.source_dir.iterdir()
                            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg")])
        total = len(files)
        success = failed = skipped = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if total == 0:
            self.done({"total": 0, "success": 0, "failed": 0, "skipped": 0})
            return

        engine_mode = self.settings.get("engine", "AI")
        ai_engine = None
        if engine_mode == "AI":
            model_name = self.settings.get("model", "RealESRGAN_x4plus")
            model_path = MODELS_DIR / f"{model_name}.pth"
            try:
                ai_engine = RealESRGANEngine(
                    model_name, model_path,
                    tile=self.settings.get("tile", 256),
                    tile_pad=self.settings.get("tile_pad", 10),
                    half=True,
                )
                info = ai_engine.info()
                self.log(
                    "AI Engine siap | model: {f} | arsitektur: {a} | blok: {b} | "
                    "checkpoint: valid | presisi: {p} | device: {d}".format(
                        f=info["model_file"], a=info["model_arch"], b=info["model_blocks"],
                        p=info["precision"], d=info["device"])
                )
            except Exception as exc:
                self.log(f"AI Engine tidak dapat dimulai: {exc}")
                self.done({"total": total, "success": 0, "failed": total, "skipped": 0})
                return

        skip_existing = bool(self.settings.get("skip_existing", False))
        rows = []

        for index, path in enumerate(files, start=1):
            if self.cancel_event.is_set():
                skipped += (total - index + 1)
                break
            self.progress(index - 1, total, success, failed,
                          f"Memproses {index}/{total}: {path.name}")

            if skip_existing and (self.output_dir / f"{output_stem(path, self.settings)}.jpg").exists():
                skipped += 1
                self.log(f"[{index}/{total}] Dilewati (output sudah ada): {path.name}")
                self.progress(index, total, success, failed,
                              f"Selesai {index}/{total}: {path.name}")
                continue

            try:
                report, out_path = process_image(
                    path, self.output_dir, self.settings, ai_engine=ai_engine, log=self.log
                )
                report["output"] = out_path.name
                report["aspect"] = round(report["width"] / report["height"], 4) if report.get("height") else ""
                report["error"] = ""
                rows.append(report)
                if report.get("ok"):
                    success += 1
                    produced = out_path.name
                    if report.get("psd") and report["psd"] != "-":
                        produced += f" + {report['psd']}"
                    self.log(f"  Selesai: {produced} "
                             f"({report['method']}, {report['time_s']}s, "
                             f"{report.get('model_arch', '-')} {report.get('model_blocks', '-')} blok, "
                             f"AI {report.get('ai_time_s', '-')}s, ICC: {report.get('icc', '-')})")
                else:
                    failed += 1
                    self.log(f"  GAGAL validasi: {out_path.name}")
            except Exception as exc:
                failed += 1
                self.log(f"  GAGAL: {path.name} - {describe(exc)}")
                self.log(traceback.format_exc())
                rows.append({
                    "source": path.name, "output": "-", "method": "-",
                    "model": "-", "ai_strength": "-", "ok": False,
                    "error": describe(exc),
                })
            finally:
                free_memory()
                self.progress(index, total, success, failed,
                              f"Selesai {index}/{total}: {path.name}")

        if rows:
            report_path = _write_report(self.output_dir, rows)
            self.log(f"Laporan tersimpan: {report_path.name}")

        self.done({"total": total, "success": success, "failed": failed, "skipped": skipped})
