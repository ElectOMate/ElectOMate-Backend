#!/usr/bin/env python3
"""
Q1 FULL production — 3 videos (YES/NO/CONTEXT), ~4 min each.
- Raw last-frame continuity (no HQ regen — avoids Veo safety filter)
- Trailing-silence audio trimming
- Max 14 words per segment
- Strong anti-subtitle prompting
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
ROOT = Path(__file__).parent.parent.parent.parent
JSON_PATH = ROOT / "ElectOMate-Frontend/HungaryElections2026/hungary_2026_video_arguments.json"
OUTPUT = Path(__file__).parent / "output" / "election_q01_final"

# ---------------------------------------------------------------------------
# Characters & Settings
# ---------------------------------------------------------------------------
CONFIGS = {
    "yes": {
        "character": (
            "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
            "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
            "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
            "bracelet on one wrist. No makeup. Natural skin texture."
        ),
        "setting": (
            "A modern minimalist living room with warm natural tones. Behind her: a low credenza "
            "in light oak wood with a few books and a small ceramic vase. A large monstera plant "
            "to one side. Walls in warm off-white. A floor lamp with a linen shade casting soft "
            "warm light. Natural daylight from a large window to the left. Lived-in but curated."
        ),
        "camera": "Shot on a Sony A7IV with Sigma 85mm f/1.4 at f/2.0. Warm natural color grading. Soft bokeh. Fine grain.",
        "angle": "Medium shot, straight-on, waist-up. Centered. She looks at camera.",
        "pronoun": "She",
    },
    "no": {
        "character": (
            "A Southern European man in his early 30s with curly dark hair, olive skin, brown eyes, "
            "light stubble. He wears a simple light gray henley shirt with sleeves pushed up. "
            "A worn leather watch on his wrist. No other accessories. Calm, focused expression."
        ),
        "setting": (
            "A warm modern living room in muted gray-beige tones. Behind him: a concrete-effect wall "
            "in warm medium gray. A low wooden bench with architecture books and a small terracotta "
            "planter. Soft warm light from the right, as from a window with linen curtains. Real, grounded."
        ),
        "camera": "Shot on a Leica SL2 with Summilux 75mm f/1.4. Rich warm tones. Cinematic depth. Fine grain.",
        "angle": "Medium shot, straight-on, waist-up. Centered. He looks at camera.",
        "pronoun": "He",
    },
    "context": {
        "character": (
            "A Central European man in his mid-30s with short dark hair, clean-shaven, angular jawline, "
            "dark brown eyes. He wears a navy crew-neck merino sweater over a white t-shirt collar. "
            "No jewelry. Natural skin texture. Serious, composed expression."
        ),
        "setting": (
            "A converted industrial loft with cool blue undertones. Behind him: exposed concrete columns "
            "and high ceiling with visible beams. A large steel-framed window with afternoon sun pouring "
            "through, casting warm light shafts. A dark wooden bookcase. A monstera catching sunlight. "
            "Real architectural depth."
        ),
        "camera": "Shot on a Canon R5 with RF 50mm f/1.2L. Cool shadows, warm highlights. Multiple depth layers. Fine grain.",
        "angle": "Medium shot, straight-on, waist-up. Centered. He looks at camera.",
        "pronoun": "He",
    },
}

RULES = (
    "ABSOLUTE RULES:\n"
    "1. ZERO text on screen. No subtitles, no captions, no words, no letters, no titles, "
    "no lower thirds, no watermarks. Only the person and the room.\n"
    "2. Static locked camera. No transitions, no swipes, no zooms, no pans.\n"
    "3. After speaking, holds PERFECTLY STILL. No nodding, no looking away.\n"
    "4. Speaks naturally in Hungarian at calm unhurried pace. "
    "The line is SHORT — finishes well within 8 seconds."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_script(text, max_words=14):
    """Split into segments at sentence boundaries, max 14 words.
    Splits long sentences at commas."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    raw_segs = []
    cur = []
    cw = 0
    for sent in sentences:
        w = len(sent.split())
        if cw + w > max_words and cur:
            raw_segs.append(' '.join(cur))
            cur = [sent]
            cw = w
        else:
            cur.append(sent)
            cw += w
    if cur:
        raw_segs.append(' '.join(cur))

    # Split any remaining long segments at commas
    final = []
    for seg in raw_segs:
        words = seg.split()
        if len(words) > max_words:
            # Try splitting at comma nearest to middle
            comma_positions = [i for i, w in enumerate(words) if ',' in w]
            if comma_positions:
                mid = len(words) // 2
                best = min(comma_positions, key=lambda x: abs(x - mid))
                final.append(' '.join(words[:best + 1]))
                final.append(' '.join(words[best + 1:]))
            else:
                # Hard split at middle
                mid = len(words) // 2
                final.append(' '.join(words[:mid]))
                final.append(' '.join(words[mid:]))
        else:
            final.append(seg)

    return [s for s in final if s.strip()]


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def gen_start_frame(client, cfg, frames_dir, name):
    from google.genai import types
    out = frames_dir / f"start_{name}.png"
    if out.exists():
        print(f"    [cached] {out.name}")
        return out
    prompt = f"{cfg['character']}\n\n{cfg['setting']}\n\n{cfg['angle']}\n\n{cfg['camera']}"
    print(f"    Generating start frame: {name}...")
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
    sys.exit(f"ERROR: No image for {name}")


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


