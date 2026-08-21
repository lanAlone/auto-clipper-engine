"""
Cache Module (HF Dataset Caching)
Menyimpan dan memeriksa apakah transcript.json dan clips.json sudah pernah
diproses sebelumnya untuk video_id yang sama, sehingga menghemat kuota & waktu komputasi.
"""

import os
import json
from typing import Optional, Dict, Any
from huggingface_hub import HfApi, hf_hub_download


def get_cached_transcript(video_id: str, public_repo_id: str, hf_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Mencari file cache transcript/{video_id}.json di HF dataset publik."""
    if not public_repo_id:
        return None
    try:
        local_path = hf_hub_download(
            repo_id=public_repo_id,
            repo_type="dataset",
            filename=f"transcripts/{video_id}.json",
            token=hf_token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cached_transcript(video_id: str, transcript_data: Dict[str, Any], public_repo_id: str, hf_token: str) -> bool:
    """Menyimpan file transcript/{video_id}.json ke dataset publik."""
    if not public_repo_id or not hf_token:
        return False
    try:
        api = HfApi(token=hf_token)
        json_bytes = json.dumps(transcript_data, indent=2).encode("utf-8")
        api.upload_file(
            path_or_fileobj=json_bytes,
            path_in_repo=f"transcripts/{video_id}.json",
            repo_id=public_repo_id,
            repo_type="dataset",
            commit_message=f"Cache transcript for {video_id}"
        )
        return True
    except Exception as e:
        print(f"[Warning] Gagal simpan cache transkrip: {e}")
        return False


def get_cached_clips(video_id: str, public_repo_id: str, hf_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Mencari file cache clips/{video_id}.json di HF dataset publik."""
    if not public_repo_id:
        return None
    try:
        local_path = hf_hub_download(
            repo_id=public_repo_id,
            repo_type="dataset",
            filename=f"clips/{video_id}.json",
            token=hf_token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cached_clips(video_id: str, clips_data: Dict[str, Any], public_repo_id: str, hf_token: str) -> bool:
    """Menyimpan file clips/{video_id}.json ke dataset publik."""
    if not public_repo_id or not hf_token:
        return False
    try:
        api = HfApi(token=hf_token)
        json_bytes = json.dumps(clips_data, indent=2).encode("utf-8")
        api.upload_file(
            path_or_fileobj=json_bytes,
            path_in_repo=f"clips/{video_id}.json",
            repo_id=public_repo_id,
            repo_type="dataset",
            commit_message=f"Cache clips for {video_id}"
        )
        return True
    except Exception as e:
        print(f"[Warning] Gagal simpan cache clips: {e}")
        return False
