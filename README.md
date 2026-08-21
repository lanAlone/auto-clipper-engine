# Auto-Clipper Engine (Layer Compute - GitHub Actions)

Repositori publik untuk mengeksekusi pipeline komputasi berat Auto-Clipper menggunakan GitHub Actions (Compute Minutes Unlimited & Gratis).

### Pipeline Stages:
1. **Stage 1: Download & Audio Optimization (`download.py`)** — 4-Tier Stealth Downloader (yt-dlp, PO-Token, CloakBrowser, BYOC Cookies) + Downsample 16kHz Mono 32kbps MP3.
2. **Stage 2: Transkripsi (`transcribe.py`)** — Ekstrak Subtitle YouTube Native (0 API cost) atau Groq Whisper (`whisper-large-v3-turbo`).
3. **Stage 3: Deteksi Momen (`detect_highlights.py`)** — Rotasi Multi-LLM Otomatis + Word-Level Snapping (+0.2s padding).
4. **Stage 4: Remotion Props (`prep_render_props.py`)** — Frame calculation, speech-aware ducking cues, & captions.
5. **Stage 5: Rendering 9:16 (`render.py`)** — Remotion Headless CLI dengan mode Blurred Stack & Center Crop (`--concurrency=1`, `--gl=angle`).
6. **Stage 6: Upload (`upload.py`)** — Push MP4 ke Hugging Face Dataset dengan Exponential Backoff Retry.
