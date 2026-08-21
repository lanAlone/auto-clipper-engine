"""
Render Props Builder
Mengonversi transkrip kata-per-kata dan kandidat klip menjadi file inputProps JSON
yang presisi untuk engine Remotion (frame-level accuracy, ducking cues, & captions).
"""

import os
import json
from typing import Dict, Any, List


FPS = 30


def build_clip_render_props(
    clip: Dict[str, Any],
    transcript_words: List[Dict[str, Any]],
    source_video_path: str,
    output_dir: str,
    crop_mode: str = "blurred_stack",
    caption_style: str = "bold_yellow",
    bg_music_file: str = "assets/audio/bg_lofi.mp3",
    sfx_file: str = "assets/audio/whoosh.mp3"
) -> str:
    """
    Menyusun render_props/{clip_id}.json untuk satu klip.
    Mengembalikan path file JSON props yang siap dibaca Remotion.
    """
    os.makedirs(output_dir, exist_ok=True)
    clip_id = clip["clip_id"]
    c_start = float(clip["start"])
    c_end = float(clip["end"])
    c_duration = c_end - c_start
    total_frames = int(round(c_duration * FPS))

    # 1. Filter & Hitung Frame Captions Relatif ke Awal Klip
    clip_captions = []
    speech_ranges = []

    for w in transcript_words:
        w_start = float(w.get("start", 0.0))
        w_end = float(w.get("end", 0.0))
        word_text = w.get("word", "").strip()

        if not word_text:
            continue

        # Cek apakah kata berada dalam rentang klip
        if w_end >= c_start and w_start <= c_end:
            rel_start_sec = max(0.0, w_start - c_start)
            rel_end_sec = min(c_duration, w_end - c_start)

            start_frame = int(round(rel_start_sec * FPS))
            end_frame = int(round(rel_end_sec * FPS))

            if end_frame > start_frame:
                clip_captions.append({
                    "word": word_text,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "start_sec": rel_start_sec,
                    "end_sec": rel_end_sec
                })
                speech_ranges.append({
                    "start_frame": start_frame,
                    "end_frame": end_frame
                })

    # 2. SFX Cues (Whoosh di awal dan di pertengahan transisi)
    sfx_cues = []
    if os.path.exists(sfx_file):
        sfx_cues.append({"file": sfx_file, "at_frame": 0, "volume": 0.5})
        if total_frames > 300:
            sfx_cues.append({"file": sfx_file, "at_frame": int(total_frames // 2), "volume": 0.4})

    # 3. Struktur Props Lengkap Remotion
    props_payload = {
        "clip_id": clip_id,
        "title": clip.get("title", "Highlight"),
        "source_video": os.path.abspath(source_video_path).replace("\\", "/"),
        "start_sec": c_start,
        "end_sec": c_end,
        "duration_frames": total_frames,
        "fps": FPS,
        "width": 1080,
        "height": 1920,
        "crop_mode": crop_mode,          # "blurred_stack" | "center_crop"
        "caption_style": caption_style,  # "bold_yellow" | "clean_white" | "neon_cyan"
        "captions": clip_captions,
        "speech_ranges": speech_ranges,
        "backsound": {
            "file": os.path.abspath(bg_music_file).replace("\\", "/") if os.path.exists(bg_music_file) else None,
            "volume_base": 0.14,
            "duck_to": 0.03
        },
        "sfx_cues": sfx_cues
    }

    props_file_path = os.path.join(output_dir, f"props_{clip_id}.json")
    with open(props_file_path, "w", encoding="utf-8") as f:
        json.dump(props_payload, f, indent=2)

    return props_file_path


def build_all_render_props(
    transcript_dict: Dict[str, Any],
    clips_dict: Dict[str, Any],
    source_video_path: str,
    output_dir: str = "work/render_props",
    crop_mode: str = "blurred_stack",
    caption_style: str = "bold_yellow"
) -> List[str]:
    """
    Membangun file props untuk semua kandidat klip.
    Mengembalikan daftar file props JSON yang telah siap.
    """
    words = transcript_dict.get("words", [])
    candidates = clips_dict.get("candidates", [])
    props_paths = []

    for c in candidates:
        p_path = build_clip_render_props(
            clip=c,
            transcript_words=words,
            source_video_path=source_video_path,
            output_dir=output_dir,
            crop_mode=crop_mode,
            caption_style=caption_style
        )
        props_paths.append(p_path)

    return props_paths
