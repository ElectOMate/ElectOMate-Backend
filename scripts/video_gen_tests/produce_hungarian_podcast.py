#!/usr/bin/env python3
"""
Producer: 2-Minute Hungarian Democracy Podcast
Generates 15 × 8s clips via Veo 3.0, concatenates with ffmpeg.

Multi-angle shots with character consistency.
Continuity via last-frame extraction or new angle images from Nano Banana.
"""

import json
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

from config import GEMINI_API_KEY, OUTPUT_DIR

# Directories
PODCAST_DIR = OUTPUT_DIR / "hungarian_podcast"
FRAMES_DIR = PODCAST_DIR / "frames"
CLIPS_DIR = PODCAST_DIR / "clips"
for d in [PODCAST_DIR, FRAMES_DIR, CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Character description (consistent across all angles) ---
CHARACTER = (
    "A photorealistic shot of a male podcast host in his early 40s with short brown hair "
    "and gray temples, a neatly trimmed beard, round tortoiseshell glasses, wearing a khaki "
    "field vest over a dark brown henley shirt. He is seated at a dark walnut podcast desk "
    "with two professional boom-arm microphones. Behind him is a large world map with "
    "democracy index color highlights. Warm tungsten key light from above-left creates "
    "subtle shadows. A small desk label reads 'Democracy Deep Dive'. "
    "Cinematic look, 4K quality, shallow depth of field, film grain."
)

# --- Angle modifiers for Nano Banana ---
ANGLES = {
    "medium_front": (
        "Medium shot, straight-on, waist-up framing. Both microphones visible. "
        "Centered symmetrical composition. He looks directly at camera."
    ),
    "side_left": (
        "Three-quarter shot from 45 degrees to the left. The host is slightly turned "
        "toward this camera. One microphone prominent in foreground, the other behind. "
        "Off-center composition, rule of thirds. Rim light on the right side of his face."
    ),
    "side_right": (
        "Three-quarter shot from 45 degrees to the right. Mirror of the left angle. "
        "One microphone in foreground right. Host slightly turned toward camera. "
        "Key light creates modeling on the left side of his face."
    ),
    "closeup_front": (
        "Tight close-up, head and shoulders only. Very shallow depth of field, "
        "background heavily blurred. Eyes tack-sharp. Intimate, intense framing."
    ),
    "closeup_side": (
        "Near-profile close-up from the left side. Dramatic rim lighting on the edge "
        "of his face. Moody, contemplative. One microphone soft in the foreground bokeh."
    ),
    "wide_establishing": (
        "Wide establishing shot showing the full desk, both microphones on boom arms, "
        "the complete world map behind him, and the warm studio environment. "
        "He is centered but smaller in frame, showing the full set."
    ),
}

# --- Shot list: (clip_number, angle_key, is_continuation, video_prompt) ---
SHOTS = [
    (1, "medium_front", False,
     "The host looks directly at the camera and speaks warmly: "
     "'Welcome to Democracy Deep Dive. Today, we're exploring one of Central Europe's "
     "most fascinating stories — Hungarian democracy.' "
     "He gives a slight nod. Calm, authoritative delivery. "
     "Soft ambient studio hum, subtle background music."),

    (2, "medium_front", True,  # continuation from clip 1
     "The host continues speaking to camera: "
     "'Hungary has one of the most complex democratic histories in the region. "
     "From revolution to dictatorship to rebirth — it is quite a journey.' "
     "He gestures gently with his right hand. Camera holds steady. "
     "Warm studio ambience continues."),

    (3, "side_left", False,
     "Seen from the side, the host turns slightly toward this camera and says: "
     "'It all started in 1848, when Hungary launched a bold democratic revolution "
     "against Habsburg imperial rule. Lajos Kossuth became a national hero.' "
     "He speaks with conviction. The microphone is prominent in the foreground. "
     "Studio ambience, documentary tone."),

    (4, "closeup_front", False,
     "In tight close-up, the host leans in slightly and says in a lower, more intimate tone: "
     "'But here is what most people do not know. That revolution was crushed — "
     "and it took over a hundred years before Hungary saw real democracy again.' "
     "His eyes are intense. Very shallow depth of field. "
     "Hushed studio atmosphere, subtle tension in the background music."),

    (5, "side_left", False,
     "From the side angle, the host speaks with enthusiasm: "
     "'After the fall of communism in 1989, Hungary was the very first Eastern Bloc country "
     "to hold free multi-party elections. It was a remarkable moment.' "
     "He smiles slightly. Gestures toward the map behind him. "
     "Upbeat background music, studio ambience."),

    (6, "medium_front", False,
     "Back to the front angle. The host speaks clearly: "
     "'The 1990 elections were a true watershed. Six different parties entered parliament. "
     "The whole spectrum, from liberal to conservative, was represented.' "
     "He counts on his fingers as he lists them. Steady camera. "
     "Warm studio sound, factual documentary tone."),

    (7, "wide_establishing", False,
     "In a wide shot showing the full studio, the host gestures broadly toward the world map: "
     "'Look at Hungary on the map — right at the crossroads of East and West. "
     "Vienna to the west, Kyiv to the east. That geography shapes everything.' "
     "His arm sweeps across the map. The full podcast setup is visible. "
     "Ambient studio sound, contemplative background music."),

    (8, "side_right", False,
     "From the right side angle, the host says: "
     "'Joining the European Union in 2004 was seen as the ultimate democratic validation. "
     "Hungary had made it. The transition was complete — or so people thought.' "
     "He pauses thoughtfully at the end. Rim light on his face. "
     "Studio ambience, a note of gravity in the background music."),

    (9, "closeup_front", False,
     "In tight close-up, the host speaks with measured intensity: "
     "'But the real tension began after 2010. New supermajorities in parliament "
     "opened the door to sweeping constitutional changes.' "
     "He holds the camera's gaze. Very still. "
     "Quiet studio, tension in the score."),

    (10, "medium_front", False,
     "The host speaks directly to camera: "
     "'A new fundamental law replaced the old constitution. The judiciary was restructured. "
     "Media regulations changed. The balance of institutional power shifted.' "
     "He speaks deliberately, ticking off points with his hand. "
     "Documentary narration style, neutral background music."),

    (11, "side_left", False,
     "From the left angle, the host compares: "
     "'Now compare this to the neighbors. Poland went through its own institutional battles. "
     "Czech Republic stayed more stable. Slovakia oscillated. Each path was unique.' "
     "He glances toward the map. Thoughtful tone. "
     "Studio ambience, analytical background music."),

    (12, "wide_establishing", False,
     "Wide shot of the full studio. The host speaks with admiration: "
     "'Through all of this, Hungarian civil society has remained remarkably active. "
     "Universities, NGOs, independent media — they have pushed back and adapted.' "
     "He nods slowly. The full studio set is visible. "
     "Warmer background music, respectful tone."),

    (13, "closeup_side", False,
     "Near-profile close-up. The host pauses, then says reflectively: "
     "'Democracy is never finished. It is always a work in progress. "
     "Every generation must choose to defend it — or risk losing it.' "
     "Dramatic rim lighting on his face. A long, contemplative beat. "
     "Very quiet, almost no background music. Just studio air."),

    (14, "medium_front", False,
     "Back to the front. The host speaks with warmth and conviction: "
     "'What Hungary teaches us is that democratic institutions must be actively maintained. "
     "They are not self-sustaining. They require vigilance, participation, and courage.' "
     "He places his hand on the desk for emphasis. "
     "Uplifting background music swells slightly."),

    (15, "medium_front", True,  # continuation from clip 14
     "The host smiles and delivers the sign-off: "
     "'That is all for today's Democracy Deep Dive. Thank you for watching. "
     "Stay informed, stay curious, and never stop asking questions. Until next time.' "
     "He gives a warm nod to camera. The music resolves. "
     "Studio ambience fades gently."),
]


def get_client():
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def generate_angle_image(client, angle_key: str) -> Path:
    """Generate a start frame image for a given camera angle."""
    from google.genai import types

    output_path = FRAMES_DIR / f"angle_{angle_key}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    prompt = f"{CHARACTER}\n\n{ANGLES[angle_key]}"
    print(f"    Generating image for angle: {angle_key}...")

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

    print(f"    ERROR: No image generated for {angle_key}")
    sys.exit(1)


def extract_last_frame(video_path: Path, output_path: Path) -> Path:
    """Extract the last frame of a video using ffmpeg."""
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    # Get duration first
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", str(video_path)],
        capture_output=True, text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    # Seek to 0.1s before end
    seek_time = max(0, duration - 0.1)

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(seek_time), "-i", str(video_path),
         "-frames:v", "1", "-q:v", "1", str(output_path)],
        capture_output=True, check=True,
    )
    print(f"    Extracted last frame: {output_path.name}")
    return output_path


