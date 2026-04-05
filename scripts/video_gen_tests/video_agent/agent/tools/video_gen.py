"""Video generation tools: Nano Banana image gen + Veo 3.0 video gen."""

import os
import time
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

VEO_POLL_TIMEOUT = 300
VEO_POLL_INTERVAL = 15


def get_gemini_client():
    from google import genai
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))


def generate_image(prompt: str, output_path: str, aspect_ratio: str = "16:9") -> str:
    """Generate an image using Nano Banana (Gemini image gen)."""
    from google.genai import types

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if Path(output_path).exists():
        return output_path

    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )

    for part in response.parts:
        if part.inline_data:
            image = PILImage.open(BytesIO(part.inline_data.data))
            image.save(output_path)
            return output_path

    raise RuntimeError("No image generated")


def generate_video_clip(
    image_path: str,
    prompt: str,
    output_path: str,
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
) -> str:
    """Generate an 8-second video clip using Veo 3.0."""
    from google.genai import types

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if Path(output_path).exists() and Path(output_path).stat().st_size > 100_000:
        return output_path

    client = get_gemini_client()
    image = types.Image.from_file(location=image_path)

    operation = client.models.generate_videos(
        model="veo-3.0-generate-001",
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        ),
    )

    start = time.time()
    while not operation.done:
        if time.time() - start > VEO_POLL_TIMEOUT:
            raise TimeoutError(f"Veo timed out after {VEO_POLL_TIMEOUT}s")
        time.sleep(VEO_POLL_INTERVAL)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        raise RuntimeError("No video generated")

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(output_path)

    return output_path


def generate_script(topic: str, num_segments: int, tone: str, language: str) -> list[dict]:
    """Generate a timestamped script with source citation points."""
    client = get_gemini_client()

    prompt = (
        f"You are a professional script writer for a political explainer YouTube video.\n"
        f"Topic: {topic}\n"
        f"Tone: {tone}\n"
        f"Language: {language}\n"
        f"Number of segments: {num_segments}\n\n"
        f"Write a script as a JSON array. Each segment should have:\n"
        f"- 'segment_num': integer\n"
        f"- 'text': the spoken dialogue (1-2 sentences, speakable in ~8 seconds)\n"
        f"- 'camera_angle': one of 'medium_front', 'side_left', 'side_right', 'closeup_front', 'wide'\n"
        f"- 'needs_source': boolean (true if this segment cites a fact that needs sourcing)\n"
        f"- 'source_hint': string (what kind of source to find, e.g. 'election statistics 2022')\n"
        f"- 'b_roll_suggestion': string or null (what visual to show alongside, e.g. 'map of Hungary')\n\n"
        f"The first segment should be an intro, the last a sign-off.\n"
        f"Output ONLY valid JSON, no markdown fences."
    )

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    import json
    segments = json.loads(text)
    return segments
