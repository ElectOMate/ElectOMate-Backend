from fastapi import APIRouter, HTTPException
from .Bingsearch import perform_search
from ..models import SearchQuery

router = APIRouter()

@router.post("/search")
async def search_route(query: SearchQuery) -> dict:
    try:
        # Call the service function that implements the search logic
        return await perform_search(query)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))