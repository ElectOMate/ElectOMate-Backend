from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from em_backend.models import SupportedLanguages
from em_backend.realtime.reatime import get_session
from em_backend.models import ChatFunctionCallRequest
from em_backend.config import weaviate_async_client, langchain_async_clients
from em_backend.query.query import query_rag

router = APIRouter()


@router.get("/session/{language_code}")
async def session(language_code: SupportedLanguages):
    response = await get_session(language_code)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch session: {response.text}",
        )

    data = response.json()
    return {"client_secret": data["client_secret"]}


# ------------------------------
# NEW: function-calling route
# ------------------------------
@router.post("/function/fetch-rag-data")
async def fetch_rag_data(
    payload: ChatFunctionCallRequest,
):
    """
    This route is called internally by your function-calling logic (via real-time).
    It just delegates to the RAG pipeline used in /chat/{country_code}.
    """
    country_code = payload.country_code
    question_obj = payload.question_body
    if not question_obj.question:
        raise HTTPException(status_code=400, detail="No question provided.")


    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    # Return the full response
    response = await query_rag(
        question_obj.question,
        question_obj.rerank,
        langchain_async_clients,
        weaviate_async_client,
        country_code,
    )
    return JSONResponse(response)
