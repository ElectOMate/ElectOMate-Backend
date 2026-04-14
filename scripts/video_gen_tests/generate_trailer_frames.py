#!/usr/bin/env python3
"""
Generate 3 versions of every start frame for the NotHabermas trailer.
No video generation — just Nano Banana images.
Outputs absolute paths for all generated images.
"""

import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage

from config import GEMINI_API_KEY, OUTPUT_DIR

# Output directory
TRAILER_DIR = OUTPUT_DIR / "trailer_frames"
TRAILER_DIR.mkdir(parents=True, exist_ok=True)

NUM_VERSIONS = 3

# --- All image prompts from trailer_script.md ---
# Each entry: (scene_id, prompt)
IMAGE_PROMPTS = [
    ("1_1", (
        "Cinematic close-up of a middle-aged father in a dim kitchen, veins visible on his neck, "
        "mouth open mid-shout, pointing aggressively at someone off-camera. Warm tungsten light from "
        "a single overhead bulb. Shallow depth of field. 35mm film grain. Dramatic shadows on face."
    )),

    ("1_2", (
        "Split-screen composition. Left side: a young man in a black hoodie at a protest, face "
        "contorted in rage, holding a red banner with a clenched fist symbol, smoke in the background, "
        "dramatic side-lighting. Right side: a middle-aged man in a polo shirt at a counter-protest, "
        "face equally furious, waving a national flag, golden hour backlight. Both figures shot in "
        "cinematic 2.39:1 aspect ratio. Photorealistic, shallow depth of field."
    )),

    ("1_3", (
        "Cinematic wide shot of an empty dinner table with two chairs pushed back, half-eaten food "
        "on plates, a knocked-over glass of water. Evening light through curtains. The scene looks "
        "like two people just walked away mid-conversation. Melancholic. Shot on anamorphic lens with "
        "subtle lens flare from the window."
    )),

    ("2_1a", (
        "Cinematic portrait of a weathered 55-year-old coal miner in a hard hat, standing in front "
        "of an industrial landscape at dusk. Arms crossed. Defiant expression. Orange industrial light "
        "behind him. Shot on 85mm lens, f/1.4, cinematic color grading with teal shadows and orange highlights."
    )),

    ("2_1b", (
        "Cinematic portrait of a 22-year-old climate activist, tears streaming down her face, standing "
        "in front of a dried-up riverbed with cracked earth. She wears a hand-painted sign around her "
        "neck. Golden hour light. Emotional. Shot at eye level, intimate framing."
    )),

    ("2_2a", (
        "Cinematic close-up of a 30-year-old tattooed vegan chef in a bright modern kitchen, holding "
        "a vibrant plant-based dish, looking directly at camera with calm intensity. Natural window "
        "light. Clean, minimal background. Shallow depth of field."
    )),

    ("2_2b", (
        "Cinematic portrait of a 45-year-old cattle rancher leaning on a wooden fence at sunrise, "
        "cowboy hat, weathered hands, a vast pasture behind him. Warm golden light. He looks tired "
        "but proud. Shot in wide aspect ratio."
    )),

    ("2_3a", (
        "Cinematic portrait of a 40-year-old man in a plain black t-shirt at a rally, jaw clenched, "
        "intense stare, holding a sign that reads 'OUR COUNTRY FIRST'. Crowd blurred behind him. "
        "Hard directional light from the left, deep shadows on the right side of his face. Gritty, "
        "photojournalistic style."
    )),

    ("2_3b", (
        "Cinematic portrait of a 35-year-old woman with short hair and round glasses in a university "
        "lecture hall, leaning forward passionately, fist on the desk. Warm overhead fluorescent light. "
        "Books stacked around her. Intellectual intensity. Shot slightly from below."
    )),

    ("2_4", (
        "Cinematic medium shot of a father and teenage son in a living room, facing each other. The "
        "father stands with arms open in frustration, the son sits on the couch with headphones around "
        "his neck, looking away. A TV glows blue in the background. Tension in the body language. "
        "Domestic evening light. Shot through a slightly dirty window or doorframe to create voyeuristic framing."
    )),

    ("3_1", (
        "Black screen with a single line of white text in a clean sans-serif font: "
        "'What if you could practice the conversation before it happens?' "
        "The text appears letter by letter. Cinematic 2.39:1 aspect ratio. Subtle film grain on the black."
    )),

    ("3_2", (
        "Cinematic over-the-shoulder shot of a person holding a phone, a WhatsApp conversation visible "
        "on screen. The messages show a calm, structured dialogue. The person is sitting in a warm, cozy "
        "room. Soft evening light. Shallow depth of field so the phone screen is in focus and the "
        "background is a warm blur."
    )),

    ("4_1", (
        "Cinematic shot of a smartphone screen showing a WhatsApp message that says 'Is this true?' "
        "with a forwarded news headline below it. A glowing checkmark appears as a reply. The phone "
        "is held by a hand in a coffee shop setting. Shallow depth of field. Warm, inviting light."
    )),

    ("4_2", (
        "Cinematic top-down shot of three phones on a table arranged in a triangle, each showing a "
        "WhatsApp group conversation. The middle area between the phones glows subtly as if the "
        "conversation is connecting them. Clean wooden table. Dramatic overhead light."
    )),

    ("4_3", (
        "Cinematic close-up of a person's face transitioning from frustration to understanding — "
        "captured mid-expression change. Soft, warm studio lighting from both sides. The face is "
        "slightly out of focus at first, then pulls into sharp focus. Intimate, emotional. 85mm portrait lens."
    )),

    ("5_1", (
        "Cinematic shot of a hand tapping 'Send' on a WhatsApp message. The message reads "
        "'I want to talk to someone who disagrees with me.' The screen glows in a dark room. "
        "Intimate. Shot macro on the fingertip touching the screen."
    )),

    ("5_2", (
        "Cinematic shot of the WhatsApp contact card for NotHabermas — a clean, minimal logo as "
        "the profile picture, on a phone held casually. Background is blurred city lights at night. "
        "The screen is the main light source on the person's face."
    )),

    ("5_3", (
        "Cinematic wide shot. The same empty dinner table from Scene 1.3, but now two people are "
        "sitting across from each other, leaning in, mid-conversation. The knocked-over glass has "
        "been picked up. The evening light is warmer now. Same anamorphic lens, but the mood has "
        "shifted from melancholy to hope. Subtle lens flare from the window."
    )),
]


