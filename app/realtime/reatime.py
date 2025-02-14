from httpx import AsyncClient
import httpx

from ..models import SupportedLanguages
from ..config import settings
from ..statics.prompts import realtime_session_instructions
from ..statics.tools import realtime_session_tools

async def get_session(language: SupportedLanguages):
   async with AsyncClient() as client:
        print(f"Language: {language}")
        print(f"Instructions: {realtime_session_instructions.get(language, 'Not Found')}")
        print(f"Tools: {realtime_session_tools.get(language, 'Not Found')}")
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
   




   