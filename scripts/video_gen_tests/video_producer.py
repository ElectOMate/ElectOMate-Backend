#!/usr/bin/env python3
"""
video_producer.py — General-purpose AI video production pipeline.

Generates multi-clip videos with Nano Banana (image gen) + Veo 3.0 (video gen),
stitches them with ffmpeg, and optionally mixes background music.

Can be called as a CLI tool or imported as a library.

Usage (CLI):
    python video_producer.py --config production.json
    python video_producer.py --topic "Hungarian democracy" --duration 60 --perspectives 3 --style podcast
    python video_producer.py --topic "Space exploration" --duration 120 --perspectives 5 --style documentary --orientation portrait

Usage (Library):
    from video_producer import VideoProducer, ProductionConfig
    config = ProductionConfig(topic="...", duration_seconds=60, num_perspectives=3)
    producer = VideoProducer(config)
    result = producer.produce()
    print(result.final_video_path)
"""

import argparse
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

try:
    from PIL import Image as PILImage
except ImportError:
    print("ERROR: pip install Pillow")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ProductionConfig:
    """All parameters for a video production run."""

    # Content
    topic: str = "An interesting topic"
    style: str = "podcast"  # podcast | documentary | explainer | selfie | interview
    tone: str = "serious"   # serious | funny | dramatic | casual
    language: str = "English"

    # Dimensions
    duration_seconds: int = 60           # Total target duration
    clip_duration: int = 8               # Each clip is 8s (Veo limit)
    num_perspectives: int = 3            # Number of distinct camera angles
    orientation: str = "landscape"       # landscape (16:9) | portrait (9:16)

    # Character
    character_description: str = ""      # If empty, auto-generated from style
    setting_description: str = ""        # If empty, auto-generated from style

    # Technical
    resolution: str = "720p"
    model_image: str = "gemini-2.5-flash-image"
    model_video: str = "veo-3.0-generate-001"
    veo_poll_timeout: int = 300          # Max seconds to wait per clip
    poll_interval: int = 15

    # Music
    background_music_path: str = ""      # Path to MP3 for background music
    music_volume: float = 0.12           # 0.0-1.0, how loud the music is

    # Output
    output_dir: str = "./output"
    project_name: str = ""               # Auto-generated if empty

    def __post_init__(self):
        if not self.project_name:
            slug = self.topic.lower().replace(" ", "_")[:30]
            self.project_name = f"{slug}_{self.style}"

    @property
    def num_clips(self) -> int:
        return max(1, math.ceil(self.duration_seconds / self.clip_duration))

    @property
    def aspect_ratio(self) -> str:
        return "9:16" if self.orientation == "portrait" else "16:9"


@dataclass
class ProductionResult:
    """Result of a production run."""
    final_video_path: str = ""
    final_video_with_music_path: str = ""
    clips_dir: str = ""
    frames_dir: str = ""
    log_path: str = ""
    duration_seconds: float = 0.0
    num_clips_generated: int = 0
    num_clips_failed: int = 0
    success: bool = False


# ---------------------------------------------------------------------------
# Style presets — auto-generate character/setting/angles from style name
# ---------------------------------------------------------------------------

