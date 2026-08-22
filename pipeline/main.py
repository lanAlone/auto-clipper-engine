"""
Main Pipeline Orchestrator (Lightweight Two-Phase Architecture)
Mendukung podcast 1-3 jam dengan performa tinggi & hemat resource runner.
"""

import os
import sys
import argparse
import traceback

# Ensure repo root is always in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from pipeline.status import update_status
from pipeline.download import download_audio_and_subtitles, download_clip_section
from pipeline.fetch_user_key import get_user_key
from pipeline.transcribe import transcribe
from pipeline.detect_highlights import detect_highlights
from pipeline.prep_render_props import build_clip_render_props
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
        # STAGE 1: EKSTRAKSI AUDIO & SUBTITLE CEPAT (FASE 1)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "downloading", "Mengambil audio podcast & memeriksa subtitle YouTube...")
        audio_path, video_id, duration_sec, vtt_path = download_audio_and_subtitles(
            url=url,
            user_id=user_id,
            output_dir="work/media"
        )
        print(f"[Pipeline] Video ID: {video_id} (Durasi: {duration_sec/60:.1f} menit)")

        # ----------------------------------------------------------------------
        # STAGE 2: TRANSKRIPSI AUDIO / CACHE / SUBTITLE
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "transcribing", "Menganalisis transkrip percakapan kata-per-kata...", video_id=video_id)
        
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
        # STAGE 3: DETEKSI MOMEN HIGHLIGHT TERBAIK (LLM ROTATION)
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "detecting", "Mendeteksi momen viral & hook terbaik dengan AI...", video_id=video_id)
        
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
        # STAGE 4 & 5: SELECTIVE CLIP DOWNLOAD & REMOTION RENDERING (FASE 2)
        # ----------------------------------------------------------------------
        candidates = clips_dict.get("candidates", [])[:args.clip_count]
        rendered_clips = []
        words = transcript_dict.get("words", [])

        update_status(
            job_id, user_id, "rendering",
            f"Merender {len(candidates)} klip vertikal berkualitas tinggi...",
            video_id=video_id,
            llm_used=llm_used
        )

        for idx, c_data in enumerate(candidates):
            cid = c_data["clip_id"]
            c_start = float(c_data["start"])
            c_end = float(c_data["end"])
            
            print(f"[Pipeline] Memproses Klip #{idx+1}/{len(candidates)} ({cid}) [Rentang: {c_start:.1f}s - {c_end:.1f}s]...")

            # 1. Download potongan klip saja
            section_video_path = download_clip_section(
                url=url,
                user_id=user_id,
                clip_id=cid,
                start_sec=c_start,
                end_sec=c_end,
                output_dir="work/media"
            )

            # 2. Siapkan Props Remotion untuk klip ini
            # Karena video sudah dipotong pas, durasi klip diukur dari 0 sampai (c_end - c_start)
            props_file = build_clip_render_props(
                clip=c_data,
                transcript_words=words,
                source_video_path=section_video_path,
                output_dir="work/render_props",
                crop_mode=args.crop_mode,
                caption_style=args.caption_style
            )

            # 3. Render Klip dengan Remotion CLI
            out_mp4 = f"work/output/{cid}.mp4"
            os.makedirs("work/output", exist_ok=True)
            render_clip(
                props_json_path=props_file,
                output_mp4_path=out_mp4,
                remotion_dir="remotion"
            )

            rendered_clips.append({
                "clip_id": cid,
                "title": c_data.get("title", f"Klip {cid}"),
                "duration": c_data.get("duration", round(c_end - c_start, 1)),
                "mp4_path": out_mp4,
                "hook_reason": c_data.get("hook_reason", ""),
                "viral_score": c_data.get("viral_score", 8.5)
            })

        # ----------------------------------------------------------------------
        # STAGE 6: UPLOAD HASIL KE CLOUD DATASET
        # ----------------------------------------------------------------------
        update_status(job_id, user_id, "uploading", "Mengunggah video klip hasil ke cloud storage...", video_id=video_id, llm_used=llm_used)
        uploaded_results = upload_all_results(
            video_id=video_id,
            rendered_clips=rendered_clips,
            public_repo_id=public_repo_id,
            hf_token=hf_token
        )

        # ----------------------------------------------------------------------
        # STAGE 7: SELESAI
        # ----------------------------------------------------------------------
        update_status(
            job_id=job_id,
            user_id=user_id,
            status="done",
            message=f"Selesai! {len(uploaded_results)} klip 9:16 siap diunduh dan diposting.",
            video_id=video_id,
            clips=uploaded_results,
            llm_used=llm_used
        )
        print(f"=== Pipeline Berhasil Tuntas: Job {job_id} ===")

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
