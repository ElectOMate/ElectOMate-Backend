from fastapi import APIRouter, HTTPException

from em_backend.models import EvaluationRequest, QuestionnaireQuestion, UserAnswer
from em_backend.custom_answers.custom_answers import get_custom_answers_evaluation


import logging

router = APIRouter()

@router.post("/custom_answer_evaluation")
async def evaluate_custom_answers(request: EvaluationRequest):
    try:
        logging.debug("Received evaluation request")

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

        logging.debug("Starting evaluation process")

        # Call the actual evaluation function
        evaluation_results = await get_custom_answers_evaluation(
            questionnaire_questions,
            user_answers
        )
        logging.debug("Evaluation completed successfully")

        
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
        
        logging.debug("Returning formatted results")
        return formatted_results
        
    except Exception as e:
        logging.error(f"Error during evaluation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))