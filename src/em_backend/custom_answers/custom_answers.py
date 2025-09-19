from ..langchain_citation_client import HumanMessage
import weaviate.classes as wvc

from em_backend.models import QuestionnaireQuestion, UserAnswer
from em_backend.config import langchain_async_clients, weaviate_async_client
from em_backend.statics.questionaire_party_answers import (
    questionnaire_party_answers,
    default_party_info,
)
from em_backend.statics.evaluation_prompts import EVALUATION_PROMPT2
from em_backend.statics.party_answers import party_answers
from em_backend.custom_answers.score_calculator import calculate_standard_scores, combine_results

import json
import logging


async def get_party_contexts(
    party_name: str, lookup_prompts: list[str], max_contexts=7
) -> tuple[list[str], list[dict]]:
    """Retrieve relevant party program contexts using OpenAI embeddings + Weaviate."""
    try:
        # Generate embeddings for lookup prompts
        # TO REMOVE: outdated calls -- migrating to third-party service
        embed_response = await langchain_async_clients[
            "embed_client"
        ].embed(
            texts=lookup_prompts,
            model="embed-multilingual-v3.0",
            input_type="search_query",
            embedding_types=["float"],
        )

        # Query Weaviate collection
        collection = weaviate_async_client.collections.get("Documents")
        contexts = []
        details = []

        for embedding in embed_response.embeddings.float:
            result = await collection.query.hybrid(
                query=" ".join(lookup_prompts),  # Combine prompts for hybrid search
                vector=embedding,
                limit=max_contexts,
                filters=wvc.query.Filter.by_property("filename").like(
                    f"{party_name.lower()}.pdf"
                ),
            )

            for obj in result.objects:
                title = obj.properties.get("title", "No title available")
                chunk_content = obj.properties.get(
                    "chunk_content", "No content available"
                )
                details.append({"title": title, "content": chunk_content})
                contexts.append(chunk_content)

        # Remove duplicates while preserving order
        unique_contexts = list(dict.fromkeys(contexts))
        return unique_contexts, details

    except Exception as e:
        default_value = default_party_info.get(party_name, "No context available")
        return [default_value], [{"title": "", "content": default_value}]


async def compare_user_response_to_party(
    question_id: int,
    question: str,
    main_parties: list[str],
    party_responses: list[str],
    user_response: str,
    main_contexts: dict,
):
    """
    Compares user response to party positions using OpenAI with RAG contexts
    """
    try:
        # Prepare evaluation prompt with contexts
        prompt_value = EVALUATION_PROMPT2.invoke(
            {
                "question": question,
                "main_parties": main_parties,
                "party_responses": party_responses,
                "user_response": user_response,
                "main_contexts": main_contexts,
                "agreement_score": 0,
            }
        )

        # Force `prompt_value` to a simple string
        # If `prompt_value` is already a string, just use it.
        # Otherwise, if it's a StringPromptValue, use .text
        prompt_str = (
            prompt_value.text if hasattr(prompt_value, "text") else str(prompt_value)
        )

        messages = [HumanMessage(content=prompt_str)]
        evaluation_response = await langchain_async_clients["langchain_chat_client"].chat(
            model="gpt-4o", messages=messages
        )
        evaluation_content = evaluation_response.message.content[0].text
        evaluation_dict = json.loads(evaluation_content)
        return process_evaluation(evaluation_dict)

    except Exception as e:
        return None


def process_evaluation(evaluation_dict):
    """Process OpenAI evaluation response"""
    agreement_scores = {}
    reasonings = {}
    for party, items in evaluation_dict.items():
        if "agreement_score" in items and "reasoning" in items:
            agreement_scores[party] = items["agreement_score"]
            reasonings[party] = items["reasoning"]
    return agreement_scores, reasonings


async def get_custom_answers_evaluation(
    questionnaire_questions: list[QuestionnaireQuestion],
    custom_answers: list[UserAnswer],
):
    """
    Main evaluation flow using OpenAI RAG and party program analysis
    """
    # Define all possible parties first
    main_parties = [
        "SPD",
        "GRUENE",
        "FDP",
        "CDU/CSU",
        "LINKE",
        "AFD",
        "FREIE WÄHLER",
        "Volt",
        "MLPD",
        "BÜNDNIS DEUTSCHLAND",
        "BSW",
    ]

    # Initialize party_scores as a dictionary of dictionaries
    party_scores = {
        party: {"score": 0, "short_name": party, "full_name": "", "partyInfo": ""}
        for party in main_parties
    }

    non_skipped_count = 0
    for idx, (question, answer) in enumerate(
        zip(questionnaire_questions, custom_answers)
    ):
        if answer.custom_answer:
            answer_type = "custom"
        else:
            answer_type = "button"

        # Log button answers with minimal details and skip further evaluation
        if answer_type == "button":
            continue

        # Get party responses for current question
        party_responses = questionnaire_party_answers.get(
            question.id,  # Use question ID instead of index
            {},  # Default to empty dict if not found
        ).values()  # Keep .values() for compatibility

        # Add error handling for empty responses
        if not party_responses:
            logging.warning(f"No party responses found for question ID {question.id}")
            continue

        # Retrieve contexts for all parties
        party_contexts = {}
        party_contexts_log = {}
        for party in main_parties:
            # Generate search queries from question/answer
            lookup_prompt = f"""
            Given the question: {question.q}
            And user's response: {answer.custom_answer}
            Generate relevant search queries to find party positions on this topic.
            Return ONLY a JSON array in this format: {{"lookupPrompts": ["query1", "query2"]}}
            """

            # Get lookup prompts
            lookup_response = await langchain_async_clients["langchain_chat_client"].chat(
                model="gpt-4o",
                messages=[HumanMessage(content=lookup_prompt)],
            )
            lookup_data = json.loads(lookup_response.message.content[0].text)
            lookup_prompts = lookup_data.get(
                "lookupPrompts", [question.q, answer.custom_answer]
            )

            # Perform filtered search
            contexts, details = await get_party_contexts(party, lookup_prompts)

            party_contexts[party] = contexts
            party_contexts_log[party] = details

        # Split contexts
        main_contexts = {k: v for k, v in party_contexts.items() if k in main_parties}

        # Get OpenAI evaluation
        processed_eval, _ = await compare_user_response_to_party(
            question_id=idx,
            question=question.q,
            main_parties=main_parties,
            party_responses=list(party_responses),
            user_response=answer.custom_answer,
            main_contexts=main_contexts,
        )

        if processed_eval and not answer.skipped:
            non_skipped_count += 1

    # Calculate standard scores for non-custom answers
    standard_results = calculate_standard_scores(
        [a for a in custom_answers if not a.custom_answer],
        party_answers,  # Pass the entire JSON data
    )

    # Get custom results (your existing implementation)
    custom_results = [
        {
            "short_name": party["short_name"],
            "score": party["score"],
            "full_name": party["full_name"],
            "partyInfo": party["partyInfo"],
        }
        for party in party_scores.values()  # Ensure you're iterating over the values
    ]

    # Combine both results
    final_results = combine_results(standard_results, custom_results)

    # Normalize custom party scores: divide by the count of non-skipped questions if >0
    if non_skipped_count > 0:
        for party in party_scores:
            party_scores[party]["score"] /= non_skipped_count

    return final_results
