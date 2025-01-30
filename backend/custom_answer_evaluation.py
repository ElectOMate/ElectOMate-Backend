# custom_answer_evaluation.py

import random
import json
import asyncio
from collections import defaultdict
from typing import List
from backend.models import QuestionnaireQuestion, UserAnswer
from backend.assets.questionnaire_party_answers import questionnaire_party_answers
from backend.clients import AzureOpenAIClientManager
from backend.prompts.eval_prompts import EVALUATION_PROMPT, GENERATE_LOOKUP_PROMPT, EVALUATION_PROMPT2

classication_to_score = {"strongly disagree" : -1, "disagree" : -0.5, "neutral" : 0, "agree" : 0.5, "strongly agree" : 1}

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

async def compare_user_response_to_party(question_id : int, question: str, 
                                         main_parties: List[str], smaller_parties: List[str],
                                         party_responses: List[str], 
                                         user_response: str, main_contexts: List[str],
                                         smaller_contexts: List[str],
                                         openai_client: AzureOpenAIClientManager
                                         ):
    """
    Compares a user's custom response to a party's response using an LLM. Creates a classification of agreement and provides concise reasoning.
    """
    
    # TODO: fetch the smaller parties contexts
    messages = EVALUATION_PROMPT2.invoke({"question" : question, "main_parties" : main_parties, "party_responses" : 
                                          party_responses, "user_response" : user_response, "smaller_parties": smaller_parties, "main_contexts": main_contexts, "smaller_contexts": smaller_contexts})
    evaluation_response = openai_client.get_chat_client().invoke(messages)
    try:
        evaluation_dict = json.loads(evaluation_response.content)
        agreement_scores = {}
        reasonings = {}
        for party, items in evaluation_dict.items():
            if "agreement_score" not in items or "reasoning" not in items:
                return None
            agreement_scores[party] = items["agreement_score"]
            reasonings[party] = items["reasoning"]
        return question_id, agreement_scores, reasonings
    
    except:
        print("Failed Parsing Agreement Score Responses with Response Content: ", evaluation_response.content)
        return None

# Fetches the RAG prompts needed to do the context lookups in the party programmes for better evaluation of the custom answers
async def getRAGPrompts(question: QuestionnaireQuestion, answer: UserAnswer,  openai_client: AzureOpenAIClientManager):
    
    messages = GENERATE_LOOKUP_PROMPT.invoke({"question" : question.q, "custom_answer" : answer.custom_answer})
    lookup_response = openai_client.get_embedding_client().invoke(messages)
    
    try:
        lookup_dict = json.loads(lookup_response.content)
        if "lookupPrompts" not in lookup_dict or len(lookup_dict["lookupPrompts"]) < 1:
            return None
        return lookup_dict["lookupPrompts"] # Python List
    except:
        print("Failed Parsing Lookup Prompt with Response Content: ", lookup_response.content)
        return None
    
        

async def get_custom_answers_evaluation(questionnaire_questions: List[QuestionnaireQuestion], 
                                  custom_answers: List[UserAnswer], 
                                  openai_client: AzureOpenAIClientManager
                                  ):
    """
    Creates a similarity score of the users to each party based on their questionnaire responses. 
    If a custom answer is provided will use an LLM to rank the similarity to the party's stance on the issue.
    """
    
    
    parties_list = []
    question_to_responses = {}
    
    # task = asyncio.create_task(compare_user_response_to_party(i, question.q, party, party_response, answer.custom_answer, openai_client))
    for i, (question, answer) in enumerate(zip(questionnaire_questions, custom_answers)):
        if answer.custom_answer == "":
            continue
        
        
        party_to_response = questionnaire_party_answers[i]
        if len(parties_list) < 1:
            parties_list = [k for k, v in party_to_response.items()]
        parties = parties_list 
        
        # TODO: Split parties into main and smaller
        main_parties = ["SPD", ..., "AfD"] 
        smaller_parties = ["Tierpartei", ..., "Piratenpartei"]

        party_responses = [v for k, v in party_to_response.items()]
       
        # TODO: Implement the actual retrieval of information with the prompts
        lookupPrompts = getRAGPrompts(question, answer, openai_client=openai_client)
        main_contexts = {
            "SPD": ["", ..., ""],
            # ...
            "AfD": ["", ..., ""]
        }
        
        # TODO: Implement the fetching of the smaller parties' descriptions
        smaller_contexts = {
            "Tierpartei": "Tiere und so",
            # ...
            "Piratenpartei": "Piraten und so"
        }

        resp = await compare_user_response_to_party(question_id=i, question=question, 
                                         main_parties=main_parties, smaller_parties=smaller_parties,
                                         party_responses=party_responses, 
                                         user_response=answer, main_contexts=main_contexts,
                                         smaller_contexts=smaller_contexts,
                                         openai_client=openai_client
                                         )
        if resp is None:
            print("Failed parsing the LLMs response to generate the agreement scores")
            return
        else:
            _, agreement_scores, reasonings = resp
    
        question_to_responses[i] = {
            "question": question,
            "user_answer": answer,
            "agreement_scores": agreement_scores,
            "reasonings": reasonings
        } 

    # Only count questions that have a response for every party
    question_to_responses = {q : response_dicts for q, response_dicts in question_to_responses.items() if len(response_dicts) == len(parties_list)}
    if len(question_to_responses) == 0:
        print("No valid custom evaluation.")
        return parties_list
    
    # TODO: Here the implementation basically aggregates a score from all the scores obtained from the questions
    # However what we want to do is to output the scores for each single question
    
    # The other question is also how to aggregate the button scores with the scores
    
    return question_to_responses
    
    print(f"Number of valid custom questions to evaluate {len(question_to_responses)}")
   
    # Sort parties by score descending
    parties_sorted = sorted(parties_list, key=lambda x: x["score"], reverse=True)

    # Return the newly sorted and scored list
    return parties_sorted


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