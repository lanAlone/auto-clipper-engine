"""
Downloader Module (Lightweight Two-Phase & Cloudflare WARP Residential Bypass)
Mendukung video podcast YouTube hingga 3 JAM (10.800 detik).
Menggunakan Cloudflare WARP proxy + multi-client Android/iOS/TV untuk 100% bypass Botguard.
"""

import os
import sys
import subprocess
import re
import json
from typing import Tuple, Optional, List, Dict, Any

from pipeline.fetch_user_key import get_user_cookie_file
from pipeline.stealth_session import generate_youtube_session_cookies
from pipeline.invidious_proxy import download_audio_via_invidious, download_video_section_via_invidious
from pipeline.playwright_extractor import get_stream_url_sync


MAX_DURATION_SECONDS = 10800  # 3 Jam Penuh (Podcast Panjang)
WARP_PROXY = "socks5://127.0.0.1:40000"


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
    return "video_" + re.sub(r"[^a-zA-Z0-9]", "_", url)[-8:]


def check_video_metadata(url: str, cookie_file: Optional[str] = None) -> Tuple[bool, float, str, str]:
    """
    Mengambil durasi & judul video tanpa mengunduh konten (pre-flight check).
    """
    video_id = extract_video_id(url)
    clients = [
        "youtube:player_client=android_creator,android",
        "youtube:player_client=ios",
        "youtube:player_client=tv_embedded,tv",
        "youtube:player_client=mweb"
    ]

    import shutil
    node_path = shutil.which("node") or "node"
    
    for client_arg in clients:
        for use_proxy in [True, False]:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--skip-download",
                "--print", "%(duration)s|||%(title)s",
                "--no-warnings",
                "--js-runtimes", f"nodejs:{node_path}",
                "--extractor-args", client_arg
            ]
            if use_proxy:
                cmd.extend(["--proxy", WARP_PROXY])
            if cookie_file and os.path.exists(cookie_file):
                cmd.extend(["--cookies", cookie_file])
            cmd.append(url)

            code, out, err = run_cmd(cmd, timeout_sec=30)
            if code == 0 and "|||" in out:
                parts = out.strip().split("|||")
                dur_str = parts[0].strip() if len(parts) > 0 else "0"
                title = parts[1].strip() if len(parts) > 1 else f"YouTube Video {video_id}"
                try:
                    dur = float(dur_str)
                except ValueError:
                    dur = 0.0

                if dur > MAX_DURATION_SECONDS:
                    hours = round(dur / 3600, 1)
                    return False, dur, title, f"Durasi video ({hours} jam) melebihi batas maksimum 3 jam."
                return True, dur, title, ""

    print(f"[Warning] Pre-flight metadata dilewati, melanjutkan langsung ke ekstraksi audio.")
    return True, 1800.0, f"YouTube Video {video_id}", ""


