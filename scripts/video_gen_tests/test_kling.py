#!/usr/bin/env python3
"""
Test Script: Kling AI 3.0 — Image-to-Video with Native Audio
Uses a start frame image to generate a podcast video with voice.

Usage:
    python test_kling.py [--image PATH_TO_START_FRAME]

If no --image is provided, it uses the Nano Banana output as the start frame.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

import jwt
import requests

from config import (
    KLING_ACCESS_KEY,
    KLING_BASE_URL,
    KLING_SECRET_KEY,
    OUTPUT_DIR,
    VIDEO_NEGATIVE_PROMPT,
    VIDEO_PROMPT,
)


def generate_jwt() -> str:
    """Generate a short-lived JWT token for Kling API auth."""
    now = int(time.time())
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": now + 1800,
        "nbf": now - 5,
    }
    return jwt.encode(payload, KLING_SECRET_KEY, headers=headers)


def api_headers() -> dict:
    return {
        "Authorization": f"Bearer {generate_jwt()}",
        "Content-Type": "application/json",
    }


def image_to_base64(image_path: Path) -> str:
    """Read an image file and return its base64 encoding."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_task(image_path: Path) -> str:
    """Submit an image-to-video task and return the task ID."""
    b64 = image_to_base64(image_path)

    payload = {
        "model_name": "kling-v3",
        "image": b64,
        "prompt": VIDEO_PROMPT,
        "negative_prompt": VIDEO_NEGATIVE_PROMPT,
        "duration": "5",
        "mode": "pro",
        "cfg_scale": 0.5,
        "sound": 1,
    }

    resp = requests.post(
        f"{KLING_BASE_URL}/v1/videos/image2video",
        headers=api_headers(),
        json=payload,
        timeout=60,
    )
    data = resp.json()
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} — {data}")
        sys.exit(1)

    if "data" not in data or "task_id" not in data["data"]:
        print(f"ERROR: Unexpected response: {data}")
        sys.exit(1)

    return data["data"]["task_id"]


def poll_task(task_id: str, max_wait: int = 300) -> str:
    """Poll until the task completes. Returns the video URL."""
    print(f"Polling task {task_id}...")
    start = time.time()

    while time.time() - start < max_wait:
        resp = requests.get(
            f"{KLING_BASE_URL}/v1/videos/image2video/{task_id}",
            headers=api_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["task_status"]
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] Status: {status}")

        if status == "succeed":
            video_url = data["task_result"]["videos"][0]["url"]
            return video_url
        elif status == "failed":
            print(f"ERROR: Task failed. Response: {data}")
            sys.exit(1)

        time.sleep(10)

    print(f"ERROR: Timed out after {max_wait}s")
    sys.exit(1)


def download_video(url: str, output_path: Path) -> None:
    """Download the video from the URL."""
    print(f"Downloading video...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)
    size_mb = len(resp.content) / (1024 * 1024)
    print(f"Saved: {output_path} ({size_mb:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kling 3.0 image-to-video test")
    parser.add_argument(
        "--image",
        type=Path,
        default=OUTPUT_DIR / "nano_banana_podcast_frame.png",
        help="Path to start frame image",
    )
    args = parser.parse_args()

    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        print("ERROR: KLING_ACCESS_KEY and KLING_SECRET_KEY must be set in .env")
        sys.exit(1)

    if not args.image.exists():
        print(f"ERROR: Image not found: {args.image}")
        print("Run test_nano_banana.py first to generate the start frame.")
        sys.exit(1)

    print("=== Kling AI 3.0 — Image-to-Video with Audio ===")
    print(f"Model: kling-v3 (pro mode)")
    print(f"Start frame: {args.image}")
    print(f"Audio: enabled (native voice generation)")
    print(f"Prompt: {VIDEO_PROMPT[:80]}...")
    print()

    task_id = create_task(args.image)
    print(f"Task created: {task_id}")

    video_url = poll_task(task_id)
    print(f"\nVideo URL: {video_url}")

    output_path = OUTPUT_DIR / "kling_democracy_podcast.mp4"
    download_video(video_url, output_path)

    print("\n=== SUCCESS ===")
    print(f"Video URL: {video_url}")
    print(f"Local file: {output_path.resolve()}")


if __name__ == "__main__":
    main()
