from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from ..models import Question, Answer, SupportedLanguages
from ..config import weaviate_async_client, cohere_async_clients
from .query import stream_rag, query_rag

import logging

router = APIRouter()

@router.post("/stream/{language_code}")
async def stream(
    language_code: SupportedLanguages, question: Question
) -> StreamingResponse:
    logging.debug(f"POST request received at /stream/{language_code}...")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    return StreamingResponse(
        stream_rag(
            question.question,
            question.rerank,
            cohere_async_clients,
            weaviate_async_client,
            language_code
        ),
        media_type="text/event-stream",
    )


@router.post("/query/{language_code}")
async def query(language_code: SupportedLanguages, question: Question) -> Answer:
    logging.debug(f"POST request received at /query/{language_code}...")
    print(f"question: {question}")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")
    else:
        print("Weaviate is ready.")

    # Return the full response
    response = await query_rag(
        question.question, question.rerank, cohere_async_clients, weaviate_async_client, language_code
    )
    return JSONResponse(
        response
    )