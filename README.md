# PRO JPG AI UPSCALER

Aplikasi desktop (Windows) untuk **upscaling batch gambar JPG/JPEG** dengan kualitas mendekati hasil olah profesional di Photoshop. Menggabungkan baseline **Lanczos** dengan **Real-ESRGAN (AI)** secara konservatif, lalu diteruskan ke tahap *color management* sRGB, penyematan profil ICC, dan ekspor JPEG/PSD beresolusi tinggi (300 DPI).

- Bahasa: Python 3.11 / 3.12 (64-bit)
- GUI: Tkinter
- AI: Real-ESRGAN (PyTorch + CUDA)
- Pengolahan gambar: Pillow + NumPy

---

## 1. Fitur Utama

- **Batch JPG/JPEG** dari satu folder (hanya file di level teratas), dengan **daftar centang (checklist)** untuk memilih file satuan atau semua file.
- **Dua engine**:
  - **Standard** — resize Lanczos / Bicubic (tidak memerlukan PyTorch).
  - **AI** — Real-ESRGAN x4 (wajib CUDA NVIDIA).
- **Model AI yang didukung** (terdeteksi otomatis dari isi file `.pth`, bukan dari namanya):
  - `RealESRGAN_x4plus` — serba guna: foto, background, ornamen, objek metalik, gradasi. **Default.**
  - `RealESRGAN_x4plus_anime_6B` — khusus ilustrasi / anime.
- **Pipeline AI konservatif** (kualitas natural, minim artefak):
  `Lanczos baseline → Real-ESRGAN x4 → Lanczos ke target → AI strength blending → enhancement → sRGB → JPEG/PSD → validasi`.
- **AI Strength 0–100 %** dengan preset: Conservative 20 / Balanced 30 / Enhanced 50 / Full AI 100.
- **Detail Enhancement**: Off / Low / Medium / High.
- **Noise Reduction**: Off / Low / Medium / High (bawaan Off).
- **Selective Edge Sharpening**: hanya tepi kuat (garis geometris, tepi bintang/snowflake, ornamen logam) yang dipertajam; gradasi halus, bokeh, dan bayangan lembut dilindungi (anti-halo). **Radius bersifat sadar-dimensi** — nilai berlaku pada resolusi referensi 2048 px lalu diskalakan ke dimensi output (dibatasi 0.3–3.0 px). Default ringan: Amount 8 / Radius 0.6 / Threshold 4.
- **Color management**: konversi ICC sumber ke sRGB dan **menyematkan profil `sRGB IEC61966-2.1`** pada output JPG dan PSD.
- **Output presets**: 1920×600, 1920×700, 1920×900, 3543×4961, 4961×3543, dan Custom.
- **Mode geometri**: Exact Canvas / Preserve Aspect Ratio / Fit / Crop / Stretch.
- **Canvas fill** untuk Exact Canvas & Fit: **Edge Extension** (default, mereplikasi piksel tepi) atau warna background.
- **Output format**: JPG selalu; **PSD 8-bit RGB opsional** (ditulis sendiri, kompresi RLE PackBits).
- **Opsi penamaan**: nama file asli atau akhiran `_PRO_UPSCALED`.
- **JPEG**: kualitas 95 / 98 / 100 (bervariasi), chroma subsampling 4:4:4 / 4:2:2 / 4:2:0. **DPI 300**, mode RGB.
- **Nada selesai** (opsional): bunyi penanda saat batch selesai.
- **Laporan validasi `upscale_report.csv`** di folder output (lihat bagian 6).
- **Tanpa menimpa file**: nama output otomatis dibuat unik; tersedia opsi *skip* file yang sudah ada.

---

## 2. Persyaratan

- Windows 10/11, 64-bit.
- Python 3.11 atau 3.12, 64-bit.
- Untuk AI: GPU **NVIDIA dengan CUDA** + PyTorch bertipe CUDA.
  Standard Engine dapat berjalan tanpa PyTorch/CUDA.

---

## 3. Instalasi

Jalankan CMD/PowerShell di folder proyek.

### 3.1 Dasar (Standard Engine)

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3.2 AI Engine (Real-ESRGAN + CUDA)

1. Pasang PyTorch + torchvision bertipe CUDA memakai pemilih resmi:
   https://pytorch.org/get-started/locally/ (jangan memakai build CPU-only).
2. Pasang dependensi AI:

```bat
python -m pip install -r requirements-ai.txt
```

3. Verifikasi CUDA:

```bat
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
```

---

## 4. Menjalankan Aplikasi

```bat
.venv\Scripts\python main.py
```

Model AI dimuat **sekali per batch** untuk efisiensi memori. Model yang tersedia dibaca otomatis dari folder `models/`.

---

## 5. Panduan Antarmuka (UI)

Jendela terbagi menjadi beberapa area. Ukuran jendela menyesuaikan layar laptop dan seluruh kontrol muat tanpa scroll vertikal.

### 5.1 Header

- **Judul**: `PRO JPG AI Upscaler`.
- **Status GPU** (kanan atas):
  - `CUDA READY: <nama GPU>` (hijau) — GPU NVIDIA terdeteksi.
  - `CUDA NOT AVAILABLE` (oranye) — tidak terdeteksi; Standard Engine tetap bisa dipakai.

