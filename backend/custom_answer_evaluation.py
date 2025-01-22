import random
import json
import asyncio
from collections import defaultdict
from typing import List
from backend.models import QuestionnaireQuestion, UserAnswer
from backend.assets.questionnaire_party_answers import questionnaire_party_answers
from backend.clients import AzureOpenAIClientManager
from backend.prompts.eval_prompts import EVALUATION_PROMPT

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

async def compare_user_response_to_party(question_id : int, question: str, 
                                         party: str, party_response: str, 
                                         user_response: str, openai_client: AzureOpenAIClientManager
                                         ):
    """
    Compares a user's custom response to a party's response using an LLM. Creates a classification of agreement and provides concise reasoning.
    """
    messages = EVALUATION_PROMPT.invoke({"question" : question, "party" : party, "party_response" : 
                                          party_response, "user_response" : user_response})
    evaluation_response = openai_client.get_chat_client().invoke(messages)
    try:
        evaluation_dict = json.loads(evaluation_response.content)
        if "agreement_classification" not in evaluation_dict or "reasoning" not in evaluation_dict:
            return None
        
        if evaluation_dict["agreement_classification"] in classication_to_score:
            evaluation_dict["agreement_score"] = classication_to_score[evaluation_dict["agreement_classification"]]
        else:
            return None
        evaluation_dict["question_id"] = question_id
        evaluation_dict["party"] = party

        return evaluation_dict
    except:
        print("Failed Parsing with Response Content: ", evaluation_response.content)
        return None
        

async def get_custom_answers_evaluation(questionnaire_questions: List[QuestionnaireQuestion], 
                                  custom_answers: List[UserAnswer], 
                                  openai_client: AzureOpenAIClientManager
                                  ):
    """
    Creates a similarity score of the users to each party based on their questionnaire responses. 
    If a custom answer is provided will use an LLM to rank the similarity to the party's stance on the issue.
    """
    
    tasks = []
    responses = []
    parties = set()

    for i, (question, answer) in enumerate(zip(questionnaire_questions, custom_answers)):
        if answer.custom_answer == "":
            continue
    
        party_to_response = questionnaire_party_answers[i]
        for party, party_response in party_to_response.items():
            parties.add(party)
            task = asyncio.create_task(compare_user_response_to_party(i, question.q, party, party_response, answer.custom_answer, openai_client))
            tasks.append(task)
            
    responses = await asyncio.gather(*tasks)

    question_to_responses = defaultdict(list)
    for response_dict in responses:
        if response_dict is None:
            continue
        print(response_dict)
        question_to_responses[response_dict["question_id"]].append(response_dict)

    parties_list = default_parties_list.copy()
    # Only count questions that have a response for every party
    question_to_responses = {q : response_dicts for q, response_dicts in question_to_responses.items() if len(response_dicts) == len(parties)}
    if len(question_to_responses) == 0:
        print("No valid custom evaluation.")
        return parties_list
    
    party_to_score = {p : 0 for p in parties}
    for question_id, response_dict in question_to_responses.items():
        party_to_score[response_dict["party"]] += response_dict["agreement_score"]

    for party_dict in parties_list:
        party_dict["score"] = party_to_score[party_dict["short_name"]] / len(question_to_responses)

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