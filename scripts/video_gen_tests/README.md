# Video Generation Test Scripts

Test scripts for Kling AI 3.0, Google Veo 3.1, and Nano Banana (Gemini) image generation.

## Setup

```bash
cd ElectOMate-Backend/scripts/video_gen_tests
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## API Keys

| Service | Key Name | Get It At |
|---------|----------|-----------|
| **Kling AI 3.0** | `KLING_ACCESS_KEY` + `KLING_SECRET_KEY` | https://app.klingai.com/global/dev/api-key |
| **Google Gemini** (Veo 3.1 + Nano Banana) | `GEMINI_API_KEY` | https://aistudio.google.com (Key icon, top-right) |

## Scripts

| Script | What It Does |
|--------|-------------|
| `test_nano_banana.py` | Generates a podcast start-frame image using Gemini image gen |
| `test_kling.py` | Image-to-video with Kling 3.0 + native voice audio |
| `test_veo.py` | Image-to-video with Veo 3.1 + native voice audio |
| `run_all.py` | Runs the full pipeline: image → both video generators |

## Usage

```bash
# Full pipeline
python run_all.py

# Or run individually
python test_nano_banana.py          # Generate start frame first
python test_kling.py                # Then video gen
python test_veo.py                  # Then video gen

# Use a custom start frame
python test_kling.py --image /path/to/your/image.png
python test_veo.py --image /path/to/your/image.png
```

## Output

All outputs go to `./output/`:
- `nano_banana_podcast_frame.png` — Start frame image
- `kling_democracy_podcast.mp4` — Kling 3.0 video with voice
- `veo_democracy_podcast.mp4` — Veo 3.1 video with voice