### 5.2 Panel "Input & Output"

- **Source folder** — folder berisi JPG/JPEG. Klik **Browse** atau tekan `Enter` untuk memuat daftar file.
- **Output folder** — folder tujuan hasil. Klik **Browse**. Tidak boleh sama dengan folder sumber.

### 5.3 Panel "Source Files (JPG/JPEG)"

- Daftar centang seluruh file `.jpg`/`.jpeg` pada folder sumber (semua tercentang secara bawaan).
- **Refresh** — muat ulang daftar file.
- **Select All** — centang semua file.
- **Clear** — hapus semua centang.
- Label kanan: `X / Y file dipilih`.

### 5.4 Tab "Output"

| Kontrol | Fungsi |
| --- | --- |
| **Engine** | `AI` (Real-ESRGAN) atau `Standard` (Lanczos/Bicubic). |
| **AI Model** | Pilih model dari folder `models/`. Daftar dimuat dinamis. |
| **Output preset** | Ukuran target: 1920×600, 1920×700, 1920×900, 3543×4961, 4961×3543, atau Custom. |
| **Resize mode** | Cara menyesuaikan gambar ke target: Exact Canvas, Preserve Aspect Ratio, Fit, Crop, Stretch. |
| **Canvas fill** | Pengisian sisa kanvas (Exact Canvas/Fit): **Edge Extension** (default) atau Background Color. |
| **Background (hex)** | Warna latar, contoh `#FFFFFF`. Dipakai bila Canvas fill = Background Color. |
| **Width / Height (px)** | Dimensi target manual (16–20000). Mengubahnya otomatis mengeset preset ke `Custom`. |
| **Standard filter** | Filter resize Standar/baseline: Lanczos atau Bicubic. |
| **Tile size (AI)** | Ukuran tile inferensi (128–512). Tile lebih kecil menurunkan pemakaian VRAM. |
| **JPEG Quality** | 95 / 98 / 100. |
| **Chroma subsampling** | 4:4:4 (terbaik) / 4:2:2 / 4:2:0. |
| **DPI 300 x 300** | Tetap (label). Metadata resolusi output. |
| **Nama = file asli** | Jika dicentang, output memakai nama file asli; jika tidak, ditambah `_PRO_UPSCALED`. |
| **Simpan PSD** | Jika dicentang, selain JPG juga menyimpan PSD 8-bit RGB. |
| **Skip yang sudah ada** | Lewati file yang output JPG-nya sudah ada. |
| **Suara selesai** | Bunyi penanda saat proses batch selesai. |

### 5.5 Tab "AI & Quality"

| Kontrol | Fungsi |
| --- | --- |
| **AI Strength (%)** | Bobot hasil AI (0–100). 0 = murni Lanczos, 100 = murni AI. |
| **AI Strength preset** | Conservative 20 / Balanced 30 / Enhanced 50 / Full AI 100 / Custom. |
| **Detail Enhancement** | Off / Low / Medium / High — menambah satu pass penajaman detail (digabung dengan sharpening). |
| **Noise Reduction** | Off / Low / Medium / High — diterapkan pada sumber sebelum upscaling. |
| **Sharpening Amount** | Kekuatan sharpening (0–300). |
| **Sharpening Radius** | Radius pada resolusi referensi 2048 px (0.1–5.0); diskalakan ke dimensi output. |
| **Sharpening Threshold** | Ambang minimum detail yang diperkuat (0–50). |

> Catatan: sharpening bersifat *edge-aware* (menggunakan edge mask + protection mask) sehingga area gradasi/bokeh tidak tersentuh; lihat bagian 7.

### 5.6 Tombol Aksi

- **START PROCESSING** — mulai batch. Tombol dinonaktifkan saat proses berjalan.
- **CANCEL** — berhenti setelah gambar yang sedang diproses selesai.
- **Save Preset** — simpan pengaturan saat ini ke `config/settings.json`.
- **Open Output Folder** — buka folder output di File Explorer.

### 5.7 Panel Bawah

- **Progress** — status teks, progress bar, dan hitungan `berhasil / gagal`.
- **Processing Log** — catatan langkah proses per gambar, ringkasan waktu, arsitektur model, dsb.

---

## 6. Pipeline Pemrosesan

1. Muat gambar sumber + terapkan orientasi EXIF.
2. Baca profil ICC yang tertanam.
3. Analisis dimensi sumber.
4. Normalisasi ke ruang kerja sRGB.
5. *Noise reduction* opsional (pada sumber).
6. Buat **baseline** Lanczos/Bicubic sesuai geometri target.
7. **Inferensi Real-ESRGAN x4** (hanya bila target lebih besar dari sumber — *enlargement*).
8. Resize hasil AI ke target memakai Lanczos.
9. **AI strength blending**: `(1 − α)·baseline + α·AI`.
10. **Detail enhancement + selective edge sharpening** (satu pass).
11. Konversi akhir ke sRGB + sematkan profil `sRGB IEC61966-2.1`.
12. Ekspor **JPG** (dan **PSD** bila diaktifkan).
13. Validasi hasil (format, mode RGB, dimensi, ICC, DPI).

