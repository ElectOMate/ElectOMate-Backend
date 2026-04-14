#!/usr/bin/env python3
"""
NotHabermas Cinematic Trailer — Final Production

Structure: Short 3-5s cuts. Narrator (same woman from onboarding) interleaved
with b-roll persona shots. No phone-only scenes. ~70 seconds total.

Pipeline:
1. Generate narrator start frames (Nano Banana)
2. Generate ALL video clips (Veo 3.0) — narrator + b-roll
3. Trim each clip to target duration (3-5s)
4. Concatenate
5. Mix background music (Tony Anderson - Retour)
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

VEO_POLL_TIMEOUT = 300

# Directories
PROJECT_DIR = OUTPUT_DIR / "trailer_final"
FRAMES_DIR = PROJECT_DIR / "frames"
CLIPS_DIR = PROJECT_DIR / "clips"
TRIMMED_DIR = PROJECT_DIR / "trimmed"
for d in [PROJECT_DIR, FRAMES_DIR, CLIPS_DIR, TRIMMED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Selected b-roll frames (already generated)
BROLL_DIR = OUTPUT_DIR / "trailer_frames"

# Music
MUSIC_PATH = OUTPUT_DIR / "Tony Anderson - Retour.mp3"

# --- Narrator character (same as onboarding v2) ---
NARRATOR_BASE = (
    "A photorealistic shot of a woman in her late 30s with dark wavy shoulder-length hair, "
    "wearing a white linen blouse. She is in a cozy home study with warm-toned wooden "
    "bookshelves filled with books behind her. A vintage Edison bulb hangs to the left. "
    "Natural warm lighting, shallow depth of field, cinematic quality, 4K, 16:9 aspect ratio."
)

# ============================================================================
# SHOT LIST — each entry:
#   (shot_id, type, duration_s, image_source, video_prompt, script_text)
#
# type: "narrator" (generate frame) or "broll" (use selected frame)
# image_source: for broll = filename in BROLL_DIR, for narrator = pose description
# ============================================================================

SHOT_LIST = [
    # --- ACT 1: THE PROBLEM ---
    {
        "id": "n01",
        "type": "narrator",
        "duration": 5,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, straight-on. She looks directly at camera with a serious, "
            "contemplative expression. Hands clasped on desk. The mood is somber."
        ),
        "video_prompt": (
            "Medium shot, straight-on. The woman pauses for 2 seconds, then speaks seriously "
            "to camera: 'Every day, millions of conversations end before they begin.' "
            "Somber, measured delivery. Quiet room tone. No music."
        ),
        "script": "Every day, millions of conversations end before they begin.",
    },
    {
        "id": "b01_father",
        "type": "broll",
        "duration": 3,
        "image_source": "1_1_v2.png",
        "video_prompt": (
            "The father shouts angrily, pointing at someone off-camera. His face is intense, "
            "veins on neck. Muffled shouting. A door slams. Dim kitchen, single overhead bulb. "
            "Dramatic, tense. No music."
        ),
        "script": "(muffled shouting, door slam)",
    },
    {
        "id": "b02_protest",
        "type": "broll",
        "duration": 3,
        "image_source": "1_2_v2.png",
        "video_prompt": (
            "Split-screen. Left: the young man in hoodie screams at a protest, waving his fist banner. "
            "Right: the older man waves his flag furiously. Both sides shouting. Crowd noise, chanting. "
            "Chaotic, aggressive energy. Smoke drifts."
        ),
        "script": "(crowd chanting, overlapping)",
    },
    {
        "id": "n02",
        "type": "narrator",
        "duration": 4,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, slight three-quarter angle from the left. She has a sad, reflective "
            "expression. Looking slightly down then back to camera."
        ),
        "video_prompt": (
            "Three-quarter angle from left. The woman speaks with quiet sadness: "
            "'Left against right. Young against old. We have forgotten how to talk to each other.' "
            "Slow, deliberate. Warm room tone."
        ),
        "script": "Left against right. Young against old. We have forgotten how to talk to each other.",
    },
    {
        "id": "b03_table_empty",
        "type": "broll",
        "duration": 3,
        "image_source": "1_3_v1.png",
        "video_prompt": (
            "Slow pan across the empty dinner table. Chairs pushed back, half-eaten food, "
            "knocked-over glass. Evening light through curtains, lens flare. A chair scrapes. "
            "Phone notification chime. Then silence. Melancholic."
        ),
        "script": "(chair scrape, phone chime, silence)",
    },

    # --- ACT 2: THE CLASHES (rapid persona montage) ---
    {
        "id": "b04_miner",
        "type": "broll",
        "duration": 4,
        "image_source": "2_1a_v2.png",
        "video_prompt": (
            "The coal miner looks at camera, arms crossed, and speaks gruffly: "
            "'Climate change? I have worked this mine for thirty years. You want to take my job "
            "for a theory?' Defiant. Industrial hum. Dusk light behind him."
        ),
        "script": "Climate change? I've worked this mine for thirty years. You want to take my job for a theory?",
    },
    {
        "id": "b05_activist",
        "type": "broll",
        "duration": 4,
        "image_source": "2_1b_v2.png",
        "video_prompt": (
            "The climate activist, tears on her face, speaks with shaking voice: "
            "'A theory? My village has not had rain in two years. This is not a theory. "
            "This is my home disappearing.' Wind over dry cracked earth. Golden hour."
        ),
        "script": "A theory? My village hasn't had rain in two years. This isn't a theory. This is my home disappearing.",
    },
    {
        "id": "b06_vegan",
        "type": "broll",
        "duration": 3,
        "image_source": "2_2a_v2.png",
        "video_prompt": (
            "The tattooed vegan chef holds his dish and speaks with calm intensity: "
            "'You are eating suffering. Every single meal.' Direct stare at camera. "
            "Bright kitchen. Chopping sounds fade in."
        ),
        "script": "You're eating suffering. Every single meal.",
    },
    {
        "id": "b07_rancher",
        "type": "broll",
        "duration": 3,
        "image_source": "2_2b_v3.png",
        "video_prompt": (
            "The cattle rancher leans on his fence and replies slowly: "
            "'My family has raised cattle for four generations. I know every one by name.' "
            "Morning birds. Cattle in the pasture behind him. Sunrise glow."
        ),
        "script": "My family has raised cattle for four generations. I know every one by name.",
    },
    {
        "id": "b08_nationalist",
        "type": "broll",
        "duration": 3,
        "image_source": "2_3a_v2.png",
        "video_prompt": (
            "The man at the rally speaks sharply: 'They call me extreme? I want borders. "
            "I want safety. That is extreme now?' Jaw clenched. Crowd blurred behind. "
            "Megaphone distortion in background."
        ),
        "script": "They call me extreme? I want borders. I want safety. That's extreme now?",
    },
    {
        "id": "b09_marxist",
        "type": "broll",
        "duration": 3,
        "image_source": "2_3b_v3.png",
        "video_prompt": (
            "The woman in the lecture hall leans forward, fist on desk, and fires back rapidly: "
            "'Your borders protect capital, not people. Wake up.' Lecture hall echo. "
            "Fluorescent light overhead. Books around her."
        ),
        "script": "Your borders protect capital, not people. Wake up.",
    },
    {
        "id": "b10_fatherson",
        "type": "broll",
        "duration": 4,
        "image_source": "2_4_v1.png",
        "video_prompt": (
            "Through the window: the father gestures with open arms in frustration and shouts: "
            "'I am trying to protect you!' The teenage son, arms crossed, quietly responds: "
            "'You are not protecting me. You are controlling me.' TV static. Clock ticking. Silence."
        ),
        "script": "I'm trying to protect you! / You're not protecting me. You're controlling me.",
    },

    # --- ACT 3: THE TURN ---
    {
        "id": "n03",
        "type": "narrator",
        "duration": 5,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, straight-on. She pauses, then speaks with quiet intensity. "
            "Leaning forward slightly. Eyes locked on camera. A turning-point moment."
        ),
        "video_prompt": (
            "Medium shot. 3 seconds of silence. Then the woman speaks softly but with conviction: "
            "'What if you could practice the hardest conversations — before they happen?' "
            "Quiet. Intimate. A single WhatsApp notification chime at the very end."
        ),
        "script": "What if you could practice the hardest conversations — before they happen?",
    },

    # --- ACT 4: THE SOLUTION ---
    {
        "id": "b11_whatsapp",
        "type": "broll",
        "duration": 3,
        "image_source": "3_2_v1.png",
        "video_prompt": (
            "Over-the-shoulder: the person scrolls through a WhatsApp conversation in a cozy room. "
            "Green message bubbles. Fireplace glow. Soft typing sounds. "
            "Calm, structured dialogue visible on screen. Shallow depth of field."
        ),
        "script": "(typing sounds)",
    },
    {
        "id": "n04",
        "type": "narrator",
        "duration": 5,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, slight three-quarter from right. She looks confident and warm. "
            "One hand gently gesturing as she explains. Engaged, informative expression."
        ),
        "video_prompt": (
            "Three-quarter angle from right. The woman speaks with confidence: "
            "'NotHabermas gives you AI conversation partners — with real personalities, "
            "real beliefs, and real pushback. On WhatsApp.' Clear, direct delivery."
        ),
        "script": "NotHabermas gives you AI conversation partners — with real personalities, real beliefs, and real pushback.",
    },
    {
        "id": "n05",
        "type": "narrator",
        "duration": 4,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, straight-on. She counts features with her fingers. "
            "Enthusiastic, practical energy. Slight smile."
        ),
        "video_prompt": (
            "Medium shot. She counts on her fingers as she speaks: "
            "'Fact-checking. Mediation. Emotional intelligence training. All in one place.' "
            "Friendly, clear. Warm study background."
        ),
        "script": "Fact-checking. Mediation. Emotional intelligence training.",
    },

    # --- ACT 5: THE CLOSE ---
    {
        "id": "b12_table_hope",
        "type": "broll",
        "duration": 4,
        "image_source": "5_3_v2.png",
        "video_prompt": (
            "The same dinner table, but now two people sit across from each other, leaning in, "
            "mid-conversation. Wine glasses. Anamorphic lens flare from the window. "
            "The mood has shifted from melancholy to warmth and hope. Gentle ambient sound."
        ),
        "script": "(warm conversation ambience)",
    },
    {
        "id": "n06",
        "type": "narrator",
        "duration": 5,
        "image_prompt": (
            f"{NARRATOR_BASE} "
            "Medium shot, straight-on. Big, genuine smile. Warm sign-off energy. "
            "Relaxed posture. The warmest frame."
        ),
        "video_prompt": (
            "Medium shot. The woman speaks with warmth and conviction: "
            "'The gap does not close itself. Start the conversation.' "
            "She pauses. Then quieter, with a smile: 'NotHabermas. Happy hacking.' "
            "Warm room tone fades."
        ),
        "script": "The gap doesn't close itself. Start the conversation. NotHabermas. Happy hacking.",
    },
    {
        "id": "b13_table_final",
        "type": "broll",
        "duration": 3,
        "image_source": "5_3_v1.png",
        "video_prompt": (
            "Final shot: the couple at the dinner table, silhouetted in golden sunset light. "
            "They lean toward each other. Intimate. Hopeful. The frame slowly darkens. "
            "A single soft WhatsApp notification chime. Fade to black."
        ),
        "script": "(WhatsApp chime, fade to black)",
    },
]

# Total duration
TOTAL_DURATION = sum(s["duration"] for s in SHOT_LIST)


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_narrator_frame(client, shot_id: str, prompt: str) -> Path:
    """Generate a narrator start frame via Nano Banana."""
    from google.genai import types

    output_path = FRAMES_DIR / f"{shot_id}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    print(f"    Generating narrator frame: {shot_id}...")
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
                        return output_path
            print(f"    Attempt {attempt + 1}/3: empty, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"    Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(5)

    raise RuntimeError(f"Narrator frame generation failed for {shot_id}")


def generate_clip(client, shot_id: str, start_frame: Path, prompt: str) -> Path | None:
    """Generate an 8-second video clip via Veo 3.0."""
    from google.genai import types

    output_path = CLIPS_DIR / f"{shot_id}.mp4"
    if output_path.exists() and output_path.stat().st_size > 100_000:
        size_mb = output_path.stat().st_size / (1024 * 1024)
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
            print(f"    TIMEOUT after {VEO_POLL_TIMEOUT}s")
            return None
        print(f"    [{elapsed}s] Generating...")
        time.sleep(15)
        operation = client.operations.get(operation)

    elapsed = int(time.time() - start)

    if not operation.response or not operation.response.generated_videos:
        print(f"    ERROR: No video for {shot_id}")
        return None

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Done in {elapsed}s: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def trim_clip(input_path: Path, output_path: Path, duration: int) -> Path:
    """Trim a clip to the target duration from the start."""
    if output_path.exists() and output_path.stat().st_size > 50_000:
        print(f"    [cached] {output_path.name}")
        return output_path

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path),
         "-t", str(duration),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         str(output_path)],
        capture_output=True, check=True,
    )
    return output_path


def concatenate(clip_paths: list[Path], output_path: Path) -> Path:
    """Concatenate clips with ffmpeg."""
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
    return output_path


def mix_music(video_path: Path, music_path: Path, output_path: Path, volume: float = 0.10) -> Path | None:
    """Mix background music."""
    try:
        subprocess.run(
            ["ffmpeg", "-y",
             "-i", str(video_path), "-i", str(music_path),
             "-filter_complex",
             f"[0:a]volume=1.0[voice];[1:a]volume={volume}[bg];"
             f"[voice][bg]amix=inputs=2:duration=shortest[out]",
             "-map", "0:v", "-map", "[out]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart",
             str(output_path)],
            capture_output=True, check=True,
        )
        return output_path
    except subprocess.CalledProcessError:
        print("    WARNING: Music mixing failed")
        return None


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    client = get_client()
    num_shots = len(SHOT_LIST)

    # =====================================================================
    # Print full script
    # =====================================================================
    print("=" * 70)
    print(f"  NOTHABERMAS TRAILER — FINAL PRODUCTION")
    print(f"  {num_shots} shots, ~{TOTAL_DURATION}s total")
    print("=" * 70)

    print("\n  SCRIPT:")
    print("  " + "-" * 66)
    t = 0
    for shot in SHOT_LIST:
        tag = "NARRATOR" if shot["type"] == "narrator" else "B-ROLL"
        print(f"  [{t:02d}-{t + shot['duration']:02d}s] [{tag}] {shot['id']}")
        print(f"           {shot['script']}")
        t += shot["duration"]
    print("  " + "-" * 66)
    print(f"  Total: ~{TOTAL_DURATION}s\n")

    # =====================================================================
    # PHASE 1: Generate narrator frames
    # =====================================================================
    narrator_shots = [s for s in SHOT_LIST if s["type"] == "narrator"]
    print(f"\n{'=' * 70}")
    print(f"  PHASE 1: Generating {len(narrator_shots)} narrator frames (Nano Banana)")
    print(f"{'=' * 70}")

    for shot in narrator_shots:
        print(f"\n  {shot['id']}: {shot['script'][:50]}...")
        generate_narrator_frame(client, shot["id"], shot["image_prompt"])

    # =====================================================================
    # PHASE 2: Generate all video clips (Veo 3.0)
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 2: Generating {num_shots} video clips (Veo 3.0)")
    print(f"{'=' * 70}")

    clip_paths: dict[str, Path] = {}
    failed = []

    for i, shot in enumerate(SHOT_LIST):
        print(f"\n  Shot {i + 1}/{num_shots} — {shot['id']} ({shot['type']}, {shot['duration']}s)")

        if shot["type"] == "narrator":
            frame = FRAMES_DIR / f"{shot['id']}.png"
        else:
            frame = BROLL_DIR / shot["image_source"]
            if not frame.exists():
                print(f"    ERROR: B-roll frame not found: {frame}")
                failed.append(shot["id"])
                continue

        clip = generate_clip(client, shot["id"], frame, shot["video_prompt"])
        if clip:
            clip_paths[shot["id"]] = clip
        else:
            failed.append(shot["id"])
            print(f"    SKIPPING {shot['id']}")

    # =====================================================================
    # PHASE 3: Trim clips to target duration
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 3: Trimming {len(clip_paths)} clips to target durations")
    print(f"{'=' * 70}")

    trimmed_paths: list[Path] = []
    for shot in SHOT_LIST:
        if shot["id"] not in clip_paths:
            continue
        raw = clip_paths[shot["id"]]
        trimmed = TRIMMED_DIR / f"{shot['id']}_trimmed.mp4"
        print(f"\n  {shot['id']}: {shot['duration']}s")
        trim_clip(raw, trimmed, shot["duration"])
        trimmed_paths.append(trimmed)

    # =====================================================================
    # PHASE 4: Concatenate
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  PHASE 4: Concatenating {len(trimmed_paths)} clips")
    print(f"{'=' * 70}")

    final_output = PROJECT_DIR / "nothabermas_trailer_FINAL.mp4"
    concatenate(trimmed_paths, final_output)

    # =====================================================================
    # PHASE 5: Mix music
    # =====================================================================
    final_with_music = None
    if MUSIC_PATH.exists():
        print(f"\n\n{'=' * 70}")
        print(f"  PHASE 5: Mixing background music")
        print(f"{'=' * 70}")
        music_output = PROJECT_DIR / "nothabermas_trailer_FINAL_music.mp4"
        final_with_music = mix_music(final_output, MUSIC_PATH, music_output, volume=0.10)
    else:
        print(f"\n  Skipping music — file not found: {MUSIC_PATH}")

    # =====================================================================
    # Summary
    # =====================================================================
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration,size",
         "-of", "json", str(final_output)],
        capture_output=True, text=True,
    )
    info = json.loads(probe.stdout)["format"]
    duration = float(info["duration"])
    size_mb = int(info["size"]) / (1024 * 1024)

    print(f"\n\n{'=' * 70}")
    print(f"  PRODUCTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Final video:      {final_output.resolve()}")
    if final_with_music:
        print(f"  With music:       {final_with_music.resolve()}")
    print(f"  Duration:         {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"  Size:             {size_mb:.1f} MB")
    print(f"  Shots completed:  {len(trimmed_paths)}/{num_shots}")
    if failed:
        print(f"  Failed:           {', '.join(failed)}")
    print(f"  Clips:            {CLIPS_DIR.resolve()}/")
    print(f"  Trimmed:          {TRIMMED_DIR.resolve()}/")
    print(f"  Narrator frames:  {FRAMES_DIR.resolve()}/")


if __name__ == "__main__":
    main()