def downsample_audio_for_groq(input_audio_or_video: str, output_audio_path: str) -> bool:
    """
    Mengekstrak audio menjadi MP3 16kHz Mono 32kbps.
    Ukuran file hanya ~14MB per jam (sangat hemat bandwidth & Groq Whisper compatible).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_audio_or_video,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "32k",
        "-f", "mp3",
        output_audio_path
    ]
    code, out, err = run_cmd(cmd, timeout_sec=180)
    return code == 0 and os.path.exists(output_audio_path)


def download_audio_and_subtitles(
    url: str,
    user_id: str,
    output_dir: str = "work/media"
) -> Tuple[str, str, float, Optional[str]]:
    """
    FASE 1: Unduh HANYA audio ringan dan subtitle WebVTT untuk transkripsi.
    Mengembalikan (audio_whisper_path, video_id, duration_sec, subtitle_vtt_path).
    """
    os.makedirs(output_dir, exist_ok=True)
    video_id = extract_video_id(url)
    audio_raw_template = os.path.join(output_dir, f"{video_id}_raw.%(ext)s")
    audio_whisper_path = os.path.join(output_dir, f"{video_id}_whisper.mp3")
    sub_id_vtt = os.path.join(output_dir, f"{video_id}.id.vtt")
    sub_en_vtt = os.path.join(output_dir, f"{video_id}.en.vtt")

    user_cookie_file = None
    try:
        user_cookie_file = get_user_cookie_file(user_id)
    except Exception as e:
        print(f"[Info] Status cookie user: {e}")

    # Validasi Durasi & Metadata
    is_valid, duration_sec, title, dur_err = check_video_metadata(url, cookie_file=user_cookie_file)
    if not is_valid and "melebihi batas" in dur_err:
        raise ValueError(dur_err)

    print(f"[Downloader] Memproses video: '{title}' ({duration_sec:.1f} detik)...")

    import shutil
    node_path = shutil.which("node") or "node"

    base_args = [
        sys.executable, "-m", "yt_dlp",
        "--format", "bestaudio/best",
        "-o", audio_raw_template,
        "--no-playlist",
        "--force-ipv4",
        "--js-runtimes", f"nodejs:{node_path}"
    ]

    tier_errors = []
    download_success = False
    raw_audio_path = ""

    # Strategy: Loop through WARP proxy & direct with different player clients
    # With yt-dlp >= 2025, tv, ios, and mweb are the most resilient against botguard
    strategies = [
        ("Tier 1 (WARP + iOS)", [WARP_PROXY], "youtube:player_client=ios"),
        ("Tier 2 (WARP + Android Creator)", [WARP_PROXY], "youtube:player_client=android_creator"),
        ("Tier 3 (WARP + Web Creator)", [WARP_PROXY], "youtube:player_client=web_creator"),
        ("Tier 4 (Direct + iOS)", [], "youtube:player_client=ios"),
        ("Tier 5 (Direct + Android Creator)", [], "youtube:player_client=android_creator"),
        ("Tier 6 (Direct + Default)", [], "youtube:player_client=default")
    ]

    for label, proxy_opts, client_arg in strategies:
        print(f"[Downloader] Mencoba {label}...")
        cmd = list(base_args)
        if proxy_opts:
            cmd.extend(["--proxy", proxy_opts[0]])
        cmd.extend(["--extractor-args", client_arg])
        if user_cookie_file:
            cmd.extend(["--cookies", user_cookie_file])
        cmd.append(url)

        code, out, err = run_cmd(cmd, timeout_sec=180)
        raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
        if code == 0 and raw_files:
            download_success = True
            raw_audio_path = raw_files[0]
            print(f"[Downloader] SUKSES mengunduh audio via {label}!")
            break
        else:
            tier_errors.append(f"{label}: {err[-300:].strip().replace(chr(10), ' ')}")

    # Fallback to Playwright Embed Cookies if still blocked
    if not download_success:
        print("[Downloader] Mencoba Playwright Embed Session Handshake...")
        stealth_cookie = generate_youtube_session_cookies(video_id)
        if stealth_cookie and os.path.exists(stealth_cookie):
            cmd = base_args + [
                "--cookies", stealth_cookie,
                "--extractor-args", "youtube:player_client=android,ios,mweb",
                url
            ]
            code5, out5, err5 = run_cmd(cmd, timeout_sec=180)
            raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
            if code5 == 0 and raw_files:
                download_success = True
                raw_audio_path = raw_files[0]
                print("[Downloader] SUKSES mengunduh audio via Playwright Embed Session!")

    # Fallback Tier 8: Playwright Native Stream Intercept
    if not download_success:
        print("[Downloader] Mencoba Tier 8: Playwright Native Stream Intercept...")
        raw_audio_path = os.path.join(output_dir, f"{video_id}_raw_pw.m4a")
        stream_url = get_stream_url_sync(url, user_cookie_file)
        if stream_url:
            print(f"[Downloader] Stream URL Ditemukan! Mengunduh dengan ffmpeg...")
            cmd = ["ffmpeg", "-y", "-i", stream_url, "-c", "copy", raw_audio_path]
            code, out, err = run_cmd(cmd, timeout_sec=300)
            if code == 0 and os.path.exists(raw_audio_path) and os.path.getsize(raw_audio_path) > 100000:
                download_success = True
                print("[Downloader] SUKSES mengunduh audio via Playwright Native Intercept!")
            else:
                print(f"[Downloader] Gagal mengunduh stream URL dengan ffmpeg: {err[-100:]}")

    # Fallback to Invidious Proxy Stream (Tier 9 - Ultimate Cloud Bypass)
    if not download_success:
        print("[Downloader] Mencoba Tier 9: Invidious API Proxy Stream (Bypass 403)...")
        raw_audio_path = os.path.join(output_dir, f"{video_id}_raw_proxy.m4a")
        if download_audio_via_invidious(video_id, raw_audio_path):
            download_success = True
            print("[Downloader] SUKSES mengunduh audio via Invidious Proxy Stream!")
            
    if not download_success:
        err_msg = " | ".join(tier_errors)
        raise RuntimeError(f"Gagal mengunduh audio stream dari YouTube ({err_msg}).")

    # Ekstrak audio 16kHz 32kbps mono untuk Whisper
    downsampled = downsample_audio_for_groq(raw_audio_path, audio_whisper_path)
    if not downsampled:
        audio_whisper_path = raw_audio_path

    # Cek Subtitle VTT
    found_sub = None
    if os.path.exists(sub_id_vtt):
        found_sub = sub_id_vtt
    elif os.path.exists(sub_en_vtt):
        found_sub = sub_en_vtt

    return audio_whisper_path, video_id, duration_sec, found_sub


def download_clip_section(
    url: str,
    user_id: str,
    clip_id: str,
    start_sec: float,
    end_sec: float,
    output_dir: str = "work/media"
) -> str:
    """
    FASE 2: Mengunduh HANYA potongan video 30-60 detik yang terpilih untuk rendering.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_mp4_path = os.path.join(output_dir, f"section_{clip_id}.mp4")

    if os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 100000:
        return out_mp4_path

    def sec_to_ts(s):
        m, sec = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"

    ts_start = sec_to_ts(max(0.0, start_sec - 0.5))
    ts_end = sec_to_ts(end_sec + 0.5)

    user_cookie_file = None
    try:
        user_cookie_file = get_user_cookie_file(user_id)
    except Exception:
        pass

    section_spec = f"*{ts_start}-{ts_end}"
    print(f"[Downloader] Mengunduh segmen video '{clip_id}': rentang {ts_start} -> {ts_end}...")

    strategies = [
        (WARP_PROXY, "youtube:player_client=ios"),
        (WARP_PROXY, "youtube:player_client=android_creator"),
        (WARP_PROXY, "youtube:player_client=web_creator"),
        (None, "youtube:player_client=ios"),
        (None, "youtube:player_client=android_creator"),
        (None, "youtube:player_client=web_creator")
    ]

    for proxy, client_arg in strategies:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--download-sections", section_spec,
            "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--force-keyframes-at-cuts",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--extractor-args", client_arg,
            "-o", out_mp4_path
        ]
        if proxy:
            cmd.extend(["--proxy", proxy])
        if user_cookie_file:
            cmd.extend(["--cookies", user_cookie_file])
        cmd.append(url)

        code, out, err = run_cmd(cmd, timeout_sec=180)
        if code == 0 and os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 50000:
            print(f"[Downloader] Sukses mengunduh segmen {clip_id} (Proxy: {bool(proxy)}, Client: {client_arg})!")
            return out_mp4_path

    # Fallback Tier 8: Playwright Native Stream
    print(f"[Downloader] Mencoba Tier 8 untuk segmen {clip_id}: Playwright Native Stream Intercept...")
    stream_url = get_stream_url_sync(url, user_cookie_file)
    if stream_url:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, start_sec - 0.5)),
            "-i", stream_url,
            "-t", str((end_sec - start_sec) + 1.0),
            "-c", "copy",
            out_mp4_path
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if proc.returncode == 0 and os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 50000:
            print(f"[Downloader] Sukses mengunduh segmen {clip_id} via Playwright Native!")
            return out_mp4_path

    # Fallback Tier 9 untuk Video
    print(f"[Downloader] Mencoba Tier 9 untuk segmen {clip_id}: Invidious Proxy Video Stream...")
    if download_video_section_via_invidious(video_id, start_sec, end_sec, out_mp4_path):
        print(f"[Downloader] Sukses mengunduh segmen {clip_id} via Invidious Proxy!")
        return out_mp4_path

    raise RuntimeError(f"Gagal mengunduh klip segmen {clip_id} setelah mencoba seluruh strategi WARP, Direct, dan Proxy.")
