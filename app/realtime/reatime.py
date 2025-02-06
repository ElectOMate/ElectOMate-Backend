from httpx import AsyncClient

from ..models import SupportedLanguages
from ..config import settings
from ..statics.prompts import realtime_session_instructions
from ..statics.tools import realtime_session_tools

async def get_session(language: SupportedLanguages):
    with AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "verse",
                "modalities": ["audio", "text"],
                "instructions": realtime_session_instructions[language],
                "tools": [realtime_session_tools[language]],
                "tool_choice": "required",
            },
        )
    return response