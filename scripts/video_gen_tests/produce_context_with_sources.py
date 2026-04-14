#!/usr/bin/env python3
"""
Producer: Election Context Video with Source Overlays

Produces the CONTEXT (blue) video for Q1 with:
1. Veo 3.0 clips (no subtitles)
2. Source citation cards overlaid via ffmpeg
3. One Kling comparison clip

Pipeline:
  Nano Banana → start frames
  Veo 3.0 → clips (no subtitles prompt)
  PIL → transparent source card PNGs
  ffmpeg → composite overlays onto clips
  ffmpeg → concatenate final video
  Kling → one comparison clip
"""

import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from textwrap import wrap

import jwt
import requests
from PIL import Image as PILImage, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KLING_ACCESS_KEY = os.environ.get("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.environ.get("KLING_SECRET_KEY", "")
VEO_POLL_TIMEOUT = 300

OUTPUT_BASE = Path("output/election_q01_sources")
FRAMES_DIR = OUTPUT_BASE / "frames"
CLIPS_DIR = OUTPUT_BASE / "clips"
OVERLAY_DIR = OUTPUT_BASE / "overlays"
COMPOSITED_DIR = OUTPUT_BASE / "composited"
KLING_DIR = OUTPUT_BASE / "kling"

for d in [OUTPUT_BASE, FRAMES_DIR, CLIPS_DIR, OVERLAY_DIR, COMPOSITED_DIR, KLING_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Character (v5e Mediterranean)
# ---------------------------------------------------------------------------
CHARACTER = (
    "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
    "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
    "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
    "bracelet on one wrist. No other jewelry, no makeup. Visible natural skin texture, "
    "real human face."
)

SETTING_BLUE = (
    "Medium shot, waist-up framing — no legs visible, no table, no desk, no furniture. "
    "She stands upright. "
    "BACKGROUND: A single monochromatic canvas backdrop in a deep muted blue color "
    "(bright spotlight center ~#4a6a8a, fading to very dark ~#0e1e2e at edges). "
    "A single soft spotlight hits the center behind her, creating a diffused bright area "
    "that smoothly darkens toward all edges — classic portrait vignette. No equipment, "
    "no props, no text. Just the smooth gradient. "
    "LIGHTING: One overhead softbox from above. One key light from upper left creating "
    "gentle modeling on her face with subtle shadow on right side."
)

CAMERA = (
    "Shot on a Leica SL2 with a Summilux 75mm f/1.4 lens. Exceptional subject separation. "
    "Rich warm skin tones. Cinematic depth. Fine organic grain."
)

ANGLES = {
    "medium_front": "Medium shot, straight-on, waist-up. Centered. She looks directly at camera. Minimal movement.",
    "side_left": "Three-quarter shot from 45° left. She has turned slightly to her left. Rim light on right side of face.",
    "closeup_front": "Tight close-up, head and shoulders. Shallow DOF. Eyes tack-sharp. Very still.",
}

HOLD_STILL = (
    "IMPORTANT: After finishing the spoken line, she holds perfectly still — maintaining "
    "eye contact, steady posture, neutral expression. No nodding, no looking away. "
    "The clip ends with her holding position in stillness. "
    "CRITICAL: No camera transitions, no swipe effects, no wipe effects, no zoom transitions, "
    "no cross-dissolves, no scene changes. The camera stays completely locked in position "
    "throughout the entire clip. Static camera, no movement. "
    "Do NOT generate any subtitles, captions, text overlays, or on-screen text. "
    "The video must be clean with no text whatsoever."
)

# ---------------------------------------------------------------------------
# Q1 Context shots with source annotations
# ---------------------------------------------------------------------------
# Each shot: (clip_num, angle, dialogue, sources)
# sources: list of {text, position, appear_at, disappear_at, type}
#   position: "left" or "right"
#   appear_at/disappear_at: seconds into the 8s clip
#   type: "source" (citation) or "stat" (data point)

CONTEXT_SHOTS = [
    {
        "clip": 1,
        "angle": "medium_front",
        "dialogue": (
            "Üdvözlöm. Ma arról a kérdésről beszélünk, hogy Magyarország "
            "tárgyaljon-e Oroszországgal az ukrajnai háború lezárásáért."
        ),
        "sources": [],  # Intro — no sources needed
    },
    {
        "clip": 2,
        "angle": "side_left",
        "dialogue": (
            "Magyarország megvétózta az EU Ukrajnának szánt hitelcsomagjait, "
            "és nem küldött fegyvereket."
        ),
        "sources": [
            {
                "text": "Reuters, 2024.11.19\n\"Hungary blocks €50bn\nEU loan for Ukraine\"",
                "position": "right",
                "appear_at": 1.0,
                "disappear_at": 7.0,
                "type": "source",
            },
        ],
    },
    {
        "clip": 3,
        "angle": "medium_front",
        "dialogue": (
            "Az ellenzéki pártok azt javasolják, hogy Magyarország szüntesse meg "
            "az EU-s támogatást blokkoló vétókat."
        ),
        "sources": [
            {
                "text": "TISZA Manifesto, 2025\n\"End vetoes blocking\nEU support for Ukraine\"",
                "position": "left",
                "appear_at": 0.5,
                "disappear_at": 6.5,
                "type": "source",
            },
        ],
    },
    {
        "clip": 4,
        "angle": "closeup_front",
        "dialogue": (
            "Nézzük meg mindkét oldal érveit. Először az igen, aztán a nem álláspontot."
        ),
        "sources": [
            {
                "text": "European Council\nForeign Affairs\nDecisions 2024-2026",
                "position": "right",
                "appear_at": 1.0,
                "disappear_at": 6.0,
                "type": "source",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Step 2: Generate source card PNGs with PIL (transparent background)
# ---------------------------------------------------------------------------

def create_source_card(text: str, card_type: str, output_path: Path,
                       width: int = 320, padding: int = 16) -> Path:
    """Create a transparent PNG source card with rounded-corner look."""
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
        font_small = font

    # Determine colors based on type
    if card_type == "source":
        bg_color = (0, 0, 0, 180)       # Semi-transparent black
        accent_color = (100, 180, 255)    # Blue accent
        label = "SOURCE"
    else:  # stat
        bg_color = (0, 0, 0, 180)
        accent_color = (100, 255, 150)    # Green accent
        label = "DATA"

    # Calculate text height
    lines = text.split("\n")
    line_height = 26
    total_height = padding + 24 + 8 + (len(lines) * line_height) + padding

    # Create RGBA image
    img = PILImage.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw semi-transparent rounded rectangle background
    draw.rounded_rectangle(
        [0, 0, width - 1, total_height - 1],
        radius=12,
        fill=bg_color,
        outline=(*accent_color, 200),
        width=2,
    )

    # Draw accent label
    draw.text((padding, padding), label, fill=(*accent_color, 255), font=font_small)

    # Draw accent line
    draw.line(
        [(padding, padding + 18), (width - padding, padding + 18)],
        fill=(*accent_color, 120),
        width=1,
    )

    # Draw source text
    y = padding + 28
    for line in lines:
        draw.text((padding, y), line, fill=(255, 255, 255, 240), font=font)
        y += line_height

    img.save(output_path)
    print(f"    Created: {output_path.name} ({width}x{total_height})")
    return output_path


# ---------------------------------------------------------------------------
# Step 3: Veo 3.0 clip generation (no subtitles)
# ---------------------------------------------------------------------------

def get_gemini_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_start_frame(client, angle: str) -> Path:
    from google.genai import types

    output_path = FRAMES_DIR / f"angle_{angle}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    prompt = f"{CHARACTER}\n\n{SETTING_BLUE}\n\n{ANGLES[angle]}\n\n{CAMERA}"
    print(f"    Generating start frame: {angle}...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    for part in response.parts:
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"    Saved: {output_path.name} ({image.size[0]}x{image.size[1]})")
            return output_path
    print(f"    ERROR: No image for {angle}")
    sys.exit(1)


def extract_last_frame(video_path: Path, output_path: Path) -> Path:
    if output_path.exists():
        return output_path
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", str(video_path)],
        capture_output=True, text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(max(0, duration - 0.1)), "-i", str(video_path),
         "-frames:v", "1", "-q:v", "1", str(output_path)],
        capture_output=True, check=True,
    )
    return output_path


def generate_veo_clip(client, clip_num: int, start_frame: Path, prompt: str) -> Path | None:
    from google.genai import types

    output_path = CLIPS_DIR / f"clip_{clip_num:02d}.mp4"
    if output_path.exists() and output_path.stat().st_size > 100000:
        print(f"    [cached] {output_path.name}")
        return output_path

    image = types.Image.from_file(location=str(start_frame))
    print(f"    Submitting Veo 3.0...")

    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(aspect_ratio="16:9", resolution="720p"),
    )

    start = time.time()
    while not operation.done:
        elapsed = int(time.time() - start)
        if elapsed > VEO_POLL_TIMEOUT:
            print(f"    TIMEOUT")
            return None
        print(f"    [{elapsed}s] Generating...")
        time.sleep(15)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        reasons = getattr(operation.response, 'rai_media_filtered_reasons', ['unknown']) if operation.response else ['no response']
        print(f"    FAILED: {reasons}")
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Done in {int(time.time() - start)}s: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


# ---------------------------------------------------------------------------
# Step 4: Composite source overlays via ffmpeg
# ---------------------------------------------------------------------------

def composite_overlay(video_path: Path, sources: list, clip_num: int) -> Path:
    """Overlay source cards onto a video clip using ffmpeg."""
    output_path = COMPOSITED_DIR / f"clip_{clip_num:02d}_sourced.mp4"

    if not sources:
        # No sources — just copy
        subprocess.run(["cp", str(video_path), str(output_path)], check=True)
        print(f"    No overlays for clip {clip_num}")
        return output_path

    # Get video dimensions
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
         "-of", "json", str(video_path)],
        capture_output=True, text=True,
    )
    streams = json.loads(probe.stdout)["streams"][0]
    vid_w, vid_h = int(streams["width"]), int(streams["height"])

    # Build ffmpeg filter chain
    inputs = ["-i", str(video_path)]
    filter_parts = []
    prev_label = "0:v"

    for i, src in enumerate(sources):
        card_path = OVERLAY_DIR / f"clip{clip_num:02d}_src{i:02d}.png"
        create_source_card(src["text"], src["type"], card_path)
        inputs.extend(["-i", str(card_path)])

        # Position: left side or right side (never center third)
        if src["position"] == "left":
            x = 20
        else:
            x = vid_w - 340  # 320px card + 20px margin

        # Vertical: lower third area
        y = vid_h - 200

        in_idx = i + 1
        out_label = f"v{i}"
        enable = f"between(t,{src['appear_at']},{src['disappear_at']})"

        filter_parts.append(
            f"[{prev_label}][{in_idx}:v]overlay=x={x}:y={y}:enable='{enable}'[{out_label}]"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ffmpeg overlay error: {result.stderr[-200:]}")
        # Fallback: copy without overlay
        subprocess.run(["cp", str(video_path), str(output_path)], check=True)
        return output_path

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Composited: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def concatenate(clip_paths: list[Path], output_path: Path) -> None:
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         str(output_path)],
        capture_output=True, check=True,
    )
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Final: {output_path.name} ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Step 5: Kling comparison clip
# ---------------------------------------------------------------------------

