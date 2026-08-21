"""
Downloader Module (4-Tier Stealth Download & Audio Optimizer)
Mengunduh video YouTube dengan perlindungan multi-tier anti-bot,
memeriksa batasan durasi (max 45m), dan mengekstrak audio 16kHz 32kbps mono untuk Groq.
"""

import os
import subprocess
import re
import json
from typing import Tuple, Optional

from pipeline.fetch_user_key import get_user_cookie_file
from pipeline.stealth_session import get_stealth_cookies_file


MAX_DURATION_SECONDS = 2700  # 45 Menit


def run_cmd(cmd_list: list, timeout_sec: int = 300) -> Tuple[int, str, str]:
    """Menjalankan subprocess dengan timeout dan penangkapan output."""
    try:
        proc = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout melebihi {timeout_sec} detik"
    except Exception as e:
        return -1, "", str(e)


def extract_video_id(url: str) -> str:
    """Mengekstrak 11-karakter YouTube Video ID dari berbagai format URL."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:shorts\/)([0-9A-Za-z_-]{11})"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    # Fallback
    return "video_" + re.sub(r"[^a-zA-Z0-9]", "_", url)[-8:]


def check_video_metadata(url: str, cookie_file: Optional[str] = None) -> Tuple[bool, float, str, str]:
    """
    Mengambil durasi & judul video tanpa mengunduh konten (pre-flight check).
    Mengembalikan (is_valid, duration_seconds, title, error_msg).
    """
    cmd = ["yt-dlp", "--skip-download", "--print", "%(duration)s|||%(title)s", "--no-warnings"]
    if cookie_file and os.path.exists(cookie_file):
        cmd.extend(["--cookies", cookie_file])
    cmd.append(url)

    code, out, err = run_cmd(cmd, timeout_sec=40)
    if code != 0 or not out.strip():
        # Coba lagi dengan client android
        cmd_alt = ["yt-dlp", "--skip-download", "--print", "%(duration)s|||%(title)s", "--extractor-args", "youtube:player_client=android", url]
        code_alt, out_alt, err_alt = run_cmd(cmd_alt, timeout_sec=40)
        if code_alt != 0 or not out_alt.strip():
            return False, 0.0, "", f"Gagal membaca informasi video: {err or err_alt}"
        out = out_alt

    parts = out.strip().split("|||")
    dur_str = parts[0].strip() if len(parts) > 0 else "0"
    title = parts[1].strip() if len(parts) > 1 else "YouTube Video"

    try:
        dur = float(dur_str)
    except ValueError:
        dur = 0.0

    if dur > MAX_DURATION_SECONDS:
        mins = int(dur // 60)
        return False, dur, title, f"Durasi video ({mins} menit) melebihi batas maksimum 45 menit untuk tier gratis."

    return True, dur, title, ""


def downsample_audio_for_groq(input_video_path: str, output_audio_path: str) -> bool:
    """
    Mengekstrak audio menjadi MP3 16kHz Mono 32kbps.
    Ukuran file menjadi sangat kecil (~14MB per jam), anti-error 413 Groq 25MB.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "32k",
        "-f", "mp3",
        output_audio_path
    ]
    code, out, err = run_cmd(cmd, timeout_sec=120)
    return code == 0 and os.path.exists(output_audio_path)


