"""Post-processing: ffmpeg overlays, captions, B-roll compositing, source cards."""

import json
import subprocess
from pathlib import Path


def extract_last_frame(video_path: str, output_path: str) -> str:
    """Extract the last frame of a video."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(output_path).exists():
        return output_path

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", video_path],
        capture_output=True, text=True,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    seek = max(0, duration - 0.1)

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(seek), "-i", video_path,
         "-frames:v", "1", "-q:v", "1", output_path],
        capture_output=True, check=True,
    )
    return output_path


def add_source_overlay(
    video_path: str,
    source_image_path: str,
    source_label: str,
    output_path: str,
    position: str = "bottom_right",
    duration: float = 5.0,
    start_time: float = 0.0,
) -> str:
    """Overlay a source card image on top of a video clip for a given duration."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Position mapping
    positions = {
        "bottom_right": "W-w-40:H-h-40",
        "bottom_left": "40:H-h-40",
        "top_right": "W-w-40:40",
        "top_left": "40:40",
    }
    overlay_pos = positions.get(position, positions["bottom_right"])

    # Scale overlay to 30% of video width
    filter_complex = (
        f"[1:v]scale=iw*0.3:-1[ovr];"
        f"[0:v][ovr]overlay={overlay_pos}:"
        f"enable='between(t,{start_time},{start_time + duration})'[outv]"
    )

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-i", source_image_path,
         "-filter_complex", filter_complex,
         "-map", "[outv]", "-map", "0:a?",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "copy",
         output_path],
        capture_output=True, check=True,
    )
    return output_path


def add_text_overlay(
    video_path: str,
    text: str,
    output_path: str,
    position: str = "bottom_center",
    font_size: int = 24,
    start_time: float = 0.0,
    duration: float = 5.0,
    bg_opacity: float = 0.6,
) -> str:
    """Add text overlay (for source labels, captions, etc)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Escape special chars for ffmpeg drawtext
    escaped = text.replace("'", "'\\''").replace(":", "\\:")

    positions = {
        "bottom_center": "x=(w-text_w)/2:y=h-th-60",
        "top_center": "x=(w-text_w)/2:y=40",
        "bottom_left": "x=40:y=h-th-60",
    }
    pos = positions.get(position, positions["bottom_center"])

    drawtext = (
        f"drawtext=text='{escaped}':{pos}:"
        f"fontsize={font_size}:fontcolor=white:"
        f"box=1:boxcolor=black@{bg_opacity}:boxborderw=10:"
        f"enable='between(t,{start_time},{start_time + duration})'"
    )

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", drawtext,
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "copy",
         output_path],
        capture_output=True, check=True,
    )
    return output_path


def generate_srt(segments: list[dict], clip_duration: float = 8.0) -> str:
    """Generate SRT subtitle content from script segments with timing-aware text splits."""
    lines = []
    subtitle_index = 1

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue

        clip_start = i * clip_duration
        clip_end = clip_start + clip_duration

        # Split text into phrases by punctuation or max length
        phrases = _split_text_into_phrases(text, max_words=15)

        if not phrases:
            continue

        # Distribute phrases evenly across clip duration
        phrase_duration = clip_duration / len(phrases)

        for j, phrase in enumerate(phrases):
            phrase_start = clip_start + (j * phrase_duration)
            phrase_end = min(phrase_start + phrase_duration, clip_end)

            lines.append(str(subtitle_index))
            lines.append(f"{_format_srt_time(phrase_start)} --> {_format_srt_time(phrase_end)}")
            lines.append(phrase.strip())
            lines.append("")

            subtitle_index += 1

    return "\n".join(lines)


def _split_text_into_phrases(text: str, max_words: int = 15) -> list[str]:
    """Split text into subtitle-friendly phrases by punctuation and length."""
    import re

    # First split by sentence-ending punctuation
    sentences = re.split(r'([.!?]+\s+)', text)

    phrases = []
    current_phrase = ""

    for part in sentences:
        if not part.strip():
            continue

        # If it's punctuation, add to current phrase
        if re.match(r'^[.!?]+\s*$', part):
            current_phrase += part
            continue

        # Check if adding this would exceed max words
        test_phrase = (current_phrase + " " + part).strip()
        word_count = len(test_phrase.split())

        if word_count > max_words and current_phrase:
            # Flush current phrase
            phrases.append(current_phrase.strip())
            current_phrase = part
        else:
            current_phrase = test_phrase

    if current_phrase.strip():
        phrases.append(current_phrase.strip())

    # If phrases are still too long, split by commas or clauses
    final_phrases = []
    for phrase in phrases:
        if len(phrase.split()) > max_words:
            # Split by comma
            parts = phrase.split(',')
            for part in parts:
                if part.strip():
                    final_phrases.append(part.strip())
        else:
            final_phrases.append(phrase)

    return final_phrases


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def burn_captions(video_path: str, srt_path: str, output_path: str) -> str:
    """Burn SRT captions into video by overlaying caption images per segment."""
    from PIL import Image, ImageDraw, ImageFont

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Parse SRT
    with open(srt_path) as f:
        srt_content = f.read()

    segments = []
    blocks = srt_content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            time_line = lines[1]
            text = " ".join(lines[2:])
            start_str, end_str = time_line.split(" --> ")
            segments.append({"start": _srt_to_seconds(start_str), "end": _srt_to_seconds(end_str), "text": text})

    if not segments:
        # No captions to burn, just copy
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    # Get video dimensions
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
         "-of", "json", video_path],
        capture_output=True, text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    vid_w = streams[0]["width"]
    vid_h = streams[0]["height"]

    # Create caption overlay images
    caption_dir = Path(output_path).parent / "caption_overlays"
    caption_dir.mkdir(exist_ok=True)

    filter_parts = []
    inputs = ["-i", video_path]

    for i, seg in enumerate(segments):
        # Create transparent-ish caption image
        cap_img = Image.new("RGBA", (vid_w, 80), (0, 0, 0, 160))
        draw = ImageDraw.Draw(cap_img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # Center text
        text = seg["text"]
        if len(text) > 60:
            text = text[:57] + "..."
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (vid_w - tw) // 2
        draw.text((x, 20), text, fill=(255, 255, 255, 255), font=font)

        cap_path = str(caption_dir / f"cap_{i:02d}.png")
        cap_img.save(cap_path)

        inputs.extend(["-i", cap_path])
        inp_idx = i + 1
        y_pos = vid_h - 100
        prev = f"[tmp{i}]" if i > 0 else "[0:v]"
        out = f"[tmp{i+1}]" if i < len(segments) - 1 else "[outv]"
        filter_parts.append(
            f"{prev}[{inp_idx}:v]overlay=0:{y_pos}:"
            f"enable='between(t,{seg['start']},{seg['end']})'{out}"
        )

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        output_path,
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _srt_to_seconds(ts: str) -> float:
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def concatenate_clips(clip_paths: list[str], output_path: str) -> str:
    """Concatenate clips with ffmpeg."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    concat_file = str(Path(output_path).parent / "concat_list.txt")

    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{Path(clip).resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", concat_file,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         output_path],
        capture_output=True, check=True,
    )
    return output_path