STYLE_PRESETS = {
    "podcast": {
        "character": (
            "A {gender} podcast host in their {age}s, {appearance}. "
            "Seated at a dark wooden desk with two professional boom-arm microphones. "
            "Wearing smart-casual attire. "
        ),
        "setting": (
            "A professional podcast studio. Background: {background}. "
            "Warm tungsten key light from above-left. Desk label reads '{show_name}'. "
            "Cinematic, 4K quality, shallow depth of field."
        ),
        "angles": {
            "medium_front": "Medium shot, straight-on, waist-up. Both microphones visible. Centered composition. Looking at camera.",
            "side_left": "Three-quarter shot from 45° left. One mic prominent in foreground. Rim light on right side of face.",
            "side_right": "Three-quarter shot from 45° right. One mic in foreground right. Key light models left side of face.",
            "closeup_front": "Tight close-up, head and shoulders. Very shallow DOF. Eyes tack-sharp. Intimate framing.",
            "closeup_side": "Near-profile from left. Dramatic rim lighting on face edge. Contemplative mood.",
            "wide_establishing": "Wide shot showing full desk, both mics on boom arms, complete background, studio environment.",
        },
        "defaults": {
            "gender": "male", "age": "40", "appearance": "short brown hair, neat beard, glasses",
            "background": "a large world map with color-coded data", "show_name": "Deep Dive",
        },
    },
    "selfie": {
        "character": (
            "A {gender} content creator in their {age}s, {appearance}. "
            "Holding phone at selfie angle, slightly above eye level. "
        ),
        "setting": (
            "A cozy room: {background}. "
            "Natural window light, golden hour glow. iPhone selfie camera quality, "
            "slightly wide-angle distortion. {orientation_note}"
        ),
        "angles": {
            "selfie_straight": "Classic selfie, phone at arm's length. Playful expression. Face fills upper third.",
            "selfie_close": "Very close selfie, big expressive eyes. Eyebrows raised. Slight fish-eye.",
            "selfie_side": "Selfie from side angle, looking over shoulder. More room visible. One hand gesturing.",
            "selfie_low": "Phone held lower, looking down at camera. Power pose. Background bokeh above.",
        },
        "defaults": {
            "gender": "female", "age": "25", "appearance": "wavy hair, expressive eyes, cheeky smile, hoop earrings",
            "background": "exposed brick wall, fairy lights, messy bookshelf",
            "orientation_note": "Vertical 9:16 portrait orientation.",
        },
    },
    "documentary": {
        "character": (
            "A {gender} narrator in their {age}s, {appearance}. "
            "Standing or seated in a dramatic setting. Professional presence. "
        ),
        "setting": (
            "{background}. "
            "Cinematic lighting with dramatic shadows. "
            "Shot on RED camera, 4K, film grain, shallow DOF."
        ),
        "angles": {
            "medium_front": "Medium shot, slight low angle. Subject centered. Dramatic lighting.",
            "side_left": "Profile from left. Strong rim light. Contemplative pose.",
            "wide_establishing": "Wide establishing shot. Full environment visible. Subject smaller in frame.",
            "closeup_front": "Extreme close-up on face. Eyes sharp. Background fully blurred.",
            "over_shoulder": "Over-the-shoulder angle, looking at something off-screen. Mysterious.",
        },
        "defaults": {
            "gender": "male", "age": "50", "appearance": "weathered face, gray hair, piercing eyes",
            "background": "ancient ruins at golden hour, dramatic clouds",
        },
    },
    "explainer": {
        "character": (
            "A {gender} science communicator in their {age}s, {appearance}. "
            "Animated and enthusiastic. Using hand gestures. "
        ),
        "setting": (
            "{background}. "
            "Clean modern lighting. Slightly over-exposed for a bright, accessible feel. "
            "4K, sharp focus."
        ),
        "angles": {
            "medium_front": "Medium shot, straight-on. Clean background. Direct to camera.",
            "side_gesture": "Side angle, hands visible gesturing at invisible diagram.",
            "closeup_front": "Close-up, eyes wide with enthusiasm. Slight smile.",
            "wide_whiteboard": "Wider shot with whiteboard or screen visible behind. Teaching pose.",
        },
        "defaults": {
            "gender": "female", "age": "30", "appearance": "smart casual, confident stance, warm smile",
            "background": "a clean modern studio with subtle colored lighting",
        },
    },
}


# ---------------------------------------------------------------------------
# Shot list generator
# ---------------------------------------------------------------------------

def generate_shot_list(config: ProductionConfig, script_segments: list[str]) -> list[dict]:
    """
    Generate a shot list from script segments and config.

    Each shot = {clip_num, angle, is_continuation, prompt}
    """
    preset = STYLE_PRESETS.get(config.style, STYLE_PRESETS["podcast"])
    angle_names = list(preset["angles"].keys())

    # Select which angles to use based on num_perspectives
    selected_angles = angle_names[:min(config.num_perspectives, len(angle_names))]

    shots = []
    prev_angle = None

    for i, segment_text in enumerate(script_segments):
        clip_num = i + 1

        # Decide angle: cycle through selected angles, occasional continuation
        angle_idx = i % len(selected_angles)
        angle = selected_angles[angle_idx]

        # Make it a continuation if same angle as previous and it makes sense
        is_continuation = (angle == prev_angle and i > 0 and i % 3 == 0)

        # Build video prompt with audio cues
        angle_desc = preset["angles"][angle]
        prompt = (
            f"{angle_desc} "
            f"The host speaks to camera: '{segment_text}' "
            f"Natural delivery, {config.tone} tone. "
            f"Ambient room sound, subtle background atmosphere."
        )

        shots.append({
            "clip_num": clip_num,
            "angle": angle,
            "is_continuation": is_continuation,
            "prompt": prompt,
            "script_text": segment_text,
        })
        prev_angle = angle

    return shots