def detect_speech_end(clip_path):
    """Find trailing silence — the silence that extends to the clip's end."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(clip_path), "-af", "silencedetect=noise=-30dB:d=0.3",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total = float(dur_r.stdout.strip())
    silence_starts = [float(s) for s in re.findall(r'silence_start: ([\d.]+)', result.stderr)]
    silence_ends = [float(s) for s in re.findall(r'silence_end: ([\d.]+)', result.stderr)]

    for i in range(len(silence_starts)):
        s_end = silence_ends[i] if i < len(silence_ends) else total
        if s_end >= total - 0.5:
            return silence_starts[i]
    return total


def trim_to_speech(clip_path, out_path):
    if out_path.exists() and out_path.stat().st_size > 50000:
        return out_path
    speech_end = detect_speech_end(clip_path)
    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total = float(dur_r.stdout.strip())
    trim_end = min(total, speech_end + 0.5)
    print(f"      Trim: speech ends {speech_end:.1f}s → {trim_end:.1f}s (of {total:.1f}s)")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(clip_path), "-t", str(trim_end),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)],
        capture_output=True, check=True,
    )
    return out_path


def gen_clip(client, num, start_frame, prompt, clips_dir):
    from google.genai import types
    out = clips_dir / f"clip_{num:02d}.mp4"
    if out.exists() and out.stat().st_size > 100000:
        print(f"      [cached] {out.name}")
        return out
    img = types.Image.from_file(location=str(start_frame))
    print(f"      Veo 3.0...")
    try:
        op = client.models.generate_videos(
            model="veo-3.0-generate-001", prompt=prompt, image=img,
            config=types.GenerateVideosConfig(aspect_ratio="16:9", resolution="720p"),
        )
    except Exception as e:
        print(f"      API ERROR: {e}")
        return None

    t0 = time.time()
    while not op.done:
        el = int(time.time() - t0)
        if el > VEO_POLL_TIMEOUT:
            print(f"      TIMEOUT"); return None
        print(f"      [{el}s]...")
        time.sleep(15)
        try:
            op = client.operations.get(op)
        except Exception as e:
            print(f"      POLL ERROR: {e}")
            return None
    if not op.response or not op.response.generated_videos:
        reasons = getattr(op.response, 'rai_media_filtered_reasons', ['?']) if op.response else ['none']
        print(f"      FILTERED: {reasons}")
        return None
    v = op.response.generated_videos[0]
    client.files.download(file=v.video)
    v.video.save(str(out))
    print(f"      Done: {out.name} ({out.stat().st_size/1024/1024:.1f}MB)")
    return out


def concat(clips, out):
    lst = out.parent / f"concat_{out.stem}.txt"
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
    print(f"    FINAL: {out.name} ({out.stat().st_size/1024/1024:.1f}MB, {dur:.0f}s = {dur/60:.1f}min)")


def produce_video(client, script_key, video_type, video_name):
    cfg = CONFIGS[video_type]
    frames_dir = OUTPUT / "frames"
    clips_dir = OUTPUT / f"clips_{video_type}"
    trimmed_dir = OUTPUT / f"trimmed_{video_type}"
    for d in [frames_dir, clips_dir, trimmed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Load script
    with open(JSON_PATH) as f:
        data = json.load(f)
    q1 = data['questions'][0]
    full_text = q1['video_scripts'][script_key]['full_script']
    segments = split_script(full_text, max_words=14)

    print(f"\n{'='*60}")
    print(f"  {video_name}")
    print(f"  {len(segments)} segments, {sum(len(s.split()) for s in segments)} words")
    print(f"  Est. duration: ~{len(segments) * 6}s ({len(segments) * 6 / 60:.1f}min)")
    print(f"{'='*60}")

    # Start frame
    start_frame = gen_start_frame(client, cfg, frames_dir, video_type)

    # Generate clips
    trimmed_clips = []
    prev_clip = None
    failed = 0

    for i, seg in enumerate(segments):
        num = i + 1
        print(f"\n    [{num}/{len(segments)}] ({len(seg.split())}w) {seg[:55]}...")

        prompt = (
            f"{cfg['character']}\n\n{cfg['setting']}\n\n{cfg['angle']}\n\n{cfg['camera']}\n\n"
            f"{cfg['pronoun']} speaks in Hungarian: \"{seg}\"\n\n{RULES}"
        )

        # Use raw last frame for continuity (no HQ regen)
        if prev_clip and prev_clip.exists():
            sf = frames_dir / f"lf_{video_type}_{num-1:02d}.png"
            extract_last_frame(prev_clip, sf)
        else:
            sf = start_frame

        raw = gen_clip(client, num, sf, prompt, clips_dir)
        if raw:
            t = trimmed_dir / f"clip_{num:02d}.mp4"
            trim_to_speech(raw, t)
            trimmed_clips.append(t)
            prev_clip = raw
        else:
            failed += 1
            # Don't update prev_clip — next clip will use the last successful frame

    # Concat
    if trimmed_clips:
        final = OUTPUT / f"{video_name}.mp4"
        concat(trimmed_clips, final)
        print(f"    Clips: {len(trimmed_clips)}/{len(segments)} (failed: {failed})")
        return final
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        sys.exit("Set GEMINI_API_KEY")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    client = get_client()
    t0 = datetime.now(timezone.utc)

    results = []

    # YES video (type_1_avatar) — Mediterranean woman, warm living room
    v1 = produce_video(client, "type_1_avatar", "yes", "q01_yes_full")
    results.append(("YES (green/warm)", v1))

    # NO video (type_2_debate) — Grayish man
    v2 = produce_video(client, "type_2_debate", "no", "q01_no_full")
    results.append(("NO (gray)", v2))

    # CONTEXT video (type_3_analysis) — Bluish loft man
    v3 = produce_video(client, "type_3_analysis", "context", "q01_context_full")
    results.append(("CONTEXT (blue)", v3))

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\n{'='*60}")
    print(f"  ALL DONE — {elapsed/60:.0f} minutes")
    for label, path in results:
        if path and path.exists():
            dur_r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                capture_output=True, text=True,
            )
            dur = float(dur_r.stdout.strip())
            mb = path.stat().st_size / (1024 * 1024)
            print(f"  {label}: {path.name} — {dur:.0f}s ({dur/60:.1f}min), {mb:.1f}MB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
