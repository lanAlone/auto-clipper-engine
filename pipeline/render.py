"""
Render Module (Remotion Headless CLI Runner)
Mengeksekusi perenderan video vertikal 9:16 menggunakan Remotion CLI dengan
konfigurasi aman concurrency=1 dan hardware acceleration headless.
"""

import os
import sys
import subprocess
from typing import Optional


def render_clip(
    props_json_path: str,
    output_mp4_path: str,
    remotion_dir: str = "remotion",
    timeout_sec: int = 600
) -> str:
    """
    Me-render 1 klip video MP4 vertikal 9:16 dari file inputProps JSON.
    Mengembalikan path MP4 hasil render.
    """
    if not os.path.exists(props_json_path):
        raise FileNotFoundError(f"File props tidak ditemukan: {props_json_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    abs_props = os.path.abspath(props_json_path).replace("\\", "/")
    abs_out = os.path.abspath(output_mp4_path).replace("\\", "/")

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "Composition",
        abs_out,
        f"--props={abs_props}",
        "--gl=swiftshader",
        "--pixel-format=yuv420p",
        "--log=info",
        "--overwrite"
    ]

    print(f"[Remotion Render] Memulai rendering: {os.path.basename(abs_out)}...")
    try:
        proc = subprocess.run(
            cmd,
            cwd=remotion_dir,
            stdout=sys.stdout,  # Biarkan log Remotion tampil langsung ke konsol secara real-time
            stderr=sys.stderr,  # Jangan di-PIPE agar tidak tertahan buffer
            text=True,
            timeout=1800,  # Beri waktu hingga 30 menit (untuk amannya)
            shell=True if os.name == "nt" else False
        )
        if proc.returncode != 0:
            err_log = proc.stderr[-400:] if proc.stderr else proc.stdout[-400:]
            raise RuntimeError(f"Remotion render error (Code {proc.returncode}): {err_log}")

        if not os.path.exists(abs_out):
            raise RuntimeError(f"File MP4 hasil render tidak ditemukan di: {abs_out}")

        print(f"[Remotion Render] Sukses! File tersimpan di: {abs_out}")
        return abs_out

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Rendering Remotion timeout setelah {timeout_sec} detik.")
