"""Research tools: web search, knowledge base search, screenshot capture."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx


async def web_search(query: str, output_dir: str) -> dict[str, Any]:
    """Search the web via Perplexity API and return structured results with sources."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")

    # Fallback to Gemini if no Perplexity key
    if not api_key:
        return await _gemini_search(query, output_dir)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": query}],
            },
            timeout=30,
        )
        data = resp.json()

    answer = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])

    result = {
        "query": query,
        "answer": answer,
        "sources": [{"index": i + 1, "url": url} for i, url in enumerate(citations)],
    }

    # Save result
    out = Path(output_dir) / "research"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "web_search_results.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


async def _gemini_search(query: str, output_dir: str) -> dict[str, Any]:
    """Fallback: use Gemini for research when Perplexity unavailable."""
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"Research this topic thoroughly and provide factual information with sources. "
            f"Format your response as JSON with 'answer' (string) and 'sources' (list of "
            f"objects with 'index', 'title', 'url', 'description'). Topic: {query}"
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        result = json.loads(text)

        # Gemini sometimes returns nested JSON - check if answer is a JSON string
        if "answer" in result and isinstance(result["answer"], str):
            try:
                inner_result = json.loads(result["answer"])
                if isinstance(inner_result, dict) and "sources" in inner_result:
                    # Merge inner sources with outer result
                    result["sources"] = inner_result.get("sources", [])
                    result["answer"] = inner_result.get("answer", result["answer"])
            except json.JSONDecodeError:
                pass  # answer is just a regular string, not nested JSON
    except json.JSONDecodeError:
        result = {"answer": text, "sources": []}

    result["query"] = query

    out = Path(output_dir) / "research"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "web_search_results.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def take_screenshot(url: str, output_path: str, width: int = 1280, height: int = 720) -> str:
    """Take a screenshot of a URL using Puppeteer/Chrome headless."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Use Chrome headless directly
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]
    chrome = next((p for p in chrome_paths if Path(p).exists()), None)

    if chrome:
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--screenshot={output_path}", f"--window-size={width},{height}",
             "--hide-scrollbars", url],
            capture_output=True, timeout=30,
        )
        if Path(output_path).exists():
            return output_path

    # Fallback: generate a placeholder card image with the URL text
    _generate_source_card(url, output_path)
    return output_path


def _generate_source_card(url: str, output_path: str) -> None:
    """Generate a simple source card image with URL text."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1280, 720), color=(20, 20, 30))
    draw = ImageDraw.Draw(img)

    # Try to use a system font
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = font_large

    draw.text((60, 280), "SOURCE", fill=(100, 180, 255), font=font_large)
    # Truncate URL if too long
    display_url = url if len(url) < 80 else url[:77] + "..."
    draw.text((60, 340), display_url, fill=(200, 200, 200), font=font_small)

    img.save(output_path)


def search_knowledge_base(query: str, manifesto_dir: str) -> list[dict]:
    """Search local manifesto PDFs for relevant content."""
    results = []
    manifesto_path = Path(manifesto_dir)

    if not manifesto_path.exists():
        return results

    for pdf_file in manifesto_path.glob("**/*.pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(pdf_file) as pdf:
                for i, page in enumerate(pdf.pages[:20]):  # First 20 pages
                    text = page.extract_text() or ""
                    if any(term.lower() in text.lower() for term in query.split()):
                        results.append({
                            "source": str(pdf_file),
                            "page": i + 1,
                            "excerpt": text[:500],
                            "type": "manifesto",
                        })
        except Exception:
            continue

    return results[:10]  # Top 10 matches
