#!/usr/bin/env python3
"""
Full 4-minute video production for Q1 — 3 videos (YES/NO/CONTEXT).
Uses enriched scripts from hungary_2026_video_arguments.json.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
VEO_POLL_TIMEOUT = 300
BASE_DIR = Path(__file__).parent
JSON_PATH = BASE_DIR.parent.parent.parent / "ElectOMate-Frontend/HungaryElections2026/hungary_2026_video_arguments.json"
OUTPUT = BASE_DIR / "output" / "election_q01_full"

# v5e Mediterranean character
CHARACTER = (
    "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
    "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
    "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
    "bracelet on one wrist. No other jewelry, no makeup. Visible natural skin texture."
)

CAMERA = (
    "Shot on a Leica SL2 with a Summilux 75mm f/1.4 lens. Exceptional subject separation. "
    "Rich warm skin tones. Cinematic depth. Fine organic grain."
)

BACKGROUNDS = {
    "yes": {"color": "deep muted green", "center": "#4a7a5a", "edge": "#0e2e1a"},
    "no": {"color": "deep muted amber-yellow", "center": "#8a7a4a", "edge": "#2e2410"},
    "context": {"color": "deep muted blue", "center": "#4a6a8a", "edge": "#0e1e2e"},
}

ANGLES = ["medium_front", "side_left", "closeup_front"]
ANGLE_DESCS = {
    "medium_front": "Medium shot, straight-on, waist-up. Centered. She looks at camera. Minimal movement.",
    "side_left": "Three-quarter shot from 45° left. Rim light on right side of face. Same background.",
    "closeup_front": "Tight close-up, head and shoulders. Shallow DOF. Eyes tack-sharp. Very still.",
}

PROMPT_SUFFIX = (
    "IMPORTANT: After finishing speaking, she holds perfectly still — eye contact, "
    "neutral expression, no nodding, no looking away. "
    "No camera transitions, no swipe effects, no wipe, no zoom. Static locked camera. "
    "No subtitles, no captions, no text on screen whatsoever."
)


def make_setting(bg_key):
    bg = BACKGROUNDS[bg_key]
    return (
        f"Medium shot, waist-up — no legs, no table, no furniture. She stands upright. "
        f"BACKGROUND: Single monochromatic canvas in {bg['color']} "
        f"(center ~{bg['center']}, edges ~{bg['edge']}). Soft spotlight vignette. "
        f"LIGHTING: Overhead softbox + key light from upper left."
    )


def split_script(text, max_words=22):
    """Split into segments at sentence boundaries, ~22 words each for 8s clips."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    segments = []
    current = []
    current_words = 0
    for sent in sentences:
        w = len(sent.split())
        if current_words + w > max_words and current:
            segments.append(' '.join(current))
            current = [sent]
            current_words = w
        else:
            current.append(sent)
            current_words += w
    if current:
        segments.append(' '.join(current))
    return segments


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def gen_start_frame(client, angle, bg_key, frames_dir):
    from google.genai import types
    out = frames_dir / f"angle_{bg_key}_{angle}.png"
    if out.exists():
        print(f"    [cached] {out.name}")
        return out
    setting = make_setting(bg_key)
    prompt = f"{CHARACTER}\n\n{setting}\n\n{ANGLE_DESCS[angle]}\n\n{CAMERA}"
    print(f"    Generating {bg_key}/{angle}...")
    resp = client.models.generate_content(
        model="gemini-2.5-flash-image", contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    for part in resp.parts:
        if part.inline_data:
            img = PILImage.open(BytesIO(part.inline_data.data))
            img.save(out)
            print(f"    Saved: {out.name}")
            return out
    print(f"    ERROR: No image")
    sys.exit(1)


def extract_last_frame(video, out):
    if out.exists():
        return out
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True,
    )
    dur = float(json.loads(r.stdout)["format"]["duration"])
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(max(0, dur - 0.1)), "-i", str(video),
         "-frames:v", "1", "-q:v", "1", str(out)],
        capture_output=True, check=True,
    )
    return out


