"""
Video Production Agent — orchestrates the full pipeline.

This module ties together research, video generation, and post-processing
into a single callable pipeline. It can be invoked directly from Python
or via the FastAPI backend.
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from video_agent dir or parent
for env_path in [Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break

from agent.tools import research, video_gen, post_process


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class VideoAgentConfig:
    """Full configuration for a video production run."""
    # Content
    topic: str = "Democracy in Hungary"
    language: str = "English"
    tone: str = "serious"  # serious | funny | dramatic | casual

    # Video params
    duration_seconds: int = 60
    clip_duration: int = 8
    num_perspectives: int = 3
    orientation: str = "landscape"  # landscape | portrait
    resolution: str = "720p"

    # Character
    character_description: str = ""
    character_gender: str = "male"
    character_age: str = "40"

    # Sources
    search_sources: list[str] = field(default_factory=lambda: ["web"])  # web, knowledge_base, wikipedia
    manifesto_dir: str = ""  # Path to local manifesto PDFs

    # Music
    background_music_path: str = ""
    music_volume: float = 0.12

    # Output
    output_dir: str = "./output"
    project_name: str = ""

    # Captions
    generate_captions: bool = True

    def __post_init__(self):
        if not self.project_name:
            slug = self.topic.lower().replace(" ", "_")[:30]
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            self.project_name = f"{slug}_{ts}"

    @property
    def num_clips(self) -> int:
        return max(1, self.duration_seconds // self.clip_duration)

    @property
    def aspect_ratio(self) -> str:
        return "9:16" if self.orientation == "portrait" else "16:9"


@dataclass
class ProductionResult:
    final_video: str = ""
    final_video_captioned: str = ""
    final_video_music: str = ""
    metadata_path: str = ""
    sources: list[dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    success: bool = False
    error: str = ""


# ---------------------------------------------------------------------------
# Character + Angle Presets
# ---------------------------------------------------------------------------

ANGLES = {
    "medium_front": (
        "Medium shot, straight-on, waist-up. Professional podcast setting. "
        "Looking directly at camera. Centered composition."
    ),
    "side_left": (
        "Three-quarter shot from 45° left. One microphone prominent. "
        "Rim light on right side of face. Off-center composition."
    ),
    "side_right": (
        "Three-quarter shot from 45° right. Key light models left side. "
        "One microphone in foreground right."
    ),
    "closeup_front": (
        "Tight close-up, head and shoulders. Very shallow depth of field. "
        "Eyes sharp. Intimate, intense framing."
    ),
    "wide": (
        "Wide establishing shot showing full desk, microphones, and background. "
        "Subject centered but smaller in frame."
    ),
}


def _build_character_prompt(config: VideoAgentConfig, angle_key: str) -> str:
    if config.character_description:
        char = config.character_description
    else:
        char = (
            f"A {config.character_gender} political commentator in their {config.character_age}s, "
            f"with a professional appearance, glasses, and smart-casual attire. "
            f"Seated at a dark walnut podcast desk with two boom-arm microphones. "
        )

    setting = (
        "Behind them is a large wall-mounted screen or world map with political data. "
        "Warm tungsten studio lighting from above-left. A desk label reads 'Deep Dive'. "
        "Cinematic, 4K quality, shallow depth of field, professional YouTube studio."
    )

    angle_desc = ANGLES.get(angle_key, ANGLES["medium_front"])
    return f"A photorealistic shot of {char}\n\n{setting}\n\n{angle_desc}"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class VideoProducerAgent:
    """Orchestrates the full video production pipeline."""

    def __init__(self, config: VideoAgentConfig, progress_callback=None):
        self.config = config
        self.progress = progress_callback or (lambda step, msg: print(f"  [{step}] {msg}"))
        self.project_dir = Path(config.output_dir) / config.project_name
        self.frames_dir = self.project_dir / "frames"
        self.clips_dir = self.project_dir / "clips"
        self.sources_dir = self.project_dir / "sources"

        for d in [self.project_dir, self.frames_dir, self.clips_dir, self.sources_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.metadata = {
            "config": asdict(config),
            "run_started": None,
            "run_finished": None,
            "script": [],
            "sources": [],
            "clips": [],
            "timestamps": [],
            "final_outputs": [],
        }

    async def produce(self) -> ProductionResult:
        result = ProductionResult()
        self.metadata["run_started"] = datetime.now(timezone.utc).isoformat()

        try:
            self.progress("init", f"Starting production: {self.config.topic}")

            # Step 1: Research
            self.progress("research", "Researching topic...")
            research_data = await self._research()

            # Step 2: Generate script
            self.progress("script", "Generating script...")
            script = self._generate_script()
            self.metadata["script"] = script

            # Step 3: Collect sources
            self.progress("sources", "Collecting source materials...")
            sources = self._collect_sources(script, research_data)
            self.metadata["sources"] = sources
            result.sources = sources

            # Step 4: Generate angle images
            self.progress("images", "Generating camera angle images...")
            angle_images = self._generate_angle_images(script)

            # Step 5: Generate video clips
            self.progress("video", "Generating video clips...")
            clip_paths = self._generate_clips(script, angle_images)

            # Step 6: Add source overlays
            self.progress("overlays", "Adding source overlays...")
            clip_paths = self._add_source_overlays(clip_paths, script, sources)

            # Step 7: Concatenate
            self.progress("concat", "Concatenating clips...")
            final = post_process.concatenate_clips(
                clip_paths,
                str(self.project_dir / f"{self.config.project_name}_FINAL.mp4"),
            )
            result.final_video = final
            self.metadata["final_outputs"].append(final)

            # Step 8: Captions
            if self.config.generate_captions:
                self.progress("captions", "Adding captions...")
                result.final_video_captioned = self._add_captions(final, script)
                self.metadata["final_outputs"].append(result.final_video_captioned)

            # Step 9: Background music
            if self.config.background_music_path:
                self.progress("music", "Mixing background music...")
                music_out = str(self.project_dir / f"{self.config.project_name}_FINAL_music.mp4")
                result.final_video_music = post_process.mix_background_music(
                    final, self.config.background_music_path, music_out,
                    self.config.music_volume,
                )
                self.metadata["final_outputs"].append(result.final_video_music)

            # Step 10: Build timestamp log
            self.progress("metadata", "Building metadata...")
            self._build_timestamps(script, sources)

            # Finalize
            self.metadata["run_finished"] = datetime.now(timezone.utc).isoformat()
            result.metadata_path = self._write_metadata()
            result.success = True

            # Probe duration
            import subprocess
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "json", final],
                capture_output=True, text=True,
            )
            result.duration_seconds = float(json.loads(probe.stdout)["format"]["duration"])

            self.progress("done", f"Production complete: {final}")

        except Exception as e:
            result.error = str(e)
            self.metadata["error"] = str(e)
            self.metadata["run_finished"] = datetime.now(timezone.utc).isoformat()
            self._write_metadata()
            self.progress("error", f"Failed: {e}")
            import traceback
            traceback.print_exc()

        return result

    # --- Internal steps ---

    async def _research(self) -> dict:
        data = {}
        if "web" in self.config.search_sources:
            data = await research.web_search(
                f"{self.config.topic} facts statistics sources",
                str(self.project_dir),
            )
        if "knowledge_base" in self.config.search_sources and self.config.manifesto_dir:
            kb_results = research.search_knowledge_base(
                self.config.topic, self.config.manifesto_dir,
            )
            data["knowledge_base_results"] = kb_results
        return data

    def _generate_script(self) -> list[dict]:
        return video_gen.generate_script(
            self.config.topic,
            self.config.num_clips,
            self.config.tone,
            self.config.language,
        )

    def _collect_sources(self, script: list[dict], research_data: dict) -> list[dict]:
        sources = []
        source_idx = 1

        # Sources from research
        for src in research_data.get("sources", []):
            screenshot_path = str(self.sources_dir / f"source_{source_idx:02d}.png")
            research.take_screenshot(src.get("url", ""), screenshot_path)
            sources.append({
                "index": source_idx,
                "title": src.get("title", src.get("url", f"Source {source_idx}")),
                "url": src.get("url", ""),
                "description": src.get("description", ""),
                "screenshot": screenshot_path,
                "type": "web",
            })
            source_idx += 1

        # Sources from script hints
        for seg in script:
            if seg.get("needs_source") and seg.get("source_hint"):
                hint = seg["source_hint"]
                screenshot_path = str(self.sources_dir / f"source_{source_idx:02d}.png")
                research._generate_source_card(hint, screenshot_path)
                sources.append({
                    "index": source_idx,
                    "title": hint,
                    "url": "",
                    "description": f"Source for: {seg.get('text', '')[:80]}",
                    "screenshot": screenshot_path,
                    "type": "script_citation",
                })
                source_idx += 1

        return sources

    def _generate_angle_images(self, script: list[dict]) -> dict[str, str]:
        angle_images = {}
        angles_needed = set()

        for seg in script:
            angle = seg.get("camera_angle", "medium_front")
            if angle not in ANGLES:
                angle = "medium_front"
            angles_needed.add(angle)

        # Limit to num_perspectives
        angle_list = list(ANGLES.keys())
        selected = [a for a in angle_list if a in angles_needed][:self.config.num_perspectives]
        if not selected:
            selected = angle_list[:self.config.num_perspectives]

        for angle in selected:
            prompt = _build_character_prompt(self.config, angle)
            output = str(self.frames_dir / f"angle_{angle}.png")
            self.progress("images", f"  Generating {angle}...")
            video_gen.generate_image(prompt, output, self.config.aspect_ratio)
            angle_images[angle] = output

        return angle_images

    def _generate_clips(self, script: list[dict], angle_images: dict[str, str]) -> list[str]:
        clip_paths = []
        prev_clip = None
        available_angles = list(angle_images.keys())

        for i, seg in enumerate(script):
            clip_num = i + 1
            angle = seg.get("camera_angle", "medium_front")

            # Fall back to available angle
            if angle not in angle_images:
                angle = available_angles[i % len(available_angles)]

            self.progress("video", f"  Clip {clip_num}/{len(script)} — {angle}")

            # Determine start frame
            if prev_clip and angle == script[i - 1].get("camera_angle") and i % 3 == 0:
                # Continuation: use last frame
                frame_path = str(self.frames_dir / f"lastframe_{clip_num - 1:02d}.png")
                post_process.extract_last_frame(prev_clip, frame_path)
            else:
                frame_path = angle_images[angle]

            # Build video prompt
            text = seg.get("text", "")
            video_prompt = (
                f"The host speaks to camera and says: '{text}' "
                f"Natural delivery, {self.config.tone} tone. "
                f"Professional studio setting. Ambient room sound."
            )

            output = str(self.clips_dir / f"clip_{clip_num:02d}.mp4")
            try:
                video_gen.generate_video_clip(
                    frame_path, video_prompt, output,
                    self.config.aspect_ratio, self.config.resolution,
                )
                clip_paths.append(output)
                prev_clip = output

                self.metadata["clips"].append({
                    "clip_num": clip_num,
                    "angle": angle,
                    "text": text,
                    "file": output,
                })
            except Exception as e:
                self.progress("video", f"  FAILED clip {clip_num}: {e}")

        return clip_paths

    def _add_source_overlays(
        self, clip_paths: list[str], script: list[dict], sources: list[dict]
    ) -> list[str]:
        """Add source overlay images to clips that need citations."""
        updated_paths = []
        source_queue = list(sources)
        source_idx = 0

        for i, clip in enumerate(clip_paths):
            seg = script[i] if i < len(script) else {}

            if seg.get("needs_source") and source_idx < len(source_queue):
                src = source_queue[source_idx]
                overlay_output = clip.replace(".mp4", "_sourced.mp4")

                try:
                    # Add source screenshot overlay
                    if Path(src["screenshot"]).exists():
                        post_process.add_source_overlay(
                            clip, src["screenshot"],
                            f"Source {src['index']}",
                            overlay_output,
                            position="bottom_right",
                            duration=5.0,
                            start_time=3.0,  # Show source 3s into clip
                        )
                        updated_paths.append(overlay_output)
                    else:
                        updated_paths.append(clip)

                    source_idx += 1
                except Exception:
                    updated_paths.append(clip)
            else:
                updated_paths.append(clip)

        return updated_paths

    def _add_captions(self, video_path: str, script: list[dict]) -> str:
        srt_content = post_process.generate_srt(script, self.config.clip_duration)
        srt_path = str(self.project_dir / "captions.srt")
        with open(srt_path, "w") as f:
            f.write(srt_content)

        captioned_output = video_path.replace("_FINAL.mp4", "_FINAL_captioned.mp4")
        try:
            return post_process.burn_captions(video_path, srt_path, captioned_output)
        except Exception as e:
            self.progress("captions", f"  Caption burn failed: {e}")
            return ""

    def _build_timestamps(self, script: list[dict], sources: list[dict]) -> None:
        timestamps = []
        source_idx = 0

        for i, seg in enumerate(script):
            start_s = i * self.config.clip_duration
            end_s = start_s + self.config.clip_duration
            entry = {
                "start": f"{int(start_s // 60)}:{int(start_s % 60):02d}",
                "end": f"{int(end_s // 60)}:{int(end_s % 60):02d}",
                "text": seg.get("text", ""),
                "camera_angle": seg.get("camera_angle", ""),
            }

            if seg.get("needs_source") and source_idx < len(sources):
                src = sources[source_idx]
                entry["source"] = {
                    "index": src["index"],
                    "title": src["title"],
                    "url": src.get("url", ""),
                    "shown_at": f"{int((start_s + 3) // 60)}:{int((start_s + 3) % 60):02d}",
                }
                source_idx += 1

            timestamps.append(entry)

        self.metadata["timestamps"] = timestamps

    def _write_metadata(self) -> str:
        path = str(self.project_dir / "production_metadata.json")
        with open(path, "w") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        return path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def run_production(config: VideoAgentConfig) -> ProductionResult:
    agent = VideoProducerAgent(config)
    return await agent.produce()


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Video Production Agent")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--perspectives", type=int, default=3)
    parser.add_argument("--tone", default="serious")
    parser.add_argument("--language", default="English")
    parser.add_argument("--orientation", default="landscape")
    parser.add_argument("--output", default="./output")
    parser.add_argument("--music", default="")
    parser.add_argument("--captions", action="store_true", default=True)
    args = parser.parse_args()

    config = VideoAgentConfig(
        topic=args.topic,
        duration_seconds=args.duration,
        num_perspectives=args.perspectives,
        tone=args.tone,
        language=args.language,
        orientation=args.orientation,
        output_dir=args.output,
        background_music_path=args.music,
        generate_captions=args.captions,
    )

    result = asyncio.run(run_production(config))
    if result.success:
        print(f"\nFinal video: {result.final_video}")
        print(f"Metadata: {result.metadata_path}")
        if result.final_video_captioned:
            print(f"Captioned: {result.final_video_captioned}")
    else:
        print(f"\nFailed: {result.error}")
        sys.exit(1)
