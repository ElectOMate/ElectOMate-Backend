"""YouTube video transcription connector using Google Gemini 2.5 Pro.

Transcribes Hungarian political YouTube videos with speaker diarization
and timestamps via the Gemini multimodal API.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date

import structlog
from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from em_backend.core.config import settings
from em_backend.graph.connectors.base import (
    IngestedDocument,
    Modality,
    SourceType,
    SpeakerInfo,
    TextSegment,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Transcription prompt
# ---------------------------------------------------------------------------

TRANSCRIPTION_PROMPT = """\
You are a professional Hungarian-language transcription assistant.

Transcribe the following YouTube video in Hungarian. Produce a verbatim transcript
with the following rules:

1. **Timestamps**: Start every new speech segment with a timestamp in [MM:SS] format.
2. **Speaker diarization**: Identify each speaker. Use their real name if it is
   displayed on screen or mentioned in the video. Otherwise label them as
   "Speaker 1", "Speaker 2", etc.  Format: `[MM:SS] Speaker Name:`
3. **Language**: The transcript MUST be in Hungarian. Do not translate.
4. **Fidelity**: Transcribe verbatim — do not summarize or paraphrase.
5. **Non-speech**: Note significant non-speech audio in parentheses, e.g.
   "(taps)" or "(zene)" only when relevant.

Output ONLY the transcript, no commentary. Example format:

