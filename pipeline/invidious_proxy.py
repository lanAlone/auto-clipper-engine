import os
import requests
from typing import Optional, Tuple
import subprocess

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.f5.si",
    "https://yt.chocolatemoo53.com",
    "https://invidious.tiekoetter.com",
    "https://inv.nadeko.ygg",
    "https://invidious.nerdvpn.de"
]

def get_proxy_stream_url(video_id: str, itag: int) -> str:
    """Mengembalikan URL streaming yang proxy traffic lewat Invidious server."""
    for inst in INVIDIOUS_INSTANCES:
        url = f"{inst}/latest_version?id={video_id}&itag={itag}"
        try:
            # Lakukan pre-flight check HEAD request
            r = requests.head(url, timeout=10)
            if r.status_code in [200, 206, 302]:
                return url
        except Exception:
            continue
    
    # Jika gagal preflight, kembalikan instans pertama sebagai fallback buta
    return f"{INVIDIOUS_INSTANCES[0]}/latest_version?id={video_id}&itag={itag}"

def download_audio_via_invidious(video_id: str, output_path: str) -> bool:
    """Mengunduh audio m4a (itag 140) menggunakan ffmpeg untuk stream handling."""
    stream_url = get_proxy_stream_url(video_id, 140)
    print(f"[InvidiousProxy] Mencoba unduh audio via: {stream_url.split('/latest')[0]}")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", stream_url,
        "-c", "copy",
        output_path
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
            return True
        else:
            print(f"[InvidiousProxy] FFmpeg gagal: {proc.stderr.decode()[-200:]}")
            return False
    except Exception as e:
        print(f"[InvidiousProxy] Error: {e}")
        return False

def download_video_section_via_invidious(video_id: str, start_sec: float, end_sec: float, output_path: str) -> bool:
    """Mengunduh segmen video mp4 720p (itag 22) menggunakan ffmpeg seek server-side (-ss sebelum -i)."""
    stream_url = get_proxy_stream_url(video_id, 22)
    print(f"[InvidiousProxy] Mencoba unduh segmen video via: {stream_url.split('/latest')[0]}")
    
    # -ss sebelum -i membuat ffmpeg melompat (seek) via HTTP range request! Sangat efisien!
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0.0, start_sec - 0.5)),
        "-i", stream_url,
        "-t", str((end_sec - start_sec) + 1.0),
        "-c", "copy",
        output_path
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 50000:
            return True
        else:
            print(f"[InvidiousProxy] FFmpeg gagal: {proc.stderr.decode()[-200:]}")
            return False
    except Exception as e:
        print(f"[InvidiousProxy] Error: {e}")
        return False
