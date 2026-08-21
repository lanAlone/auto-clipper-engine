"""
Transcribe Module (YouTube Subtitle Fallback + Groq Whisper Engine)
Mengekstrak transkrip kata-per-kata dan segmen kalimat.
Mendahulukan subtitle bawaan YouTube jika ada, atau menggunakan Groq Whisper-large-v3-turbo.
"""

import os
import re
import json
import requests
from typing import Dict, Any, Optional, List


def parse_vtt_timestamp(ts_str: str) -> float:
    """Mengonversi format timestamp VTT (HH:MM:SS.mmm atau MM:SS.mmm) ke detik float."""
    clean = ts_str.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(clean)


def parse_vtt_subtitles(vtt_path: str, video_id: str) -> Optional[Dict[str, Any]]:
    """
    Mem-parsing file WebVTT hasil unduhan yt-dlp menjadi format transcript.json standar.
    """
    if not vtt_path or not os.path.exists(vtt_path):
        return None

    try:
        with open(vtt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex untuk cue VTT: (start) --> (end) \n (text)
        cue_pattern = re.compile(
            r"((?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})[^\n]*\n([\s\S]*?)(?=\n\n|\n(?:\d{1,2}:)?\d{2}:\d{2}|$)"
        )
        matches = cue_pattern.findall(content)
        if not matches:
            return None

        segments = []
        words = []
        seg_id = 0

        for start_str, end_str, raw_text in matches:
            # Bersihkan tag VTT seperti <c> </c> atau formatting
            clean_text = re.sub(r"<[^>]+>", "", raw_text).strip()
            clean_text = re.sub(r"\s+", " ", clean_text)
            if not clean_text:
                continue

            s_time = parse_vtt_timestamp(start_str)
            e_time = parse_vtt_timestamp(end_str)
            
            segments.append({
                "id": seg_id,
                "start": round(s_time, 2),
                "end": round(e_time, 2),
                "text": clean_text
            })

            # Buat aproksimasi word timestamps jika tidak ada tag per-kata
            seg_words = clean_text.split()
            if seg_words:
                word_dur = (e_time - s_time) / len(seg_words)
                for i, w in enumerate(seg_words):
                    w_start = s_time + (i * word_dur)
                    w_end = w_start + word_dur
                    words.append({
                        "word": w,
                        "start": round(w_start, 2),
                        "end": round(w_end, 2)
                    })

            seg_id += 1

        if not segments:
            return None

        total_dur = segments[-1]["end"]
        return {
            "video_id": video_id,
            "duration_sec": total_dur,
            "source": "youtube_native_subtitles",
            "words": words,
            "segments": segments
        }

    except Exception as e:
        print(f"[Warning] Gagal parsing VTT: {e}")
        return None


def transcribe_with_groq(
    audio_path: str,
    groq_api_key: str,
    video_id: str
) -> Dict[str, Any]:
    """
    Memanggil Groq Whisper API (whisper-large-v3-turbo) dengan format verbose_json
    dan word/segment timestamps.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan di: {audio_path}")

    if not groq_api_key or not groq_api_key.strip():
        raise ValueError("API Key Groq untuk transkripsi audio tidak tersedia.")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {groq_api_key.strip()}"
    }

    # Buka file audio 32kbps mono
    with open(audio_path, "rb") as f:
        files = {
            "file": (os.path.basename(audio_path), f, "audio/mp3")
        }
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
            "timestamp_granularities[]": ["word", "segment"]
        }

        try:
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=180)
        except requests.exceptions.Timeout:
            raise RuntimeError("Request transkripsi audio ke Groq API timeout (>180 detik).")

    if resp.status_code != 200:
        if resp.status_code in (401, 403):
            raise RuntimeError(f"Kunci API Groq ditolak (Status {resp.status_code}). Periksa kembali kunci Groq Anda di Tab Pengaturan.")
        elif resp.status_code == 429:
            raise RuntimeError("Kunci API Groq terkena Rate Limit kuota harian audio. Silakan tunggu beberapa menit.")
        elif resp.status_code == 413:
            raise RuntimeError("File audio terlalu besar (>25MB). Sistem downsampling otomatis gagal.")
        else:
            raise RuntimeError(f"Groq API Transcribe error ({resp.status_code}): {resp.text[:150]}")

    result_json = resp.json()

    # Normalisasi format transcript
    duration = result_json.get("duration", 0.0)
    raw_segments = result_json.get("segments", [])
    raw_words = result_json.get("words", [])

    segments = []
    for s in raw_segments:
        segments.append({
            "id": s.get("id", len(segments)),
            "start": round(float(s.get("start", 0.0)), 2),
            "end": round(float(s.get("end", 0.0)), 2),
            "text": s.get("text", "").strip()
        })

    words = []
    for w in raw_words:
        words.append({
            "word": w.get("word", "").strip(),
            "start": round(float(w.get("start", 0.0)), 2),
            "end": round(float(w.get("end", 0.0)), 2)
        })

    return {
        "video_id": video_id,
        "duration_sec": duration,
        "source": "groq_whisper_large_v3_turbo",
        "words": words,
        "segments": segments
    }


def transcribe(
    audio_path: str,
    groq_api_key: str,
    video_id: str,
    vtt_sub_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Entry point transkripsi: Coba subtitle native YouTube dulu, jika tidak ada baru gunakan Groq.
    """
    if vtt_sub_path:
        print("[Transcribe] Mencoba mengekstrak subtitle YouTube native...")
        sub_data = parse_vtt_subtitles(vtt_sub_path, video_id)
        if sub_data and len(sub_data.get("segments", [])) > 5:
            print(f"[Transcribe] Berhasil menggunakan subtitle YouTube ({len(sub_data['segments'])} segmen, 0 API cost).")
            return sub_data

    print("[Transcribe] Mengirim audio 32kbps ke Groq Whisper API...")
    return transcribe_with_groq(audio_path, groq_api_key, video_id)
