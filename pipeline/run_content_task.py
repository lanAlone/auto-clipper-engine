"""
Content Task Dispatcher Runner
Entry point untuk workflow content-task.yml.
"""

import os
import sys
import json
import argparse

from pipeline.content_status import update_content_status
from pipeline.cache import get_cached_transcript, get_cached_clips
from pipeline.generate_content import generate_social_content
from pipeline.build_schedule import build_draft_schedule
from pipeline.summarize_performance import summarize_user_performance
from huggingface_hub import HfApi


def main():
    parser = argparse.ArgumentParser(description="Run Content Task")
    parser.add_argument("--job_id", required=True)
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--task_type", required=True, choices=["generate_content", "build_schedule", "summarize_performance"])
    parser.add_argument("--video_id", required=True)
    parser.add_argument("--payload_json", default="{}")

    args = parser.parse_args()
    public_repo_id = os.getenv("HF_DATASET_REPO_ID", "")
    hf_token = os.getenv("HF_TOKEN", "")

    update_content_status(args.job_id, args.user_id, args.task_type, "running", f"Memulai pengerjaan {args.task_type}...")

    try:
        extra_data = json.loads(args.payload_json)
    except Exception:
        extra_data = {}

    try:
        if args.task_type == "generate_content":
            trans = get_cached_transcript(args.video_id, public_repo_id, hf_token)
            clips = get_cached_clips(args.video_id, public_repo_id, hf_token)
            if not clips or not trans:
                raise RuntimeError(f"Video {args.video_id} belum memiliki data transkrip/klip tersimpan.")

            res = generate_social_content(args.video_id, args.user_id, clips, trans, public_repo_id, hf_token)
            
            # Simpan ke content/{video_id}.json
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=json.dumps(res, indent=2).encode("utf-8"),
                path_in_repo=f"content/{args.video_id}.json",
                repo_id=public_repo_id,
                repo_type="dataset",
                commit_message=f"Generate content for {args.video_id}"
            )
            update_content_status(args.job_id, args.user_id, args.task_type, "done", "Berhasil membuat 5 variasi hook & caption!", result_data=res)

        elif args.task_type == "build_schedule":
            # Ambil content data
            # Jalankan build_draft_schedule
            content_data = extra_data.get("content_data") or {}
            res = build_draft_schedule(args.video_id, args.user_id, content_data)
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=json.dumps(res, indent=2).encode("utf-8"),
                path_in_repo=f"schedule/{args.video_id}.json",
                repo_id=public_repo_id,
                repo_type="dataset",
                commit_message=f"Build draft schedule for {args.video_id}"
            )
            update_content_status(args.job_id, args.user_id, args.task_type, "done", "Berhasil menyusun kalender draft posting!", result_data=res)

        elif args.task_type == "summarize_performance":
            raw_entries = extra_data.get("entries", [])
            res = summarize_user_performance(args.video_id, args.user_id, raw_entries)
            api = HfApi(token=hf_token)
            api.upload_file(
                path_or_fileobj=json.dumps(res, indent=2).encode("utf-8"),
                path_in_repo=f"performance/{args.video_id}.json",
                repo_id=public_repo_id,
                repo_type="dataset",
                commit_message=f"Summarize performance for {args.video_id}"
            )
            update_content_status(args.job_id, args.user_id, args.task_type, "done", "Berhasil menganalisis data performa!", result_data=res)

    except Exception as e:
        print(f"[Error] Task {args.task_type} gagal: {e}")
        update_content_status(args.job_id, args.user_id, args.task_type, "error", f"Gagal mengeksekusi task: {str(e)}", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
