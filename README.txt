PRO JPG AI UPSCALER — SOURCE PROJECT
====================================

IMPORTANT: This is the first development build. Test the Python version before
packaging it as a portable EXE.

1. FEATURES
-----------
- Tkinter desktop GUI
- Batch JPG/JPEG processing (top-level folder only), daftar file ditampilkan
  dengan checkbox sehingga dapat memilih file tertentu (satuan) atau semua file
- Standard engine: Lanczos / Bicubic
- Optional AI engine: Real-ESRGAN x4plus (default, general-purpose: foto,
  background, ornamen) dan Anime 6B (khusus ilustrasi/anime) — CUDA
- Conservative AI Super Resolution pipeline:
  Lanczos baseline -> Real-ESRGAN x4 -> Lanczos ke target -> AI strength blending
  -> conservative enhancement -> sRGB -> JPEG -> validasi
- AI Strength 0-100% (preset: Conservative 20 / Balanced 30 / Enhanced 50 / Full AI 100)
- Detail Enhancement: Off / Low / Medium / High
- Noise Reduction: Off / Low / Medium / High
- Sharpening: Amount / Radius / Threshold dengan edge-aware masking (hanya tepi
  kuat yang dipertajam; gradasi halus, bokeh, dan bayangan lembut dilindungi)
  dan anti-halo. Radius bersifat sadar-dimensi: nilai berlaku pada resolusi
  referensi 2048 px lalu diskalakan ke dimensi output (dibatasi 0.3-3.0 px).
  Default ringan: Amount 8 / Radius 0.6 / Threshold 4.
- Color management: konversi ICC sumber ke sRGB + menyematkan profil
  sRGB IEC61966-2.1 di output (JPG dan PSD)
- Output presets:
  1920 x 600
  1920 x 700
  1920 x 900
  3543 x 4961
  4961 x 3543
  Custom (Width / Height manual)
- Output geometry: Exact Canvas / Preserve Aspect Ratio / Fit / Crop / Stretch
- Canvas fill untuk Exact Canvas / Fit: Edge Extension (default) atau warna
  background. White padding bukan satu-satunya pilihan.
- Output format: JPG selalu, PSD 8-bit RGB opsional
- Opsi penamaan output: nama file asli atau akhiran `_PRO_UPSCALED`
- JPEG quality 95 / 98 / 100 (default 98), Chroma subsampling 4:4:4 / 4:2:2 / 4:2:0
- 300 DPI metadata, RGB output
- Laporan validasi `upscale_report.csv` di folder output (mencatat sumber/output
  dimensi, AI intermediate, nama file model, arsitektur, jumlah RRDB block,
  status validasi checkpoint, device CUDA, presisi FP16/FP32, tile, AI strength,
  parameter sharpening (amount/radius/threshold), ICC, DPI, ukuran file, dan
  status). Waktu dipecah menjadi preprocessing, AI, resize, blending,
  enhancement, export, dan total (komponen-komponennya saling eksklusif
  sehingga dapat dijumlahkan).
- No overwrite of existing output files; opsi skip file yang sudah ada
- AI policy selected by user:
  If the source already has enough pixels for the selected target geometry,
  skip AI and resize/downsample with Lanczos. If enlargement is needed, use AI
  x4 and then resize to exact final dimensions with Lanczos.

2. PYTHON VERSION
-----------------
Recommended: Python 3.11 or 3.12, 64-bit.
Use a virtual environment.

Open CMD in this project folder:

    py -3.12 -m venv .venv
    .venv\Scripts\activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

Standard Engine does not require PyTorch.

Run Standard Engine:

    python main.py

3. AI ENGINE INSTALLATION
-------------------------
AI dependencies are sensitive to Python, PyTorch, torchvision, and CUDA versions.
Do not blindly install a CPU-only PyTorch build.

A. Install a CUDA-enabled PyTorch + torchvision build using the official selector:
   https://pytorch.org/get-started/locally/

B. Verify CUDA:

    python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"

