import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import queue

from app.settings import load_settings, save_settings, MODELS_DIR, ASSETS_DIR
from app.theme import apply_theme
from core.image_ops import PRESETS, RESIZE_MODES, CANVAS_FILL_MODES
from core.gpu_manager import status as gpu_status
from core.batch_processor import BatchProcessor
from engines.realesrgan_engine import MODEL_KIND

AI_PRESETS = {"Conservative": 20, "Balanced": 30, "Enhanced": 50, "Full AI": 100}
DETAIL_LEVELS = ["Off", "Low", "Medium", "High"]
NOISE_LEVELS = ["Off", "Low", "Medium", "High"]
SUBSAMPLING_OPTIONS = ["4:4:4", "4:2:2", "4:2:0"]
STANDARD_FILTERS = ["Lanczos", "Bicubic"]


class UpscalerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PRO JPG AI Upscaler")
        self._apply_window_icon()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1060, max(760, screen_w - 60))
        win_h = min(720, max(540, screen_h - 110))
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2 - 20)
        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.minsize(min(940, win_w), min(600, win_h))
        self.settings = load_settings()
        self.events = queue.Queue()
        self.processor = None
        self.worker = None
        self.file_vars = {}

        s = self.settings
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.engine_var = tk.StringVar(value=s["engine"])
        self.model_var = tk.StringVar(value=s["model"])
        self.preset_var = tk.StringVar(value=s["preset"])
        self.mode_var = tk.StringVar(value=s.get("resize_mode", "Exact Canvas"))
        self.canvas_fill_var = tk.StringVar(value=s.get("canvas_fill", "Edge Extension"))
        self.ai_preset_var = tk.StringVar(value=s.get("ai_preset", "Balanced"))
        self.ai_strength_var = tk.IntVar(value=s.get("ai_strength", 30))
        self.detail_var = tk.StringVar(value=s.get("detail_enhancement", "Low"))
        self.noise_var = tk.StringVar(value=s.get("noise_reduction", "Off"))
        self.sharpen_amount_var = tk.IntVar(value=s.get("sharpen_amount", 0))
        self.sharpen_radius_var = tk.DoubleVar(value=s.get("sharpen_radius", 1.0))
        self.sharpen_threshold_var = tk.IntVar(value=s.get("sharpen_threshold", 3))
        self.quality_var = tk.IntVar(value=s.get("jpeg_quality", 98))
        self.subsampling_var = tk.StringVar(value=s.get("subsampling", "4:4:4"))
        self.filter_var = tk.StringVar(value=s.get("standard_filter", "Lanczos"))
        self.tile_var = tk.IntVar(value=s.get("tile", 256))
        self.bg_var = tk.StringVar(value=s.get("background", "#FFFFFF"))
        self.skip_var = tk.BooleanVar(value=bool(s.get("skip_existing", False)))
        self.naming_var = tk.BooleanVar(value=(s.get("output_naming", "suffix") == "original"))
        self.psd_var = tk.BooleanVar(value=bool(s.get("save_psd", True)))
        self.sound_var = tk.BooleanVar(value=bool(s.get("sound_on_done", True)))
        self.custom_w_var = tk.IntVar(value=s.get("custom_width", 4961))
        self.custom_h_var = tk.IntVar(value=s.get("custom_height", 3543))
        if s.get("preset") in PRESETS:
            _pw, _ph = PRESETS[s["preset"]]
            self.custom_w_var.set(_pw)
            self.custom_h_var.set(_ph)
        self.status_var = tk.StringVar(value="Ready")

        apply_theme(self)
        self._build_ui()
        self.after(100, self._poll_events)
        self._check_gpu()

    def _apply_window_icon(self):
        icon_path = ASSETS_DIR / "icon.ico"
        try:
            if icon_path.exists():
                self.iconbitmap(default=str(icon_path))
        except Exception:
            pass

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self):
        # Layout ringkas: seluruh konten dibuat muat satu layar tanpa scroll.
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="PRO JPG AI Upscaler", style="Header.TLabel").pack(side="left")
        self.gpu_label = ttk.Label(header, text="Checking GPU...")
        self.gpu_label.pack(side="right")

        folders = ttk.LabelFrame(root, text="Input & Output", padding=8)
        folders.pack(fill="x", pady=(6, 6))
        self._folder_row(folders, "Source folder", self.source_var, self._browse_source,
                         self._refresh_file_list)
        self._folder_row(folders, "Output folder", self.output_var, self._browse_output)

        # Dua kolom yang mengisi sisa jendela: daftar file (kiri) & pengaturan (kanan).
        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        files_frame = ttk.LabelFrame(body, text="Source Files (JPG/JPEG)", padding=6)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_wrap = ttk.Frame(files_frame)
        list_wrap.pack(fill="both", expand=True)
        self.file_canvas = tk.Canvas(list_wrap, height=70, highlightthickness=1,
                                     background="#FFFFFF")
        file_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.file_canvas.yview)
        self.file_canvas.configure(yscrollcommand=file_scroll.set)
        self.file_canvas.pack(side="left", fill="both", expand=True)
        file_scroll.pack(side="right", fill="y")
        self.file_inner = ttk.Frame(self.file_canvas)
        self._file_window = self.file_canvas.create_window((0, 0), window=self.file_inner, anchor="nw")
        self.file_inner.bind(
            "<Configure>",
            lambda e: self.file_canvas.configure(scrollregion=self.file_canvas.bbox("all")))
        self.file_canvas.bind(
            "<Configure>",
            lambda e: self.file_canvas.itemconfigure(self._file_window, width=e.width))
        self.file_canvas.bind(
            "<Enter>",
            lambda e: self.file_canvas.bind_all("<MouseWheel>", self._on_file_mousewheel))
        self.file_canvas.bind("<Leave>", lambda e: self.file_canvas.unbind_all("<MouseWheel>"))

        file_actions = ttk.Frame(files_frame)
        file_actions.pack(fill="x", pady=(6, 0))
        ttk.Button(file_actions, text="Refresh", command=self._refresh_file_list).pack(side="left")
        ttk.Button(file_actions, text="Select All", command=self._select_all_files).pack(side="left", padx=6)
        ttk.Button(file_actions, text="Clear", command=self._clear_file_selection).pack(side="left")
        self.file_count_label = ttk.Label(file_actions, text="0 file dipilih")
        self.file_count_label.pack(side="right")

        self._build_settings(body)

        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(8, 6))
        self.start_btn = ttk.Button(actions, text="START PROCESSING", style="Accent.TButton",
                                    command=self._start)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(actions, text="CANCEL", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ttk.Button(actions, text="Save Preset", command=self._save_preset).pack(side="left")
        ttk.Button(actions, text="Open Output Folder", command=self._open_output).pack(side="right")

        # Progress dan Log berdampingan agar tinggi total UI tetap ringkas.
        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(2, 0))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=2)

        status = ttk.LabelFrame(bottom, text="Progress", padding=8)
        status.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(status, textvariable=self.status_var, wraplength=280,
                  justify="left").pack(anchor="w")
        self.progress = ttk.Progressbar(status, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(7, 3))
        self.count_label = ttk.Label(status, text="0 / 0")
        self.count_label.pack(anchor="e")

        log_frame = ttk.LabelFrame(bottom, text="Processing Log", padding=6)
        log_frame.grid(row=0, column=1, sticky="nsew")
        self.log_text = tk.Text(log_frame, height=5, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._log("Aplikasi siap. Pilih folder sumber dan folder output.")

    def _on_file_mousewheel(self, event):
        self.file_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _show_centered_info(self, title, message):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=message, justify="center", anchor="center").pack()
        ttk.Button(body, text="OK", command=dialog.destroy).pack(pady=(18, 0))
        dialog.update_idletasks()
        w, h = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.grab_set()
        dialog.focus_set()
        self.wait_window(dialog)

    def _available_models(self):
        names = sorted(p.stem for p in MODELS_DIR.glob("*.pth"))
        current = self.model_var.get()
        if current and current not in names:
            names.append(current)
        return names or ["RealESRGAN_x4plus"]

    def _cell(self, parent, band, col, label_text, widget):
        ttk.Label(parent, text=label_text).grid(
            row=band * 2, column=col, sticky="w", padx=(0, 8),
            pady=(0 if band == 0 else 4, 0))
        widget.grid(row=band * 2 + 1, column=col, sticky="ew", padx=(0, 8), pady=(2, 0))
        return widget

    def _build_settings(self, parent):
        nb = ttk.Notebook(parent)
        nb.grid(row=0, column=1, sticky="nsew")

        # ---------------------------------------------------------- Output ---
        out = ttk.Frame(nb, padding=8)
        nb.add(out, text="Output")
        for col in range(3):
            out.columnconfigure(col, weight=1, uniform="s")

        engine = ttk.Combobox(out, textvariable=self.engine_var,
                              values=["AI", "Standard"], state="readonly")
        engine.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 0, 0, "Engine", engine)

        model = ttk.Combobox(out, textvariable=self.model_var,
                             values=self._available_models(), state="readonly")
        model.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 0, 1, "AI Model", model)

        preset = ttk.Combobox(out, textvariable=self.preset_var,
                              values=list(PRESETS.keys()) + ["Custom"], state="readonly")
        preset.bind("<<ComboboxSelected>>", lambda e: self._on_preset_selected())
        self._cell(out, 0, 2, "Output preset", preset)

        mode = ttk.Combobox(out, textvariable=self.mode_var, values=RESIZE_MODES, state="readonly")
        mode.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 1, 0, "Resize mode", mode)

        fill = ttk.Combobox(out, textvariable=self.canvas_fill_var, values=CANVAS_FILL_MODES,
                            state="readonly")
        fill.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 1, 1, "Canvas fill", fill)

        bg = ttk.Entry(out, textvariable=self.bg_var)
        bg.bind("<FocusOut>", lambda e: self._save_settings())
        self._cell(out, 1, 2, "Background (hex)", bg)

        width = ttk.Spinbox(out, from_=16, to=20000, textvariable=self.custom_w_var,
                            command=self._on_custom_change)
        width.bind("<FocusOut>", lambda e: self._on_custom_change())
        width.bind("<Return>", lambda e: self._on_custom_change())
        self._cell(out, 2, 0, "Width (px)", width)

        height = ttk.Spinbox(out, from_=16, to=20000, textvariable=self.custom_h_var,
                             command=self._on_custom_change)
        height.bind("<FocusOut>", lambda e: self._on_custom_change())
        height.bind("<Return>", lambda e: self._on_custom_change())
        self._cell(out, 2, 1, "Height (px)", height)

        filt = ttk.Combobox(out, textvariable=self.filter_var, values=STANDARD_FILTERS, state="readonly")
        filt.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 2, 2, "Standard filter", filt)

        tile = ttk.Combobox(out, textvariable=self.tile_var, values=[128, 192, 256, 384, 512],
                            state="readonly")
        tile.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 3, 0, "Tile size (AI)", tile)

        quality = ttk.Combobox(out, textvariable=self.quality_var, values=[95, 98, 100], state="readonly")
        quality.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 3, 1, "JPEG Quality", quality)

        sub = ttk.Combobox(out, textvariable=self.subsampling_var, values=SUBSAMPLING_OPTIONS,
                           state="readonly")
        sub.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(out, 3, 2, "Chroma subsampling", sub)

        # Band 4: DPI + opsi penamaan file & format output (JPG selalu, PSD opsional).
        fmt = ttk.Frame(out)
        fmt.grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(fmt, text="DPI 300 x 300").pack(side="left", padx=(0, 10))
        ttk.Checkbutton(fmt, text="Nama = file asli", variable=self.naming_var,
                        command=self._save_settings).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(fmt, text="Simpan PSD", variable=self.psd_var,
                        command=self._save_settings).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(fmt, text="Skip yang sudah ada", variable=self.skip_var,
                        command=self._save_settings).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(fmt, text="Suara selesai", variable=self.sound_var,
                        command=self._save_settings).pack(side="left")

        # ------------------------------------------------------ AI & Quality ---
        ai = ttk.Frame(nb, padding=8)
        nb.add(ai, text="AI & Quality")
        for col in range(3):
            ai.columnconfigure(col, weight=1, uniform="s")

        strength = ttk.Spinbox(ai, from_=0, to=100, textvariable=self.ai_strength_var,
                               command=self._on_ai_strength)
        strength.bind("<FocusOut>", lambda e: self._on_ai_strength())
        strength.bind("<Return>", lambda e: self._on_ai_strength())
        self._cell(ai, 0, 0, "AI Strength (%)", strength)

        ai_preset = ttk.Combobox(ai, textvariable=self.ai_preset_var,
                                  values=list(AI_PRESETS.keys()) + ["Custom"], state="readonly")
        ai_preset.bind("<<ComboboxSelected>>", lambda e: self._on_ai_preset())
        self._cell(ai, 0, 1, "AI Strength preset", ai_preset)

        detail = ttk.Combobox(ai, textvariable=self.detail_var, values=DETAIL_LEVELS, state="readonly")
        detail.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(ai, 0, 2, "Detail Enhancement", detail)

        noise = ttk.Combobox(ai, textvariable=self.noise_var, values=NOISE_LEVELS, state="readonly")
        noise.bind("<<ComboboxSelected>>", lambda e: self._save_settings())
        self._cell(ai, 1, 0, "Noise Reduction", noise)

        amount = ttk.Spinbox(ai, from_=0, to=300, textvariable=self.sharpen_amount_var,
                             command=self._save_settings)
        self._cell(ai, 1, 1, "Sharpening Amount", amount)

        radius = ttk.Spinbox(ai, from_=0.1, to=5.0, increment=0.1,
                             textvariable=self.sharpen_radius_var, command=self._save_settings)
        self._cell(ai, 1, 2, "Sharpening Radius", radius)

        threshold = ttk.Spinbox(ai, from_=0, to=50, textvariable=self.sharpen_threshold_var,
                                command=self._save_settings)
        self._cell(ai, 2, 0, "Sharpening Threshold", threshold)

    def _folder_row(self, parent, label, variable, command, on_commit=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=15).pack(side="left")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        if on_commit is not None:
            entry.bind("<Return>", lambda e: on_commit())
            entry.bind("<FocusOut>", lambda e: on_commit())
        ttk.Button(row, text="Browse", command=command).pack(side="right")

    # -------------------------------------------------------------- folders ---
    def _browse_source(self):
        p = filedialog.askdirectory(title="Pilih folder JPG/JPEG")
        if p:
            self.source_var.set(p)
            self._refresh_file_list()

    def _source_files(self):
        folder = self.source_var.get().strip()
        if not folder or not Path(folder).is_dir():
            return []
        return sorted(p for p in Path(folder).iterdir()
                      if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg"))

    def _refresh_file_list(self):
        for child in self.file_inner.winfo_children():
            child.destroy()
        self.file_vars = {}
        files = self._source_files()
        for path in files:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(self.file_inner, text=path.name, variable=var,
                            command=self._update_selected_label).pack(anchor="w", fill="x")
            self.file_vars[str(path)] = var
        self.file_canvas.configure(scrollregion=self.file_canvas.bbox("all"))
        self._update_selected_label()

    def _update_selected_label(self):
        total = len(self.file_vars)
        chosen = sum(1 for v in self.file_vars.values() if v.get())
        self.file_count_label.config(text=f"{chosen} / {total} file dipilih")

    def _select_all_files(self):
        for var in self.file_vars.values():
            var.set(True)
        self._update_selected_label()

    def _clear_file_selection(self):
        for var in self.file_vars.values():
            var.set(False)
        self._update_selected_label()

    def _selected_files(self):
        return [path for path, var in self.file_vars.items() if var.get()]

    def _browse_output(self):
        p = filedialog.askdirectory(title="Pilih folder output")
        if p:
            self.output_var.set(p)

    # ------------------------------------------------------------- settings ---
    def _settings_dict(self):
        return {
            "engine": self.engine_var.get(),
            "model": self.model_var.get(),
            "preset": self.preset_var.get(),
            "custom_width": max(16, int(self.custom_w_var.get())),
            "custom_height": max(16, int(self.custom_h_var.get())),
            "resize_mode": self.mode_var.get(),
            "canvas_fill": self.canvas_fill_var.get(),
            "background": self.bg_var.get().strip() or "#FFFFFF",
            "standard_filter": self.filter_var.get(),
            "ai_strength": max(0, min(100, int(self.ai_strength_var.get()))),
            "ai_preset": self.ai_preset_var.get(),
            "detail_enhancement": self.detail_var.get(),
            "noise_reduction": self.noise_var.get(),
            "sharpen_amount": max(0, min(300, int(self.sharpen_amount_var.get()))),
            "sharpen_radius": max(0.1, float(self.sharpen_radius_var.get())),
            "sharpen_threshold": max(0, min(50, int(self.sharpen_threshold_var.get()))),
            "color_preservation": True,
            "gradient_preservation": True,
            "jpeg_quality": max(70, min(100, int(self.quality_var.get()))),
            "subsampling": self.subsampling_var.get(),
            "dpi": 300,
            "tile": int(self.tile_var.get()),
            "tile_pad": 10,
            "skip_existing": bool(self.skip_var.get()),
            "output_naming": "original" if self.naming_var.get() else "suffix",
            "save_psd": bool(self.psd_var.get()),
            "sound_on_done": bool(self.sound_var.get()),
            "output_suffix": "_PRO_UPSCALED",
        }

    def _save_settings(self):
        try:
            self.settings = self._settings_dict()
            save_settings(self.settings)
        except Exception:
            pass

    def _save_preset(self):
        try:
            self.settings = self._settings_dict()
            save_settings(self.settings)
            messagebox.showinfo("Save Preset", "Pengaturan berhasil disimpan.")
        except Exception as exc:
            messagebox.showerror("Save Preset", str(exc))

    def _on_preset_selected(self):
        preset = self.preset_var.get()
        if preset in PRESETS:
            w, h = PRESETS[preset]
            self.custom_w_var.set(w)
            self.custom_h_var.set(h)
        self._save_settings()

    def _on_custom_change(self):
        try:
            self.preset_var.set("Custom")
        except Exception:
            pass
        self._save_settings()

    def _on_ai_preset(self):
        name = self.ai_preset_var.get()
        if name in AI_PRESETS:
            self.ai_strength_var.set(AI_PRESETS[name])
        self._save_settings()

    def _on_ai_strength(self):
        try:
            value = int(self.ai_strength_var.get())
        except Exception:
            return
        match = next((k for k, v in AI_PRESETS.items() if v == value), "Custom")
        self.ai_preset_var.set(match)
        self._save_settings()

    # ------------------------------------------------------------------ gpu ---
    def _check_gpu(self):
        info = gpu_status()
        if info["available"]:
            self.gpu_label.config(text=f"CUDA READY: {info['name']}", foreground="#16834A")
            self._log(f"NVIDIA CUDA tersedia: {info['name']}")
        else:
            self.gpu_label.config(text="CUDA NOT AVAILABLE", foreground="#B45F06")
            self._log(f"CUDA tidak tersedia. {info['reason']}. Standard Engine tetap dapat digunakan.")
        models = sorted(p.stem for p in MODELS_DIR.glob("*.pth"))
        self._log(f"Model AI tersedia ({len(models)}): {', '.join(models) if models else 'tidak ada'}")
        for name in models:
            kind = MODEL_KIND.get(name)
            if kind:
                self._log(f"  {name}: {kind}")

    # ------------------------------------------------------------- processing ---
    def _start(self):
        source, output = self.source_var.get().strip(), self.output_var.get().strip()
        if not source or not Path(source).is_dir():
            messagebox.showerror("Source folder", "Pilih folder sumber yang valid.")
            return
        if not output:
            messagebox.showerror("Output folder", "Pilih folder output.")
            return
        if Path(source).resolve() == Path(output).resolve():
            messagebox.showerror("Folder tidak valid", "Folder output harus berbeda dari folder sumber.")
            return
        selected = self._selected_files()
        if not selected:
            messagebox.showerror("File sumber", "Tidak ada file JPG/JPEG yang dipilih.")
            return
        try:
            self.settings = self._settings_dict()
            if not self.settings["background"].startswith("#") or len(self.settings["background"]) != 7:
                raise ValueError("Background harus berupa kode HEX, contoh #FFFFFF.")
            save_settings(self.settings)
        except Exception as exc:
            messagebox.showerror("Pengaturan tidak valid", str(exc))
            return
        self.progress["value"] = 0
        self.count_label.config(text="0 / 0")
        self.status_var.set("Processing...")
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.processor = BatchProcessor(
            self.settings, source, output,
            lambda msg: self.events.put(("log", msg)),
            lambda i, n, s, f, name: self.events.put(("progress", i, n, s, f, name)),
            lambda result: self.events.put(("done", result)),
            files=selected,
        )
        self.worker = threading.Thread(target=self.processor.run, daemon=True)
        self.worker.start()

    def _cancel(self):
        if self.processor:
            self.processor.cancel()
            self.status_var.set("Cancelling after current image...")
            self.cancel_btn.config(state="disabled")

    def _open_output(self):
        p = self.output_var.get().strip()
        if p and Path(p).is_dir():
            import os
            os.startfile(p)
        else:
            messagebox.showinfo("Output", "Folder output belum tersedia.")

    def _log(self, message):
        self.log_text.insert("end", str(message) + "\n")
        self.log_text.see("end")

    def _play_done_sound(self):
        """Mainkan nada penanda proses selesai (dapat dimatikan lewat checkbox)."""
        if not self.sound_var.get():
            return
        try:
            import winsound

            def _chime():
                for freq, dur in ((880, 120), (1175, 180)):
                    winsound.Beep(freq, dur)

            threading.Thread(target=_chime, daemon=True).start()
        except Exception:
            try:
                self.bell()
            except Exception:
                pass

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "log":
                    self._log(event[1])
                elif event[0] == "progress":
                    _, i, n, s, f, name = event
                    self.progress["value"] = (i / n) * 100 if n else 0
                    self.count_label.config(text=f"{i} / {n} | Berhasil: {s} | Gagal: {f}")
                    if name:
                        self.status_var.set(name)
                elif event[0] == "done":
                    result = event[1]
                    total = result["total"]
                    self.progress["value"] = 100 if total else 0
                    self.count_label.config(
                        text=f"{total} / {total} | Berhasil: {result['success']} | Gagal: {result['failed']}")
                    self.status_var.set("Finished")
                    self.start_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self._play_done_sound()
                    self._log(f"Ringkasan: {result}")
                    self._show_centered_info(
                        "Selesai",
                        f"Proses selesai.\n\nBerhasil: {result['success']}\n"
                        f"Gagal: {result['failed']}\nDilewati: {result['skipped']}")
        except queue.Empty:
            pass
        self.after(100, self._poll_events)
