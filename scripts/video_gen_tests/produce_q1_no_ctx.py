#!/usr/bin/env python3
"""
Q1 test: 3 clips each for NO (grayish man v7d) and CONTEXT (bluish man v7b_v3_loft).
Same pipeline as produce_q1_v6a.py: short segments, audio trim, HQ frame regen.
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
OUTPUT = Path(__file__).parent / "output" / "election_q01_no_ctx"

# ---- Characters ----
CHAR_GRAYISH = (
    "A Southern European man in his early 30s with curly dark hair, olive skin, brown eyes, "
    "light stubble. He wears a simple light gray henley shirt with sleeves pushed up slightly. "
    "A worn leather watch on his wrist. No other accessories. Calm, focused expression."
)

CHAR_BLUISH = (
    "A Central European man in his mid-30s with short dark hair, clean-shaven, angular jawline, "
    "dark brown eyes. He wears a navy crew-neck merino sweater over a white t-shirt collar. "
    "No jewelry. Natural skin texture with visible stubble shadow. Serious, composed expression."
)

# ---- Settings ----
SETTING_GRAYISH = (
    "A warm modern living room in muted gray-beige tones. Behind him: a concrete-effect wall "
    "in warm medium gray. A low wooden bench with a couple of architecture books and a small "
    "terracotta planter. Soft warm light from the right, as if from a window with linen curtains. "
    "The space feels real and grounded."
)

SETTING_BLUISH = (
    "A converted industrial loft with cool blue undertones. Behind him: exposed concrete columns "
    "and a high ceiling with visible beams. A large steel-framed window on the far wall with "
    "afternoon sun pouring through, casting long warm light shafts across the blue-gray space. "
    "A dark wooden bookcase against the side wall. A green monstera plant catching the sunlight. "
    "The room has genuine architectural depth."
)

CAMERA_GRAY = "Shot on a Leica SL2 with Summilux 75mm f/1.4. Rich warm tones. Cinematic depth. Fine grain."
CAMERA_BLUE = "Shot on a Canon R5 with RF 50mm f/1.2L. Cool shadows, warm highlights. Multiple depth layers. Fine grain."

ANGLE = "Medium shot, straight-on, waist-up. Centered. He looks at camera."

RULES = (
    "ABSOLUTE RULES:\n"
    "1. ZERO text on screen. No subtitles, no captions, no words, no letters, no titles. "
    "Only the man and the room.\n"
    "2. Static locked camera. No transitions, no swipes, no zooms.\n"
    "3. After speaking, he holds PERFECTLY STILL. No nodding, no looking away.\n"
    "4. He speaks naturally in Hungarian at a calm, unhurried pace. "
    "The line is SHORT — he finishes well within 8 seconds."
)

# ---- Hand-crafted SHORT segments ----
NO_SEGMENTS = [
    "Ennél a kérdésnél nézzük meg az ellenérveket a diplomáciai megközelítéssel szemben.",
    "Az Oroszországgal való kétoldalú tárgyalás aláássa az európai egységet a legveszélyesebb pillanatban.",
    "A vétók elszigetelték Magyarországot, és rombolják a NATO-partneri bizalmat.",
]

CTX_SEGMENTS = [
    "Ennél a kérdésnél érdemes szélesebb kontextusban gondolkodni.",
    "Az Alaptörvény Q cikke szerint Magyarország a békére törekszik a világ népeivel.",
    "A SIPRI adatai szerint a fegyverszállítások huszonöt százalékkal nőttek 2019 óta.",
]


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def gen_start_frame(client, char, setting, camera, frames_dir, name):
    from google.genai import types
    out = frames_dir / f"angle_{name}.png"
    if out.exists():
        print(f"  [cached] {out.name}")
        return out
    prompt = f"{char}\n\n{ANGLE}\n\n{setting}\n\n{camera}"
    print(f"  Generating start frame: {name}...")
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


def regenerate_frame_hq(client, screenshot_path, output_path):
    from google.genai import types
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path
    ref = PILImage.open(screenshot_path)
    buf = BytesIO()
    ref.save(buf, format="PNG")
    buf.seek(0)
    prompt = (
        "Reproduce this exact image at higher quality. Keep every detail identical: "
        "the man's exact pose, expression, hair, clothing, and the exact background. "
        "Do NOT change anything. Just output a clean, sharp, high-quality version."
    )
    print(f"    Regenerating frame HQ...")
    resp = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[types.Part.from_bytes(data=buf.read(), mime_type="image/png"), prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    if resp and resp.parts:
        for part in resp.parts:
            if part.inline_data:
                img = PILImage.open(BytesIO(part.inline_data.data))
                img.save(output_path)
                print(f"    HQ: {output_path.name}")
                return output_path
    print(f"    HQ failed, using raw screenshot")
    ref.save(output_path)
    return output_path


def detect_speech_end(clip_path):
    result = subprocess.run(
        ["ffmpeg", "-i", str(clip_path), "-af", "silencedetect=noise=-30dB:d=0.4", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    dur_r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip_path)],
        capture_output=True, text=True,
    )
    total = float(dur_r.stdout.strip())
    silence_starts = [float(s) for s in re.findall(r'silence_start: ([\d.]+)', result.stderr)]
    silence_ends = [float(s) for s in re.findall(r'silence_end: ([\d.]+)', result.stderr)]

    # Find TRAILING silence = extends to clip end, not a mid-sentence pause
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
    print(f"    Speech ends: {speech_end:.1f}s → trim to {trim_end:.1f}s")
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


def produce(client, segments, char, setting, camera, style_name, video_name):
    frames_dir = OUTPUT / "frames"
    clips_dir = OUTPUT / f"clips_{style_name}"
    trimmed_dir = OUTPUT / f"trimmed_{style_name}"
    for d in [frames_dir, clips_dir, trimmed_dir]:
        d.mkdir(parents=True, exist_ok=True)

    total = len(segments)
    print(f"\n{'='*50}")
    print(f"  {video_name} — {total} clips")
    print(f"{'='*50}")

    sf = gen_start_frame(client, char, setting, camera, frames_dir, style_name)

    trimmed = []
    prev_clip = None
    for i, seg in enumerate(segments):
        num = i + 1
        print(f"\n  [{num}/{total}] ({len(seg.split())}w) {seg[:60]}...")

        prompt = (
            f"{char}\n\n{setting}\n\n{ANGLE}\n\n{camera}\n\n"
            f"He speaks in Hungarian: \"{seg}\"\n\n{RULES}"
        )

        if prev_clip and prev_clip.exists():
            raw_lf = frames_dir / f"lf_raw_{style_name}_{num-1:02d}.png"
            extract_last_frame(prev_clip, raw_lf)
            sf_hq = frames_dir / f"lf_hq_{style_name}_{num-1:02d}.png"
            regenerate_frame_hq(client, raw_lf, sf_hq)
            frame = sf_hq
        else:
            frame = sf

        raw = gen_clip(client, num, frame, prompt, clips_dir)
        if raw:
            t = trimmed_dir / f"clip_{num:02d}.mp4"
            trim_to_speech(raw, t)
            trimmed.append(t)
            prev_clip = raw

    if trimmed:
        final = OUTPUT / f"{video_name}.mp4"
        concat(trimmed, final)
        return final


def main():
    if not GEMINI_API_KEY:
        sys.exit("Set GEMINI_API_KEY")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    client = get_client()
    t0 = datetime.now(timezone.utc)

    # NO video — grayish man (v7d)
    produce(client, NO_SEGMENTS, CHAR_GRAYISH, SETTING_GRAYISH, CAMERA_GRAY, "no_gray", "q01_no_test")

    # CONTEXT video — bluish man (v7b_v3_loft)
    produce(client, CTX_SEGMENTS, CHAR_BLUISH, SETTING_BLUISH, CAMERA_BLUE, "ctx_blue", "q01_ctx_test")

    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"\n  All done in {elapsed/60:.1f} min")


if __name__ == "__main__":
    main()
