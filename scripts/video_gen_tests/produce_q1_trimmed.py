#!/usr/bin/env python3
"""
Q1 video production with:
- Strong anti-subtitle prompting
- Audio-based clip trimming (0.7s before speech, 0.5s after speech)
- Configurable clip limit for testing
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
OUTPUT = BASE_DIR / "output" / "election_q01_trimmed"

# How many clips to render (set low for testing)
MAX_CLIPS = int(os.environ.get("MAX_CLIPS", "3"))

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
    "medium_front": "Medium shot, straight-on, waist-up. Centered. She looks at camera.",
    "side_left": "Three-quarter from 45° left. Rim light on right side of face.",
    "closeup_front": "Tight close-up, head and shoulders. Shallow DOF. Eyes sharp.",
}

# VERY strong anti-subtitle + anti-transition + hold-still prompt
PROMPT_RULES = (
    "ABSOLUTE RULES — MUST FOLLOW ALL:\n"
    "1. ZERO text on screen. No subtitles. No captions. No words. No letters. No titles. "
    "No lower thirds. No name plates. No watermarks. The video frame must contain ONLY "
    "the woman and the background — nothing else.\n"
    "2. Static locked camera. No transitions, no swipes, no wipes, no zooms, no pans.\n"
    "3. After she finishes speaking, she holds PERFECTLY STILL with neutral expression. "
    "No nodding, no looking away, no extra gestures.\n"
    "4. She speaks naturally in Hungarian. The dialogue is SHORT — she can finish it "
    "well within 8 seconds with natural pacing, not rushed."
)


def make_setting(bg_key):
    bg = BACKGROUNDS[bg_key]
    return (
        f"Waist-up framing, no furniture. She stands upright. "
        f"Single monochromatic canvas backdrop in {bg['color']} "
        f"(center ~{bg['center']}, edges ~{bg['edge']}). Soft spotlight vignette. "
        f"Overhead softbox + key light from upper left."
    )


def split_script(text, max_words=18):
    """Split into SHORT segments (~18 words) so speech fits in 8 seconds."""
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
    sys.exit(f"ERROR: No image for {bg_key}/{angle}")


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


def detect_speech_boundaries(clip_path):
    """Detect when speech starts and ends using ffmpeg silencedetect.
    Returns (speech_start, speech_end) in seconds."""
    duration_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total_dur = float(duration_r.stdout.strip())

    # Detect silence periods (threshold -35dB, min duration 0.2s)
    result = subprocess.run(
        ["ffmpeg", "-i", str(clip_path), "-af", "silencedetect=noise=-35dB:d=0.2",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    stderr = result.stderr

    silences = []
    starts = re.findall(r'silence_start: ([\d.]+)', stderr)
    ends = re.findall(r'silence_end: ([\d.]+)', stderr)

    for s, e in zip(starts, ends):
        silences.append((float(s), float(e)))

    # Also catch trailing silence (silence_start without matching end)
    if len(starts) > len(ends):
        silences.append((float(starts[-1]), total_dur))

    if not silences:
        # No silence detected — speech fills the whole clip
        return 0.0, total_dur

    # Speech starts after the first silence ends (or at 0 if no leading silence)
    speech_start = 0.0
    if silences and silences[0][0] < 0.5:  # Leading silence
        speech_start = silences[0][1]

    # Speech ends at the start of trailing silence
    speech_end = total_dur
    if silences and silences[-1][1] >= total_dur - 0.3:  # Trailing silence
        speech_end = silences[-1][0]

    return speech_start, speech_end


def trim_clip(clip_path, trimmed_path, pre_pad=0.7, post_pad=0.5):
    """Trim clip to speech boundaries with padding."""
    if trimmed_path.exists() and trimmed_path.stat().st_size > 50000:
        return trimmed_path

    speech_start, speech_end = detect_speech_boundaries(clip_path)

    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total_dur = float(dur_r.stdout.strip())

    trim_start = max(0, speech_start - pre_pad)
    trim_end = min(total_dur, speech_end + post_pad)
    trim_duration = trim_end - trim_start

    print(f"    Audio: {speech_start:.1f}s-{speech_end:.1f}s | "
          f"Trim: {trim_start:.1f}s-{trim_end:.1f}s ({trim_duration:.1f}s)")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(clip_path),
         "-ss", str(trim_start), "-t", str(trim_duration),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         str(trimmed_path)],
        capture_output=True, check=True,
    )
    return trimmed_path


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
        reasons = getattr(op.response, 'rai_media_filtered_reasons', ['?']) if op.response else ['none']
        print(f"    FAILED: {reasons}"); return None
    v = op.response.generated_videos[0]
    client.files.download(file=v.video)
    v.video.save(str(out))
    mb = out.stat().st_size / (1024 * 1024)
    print(f"    Raw: {out.name} ({mb:.1f}MB)")
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
    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    dur = float(dur_r.stdout.strip())
    print(f"    Final: {out.name} ({out.stat().st_size/1024/1024:.1f}MB, {dur:.1f}s)")


def produce_video(client, segments, bg_key, label, video_name, max_clips):
    frames_dir = OUTPUT / "frames"
    clips_dir = OUTPUT / f"clips_{bg_key}"
    trimmed_dir = OUTPUT / f"trimmed_{bg_key}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    trimmed_dir.mkdir(parents=True, exist_ok=True)

    setting = make_setting(bg_key)
    segments = segments[:max_clips]
    total = len(segments)

    print(f"\n{'='*50}")
    print(f"  {label} — {total} clips (limited to {max_clips})")
    print(f"{'='*50}")

    # Start frames
    print("\n  Start frames:")
    for a in ANGLES:
        gen_start_frame(client, a, bg_key, frames_dir)

    # Generate + trim clips
    print(f"\n  Generating {total} clips:")
    trimmed_clips = []
    prev_angle = None
    prev_clip = None

    for i, seg in enumerate(segments):
        num = i + 1
        angle = ANGLES[i % len(ANGLES)]
        same = (angle == prev_angle)

        print(f"\n  [{num}/{total}] {angle} ({len(seg.split())}w): {seg[:60]}...")

        prompt = (
            f"{CHARACTER}\n\n{setting}\n\n{ANGLE_DESCS[angle]}\n\n{CAMERA}\n\n"
            f"She speaks in Hungarian: \"{seg}\"\n\n"
            f"{PROMPT_RULES}"
        )

        if same and prev_clip and prev_clip.exists():
            sf = frames_dir / f"lf_{bg_key}_{num-1:02d}.png"
            extract_last_frame(prev_clip, sf)
        else:
            sf = frames_dir / f"angle_{bg_key}_{angle}.png"

        raw_clip = gen_clip(client, num, sf, prompt, clips_dir)
        if raw_clip:
            # Trim based on audio
            trimmed = trimmed_dir / f"clip_{num:02d}_trimmed.mp4"
            trim_clip(raw_clip, trimmed)
            trimmed_clips.append(trimmed)
            prev_clip = raw_clip
        prev_angle = angle

    # Concat trimmed clips
    if trimmed_clips:
        print(f"\n  Concatenating {len(trimmed_clips)} trimmed clips:")
        final = OUTPUT / f"{video_name}.mp4"
        concat(trimmed_clips, final)
        return final
    return None


def main():
    if not GEMINI_API_KEY:
        sys.exit("ERROR: Set GEMINI_API_KEY")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH) as f:
        data = json.load(f)
    q1 = data['questions'][0]
    scripts = q1['video_scripts']

    client = get_client()
    t0 = datetime.now(timezone.utc)

    yes_segs = split_script(scripts['type_1_avatar']['full_script'], max_words=18)
    no_segs = split_script(scripts['type_2_debate']['full_script'], max_words=18)
    ctx_segs = split_script(scripts['type_3_analysis']['full_script'], max_words=18)

    print(f"Full segments: YES={len(yes_segs)}, NO={len(no_segs)}, CTX={len(ctx_segs)}")
    print(f"Rendering first {MAX_CLIPS} clips of YES video only (for testing)")

    v1 = produce_video(client, yes_segs, "yes", "YES (green)", "q01_yes_test", MAX_CLIPS)

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\n{'='*50}")
    print(f"  TEST DONE — {elapsed/60:.1f} min")
    if v1 and v1.exists():
        print(f"  {v1.name}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
