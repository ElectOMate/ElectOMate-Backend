#!/usr/bin/env python3
"""
Producer: NotHabermas Onboarding Video (~50s)
Generates 7 × 8s clips via Veo 3.0, concatenates with ffmpeg.

KEY DIFFERENCE from other producers:
- Clip 1 uses a provided start image (v6c_cozy_study.png)
- For clips 2+, we extract the last frame of the previous clip,
  feed it to Gemini Nano Banana to REGENERATE a similar-but-refreshed
  pose (not a copy — a better version), and use THAT as the next
  clip's start frame. No raw last-frame reuse.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

from config import GEMINI_API_KEY, OUTPUT_DIR


# --- Production log ---
PRODUCTION_LOG: dict = {
    "run_started": None,
    "run_finished": None,
    "model_image": "gemini-2.5-flash-image",
    "model_video": "veo-3.0-generate-001",
    "pipeline_note": "Gemini-regenerated frames (not raw last-frame reuse)",
    "shots": [],
    "clips_generated": [],
    "clips_failed": [],
    "regenerated_frames": [],
    "final_outputs": [],
}
VEO_POLL_TIMEOUT = 300  # 5 minutes max per clip

# Directories
PROJECT_DIR = OUTPUT_DIR / "nothabermas_onboarding"
FRAMES_DIR = PROJECT_DIR / "frames"
CLIPS_DIR = PROJECT_DIR / "clips"
for d in [PROJECT_DIR, FRAMES_DIR, CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Starting image
START_IMAGE = OUTPUT_DIR / "style_test_v6" / "v6c_cozy_study.png"

# --- Character description for Gemini regeneration ---
CHARACTER_REGEN_PROMPT = (
    "A photorealistic medium shot of a woman in her late 30s with dark wavy hair, "
    "wearing a white linen blouse. She is in a cozy home study with warm-toned wooden "
    "bookshelves filled with books behind her. A vintage Edison bulb hangs to the left. "
    "Natural warm lighting, shallow depth of field, cinematic quality, 16:9 aspect ratio. "
    "She looks directly at the camera with a friendly, approachable expression."
)

# --- Script segments (7 clips × ~8s each = ~56s) ---
SCRIPT_SEGMENTS = [
    # Clip 1 — Welcome
    "Hey! Welcome to NotHabermas. You just got access to your own AI-powered "
    "conversation partner on WhatsApp. Let me quickly show you what you can do.",

    # Clip 2 — Fact-checking
    "First up: fact-checking. Send any claim to the main agent and it will "
    "verify it for you — with real sources. No more forwarding random stuff "
    "without knowing if it's true.",

    # Clip 3 — Mediation
    "Second: mediation. Got a disagreement? The agent can open a group chat "
    "with a mediator that helps both sides find common ground — fairly and "
    "without taking sides.",

    # Clip 4 — Emotional Intelligence
    "Third: emotional intelligence training. You can simulate tough conversations "
    "— family conflicts, workplace tension — in a safe space to practice how you respond.",

    # Clip 5 — How to start
    "To get started, just text the main agent and tell it what you need. "
    "Say 'fact-check', 'mediate', or 'practice' — and you'll be forwarded "
    "into the right group chat.",

    # Clip 6 — Housekeeping
    "One important thing: please don't share this number or add it to any "
    "existing group chats. It won't be able to reply there. This works best "
    "as a one-on-one conversation.",

    # Clip 7 — Close
    "This is still a test version, so bear with us. Happy hackathon, and "
    "have fun exploring! If something breaks, that's just a feature in disguise.",
]

# --- Video prompts per clip ---
SHOTS = []
for i, text in enumerate(SCRIPT_SEGMENTS):
    clip_num = i + 1

    # Vary the camera direction slightly per clip for visual interest
    if clip_num in (1, 4, 7):
        camera = "Medium shot, straight-on, waist-up. Centered composition."
    elif clip_num in (2, 5):
        camera = "Slight three-quarter angle from the left. Warm rim light on right side of face."
    else:
        camera = "Slight three-quarter angle from the right. Soft key light from left."

    prompt = (
        f"{camera} "
        f"The woman speaks warmly and directly to camera: '{text}' "
        f"Natural, conversational delivery. Friendly tone, slight smile. "
        f"Cozy study background with bookshelves. Warm ambient lighting. "
        f"Subtle room tone, no background music."
    )
    SHOTS.append((clip_num, prompt, text))


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def extract_last_frame(video_path: Path, output_path: Path) -> Path:
    """Extract the last frame of a video using ffmpeg."""
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", str(video_path)],
        capture_output=True, text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    seek_time = max(0, duration - 0.1)

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(seek_time), "-i", str(video_path),
         "-frames:v", "1", "-q:v", "1", str(output_path)],
        capture_output=True, check=True,
    )
    print(f"    Extracted last frame: {output_path.name}")
    return output_path


def regenerate_frame_from_reference(client, reference_image_path: Path, clip_num: int) -> Path:
    """
    Feed a reference image to Gemini Nano Banana and ask it to recreate
    a similar-but-refreshed version. NOT a copy — a better pose.
    """
    from google.genai import types

    output_path = FRAMES_DIR / f"regen_clip_{clip_num:02d}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    # Load the reference image
    ref_image = PILImage.open(reference_image_path)
    buf = BytesIO()
    ref_image.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    regen_prompt = (
        "Look at this reference image. Create a NEW photorealistic image of the SAME woman "
        "in the SAME cozy study setting with bookshelves. Keep the same character (dark wavy hair, "
        "white linen blouse) and the same warm lighting. "
        "But make it a FRESH take — a slightly different natural pose, maybe a subtle shift in "
        "expression (warmer smile, or a thoughtful look, or mid-gesture). "
        "Do NOT just copy the image. Recreate the scene with the same person but a new natural moment. "
        "Photorealistic, cinematic, 4K quality, 16:9 aspect ratio, shallow depth of field."
    )

    print(f"    Regenerating frame for clip {clip_num} via Nano Banana...")

    # Retry up to 3 times — Gemini sometimes returns empty responses
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/png",
                                    data=image_bytes,
                                )
                            ),
                            types.Part(text=regen_prompt),
                        ]
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
            if response.parts:
                break
            print(f"    Attempt {attempt + 1}/3: empty response, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"    Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(5)
            response = None

    if response and response.parts:
        pass  # fall through to the loop below
    else:
        print(f"    All attempts returned empty — falling back to text-only")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=CHARACTER_REGEN_PROMPT,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

    for part in (response.parts or []):
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"    Regenerated: {output_path.name} ({image.size[0]}x{image.size[1]})")
            PRODUCTION_LOG["regenerated_frames"].append({
                "clip": clip_num,
                "reference": str(reference_image_path.resolve()),
                "output": str(output_path.resolve()),
                "size": f"{image.size[0]}x{image.size[1]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return output_path

    print(f"    ERROR: No image regenerated for clip {clip_num}")
    # Fallback: generate from text prompt only
    print(f"    Falling back to text-only generation...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=CHARACTER_REGEN_PROMPT,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    for part in (response.parts or []):
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"    Fallback generated: {output_path.name}")
            return output_path

    raise RuntimeError(f"Frame regeneration failed entirely for clip {clip_num}")


def generate_video_clip(client, clip_num: int, start_frame: Path, prompt: str) -> Path | None:
    """Generate an 8-second video clip using Veo 3.0."""
    from google.genai import types

    output_path = CLIPS_DIR / f"clip_{clip_num:02d}.mp4"
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if size_mb > 0.1:
            print(f"    [cached] {output_path.name} ({size_mb:.1f} MB)")
            return output_path

    image = types.Image.from_file(location=str(start_frame))

    print(f"    Submitting Veo 3.0 request...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="720p",
        ),
    )

    start = time.time()
    while not operation.done:
        elapsed = int(time.time() - start)
        if elapsed > VEO_POLL_TIMEOUT:
            print(f"    ERROR: Timed out after {VEO_POLL_TIMEOUT}s for clip {clip_num}")
            PRODUCTION_LOG["clips_failed"].append({
                "type": "video", "clip": clip_num, "reason": "timeout",
            })
            return None
        print(f"    [{elapsed}s] Generating...")
        time.sleep(15)
        operation = client.operations.get(operation)

    elapsed = int(time.time() - start)

    if not operation.response or not operation.response.generated_videos:
        print(f"    ERROR: No video generated for clip {clip_num}")
        PRODUCTION_LOG["clips_failed"].append({
            "type": "video", "clip": clip_num, "reason": "no_response",
        })
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")

    PRODUCTION_LOG["clips_generated"].append({
        "type": "video",
        "clip": clip_num,
        "file": str(output_path.resolve()),
        "size_mb": round(size_mb, 1),
        "generation_time_s": elapsed,
        "prompt": prompt[:120] + "..." if len(prompt) > 120 else prompt,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return output_path


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> None:
    """Concatenate all clips using ffmpeg concat demuxer."""
    concat_file = PROJECT_DIR / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_file),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         str(output_path)],
        capture_output=True, check=True,
    )
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Final video: {output_path} ({size_mb:.1f} MB)")


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    if not START_IMAGE.exists():
        print(f"ERROR: Start image not found: {START_IMAGE}")
        sys.exit(1)

    PRODUCTION_LOG["run_started"] = datetime.now(timezone.utc).isoformat()
    PRODUCTION_LOG["start_image"] = str(START_IMAGE.resolve())
    PRODUCTION_LOG["shots"] = [
        {"clip": n, "prompt": p[:120], "script": t}
        for n, p, t in SHOTS
    ]

    client = get_client()
    num_clips = len(SHOTS)
    clip_paths: list[Path] = []

    print("=" * 60)
    print("  NOTHABERMAS ONBOARDING VIDEO — PRODUCTION")
    print(f"  {num_clips} clips x 8s = ~{num_clips * 8}s")
    print("  Pipeline: Gemini-regenerated frames (no raw last-frame reuse)")
    print("=" * 60)

    # Copy start image to frames dir for reference
    import shutil
    start_copy = FRAMES_DIR / "start_original.png"
    if not start_copy.exists():
        shutil.copy2(START_IMAGE, start_copy)

    prev_clip_path: Path | None = None

    for clip_num, prompt, script_text in SHOTS:
        print(f"\n  Clip {clip_num:02d}/{num_clips}")
        print(f"  Script: {script_text[:60]}...")

        if clip_num == 1:
            # First clip uses the provided start image directly
            start_frame = START_IMAGE
            print(f"    Using original start image: {START_IMAGE.name}")
        else:
            # Extract last frame from previous clip
            lastframe_path = FRAMES_DIR / f"lastframe_clip_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip_path, lastframe_path)

            # Feed to Gemini to regenerate a similar-but-refreshed frame
            start_frame = regenerate_frame_from_reference(
                client, lastframe_path, clip_num
            )

        clip_path = generate_video_clip(client, clip_num, start_frame, prompt)
        if clip_path:
            clip_paths.append(clip_path)
            prev_clip_path = clip_path
        else:
            print(f"    SKIPPING clip {clip_num} due to generation failure")

    # Concatenate
    print(f"\n--- Concatenating {len(clip_paths)} clips ---")
    final_output = PROJECT_DIR / "nothabermas_onboarding_FINAL.mp4"
    concatenate_clips(clip_paths, final_output)

    PRODUCTION_LOG["final_outputs"].append(str(final_output.resolve()))

    # Verify
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration,size", "-of", "json", str(final_output)],
        capture_output=True, text=True,
    )
    info = json.loads(result.stdout)["format"]
    duration = float(info["duration"])
    size_mb = int(info["size"]) / (1024 * 1024)

    PRODUCTION_LOG["run_finished"] = datetime.now(timezone.utc).isoformat()
    PRODUCTION_LOG["final_duration_s"] = round(duration, 2)
    PRODUCTION_LOG["final_size_mb"] = round(size_mb, 1)
    PRODUCTION_LOG["total_clips"] = len(clip_paths)
    PRODUCTION_LOG["clips_failed_count"] = len(PRODUCTION_LOG["clips_failed"])

    # Write production log
    log_path = PROJECT_DIR / "production_log.json"
    with open(log_path, "w") as f:
        json.dump(PRODUCTION_LOG, f, indent=2, ensure_ascii=False)
    print(f"\n  Production log: {log_path.resolve()}")

    # Summary
    print("\n" + "=" * 60)
    print("  PRODUCTION COMPLETE")
    print("=" * 60)
    print(f"  Final video:  {final_output.resolve()}")
    print(f"  Clips:        {CLIPS_DIR.resolve()}/")
    print(f"  Frames:       {FRAMES_DIR.resolve()}/")
    print(f"  Duration:     {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"  Size:         {size_mb:.1f} MB")
    print(f"  Log:          {log_path.resolve()}")

    # Show regenerated frames
    regen_frames = sorted(FRAMES_DIR.glob("regen_clip_*.png"))
    if regen_frames:
        print(f"\n  Regenerated frames (Nano Banana):")
        for f in regen_frames:
            print(f"    {f.resolve()}")

    lastframes = sorted(FRAMES_DIR.glob("lastframe_clip_*.png"))
    if lastframes:
        print(f"\n  Last frames (extracted from clips):")
        for f in lastframes:
            print(f"    {f.resolve()}")


if __name__ == "__main__":
    main()
