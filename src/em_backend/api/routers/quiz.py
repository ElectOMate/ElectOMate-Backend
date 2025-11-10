import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.api.routers.v2 import get_database_session
from em_backend.database.models import (
    QuizResult,
    QuizResultAnswer,
)
from sqlalchemy import select, func

router = APIRouter(prefix="/quiz", tags=["quiz"])

# Storage directory for quiz results
QUIZ_RESULTS_FOLDER = Path(__file__).parent.parent.parent.parent.parent / "Quiz_Results_Folder"

# Correct answers for quiz questions (hardcoded for security)
CORRECT_ANSWERS = {
    1: 1,  # The Bundestag
    2: 1,  # The Bundestag
    3: 2,  # 16
    4: 1,  # 5%
    5: 2,  # The Bundesrat
}

# Question texts (from frontend JSON files)
QUIZ_QUESTIONS = {
    1: "What is the main legislative body in Germany?",
    2: "Who elects the German Chancellor?",
    3: "How many federal states (Bundesländer) does Germany have?",
    4: "What is the minimum percentage a party needs to enter the Bundestag?",
    5: "Which institution represents the federal states at the national level?",
}

# Question options (from frontend JSON files)
QUIZ_OPTIONS = {
    1: ["The Bundesrat", "The Bundestag", "The Federal Constitutional Court", "The Federal President"],
    2: ["The people directly", "The Bundestag", "The Bundesrat", "The Federal Convention"],
    3: ["12", "14", "16", "18"],
    4: ["3%", "5%", "7%", "10%"],
    5: ["The Bundestag", "The Federal Constitutional Court", "The Bundesrat", "The Federal Government"],
}


# API Models
class QuizAnswer(BaseModel):
    """A single answer submission."""
    question_id: int = Field(description="The ID of the question")
    selected_option: int = Field(description="The index of the selected option (0-based)")


class QuizSubmission(BaseModel):
    """Quiz submission with all answers."""
    answers: list[QuizAnswer] = Field(description="List of all answers")
    country_code: str = Field(default="CL", description="2-letter country code (defaults to 'CL' for Chile)")


class AnswerDetail(BaseModel):
    """Details about a single answer."""
    question_id: int = Field(description="The ID of the question")
    selected_option: int = Field(description="The option selected by user (0-based)")
    correct_option: int = Field(description="The correct option (0-based)")
    is_correct: bool = Field(description="Whether the answer was correct")


class ScoreDistributionPoint(BaseModel):
    """A single point in the score distribution curve."""
    score: int = Field(description="Score percentage (0-100)")
    count: int = Field(description="Number of people who got this score")


class QuizSubmissionResponse(BaseModel):
    """Response after submitting quiz."""
    message: str = Field(description="Success message")
    submission_id: str = Field(description="Unique submission identifier")
    score: int = Field(description="User's score as percentage (0-100)")
    total_questions: int = Field(description="Total number of questions")
    correct_count: int = Field(description="Number of correct answers")
    answer_details: list[AnswerDetail] = Field(description="Details for each answer")
    score_distribution: list[ScoreDistributionPoint] = Field(
        description="Distribution of scores across all users"
    )


