"""
Generate Content Module (5 Hook Variations, Captions, Titles, Hashtags, & CTA)
Menghasilkan materi copywriting media sosial lengkap untuk semua klip dalam 1 panggilan LLM.
"""

import json
import datetime
from typing import Dict, Any, List, Optional
from pipeline.llm_router import call_llm_json
from pipeline.brand import get_brand_voice


def generate_social_content(
    video_id: str,
    user_id: str,
    clips_dict: Dict[str, Any],
    transcript_dict: Dict[str, Any],
    public_repo_id: str = "",
    hf_token: str = ""
) -> Dict[str, Any]:
    """
    Menghasilkan 5 varian hook on-screen, 1 caption utama, 3 opsi judul, hashtag, dan CTA per klip.
    """
    brand = get_brand_voice(user_id, public_repo_id, hf_token)
    brand_context = ""
    if brand:
        brand_context = f"""
PANDUAN BRAND VOICE USER (WAJIB DIIKUTI):
- Niche: {brand.get('niche', 'Umum')}
- Tone of Voice: {brand.get('voice', 'Santai & Menarik')}
- Do's: {', '.join(brand.get('do', []))}
- Don'ts: {', '.join(brand.get('dont', []))}
"""

    candidates = clips_dict.get("candidates", [])
    clips_summary = []
    for c in candidates:
        clips_summary.append(f"- Klip [{c.get('clip_id')}]: {c.get('title')} (Detik {c.get('start')} s/d {c.get('end')}). Hook reason: {c.get('hook_reason')}")

    clips_text = "\n".join(clips_summary)

    system_prompt = (
        "Anda adalah Viral Social Media Copywriter untuk Shorts, TikTok, dan Instagram Reels. "
        "Tugas Anda adalah membuat copywriting hooks, captions, judul, dan hashtags yang memicu interaksi tinggi."
    )

    user_prompt = f"""Berikut adalah daftar klip video yang telah dipotong:
{clips_text}

{brand_context}

TUGAS ANDA:
Untuk SETIAP klip di atas, buatkan:
1. 'hooks': Tepat 5 variasi hook pembuka teks di layar (onscreen_text) dan kalimat pembuka lisan (spoken_opener).
2. 'caption': 1 caption persuasif lengkap dengan format baris rapi untuk Instagram/TikTok.
3. 'title_options': 3 pilihan judul click-worthy (namun jujur).
4. 'hashtags': 5-8 hashtag relevan.
5. 'cta': 1 Call-To-Action kuat.

Kembalikan HANYA format JSON valid:
{{
  "video_id": "{video_id}",
  "clips": [
    {{
      "clip_id": "c1",
      "hooks": [
        {{"onscreen_text": "Teks hook layar 1", "spoken_opener": "Kalimat pembuka 1"}},
        {{"onscreen_text": "Teks hook layar 2", "spoken_opener": "Kalimat pembuka 2"}},
        {{"onscreen_text": "Teks hook layar 3", "spoken_opener": "Kalimat pembuka 3"}},
        {{"onscreen_text": "Teks hook layar 4", "spoken_opener": "Kalimat pembuka 4"}},
        {{"onscreen_text": "Teks hook layar 5", "spoken_opener": "Kalimat pembuka 5"}}
      ],
      "caption": "Teks caption lengkap...",
      "title_options": ["Judul 1", "Judul 2", "Judul 3"],
      "hashtags": ["#tag1", "#tag2"],
      "cta": "Follow akun ini untuk part 2..."
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    parsed_json, _ = call_llm_json(user_id=user_id, messages=messages, temperature=0.6)
    parsed_json["video_id"] = video_id
    parsed_json["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return parsed_json
