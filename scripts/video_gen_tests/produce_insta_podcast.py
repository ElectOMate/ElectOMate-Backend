#!/usr/bin/env python3
"""
Producer: 1-Minute Instagram Reel — Hungarian Democracy, but make it fun.
British girl, selfie-style, vertical 9:16, funny takes.
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

PRODUCTION_LOG: dict = {
    "run_started": None,
    "run_finished": None,
    "model_image": "gemini-2.5-flash-image",
    "model_video": "veo-3.0-generate-001",
    "format": "9:16 vertical (Instagram Reel)",
    "character_description": None,
    "angles": {},
    "shots": [],
    "clips_generated": [],
    "clips_failed": [],
    "final_outputs": [],
}
VEO_POLL_TIMEOUT = 300

# Directories
PODCAST_DIR = OUTPUT_DIR / "insta_democracy"
FRAMES_DIR = PODCAST_DIR / "frames"
CLIPS_DIR = PODCAST_DIR / "clips"
for d in [PODCAST_DIR, FRAMES_DIR, CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Character ---
CHARACTER = (
    "A photorealistic selfie-style photo of a stylish British woman in her mid-20s "
    "with wavy dark blonde hair, light freckles, expressive green eyes, and a cheeky smile. "
    "She is holding her phone up at a selfie angle, slightly above eye level. "
    "She wears an oversized vintage band t-shirt and gold hoop earrings. "
    "Behind her is a cozy London flat: exposed brick wall, fairy lights, a messy bookshelf "
    "with history books and a small Hungarian flag sticker on her laptop visible in background. "
    "Natural window light from the left, golden hour glow. iPhone selfie camera quality, "
    "slightly wide-angle distortion. Vertical 9:16 portrait orientation."
)

ANGLES = {
    "selfie_straight": (
        "Classic selfie angle, phone held at arm's length slightly above eye level. "
        "She looks directly into the camera lens with a playful expression. "
        "Her face fills the upper third of the vertical frame."
    ),
    "selfie_close": (
        "Very close selfie, phone close to face, big expressive eyes filling the frame. "
        "Eyebrows raised, about-to-spill-the-tea expression. "
        "Slightly fish-eye effect from proximity."
    ),
    "selfie_side": (
        "Selfie from a side angle, she's turned to look at camera over her shoulder. "
        "More of the room visible. Casual, mid-thought pose. "
        "One hand gesturing, the other holding the phone."
    ),
    "selfie_low": (
        "Phone held lower, looking down at camera. Power pose angle. "
        "She looks confident and slightly dramatic. "
        "Ceiling fairy lights create bokeh above her head."
    ),
}

SHOTS = [
    (1, "selfie_straight", False,
     "The woman looks into the camera and says in an excited British accent: "
     "'Right, so I just found out the most mental thing about Hungarian democracy "
     "and I literally cannot keep it to myself.' "
     "She widens her eyes dramatically. Natural selfie movement, slight phone shake. "
     "Room tone, no music. Authentic iPhone audio quality."),

    (2, "selfie_close", False,
     "Very close to camera, she whispers conspiratorially in a British accent: "
     "'So in 1848, yeah, Hungary basically said to the Habsburg Empire — "
     "nah mate, we are done. Full revolution. Absolute scenes.' "
     "She pulls back slightly, impressed by her own fact. "
     "Natural room audio, slight laugh at the end."),

    (3, "selfie_straight", True,
     "She continues, gesturing with one hand, British accent: "
     "'And then — and this is the bit that gets me — after like forty years "
     "of communism, Hungary was the FIRST Eastern Bloc country to hold free elections. "
     "First! In 1990!' "
     "She points at camera for emphasis. Animated, energetic delivery. "
     "Natural room sound."),

    (4, "selfie_side", False,
     "From a side angle, she turns to camera and says casually in British English: "
     "'Like imagine being Hungarian in 1989, watching the Berlin Wall come down, "
     "and thinking — right, it is our turn now. Absolute legends.' "
     "She does a little chef's kiss gesture. Casual and funny. "
     "Room ambience, she chuckles."),

    (5, "selfie_low", False,
     "Looking down at camera dramatically, she says in a posh British accent: "
     "'But here is where it gets properly spicy. After 2010, the government "
     "rewrote the entire constitution. The ENTIRE thing. "
     "That is like rewriting the rules mid-game.' "
     "She raises her eyebrows and does a shocked face. "
     "Room tone, dramatic pause."),

    (6, "selfie_close", False,
     "Close to camera again, she says earnestly in British English: "
     "'The thing is though, Hungarian people are genuinely brilliant at "
     "not giving up. Civil society, protests, independent media — "
     "they keep showing up. Respect, honestly.' "
     "She nods with genuine admiration. Warmer tone. "
     "Natural room sound."),

    (7, "selfie_straight", False,
     "Back to classic selfie, she wraps up with a big smile, British accent: "
     "'Anyway, that is your Hungarian democracy history lesson for today. "
     "You are welcome. Follow for more unhinged history content. "
     "And if you are Hungarian — big up yourselves, you lot are class.' "
     "She does a peace sign and winks. "
     "Room sound, she laughs at the end."),

    (8, "selfie_straight", True,
     "She leans in one more time and adds cheekily in British English: "
     "'Oh and by the way, Budapest is absolutely gorgeous. "
     "Go visit. Right, bye!' "
     "She reaches forward to tap the stop button. The video cuts. "
     "Natural room audio, quick ending."),
]


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_angle_image(client, angle_key: str) -> Path:
    from google.genai import types
    output_path = FRAMES_DIR / f"angle_{angle_key}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    prompt = f"{CHARACTER}\n\n{ANGLES[angle_key]}"
    print(f"    Generating: {angle_key}...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="9:16"),
        ),
    )
    for part in response.parts:
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            print(f"    Saved: {output_path.name} ({image.size[0]}x{image.size[1]})")
            PRODUCTION_LOG["clips_generated"].append({
                "type": "image", "angle": angle_key,
                "file": str(output_path.resolve()),
                "size": f"{image.size[0]}x{image.size[1]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return output_path
    print(f"    ERROR: No image for {angle_key}")
    PRODUCTION_LOG["clips_failed"].append({"type": "image", "angle": angle_key})
    sys.exit(1)


def extract_last_frame(video_path: Path, output_path: Path) -> Path:
    if output_path.exists():
        return output_path
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", str(video_path)],
        capture_output=True, text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    seek = max(0, duration - 0.1)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(seek), "-i", str(video_path),
         "-frames:v", "1", "-q:v", "1", str(output_path)],
        capture_output=True, check=True,
    )
    print(f"    Extracted last frame: {output_path.name}")
    return output_path


def generate_clip(client, clip_num: int, start_frame: Path, prompt: str) -> Path:
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
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
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

    if not operation.response or not operation.response.generated_videos:
        print(f"    ERROR: No video for clip {clip_num}")
        PRODUCTION_LOG["clips_failed"].append({
            "type": "video", "clip": clip_num, "reason": "no_response",
        })
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    elapsed = int(time.time() - start)
    print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")

    PRODUCTION_LOG["clips_generated"].append({
        "type": "video", "clip": clip_num,
        "file": str(output_path.resolve()),
        "size_mb": round(size_mb, 1),
        "generation_time_s": elapsed,
        "prompt": prompt[:120] + "..." if len(prompt) > 120 else prompt,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return output_path


def concatenate(clip_paths: list[Path], output_path: Path):
    concat_file = PODCAST_DIR / "concat_list.txt"
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
    print(f"Final: {output_path} ({size_mb:.1f} MB)")


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    PRODUCTION_LOG["run_started"] = datetime.now(timezone.utc).isoformat()
    PRODUCTION_LOG["character_description"] = CHARACTER
    PRODUCTION_LOG["angles"] = ANGLES
    PRODUCTION_LOG["shots"] = [
        {"clip": n, "angle": a, "continuation": c, "prompt": p}
        for n, a, c, p in SHOTS
    ]

    client = get_client()
    clip_paths = []

    print("=" * 60)
    print("  INSTA REEL: Hungarian Democracy, But Make It Fun")
    print("  8 clips × 8s = ~1 minute, vertical 9:16")
    print("=" * 60)

    # Phase 1: Angle images
    print("\n--- Phase 1: Nano Banana angle images ---")
    unique = {angle for _, angle, cont, _ in SHOTS if not cont}
    for angle in sorted(unique):
        generate_angle_image(client, angle)

    # Phase 2: Clips
    print("\n--- Phase 2: Veo 3.0 clips ---")
    prev_clip = None
    for clip_num, angle, is_cont, prompt in SHOTS:
        print(f"\n  Clip {clip_num:02d}/8 — {angle}" +
              (" (cont)" if is_cont else ""))
        if is_cont and prev_clip and prev_clip.exists():
            frame = FRAMES_DIR / f"lastframe_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip, frame)
        else:
            frame = FRAMES_DIR / f"angle_{angle}.png"

        clip = generate_clip(client, clip_num, frame, prompt)
        if clip:
            clip_paths.append(clip)
            prev_clip = clip

    # Phase 3: Concat
    print(f"\n--- Phase 3: Concatenating {len(clip_paths)} clips ---")
    final = PODCAST_DIR / "insta_hungarian_democracy_FINAL.mp4"
    concatenate(clip_paths, final)
    PRODUCTION_LOG["final_outputs"].append(str(final.resolve()))

    # Phase 4: Mix background music
    music_file = OUTPUT_DIR / "Tony Anderson - Retour.mp3"
    if music_file.exists():
        print("\n--- Phase 4: Mixing background music ---")
        final_music = PODCAST_DIR / "insta_hungarian_democracy_FINAL_music.mp4"
        try:
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", str(final),
                 "-i", str(music_file),
                 "-filter_complex",
                 "[0:a]volume=1.0[voice];[1:a]volume=0.12[music];"
                 "[voice][music]amix=inputs=2:duration=shortest[out]",
                 "-map", "0:v", "-map", "[out]",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-movflags", "+faststart",
                 str(final_music)],
                capture_output=True, check=True,
            )
            size_mb = final_music.stat().st_size / (1024 * 1024)
            print(f"  With music: {final_music.name} ({size_mb:.1f} MB)")
            PRODUCTION_LOG["final_outputs"].append(str(final_music.resolve()))
            PRODUCTION_LOG["background_music"] = str(music_file.resolve())
        except subprocess.CalledProcessError as e:
            print(f"  WARNING: Music mixing failed: {e.stderr[:200] if e.stderr else 'unknown error'}")
    else:
        print("\n--- Phase 4: Skipping music (no music file found) ---")

    # Verify
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration,size", "-of", "json", str(final)],
        capture_output=True, text=True,
    )
    info = json.loads(result.stdout)["format"]
    dur = float(info["duration"])
    sz = int(info["size"]) / (1024 * 1024)

    PRODUCTION_LOG["run_finished"] = datetime.now(timezone.utc).isoformat()
    PRODUCTION_LOG["final_duration_s"] = round(dur, 2)
    PRODUCTION_LOG["final_size_mb"] = round(sz, 1)
    PRODUCTION_LOG["total_clips"] = len(clip_paths)
    PRODUCTION_LOG["clips_failed_count"] = len(PRODUCTION_LOG["clips_failed"])

    # Write production log
    log_path = PODCAST_DIR / "production_log.json"
    with open(log_path, "w") as f:
        json.dump(PRODUCTION_LOG, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)
    print(f"  File: {final.resolve()}")
    print(f"  Duration: {int(dur // 60)}:{int(dur % 60):02d}")
    print(f"  Size: {sz:.1f} MB")
    print(f"  Format: 9:16 vertical (Instagram Reel)")
    print(f"  Log: {log_path.resolve()}")


if __name__ == "__main__":
    main()