def generate_video_clip(client, clip_num: int, start_frame: Path, prompt: str) -> Path:
    """Generate an 8-second video clip using Veo 3.0."""
    from google.genai import types

    output_path = CLIPS_DIR / f"clip_{clip_num:02d}.mp4"
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if size_mb > 0.1:  # not empty/corrupt
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
        print(f"    [{elapsed}s] Generating...")
        time.sleep(15)
        operation = client.operations.get(operation)

    elapsed = int(time.time() - start)

    if not operation.response or not operation.response.generated_videos:
        print(f"    ERROR: No video generated for clip {clip_num}")
        print(f"    Operation: {operation}")
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> None:
    """Concatenate all clips using ffmpeg concat demuxer."""
    # Create concat file
    concat_file = PODCAST_DIR / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")

    # Re-encode to ensure consistent format across all clips
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

    client = get_client()
    clip_paths: list[Path] = []

    print("=" * 60)
    print("  HUNGARIAN DEMOCRACY PODCAST — PRODUCTION")
    print("  15 clips × 8s = 2 minutes")
    print("=" * 60)

    # Phase 1: Generate all unique angle images
    print("\n--- Phase 1: Generating angle images via Nano Banana ---")
    unique_angles = set()
    for _, angle, is_cont, _ in SHOTS:
        if not is_cont:
            unique_angles.add(angle)

    for angle in sorted(unique_angles):
        generate_angle_image(client, angle)

    # Phase 2: Generate clips
    print("\n--- Phase 2: Generating video clips via Veo 3.0 ---")
    prev_clip_path: Path | None = None

    for clip_num, angle, is_continuation, prompt in SHOTS:
        print(f"\n  Clip {clip_num:02d}/15 — {angle}" +
              (" (continuation)" if is_continuation else ""))

        if is_continuation and prev_clip_path and prev_clip_path.exists():
            # Extract last frame from previous clip
            start_frame = FRAMES_DIR / f"lastframe_clip_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip_path, start_frame)
        else:
            # Use the angle image
            start_frame = FRAMES_DIR / f"angle_{angle}.png"

        clip_path = generate_video_clip(client, clip_num, start_frame, prompt)
        if clip_path:
            clip_paths.append(clip_path)
            prev_clip_path = clip_path
        else:
            print(f"    SKIPPING clip {clip_num} due to generation failure")

    # Phase 3: Concatenate
    print(f"\n--- Phase 3: Concatenating {len(clip_paths)} clips ---")
    final_output = PODCAST_DIR / "hungarian_democracy_podcast_FINAL.mp4"
    concatenate_clips(clip_paths, final_output)

    # Summary
    print("\n" + "=" * 60)
    print("  PRODUCTION COMPLETE")
    print("=" * 60)
    print(f"  Final video: {final_output.resolve()}")
    print(f"  Clips: {CLIPS_DIR.resolve()}/")
    print(f"  Frames: {FRAMES_DIR.resolve()}/")

    # Verify
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration,size", "-of", "json", str(final_output)],
        capture_output=True, text=True,
    )
    info = json.loads(result.stdout)["format"]
    duration = float(info["duration"])
    size_mb = int(info["size"]) / (1024 * 1024)
    print(f"  Duration: {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"  Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
