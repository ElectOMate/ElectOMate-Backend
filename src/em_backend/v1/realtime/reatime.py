from em_backend.statics.prompts import realtime_session_instructions
from em_backend.statics.tools import realtime_session_tools
from httpx import AsyncClient

from em_backend.config import settings
from em_backend.old_models import SupportedLanguages


async def get_session(language: SupportedLanguages):
    async with AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "coral",
                "modalities": ["audio", "text"],
                "instructions": realtime_session_instructions[language],
                "tools": [realtime_session_tools[language]],
                # "tool_choice": "required",
                # "temperature": 0.0,
                # "turn_detection": False,
            },
        )
        return response
