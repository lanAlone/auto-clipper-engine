"""
Downloader Module (Lightweight Two-Phase & 6-Tier Resilient YouTube Extraction)
Mendukung video podcast YouTube hingga 3 JAM (10.800 detik).
Menggunakan strategi multi-client Android/iOS/TV untuk bypass Botguard pada IP datacenter.
"""

import os
import subprocess
import re
import json
from typing import Tuple, Optional, List, Dict, Any

from pipeline.fetch_user_key import get_user_cookie_file
from pipeline.stealth_session import generate_youtube_session_cookies


MAX_DURATION_SECONDS = 10800  # 3 Jam Penuh (Podcast Panjang)


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

    for client_arg in clients:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--print", "%(duration)s|||%(title)s",
            "--no-warnings",
            "--extractor-args", client_arg
        ]
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

    # Soft fallback jika pre-flight metadata lambat / terblokir
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

    base_args = [
        "yt-dlp",
        "--format", "bestaudio[ext=m4a]/bestaudio/best",
        "--write-auto-sub", "--sub-lang", "id,en",
        "--sub-format", "vtt",
        "-o", audio_raw_template,
        "--no-playlist"
    ]

    tier_errors = []
    download_success = False
    raw_audio_path = ""

    # Tier 1: Client Android Creator & Android App (Paling kebal Botguard di datacenter IP)
    print("[Downloader] Mencoba Tier 1 (Android Creator Client)...")
    t1_args = base_args + ["--extractor-args", "youtube:player_client=android_creator,android", url]
    if user_cookie_file:
        t1_args.extend(["--cookies", user_cookie_file])
    code1, out1, err1 = run_cmd(t1_args, timeout_sec=180)
    raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
    if code1 == 0 and raw_files:
        download_success = True
        raw_audio_path = raw_files[0]
        print("[Tier 1] Berhasil mengunduh audio stream via Android Creator client.")
    else:
        tier_errors.append(f"Tier 1: {err1[-100:].strip()}")

    # Tier 2: Client iOS (Apple AVPlayer format)
    if not download_success:
        print("[Downloader] Mencoba Tier 2 (iOS Client)...")
        t2_args = base_args + ["--extractor-args", "youtube:player_client=ios", url]
        if user_cookie_file:
            t2_args.extend(["--cookies", user_cookie_file])
        code2, out2, err2 = run_cmd(t2_args, timeout_sec=180)
        raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
        if code2 == 0 and raw_files:
            download_success = True
            raw_audio_path = raw_files[0]
            print("[Tier 2] Berhasil mengunduh audio stream via iOS client.")
        else:
            tier_errors.append(f"Tier 2: {err2[-100:].strip()}")

    # Tier 3: Client TV Embedded (Smart TV streams)
    if not download_success:
        print("[Downloader] Mencoba Tier 3 (Smart TV Embedded Client)...")
        t3_args = base_args + ["--extractor-args", "youtube:player_client=tv_embedded,tv", url]
        if user_cookie_file:
            t3_args.extend(["--cookies", user_cookie_file])
        code3, out3, err3 = run_cmd(t3_args, timeout_sec=180)
        raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
        if code3 == 0 and raw_files:
            download_success = True
            raw_audio_path = raw_files[0]
            print("[Tier 3] Berhasil mengunduh audio via TV client.")
        else:
            tier_errors.append(f"Tier 3: {err3[-100:].strip()}")

    # Tier 4: Client Mobile Web
    if not download_success:
        print("[Downloader] Mencoba Tier 4 (Mobile Web Client)...")
        t4_args = base_args + ["--extractor-args", "youtube:player_client=mweb", url]
        if user_cookie_file:
            t4_args.extend(["--cookies", user_cookie_file])
        code4, out4, err4 = run_cmd(t4_args, timeout_sec=180)
        raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
        if code4 == 0 and raw_files:
            download_success = True
            raw_audio_path = raw_files[0]
            print("[Tier 4] Berhasil mengunduh audio via Mobile Web client.")
        else:
            tier_errors.append(f"Tier 4: {err4[-100:].strip()}")

    # Tier 5: Playwright Headless YouTube Embed Handshake Session
    if not download_success:
        print("[Downloader] Mencoba Tier 5 (Playwright Embed Session Handshake)...")
        stealth_cookie = generate_youtube_session_cookies(video_id)
        if stealth_cookie and os.path.exists(stealth_cookie):
            t5_args = base_args + [
                "--cookies", stealth_cookie,
                "--extractor-args", "youtube:player_client=android,ios,mweb",
                url
            ]
            code5, out5, err5 = run_cmd(t5_args, timeout_sec=180)
            raw_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(f"{video_id}_raw")]
            if code5 == 0 and raw_files:
                download_success = True
                raw_audio_path = raw_files[0]
                print("[Tier 5] Berhasil mengunduh audio via Playwright Embed Session.")
            else:
                tier_errors.append(f"Tier 5: {err5[-100:].strip()}")

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

    clients = [
        "youtube:player_client=android_creator,android",
        "youtube:player_client=ios",
        "youtube:player_client=tv_embedded,tv",
        "youtube:player_client=mweb"
    ]

    for client_arg in clients:
        cmd = [
            "yt-dlp",
            "--download-sections", section_spec,
            "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--force-keyframes-at-cuts",
            "--extractor-args", client_arg,
            "-o", out_mp4_path,
            url
        ]
        if user_cookie_file:
            cmd.extend(["--cookies", user_cookie_file])

        code, out, err = run_cmd(cmd, timeout_sec=180)
        if code == 0 and os.path.exists(out_mp4_path) and os.path.getsize(out_mp4_path) > 50000:
            print(f"[Downloader] Sukses mengunduh segmen {clip_id} via {client_arg}.")
            return out_mp4_path

    raise RuntimeError(f"Gagal mengunduh klip segmen {clip_id} setelah mencoba seluruh player client.")
