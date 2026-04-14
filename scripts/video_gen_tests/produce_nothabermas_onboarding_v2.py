#!/usr/bin/env python3
"""
Producer: NotHabermas Onboarding Video v2 (~50s)

Pipeline:
1. Print ALL prompts (image + video) upfront
2. Generate ALL 7 start frames via Nano Banana FIRST (no last-frame extraction ever)
3. Generate ALL 7 video clips via Veo 3.0
4. Concatenate into final video

Each clip gets its own freshly generated start frame from Nano Banana.
No screenshots of last frames. No frame degradation.
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
    "pipeline": "all-frames-upfront (no last-frame extraction)",
    "image_prompts": [],
    "video_prompts": [],
    "frames_generated": [],
    "clips_generated": [],
    "clips_failed": [],
    "final_outputs": [],
}
VEO_POLL_TIMEOUT = 300

# Directories
PROJECT_DIR = OUTPUT_DIR / "nothabermas_onboarding_v2"
FRAMES_DIR = PROJECT_DIR / "frames"
CLIPS_DIR = PROJECT_DIR / "clips"
for d in [PROJECT_DIR, FRAMES_DIR, CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Base character description ---
CHARACTER_BASE = (
    "A photorealistic shot of a woman in her late 30s with dark wavy shoulder-length hair, "
    "wearing a white linen blouse. She is in a cozy home study with warm-toned wooden "
    "bookshelves filled with books behind her. A vintage Edison bulb hangs to the left. "
    "Natural warm lighting, shallow depth of field, cinematic quality, 4K, 16:9 aspect ratio."
)

# --- Per-clip image prompts (varied poses/expressions for visual interest) ---
IMAGE_PROMPTS = {
    1: (
        f"{CHARACTER_BASE} "
        "Medium shot, straight-on, waist-up. She looks directly at camera with a warm, "
        "welcoming smile. Hands resting naturally on the desk in front of her. "
        "Inviting, open body language."
    ),
    2: (
        f"{CHARACTER_BASE} "
        "Medium shot, slight three-quarter angle from the left. She has an engaged, "
        "informative expression — eyebrows slightly raised, mouth slightly open as if "
        "about to explain something. One hand slightly raised in a gentle explaining gesture."
    ),
    3: (
        f"{CHARACTER_BASE} "
        "Medium shot, slight three-quarter angle from the right. She looks thoughtful "
        "and empathetic. Hands together in front of her. A calm, mediating presence. "
        "Soft key light from the left side."
    ),
    4: (
        f"{CHARACTER_BASE} "
        "Medium shot, straight-on. She has a warm, encouraging expression. "
        "Leaning forward slightly, hands open in a supportive gesture. "
        "Conveying care and understanding."
    ),
    5: (
        f"{CHARACTER_BASE} "
        "Medium shot, slight three-quarter angle from the left. She looks enthusiastic "
        "and practical. One hand gesturing toward camera as if giving instructions. "
        "Friendly, helpful energy. Warm rim light on the right."
    ),
    6: (
        f"{CHARACTER_BASE} "
        "Medium shot, slight three-quarter angle from the right. She has a more serious, "
        "earnest expression — like sharing an important reminder. Slight head tilt. "
        "One finger gently raised. Still warm and approachable."
    ),
    7: (
        f"{CHARACTER_BASE} "
        "Medium shot, straight-on. She has a big, genuine smile — a warm sign-off. "
        "Relaxed posture, maybe a small wave or thumbs up. Bright, friendly energy. "
        "The warmest and most inviting frame of all."
    ),
}

# --- Script segments ---
SCRIPT_SEGMENTS = {
    1: (
        "Hey! Welcome to NotHabermas. You just got access to your own AI-powered "
        "conversation partner on WhatsApp. Let me quickly show you what you can do."
    ),
    2: (
        "First up: fact-checking. Send any claim to the main agent and it will "
        "verify it for you — with real sources. No more forwarding random stuff "
        "without knowing if it's true."
    ),
    3: (
        "Second: mediation. Got a disagreement? The agent can open a group chat "
        "with a mediator that helps both sides find common ground — fairly and "
        "without taking sides."
    ),
    4: (
        "Third: emotional intelligence training. You can simulate tough conversations "
        "— family conflicts, workplace tension — in a safe space to practice how you respond."
    ),
    5: (
        "To get started, just text the main agent and tell it what you need. "
        "Say 'fact-check', 'mediate', or 'practice' — and you'll be forwarded "
        "into the right group chat."
    ),
    6: (
        "One important thing: please don't share this number or add it to any "
        "existing group chats. It won't be able to reply there. This works best "
        "as a one-on-one conversation."
    ),
    7: (
        "This is still a test version, so bear with us. Happy hackathon, and "
        "have fun exploring! If something breaks, that's just a feature in disguise."
    ),
}

# --- Video prompts (built from image + script) ---
VIDEO_PROMPTS = {}
for clip_num in range(1, 8):
    text = SCRIPT_SEGMENTS[clip_num]

    if clip_num in (1, 4, 7):
        camera = "Medium shot, straight-on, waist-up. Centered composition."
    elif clip_num in (2, 5):
        camera = "Slight three-quarter angle from the left. Warm rim light on right side of face."
    else:
        camera = "Slight three-quarter angle from the right. Soft key light from left."

    VIDEO_PROMPTS[clip_num] = (
        f"{camera} "
        f"The woman speaks warmly and directly to camera: '{text}' "
        f"Natural, conversational delivery. Friendly tone, slight smile. "
        f"Cozy study background with bookshelves. Warm ambient lighting. "
        f"Subtle room tone, no background music."
    )


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_start_frame(client, clip_num: int, prompt: str) -> Path:
    """Generate a start frame via Nano Banana."""
    from google.genai import types

    output_path = FRAMES_DIR / f"frame_clip_{clip_num:02d}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    print(f"    Generating frame for clip {clip_num}...")

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        image = PILImage.open(BytesIO(part.inline_data.data))
                        image.save(output_path)
                        print(f"    Saved: {output_path.name} ({image.size[0]}x{image.size[1]})")
                        PRODUCTION_LOG["frames_generated"].append({
                            "clip": clip_num,
                            "file": str(output_path.resolve()),
                            "size": f"{image.size[0]}x{image.size[1]}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        return output_path
            print(f"    Attempt {attempt + 1}/3: empty response, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"    Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(5)

    raise RuntimeError(f"Frame generation failed for clip {clip_num} after 3 attempts")


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
    print(f"  Final video: {output_path} ({size_mb:.1f} MB)")


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    PRODUCTION_LOG["run_started"] = datetime.now(timezone.utc).isoformat()
    client = get_client()
    num_clips = 7

    # =====================================================================
    # PHASE 0: Print ALL prompts upfront (for reuse in parallel agents)
    # =====================================================================
    print("=" * 70)
    print("  NOTHABERMAS ONBOARDING VIDEO v2 — ALL PROMPTS")
    print("=" * 70)

    for clip_num in range(1, num_clips + 1):
        print(f"\n{'─' * 70}")
        print(f"  CLIP {clip_num}")
        print(f"{'─' * 70}")
        print(f"\n  [NANO BANANA IMAGE PROMPT]:")
        print(f"  {IMAGE_PROMPTS[clip_num]}")
        print(f"\n  [VEO 3.0 VIDEO PROMPT]:")
        print(f"  {VIDEO_PROMPTS[clip_num]}")
        print(f"\n  [SCRIPT TEXT]:")
        print(f"  {SCRIPT_SEGMENTS[clip_num]}")

    # Save prompts to JSON for external use
    prompts_export = {
        "model_image": "gemini-2.5-flash-image",
        "model_video": "veo-3.0-generate-001",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "clips": [],
    }
    for clip_num in range(1, num_clips + 1):
        prompts_export["clips"].append({
            "clip_num": clip_num,
            "image_prompt": IMAGE_PROMPTS[clip_num],
            "video_prompt": VIDEO_PROMPTS[clip_num],
            "script_text": SCRIPT_SEGMENTS[clip_num],
        })

    prompts_path = PROJECT_DIR / "prompts.json"
    with open(prompts_path, "w") as f:
        json.dump(prompts_export, f, indent=2, ensure_ascii=False)
    print(f"\n\n  Prompts exported to: {prompts_path.resolve()}")

    PRODUCTION_LOG["image_prompts"] = [
        {"clip": n, "prompt": IMAGE_PROMPTS[n]} for n in range(1, num_clips + 1)
    ]
    PRODUCTION_LOG["video_prompts"] = [
        {"clip": n, "prompt": VIDEO_PROMPTS[n]} for n in range(1, num_clips + 1)
    ]

    # =====================================================================
    # PHASE 1: Generate ALL start frames via Nano Banana
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 1: Generating ALL {num_clips} start frames (Nano Banana)")
    print(f"{'=' * 70}")

    frames: dict[int, Path] = {}
    for clip_num in range(1, num_clips + 1):
        print(f"\n  Frame {clip_num}/{num_clips}")
        frame = generate_start_frame(client, clip_num, IMAGE_PROMPTS[clip_num])
        frames[clip_num] = frame

    print(f"\n  All {len(frames)} frames generated.")

    # =====================================================================
    # PHASE 2: Generate ALL video clips via Veo 3.0
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 2: Generating ALL {num_clips} video clips (Veo 3.0)")
    print(f"{'=' * 70}")

    clip_paths: list[Path] = []
    for clip_num in range(1, num_clips + 1):
        print(f"\n  Clip {clip_num}/{num_clips}")
        print(f"  Script: {SCRIPT_SEGMENTS[clip_num][:60]}...")

        clip = generate_video_clip(
            client, clip_num, frames[clip_num], VIDEO_PROMPTS[clip_num]
        )
        if clip:
            clip_paths.append(clip)
        else:
            print(f"    SKIPPING clip {clip_num}")

    # =====================================================================
    # PHASE 3: Concatenate
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 3: Concatenating {len(clip_paths)} clips")
    print(f"{'=' * 70}")

    final_output = PROJECT_DIR / "nothabermas_onboarding_v2_FINAL.mp4"
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

    log_path = PROJECT_DIR / "production_log.json"
    with open(log_path, "w") as f:
        json.dump(PRODUCTION_LOG, f, indent=2, ensure_ascii=False)

    # =====================================================================
    # Summary
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PRODUCTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Final video:  {final_output.resolve()}")
    print(f"  Clips:        {CLIPS_DIR.resolve()}/")
    print(f"  Frames:       {FRAMES_DIR.resolve()}/")
    print(f"  Prompts:      {prompts_path.resolve()}")
    print(f"  Duration:     {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"  Size:         {size_mb:.1f} MB")
    print(f"  Log:          {log_path.resolve()}")

    print(f"\n  Start frames (Nano Banana):")
    for clip_num in sorted(frames):
        print(f"    Clip {clip_num}: {frames[clip_num].resolve()}")


if __name__ == "__main__":
    main()
