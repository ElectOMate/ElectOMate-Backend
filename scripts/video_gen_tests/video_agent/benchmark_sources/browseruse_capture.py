"""Enhanced screenshot capture with intelligent content detection."""

import os
import asyncio
import subprocess
from pathlib import Path
from PIL import Image
import time

async def capture_with_intelligent_fallback(url: str, output_path: str) -> dict:
    """
    Capture screenshot with intelligent scrolling to find interesting content.

    Tries multiple scroll positions and selects the best one based on:
    - Content diversity (color variety)
    - File size (indicates text/images loaded)
    - Visual analysis

    Returns dict with:
    - success: bool
    - screenshot_path: str
    - content_score: float (0-1)
    - attempts: int
    - description: str
    """
    print(f"    🔍 Intelligent screenshot capture for {url[:50]}...")

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]
    chrome = next((p for p in chrome_paths if Path(p).exists()), None)

    if not chrome:
        return {
            "success": False,
            "screenshot_path": "",
            "content_score": 0.0,
            "attempts": 0,
            "description": "Chrome not found"
        }

    # Try multiple strategies to capture interesting content
    strategies = [
        {"scroll": 0, "wait": 3, "desc": "Landing page with content loaded"},
        {"scroll": 800, "wait": 2, "desc": "First scroll - main content"},
        {"scroll": 1600, "wait": 2, "desc": "Second scroll - deeper content"},
        {"scroll": 400, "wait": 2, "desc": "Shallow scroll - article start"},
    ]

    best_screenshot = None
    best_score = 0.0
    best_description = ""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    for idx, strategy in enumerate(strategies):
        temp_path = str(Path(output_path).parent / f"temp_{idx}.png")

        try:
            print(f"    → Strategy {idx+1}/4: {strategy['desc']}")

            # Build Chrome command with JavaScript to scroll
            cmd = [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--screenshot={temp_path}",
                "--window-size=1920,1200",
                "--hide-scrollbars",
                "--disable-dev-shm-usage",
                url
            ]

            # Run Chrome
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait for page to load
            await asyncio.sleep(strategy["wait"])

            # If scroll needed, take another screenshot with JavaScript
            if strategy["scroll"] > 0:
                # Kill first process
                process.kill()

                # Take screenshot with scroll
                scroll_cmd = cmd + [
                    "--virtual-time-budget=5000",
                    f"--run-all-compositor-stages-before-draw"
                ]

                subprocess.run(
                    scroll_cmd,
                    capture_output=True,
                    timeout=15
                )
            else:
                # Wait for process to finish
                process.wait(timeout=15)

            # Analyze captured screenshot
            if Path(temp_path).exists():
                score, analysis = _analyze_screenshot_quality(temp_path)

                print(f"      Quality score: {score:.2f} - {analysis}")

                if score > best_score:
                    best_score = score
                    best_screenshot = temp_path
                    best_description = f"{strategy['desc']} - {analysis}"

                # If we found excellent content, stop trying
                if score > 0.85:
                    print(f"      ✓ Excellent content found!")
                    break

        except subprocess.TimeoutExpired:
            print(f"      ✗ Timeout")
            continue
        except Exception as e:
            print(f"      ✗ Error: {e}")
            continue

    # Use best screenshot
    if best_screenshot and Path(best_screenshot).exists():
        import shutil
        shutil.copy(best_screenshot, output_path)

        # Clean up temp files
        for temp_file in Path(output_path).parent.glob("temp_*.png"):
            try:
                temp_file.unlink()
            except:
                pass

        print(f"    ✓ Best capture: score {best_score:.2f}")

        return {
            "success": True,
            "screenshot_path": output_path,
            "content_score": best_score,
            "attempts": len(strategies),
            "description": best_description
        }

    return {
        "success": False,
        "screenshot_path": "",
        "content_score": 0.0,
        "attempts": len(strategies),
        "description": "All capture strategies failed"
    }


def _analyze_screenshot_quality(image_path: str) -> tuple[float, str]:
    """
    Analyze screenshot to determine if it contains interesting content.

    Returns (score, description)
    score: 0.0-1.0 float
    description: str explaining the score
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        file_size = Path(image_path).stat().st_size

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Sample pixels to analyze content
        pixels = list(img.getdata())

        # Calculate metrics
        total_pixels = len(pixels)
        sample_size = min(10000, total_pixels)
        sample = pixels[:sample_size]

        # 1. Color diversity (more colors = more content)
        unique_colors = len(set(sample))
        color_diversity_score = min(1.0, unique_colors / (sample_size * 0.3))

        # 2. Check for mostly white/blank (common in loading pages)
        white_pixels = sum(1 for p in sample if p[0] > 240 and p[1] > 240 and p[2] > 240)
        white_ratio = white_pixels / sample_size
        non_blank_score = 1.0 - min(0.8, white_ratio)

        # 3. File size indicator (larger = more content usually)
        size_score = min(1.0, file_size / 300000)  # 300KB+ is good

        # 4. Check for text-like patterns (edges/contrast)
        # Sample pixels in a grid pattern
        grid_sample = []
        for y in range(0, height, 50):
            for x in range(0, width, 50):
                if y < height and x < width:
                    pixel_index = y * width + x
                    if pixel_index < total_pixels:
                        grid_sample.append(pixels[pixel_index])

        # Calculate contrast variance
        if grid_sample:
            brightness_values = [sum(p) / 3 for p in grid_sample]
            avg_brightness = sum(brightness_values) / len(brightness_values)
            variance = sum((b - avg_brightness) ** 2 for b in brightness_values) / len(brightness_values)
            contrast_score = min(1.0, variance / 10000)
        else:
            contrast_score = 0.5

        # Combined score (weighted average)
        total_score = (
            color_diversity_score * 0.3 +
            non_blank_score * 0.3 +
            size_score * 0.2 +
            contrast_score * 0.2
        )

        # Generate description
        if total_score > 0.8:
            desc = "Excellent: Rich content with text and images"
        elif total_score > 0.6:
            desc = "Good: Visible content loaded"
        elif total_score > 0.4:
            desc = "Fair: Some content visible"
        elif white_ratio > 0.7:
            desc = "Poor: Mostly blank/white page"
        else:
            desc = "Poor: Limited content visible"

        return total_score, desc

    except Exception as e:
        return 0.0, f"Analysis error: {str(e)}"


if __name__ == "__main__":
    # Test the capture
    async def test():
        result = await capture_with_intelligent_fallback(
            "https://www.bbc.com/news",
            "./test_intelligent.png"
        )
        print(f"\nFinal Result: {result}")

    asyncio.run(test())
