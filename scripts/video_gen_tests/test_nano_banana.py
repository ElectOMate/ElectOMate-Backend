#!/usr/bin/env python3
"""
Test Script: Nano Banana (Google Gemini) Image Generation
Generates a podcast-studio start frame for the democracy explorer.

Usage:
    python test_nano_banana.py
"""

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

from config import GEMINI_API_KEY, IMAGE_PROMPT, OUTPUT_DIR


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set. Add it to .env")
        sys.exit(1)

    # Import here so missing key fails fast with a clear message
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    print("=== Nano Banana Image Generation ===")
    print(f"Model: gemini-2.5-flash-image")
    print(f"Prompt: {IMAGE_PROMPT[:80]}...")
    print("Generating image...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=IMAGE_PROMPT,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="16:9",
            ),
        ),
    )

    output_path: Path | None = None

    for part in response.parts:
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            output_path = OUTPUT_DIR / "nano_banana_podcast_frame.png"
            image.save(output_path)
            print(f"Image saved: {output_path}")
            print(f"Size: {image.size[0]}x{image.size[1]}")
            break

    if output_path is None:
        print("ERROR: No image in response.")
        print(f"Response text: {response.text if hasattr(response, 'text') else 'N/A'}")
        sys.exit(1)

    print("\n=== SUCCESS ===")
    print(f"Output: {output_path.resolve()}")
    return str(output_path.resolve())


if __name__ == "__main__":
    main()
