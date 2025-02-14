# custom_answer_evaluation.py

import random
import json
import asyncio
from collections import defaultdict
from typing import List
from ..models import QuestionnaireQuestion, UserAnswer
from app.api2.models2_customanswer import CustomAnswerModel
from .eval_prompts import EVALUATION_PROMPT, GENERATE_LOOKUP_PROMPT, EVALUATION_PROMPT2
from app.config import cohere_async_clients, weaviate_async_client
from weaviate.collections.classes.filters import Filter
from cohere import UserChatMessageV2
from .score_calculator import calculate_standard_scores, combine_results
import weaviate.classes as wvc

# Import party answers and default info
from . import questionnaire_party_answers
from .questionnaire_party_answers import default_party_info

# New imports for logging
import os
from datetime import datetime, timezone
import subprocess

from app.query.query import database_search

# Set the log file path (JSON Lines format)
CURRENT_DIR = os.path.dirname(__file__)
LOG_FILE_PATH = os.path.join(CURRENT_DIR, "evaluation_log.jsonl")

# Load party answers data
with open('app/custom_answer_evaluation/Partyanswers.json', 'r') as f:
    PARTY_ANSWERS_DATA = json.load(f)

classication_to_score = {"strongly disagree": -1, "disagree": -0.5, "neutral": 0, "agree": 0.5, "strongly agree": 1}

default_parties_list = [
        {
            "score": 0,
            "short_name": "SPD",
            "full_name": "Sozialdemokratische Partei Deutschlands",
            "partyInfo": "The SPD is a social-democratic party advocating for social justice, welfare state expansion, and pro-EU policies." 
        },
        {
            "score": 0,
            "short_name": "GRUENE",
            "full_name": "BÜNDNIS 90/DIE GRÜNEN",
            "partyInfo": "The Greens prioritize environmental protection, social justice, human rights, and grassroots democracy."
        },
        {
            "score": 0,
            "short_name": "FDP",
            "full_name": "Freie Demokratische Partei",
            "partyInfo": "The FDP is a liberal party focusing on free markets, individual rights, lower taxes, and pro-business policies."
        },
        {
            "score": 0,
            "short_name": "CDU/CSU",
            "full_name": "Christlich Demokratische Union Deutschlands",
            "partyInfo": "The CDU/CSU is a center-right political alliance with a focus on social market economy, European integration, and conservative values."
        },
        {
            "score": 0,
            "short_name": "LINKE",
            "full_name": "DIE LINKE",
            "partyInfo": "DIE LINKE is a left-wing party emphasizing anti-capitalism, social equality, wealth redistribution, and pacifism."
        },
        {
            "score": 0,
            "short_name": "AFD",
            "full_name": "Alternative für Deutschland",
            "partyInfo": "The AfD is a right-wing populist party, critical of the EU and immigration, with a focus on national sovereignty."
        }
]


# TEMPORARY: To display the JSON structure I will be working with to integrate the discrete answers from the buttons into the evaluation score
sample_json_structure = {
    "custom_answer": "",
    "users_answer": "",
    "wheights": "",
    "skipped": ""
}


# New helper function for logging evaluation details
def append_evaluation_log(log_entry: dict):
    """Appends a log entry (in JSON Lines format) to the evaluation log file and formats the file."""
    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # Format the JSON file using jq
        subprocess.run(
            f"jq . {LOG_FILE_PATH} > {LOG_FILE_PATH}.tmp && mv {LOG_FILE_PATH}.tmp {LOG_FILE_PATH}",
            shell=True,
            check=True
        )
    except Exception as e:
        print(f"Failed to write log entry or format file: {str(e)}")

        
