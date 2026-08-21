"""
Content Status Module
Menyimpan status task konten ringan ke content_status/{job_id}.json di dataset publik.
"""

import os
import json
import datetime
from huggingface_hub import HfApi


def update_content_status(
    job_id: str,
    user_id: str,
    task_type: str,
    status: str,
    message: str,
    result_data: dict = None,
    error: str = None
) -> bool:
    repo_id = os.getenv("HF_DATASET_REPO_ID")
    token = os.getenv("HF_TOKEN")
    if not repo_id or not token:
        print(f"[Content Status] {job_id} ({task_type}): [{status}] {message}")
        return True

    payload = {
        "job_id": job_id,
        "user_id": user_id,
        "task_type": task_type,
        "status": status,
        "message": message,
        "result_data": result_data,
        "error": error,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    try:
        api = HfApi(token=token)
        api.upload_file(
            path_or_fileobj=json.dumps(payload, indent=2).encode("utf-8"),
            path_in_repo=f"content_status/{job_id}.json",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Update content task {job_id}: {status}"
        )
        return True
    except Exception as e:
        print(f"[Warning] Gagal update content status: {e}")
        return False
