#!/usr/bin/env python3
"""
Producer: Election Explainer — 3 Separate Videos per Question

For each question, produces:
  1. CONTEXT video (blue background) — intro + context facts
  2. YES video (green background) — arguments for
  3. NO video (yellow background) — arguments against

Same presenter (v5e Mediterranean), different backdrop colors.
Dialogue kept SHORT (~15-20 words per 8s clip) to avoid cut-offs.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
VEO_POLL_TIMEOUT = 300
OUTPUT_BASE = Path("output")

# ---------------------------------------------------------------------------
# Character (v5e Mediterranean — shared across all 3 videos)
# ---------------------------------------------------------------------------
CHARACTER = (
    "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
    "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
    "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
    "bracelet on one wrist. No other jewelry, no makeup. Visible natural skin texture, "
    "real human face."
)

CAMERA = (
    "Shot on a Leica SL2 with a Summilux 75mm f/1.4 lens. Exceptional subject separation. "
    "Rich warm skin tones. Cinematic depth. Fine organic grain."
)

# ---------------------------------------------------------------------------
# Background colors per video type
# ---------------------------------------------------------------------------
BACKGROUNDS = {
    "context": {
        "color_name": "deep muted blue",
        "spotlight_center": "#4a6a8a",
        "edge_dark": "#0e1e2e",
        "label": "CONTEXT",
    },
    "yes": {
        "color_name": "deep muted green",
        "spotlight_center": "#4a7a5a",
        "edge_dark": "#0e2e1a",
        "label": "YES",
    },
    "no": {
        "color_name": "deep muted amber-yellow",
        "spotlight_center": "#8a7a4a",
        "edge_dark": "#2e2410",
        "label": "NO",
    },
}


def make_setting(bg_key: str) -> str:
    bg = BACKGROUNDS[bg_key]
    return (
        f"Medium shot, waist-up framing — no legs visible, no table, no desk, no furniture. "
        f"She stands upright. "
        f"BACKGROUND: A single monochromatic canvas backdrop in a {bg['color_name']} color "
        f"(bright spotlight center ~{bg['spotlight_center']}, fading to very dark "
        f"~{bg['edge_dark']} at edges). A single soft spotlight hits the center behind her, "
        f"creating a diffused bright area that smoothly darkens toward all edges — classic "
        f"portrait vignette. No equipment, no props, no text. Just the smooth gradient. "
        f"LIGHTING: One overhead softbox from above. One key light from upper left creating "
        f"gentle modeling on her face with subtle shadow on right side."
    )


# ---------------------------------------------------------------------------
# Angle descriptions
# ---------------------------------------------------------------------------
ANGLES = {
    "medium_front": "Medium shot, straight-on, waist-up. Centered. She looks directly at camera. Minimal movement, composed posture.",
    "side_left": "Three-quarter shot from 45° left. She has turned slightly to her left from the front-facing position. She may take a small half-step but stays in the same spot. Rim light on right side of face. Same background visible.",
    "closeup_front": "Tight close-up, head and shoulders. Shallow DOF. Eyes tack-sharp. Very still, minimal head movement.",
}

# Transition prompt for when switching FROM medium_front TO side_left
TRANSITION_TO_SIDE = (
    "The presenter slowly turns her head and body slightly to her left, shifting her weight "
    "gently. She takes a small half-step to settle into a three-quarter angle. The movement "
    "is natural and unhurried. She continues speaking as she turns."
)

# Prompt suffix to prevent weird end-of-clip movements
HOLD_STILL_SUFFIX = (
    "IMPORTANT: After finishing the spoken line, she holds perfectly still — maintaining "
    "eye contact, steady posture, neutral expression. No nodding, no looking away, no "
    "extra gestures. The clip should end with her holding her position in stillness. "
    "CRITICAL: No camera transitions, no swipe effects, no wipe effects, no zoom transitions, "
    "no cross-dissolves, no scene changes. The camera stays completely locked in position "
    "throughout the entire clip. Static camera, no movement. "
    "Do NOT generate any subtitles, captions, or on-screen text of any kind."
)


# ---------------------------------------------------------------------------
# Q1 shot lists — SHORT dialogue (~15-20 words max per clip)
# ---------------------------------------------------------------------------

Q1_CONTEXT_SHOTS = [
    # Blue background — intro + context
    (1, "medium_front", False,
     "Üdvözlöm. Ma arról a kérdésről beszélünk, hogy Magyarország tárgyaljon-e "
     "Oroszországgal az ukrajnai háború lezárásáért."),

    (2, "side_left", False,
     "Magyarország megvétózta az EU Ukrajnának szánt hitelcsomagjait, "
     "és nem küldött fegyvereket."),

    (3, "medium_front", False,
     "Az ellenzéki pártok azt javasolják, hogy Magyarország szüntesse meg "
     "az EU-s támogatást blokkoló vétókat."),

    (4, "closeup_front", False,
     "Nézzük meg mindkét oldal érveit. Először az igen, aztán a nem álláspontot."),
]

Q1_YES_SHOTS = [
    # Green background — arguments FOR
    (1, "medium_front", False,
     "Az igen oldal szerint a diplomácia a leghatékonyabb út a konfliktus lezárásához."),

    (2, "side_left", False,
     "Magas szintű tárgyalások már zajlottak Moszkvában. Budapestet is felajánlották "
     "tárgyalási helyszínnek."),

    (3, "closeup_front", False,
     "Európa kockáztatja, hogy belekeveredik egy olyan háborúba, "
     "amelyre nincs katonai megoldás."),

    (4, "medium_front", False,
     "Magyarországnak meg kell védenie szuverenitását. Nem szabad fegyvereket "
     "vagy katonákat küldenie."),

    (5, "side_left", False,
     "A békét kell előtérbe helyezni a brüsszeli katonai eszkalációval szemben. "
     "Ez az igen álláspont."),
]

Q1_NO_SHOTS = [
    # Yellow background — arguments AGAINST
    (1, "medium_front", False,
     "A nem oldal szerint az Oroszországgal való tárgyalás aláássa az európai egységet."),

    (2, "side_left", False,
     "Ukrajna védelmének támogatása uniós koordináción keresztül a felelős út. "
     "Ez erősíti a biztonságot."),

    (3, "closeup_front", False,
     "A vétók elszigetelték Magyarországot és rombolják az évtizedes "
     "NATO-partneri bizalmat."),

    (4, "medium_front", False,
     "A nyugati szövetségi rendszerekbe való beágyazás jobban szolgálja "
     "a hosszú távú nemzeti érdeket."),

    (5, "side_left", False,
     "Az orosz energiafüggőség csökkentése kulcsfontosságú. "
     "Ez a nem álláspont. A döntés az Öné."),
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_start_frame(client, angle: str, bg_key: str, out_dir: Path) -> Path:
    """Generate a start frame for a given angle and background color."""
    from google.genai import types

    output_path = out_dir / f"angle_{bg_key}_{angle}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    setting = make_setting(bg_key)
    angle_desc = ANGLES[angle]
    prompt = f"{CHARACTER}\n\n{setting}\n\n{angle_desc}\n\n{CAMERA}"

    print(f"    Generating {bg_key}/{angle}...")
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

    print(f"    ERROR: No image for {bg_key}/{angle}")
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
    seek_time = max(0, duration - 0.1)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(seek_time), "-i", str(video_path),
         "-frames:v", "1", "-q:v", "1", str(output_path)],
        capture_output=True, check=True,
    )
    return output_path


def generate_clip(client, clip_num: int, start_frame: Path, prompt: str,
                  clips_dir: Path) -> Path | None:
    from google.genai import types

    output_path = clips_dir / f"clip_{clip_num:02d}.mp4"
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if size_mb > 0.1:
            print(f"    [cached] {output_path.name} ({size_mb:.1f} MB)")
            return output_path

    image = types.Image.from_file(location=str(start_frame))

    print(f"    Submitting Veo 3.0...")
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
            print(f"    TIMEOUT clip {clip_num}")
            return None
        print(f"    [{elapsed}s] Generating...")
        time.sleep(15)
        operation = client.operations.get(operation)

    elapsed = int(time.time() - start)

    if not operation.response or not operation.response.generated_videos:
        print(f"    ERROR: No video for clip {clip_num}")
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def concatenate(clip_paths: list[Path], output_path: Path) -> None:
    concat_file = output_path.parent / "concat_list.txt"
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
    print(f"    Final: {output_path.name} ({size_mb:.1f} MB)")


def produce_video(client, shots: list, bg_key: str, project_dir: Path, video_name: str):
    """Produce one video from a shot list with a specific background."""
    frames_dir = project_dir / "frames"
    clips_dir = project_dir / f"clips_{bg_key}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    bg = BACKGROUNDS[bg_key]
    setting = make_setting(bg_key)
    total = len(shots)

    print(f"\n{'='*50}")
    print(f"  {bg['label']} VIDEO — {total} clips × 8s")
    print(f"  Background: {bg['color_name']}")
    print(f"{'='*50}")

    # Phase 1: Generate start frames
    print(f"\n  Phase 1: Start frames")
    unique_angles = set()
    for _, angle, is_cont, _ in shots:
        if not is_cont:
            unique_angles.add(angle)
    for angle in sorted(unique_angles):
        generate_start_frame(client, angle, bg_key, frames_dir)

    # Phase 2: Generate clips
    print(f"\n  Phase 2: Generating {total} clips")
    clip_paths: list[Path] = []
    prev_clip: Path | None = None

    prev_angle = None
    for clip_num, angle, _is_cont_unused, dialogue in shots:
        changing_angle = (prev_angle is not None and angle != prev_angle)
        same_angle_continuation = (prev_angle is not None and angle == prev_angle)

        print(f"\n  Clip {clip_num:02d}/{total} — {angle}"
              + (" (angle change)" if changing_angle else "")
              + (" (continuation)" if same_angle_continuation else ""))

        angle_desc = ANGLES[angle]

        # Build transition context if switching angles
        transition = ""
        if changing_angle and angle == "side_left":
            transition = f"\n\n{TRANSITION_TO_SIDE}"

        video_prompt = (
            f"{CHARACTER}\n\n{setting}\n\n{angle_desc}\n\n{CAMERA}"
            f"{transition}\n\n"
            f"The presenter speaks in Hungarian with calm, natural delivery: "
            f"'{dialogue}' "
            f"\n\n{HOLD_STILL_SUFFIX}"
        )

        # Continuity logic:
        # - Same angle as previous clip → use last frame of previous clip
        # - Different angle → use the Nano Banana start frame for that angle
        if same_angle_continuation and prev_clip and prev_clip.exists():
            start_frame = frames_dir / f"lastframe_{bg_key}_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip, start_frame)
            print(f"    Using last frame from clip {clip_num - 1}")
        else:
            start_frame = frames_dir / f"angle_{bg_key}_{angle}.png"
            print(f"    Using Nano Banana frame for {angle}")

        clip = generate_clip(client, clip_num, start_frame, video_prompt, clips_dir)
        if clip:
            clip_paths.append(clip)
            prev_clip = clip
        else:
            print(f"    SKIPPED clip {clip_num}")

        prev_angle = angle

    # Phase 3: Concatenate
    print(f"\n  Phase 3: Concatenating {len(clip_paths)} clips")
    output = project_dir / f"{video_name}.mp4"
    concatenate(clip_paths, output)
    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    client = get_client()
    project_dir = OUTPUT_BASE / "election_q01_3videos"
    project_dir.mkdir(parents=True, exist_ok=True)

    start_time = datetime.now(timezone.utc)
    results = []

    # Video 1: CONTEXT (blue)
    v1 = produce_video(client, Q1_CONTEXT_SHOTS, "context", project_dir, "q01_context_blue")
    results.append(("CONTEXT (blue)", v1))

    # Video 2: YES (green)
    v2 = produce_video(client, Q1_YES_SHOTS, "yes", project_dir, "q01_yes_green")
    results.append(("YES (green)", v2))

    # Video 3: NO (yellow)
    v3 = produce_video(client, Q1_NO_SHOTS, "no", project_dir, "q01_no_yellow")
    results.append(("NO (yellow)", v3))

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    print(f"\n{'='*50}")
    print(f"  ALL DONE — {elapsed/60:.1f} minutes total")
    for label, path in results:
        size = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        print(f"  {label}: {path.name} ({size:.1f} MB)")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