async def compare_user_response_to_party(
    question_id: int,
    question: str,
    main_parties: List[str],
    party_responses: List[str],
    user_response: str,
    main_contexts: dict,
):
    """
    Compares user response to party positions using Cohere with RAG contexts
    """
    try:
        # Prepare evaluation prompt with contexts
        prompt_value = EVALUATION_PROMPT2.invoke({
            "question": question,
            "main_parties": main_parties,
            "party_responses": party_responses,
            "user_response": user_response,
            "main_contexts": main_contexts,
            "agreement_score": 0,
        })

        # Force `prompt_value` to a simple string
        # If `prompt_value` is already a string, just use it.
        # Otherwise, if it's a StringPromptValue, use .text
        prompt_str = (
            prompt_value.text if hasattr(prompt_value, "text") else str(prompt_value)
        )

        messages = [UserChatMessageV2(content=prompt_str)]
        evaluation_response = await cohere_async_clients["command_r_async_client"].chat(
            model="command-r-08-2024",
            messages=messages
        )
        evaluation_content = evaluation_response.message.content[0].text
        evaluation_dict = json.loads(evaluation_content)        
        print("\n")
        print("Evaluation for", question_id, question)
        print(json.dumps(evaluation_dict, indent=4))
        print("\n")
        return process_evaluation(evaluation_dict)
        
    except Exception as e:
        print(f"Evaluation error: {str(e)}")
        return None

async def get_party_contexts(party_name: str, lookup_prompts: List[str], max_contexts=7) -> (List[str], List[dict]):
    """Retrieve relevant party program contexts using Cohere embeddings + Weaviate."""
    try:
        # Generate embeddings for lookup prompts
        embed_response = await cohere_async_clients["embed_multilingual_async_client"].embed(
            texts=lookup_prompts,
            model="embed-multilingual-v3.0",
            input_type="search_query",
            embedding_types=["float"]
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
                filters=wvc.query.Filter.by_property("filename").like(f"{party_name.lower()}.pdf")
            )
            
            for obj in result.objects:
                title = obj.properties.get("title", "No title available")
                chunk_content = obj.properties.get("chunk_content", "No content available")
                details.append({"title": title, "content": chunk_content})
                contexts.append(chunk_content)
    
        # Remove duplicates while preserving order
        unique_contexts = list(dict.fromkeys(contexts))
        return unique_contexts, details
    
    except Exception as e:
        print(f"Context retrieval error: {str(e)}")
        default_value = default_party_info.get(party_name, "No context available")
        return [default_value], [{"title": "", "content": default_value}]