Expected: True and NVIDIA GeForce RTX 4060 Laptop GPU.

C. Install Real-ESRGAN dependencies using the official repository instructions:
   https://github.com/xinntao/Real-ESRGAN

Compatibility note:
Some BasicSR / torchvision combinations have import incompatibilities.
If installation fails, use a clean virtual environment and follow the
repository's currently supported installation instructions. Do not randomly
upgrade torchvision after installing the AI stack.

4. MODEL FILES
--------------
Place model weights in this folder:

    models\RealESRGAN_x4plus.pth
    models\RealESRGAN_x4plus_anime_6B.pth

Official project:
    https://github.com/xinntao/Real-ESRGAN

Download the matching pretrained weights from the official project's releases
or model links. The application does not silently download model files.

Catatan: arsitektur model dideteksi otomatis dari isi file .pth (RRDBNet vs
SRVGGNetCompact) beserta jumlah blok dan skala, sehingga aplikasi tetap dapat
memuat model meskipun nama file tidak sesuai. Checkpoint divalidasi secara
strict terhadap arsitektur yang dibangun; kombinasi arsitektur + bobot yang
tidak cocok akan ditolak dengan pesan jelas (bukan hasil yang salah diam-diam).

Contoh hasil deteksi:
- RealESRGAN_x4plus.pth          -> RRDBNet x4 (23 blocks), general-purpose
- RealESRGAN_x4plus_anime_6B.pth -> RRDBNet x4 (6 blocks), anime/ilustrasi

5. GPU / MEMORY SETTINGS
------------------------
For RTX 4060 Laptop GPU 8 GB and system RAM 16 GB:
- Start with tile 256.
- Use FP16.
- Process one image at a time.
- If CUDA Out of Memory occurs, the engine retries with smaller tiles.
- Avoid running other GPU-heavy applications during large jobs.

6. BUILD PORTABLE EXE
---------------------
Install PyInstaller in the same virtual environment:

    python -m pip install pyinstaller

Build:

    python -m PyInstaller --noconfirm --clean --onedir --windowed ^
      --name PRO_JPG_AI_UPSCALER ^
      --collect-all realesrgan ^
      --collect-all basicsr ^
      --collect-all torch ^
      --collect-all torchvision ^
      main.py

For a Standard-only build without AI dependencies:

    python -m PyInstaller --noconfirm --clean --onedir --windowed ^
      --name PRO_JPG_AI_UPSCALER main.py

Copy the models folder, config folder, and logs folder beside the EXE.
Final portable structure:

    PRO_JPG_AI_UPSCALER\
      PRO_JPG_AI_UPSCALER.exe
      models\
      config\
      logs\

7. IMPORTANT IMAGE NOTES
------------------------
- 300 DPI is metadata; it does not create additional pixels.
- AI may reconstruct or invent details. Inspect text, logos, faces, and
  geometric patterns before submitting stock assets.
- Preserve Aspect Ratio mempertahankan seluruh gambar tanpa crop/stretch;
  ukuran akhir mengikuti rasio sumber (mis. sumber 2432 x 1728 dengan target
  width 4961 menghasilkan ~4961 x 3525, bukan 4961 x 3543).
- Exact Canvas mempertahankan seluruh gambar; sisa kanvas diisi Edge Extension
  (default) atau warna background, bukan hanya white padding.
- Fit mirip Exact Canvas tetapi tanpa memaksa ukuran target.
- Crop fills the canvas and cuts off excess edges.
- Stretch changes the aspect ratio.
- This application does not modify source files.
- Source scanning is not recursive in this first build.

8. CURRENT DEVELOPMENT LIMITATIONS
----------------------------------
- Preview / before-after comparison is planned for the next iteration.
- GPU telemetry and persistent job history are planned.
- ICC conversion berjalan saat gambar sumber memiliki profil; gambar tanpa
  profil dianggap sudah sRGB dan tetap disematkan profil sRGB pada output.
- The app currently uses a sequential worker and one AI inference at a time.