def mix_background_music(
    video_path: str, music_path: str, output_path: str, music_volume: float = 0.12
) -> str:
    """Mix background music into video at low volume."""
    if not Path(music_path).exists():
        return video_path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["ffmpeg", "-y",
         "-i", video_path, "-i", music_path,
         "-filter_complex",
         f"[0:a]volume=1.0[voice];[1:a]volume={music_volume}[bg];"
         f"[voice][bg]amix=inputs=2:duration=shortest[out]",
         "-map", "0:v", "-map", "[out]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart",
         output_path],
        capture_output=True, check=True,
    )
    return output_path


def create_split_screen(
    main_video: str,
    side_image: str,
    output_path: str,
    side_position: str = "right",
    split_ratio: float = 0.6,
) -> str:
    """Create a split-screen: main video on one side, image/content on the other."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Get video dimensions
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "stream=width,height",
         "-of", "json", main_video],
        capture_output=True, text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    w = streams[0]["width"]
    h = streams[0]["height"]

    main_w = int(w * split_ratio)
    side_w = w - main_w

    if side_position == "right":
        filter_complex = (
            f"[0:v]scale={main_w}:{h}[main];"
            f"[1:v]scale={side_w}:{h}[side];"
            f"[main][side]hstack=inputs=2[outv]"
        )
    else:
        filter_complex = (
            f"[1:v]scale={side_w}:{h}[side];"
            f"[0:v]scale={main_w}:{h}[main];"
            f"[side][main]hstack=inputs=2[outv]"
        )

    subprocess.run(
        ["ffmpeg", "-y", "-i", main_video, "-i", side_image,
         "-filter_complex", filter_complex,
         "-map", "[outv]", "-map", "0:a?",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-c:a", "copy", "-t", "8",
         output_path],
        capture_output=True, check=True,
    )
    return output_path
