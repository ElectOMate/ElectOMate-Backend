#!/usr/bin/env python3
"""
Producer: Election Explainer Video (Test — Question 1, Type 1 Avatar)

Generates multi-clip video via Nano Banana (start frames) + Veo 3.0 (8s clips),
concatenates with ffmpeg.

Style: Colorful metallic studio, professional presenter.
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

# ---------------------------------------------------------------------------
# Production log
# ---------------------------------------------------------------------------
PRODUCTION_LOG: dict = {
    "run_started": None,
    "run_finished": None,
    "model_image": "gemini-2.5-flash-image",
    "model_video": "veo-3.0-generate-001",
    "character_description": None,
    "angles": {},
    "shots": [],
    "clips_generated": [],
    "clips_failed": [],
    "final_outputs": [],
}
VEO_POLL_TIMEOUT = 300  # 5 minutes max per clip

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
PROJECT_DIR = OUTPUT_DIR / "election_test_q01"
FRAMES_DIR = PROJECT_DIR / "frames"
CLIPS_DIR = PROJECT_DIR / "clips"
for d in [PROJECT_DIR, FRAMES_DIR, CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Character & Setting — v5e Mediterranean, teal spotlight backdrop
# ---------------------------------------------------------------------------
CHARACTER = (
    "A Mediterranean woman in her early 30s with thick dark wavy hair, olive skin, "
    "strong natural eyebrows, and deep brown eyes. She wears a simple white linen "
    "button-up shirt with the collar relaxed and top button undone. A thin worn leather "
    "bracelet on one wrist. No other jewelry, no makeup. Her expression is calm and "
    "grounded — serious but approachable. Visible natural skin texture, slight under-eye "
    "shadows, real human face."
)

SETTING = (
    "Medium shot, waist-up framing — no legs visible, no table, no desk, no furniture. "
    "She stands upright. "
    "BACKGROUND: A single monochromatic canvas backdrop in a deep muted teal color "
    "(bright spotlight center ~#4d6869, fading to very dark ~#0e2227 at edges). "
    "A single soft spotlight hits the center behind her, creating a diffused bright area "
    "that smoothly darkens toward all edges — classic portrait vignette. No equipment, "
    "no props, no text. Just the smooth gradient. "
    "LIGHTING: One overhead softbox from above. One key light from upper left creating "
    "gentle modeling on her face with subtle shadow on right side."
)

CAMERA = (
    "Shot on a Leica SL2 with a Summilux 75mm f/1.4 lens. Exceptional subject separation. "
    "Rich warm skin tones with Leica color science. Cinematic depth. Fine organic grain."
)

# ---------------------------------------------------------------------------
# Camera angles
# ---------------------------------------------------------------------------
ANGLES = {
    "medium_front": (
        "Medium shot, straight-on, waist-up framing. Centered symmetrical composition. "
        "She looks directly at camera with a calm, neutral expression."
    ),
    "side_left": (
        "Three-quarter shot from 45 degrees to the left. She is slightly turned "
        "toward this camera. Rim light on the right side of her face. "
        "Teal backdrop visible with spotlight gradient."
    ),
    "closeup_front": (
        "Tight close-up, head and shoulders only. Very shallow depth of field, "
        "teal bokeh in background. Eyes tack-sharp. Intimate, engaging framing."
    ),
    "wide_establishing": (
        "Wider shot showing her from waist up with more of the teal backdrop visible. "
        "The spotlight vignette fully visible. She is centered, standing upright."
    ),
}

# ---------------------------------------------------------------------------
# Shot list — 12 clips x 8 seconds = 96 seconds
# (clip_num, angle_key, is_continuation, dialogue)
# ---------------------------------------------------------------------------
SHOTS = [
    # --- BEVEZETŐ ---
    (1, "wide_establishing", False,
     "Üdvözlöm. Ma a magyar külpolitika egyik legfontosabb kérdését járjuk körül: "
     "Magyarországnak a diplomáciai tárgyalásokat kell-e előtérbe helyeznie Oroszországgal "
     "az ukrajnai konfliktus lezárása érdekében?"),

    (2, "medium_front", False,
     "Ez egy külpolitikai kérdés — konkrétan arról szól, hogy Magyarország a saját "
     "diplomáciai útját járja-e Moszkvával, vagy kiálljon az EU mellett Ukrajna "
     "katonai támogatásában."),

    # --- KONTEXTUS ---
    (3, "side_left", False,
     "Amit tudni kell: Magyarország megvétózta az EU Ukrajnának szánt hitelcsomagjait "
     "és nem küldött fegyvereket. Ezalatt az ellenzéki pártok azt javasolják, hogy "
     "Magyarország szüntesse meg a vétóit."),

    # --- IGEN ÁLLÁSPONT ---
    (4, "medium_front", False,
     "Az igen oldal érvei: Az Oroszországgal folytatott közvetlen diplomácia a "
     "leghatékonyabb út az ukrajnai konfliktus lezárásához, és ahhoz, hogy Magyarország "
     "kimaradjon egy olyan háborúból, amelyet nem nyerhet meg."),

    (5, "closeup_front", False,
     "Magas szintű tárgyalások már zajlottak, beleértve a moszkvai találkozókat, "
     "és Budapestet is felajánlották az amerikai-orosz béketárgyalások helyszíneként."),

    (6, "side_left", False,
     "A támogatók figyelmeztetnek: az európai országok azt kockáztatják, hogy "
     "belekeverednek egy olyan konfliktus finanszírozásába és eszkalálásába, "
     "amelyre nincs katonai megoldás."),

    (7, "medium_front", True,
     "Szerintük Magyarországnak meg kell védenie szuverenitását azáltal, hogy nem küld "
     "fegyvereket, pénzt vagy katonákat Ukrajnába — a békét helyezve előtérbe a "
     "brüsszeli katonai eszkalációval szemben."),

    # --- NEM ÁLLÁSPONT ---
    (8, "medium_front", False,
     "Most pedig a nem oldal érvei: Az Oroszországgal folytatott kétoldalú diplomácia "
     "előtérbe helyezése az EU szolidaritásával szemben alapvetően aláássa az európai "
     "egységet a hidegháború óta legveszélyesebb pillanatban."),

    (9, "closeup_front", False,
     "Úgy vélik, hogy Ukrajna védelmének támogatása uniós koordináción keresztül, "
     "közvetlen katonai beavatkozás nélkül, a felelős út, amely erősíti a biztonságot "
     "és a szövetség hitelességét."),

    (10, "side_left", False,
     "A kritikusok rámutatnak, hogy az EU támogatási csomagjainak megvétózása "
     "diplomáciailag elszigeteli Magyarországot és rombolja az évtizedek alatt "
     "kiépített NATO-partneri bizalmat."),

    (11, "medium_front", False,
     "Több pro-európai keretrendszer is megerősíti, hogy Magyarország nyugati szövetségi "
     "rendszerekbe való beágyazása, az orosz energiafüggőség csökkentésével együtt, "
     "jobban szolgálja a hosszú távú nemzeti érdeket."),

    # --- ZÁRÓ ---
    (12, "wide_establishing", False,
     "Most már ismeri mindkét oldal érveit. A diplomácia melletti és a szolidaritás "
     "melletti érveket egyaránt. A döntés az Öné. Köszönöm, hogy végignézte."),
]


# ---------------------------------------------------------------------------
# API helpers (same pattern as produce_hungarian_podcast.py)
# ---------------------------------------------------------------------------

def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_angle_image(client, angle_key: str) -> Path:
    """Generate a start frame image for a given camera angle via Nano Banana."""
    from google.genai import types

    output_path = FRAMES_DIR / f"angle_{angle_key}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

    prompt = f"{CHARACTER}\n\n{SETTING}\n\n{ANGLES[angle_key]}"
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
            PRODUCTION_LOG["clips_generated"].append({
                "type": "image", "angle": angle_key,
                "file": str(output_path.resolve()),
                "size": f"{image.size[0]}x{image.size[1]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return output_path

    print(f"    ERROR: No image generated for {angle_key}")
    PRODUCTION_LOG["clips_failed"].append({"type": "image", "angle": angle_key})
    sys.exit(1)


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
        "type": "video", "clip": clip_num,
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
    print(f"    Final video: {output_path} ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set. Export it or add to .env")
        sys.exit(1)

    PRODUCTION_LOG["run_started"] = datetime.now(timezone.utc).isoformat()
    PRODUCTION_LOG["character_description"] = CHARACTER
    PRODUCTION_LOG["setting_description"] = SETTING
    PRODUCTION_LOG["angles"] = ANGLES
    PRODUCTION_LOG["shots"] = [
        {"clip": n, "angle": a, "continuation": c, "dialogue": d[:100] + "..."}
        for n, a, c, d in SHOTS
    ]

    client = get_client()
    clip_paths: list[Path] = []

    total_clips = len(SHOTS)
    print("=" * 60)
    print("  ELECTION EXPLAINER — Q1 TEST VIDEO")
    print(f"  {total_clips} clips × 8s = {total_clips * 8}s")
    print(f"  Style: Colorful metallic studio")
    print("=" * 60)

    # Phase 1: Generate all unique angle images via Nano Banana
    print("\n--- Phase 1: Generating angle images via Nano Banana ---")
    unique_angles = set()
    for _, angle, is_cont, _ in SHOTS:
        if not is_cont:
            unique_angles.add(angle)

    for angle in sorted(unique_angles):
        generate_angle_image(client, angle)

    # Phase 2: Generate video clips via Veo 3.0
    print(f"\n--- Phase 2: Generating {total_clips} video clips via Veo 3.0 ---")
    prev_clip_path: Path | None = None

    for clip_num, angle, is_continuation, dialogue in SHOTS:
        print(f"\n  Clip {clip_num:02d}/{total_clips} — {angle}"
              + (" (continuation)" if is_continuation else ""))

        # Build video prompt
        angle_desc = ANGLES[angle]
        video_prompt = (
            f"{CHARACTER}\n\n{SETTING}\n\n{angle_desc}\n\n{CAMERA}\n\n"
            f"The presenter speaks directly to camera in Hungarian with calm, natural delivery: "
            f"'{dialogue}' "
            f"Natural pacing, neutral informative tone. She speaks Hungarian fluently. "
            f"Soft ambient room tone, quiet studio atmosphere."
        )

        if is_continuation and prev_clip_path and prev_clip_path.exists():
            start_frame = FRAMES_DIR / f"lastframe_clip_{clip_num - 1:02d}.png"
            extract_last_frame(prev_clip_path, start_frame)
        else:
            start_frame = FRAMES_DIR / f"angle_{angle}.png"

        clip_path = generate_video_clip(client, clip_num, start_frame, video_prompt)
        if clip_path:
            clip_paths.append(clip_path)
            prev_clip_path = clip_path
        else:
            print(f"    SKIPPING clip {clip_num} due to generation failure")

    # Phase 3: Concatenate
    print(f"\n--- Phase 3: Concatenating {len(clip_paths)} clips ---")
    final_output = PROJECT_DIR / "election_q01_type1_FINAL.mp4"
    concatenate_clips(clip_paths, final_output)

    PRODUCTION_LOG["final_outputs"].append(str(final_output.resolve()))
    PRODUCTION_LOG["run_finished"] = datetime.now(timezone.utc).isoformat()

    # Save production log
    log_path = PROJECT_DIR / "production_log.json"
    with open(log_path, "w") as f:
        json.dump(PRODUCTION_LOG, f, indent=2)
    print(f"\n  Production log: {log_path}")

    print("\n" + "=" * 60)
    print(f"  DONE! Final video: {final_output}")
    print(f"  Clips generated: {len(clip_paths)}/{total_clips}")
    print(f"  Clips failed: {len(PRODUCTION_LOG['clips_failed'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
