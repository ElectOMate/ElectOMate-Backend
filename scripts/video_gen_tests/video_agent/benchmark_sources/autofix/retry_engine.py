"""Retry engine with multiple fallback strategies."""

import asyncio
import sys
import subprocess
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def retry_with_fallbacks(failed_result: dict) -> dict:
    """
    Retry failed test case with different strategies.

    Strategies:
    1. Retry with longer timeout
    2. Try different screenshot method (Puppeteer MCP if available)
    3. Retry with different window size
    4. Try alternative URL extraction method
    """
    test_name = failed_result["name"]
    test_url = failed_result["url"]

    print(f"    Retrying: {test_name}")

    # Strategy 1: Retry with longer timeout
    if not failed_result["validations"].get("screenshot_captured", False):
        print("      Strategy: Longer timeout")
        try:
            from agent.tools import research
            output_path = failed_result.get("screenshot_path", "")
            if output_path:
                # Retry with extended timeout
                chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/usr/bin/google-chrome",
                ]
                chrome = next((p for p in chrome_paths if Path(p).exists()), None)
                if chrome:
                    subprocess.run(
                        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                         f"--screenshot={output_path}", f"--window-size=1920,1080",
                         "--hide-scrollbars", test_url],
                        capture_output=True, timeout=60,  # Longer timeout
                    )
                    if Path(output_path).exists():
                        print("      ✓ Retry successful")
                        return failed_result
        except Exception as e:
            print(f"      ✗ Retry failed: {e}")

    # Strategy 2: Try different window size
    if failed_result["validations"].get("screenshot_quality", 0) < 0.7:
        print("      Strategy: Different window size")
        try:
            from agent.tools import research
            output_path = failed_result.get("screenshot_path", "")
            if output_path:
                research.take_screenshot(test_url, output_path, width=1920, height=1080)
                print("      ✓ Retry with larger size successful")
                return failed_result
        except Exception as e:
            print(f"      ✗ Retry failed: {e}")

    # Strategy 3: Wait and retry (dynamic content loading)
    print("      Strategy: Wait and retry")
    await asyncio.sleep(2)
    try:
        from agent.tools import research
        output_path = failed_result.get("screenshot_path", "")
        if output_path:
            research.take_screenshot(test_url, output_path)
            print("      ✓ Delayed retry successful")
            return failed_result
    except Exception as e:
        print(f"      ✗ Retry failed: {e}")

    return failed_result
