#!/usr/bin/env python3
"""
Q1 test: 3 clips with v6a warm living room + short segments + audio trim.
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
OUTPUT = Path(__file__).parent / "output" / "election_q01_v6a"

# v5e character
CHARACTER = (
    "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
    "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
    "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
    "bracelet on one wrist. No makeup. Natural skin texture."
)

# v6a warm living room
SETTING = (
    "A modern minimalist living room with warm natural tones. Behind her: a low credenza "
    "in light oak wood with a few books and a small ceramic vase. A large monstera plant "
    "to one side. Walls in warm off-white with subtle texture. A floor lamp with a linen "
    "shade casting soft warm light. Natural daylight from a large window off-frame to the "
    "left creating soft shadows. The space feels lived-in but curated. No harsh studio lighting."
)

CAMERA = (
    "Shot on a Sony A7IV with a Sigma 85mm f/1.4 Art lens at f/2.0. Soft background bokeh. "
    "Warm natural color grading. Fine grain. Real photograph feel."
)

ANGLE_DESC = "Medium shot, straight-on, waist-up. Centered. She looks at camera."

RULES = (
    "ABSOLUTE RULES:\n"
    "1. ZERO text on screen. No subtitles, no captions, no words, no letters, no titles. "
    "Only the woman and the room — nothing else on screen.\n"
    "2. Static locked camera. No transitions, no swipes, no zooms.\n"
    "3. After speaking, she holds PERFECTLY STILL. No nodding, no looking away.\n"
    "4. She speaks naturally in Hungarian at a calm, unhurried pace. "
    "The line is SHORT — she finishes well within 8 seconds."
)

# Hand-crafted SHORT segments for Q1 YES (~10-15 words each, natural Hungarian)
SEGMENTS = [
    "Ennél a kérdésnél arról van szó, hogy Magyarország tárgyaljon-e Oroszországgal a békéért.",
    "Magyarország megvétózta az uniós hitelcsomagokat, és nem küldött fegyvereket Ukrajnába.",
    "Az igen álláspont szerint a diplomácia az egyetlen valódi megoldás erre a helyzetre.",
]


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def gen_start_frame(client, frames_dir):
    from google.genai import types
    out = frames_dir / "angle_main.png"
    if out.exists():
        print(f"  [cached] {out.name}")
        return out
    prompt = f"{CHARACTER}\n\n{SETTING}\n\n{ANGLE_DESC}\n\n{CAMERA}"
    print(f"  Generating start frame...")
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
            print(f"  Saved: {out.name}")
            return out
    sys.exit("ERROR: No image")


def extract_last_frame(video, out):
    """Extract last frame as a raw screenshot."""
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


def regenerate_frame_hq(client, screenshot_path, output_path):
    """Take a screenshot and regenerate it at high quality via Nano Banana.
    Uses the screenshot as reference + detailed prompt to reproduce the exact scene."""
    from google.genai import types

    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    # Load the screenshot
    ref_image = PILImage.open(screenshot_path)

    # Use Gemini with the screenshot as input + instruction to reproduce it
    prompt = (
        f"Reproduce this exact image at higher quality. Keep every detail identical: "
        f"the woman's exact pose, expression, hair position, clothing, hand position, "
        f"and the exact background with all objects in the same position. "
        f"Do NOT change anything — same framing, same lighting, same everything. "
        f"Just output a clean, sharp, high-quality version of this exact frame.\n\n"
        f"Technical: 4K quality, sharp focus, no compression artifacts, no noise. "
        f"The output must look identical to the input but at pristine quality."
    )

    # Upload screenshot as reference
    ref_bytes = BytesIO()
    ref_image.save(ref_bytes, format="PNG")
    ref_bytes.seek(0)

    print(f"    Regenerating frame at HQ...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[
            types.Part.from_bytes(data=ref_bytes.read(), mime_type="image/png"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )

    for part in response.parts:
        if part.inline_data:
            img = PILImage.open(BytesIO(part.inline_data.data))
            img.save(output_path)
            print(f"    HQ frame: {output_path.name} ({img.size[0]}x{img.size[1]})")
            return output_path

    # Fallback: use the screenshot as-is
    print(f"    HQ regen failed, using raw screenshot")
    ref_image.save(output_path)
    return output_path


def detect_speech_end(clip_path):
    """Find where speech ends using volume analysis."""
    # Get per-frame volume levels
    result = subprocess.run(
        ["ffmpeg", "-i", str(clip_path),
         "-af", "silencedetect=noise=-30dB:d=0.4",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    stderr = result.stderr

    # Get total duration
    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total = float(dur_r.stdout.strip())

    # Find all silence periods
    silence_starts = [float(s) for s in re.findall(r'silence_start: ([\d.]+)', stderr)]
    silence_ends = [float(s) for s in re.findall(r'silence_end: ([\d.]+)', stderr)]

    # Find the TRAILING silence = the one that extends to the end of the clip.
    # This is the silence AFTER all speech finishes, not a mid-sentence breath pause.
    for i in range(len(silence_starts)):
        s_end = silence_ends[i] if i < len(silence_ends) else total
        if s_end >= total - 0.5:  # extends to within 0.5s of clip end
            return silence_starts[i]

    # No trailing silence — speech fills the whole clip
    return total


def trim_to_speech(clip_path, out_path, pre_pad=0.5, post_pad=0.5):
    """Trim clip: start at 0, end at speech_end + post_pad."""
    if out_path.exists() and out_path.stat().st_size > 50000:
        return out_path

    speech_end = detect_speech_end(clip_path)

    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total = float(dur_r.stdout.strip())

    trim_end = min(total, speech_end + post_pad)

    print(f"    Speech ends: {speech_end:.1f}s → trimming to {trim_end:.1f}s (of {total:.1f}s)")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(clip_path),
         "-t", str(trim_end),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         str(out_path)],
        capture_output=True, check=True,
    )
    return out_path


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
    print(f"    Raw: {out.name} ({out.stat().st_size/1024/1024:.1f}MB)")
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
    print(f"  Final: {out.name} ({out.stat().st_size/1024/1024:.1f}MB, {float(dur_r.stdout.strip()):.1f}s)")


def main():
    if not GEMINI_API_KEY:
        sys.exit("Set GEMINI_API_KEY")

    frames_dir = OUTPUT / "frames"
    clips_dir = OUTPUT / "clips"
    trimmed_dir = OUTPUT / "trimmed"
    for d in [OUTPUT, frames_dir, clips_dir, trimmed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    client = get_client()
    t0 = datetime.now(timezone.utc)

    print(f"=== Q1 YES — v6a warm living room — {len(SEGMENTS)} clips ===\n")

    # Start frame
    start_frame = gen_start_frame(client, frames_dir)

    # Generate clips
    trimmed = []
    prev_clip = None
    for i, seg in enumerate(SEGMENTS):
        num = i + 1
        print(f"\n  [{num}/{len(SEGMENTS)}] ({len(seg.split())}w) {seg[:60]}...")

        prompt = (
            f"{CHARACTER}\n\n{SETTING}\n\n{ANGLE_DESC}\n\n{CAMERA}\n\n"
            f"She speaks in Hungarian: \"{seg}\"\n\n"
            f"{RULES}"
        )

        # Continuity: extract last frame → regenerate at HQ → use as start frame
        if prev_clip and prev_clip.exists():
            raw_lf = frames_dir / f"lf_raw_{num-1:02d}.png"
            extract_last_frame(prev_clip, raw_lf)
            sf = frames_dir / f"lf_hq_{num-1:02d}.png"
            regenerate_frame_hq(client, raw_lf, sf)
        else:
            sf = start_frame

        raw = gen_clip(client, num, sf, prompt, clips_dir)
        if raw:
            t = trimmed_dir / f"clip_{num:02d}.mp4"
            trim_to_speech(raw, t)
            trimmed.append(t)
            prev_clip = raw

    # Concat
    if trimmed:
        print()
        final = OUTPUT / "q01_yes_v6a_test.mp4"
        concat(trimmed, final)

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\n  Done in {elapsed/60:.1f} min")


if __name__ == "__main__":
    main()