[00:00] Kovács János: Tisztelt Hölgyeim és Uraim, üdvözlöm önöket.
[00:15] Nagy Anna: Köszönöm a meghívást.
[01:02] Kovács János: Térjünk rá a mai témánkra.
"""

# ---------------------------------------------------------------------------
# Segment parsing
# ---------------------------------------------------------------------------

_SEGMENT_RE = re.compile(
    r"\[(?P<timestamp>\d{1,3}:\d{2})\]\s*(?P<speaker>[^:]+):\s*(?P<text>.+)"
)


def _parse_transcript(raw: str) -> tuple[list[TextSegment], list[SpeakerInfo]]:
    """Parse Gemini transcript text into structured segments and speakers."""
    segments: list[TextSegment] = []
    seen_speakers: dict[str, SpeakerInfo] = {}

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        match = _SEGMENT_RE.match(line)
        if match:
            timestamp = match.group("timestamp")
            speaker = match.group("speaker").strip()
            text = match.group("text").strip()

            segments.append(
                TextSegment(
                    text=text,
                    speaker=speaker,
                    timestamp=timestamp,
                )
            )

            if speaker not in seen_speakers:
                seen_speakers[speaker] = SpeakerInfo(name=speaker)
        else:
            # Line without expected format — append to previous segment or
            # create a standalone segment without speaker/timestamp.
            if segments:
                segments[-1].text += f" {line}"
            else:
                segments.append(TextSegment(text=line))

    return segments, list(seen_speakers.values())


# ---------------------------------------------------------------------------
# Gemini client helpers
# ---------------------------------------------------------------------------


def _get_client() -> genai.Client:
    """Build an authenticated Gemini client."""
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. "
            "Set it in the environment or .env file."
        )
    return genai.Client(api_key=settings.google_api_key)


class YouTubeTranscriptionError(Exception):
    """Raised when transcription fails after retries."""


# ---------------------------------------------------------------------------
# Core transcription
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    before_sleep=lambda rs: structlog.get_logger(__name__).warning(
        "retrying_transcription",
        attempt=rs.attempt_number,
        wait=rs.next_action.sleep,
    ),
)
def _call_gemini(client: genai.Client, youtube_url: str) -> str:
    """Send the YouTube URL to Gemini and return the raw transcript text.

    Retries up to 3 times with exponential back-off on transient failures.
    """
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=types.Content(
            parts=[
                types.Part(text=TRANSCRIPTION_PROMPT),
                types.Part(
                    file_data=types.FileData(file_uri=youtube_url),
                ),
            ],
        ),
    )

    if not response.text:
        raise YouTubeTranscriptionError(
            f"Gemini returned an empty response for {youtube_url}"
        )

    return response.text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe_youtube_video(
    url: str,
    title: str | None = None,
    source_type: SourceType = SourceType.INTERVIEW,
) -> IngestedDocument:
    """Transcribe a single YouTube video and return an IngestedDocument.

    Args:
        url: Full YouTube video URL (e.g. https://www.youtube.com/watch?v=...).
        title: Optional human-readable title. Falls back to the URL if not given.
        source_type: The political source category. Defaults to INTERVIEW.

    Returns:
        An IngestedDocument with timestamped, speaker-diarized segments.

    Raises:
        YouTubeTranscriptionError: If the Gemini API call fails after retries.
        RuntimeError: If GOOGLE_API_KEY is not configured.
    """
    log = logger.bind(url=url, title=title)
    log.info("transcription_started")

    client = _get_client()

    try:
        raw_text = _call_gemini(client, url)
    except Exception as exc:
        log.error("transcription_failed", error=str(exc))
        raise YouTubeTranscriptionError(
            f"Failed to transcribe {url}: {exc}"
        ) from exc

    segments, speakers = _parse_transcript(raw_text)

    doc = IngestedDocument(
        source_type=source_type,
        modality=Modality.VIDEO,
        source_url=url,
        title=title or url,
        date=date.today(),
        language="hu",
        speakers=speakers,
        segments=segments,
        raw_text=raw_text,
        metadata={
            "transcription_model": "gemini-2.5-pro",
            "segment_count": len(segments),
            "speaker_count": len(speakers),
        },
    )

    log.info(
        "transcription_complete",
        segments=len(segments),
        speakers=len(speakers),
    )
    return doc


def batch_transcribe(
    urls: list[str],
    source_type: SourceType = SourceType.INTERVIEW,
) -> list[IngestedDocument]:
    """Transcribe multiple YouTube videos sequentially.

    Failed transcriptions are logged and skipped — the returned list may be
    shorter than the input list.

    Args:
        urls: List of YouTube video URLs.
        source_type: The political source category applied to all videos.

    Returns:
        List of successfully transcribed IngestedDocument objects.
    """
    results: list[IngestedDocument] = []

    for url in urls:
        try:
            doc = transcribe_youtube_video(url, source_type=source_type)
            results.append(doc)
        except (YouTubeTranscriptionError, RuntimeError) as exc:
            logger.error("batch_transcription_skipped", url=url, error=str(exc))

    logger.info(
        "batch_transcription_complete",
        total=len(urls),
        succeeded=len(results),
        failed=len(urls) - len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Test / sample search terms for finding Hungarian political YouTube content
# ---------------------------------------------------------------------------

# These are SEARCH TERMS to find relevant videos on YouTube, not direct URLs
# (which expire or get removed). Paste them into youtube.com/results?search_query=
# to locate current content.
TEST_SEARCH_TERMS: list[dict[str, str]] = [
    {
        "description": "Parliamentary debates (Országgyűlés)",
        "search": "Országgyűlés parlamenti vita 2024",
    },
    {
        "description": "Parliamentary committee hearings",
        "search": "országgyűlés bizottsági ülés 2024",
    },
    {
        "description": "HírTV political interview",
        "search": "HírTV politikai interjú 2024",
    },
    {
        "description": "ATV Egyenes Beszéd political show",
        "search": "ATV Egyenes Beszéd 2024",
    },
    {
        "description": "Tisza Párt / Magyar Péter press conference",
        "search": "Magyar Péter Tisza Párt sajtótájékoztató 2024",
    },
    {
        "description": "Government press conference (Kormányinfó)",
        "search": "Kormányinfó Gulyás Gergely 2024",
    },
    {
        "description": "Opposition parliamentary speeches",
        "search": "ellenzéki felszólalás parlament 2024",
    },
    {
        "description": "Fidesz party congress / event",
        "search": "Fidesz kongresszus Orbán Viktor beszéd 2024",
    },
]
