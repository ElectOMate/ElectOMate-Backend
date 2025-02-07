from fastapi import APIRouter, HTTPException
from .Bingsearch import perform_search

router = APIRouter()

@router.post("/search")
async def search_route(query: dict) -> dict:
    try:
        # Call the service function that implements the search logic
        return await perform_search(query)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))