#!/usr/bin/env python3
"""
Test Script: Google Veo 3.1 — Image-to-Video with Native Audio
Uses a start frame image to generate a podcast video with voice.

Audio is always generated natively with Veo 3.x — controlled via prompt.

Usage:
    python test_veo.py [--image PATH_TO_START_FRAME]

If no --image is provided, it uses the Nano Banana output as the start frame.
"""

import argparse
import sys
import time
from pathlib import Path

from config import GEMINI_API_KEY, OUTPUT_DIR, VIDEO_PROMPT


def main() -> None:
    parser = argparse.ArgumentParser(description="Veo 3.1 image-to-video test")
    parser.add_argument(
        "--image",
        type=Path,
        default=OUTPUT_DIR / "nano_banana_podcast_frame.png",
        help="Path to start frame image",
    )
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set. Add it to .env")
        sys.exit(1)

    if not args.image.exists():
        print(f"ERROR: Image not found: {args.image}")
        print("Run test_nano_banana.py first to generate the start frame.")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    print("=== Google Veo 3.1 — Image-to-Video with Audio ===")
    print(f"Model: veo-3.0-generate-001")
    print(f"Start frame: {args.image}")
    print(f"Audio: native (always on with Veo 3.x, controlled via prompt)")
    print(f"Prompt: {VIDEO_PROMPT[:80]}...")
    print()

    # Load image
    image = types.Image.from_file(location=str(args.image))

    print("Submitting video generation request...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=VIDEO_PROMPT,
        image=image,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            resolution="720p",
        ),
    )

    print(f"Operation started. Polling for completion...")
    start = time.time()

    while not operation.done:
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] Waiting...")
        time.sleep(15)
        operation = client.operations.get(operation)

    elapsed = int(time.time() - start)
    print(f"  [{elapsed}s] Done!")

    if not operation.response or not operation.response.generated_videos:
        print(f"ERROR: No video in response.")
        print(f"Operation: {operation}")
        sys.exit(1)

    video = operation.response.generated_videos[0]

    # Download and save
    output_path = OUTPUT_DIR / "veo_democracy_podcast.mp4"
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    print(f"\n=== SUCCESS ===")
    print(f"Local file: {output_path.resolve()}")
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
