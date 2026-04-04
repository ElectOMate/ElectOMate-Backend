"""Shared configuration for video generation test scripts."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from this directory
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# --- Kling AI 3.0 ---
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_BASE_URL = "https://api.klingai.com"

# --- Google Gemini API (Veo 3.1 + Nano Banana) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Output directory ---
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Shared prompts (podcast democracy explorer theme) ---
IMAGE_PROMPT = (
    "A photorealistic medium shot of a male explorer in his 40s wearing a khaki vest "
    "and round glasses, seated at a dark wooden podcast desk with two professional "
    "microphones. Behind him is a world map with democracy index highlights. "
    "The lighting is warm and serious, like a high-end interview studio. "
    "A small label reads 'Democracy Deep Dive'. Cinematic, 4K, shallow depth of field."
)

VIDEO_PROMPT = (
    "The explorer leans forward toward the microphone and says in a calm, authoritative voice: "
    "'Did you know that ancient Athens, the birthplace of democracy, actually excluded women, "
    "slaves, and foreigners from voting — meaning only about 10 to 20 percent of the population "
    "could participate? True democracy, as we understand it today, is remarkably young.' "
    "He gestures thoughtfully with one hand. The camera slowly pushes in. "
    "Ambient studio hum and soft background music. Serious, documentary tone."
)

VIDEO_NEGATIVE_PROMPT = (
    "blurry, low quality, cartoon, anime, distorted faces, flickering, morphing, "
    "watermark, text overlay, split screen"
)