def generate_script_segments(config: ProductionConfig) -> list[str]:
    """
    Generate script segments from topic.
    Uses Gemini to write the script, or falls back to placeholder.
    """
    try:
        from google import genai
        from google.genai import types
        import os

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("No API key")

        client = genai.Client(api_key=api_key)

        system_prompt = (
            f"You are a script writer for a {config.style}-style video about '{config.topic}'. "
            f"Tone: {config.tone}. Language: {config.language}. "
            f"Write exactly {config.num_clips} short script segments, each 1-2 sentences. "
            f"Each segment should be spoken aloud in about {config.clip_duration} seconds. "
            f"The first segment is an intro, the last is a sign-off. "
            f"Output ONLY a JSON array of strings, no other text."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=system_prompt,
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        segments = json.loads(text)
        if isinstance(segments, list) and len(segments) >= 1:
            return segments[:config.num_clips]
    except Exception as e:
        print(f"    Script generation failed ({e}), using placeholders")

    # Fallback: placeholder segments
    segments = [f"Segment {i+1} about {config.topic}." for i in range(config.num_clips)]
    segments[0] = f"Welcome. Today we're talking about {config.topic}."
    segments[-1] = f"That's all about {config.topic}. Thanks for watching."
    return segments


# ---------------------------------------------------------------------------
# Producer class
# ---------------------------------------------------------------------------

class VideoProducer:
    """Orchestrates the full video production pipeline."""

    def __init__(self, config: ProductionConfig):
        self.config = config
        self.project_dir = Path(config.output_dir) / config.project_name
        self.frames_dir = self.project_dir / "frames"
        self.clips_dir = self.project_dir / "clips"
        self.log: dict = {
            "config": asdict(config),
            "run_started": None,
            "run_finished": None,
            "script_segments": [],
            "shots": [],
            "clips_generated": [],
            "clips_failed": [],
            "final_outputs": [],
        }

        # Ensure directories
        for d in [self.project_dir, self.frames_dir, self.clips_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_client(self):
        import os
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        return genai.Client(api_key=api_key)

    def _build_character_prompt(self) -> str:
        """Build the full character+setting image prompt."""
        preset = STYLE_PRESETS.get(self.config.style, STYLE_PRESETS["podcast"])
        defaults = preset.get("defaults", {})

        char = self.config.character_description or preset["character"].format(**defaults)
        setting = self.config.setting_description or preset["setting"].format(**defaults)

        return f"A photorealistic shot of {char}\n\n{setting}"

    def generate_angle_image(self, client, angle_key: str) -> Path:
        """Generate a start frame for a camera angle via Nano Banana."""
        from google.genai import types

        output_path = self.frames_dir / f"angle_{angle_key}.png"
        if output_path.exists():
            print(f"    [cached] {output_path.name}")
            return output_path

        preset = STYLE_PRESETS.get(self.config.style, STYLE_PRESETS["podcast"])
        angle_desc = preset["angles"].get(angle_key, "Medium shot, straight-on.")
        full_prompt = f"{self._build_character_prompt()}\n\n{angle_desc}"

        print(f"    Generating image: {angle_key}...")
        response = client.models.generate_content(
            model=self.config.model_image,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=self.config.aspect_ratio),
            ),
        )

        for part in response.parts:
            if part.inline_data:
                image = PILImage.open(BytesIO(part.inline_data.data))
                image.save(output_path)
                print(f"    Saved: {output_path.name} ({image.size[0]}x{image.size[1]})")
                self.log["clips_generated"].append({
                    "type": "image", "angle": angle_key,
                    "file": str(output_path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                return output_path

        print(f"    ERROR: No image for {angle_key}")
        self.log["clips_failed"].append({"type": "image", "angle": angle_key})
        raise RuntimeError(f"Image generation failed for angle {angle_key}")

    def extract_last_frame(self, video_path: Path, output_path: Path) -> Path:
        """Extract the last frame of a video clip."""
        if output_path.exists():
            return output_path

        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(video_path)],
            capture_output=True, text=True,
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
        seek = max(0, duration - 0.1)

        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(seek), "-i", str(video_path),
             "-frames:v", "1", "-q:v", "1", str(output_path)],
            capture_output=True, check=True,
        )
        return output_path

    def generate_clip(self, client, clip_num: int, start_frame: Path, prompt: str) -> Optional[Path]:
        """Generate one video clip via Veo 3.0."""
        from google.genai import types

        output_path = self.clips_dir / f"clip_{clip_num:02d}.mp4"
        if output_path.exists() and output_path.stat().st_size > 100_000:
            print(f"    [cached] {output_path.name}")
            return output_path

        image = types.Image.from_file(location=str(start_frame))

        print(f"    Submitting Veo request...")
        operation = client.models.generate_videos(
            model=self.config.model_video,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                aspect_ratio=self.config.aspect_ratio,
                resolution=self.config.resolution,
            ),
        )

        start = time.time()
        while not operation.done:
            elapsed = int(time.time() - start)
            if elapsed > self.config.veo_poll_timeout:
                print(f"    TIMEOUT after {elapsed}s")
                self.log["clips_failed"].append({
                    "type": "video", "clip": clip_num, "reason": "timeout",
                })
                return None
            print(f"    [{elapsed}s] Generating...")
            time.sleep(self.config.poll_interval)
            operation = client.operations.get(operation)

        elapsed = int(time.time() - start)

        if not operation.response or not operation.response.generated_videos:
            self.log["clips_failed"].append({
                "type": "video", "clip": clip_num, "reason": "no_response",
            })
            return None

        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save(str(output_path))

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"    Done in {elapsed}s ({size_mb:.1f} MB)")

        self.log["clips_generated"].append({
            "type": "video", "clip": clip_num,
            "file": str(output_path),
            "size_mb": round(size_mb, 1),
            "generation_time_s": elapsed,
            "prompt_preview": prompt[:150],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return output_path

    def concatenate(self, clip_paths: list[Path]) -> Path:
        """Concatenate clips with ffmpeg."""
        concat_file = self.project_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.resolve()}'\n")

        output = self.project_dir / f"{self.config.project_name}_FINAL.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file),
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart",
             str(output)],
            capture_output=True, check=True,
        )
        return output

    def mix_music(self, video_path: Path) -> Optional[Path]:
        """Mix background music into the final video."""
        music = Path(self.config.background_music_path)
        if not music.exists():
            print(f"    No music file at {music}, skipping")
            return None

        output = video_path.with_name(
            video_path.stem + "_music" + video_path.suffix
        )
        vol = self.config.music_volume

        try:
            subprocess.run(
                ["ffmpeg", "-y",
                 "-i", str(video_path), "-i", str(music),
                 "-filter_complex",
                 f"[0:a]volume=1.0[voice];[1:a]volume={vol}[bg];"
                 f"[voice][bg]amix=inputs=2:duration=shortest[out]",
                 "-map", "0:v", "-map", "[out]",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-movflags", "+faststart",
                 str(output)],
                capture_output=True, check=True,
            )
            return output
        except subprocess.CalledProcessError:
            print("    WARNING: Music mixing failed")
            return None

    def write_log(self) -> Path:
        """Write the production log JSON."""
        log_path = self.project_dir / "production_log.json"
        with open(log_path, "w") as f:
            json.dump(self.log, f, indent=2, ensure_ascii=False)
        return log_path

    def produce(self) -> ProductionResult:
        """Run the full production pipeline."""
        result = ProductionResult()
        self.log["run_started"] = datetime.now(timezone.utc).isoformat()

        client = self._get_client()
        num_clips = self.config.num_clips

        print("=" * 60)
        print(f"  VIDEO PRODUCTION: {self.config.topic}")
        print(f"  {num_clips} clips × {self.config.clip_duration}s = "
              f"~{self.config.duration_seconds}s")
        print(f"  Style: {self.config.style} | Perspectives: {self.config.num_perspectives}")
        print("=" * 60)

        # Step 1: Generate script
        print("\n--- Step 1: Script generation ---")
        segments = generate_script_segments(self.config)
        self.log["script_segments"] = segments
        for i, seg in enumerate(segments):
            print(f"  [{i+1:02d}] {seg[:80]}...")

        # Step 2: Build shot list
        print("\n--- Step 2: Shot list ---")
        shots = generate_shot_list(self.config, segments)
        self.log["shots"] = shots

        # Step 3: Generate angle images
        print("\n--- Step 3: Angle images (Nano Banana) ---")
        unique_angles = {s["angle"] for s in shots if not s["is_continuation"]}
        for angle in sorted(unique_angles):
            self.generate_angle_image(client, angle)

        # Step 4: Generate clips
        print("\n--- Step 4: Video clips (Veo 3.0) ---")
        clip_paths: list[Path] = []
        prev_clip: Optional[Path] = None

        for shot in shots:
            cn = shot["clip_num"]
            print(f"\n  Clip {cn:02d}/{num_clips} — {shot['angle']}"
                  + (" (cont)" if shot["is_continuation"] else ""))

            if shot["is_continuation"] and prev_clip and prev_clip.exists():
                frame = self.frames_dir / f"lastframe_{cn - 1:02d}.png"
                self.extract_last_frame(prev_clip, frame)
            else:
                frame = self.frames_dir / f"angle_{shot['angle']}.png"

            clip = self.generate_clip(client, cn, frame, shot["prompt"])
            if clip:
                clip_paths.append(clip)
                prev_clip = clip
            else:
                print(f"    SKIPPING clip {cn}")

        # Step 5: Concatenate
        print(f"\n--- Step 5: Concatenating {len(clip_paths)} clips ---")
        final = self.concatenate(clip_paths)
        self.log["final_outputs"].append(str(final.resolve()))
        result.final_video_path = str(final.resolve())

        # Step 6: Music
        if self.config.background_music_path:
            print("\n--- Step 6: Background music ---")
            music_result = self.mix_music(final)
            if music_result:
                self.log["final_outputs"].append(str(music_result.resolve()))
                result.final_video_with_music_path = str(music_result.resolve())

        # Finalize
        self.log["run_finished"] = datetime.now(timezone.utc).isoformat()

        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration,size",
             "-of", "json", str(final)],
            capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)["format"]
        result.duration_seconds = float(info["duration"])
        result.num_clips_generated = len(clip_paths)
        result.num_clips_failed = len(self.log["clips_failed"])
        result.clips_dir = str(self.clips_dir.resolve())
        result.frames_dir = str(self.frames_dir.resolve())

        log_path = self.write_log()
        result.log_path = str(log_path.resolve())
        result.success = True

        # Summary
        dur = result.duration_seconds
        size_mb = int(info["size"]) / (1024 * 1024)
        print(f"\n{'='*60}")
        print(f"  DONE")
        print(f"{'='*60}")
        print(f"  Video:    {result.final_video_path}")
        if result.final_video_with_music_path:
            print(f"  + Music:  {result.final_video_with_music_path}")
        print(f"  Duration: {int(dur//60)}:{int(dur%60):02d}")
        print(f"  Size:     {size_mb:.1f} MB")
        print(f"  Log:      {result.log_path}")

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI Video Production Pipeline (Nano Banana + Veo 3.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick 30-second podcast
  python video_producer.py --topic "Why cats purr" --duration 30 --style podcast

  # 2-minute documentary, 5 angles
  python video_producer.py --topic "The history of Rome" --duration 120 --perspectives 5 --style documentary

  # 1-minute Instagram reel, portrait
  python video_producer.py --topic "Fun facts about Japan" --duration 60 --style selfie --orientation portrait --tone funny

  # From a config file
  python video_producer.py --config my_production.json
        """,
    )

    parser.add_argument("--config", type=str, help="JSON config file path")
    parser.add_argument("--topic", type=str, help="Video topic")
    parser.add_argument("--duration", type=int, default=60, help="Target duration in seconds (default: 60)")
    parser.add_argument("--perspectives", type=int, default=3, help="Number of camera angles (default: 3)")
    parser.add_argument("--style", type=str, default="podcast",
                       choices=["podcast", "selfie", "documentary", "explainer"],
                       help="Visual style preset (default: podcast)")
    parser.add_argument("--tone", type=str, default="serious",
                       choices=["serious", "funny", "dramatic", "casual"],
                       help="Tone of delivery (default: serious)")
    parser.add_argument("--orientation", type=str, default="landscape",
                       choices=["landscape", "portrait"],
                       help="Video orientation (default: landscape)")
    parser.add_argument("--music", type=str, default="", help="Path to background music MP3")
    parser.add_argument("--music-volume", type=float, default=0.12, help="Music volume 0-1 (default: 0.12)")
    parser.add_argument("--output", type=str, default="./output", help="Output directory")
    parser.add_argument("--character", type=str, default="", help="Custom character description")
    parser.add_argument("--language", type=str, default="English", help="Language for script")
    parser.add_argument("--resolution", type=str, default="720p", choices=["720p", "1080p"])

    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config_data = json.load(f)
        config = ProductionConfig(**config_data)
    elif args.topic:
        config = ProductionConfig(
            topic=args.topic,
            duration_seconds=args.duration,
            num_perspectives=args.perspectives,
            style=args.style,
            tone=args.tone,
            orientation=args.orientation,
            background_music_path=args.music,
            music_volume=args.music_volume,
            output_dir=args.output,
            character_description=args.character,
            language=args.language,
            resolution=args.resolution,
        )
    else:
        parser.error("Either --config or --topic is required")

    producer = VideoProducer(config)
    result = producer.produce()

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
