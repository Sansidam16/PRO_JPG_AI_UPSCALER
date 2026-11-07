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

### 4.1 Versi Portable (Windows)

Aplikasi dapat dibungkus menjadi **folder portable** (onedir) yang berisi runtime Python + PyTorch/CUDA, sehingga pengguna akhir **tidak perlu memasang Python**. Artefak hasil build:

- Folder portable: `dist/PRO_JPG_AI_UPSCALER/`
- Arsip distribusi: `dist/PRO_JPG_AI_UPSCALER_portable_win64.zip`

Struktur paket portable:

```
PRO_JPG_AI_UPSCALER/
├─ PRO_JPG_AI_UPSCALER.exe   # jalankan ini (klik dua kali)
├─ _internal/                # runtime + PyTorch/CUDA (jangan diubah)
├─ models/                   # model .pth (dapat ditambah/diganti sendiri)
├─ assets/                   # profil sRGB IEC61966-2.1
├─ config/                   # settings.json (pengaturan tersimpan)
└─ logs/
```

Cara pakai: ekstrak ZIP, lalu jalankan `PRO_JPG_AI_UPSCALER.exe`. Semua data (pengaturan, log, model) berada **di samping exe**, sehingga paket benar-benar portable (dapat dijalankan dari flashdisk).

- Untuk fitur AI, PC tujuan tetap memerlukan **GPU NVIDIA + driver** (CUDA 12.4 sudah dibundel). Engine Standard dapat dipakai tanpa GPU.
- Ukuran besar (±4,1 GB) berasal dari library PyTorch + CUDA dan model.

Build ulang:

```bat
.venv\Scripts\python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --name PRO_JPG_AI_UPSCALER ^
    --collect-all realesrgan --collect-all basicsr --collect-all cv2 ^
    --hidden-import torch --hidden-import torchvision main.py
```

Setelah build, salin `models/`, `assets/`, dan `config/` ke dalam `dist/PRO_JPG_AI_UPSCALER/`. Folder `build/` dan `dist/` diabaikan oleh Git (lihat `.gitignore`).

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

Mengatur ke mana dan bagaimana gambar hasil ditulis.

| Kontrol | Fungsi | Catatan / Pengaruh |
| --- | --- | --- |
| **Engine** | `AI` (Real-ESRGAN + Lanczos blending) atau `Standard` (hanya resize Lanczos/Bicubic, tanpa GPU). | Tidak memengaruhi ukuran file. |
| **AI Model** | Pilih model dari folder `models/`. Daftar dimuat dinamis. | `RealESRGAN_x4plus` untuk foto/umum; `..._anime_6B` untuk ilustrasi. |
| **Output preset** | Ukuran target: 1920×600, 1920×700, 1920×900, 3543×4961, 4961×3543, atau Custom. | Memilih preset otomatis mengisi Width/Height. |
| **Resize mode** | Exact Canvas, Preserve Aspect Ratio, Fit, Crop, Stretch. | Exact Canvas/Fit = seluruh gambar + isi sisa kanvas; Preserve Aspect Ratio = rasio asli tanpa padding/crop; Crop = penuhi target lalu potong tengah; Stretch = ubah rasio agar pas target. |
| **Canvas fill** | Pengisian sisa kanvas (Exact Canvas/Fit): **Edge Extension** (default) atau Background Color. | Edge Extension (replikasi piksel tepi) menghasilkan area datar yang mengompres lebih efisien. |
| **Background (hex)** | Warna latar, contoh `#FFFFFF`. | Hanya dipakai bila Canvas fill = Background Color. |
| **Width / Height (px)** | Dimensi target manual (16–20000). Mengubahnya otomatis mengeset preset ke `Custom`. | **Faktor terbesar penentu ukuran file.** |
| **Standard filter** | Filter resize Standar/baseline: Lanczos (tajam) atau Bicubic (halus). | Dipakai juga untuk baseline yang dicampur dengan hasil AI. |
| **Tile size (AI)** | Ukuran tile inferensi (128–512). | Tile lebih kecil menurunkan pemakaian VRAM (aman untuk GPU kecil); tidak mengubah hasil akhir maupun ukuran file. |
| **JPEG Quality** | 95 / 98 / 100. | **Berpengaruh besar** ke ukuran file (95 → 100 bisa +1,5–2,5×). |
| **Chroma subsampling** | 4:4:4 (warna penuh) / 4:2:2 / 4:2:0. | 4:4:4 = file terbesar; 4:2:0 ±20–40% lebih kecil. Untuk kualitas tinggi gunakan 4:4:4. |
| **DPI 300 x 300** | Tetap (label). Metadata resolusi cetak output. | **Metadata saja** — tidak menambah jumlah piksel, hampir tidak memengaruhi ukuran file. |
| **Nama = file asli** | Jika dicentang, output memakai nama file asli; jika tidak, ditambah `_PRO_UPSCALED`. | Tidak memengaruhi ukuran file. |
| **Simpan PSD** | Jika dicentang, selain JPG juga menyimpan PSD 8-bit RGB (kompresi RLE PackBits). | Menambah file kedua; PSD jauh lebih besar daripada JPG (5–15×). |
| **Skip yang sudah ada** | Lewati file yang output JPG-nya sudah ada. | Menghemat waktu saat batch diulang. |
| **Suara selesai** | Bunyi penanda saat proses batch selesai. | Nada chime 880 Hz → 1175 Hz. |

