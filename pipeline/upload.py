"""
Upload Module (HF Dataset Result Uploader & Storage Retention)
Mengunggah file klip MP4 hasil render ke dataset publik Hugging Face
dengan mekanisme Exponential Backoff Retry dan menghasilkan link streaming langsung.
"""

import os
import time
from typing import List, Dict, Any, Optional
from huggingface_hub import HfApi


def upload_single_clip(
    video_id: str,
    clip_id: str,
    local_mp4_path: str,
    public_repo_id: str,
    hf_token: str
) -> str:
    """
    Mengunggah satu file MP4 ke dataset publik dan mengembalikan URL download/streaming langsung.
    """
    if not os.path.exists(local_mp4_path):
        raise FileNotFoundError(f"File klip tidak ditemukan: {local_mp4_path}")

    api = HfApi(token=hf_token)
    path_in_repo = f"clips/{video_id}/{clip_id}.mp4"

    # Exponential Backoff Retry (4x)
    for attempt in range(1, 5):
        try:
            api.upload_file(
                path_or_fileobj=local_mp4_path,
                path_in_repo=path_in_repo,
                repo_id=public_repo_id,
                repo_type="dataset",
                commit_message=f"Upload clip {clip_id} for video {video_id}"
            )
            # URL resolusi langsung Hugging Face
            public_url = f"https://huggingface.co/datasets/{public_repo_id}/resolve/main/{path_in_repo}"
            return public_url
        except Exception as e:
            wait_time = attempt * 3
            print(f"[Warning] Gagal upload klip {clip_id} (percobaan {attempt}/4): {e}. Menunggu {wait_time}s...")
            time.sleep(wait_time)

    raise RuntimeError(f"Gagal mengunggah file klip {clip_id} ke Hugging Face Dataset setelah 4 percobaan.")


def upload_all_results(
    video_id: str,
    rendered_clips: List[Dict[str, Any]],
    public_repo_id: str,
    hf_token: str
) -> List[Dict[str, Any]]:
    """
    Mengunggah semua file klip dan mengisi field 'url' di array clips.
    """
    uploaded_results = []
    for item in rendered_clips:
        clip_id = item["clip_id"]
        mp4_path = item["mp4_path"]
        title = item.get("title", f"Klip {clip_id}")

        print(f"[Upload] Mengunggah {clip_id} ke Hugging Face Dataset...")
        url = upload_single_clip(
            video_id=video_id,
            clip_id=clip_id,
            local_mp4_path=mp4_path,
            public_repo_id=public_repo_id,
            hf_token=hf_token
        )
        uploaded_results.append({
            "clip_id": clip_id,
            "title": title,
            "duration": item.get("duration", 30.0),
            "url": url,
            "hook_reason": item.get("hook_reason", ""),
            "viral_score": item.get("viral_score", 8.5)
        })

    return uploaded_results