async def get_custom_answers_evaluation(
    questionnaire_questions: List[QuestionnaireQuestion],
    custom_answers: List[UserAnswer]
):
    """
    Main evaluation flow using Cohere RAG and party program analysis
    """
    # Define all possible parties first
    main_parties = ["SPD", "GRUENE", "FDP", "CDU/CSU", "LINKE", "AFD", "FREIE WÄHLER", "Volt", "MLPD", "BÜNDNIS DEUTSCHLAND", "BSW"]
    all_parties = main_parties 
    
    # Initialize party_scores as a dictionary of dictionaries
    party_scores = {party: {"score": 0, "short_name": party, "full_name": "", "partyInfo": ""} for party in main_parties}

    non_skipped_count = 0
    for idx, (question, answer) in enumerate(zip(questionnaire_questions, custom_answers)):
        if answer.custom_answer:
            answer_type = "custom"
        else:
            answer_type = "button"

        # Log button answers with minimal details and skip further evaluation
        if answer_type == "button":
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "question_id": question.id,
                "question": question.q,
                "user_custom_answer": answer.custom_answer,
                "button_answer": answer.users_answer,
                "answer_type": answer_type,
                "lookup_response": None,
                "party_contexts": None,
                "evaluation_scores": None,
                "skipped": answer.skipped,
                "wheights": answer.wheights
            }
            append_evaluation_log(log_entry)
            continue

        # Get party responses for current question
        party_responses = questionnaire_party_answers.questionnaire_party_answers.get(
            question.id,  # Use question ID instead of index
            {}  # Default to empty dict if not found
        ).values()  # Keep .values() for compatibility
        
        # Add error handling for empty responses
        if not party_responses:
            print("\n\n\n")
            logger.warning(f"No party responses found for question ID {question.id}")
            print("\n\n\n")
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
            lookup_response = await cohere_async_clients["command_r_async_client"].chat(
                model="command-r-08-2024",
                messages=[UserChatMessageV2(content=lookup_prompt)]
            )
            lookup_data = json.loads(lookup_response.message.content[0].text)
            lookup_prompts = lookup_data.get("lookupPrompts", [question.q, answer.custom_answer])
            
            # Perform filtered search
            contexts, details = await get_party_contexts(party, lookup_prompts)
            
            party_contexts[party] = contexts
            party_contexts_log[party] = details

        # Split contexts
        main_contexts = {k: v for k, v in party_contexts.items() if k in main_parties}

        # Get Cohere evaluation
        processed_eval, raw_eval = await compare_user_response_to_party(
            question_id=idx,
            question=question.q,
            main_parties=main_parties,
            party_responses=list(party_responses),
            user_response=answer.custom_answer,
            main_contexts=main_contexts,
        )

        if processed_eval and not answer.skipped:
            non_skipped_count += 1
            score_log = update_scores(party_scores, processed_eval, answer)
        else:
            score_log = {}

        # Build the log entry with all requested data
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "question_id": question.id,
            "question": question.q,
            "user_custom_answer": answer.custom_answer,
            "button_answer": answer.users_answer,
            "answer_type": "custom",
            "lookup_response": lookup_data,
            "party_contexts": party_contexts_log,  # Detailed contexts with title and content for each party
            "evaluation_scores": score_log,
            "llm_raw_scores": raw_eval,
            "skipped": answer.skipped,
            "wheights": answer.wheights
        }

        # Append the log entry (including evaluation scores) to our JSON log file
        append_evaluation_log(log_entry)

    print("\n\n\n")
    print("starting standard score calculation now")
    print("\n\n\n")

    # Calculate standard scores for non-custom answers
    standard_results = calculate_standard_scores(
        [a for a in custom_answers if not a.custom_answer],
        PARTY_ANSWERS_DATA  # Pass the entire JSON data
    )
    
    # Get custom results (your existing implementation)
    custom_results = [
        {
            "short_name": party["short_name"],
            "score": party["score"],
            "full_name": party["full_name"],
            "partyInfo": party["partyInfo"]
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

# Helper functions
def process_evaluation(evaluation_dict):
    """Process Cohere evaluation response"""
    agreement_scores = {}
    reasonings = {}
    for party, items in evaluation_dict.items():
        if "agreement_score" in items and "reasoning" in items:
            agreement_scores[party] = items["agreement_score"]
            reasonings[party] = items["reasoning"]
    return agreement_scores, reasonings

def update_scores(party_scores, evaluation, answer):
    """Update scores based on evaluation results and return update log details.
       If the answer is skipped, no update is made.
    """
    if answer.skipped:
        return {}
    try:
        weight = float(answer.wheights)
    except Exception:
        weight = 1.0

    agreement_scores, _ = evaluation
    update_log = {}
    
    for party, score in agreement_scores.items():
        normalized = (score / 100) * 2 - 1
        final_score = normalized * weight
        party_scores[party]["score"] += final_score
        update_log[party] = {
            "raw_score": score,
            "normalized": normalized,
            "weight": weight,
            "mapped_score": final_score,
            "reasoning": evaluation[1].get(party, "")
        }
        print("\n\n\n")
        print(party_scores[party]["score"])
        print("\n\n\n")
    return update_log

def format_final_scores(party_scores):
    """Convert scores to expected output format"""
    return sorted(
        [{**p, "score": party_scores[p["short_name"]]["score"]} for p in default_parties_list],
        key=lambda x: x["score"],
        reverse=True
    )

def get_random_party_scores(user_answers):
    """
    Step-by-step chain of thought for how we want to implement this:
    
    1) We receive the user_answers in the exact format requested. (We do NOT modify it.)
    2) We define a fixed list of parties, each with short_name, full_name, and partyInfo.
    3) For each party, we generate a random integer score between 0 and 100.
    4) We attach that random score to each party.
    5) We sort the list of parties by the generated score in descending order.
    6) We return the transformed list of parties (same fields, just new order and random scores).
    
    We do NOT change the user's input, nor do we alter the key structure of the output.
    The only changes in the output are the random scores and reordering of the parties.
    """
    parties = [
        {
            "score": 0,
            "short_name": "SPD",
            "full_name": "Sozialdemokratische Partei Deutschlands",
            "partyInfo": "The SPD is a social-democratic party advocating for social justice, welfare state expansion, and pro-EU policies."
        },
        {
            "score": 0,
            "short_name": "GRUENE",
            "full_name": "BÜNDNIS 90/DIE GRÜNEN",
            "partyInfo": "The Greens prioritize environmental protection, social justice, human rights, and grassroots democracy."
        },
        {
            "score": 0,
            "short_name": "FDP",
            "full_name": "Freie Demokratische Partei",
            "partyInfo": "The FDP is a liberal party focusing on free markets, individual rights, lower taxes, and pro-business policies."
        },
        {
            "score": 0,
            "short_name": "CDU/CSU",
            "full_name": "Christlich Demokratische Union Deutschlands",
            "partyInfo": "The CDU/CSU is a center-right political alliance with a focus on social market economy, European integration, and conservative values."
        },
        {
            "score": 0,
            "short_name": "LINKE",
            "full_name": "DIE LINKE",
            "partyInfo": "DIE LINKE is a left-wing party emphasizing anti-capitalism, social equality, wealth redistribution, and pacifism."
        },
        {
            "score": 0,
            "short_name": "AFD",
            "full_name": "Alternative für Deutschland",
            "partyInfo": "The AfD is a right-wing populist party, critical of the EU and immigration, with a focus on national sovereignty."
        }
    ]

    # Generate random scores for each party
    for party in parties:
        party["score"] = random.randint(0, 100)

    # Sort parties by score descending
    parties_sorted = sorted(parties, key=lambda x: x["score"], reverse=True)

    # Return the newly sorted and scored list
    return parties_sorted



from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom_answer_evaluation")

class CustomAnswer(BaseModel):
    question: str
    question_id: int
    users_answer: int
    wheights: str
    Skipped: str
    custom_answer: str

class EvaluationRequest(BaseModel):
    custom_answers: List[CustomAnswer]










@router.post("/")
async def evaluate_custom_answers(request: EvaluationRequest):
    try:
        print("\n\n\n")

        logger.info("Received evaluation request")
        print("\n\n\n")

        custom_answers = request.custom_answers
        
        # Convert custom answers to the format expected by get_custom_answers_evaluation
        questionnaire_questions = [
            QuestionnaireQuestion(q=answer.question, id=answer.question_id)
            for answer in custom_answers
        ]
        
        user_answers = [
            UserAnswer(
                custom_answer=answer.custom_answer,
                users_answer=str(answer.users_answer),
                wheights=answer.wheights,
                skipped=answer.Skipped.lower() == "true"
            )
            for answer in custom_answers
        ]

        print("\n\n\n")
        logger.info("Starting evaluation process")
        print("\n\n\n")

        # Call the actual evaluation function
        evaluation_results = await get_custom_answers_evaluation(
            questionnaire_questions,
            user_answers
        )
        print("\n\n\n")
        logger.info("Evaluation completed successfully")
        print("\n\n\n")

        # logger.debug(f"Evaluation results: {evaluation_results}")
        
        # Convert to the expected format
        formatted_results = [
            {
                "short_name": party["short_name"],
                "score": party["score"],
                "full_name": party["full_name"],
                "partyInfo": party["partyInfo"]
            }
            for party in evaluation_results
        ]
        
        logger.info("Returning formatted results")
        print(json.dumps(formatted_results, indent=4))
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error during evaluation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def calculate_evaluation_scores(raw_scores: dict, weight_input: str) -> dict:
    """Convert raw LLM scores to weighted evaluation scores"""
    try:
        # Handle 'false' string from frontend
        if weight_input.lower() == 'false':
            weight = 1.0
        else:
            weight = float(weight_input)
    except (ValueError, AttributeError):
        weight = 1.0  # Default to neutral weight
    
    evaluation_scores = {}
    
    for party, data in raw_scores.items():
        raw_score = data.get('agreement_score', 50)
        # Convert 0-100 score to -1 to +1 range with weight
        normalized = ((raw_score / 100) * 2 - 1) * weight
        evaluation_scores[party] = {
            'normalized_score': normalized,
            'raw_score': raw_score,
            'weight': weight
        }
    return evaluation_scores