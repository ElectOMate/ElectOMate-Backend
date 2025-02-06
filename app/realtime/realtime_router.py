from fastapi import APIRouter, HTTPException

from ..models import SupportedLanguages
from .reatime import get_session

router = APIRouter()

@router.post("/session/{language_code}")
async def session(language_code: SupportedLanguages):
    response = await get_session(language_code)
    
    if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch session: {response.text}",
            )

    data = response.json()
    return {"client_secret": data["client_secret"]}