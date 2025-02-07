from fastapi import APIRouter, HTTPException

from ..models import (
    SupportedLanguages,
    AskAllPartiesResponse,
    PartyResponse,
    AskAllPartiesRequest,
)
from ..config import weaviate_async_client, cohere_async_clients
from ..query.query_router import query_rag


import logging

router = APIRouter()


@router.post("/askallparties/{country_code}")
async def askallparties(
    country_code: SupportedLanguages, request: AskAllPartiesRequest
) -> AskAllPartiesResponse:
    logging.info(f"POST request received at /askallparties/{country_code}/...")
    question = request.question_body.question
    selected_parties = request.selected_parties

    logging.debug(f"Received question: {question}")
    logging.debug(f"Selected parties: {selected_parties}")

    if not question:
        logging.error("Received an empty question.")
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        logging.info("Preparing to query parties' responses.")

        responses = []
        for party, isSelected in selected_parties.items():
            if isSelected:
                prefixed_question = f"What would {party} say to this: {question}"
                logging.debug(
                    f"Querying RAG for party: {party} with question: {prefixed_question}"
                )
                # Return the full response
                response = await query_rag(
                    request.question_body.question,
                    request.question_body.rerank,
                    cohere_async_clients,
                    weaviate_async_client,
                    country_code,
                )

                policies = [s.strip() for s in response.split(".") if s.strip()]
                logging.debug(f"Received policies for {party}: {policies}")
                responses.append(PartyResponse(party=party, policies=policies))

        logging.info(f"responses={responses}")
        logging.info("Successfully gathered responses from selected parties.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return AskAllPartiesResponse(responses=responses)
