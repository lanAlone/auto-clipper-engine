"""
Summarize Performance Module
Menganalisis data analitik yang diinputkan user secara manual tanpa mengarang angka.
"""

import json
import datetime
from typing import Dict, Any, List
from pipeline.llm_router import call_llm_json


def summarize_user_performance(
    video_id: str,
    user_id: str,
    raw_entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Menghasilkan ringkasan dan rekomendasi dari metrik performa nyata yang dimasukkan user.
    """
    if not raw_entries:
        return {
            "video_id": video_id,
            "entries": [],
            "summary": {
                "text": "Belum ada data performa yang dimasukkan.",
                "top_clip_id": None,
                "recommendations": [],
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }

    system_prompt = (
        "Anda adalah Data Analyst Video Performa. "
        "ATURAN MUTLAK: Hanya rujuk angka-angka yang ada di data input user. DILARANG KERAS mengarang angka baru."
    )

    user_prompt = f"""Data performa yang dimasukkan user:
{json.dumps(raw_entries, indent=2)}

TUGAS ANDA:
Analisis performa klip di atas, temukan klip terbaik, dan berikan 3 rekomendasi actionable.
Kembalikan format JSON:
{{
  "text": "Ringkasan komparatif berbasis angka nyata...",
  "top_clip_id": "c1",
  "recommendations": ["Saran 1...", "Saran 2...", "Saran 3..."]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    summary_json, _ = call_llm_json(user_id=user_id, messages=messages, temperature=0.2)
    summary_json["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "video_id": video_id,
        "entries": raw_entries,
        "summary": summary_json
    }
