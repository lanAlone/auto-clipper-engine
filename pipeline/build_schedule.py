"""
Build Schedule Module (Draft Posting Calendar)
Menyusun rekomendasi jadwal posting multi-platform untuk klip yang dihasilkan.
PERINGATAN (Gotcha #12): Status SELALU ditimpa menjadi 'draft' di kode Python.
"""

import json
import datetime
from typing import Dict, Any, List
from pipeline.llm_router import call_llm_json


def build_draft_schedule(
    video_id: str,
    user_id: str,
    content_dict: Dict[str, Any],
    platforms: List[str] = None
) -> Dict[str, Any]:
    """
    Menyusun kalender draft tanggal & jam posting rekomendasi.
    """
    target_platforms = platforms or ["tiktok", "instagram_reels", "youtube_shorts"]
    clips = content_dict.get("clips", [])
    
    system_prompt = (
        "Anda adalah Content Strategist. Tugas Anda adalah merekomendasikan tanggal dan jam posting "
        "terbaik untuk klip media sosial dalam rentang 7-14 hari ke depan."
    )

    user_prompt = f"""Klip yang tersedia: {len(clips)} klip.
Platform target: {', '.join(target_platforms)}.

Susunlah rekomendasi jadwal posting.
Kembalikan format JSON:
{{
  "video_id": "{video_id}",
  "entries": [
    {{
      "clip_id": "c1",
      "platform": "reels",
      "suggested_date": "2026-08-25",
      "suggested_time": "19:00",
      "status": "draft"
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    parsed_json, _ = call_llm_json(user_id=user_id, messages=messages, temperature=0.3)

    # GOTCHA #12: Paksa seluruh status menjadi 'draft' di kode Python!
    entries = parsed_json.get("entries", [])
    for entry in entries:
        entry["status"] = "draft"  # Dilarang keras menerima status auto-post dari LLM

    return {
        "video_id": video_id,
        "user_id": user_id,
        "entries": entries,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
