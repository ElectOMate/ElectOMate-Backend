#!/usr/bin/env python3
"""
Full Pipeline: Nano Banana → Kling 3.0 + Veo 3.1

1. Generate podcast start frame with Nano Banana (Gemini image gen)
2. Feed that frame into Kling 3.0 (image-to-video + voice)
3. Feed that frame into Veo 3.1 (image-to-video + voice)
4. Print all output paths and URLs

Usage:
    python run_all.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run_script(name: str) -> bool:
    """Run a test script and return True if successful."""
    script = SCRIPTS_DIR / name
    print(f"\n{'='*60}")
    print(f"  Running: {name}")
    print(f"{'='*60}\n")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(SCRIPTS_DIR),
    )
    return result.returncode == 0


def main() -> None:
    print("=" * 60)
    print("  VIDEO GENERATION PIPELINE")
    print("  Theme: Democracy Explorer Podcast")
    print("=" * 60)

    # Step 1: Generate start frame
    if not run_script("test_nano_banana.py"):
        print("\nFAILED: Nano Banana image generation. Aborting pipeline.")
        sys.exit(1)

    # Step 2 & 3: Run both video generators
    results = {}
    for script in ["test_kling.py", "test_veo.py"]:
        success = run_script(script)
        results[script] = success

    # Summary
    print(f"\n{'='*60}")
    print("  PIPELINE RESULTS")
    print(f"{'='*60}")
    print(f"  Nano Banana (image):  OK")
    for script, ok in results.items():
        label = script.replace("test_", "").replace(".py", "").upper()
        status = "OK" if ok else "FAILED"
        print(f"  {label} (video):  {status}")

    output_dir = SCRIPTS_DIR / "output"
    print(f"\n  Output directory: {output_dir.resolve()}")
    for f in sorted(output_dir.iterdir()):
        size = f.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / (1024*1024):.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.0f} KB"
        else:
            size_str = f"{size} B"
        print(f"    {f.name} ({size_str})")


if __name__ == "__main__":
    main()
