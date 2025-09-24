import logging

from em_backend.query.query import query_rag, stream_rag
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from em_backend.core.config import langchain_async_clients
from em_backend.v1.old_models import Answer, AnswerChunk, Question, SupportedLanguages

router = APIRouter()


@router.post("/stream/{language_code}")
async def stream(language_code: SupportedLanguages, question: Question) -> AnswerChunk:
    logging.debug(f"POST request received at /stream/{language_code}...")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    return StreamingResponse(
        stream_rag(
            question.question,
            question.selected_parties,
            question.use_web_search,
            question.use_database_search,
            langchain_async_clients,
            weaviate_async_client,
            language_code,
        ),
        media_type="text/event-stream",
    )


@router.post("/query/{language_code}")
async def query(language_code: SupportedLanguages, question: Question) -> Answer:
    logging.debug(f"POST request received at /query/{language_code}...")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    # Return the full response
    response = await query_rag(
        question.question,
        question.selected_parties,
        question.use_web_search,
        question.use_database_search,
        langchain_async_clients,
        weaviate_async_client,
        language_code,
    )
    return JSONResponse(response)
