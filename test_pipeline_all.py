import sys
import os

# Add repo root to sys.path
REPO_ROOT = r"C:\Users\Kenzie kafi\.gemini\antigravity-ide\scratch\auto-clipper\auto-clipper-engine"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

print("Testing Pipeline Units...")

# 1. Test Download helpers
from pipeline.download import extract_video_id
vid1 = extract_video_id("https://youtu.be/pHK2UxwfaL0?si=7KfrpT2eC2O4KZ-T")
vid2 = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
vid3 = extract_video_id("https://youtube.com/shorts/abcd1234efg")
assert vid1 == "pHK2UxwfaL0", f"Expected pHK2UxwfaL0, got {vid1}"
assert vid2 == "dQw4w9WgXcQ", f"Expected dQw4w9WgXcQ, got {vid2}"
assert vid3 == "abcd1234efg", f"Expected abcd1234efg, got {vid3}"
print("[PASS] extract_video_id")

# 2. Test VTT Timestamp parsing
from pipeline.transcribe import parse_vtt_timestamp
ts1 = parse_vtt_timestamp("00:01:23.456")
ts2 = parse_vtt_timestamp("02:15.800")
assert round(ts1, 2) == 83.46
assert round(ts2, 2) == 135.80
print("[PASS] parse_vtt_timestamp")

# 3. Test Word-level Snapping
from pipeline.detect_highlights import snap_timestamps_to_words
mock_words = [
    {"word": "Halo", "start": 10.2, "end": 10.6},
    {"word": "teman-teman", "start": 10.7, "end": 11.4},
    {"word": "selamat", "start": 11.5, "end": 12.0},
    {"word": "datang", "start": 12.1, "end": 12.8},
    {"word": "di", "start": 12.9, "end": 13.1},
    {"word": "podcast", "start": 13.2, "end": 13.9},
    {"word": "kita", "start": 14.0, "end": 14.4},
    {"word": "hari", "start": 40.0, "end": 40.5},
    {"word": "ini", "start": 40.6, "end": 41.0}
]
s, e = snap_timestamps_to_words(10.0, 40.8, mock_words, 100.0)
assert s >= 0 and e <= 100.0
print(f"[PASS] snap_timestamps_to_words: {s} -> {e}")

# 4. Test LLM JSON cleaning
from pipeline.llm_router import clean_json_markdown
cleaned = clean_json_markdown("```json\n{\"candidates\": []}\n```")
assert cleaned == "{\"candidates\": []}"
print("[PASS] clean_json_markdown")

# 5. Test Props Building
from pipeline.prep_render_props import build_clip_render_props
clip_data = {
    "clip_id": "c1",
    "title": "Uji Coba Klip",
    "start": 10.0,
    "end": 40.0,
    "hook_reason": "Hook yang kuat",
    "viral_score": 9.2
}
os.makedirs("work/test_render_props", exist_ok=True)
props_path = build_clip_render_props(
    clip=clip_data,
    transcript_words=mock_words,
    source_video_path="dummy_source.mp4",
    output_dir="work/test_render_props",
    crop_mode="blurred_stack",
    caption_style="bold_yellow"
)
assert os.path.exists(props_path)
print(f"[PASS] build_clip_render_props: {props_path}")

print("\n=== ALL PIPELINE UNIT TESTS PASSED (100% GREEN) ===")
