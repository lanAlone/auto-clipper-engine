import os
import sys

# Ensure repo root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

"""
Status Synchronization Module (Repo A -> Repo B via HF Dataset)
Memperbarui file status/{job_id}.json di HF dataset publik yang di-poll oleh UI Gradio.
Dilengkapi CLI runner untuk Failure Trap di GitHub Actions workflow (if: failure()).
"""

import os
import json
import time
import argparse
import datetime
from typing import Optional, List, Dict, Any
from huggingface_hub import HfApi


def update_status(
    job_id: str,
    user_id: str,
    status: str,
    message: str,
    video_id: str = "",
    clips: Optional[List[Dict[str, Any]]] = None,
    llm_used: Optional[Dict[str, str]] = None,
    error: Optional[str] = None,
    public_repo_id: Optional[str] = None,
    hf_token: Optional[str] = None
) -> bool:
    """
    Menulis status terbaru ke status/{job_id}.json di HF dataset publik
    dengan mekanisme Exponential Backoff Retry.
    """
    repo_id = public_repo_id or os.getenv("HF_DATASET_REPO_ID")
    token = hf_token or os.getenv("HF_TOKEN")

    if not repo_id or not token:
        print(f"[Status Local] Job {job_id}: [{status.upper()}] {message}")
        return True

    payload = {
        "job_id": job_id,
        "user_id": user_id,
        "video_id": video_id,
        "status": status,  # "queued | downloading | transcribing | detecting | preparing | rendering | uploading | done | error"
        "progress_message": message,
        "clips": clips or [],
        "llm_used": llm_used,
        "error": error,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    json_bytes = json.dumps(payload, indent=2).encode("utf-8")
    api = HfApi(token=token)

    # Exponential Backoff Retry (3x) untuk menghindari tabrakan Git commit
    for attempt in range(1, 4):
        try:
            api.upload_file(
                path_or_fileobj=json_bytes,
                path_in_repo=f"status/{job_id}.json",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Update status {job_id}: {status}"
            )
            return True
        except Exception as e:
            wait_time = attempt * 2
            print(f"[Warning] Gagal update status (percobaan {attempt}/3): {e}. Menunggu {wait_time}s...")
            time.sleep(wait_time)

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Auto-Clipper Job Status")
    parser.add_argument("--job_id", required=True, help="Unique Job ID")
    parser.add_argument("--user_id", default="default_user", help="Username")
    parser.add_argument("--status", required=True, help="Status string")
    parser.add_argument("--message", required=True, help="Progress message")
    parser.add_argument("--video_id", default="", help="YouTube Video ID")
    parser.add_argument("--error", default=None, help="Error message if any")

    args = parser.parse_args()
    update_status(
        job_id=args.job_id,
        user_id=args.user_id,
        status=args.status,
        message=args.message,
        video_id=args.video_id,
        error=args.error
    )
