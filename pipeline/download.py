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


def run_cmd(cmd_list: list, timeout_sec: int = 300, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """Menjalankan subprocess dengan timeout dan penangkapan output."""
    try:
        proc = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            env=env
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
                "--js-runtimes", f"node:{node_path}",
                "--remote-components", "ejs:github",
                "--extractor-args", client_arg
            ]
            if cookie_file and os.path.exists(cookie_file) and "ios" not in client_arg:
                cmd.extend(["--cookies", cookie_file])
            cmd.append(url)

            run_env = os.environ.copy()
            if use_proxy:
                run_env["HTTP_PROXY"] = WARP_PROXY
                run_env["HTTPS_PROXY"] = WARP_PROXY
                run_env["NO_PROXY"] = "127.0.0.1,localhost,::1"

            code, out, err = run_cmd(cmd, timeout_sec=30, env=run_env)
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
        if user_cookie_file and os.path.exists(user_cookie_file):
            print(f"[Downloader] Menggunakan Cookie otentikasi dari UI (Ukuran: {os.path.getsize(user_cookie_file)} bytes)")
        else:
            print("[Downloader] PERINGATAN: Tidak ada Cookie yang terdeteksi dari UI! YouTube berpotensi memblokir akses.")
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
        "--js-runtimes", f"node:{node_path}",
        "--remote-components", "ejs:github"
    ]

    tier_errors = []
    download_success = False
    raw_audio_path = ""

    # Strategy: Loop through WARP proxy with different player clients
    # Direct tiers have been removed as they are reliably blocked by YouTube
    strategies = [
        ("Tier 1 (WARP + iOS)", [WARP_PROXY], "youtube:player_client=ios"),
        ("Tier 2 (WARP + Android)", [WARP_PROXY], "youtube:player_client=android"),
        ("Tier 3 (WARP + TV/MWeb)", [WARP_PROXY], "youtube:player_client=tv,mweb"),
        ("Tier 4 (WARP + Default)", [WARP_PROXY], "youtube:player_client=default")
    ]

    for label, proxy_opts, client_arg in strategies:
        print(f"[Downloader] Mencoba {label}...")
        cmd = list(base_args)
        
        run_env = os.environ.copy()
        if proxy_opts:
            run_env["HTTP_PROXY"] = proxy_opts[0]
            run_env["HTTPS_PROXY"] = proxy_opts[0]
            run_env["NO_PROXY"] = "127.0.0.1,localhost,::1"
        
        cmd.extend(["--extractor-args", client_arg])
        
        # Batasi pemakaian PO token HANYA untuk client web-family
        if "ios" not in client_arg and "android" not in client_arg:
            cmd.extend(["--extractor-args", "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416"])
            
        # Hapus penerusan cookie untuk iOS dan Android karena ditolak secara eksplisit/memicu SABR
        if user_cookie_file and os.path.exists(user_cookie_file) and "ios" not in client_arg and "android" not in client_arg:
            cmd.extend(["--cookies", user_cookie_file])
            
        cmd.append(url)

        # DEBUG: Cetak argumen yt-dlp yang sebenarnya untuk memastikan cookie path disertakan
        cmd_safe_print = [c if "hf_" not in str(c) else "***" for c in cmd]
        print(f"[Debug] Command yt-dlp (Fase 1): {' '.join(cmd_safe_print)}")

        code, out, err = run_cmd(cmd, timeout_sec=180, env=run_env)
        raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
        if code == 0 and raw_files:
            download_success = True
            raw_audio_path = raw_files[0]
            print(f"[Downloader] SUKSES mengunduh audio via {label}!")
            break
        else:
            tier_errors.append(f"{label}: {err.strip().replace(chr(10), ' ')}")

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
    # DINONAKTIFKAN: Sangat tidak stabil di headless CI/CD dan rawan silent timeout
    # if not download_success:
    #     print("[Downloader] Mencoba Tier 8: Playwright Native Stream Intercept...")
    #     raw_audio_path = os.path.join(output_dir, f"{video_id}_raw_pw.m4a")
    #     stream_url = get_stream_url_sync(url, user_cookie_file)
    #     if stream_url:
    #         print(f"[Downloader] Stream URL Ditemukan! Mengunduh dengan ffmpeg...")
    #         cmd = ["ffmpeg", "-y", "-i", stream_url, "-c", "copy", raw_audio_path]
    #         code, out, err = run_cmd(cmd, timeout_sec=300)
    #         if code == 0 and os.path.exists(raw_audio_path) and os.path.getsize(raw_audio_path) > 100000:
    #             download_success = True
    #             print("[Downloader] SUKSES mengunduh audio via Playwright Native Intercept!")
    #         else:
    #             print(f"[Downloader] Gagal mengunduh stream URL dengan ffmpeg: {err[-100:]}")

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
    print("[Downloader] Mengekstrak audio ringan dari video lokal untuk Whisper...")
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
    video_id = extract_video_id(url)

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
        if user_cookie_file and os.path.exists(user_cookie_file):
            print(f"[Downloader] Menggunakan Cookie otentikasi dari UI (Ukuran: {os.path.getsize(user_cookie_file)} bytes)")
        else:
            print("[Downloader] PERINGATAN: Tidak ada Cookie yang terdeteksi dari UI! YouTube berpotensi memblokir akses.")
    except Exception as e:
        print(f"[Downloader] Gagal memuat cookie: {e}")

    # Direct tiers have been removed as they are reliably blocked by YouTube
    strategies = [
        ("Tier 1 (WARP + iOS)", [WARP_PROXY], "youtube:player_client=ios"),
        ("Tier 2 (WARP + Android)", [WARP_PROXY], "youtube:player_client=android"),
        ("Tier 3 (WARP + TV/MWeb)", [WARP_PROXY], "youtube:player_client=tv,mweb"),
        ("Tier 4 (WARP + Default)", [WARP_PROXY], "youtube:player_client=default")
    ]

    for label, proxy_opts, client_arg in strategies:
        # Pendelegasian penuh pemotongan ke yt-dlp untuk mencegah IP Mismatch & SABR
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--download-sections", f"*{start_sec}-{end_sec}",
            "--force-keyframes-at-cuts",
            "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--extractor-args", client_arg,
            "-o", out_mp4_path
        ]
        
        proxy = proxy_opts[0] if proxy_opts else None
        run_env = os.environ.copy()
        if proxy:
            run_env["HTTP_PROXY"] = proxy
            run_env["HTTPS_PROXY"] = proxy
            run_env["NO_PROXY"] = "127.0.0.1,localhost,::1"
            
        # Batasi pemakaian PO token HANYA untuk client web-family
        if "ios" not in client_arg and "android" not in client_arg:
            cmd.extend(["--extractor-args", "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416"])
        
        # Hapus penerusan cookie untuk iOS dan Android karena ditolak secara eksplisit/memicu SABR
        if user_cookie_file and os.path.exists(user_cookie_file) and "ios" not in client_arg and "android" not in client_arg:
            cmd.extend(["--cookies", user_cookie_file])
            
        cmd.append(url)
        
        # DEBUG print
        cmd_safe_print = [c if "hf_" not in str(c) else "***" for c in cmd]
        print(f"[Debug] Command yt-dlp (Fase 5 - {client_arg}): {' '.join(cmd_safe_print)}")

        print(f"[Downloader] Mengunduh & memotong segmen {clip_id} via yt-dlp (Proxy: {bool(proxy)})...")
        code, out, err = run_cmd(cmd, timeout_sec=300, env=run_env)
        
        if code == 0 and os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 50000:
            print(f"[Downloader] Sukses mengunduh klip {clip_id} (Proxy: {bool(proxy)}, Client: {client_arg})!")
            return out_mp4_path
        else:
            err_msg = err.strip()[-300:] if err else ''
            print(f"[Downloader] yt-dlp gagal (Proxy={bool(proxy)}). Code: {code}, Err: {err_msg}")

    # FALLBACK BARU: Full Video Lokal 
    print(f"[Downloader] --download-sections GAGAL semua. Memulai FALLBACK unduh FULL VIDEO untuk klip {clip_id}...")
    temp_full_video_path = out_mp4_path.replace(".mp4", "_full.mp4")
    
    cmd_fallback = [
        sys.executable, "-m", "yt_dlp",
        "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-o", temp_full_video_path
    ]
    
    proxy = WARP_PROXY
    run_env = os.environ.copy()
    if proxy:
        run_env["HTTP_PROXY"] = proxy
        run_env["HTTPS_PROXY"] = proxy
        run_env["NO_PROXY"] = "127.0.0.1,localhost,::1"

    # Gunakan TV/MWeb untuk fallback full video karena paling stabil
    cmd_fallback.extend(["--extractor-args", "youtube:player_client=tv,mweb"])
    cmd_fallback.extend(["--extractor-args", "youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416"])
    if user_cookie_file and os.path.exists(user_cookie_file):
        cmd_fallback.extend(["--cookies", user_cookie_file])
            
    cmd_fallback.append(url)
    
    cmd_safe_print = [c if "hf_" not in str(c) else "***" for c in cmd_fallback]
    print(f"[Debug] Command yt-dlp (Fase 5 - FALLBACK FULL VIDEO): {' '.join(cmd_safe_print)}")

    code, out, err = run_cmd(cmd_fallback, timeout_sec=1200, env=run_env) # 20 menit max
    if code == 0 and os.path.exists(temp_full_video_path) and os.path.getsize(temp_full_video_path) > 50000:
        print("[Downloader] Sukses mengunduh FULL VIDEO. Memotong segmen lokal dengan FFmpeg...")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, start_sec - 0.5)),
            "-i", temp_full_video_path,
            "-t", str((end_sec - start_sec) + 1.0),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out_mp4_path
        ]
        
        proc = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        
        # Hapus file full video
        try:
            os.remove(temp_full_video_path)
        except Exception:
            pass
            
        if proc.returncode == 0 and os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 50000:
            print(f"[Downloader] Sukses memotong segmen {clip_id} dari Full Video!")
            return out_mp4_path
        else:
            err_msg = proc.stderr.decode('utf-8', errors='ignore') if proc.stderr else ''
            print(f"[Downloader] FFmpeg potong lokal gagal. Code: {proc.returncode}. Err: {err_msg[-300:]}")
    else:
        err_msg = err.strip()[-300:] if err else ''
        print(f"[Downloader] Fallback unduh FULL VIDEO gagal. Code: {code}, Err: {err_msg}")

    # Fallback Tier 9 untuk Video
    print(f"[Downloader] Mencoba Tier 9 untuk segmen {clip_id}: Invidious Proxy Video Stream...")
    if download_video_section_via_invidious(video_id, start_sec, end_sec, out_mp4_path):
        print(f"[Downloader] Sukses mengunduh segmen {clip_id} via Invidious Proxy!")
        return out_mp4_path

    raise RuntimeError(f"Gagal mengunduh klip segmen {clip_id} setelah mencoba seluruh strategi Direct Inject dan Proxy.")
