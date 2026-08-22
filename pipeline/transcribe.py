"""
Transcribe Module (YouTube Subtitle Fallback + Chunked Groq Whisper Engine)
Mendukung transkripsi podcast panjang hingga 2-3 jam.
Jika file audio > 20MB, otomatis dipecah menjadi chunk 20 menitan dan digabungkan
secara mulus dengan offset timestamp per-kata yang presisi.
"""

import os
import re
import json
import subprocess
import requests
from typing import Dict, Any, Optional, List, Tuple


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
    """Mem-parsing WebVTT hasil unduhan yt-dlp menjadi transcript.json standar."""
    if not vtt_path or not os.path.exists(vtt_path):
        return None

    try:
        with open(vtt_path, "r", encoding="utf-8") as f:
            content = f.read()

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


def split_audio_into_chunks(audio_path: str, chunk_duration_sec: int = 1200) -> List[Tuple[str, float]]:
    """
    Memecah audio panjang menjadi beberapa potongan 20 menit (1200s).
    Mengembalikan list tuple: [(chunk_path, start_offset_seconds), ...]
    """
    out_dir = os.path.dirname(audio_path)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    
    # Ambil durasi total via ffprobe
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        dur_out = subprocess.check_output(probe_cmd, text=True).strip()
        total_duration = float(dur_out)
    except Exception:
        total_duration = 3600.0

    chunks = []
    current_start = 0.0
    idx = 0

    while current_start < total_duration:
        chunk_file = os.path.join(out_dir, f"{base_name}_chunk_{idx:03d}.mp3")
        split_cmd = [
            "ffmpeg", "-y",
            "-ss", str(current_start),
            "-i", audio_path,
            "-t", str(chunk_duration_sec),
            "-c", "copy",
            chunk_file
        ]
        res = subprocess.run(split_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(chunk_file):
            chunks.append((chunk_file, current_start))
        idx += 1
        current_start += chunk_duration_sec

    return chunks if chunks else [(audio_path, 0.0)]


def transcribe_single_audio_groq(
    audio_path: str,
    groq_api_key: str,
    time_offset: float = 0.0
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """Mengirim satu potongan audio ke Groq Whisper API."""
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {groq_api_key.strip()}"}

    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/mp3")}
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
            "timestamp_granularities[]": ["word", "segment"]
        }
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=180)

    if resp.status_code != 200:
        if resp.status_code in (401, 403):
            raise RuntimeError(f"Kunci API Groq ditolak (Status {resp.status_code}). Periksa kembali kunci Groq Anda.")
        elif resp.status_code == 429:
            raise RuntimeError("Kunci API Groq terkena Rate Limit audio harian.")
        else:
            raise RuntimeError(f"Groq API Transcribe error ({resp.status_code}): {resp.text[:150]}")

    result = resp.json()
    dur = result.get("duration", 0.0)

    segments = []
    for s in result.get("segments", []):
        segments.append({
            "start": round(float(s.get("start", 0.0)) + time_offset, 2),
            "end": round(float(s.get("end", 0.0)) + time_offset, 2),
            "text": s.get("text", "").strip()
        })

    words = []
    for w in result.get("words", []):
        words.append({
            "word": w.get("word", "").strip(),
            "start": round(float(w.get("start", 0.0)) + time_offset, 2),
            "end": round(float(w.get("end", 0.0)) + time_offset, 2)
        })

    return segments, words, dur


def transcribe_with_groq(audio_path: str, groq_api_key: str, video_id: str) -> Dict[str, Any]:
    """Transkripsi multi-chunk Groq untuk audio podcast panjang."""
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    all_segments = []
    all_words = []
    total_duration = 0.0

    if file_size_mb > 20.0:
        print(f"[Groq Whisper] File audio besar ({file_size_mb:.1f} MB). Membagi menjadi chunk 20 menit...")
        chunks = split_audio_into_chunks(audio_path, chunk_duration_sec=1200)
        for idx, (c_file, offset) in enumerate(chunks):
            print(f"[Groq Whisper] Mentranskripsi chunk #{idx+1}/{len(chunks)} (offset {offset/60:.1f}m)...")
            segs, wrds, c_dur = transcribe_single_audio_groq(c_file, groq_api_key, time_offset=offset)
            all_segments.extend(segs)
            all_words.extend(wrds)
            total_duration = max(total_duration, offset + c_dur)
            # Bersihkan chunk temporary
            if c_file != audio_path and os.path.exists(c_file):
                try: os.remove(c_file)
                except Exception: pass
    else:
        print(f"[Groq Whisper] Mentranskripsi audio langsung ({file_size_mb:.1f} MB)...")
        segs, wrds, total_duration = transcribe_single_audio_groq(audio_path, groq_api_key, time_offset=0.0)
        all_segments.extend(segs)
        all_words.extend(wrds)

    for i, s in enumerate(all_segments):
        s["id"] = i

    return {
        "video_id": video_id,
        "duration_sec": total_duration,
        "source": "groq_whisper_large_v3_turbo",
        "words": all_words,
        "segments": all_segments
    }


def transcribe(
    audio_path: str,
    groq_api_key: str,
    video_id: str,
    vtt_sub_path: Optional[str] = None
) -> Dict[str, Any]:
    """Entry point transkripsi: Coba subtitle native YouTube dulu (0 biaya), jika tidak ada baru gunakan Groq."""
    if vtt_sub_path:
        print("[Transcribe] Mencoba mengekstrak subtitle YouTube native...")
        sub_data = parse_vtt_subtitles(vtt_sub_path, video_id)
        if sub_data and len(sub_data.get("segments", [])) > 5:
            print(f"[Transcribe] Berhasil menggunakan subtitle YouTube ({len(sub_data['segments'])} segmen, 0 kuota Groq).")
            return sub_data

    print("[Transcribe] Memulai Groq Whisper-large-v3-turbo engine...")
    return transcribe_with_groq(audio_path, groq_api_key, video_id)