### 5.5 Tab "AI & Quality"

Mengatur seberapa kuat AI dan penajaman diterapkan pada hasil akhir.

| Kontrol | Fungsi | Catatan / Pengaruh |
| --- | --- | --- |
| **AI Strength (%)** | Bobot hasil AI (0–100): `Final = (1−α)·Lanczos + α·AI`. | 0 = murni Lanczos, 100 = murni AI. |
| **AI Strength preset** | Conservative 20 / Balanced 30 / Enhanced 50 / Full AI 100 / Custom. | Pintasan untuk mengisi AI Strength. |
| **Detail Enhancement** | Off / Low / Medium / High. | Digabung ke **satu pass** dengan sharpening (menambah radius & kekuatan). |
| **Noise Reduction** | Off / Low / Medium / High (bawaan Off). | Diterapkan pada sumber sebelum upscaling; level tinggi bisa menghilangkan tekstur halus. |
| **Sharpening Amount** | Kekuatan sharpening tambahan (0–300). | Ditambahkan di atas Detail Enhancement (total dibatasi 300%). Default 8. |
| **Sharpening Radius** | Radius pada resolusi referensi 2048 px (0.1–5.0); diskalakan ke dimensi output. | **Sadar-dimensi**: dibatasi 0.3–3.0 px setelah skala. Default 0.6. |
| **Sharpening Threshold** | Ambang minimum detail yang diperkuat (0–50). | Lebih tinggi = hanya tepi kuat yang dipertajam; area datar/gradasi/bokeh terlindungi (anti-halo). Default 4. |

> Catatan: sharpening bersifat *edge-aware* (menggunakan edge mask + protection mask) sehingga area gradasi/bokeh tidak tersentuh; lihat bagian 7.

### 5.6 Tombol Aksi

- **START PROCESSING** — mulai batch. Tombol dinonaktifkan saat proses berjalan.
- **CANCEL** — berhenti setelah gambar yang sedang diproses selesai.
- **Save Preset** — simpan pengaturan saat ini ke `config/settings.json`.
- **Open Output Folder** — buka folder output di File Explorer.

### 5.7 Panel Bawah

- **Progress** — status teks, progress bar, dan hitungan `berhasil / gagal`.
- **Processing Log** — catatan langkah proses per gambar, ringkasan waktu, arsitektur model, dsb.

### 5.8 Ukuran File Output

Ukuran file hasil ditentukan oleh beberapa faktor, dari yang paling berpengaruh:

1. **Dimensi output (Width × Height)** — faktor dominan. Mis. 4961×3543 ≈ 17,6 MP, jauh lebih besar daripada 1920×1080.
2. **Simpan PSD diaktifkan** — menambah file kedua yang jauh lebih besar daripada JPG.
3. **JPEG Quality** — 95 → 100 dapat menaikkan ukuran sekitar 1,5–2,5×.
4. **Chroma subsampling** — `4:4:4` paling besar, `4:2:0` sekitar 20–40% lebih kecil.
5. **Kompleksitas isi gambar** — foto bertekstur/noise tinggi menghasilkan file lebih besar daripada latar polos. Noise Reduction sedikit mengecilkan file; sharpening yang menambah detail halus memperbesar file.
6. **Resize mode & Canvas fill** — area datar (Edge Extension) mengompres jauh lebih efisien daripada `Stretch` yang mengubah seluruh piksel.

Tidak memengaruhi ukuran file: **DPI** (metadata), **Nama = file asli**, **Tile size**, **AI Strength**, dan pilihan **Engine**.

Semua JPG otomatis memakai `optimize=True` + `progressive=True`, serta disematkan profil `sRGB IEC61966-2.1`.

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