@router.post("/submit")
async def submit_quiz(
    submission: QuizSubmission,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> QuizSubmissionResponse:
    """
    Submit quiz results and calculate score.

    Questions are loaded from frontend JSON files (locales_Germany/en.json, de.json).
    This endpoint evaluates the answers, calculates the score, and returns results with distribution.
    """
    # Generate a session ID for this quiz submission
    session_id = str(uuid.uuid4())

    # Normalize country_code to uppercase
    country_code = submission.country_code.upper() if submission.country_code else None

    # Calculate score and build answer details
    answer_details = []
    correct_count = 0

    for answer in submission.answers:
        question_id = answer.question_id
        selected_option = answer.selected_option
        correct_option = CORRECT_ANSWERS.get(question_id, 0)
        is_correct = selected_option == correct_option

        if is_correct:
            correct_count += 1

        answer_details.append(
            AnswerDetail(
                question_id=question_id,
                selected_option=selected_option,
                correct_option=correct_option,
                is_correct=is_correct,
            )
        )

    total_questions = len(submission.answers)
    score = int((correct_count / total_questions) * 100) if total_questions > 0 else 0

    # Save quiz results to JSON file
    try:
        # Ensure the quiz results folder exists
        QUIZ_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

        # Create timestamp-based filename
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_{timestamp_str}_{session_id[:8]}.json"
        file_path = QUIZ_RESULTS_FOLDER / filename

        # Prepare quiz answers with full details
        quiz_answers = []
        for answer in submission.answers:
            question_id = answer.question_id
            selected_option = answer.selected_option

            # Convert option index to letter (A, B, C, D)
            selected_letter = chr(65 + selected_option)  # 0->A, 1->B, 2->C, 3->D

            quiz_answers.append({
                "question_number": question_id,
                "question_text": QUIZ_QUESTIONS.get(question_id, "Unknown question"),
                "selected_answer": selected_letter,
                "selected_answer_text": QUIZ_OPTIONS.get(question_id, [])[selected_option] if question_id in QUIZ_OPTIONS and selected_option < len(QUIZ_OPTIONS[question_id]) else "Unknown",
                "is_correct": selected_option == CORRECT_ANSWERS.get(question_id, -1),
            })

        # Prepare data to save
        data_to_save = {
            "submission_id": session_id,
            "submitted_at": timestamp.isoformat(),
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "answers": quiz_answers,
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        print(f"[QUIZ] Saved quiz results to {file_path}")

    except Exception as e:
        print(f"[QUIZ] Failed to save quiz results: {e}")
        # Don't fail the request if file saving fails

    # Save quiz results to database
    try:
        # Create QuizResult instance
        quiz_result = QuizResult(
            submission_id=session_id,
            submitted_at=timestamp,
            score=score,
            correct_count=correct_count,
            total_questions=total_questions,
            country_code=country_code,
        )

        # Create QuizResultAnswer instances for each answer
        for answer_data in quiz_answers:
            quiz_answer = QuizResultAnswer(
                question_number=answer_data["question_number"],
                question_text=answer_data["question_text"],
                selected_answer=answer_data["selected_answer"],
                selected_answer_text=answer_data["selected_answer_text"],
                is_correct=answer_data["is_correct"],
            )
            quiz_result.answers.append(quiz_answer)

        # Add to database (will auto-commit when function returns)
        db.add(quiz_result)
        await db.flush()  # Flush to get the ID without committing

        print(f"[QUIZ] Saved quiz results to database: {quiz_result.id}")

    except Exception as e:
        print(f"[QUIZ] Failed to save quiz results to database: {e}")
        # Don't fail the request if database saving fails

    # Calculate real score distribution from database
    # Filter by country if country_code is provided
    try:
        # Query all quiz results for this country and count by score
        query = select(QuizResult.score, func.count(QuizResult.id))
        if country_code is not None:
            query = query.where(QuizResult.country_code == country_code)
        query = query.group_by(QuizResult.score).order_by(QuizResult.score)

        result = await db.execute(query)
        score_counts = dict(result.all())

        # Create granular distribution with a data point for each possible score (0, 20, 40, 60, 80, 100)
        # Since we have 5 questions, possible scores are: 0%, 20%, 40%, 60%, 80%, 100%
        possible_scores = [0, 20, 40, 60, 80, 100]
        distribution = [
            ScoreDistributionPoint(
                score=s,
                count=score_counts.get(s, 0)  # Use 0 if no submissions with that score
            )
            for s in possible_scores
        ]

        print(f"[QUIZ] Score distribution: {distribution}")

    except Exception as e:
        print(f"[QUIZ] Failed to calculate distribution: {e}")
        # Fallback to empty distribution
        distribution = [
            ScoreDistributionPoint(score=s, count=0)
            for s in [0, 20, 40, 60, 80, 100]
        ]

    return QuizSubmissionResponse(
        message="Quiz submitted successfully",
        submission_id=session_id,
        score=score,
        total_questions=total_questions,
        correct_count=correct_count,
        answer_details=answer_details,
        score_distribution=distribution,
    )
