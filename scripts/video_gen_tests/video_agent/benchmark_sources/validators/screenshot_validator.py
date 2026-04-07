"""Screenshot quality validator."""

from pathlib import Path
from PIL import Image

def validate_screenshot(screenshot_path: str) -> float:
    """
    Validate screenshot quality.

    Returns quality score 0.0-1.0 based on:
    - File exists and is readable
    - Image dimensions are reasonable
    - Image is not blank/placeholder
    - File size indicates actual content
    """
    try:
        path = Path(screenshot_path)

        if not path.exists():
            return 0.0

        # Check file size (too small = placeholder)
        file_size = path.stat().st_size
        if file_size < 5000:  # Less than 5KB is likely placeholder
            return 0.3

        # Open and validate image
        img = Image.open(path)
        width, height = img.size

        # Check dimensions
        if width < 100 or height < 100:
            return 0.4

        # Check if image is not blank (sample pixels)
        pixels = list(img.getdata())
        unique_colors = len(set(pixels[:100]))  # Sample first 100 pixels

        if unique_colors < 5:  # Too few colors = likely blank
            return 0.5

        # Calculate quality score
        score = 0.0
        score += 0.3  # File exists
        score += 0.2 if file_size > 50000 else 0.1  # Good file size
        score += 0.3 if width >= 1280 and height >= 720 else 0.2  # Good dimensions
        score += 0.2 if unique_colors > 20 else 0.1  # Color diversity

        return min(1.0, score)

    except Exception as e:
        print(f"  Screenshot validation error: {e}")
        return 0.0