### Kebijakan AI

Bila gambar sumber **sudah cukup piksel** untuk geometri target, AI dilewati dan cukup di-resize dengan filter standar. AI dipakai saat diperlukan *enlargement*.

---

## 7. Laporan `upscale_report.csv`

Ditulis di folder output setelah batch. Cakupan kolom:

- **Berkas**: `source`, `output`, `psd`
- **Dimensi**: `src_w`, `src_h`, `width`, `height`, `aspect`, `mode`, `canvas_fill`, `method`
- **Model**: `model`, `model_file` (nama file aktual), `model_arch` (RRDBNet / SRVGGNetCompact), `model_blocks` (jumlah blok RRDB), `model_scale`, `ckpt_valid`
- **AI**: `ai_intermediate_w`, `ai_intermediate_h`, `ai_strength`
- **Enhancement**: `detail`, `noise`, `sharpen_amount`, `sharpen_radius`, `sharpen_threshold`
- **Perangkat**: `device` (nama GPU), `precision` (FP16/FP32), `tile`
- **Output**: `format`, `dpi`, `icc`, `has_icc`, `color_converted`, `bytes`
- **Waktu (detik, saling eksklusif/sumable)**: `preprocess_s`, `ai_time_s`, `resize_time_s`, `blend_s`, `enhance_s`, `export_time_s`, `time_s` (total)
- **Status**: `ok`, `error`

> Model yang dicatat adalah model yang **benar-benar dimuat** (dibaca dari isi file bobot), bukan sekadar label. Bila checkpoint tidak cocok dengan arsitektur, proses dihentikan dengan pesan jelas.

---

## 8. Struktur Proyek

```
PRO_JPG_AI_UPSCALER/
├─ main.py                     # Titik masuk aplikasi
├─ app/
│  ├─ gui.py                   # Antarmuka Tkinter
│  ├─ settings.py              # Default + muat/simpan pengaturan
│  └─ theme.py                 # Tema ttk
├─ core/
│  ├─ image_pipeline.py        # Orkestrasi pipeline (spec §4)
│  ├─ image_analyzer.py        # EXIF, ICC, dimensi
│  ├─ image_ops.py             # Preset, geometri, edge extension
│  ├─ color_manager.py         # Konversi & profil sRGB
│  ├─ image_exporter.py        # Ekspor + validasi JPG/PSD
│  ├─ psd_writer.py            # Penulis PSD (RLE PackBits)
│  ├─ batch_processor.py       # Batch + penulisan CSV
│  ├─ memory_manager.py        # Manajemen RAM/VRAM
│  ├─ gpu_manager.py           # Deteksi CUDA
│  └─ error_handler.py         # Deskripsi error
├─ engines/
│  ├─ realesrgan_engine.py     # Adapter Real-ESRGAN + deteksi arsitektur
│  ├─ blending_engine.py       # Blending baseline + AI
│  ├─ enhancement_engine.py    # Noise/detail/edge-aware sharpening
│  └─ standard_engine.py       # Resize standar
├─ assets/
│  └─ sRGB_IEC61966-2.1.icc    # Profil warna output
├─ config/
│  └─ settings.json            # Pengaturan tersimpan
├─ models/
│  ├─ RealESRGAN_x4plus.pth
│  └─ RealESRGAN_x4plus_anime_6B.pth
├─ requirements.txt            # Pillow, numpy
└─ requirements-ai.txt         # torch, torchvision, basicsr, realesrgan, opencv-python
```

---

## 9. Model AI

| Model | Arsitektur | Blok | Peruntukan |
| --- | --- | --- | --- |
| `RealESRGAN_x4plus.pth` | RRDBNet | 23 | Umum: foto, background, ornamen, objek metalik, gradasi (default) |
| `RealESRGAN_x4plus_anime_6B.pth` | RRDBNet | 6 | Ilustrasi / anime |

Arsitektur dan jumlah blok **dibaca dari isi file `.pth`** dan divalidasi terhadap checkpoint sebelum inferensi, sehingga label manual yang keliru tidak akan merusak hasil.

---

## 10. Troubleshooting

- **"CUDA not available"** — pastikan GPU NVIDIA + driver terpasang dan PyTorch build ber-CUDA (lihat bagian 3.2).
- **Out of Memory (VRAM)** — turunkan **Tile size (AI)** (mis. 128) atau kurangi AI Strength.
- **Warna bergeser** — pengaturan bawaan sudah menyematkan sRGB IEC61966-2.1; pastikan `assets/sRGB_IEC61966-2.1.icc` ada.
- **PSD tidak terbuka** — file PSD ditulis sebagai RGB 8-bit tanpa layer; pastikan aplikasi pembaca mendukung PSD dasar.

---

## 11. Lisensi & Kredit

- Real-ESRGAN — https://github.com/xinntao/Real-ESRGAN
- BasicSR — https://github.com/XPixelGroup/BasicSR
- Pillow — https://python-pillow.org