def download_video(
    url: str,
    user_id: str,
    output_dir: str = "work"
) -> Tuple[str, str, str, float, Optional[str]]:
    """
    Eksekusi 4-Tier Stealth Download.
    Mengembalikan: (video_path, audio_whisper_path, video_id, duration_sec, subtitle_vtt_path)
    """
    os.makedirs(output_dir, exist_ok=True)
    video_id = extract_video_id(url)
    video_out_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    video_mp4_path = os.path.join(output_dir, f"{video_id}.mp4")
    audio_mp3_path = os.path.join(output_dir, f"{video_id}_whisper.mp3")
    sub_vtt_path = os.path.join(output_dir, f"{video_id}.id.vtt")
    sub_en_vtt_path = os.path.join(output_dir, f"{video_id}.en.vtt")

    # 1. Cek kredensial cookie user (Tier 4)
    user_cookie_file = None
    try:
        user_cookie_file = get_user_cookie_file(user_id)
    except Exception as e:
        print(f"[Info] Tidak ada cookie BYOC: {e}")

    # 2. Validasi Durasi & Pre-flight
    is_valid, duration_sec, title, dur_err = check_video_metadata(url, cookie_file=user_cookie_file)
    if not is_valid and "melebihi batas" in dur_err:
        raise ValueError(dur_err)

    # 3. Eksekusi 4-Tier Download
    tier_errors = []

    # Format download: 720p/1080p MP4 + ambil subtitle otomatis jika ada
    base_args = [
        "yt-dlp",
        "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--write-auto-sub", "--sub-lang", "id,en",
        "--sub-format", "vtt",
        "-o", video_out_template,
        "--no-playlist"
    ]

    download_success = False

    # TIER 1: Direct Android/iOS Spoofing
    tier1_args = base_args + ["--extractor-args", "youtube:player_client=android,ios,tv_embedded,web", url]
    if user_cookie_file:
        tier1_args.extend(["--cookies", user_cookie_file])
    
    code1, out1, err1 = run_cmd(tier1_args, timeout_sec=240)
    if code1 == 0 and os.path.exists(video_mp4_path):
        download_success = True
        print("[Tier 1] Download berhasil via Android/iOS player client.")
    else:
        tier_errors.append(f"Tier 1: {err1[-120:].strip()}")

    # TIER 2: PO-Token / Client Fallback
    if not download_success:
        tier2_args = base_args + ["--extractor-args", "youtube:player_client=web,mweb", url]
        if user_cookie_file:
            tier2_args.extend(["--cookies", user_cookie_file])
        code2, out2, err2 = run_cmd(tier2_args, timeout_sec=240)
        if code2 == 0 and os.path.exists(video_mp4_path):
            download_success = True
            print("[Tier 2] Download berhasil via Web fallback.")
        else:
            tier_errors.append(f"Tier 2: {err2[-120:].strip()}")

    # TIER 3: CloakBrowser / Playwright Stealth Session
    if not download_success:
        print("[Tier 3] Memulai CloakBrowser Stealth Session...")
        stealth_cookie = get_stealth_cookies_file()
        if stealth_cookie:
            tier3_args = base_args + ["--cookies", stealth_cookie, url]
            code3, out3, err3 = run_cmd(tier3_args, timeout_sec=240)
            if code3 == 0 and os.path.exists(video_mp4_path):
                download_success = True
                print("[Tier 3] Download berhasil via CloakBrowser Stealth Session.")
            else:
                tier_errors.append(f"Tier 3: {err3[-120:].strip()}")

    # Jika semua tier gagal
    if not download_success or not os.path.exists(video_mp4_path):
        err_msg = " | ".join(tier_errors)
        if "Sign in to confirm" in err_msg or "bot" in err_msg.lower() or "age" in err_msg.lower():
            raise RuntimeError(
                "YouTube memblokir unduhan karena tantangan bot / pembatasan usia (18+). "
                "Silakan simpan Cookie YouTube Anda di Tab Pengaturan untuk membuka akses."
            )
        raise RuntimeError(f"Gagal mengunduh video: {err_msg}")

    # 4. Downsample Audio untuk Groq (16kHz 32kbps mono)
    print(f"[FFmpeg] Mengompres audio ke 16kHz 32kbps mono...")
    downsampled = downsample_audio_for_groq(video_mp4_path, audio_mp3_path)
    if not downsampled:
        raise RuntimeError("Gagal mengekstrak audio terkompresi dari video via FFmpeg.")

    # 5. Cek ketersediaan Subtitle VTT
    found_sub = None
    if os.path.exists(sub_vtt_path):
        found_sub = sub_vtt_path
    elif os.path.exists(sub_en_vtt_path):
        found_sub = sub_en_vtt_path

    return video_mp4_path, audio_mp3_path, video_id, duration_sec, found_sub
