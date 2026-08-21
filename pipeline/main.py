"""
Main Pipeline Orchestrator (GitHub Actions Engine Entrypoint)
Menjalankan seluruh alur pemrosesan video dari download, transkrip, deteksi highlight,
Remotion render, hingga upload hasil dengan penanganan error komprehensif.
"""

import os
import sys
import argparse
import traceback

from pipeline.status import update_status
from pipeline.download import download_video
from pipeline.fetch_user_key import get_user_key
from pipeline.transcribe import transcribe
from pipeline.detect_highlights import detect_highlights
from pipeline.prep_render_props import build_all_render_props
from pipeline.render import render_clip
from pipeline.upload import upload_all_results
from pipeline.cache import (
    get_cached_transcript, save_cached_transcript,
    get_cached_clips, save_cached_clips
)


def main():
    parser = argparse.ArgumentParser(description="Auto-Clipper Main Video Processing Pipeline")
    parser.add_argument("--job_id", required=True, help="Unique Job ID")
    parser.add_argument("--user_id", required=True, help="Username")
    parser.add_argument("--youtube_url", required=True, help="YouTube Video URL")
    parser.add_argument("--duration_mode", default="standard_30_60", help="Duration preset")
    parser.add_argument("--clip_count", type=int, default=3, help="Number of clips")
    parser.add_argument("--crop_mode", default="blurred_stack", help="Framing mode")
    parser.add_argument("--caption_style", default="bold_yellow", help="Subtitle style")

    args = parser.parse_args()
    job_id = args.job_id
    user_id = args.user_id
    url = args.youtube_url
    public_repo_id = os.getenv("HF_DATASET_REPO_ID", "")
    hf_token = os.getenv("HF_TOKEN", "")

    print(f"=== Memulai Auto-Clipper Pipeline: Job {job_id} (User: {user_id}) ===")

    try:
        # ----------------------------------------------------------------------
        # STAGE 1: DOWNLOAD VIDEO & EXTRACT AUDIO (4-TIER STEALTH)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "downloading", "Mengunduh video dengan perlindungan 4-Tier Stealth...")
        video_path, audio_path, video_id, duration_sec, vtt_path = download_video(
            url=url,
            user_id=user_id,
            output_dir="work/media"
        )
        print(f"[Pipeline] Video ID: {video_id} ({duration_sec:.1f}s)")

        # ----------------------------------------------------------------------
        # STAGE 2: TRANSKRIPSI (CACHE / SUBTITLES / GROQ WHISPER)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "transcribing", "Mengekstrak transkrip kata-per-kata...", video_id=video_id)
        
        # Cek Cache
        cached_trans = get_cached_transcript(video_id, public_repo_id, hf_token)
        if cached_trans:
            print("[Pipeline] Transkrip ditemukan di cache dataset publik.")
            transcript_dict = cached_trans
        else:
            groq_key = get_user_key(user_id, "groq")
            transcript_dict = transcribe(
                audio_path=audio_path,
                groq_api_key=groq_key,
                video_id=video_id,
                vtt_sub_path=vtt_path
            )
            save_cached_transcript(video_id, transcript_dict, public_repo_id, hf_token)

        # ----------------------------------------------------------------------
        # STAGE 3: DETEKSI HIGHLIGHT MOMEN (LLM ROTATION + WORD SNAPPING)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "detecting", "Mendeteksi momen emas terbaik dengan rotasi AI...", video_id=video_id)
        
        cached_clips = get_cached_clips(video_id, public_repo_id, hf_token)
        if cached_clips and len(cached_clips.get("candidates", [])) >= args.clip_count:
            print("[Pipeline] Klip highlight ditemukan di cache.")
            clips_dict = cached_clips
            llm_used = {"provider_id": "cache", "model_id": "cached_detection"}
        else:
            clips_dict, llm_used = detect_highlights(
                transcript_dict=transcript_dict,
                user_id=user_id,
                target_duration_mode=args.duration_mode,
                requested_clip_count=args.clip_count
            )
            save_cached_clips(video_id, clips_dict, public_repo_id, hf_token)

        # ----------------------------------------------------------------------
        # STAGE 4: PERSIAPAN REMOTION RENDER PROPS
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "preparing", "Menyiapkan komposisi video 9:16...", video_id=video_id, llm_used=llm_used)
        props_files = build_all_render_props(
            transcript_dict=transcript_dict,
            clips_dict=clips_dict,
            source_video_path=video_path,
            output_dir="work/render_props",
            crop_mode=args.crop_mode,
            caption_style=args.caption_style
        )

        # ----------------------------------------------------------------------
        # STAGE 5: RENDERING REMOTION (SEQUENTIAL & CONCURRENCY=1)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "rendering", f"Merender {len(props_files)} klip vertikal...", video_id=video_id, llm_used=llm_used)
        rendered_clips = []
        candidates = clips_dict.get("candidates", [])

        for idx, (p_file, c_data) in enumerate(zip(props_files, candidates)):
            cid = c_data["clip_id"]
            out_mp4 = f"work/output/{cid}.mp4"
            print(f"[Pipeline] Rendering Klip #{idx+1}/{len(props_files)} ({cid})...")
            render_clip(
                props_json_path=p_file,
                output_mp4_path=out_mp4,
                remotion_dir="remotion"
            )
            rendered_clips.append({
                "clip_id": cid,
                "title": c_data.get("title", f"Klip {cid}"),
                "duration": c_data.get("duration", 30.0),
                "mp4_path": out_mp4,
                "hook_reason": c_data.get("hook_reason", ""),
                "viral_score": c_data.get("viral_score", 8.5)
            })

        # ----------------------------------------------------------------------
        # STAGE 6: UPLOAD HASIL KE HUGGING FACE DATASET
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "uploading", "Mengunggah file video hasil ke cloud storage...", video_id=video_id, llm_used=llm_used)
        uploaded_results = upload_all_results(
            video_id=video_id,
            rendered_clips=rendered_clips,
            public_repo_id=public_repo_id,
            hf_token=hf_token
        )

        # ----------------------------------------------------------------------
        # STAGE 7: DONE!
        # ----------------------------------------------------------------------
        update_status(
            job_id=job_id,
            user_id=user_id,
            status="done",
            message=f"Sukses! {len(uploaded_results)} klip vertikal siap dipublikasikan.",
            video_id=video_id,
            clips=uploaded_results,
            llm_used=llm_used
        )
        print(f"=== Pipeline Selesai Sukses: Job {job_id} ===")

    except Exception as e:
        err_detail = str(e)
        traceback.print_exc()
        print(f"[Fatal Error] Pipeline gagal: {err_detail}")
        update_status(
            job_id=job_id,
            user_id=user_id,
            status="error",
            message=f"Terjadi kesalahan saat memproses video: {err_detail}",
            error=err_detail
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
