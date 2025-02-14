from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .models2 import ChatFunctionCallRequest, AnswerChunk, SupportedParties
from typing import AsyncGenerator, List
import json
import asyncio   # <-- Added import for asynchronous sleep
import logging

router = APIRouter()

async def generate_demo_chunks(request: ChatFunctionCallRequest) -> AsyncGenerator[bytes, None]:
    logging.info("Generating demo chunks...")

    # Answer type chunk
    answer_type = "web-search-answer" if request.question_body.web_search else "standard-answer"
    answer_type_chunk_obj = {
        "type": "answer-type-chunk",
        "answer_type": answer_type
    }
    answer_type_chunk = AnswerChunk(chunk=answer_type_chunk_obj).model_dump_json() + "\n\n"
    # Print and log the text portion (for answer type, this is the answer_type value)
    print("Sending chunk text:", answer_type_chunk_obj["answer_type"])
    logging.info(f"Sent answer type chunk to frontend. Text: {answer_type_chunk_obj['answer_type']}")
    yield answer_type_chunk  # yielding the chunk
    await asyncio.sleep(0.5)

    # Example answer chunks
    if request.question_body.web_search:
        for i in range(10):
            answer_delta = f"Here's a web-based answer part {i+1}: "
            web_search_chunk_obj = {
                "type": "web-search-answer-chunk",
                "answer_delta": answer_delta
            }
            web_search_chunk = AnswerChunk(chunk=web_search_chunk_obj).model_dump_json() + "\n\n"
            # Print and log the text portion (answer_delta)
            print("Sending chunk text:", answer_delta)
            logging.info(f"Sent web search chunk {i+1} to frontend. Text: {answer_delta}")
            yield web_search_chunk
            await asyncio.sleep(0.3)
    else:
        # Create tasks for each party
        tasks = [
            generate_party_chunks(party, request.question_body.selected_parties)
            for party in request.question_body.selected_parties
        ]
        # Run tasks concurrently and yield results in alternating order
        for i in range(10):
            results = await asyncio.gather(*[task.__anext__() for task in tasks])
            for result in results:
                yield result
            await asyncio.sleep(0.3)
    
    # Example citation chunk
    citation_type = "web-citation-chunk" if request.question_body.web_search else "manifesto-citation-chunk"
    citation_obj = {
        "title": "Example Source",
        "content": "Example content...",
        "url": "https://example.com" if request.question_body.web_search else None,
        "manifesto": SupportedParties.CDU_CSU if not request.question_body.web_search else None,
        "text": "Relevant text section"
    }
    citation_chunk_obj = {
        "type": citation_type,
        "citation": citation_obj
    }
    citation_chunk = AnswerChunk(chunk=citation_chunk_obj).model_dump_json() + "\n\n"
    # Print and log the citation text (inside citation_obj's "text" field)
    print("Sending chunk text:", citation_obj["text"])
    logging.info(f"Sent citation chunk to frontend. Text: {citation_obj['text']}")
    yield citation_chunk

async def generate_party_chunks(party: str, selected_parties: List[str]) -> AsyncGenerator[bytes, None]:
    for i in range(10):
        answer_delta = f"{party.upper()} position part {i+1}: "
        multi_party_chunk_obj = {
            "type": "multi-party-answer-chunk",
            "answer_delta": answer_delta,
            "party": party
        }
        multi_party_chunk = AnswerChunk(chunk=multi_party_chunk_obj).model_dump_json() + "\n\n"
        # Print and log the text portion (answer_delta)
        print("Sending chunk text:", answer_delta)
        logging.info(f"Sent multi-party chunk {i+1} for {party} to frontend. Text: {answer_delta}")
        yield multi_party_chunk
        await asyncio.sleep(0.3)

@router.post("/unified-chat")
async def unified_chat_endpoint(request: ChatFunctionCallRequest):
    try:
        print(request)
        answer = StreamingResponse(
            generate_demo_chunks(request),
            media_type="text/event-stream"
        )
        print("answer:", answer)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 