def gen_clip(client, num, start_frame, prompt, clips_dir):
    from google.genai import types
    out = clips_dir / f"clip_{num:02d}.mp4"
    if out.exists() and out.stat().st_size > 100000:
        print(f"    [cached] {out.name}")
        return out

    img = types.Image.from_file(location=str(start_frame))
    print(f"    Veo 3.0...")
    op = client.models.generate_videos(
        model="veo-3.0-generate-001", prompt=prompt, image=img,
        config=types.GenerateVideosConfig(aspect_ratio="16:9", resolution="720p"),
    )
    t0 = time.time()
    while not op.done:
        el = int(time.time() - t0)
        if el > VEO_POLL_TIMEOUT:
            print(f"    TIMEOUT"); return None
        print(f"    [{el}s]...")
        time.sleep(15)
        op = client.operations.get(op)
    if not op.response or not op.response.generated_videos:
        reasons = getattr(op.response, 'rai_media_filtered_reasons', ['?']) if op.response else ['no resp']
        print(f"    FAILED: {reasons}"); return None
    v = op.response.generated_videos[0]
    client.files.download(file=v.video)
    v.video.save(str(out))
    mb = out.stat().st_size / (1024 * 1024)
    print(f"    Done {int(time.time()-t0)}s: {out.name} ({mb:.1f}MB)")
    return out


def concat(clips, out):
    lst = out.parent / "concat.txt"
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
        capture_output=True, check=True,
    )
    print(f"    Final: {out.name} ({out.stat().st_size/1024/1024:.1f}MB)")


def produce_video(client, segments, bg_key, label, video_name):
    frames_dir = OUTPUT / "frames"
    clips_dir = OUTPUT / f"clips_{bg_key}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    setting = make_setting(bg_key)
    total = len(segments)

    print(f"\n{'='*50}")
    print(f"  {label} — {total} clips × 8s = {total*8}s")
    print(f"{'='*50}")

    # Phase 1: Start frames
    print("\n  Start frames:")
    for a in ANGLES:
        gen_start_frame(client, a, bg_key, frames_dir)

    # Phase 2: Clips
    print(f"\n  Generating {total} clips:")
    clips = []
    prev_angle = None
    prev_clip = None

    for i, seg in enumerate(segments):
        num = i + 1
        angle = ANGLES[i % len(ANGLES)]
        same = (angle == prev_angle)

        print(f"\n  [{num}/{total}] {angle} ({len(seg.split())}w)")

        prompt = (
            f"{CHARACTER}\n\n{setting}\n\n{ANGLE_DESCS[angle]}\n\n{CAMERA}\n\n"
            f"She speaks in Hungarian: '{seg}'\n\n{PROMPT_SUFFIX}"
        )

        if same and prev_clip and prev_clip.exists():
            sf = frames_dir / f"lf_{bg_key}_{num-1:02d}.png"
            extract_last_frame(prev_clip, sf)
        else:
            sf = frames_dir / f"angle_{bg_key}_{angle}.png"

        clip = gen_clip(client, num, sf, prompt, clips_dir)
        if clip:
            clips.append(clip)
            prev_clip = clip
        prev_angle = angle

    # Phase 3: Concat
    print(f"\n  Concatenating {len(clips)} clips:")
    final = OUTPUT / f"{video_name}.mp4"
    concat(clips, final)
    return final


def main():
    if not GEMINI_API_KEY:
        print("ERROR: Set GEMINI_API_KEY"); sys.exit(1)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH) as f:
        data = json.load(f)
    q1 = data['questions'][0]
    scripts = q1['video_scripts']

    client = get_client()
    t0 = datetime.now(timezone.utc)

    # Split scripts into segments
    yes_segs = split_script(scripts['type_1_avatar']['full_script'])
    no_segs = split_script(scripts['type_2_debate']['full_script'])
    ctx_segs = split_script(scripts['type_3_analysis']['full_script'])

    print(f"Segments: YES={len(yes_segs)}, NO={len(no_segs)}, CTX={len(ctx_segs)}")
    print(f"Total clips: {len(yes_segs) + len(no_segs) + len(ctx_segs)}")

    # Produce all 3
    v1 = produce_video(client, yes_segs, "yes", "YES (green)", "q01_yes_green_4min")
    v2 = produce_video(client, no_segs, "no", "NO (yellow)", "q01_no_yellow_4min")
    v3 = produce_video(client, ctx_segs, "context", "CONTEXT (blue)", "q01_context_blue_4min")

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\n{'='*50}")
    print(f"  DONE — {elapsed/60:.0f} minutes")
    for v in [v1, v2, v3]:
        if v and v.exists():
            mb = v.stat().st_size / (1024*1024)
            dur_r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                capture_output=True, text=True,
            )
            dur = float(dur_r.stdout.strip()) if dur_r.stdout.strip() else 0
            print(f"  {v.name}: {dur:.0f}s ({dur/60:.1f}min), {mb:.1f}MB")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