def generate_kling_clip(start_frame: Path, prompt: str) -> Path | None:
    """Generate one clip with Kling v3 for comparison."""
    output_path = KLING_DIR / "kling_clip_01.mp4"
    if output_path.exists() and output_path.stat().st_size > 100000:
        print(f"    [cached] {output_path.name}")
        return output_path

    # Read and base64-encode the start frame
    with open(start_frame, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Generate JWT
    now = int(time.time())
    token = jwt.encode(
        {"iss": KLING_ACCESS_KEY, "exp": now + 1800, "nbf": now - 5},
        KLING_SECRET_KEY,
        headers={"alg": "HS256", "typ": "JWT"},
    )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "model_name": "kling-v3",
        "image": img_b64,
        "prompt": prompt,
        "negative_prompt": "blur, low quality, cartoon, anime, distorted face, flickering, morphing, watermark, text overlay, subtitles, captions",
        "duration": "5",
        "mode": "pro",
        "cfg_scale": 0.5,
        "sound": 1,
    }

    print(f"    Submitting to Kling v3...")
    resp = requests.post(
        "https://api.klingai.com/v1/videos/image2video",
        headers=headers, json=payload, timeout=30,
    )
    if resp.status_code != 200:
        print(f"    Kling create error: {resp.status_code} {resp.text[:200]}")
        return None

    task_id = resp.json()["data"]["task_id"]
    print(f"    Task ID: {task_id}")

    # Poll
    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        if elapsed > 300:
            print(f"    TIMEOUT")
            return None

        # Regenerate JWT for each poll (in case it expires)
        now2 = int(time.time())
        token2 = jwt.encode(
            {"iss": KLING_ACCESS_KEY, "exp": now2 + 1800, "nbf": now2 - 5},
            KLING_SECRET_KEY,
            headers={"alg": "HS256", "typ": "JWT"},
        )
        poll_headers = {"Authorization": f"Bearer {token2}", "Content-Type": "application/json"}

        poll = requests.get(
            f"https://api.klingai.com/v1/videos/image2video/{task_id}",
            headers=poll_headers, timeout=30,
        )
        data = poll.json().get("data", {})
        status = data.get("task_status", "unknown")

        if status == "succeed":
            video_url = data["task_result"]["videos"][0]["url"]
            print(f"    Downloading Kling video...")
            vid = requests.get(video_url, timeout=120)
            output_path.write_bytes(vid.content)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")
            return output_path
        elif status == "failed":
            print(f"    Kling FAILED: {data}")
            return None
        else:
            print(f"    [{elapsed}s] Status: {status}")
            time.sleep(10)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    client = get_gemini_client()
    start_time = datetime.now(timezone.utc)

    print("=" * 60)
    print("  Q1 CONTEXT VIDEO WITH SOURCE OVERLAYS")
    print("=" * 60)

    # Phase 1: Generate start frames
    print("\n--- Phase 1: Start frames via Nano Banana ---")
    for shot in CONTEXT_SHOTS:
        generate_start_frame(client, shot["angle"])

    # Phase 2: Generate Veo clips (no subtitles)
    print("\n--- Phase 2: Veo 3.0 clips (no subtitles) ---")
    raw_clips = []
    prev_angle = None
    prev_clip = None

    for shot in CONTEXT_SHOTS:
        clip_num = shot["clip"]
        angle = shot["angle"]
        dialogue = shot["dialogue"]

        same_angle = (prev_angle == angle)
        print(f"\n  Clip {clip_num} — {angle}" + (" (continuation)" if same_angle else ""))

        video_prompt = (
            f"{CHARACTER}\n\n{SETTING_BLUE}\n\n{ANGLES[angle]}\n\n{CAMERA}\n\n"
            f"The presenter speaks in Hungarian with calm, natural delivery: "
            f"'{dialogue}'\n\n{HOLD_STILL}"
        )

        if same_angle and prev_clip and prev_clip.exists():
            start_frame = FRAMES_DIR / f"lastframe_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip, start_frame)
        else:
            start_frame = FRAMES_DIR / f"angle_{angle}.png"

        clip = generate_veo_clip(client, clip_num, start_frame, video_prompt)
        if clip:
            raw_clips.append((clip, shot))
            prev_clip = clip
        else:
            print(f"    SKIPPED clip {clip_num}")

        prev_angle = angle

    # Phase 3: Create source card overlays
    print("\n--- Phase 3: Source card overlays ---")
    for _, shot in raw_clips:
        for i, src in enumerate(shot["sources"]):
            card_path = OVERLAY_DIR / f"clip{shot['clip']:02d}_src{i:02d}.png"
            create_source_card(src["text"], src["type"], card_path)

    # Phase 4: Composite overlays onto clips
    print("\n--- Phase 4: Compositing overlays ---")
    composited_clips = []
    for clip_path, shot in raw_clips:
        composited = composite_overlay(clip_path, shot["sources"], shot["clip"])
        composited_clips.append(composited)

    # Phase 5: Concatenate final video
    print("\n--- Phase 5: Final concatenation ---")
    final_path = OUTPUT_BASE / "q01_context_blue_SOURCED.mp4"
    concatenate(composited_clips, final_path)

    # Phase 6: Kling comparison (one clip)
    print("\n--- Phase 6: Kling v3 comparison clip ---")
    if KLING_ACCESS_KEY and KLING_SECRET_KEY:
        kling_prompt = (
            "A Mediterranean woman with dark wavy hair and olive skin stands in a studio "
            "with a deep blue spotlight backdrop. She speaks calmly in Hungarian: "
            "'Üdvözlöm. Ma arról a kérdésről beszélünk, hogy Magyarország "
            "tárgyaljon-e Oroszországgal az ukrajnai háború lezárásáért.' "
            "Natural delivery, professional tone. Soft studio ambience. "
            "No subtitles, no text on screen."
        )
        kling_frame = FRAMES_DIR / "angle_medium_front.png"
        generate_kling_clip(kling_frame, kling_prompt)
    else:
        print("    SKIPPED: No Kling API keys")

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"  DONE in {elapsed/60:.1f} minutes")
    print(f"  Final video: {final_path}")
    print(f"  Kling clip:  {KLING_DIR / 'kling_clip_01.mp4'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