def get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def generate_image(client, scene_id: str, prompt: str, version: int) -> Path | None:
    """Generate one image via Nano Banana."""
    from google.genai import types

    output_path = TRAILER_DIR / f"{scene_id}_v{version}.png"
    if output_path.exists():
        print(f"    [cached] {output_path.name}")
        return output_path

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
            print(f"    Attempt {attempt + 1}/3: empty response, retrying...")
            time.sleep(5)
        except Exception as e:
            print(f"    Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(5)

    print(f"    FAILED: {scene_id} v{version}")
    return None


def main() -> None:
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    client = get_client()
    total = len(IMAGE_PROMPTS) * NUM_VERSIONS
    generated = 0
    failed = 0

    # =====================================================================
    # Print all prompts first
    # =====================================================================
    print("=" * 70)
    print("  NOTHABERMAS TRAILER — IMAGE PROMPTS")
    print(f"  {len(IMAGE_PROMPTS)} scenes × {NUM_VERSIONS} versions = {total} images")
    print("=" * 70)

    for scene_id, prompt in IMAGE_PROMPTS:
        print(f"\n  [{scene_id}]")
        print(f"  {prompt}")

    # =====================================================================
    # Generate all images
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  GENERATING {total} IMAGES")
    print(f"{'=' * 70}")

    results: dict[str, list[Path]] = {}

    for scene_id, prompt in IMAGE_PROMPTS:
        print(f"\n  Scene {scene_id} ({NUM_VERSIONS} versions)")
        results[scene_id] = []

        for v in range(1, NUM_VERSIONS + 1):
            path = generate_image(client, scene_id, prompt, v)
            if path:
                results[scene_id].append(path)
                generated += 1
            else:
                failed += 1

    # =====================================================================
    # Summary with absolute paths
    # =====================================================================
    print(f"\n\n{'=' * 70}")
    print(f"  GENERATION COMPLETE — {generated}/{total} succeeded, {failed} failed")
    print(f"{'=' * 70}")

    for scene_id, prompt in IMAGE_PROMPTS:
        print(f"\n  [{scene_id}]")
        print(f"  Prompt: {prompt[:80]}...")
        paths = results.get(scene_id, [])
        for p in paths:
            print(f"    {p.resolve()}")


if __name__ == "__main__":
    main()
