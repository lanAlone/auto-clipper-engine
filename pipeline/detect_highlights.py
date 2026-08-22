"""
Highlight Detection Module (LLM Rotation + Word-Boundary Snapping)
Menganalisis momen paling bernilai tinggi/viral dari transkrip video menggunakan
rotasi model LLM, lalu meratakan timestamp ke batas kata terdekat (Word-Level Snapping).
"""

import json
from typing import Dict, Any, List, Optional, Tuple

from pipeline.llm_router import call_llm_json


def format_transcript_for_llm(transcript_dict: Dict[str, Any], max_char_limit: int = 250000) -> str:
    """
    Mengubah array segmen transkrip menjadi teks ringkas ber-timestamp [MM:SS]
    untuk menghemat token input LLM secara signifikan.
    """
    segments = transcript_dict.get("segments", [])
    lines = []
    for s in segments:
        start_sec = s.get("start", 0.0)
        mins = int(start_sec // 60)
        secs = int(start_sec % 60)
        text = s.get("text", "").strip()
        if text:
            lines.append(f"[{mins:02d}:{secs:02d}] {text}")

    full_text = "\n".join(lines)
    if len(full_text) > max_char_limit:
        return full_text[:max_char_limit] + "\n...[transkrip dipotong untuk batas konteks]..."
    return full_text


def snap_timestamps_to_words(
    raw_start: float,
    raw_end: float,
    words: List[Dict[str, Any]],
    total_duration: float
) -> Tuple[float, float]:
    """
    Word-Level Snapping (+0.2s padding):
    Menyelaraskan timestamp potongan video agar persis berada di jeda kata alami,
    sehingga audio tidak pernah terpotong di tengah-tengah suku kata pembicara.
    """
    if not words:
        return max(0.0, raw_start), min(total_duration, raw_end)

    # 1. Cari batas kata awal (start)
    snapped_start = raw_start
    # Cari kata yang paling mendekati raw_start
    start_candidates = [w for w in words if abs(w.get("start", 0.0) - raw_start) <= 2.5]
    if start_candidates:
        closest_start_word = min(start_candidates, key=lambda w: abs(w.get("start", 0.0) - raw_start))
        snapped_start = max(0.0, closest_start_word.get("start", 0.0) - 0.15)
    else:
        # Fallback ke kata terdekat sebelumnya
        earlier_words = [w for w in words if w.get("start", 0.0) <= raw_start]
        if earlier_words:
            snapped_start = max(0.0, earlier_words[-1].get("start", 0.0) - 0.1)

    # 2. Cari batas kata akhir (end)
    snapped_end = raw_end
    end_candidates = [w for w in words if abs(w.get("end", 0.0) - raw_end) <= 2.5]
    if end_candidates:
        closest_end_word = min(end_candidates, key=lambda w: abs(w.get("end", 0.0) - raw_end))
        snapped_end = min(total_duration, closest_end_word.get("end", 0.0) + 0.25)
    else:
        # Fallback ke kata terdekat sesudahnya
        later_words = [w for w in words if w.get("end", 0.0) >= raw_end]
        if later_words:
            snapped_end = min(total_duration, later_words[0].get("end", 0.0) + 0.2)

    # Pastikan durasi minimal 10 detik
    if snapped_end - snapped_start < 10.0:
        snapped_end = min(total_duration, snapped_start + 15.0)

    return round(snapped_start, 2), round(snapped_end, 2)


def detect_highlights(
    transcript_dict: Dict[str, Any],
    user_id: str,
    target_duration_mode: str = "standard_30_60",
    requested_clip_count: int = 3
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Mendeteksi momen terbaik untuk klip vertikal pendek (Shorts/Reels/TikTok).
    Mengembalikan (clips_dict, llm_used_dict).
    """
    video_id = transcript_dict.get("video_id", "unknown_video")
    total_duration = float(transcript_dict.get("duration_sec", 600.0))
    words = transcript_dict.get("words", [])

    duration_guide = "30 sampai 60 detik"
    if target_duration_mode == "fast_under_30":
        duration_guide = "15 sampai 30 detik (cepat, padat)"
    elif target_duration_mode == "long_60_90":
        duration_guide = "60 sampai 90 detik (mendalam, cerita tuntas)"

    formatted_transcript = format_transcript_for_llm(transcript_dict)

    system_prompt = (
        "Anda adalah AI Produser Konten Video Pendek (Short-Form Content Producer) kelas dunia. "
        "Tugas Anda adalah menganalisis transkrip video panjang dan menemukan momen-momen emas terbaik "
        "yang memiliki potensi retensi tinggi, hook awal yang kuat, dan pesan yang berdiri sendiri (self-contained)."
    )

    user_prompt = f"""Berikut adalah transkrip video YouTube berdurasi {total_duration:.1f} detik:

--- TRANSKRIP LENGKAP ---
{formatted_transcript}
-------------------------

TUGAS ANDA:
Pilihlah tepat {requested_clip_count} momen potongan klip terbaik untuk dijadikan video vertikal (Shorts/Reels/TikTok).
Durasi tiap klip yang diinginkan: {duration_guide}.

Setiap klip HARUS:
1. Memiliki 'hook' kuat di 3-5 detik awal.
2. Memiliki konteks cerita/pembahasan yang tuntas (tidak menggantung aneh).
3. Nilai 'start' dan 'end' berupa angka detik desimal float (misal 124.5 bukan string).

Kembalikan HANYA format JSON valid berikut tanpa pembuka/penutup markdown:
{{
  "video_id": "{video_id}",
  "candidates": [
    {{
      "clip_id": "c1",
      "start": 120.0,
      "end": 168.5,
      "title": "Judul Menarik Singkat",
      "hook_reason": "Alasan kenapa 3 detik awal klip ini memancing rasa penasaran",
      "viral_score": 9.2
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print(f"[Detect Highlights] Mengirim transkrip ke model pool untuk user '{user_id}'...")
    parsed_json, llm_used = call_llm_json(user_id=user_id, messages=messages, temperature=0.4)

    raw_candidates = parsed_json.get("candidates", [])
    if not raw_candidates and isinstance(parsed_json, list):
        raw_candidates = parsed_json

    snapped_candidates = []
    for idx, c in enumerate(raw_candidates):
        cid = c.get("clip_id") or f"c{idx+1}"
        title = c.get("title") or f"Highlight Klip #{idx+1}"
        hook = c.get("hook_reason") or "Momen penting dalam percakapan"
        score = float(c.get("viral_score", 8.5))

        # Parsing start & end
        try:
            r_start = float(c.get("start", 0.0))
            r_end = float(c.get("end", 60.0))
        except (ValueError, TypeError):
            r_start = 0.0
            r_end = min(total_duration, 45.0)

        # Terapkan Word-Level Snapping
        s_start, s_end = snap_timestamps_to_words(r_start, r_end, words, total_duration)

        snapped_candidates.append({
            "clip_id": cid,
            "start": s_start,
            "end": s_end,
            "duration": round(s_end - s_start, 2),
            "title": title,
            "hook_reason": hook,
            "viral_score": round(score, 1)
        })

    # Jika tidak ada klip yang terdeteksi, buat 1 fallback klip otomatis
    if not snapped_candidates:
        s_end = min(total_duration, 45.0)
        snapped_candidates.append({
            "clip_id": "c1",
            "start": 0.0,
            "end": s_end,
            "duration": s_end,
            "title": "Momen Pembuka Video",
            "hook_reason": "Pembukaan dan perkenalan topik utama",
            "viral_score": 7.5
        })

    final_clips_dict = {
        "video_id": video_id,
        "total_clips": len(snapped_candidates),
        "candidates": snapped_candidates
    }

    print(f"[Detect Highlights] Berhasil mendeteksi {len(snapped_candidates)} klip menggunakan {llm_used['provider_id']} ({llm_used['model_id']}).")
    return final_clips_dict, llm_used
