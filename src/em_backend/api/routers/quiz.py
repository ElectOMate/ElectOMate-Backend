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
    QuestionnaireResult,
    QuestionnaireAnswer,
    PartyRanking,
)
from sqlalchemy import select, func

router = APIRouter(prefix="/quiz", tags=["quiz"])

# Storage directory for questionnaire results
# Path: quiz.py -> routers -> api -> em_backend -> src -> /app (mono-repo root)
QUESTIONNAIRE_RESULTS_FOLDER = Path(__file__).parent.parent.parent.parent.parent / "Questionaire_Results_Folder"

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


# ===== Questionnaire Results Upload Endpoint =====

class QuestionAnswer(BaseModel):
    """A single question and its answer."""
    question_number: int = Field(description="The question number/ID")
    question_text: str = Field(description="The full text of the question")
    answer: str = Field(description="User's answer: yes, no, neutral, or skipped")
    weight_enabled: bool = Field(description="Whether the user enabled weight for this question")
    custom_answer: str | None = Field(default=None, description="Optional custom text answer")


class PartyRankingData(BaseModel):
    """A single party's ranking result."""
    party_short_name: str = Field(description="Short name of the party (e.g., 'CDU', 'SPD')")
    party_full_name: str = Field(description="Full name of the party")
    score: float = Field(description="Match percentage (0-100)")
    rank: int = Field(description="Position in ranking (1 = highest match)")


class QuestionnaireResultUpload(BaseModel):
    """Upload model for complete questionnaire results."""
    user_id: str = Field(description="Persistent anonymous user identifier")
    country_code: str | None = Field(default=None, description="Country code for the questionnaire")
    questions: list[QuestionAnswer] = Field(description="List of all questions and answers")
    party_rankings: list[PartyRankingData] | None = Field(default=None, description="Calculated party rankings (optional)")
    submitted_at: str = Field(description="ISO timestamp of submission")


class QuestionnaireResultResponse(BaseModel):
    """Response after uploading questionnaire results."""
    message: str = Field(description="Success message")
    result_id: str = Field(description="Unique identifier for the uploaded results")
    file_path: str | None = Field(default=None, description="Path where the results were saved")


@router.post("/upload-results")
async def upload_questionnaire_results(
    results: QuestionnaireResultUpload,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> QuestionnaireResultResponse:
    """
    Upload complete questionnaire results for anonymous research.

    This endpoint accepts the user's full questionnaire answers and stores them
    both in a JSON file and in the database.

    The stored data includes:
    - Question numbers and text
    - User's answers (yes/no/neutral/skipped)
    - Upload timestamp
    - Anonymous persistent user ID
    """
    # Generate a unique result ID
    result_id = str(uuid.uuid4())

    # Parse the submitted_at timestamp
    submitted_at_datetime = datetime.fromisoformat(results.submitted_at.replace('Z', '+00:00'))

    # Calculate metadata
    metadata = {
        "total_questions": len(results.questions),
        "answered_questions": sum(1 for q in results.questions if q.answer != "skipped"),
        "weighted_questions": sum(1 for q in results.questions if q.weight_enabled),
        "custom_answers": sum(1 for q in results.questions if q.custom_answer),
    }

    # Save to JSON file (non-critical, don't fail if it errors)
    file_path = None
    try:
        # Ensure the results folder exists
        QUESTIONNAIRE_RESULTS_FOLDER.mkdir(parents=True, exist_ok=True, mode=0o777)

        # Create timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id_prefix = results.user_id[:8]  # First 8 chars of user ID
        filename = f"{timestamp}_{user_id_prefix}_{result_id[:8]}.json"
        file_path = QUESTIONNAIRE_RESULTS_FOLDER / filename

        # Prepare data to save
        data_to_save = {
            "result_id": result_id,
            "user_id": results.user_id,
            "country_code": results.country_code,
            "submitted_at": results.submitted_at,
            "questions": [q.model_dump() for q in results.questions],
            "party_rankings": [r.model_dump() for r in results.party_rankings] if results.party_rankings else [],
            "metadata": metadata,
        }

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        print(f"[QUESTIONNAIRE] Saved questionnaire results to {file_path}")

    except Exception as e:
        print(f"[QUESTIONNAIRE] Failed to save questionnaire results to file: {e}")
        file_path = None

    # Save questionnaire results to database (critical operation)
    try:
        # Create QuestionnaireResult instance
        questionnaire_result = QuestionnaireResult(
            result_id=result_id,
            user_id=results.user_id,
            submitted_at=submitted_at_datetime,
            total_questions=metadata["total_questions"],
            answered_questions=metadata["answered_questions"],
            weighted_questions=metadata["weighted_questions"],
            custom_answers_count=metadata["custom_answers"],
            country_code=results.country_code,
        )

        # Create QuestionnaireAnswer instances for each question
        for question in results.questions:
            questionnaire_answer = QuestionnaireAnswer(
                question_number=question.question_number,
                question_text=question.question_text,
                answer=question.answer,
                weight_enabled=question.weight_enabled,
                custom_answer=question.custom_answer,
            )
            questionnaire_result.questions.append(questionnaire_answer)

        # Create PartyRanking instances if provided
        if results.party_rankings:
            for ranking in results.party_rankings:
                party_ranking = PartyRanking(
                    party_short_name=ranking.party_short_name,
                    party_full_name=ranking.party_full_name,
                    score=ranking.score,
                    rank=ranking.rank,
                )
                questionnaire_result.party_rankings.append(party_ranking)

            print(f"[QUESTIONNAIRE] Added {len(results.party_rankings)} party rankings to submission")

        # Add to database (transaction will auto-commit via dependency)
        db.add(questionnaire_result)

        print(f"[QUESTIONNAIRE] Saved questionnaire results to database: {questionnaire_result.id}")

        return QuestionnaireResultResponse(
            message="Questionnaire results uploaded successfully",
            result_id=result_id,
            file_path=str(file_path.relative_to(QUESTIONNAIRE_RESULTS_FOLDER.parent)) if file_path and file_path.exists() else None,
        )

    except Exception as e:
        print(f"[QUESTIONNAIRE] Failed to save questionnaire results to database: {e}")
        import traceback
        traceback.print_exc()

        # Return error since database save is critical
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save questionnaire results: {str(e)}"
        )


# ===== Party Ranking Heatmap Analytics Endpoint =====

class RankDistribution(BaseModel):
    """Distribution of a party across different ranking positions."""
    party_short_name: str = Field(description="Short name of the party")
    party_full_name: str = Field(description="Full name of the party")
    rank_counts: dict[int, int] = Field(description="Count of submissions for each rank position")
    rank_percentages: dict[int, float] = Field(description="Percentage of submissions for each rank position")


class PartyRankingHeatmapResponse(BaseModel):
    """Response containing heatmap data for party ranking distributions."""
    country_code: str | None = Field(description="Country code filter (if applied)")
    total_submissions: int = Field(description="Total number of questionnaire submissions analyzed")
    parties: list[str] = Field(description="List of party names (y-axis)")
    rank_positions: list[int] = Field(description="List of ranking positions (x-axis, e.g., [1, 2, 3, 4, 5])")
    heatmap_matrix: list[list[float]] = Field(
        description="2D matrix of percentages. Each row = party, each column = rank position"
    )
    party_details: list[RankDistribution] = Field(description="Detailed breakdown per party")


@router.get("/ranking-heatmap")
async def get_ranking_heatmap(
    country_code: str | None = None,
    db: Annotated[AsyncSession, Depends(get_database_session)] = None,
) -> PartyRankingHeatmapResponse:
    """
    Get party ranking distribution for heatmap visualization.

    This endpoint calculates how often each party appears at each ranking position.
    For example: "Partido Comunista ranked 1st in 45% of submissions, 2nd in 30%, etc."

    Args:
        country_code: Optional 2-letter country code to filter results (e.g., 'CL', 'DE')

    Returns:
        Heatmap data with:
        - parties: List of party names for y-axis
        - rank_positions: List of ranks for x-axis (1, 2, 3, ...)
        - heatmap_matrix: 2D array where matrix[party_index][rank_index] = percentage
    """
    try:
        # Build base query
        query = select(
            PartyRanking.party_short_name,
            PartyRanking.party_full_name,
            PartyRanking.rank,
            func.count(PartyRanking.id).label('count')
        )

        # Filter by country if provided
        if country_code:
            query = query.join(
                QuestionnaireResult,
                PartyRanking.questionnaire_result_id == QuestionnaireResult.id
            ).where(
                QuestionnaireResult.country_code == country_code.upper()
            )

        # Group by party and rank
        query = query.group_by(
            PartyRanking.party_short_name,
            PartyRanking.party_full_name,
            PartyRanking.rank
        ).order_by(
            PartyRanking.party_short_name,
            PartyRanking.rank
        )

        result = await db.execute(query)
        rows = result.all()

        if not rows:
            return PartyRankingHeatmapResponse(
                country_code=country_code,
                total_submissions=0,
                parties=[],
                rank_positions=[],
                heatmap_matrix=[],
                party_details=[]
            )

        # Calculate total submissions (unique questionnaire results with rankings)
        total_query = select(func.count(func.distinct(PartyRanking.questionnaire_result_id)))
        if country_code:
            total_query = total_query.select_from(PartyRanking).join(
                QuestionnaireResult,
                PartyRanking.questionnaire_result_id == QuestionnaireResult.id
            ).where(
                QuestionnaireResult.country_code == country_code.upper()
            )
        total_result = await db.execute(total_query)
        total_submissions = total_result.scalar() or 0

        # Organize data by party
        party_data = {}
        all_ranks = set()

        for row in rows:
            party_name = row.party_short_name
            party_full = row.party_full_name
            rank = row.rank
            count = row.count

            all_ranks.add(rank)

            if party_name not in party_data:
                party_data[party_name] = {
                    'full_name': party_full,
                    'rank_counts': {},
                    'rank_percentages': {}
                }

            party_data[party_name]['rank_counts'][rank] = count
            percentage = (count / total_submissions * 100) if total_submissions > 0 else 0
            party_data[party_name]['rank_percentages'][rank] = round(percentage, 1)

        # Sort parties and ranks
        parties = sorted(party_data.keys())
        rank_positions = sorted(all_ranks)

        # Build heatmap matrix (percentage values)
        heatmap_matrix = []
        party_details = []

        for party in parties:
            row = []
            for rank in rank_positions:
                percentage = party_data[party]['rank_percentages'].get(rank, 0.0)
                row.append(percentage)

            heatmap_matrix.append(row)

            party_details.append(RankDistribution(
                party_short_name=party,
                party_full_name=party_data[party]['full_name'],
                rank_counts=party_data[party]['rank_counts'],
                rank_percentages=party_data[party]['rank_percentages']
            ))

        print(f"[HEATMAP] Generated heatmap for {len(parties)} parties, {len(rank_positions)} ranks, {total_submissions} submissions (country={country_code})")

        return PartyRankingHeatmapResponse(
            country_code=country_code,
            total_submissions=total_submissions,
            parties=parties,
            rank_positions=rank_positions,
            heatmap_matrix=heatmap_matrix,
            party_details=party_details
        )

    except Exception as e:
        print(f"[HEATMAP] Error generating ranking heatmap: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate ranking heatmap: {str(e)}"
        )


# ===== Question Answer Statistics Endpoint =====

class AnswerDistribution(BaseModel):
    """Distribution of answers for a single question."""
    yes: float = Field(description="Percentage of users who answered 'yes'")
    no: float = Field(description="Percentage of users who answered 'no'")
    neutral: float = Field(description="Percentage of users who answered 'neutral'")
    skipped: float = Field(description="Percentage of users who answered 'skipped'")


class QuestionStatistics(BaseModel):
    """Statistics for a single question."""
    question_number: int = Field(description="The question number/ID")
    question_text: str = Field(description="The full text of the question")
    answer_distribution: AnswerDistribution = Field(description="Percentage distribution of answers")
    user_answer: str | None = Field(default=None, description="The current user's answer (yes/no/neutral/skipped)")
    total_responses: int = Field(description="Total number of responses for this question")


class QuestionStatisticsResponse(BaseModel):
    """Response containing answer statistics for all questions."""
    country_code: str | None = Field(description="Country code filter (if applied)")
    user_id: str | None = Field(description="User ID for which statistics were requested")
    total_submissions: int = Field(description="Total number of questionnaire submissions analyzed")
    questions: list[QuestionStatistics] = Field(description="Statistics for each question")


@router.get("/question-statistics")
async def get_question_statistics(
    country_code: str | None = None,
    user_id: str | None = None,
    db: Annotated[AsyncSession, Depends(get_database_session)] = None,
) -> QuestionStatisticsResponse:
    """
    Get answer distribution statistics for all questionnaire questions.

    This endpoint calculates what percentage of users answered yes/no/neutral/skipped
    for each question, filtered by country. It also returns the specified user's
    own answers to each question.

    Args:
        country_code: Optional 2-letter country code to filter results (e.g., 'CL', 'DE')
        user_id: Optional user ID to fetch their specific answers

    Returns:
        Statistics with:
        - questions: List of question statistics with answer distributions
        - For each question: percentage breakdown of yes/no/neutral/skipped answers
        - user_answer: The specific user's answer if user_id is provided
    """
    try:
        # Normalize country_code to uppercase
        if country_code:
            country_code = country_code.upper()

        # Build query to get all questionnaire answers with country filter
        query = select(QuestionnaireAnswer).join(
            QuestionnaireResult,
            QuestionnaireAnswer.questionnaire_result_id == QuestionnaireResult.id
        )

        # Apply country filter if provided
        if country_code:
            query = query.where(QuestionnaireResult.country_code == country_code)

        result = await db.execute(query)
        all_answers = result.scalars().all()

        if not all_answers:
            return QuestionStatisticsResponse(
                country_code=country_code,
                user_id=user_id,
                total_submissions=0,
                questions=[]
            )

        # Calculate total unique submissions
        total_query = select(func.count(func.distinct(QuestionnaireResult.id))).select_from(
            QuestionnaireResult
        )
        if country_code:
            total_query = total_query.where(QuestionnaireResult.country_code == country_code)

        total_result = await db.execute(total_query)
        total_submissions = total_result.scalar() or 0

        # Group answers by question_number
        question_data = {}
        for answer in all_answers:
            q_num = answer.question_number
            if q_num not in question_data:
                question_data[q_num] = {
                    'question_text': answer.question_text,
                    'answers': {'yes': 0, 'no': 0, 'neutral': 0, 'skipped': 0},
                    'total': 0
                }

            # Count this answer
            answer_type = answer.answer.lower()
            if answer_type in question_data[q_num]['answers']:
                question_data[q_num]['answers'][answer_type] += 1
                question_data[q_num]['total'] += 1

        # Fetch user's specific answers if user_id is provided
        user_answers = {}
        if user_id:
            user_query = select(QuestionnaireAnswer, QuestionnaireResult.submitted_at).join(
                QuestionnaireResult,
                QuestionnaireAnswer.questionnaire_result_id == QuestionnaireResult.id
            ).where(
                QuestionnaireResult.user_id == user_id
            )

            if country_code:
                user_query = user_query.where(QuestionnaireResult.country_code == country_code)

            # Order by submitted_at desc to get the most recent submission
            user_query = user_query.order_by(QuestionnaireResult.submitted_at.desc())

            user_result = await db.execute(user_query)
            user_answer_rows = user_result.all()

            # Group by question_number and take the first (most recent) answer for each
            for answer, _ in user_answer_rows:
                if answer.question_number not in user_answers:
                    user_answers[answer.question_number] = answer.answer.lower()

        # Build response with statistics for each question
        questions_stats = []
        for q_num in sorted(question_data.keys()):
            data = question_data[q_num]
            total = data['total']

            # Calculate percentages
            distribution = AnswerDistribution(
                yes=round((data['answers']['yes'] / total * 100), 1) if total > 0 else 0.0,
                no=round((data['answers']['no'] / total * 100), 1) if total > 0 else 0.0,
                neutral=round((data['answers']['neutral'] / total * 100), 1) if total > 0 else 0.0,
                skipped=round((data['answers']['skipped'] / total * 100), 1) if total > 0 else 0.0,
            )

            questions_stats.append(QuestionStatistics(
                question_number=q_num,
                question_text=data['question_text'],
                answer_distribution=distribution,
                user_answer=user_answers.get(q_num),
                total_responses=total
            ))

        print(f"[QUESTION STATS] Generated statistics for {len(questions_stats)} questions, "
              f"{total_submissions} submissions (country={country_code}, user_id={user_id})")

        # Log detailed question data to debug mixed language issue
        print(f"[QUESTION STATS] Detailed question data:")
        for q in questions_stats:
            print(f"  Q{q.question_number}: {q.question_text[:100]}... (user_answer={q.user_answer}, total={q.total_responses})")

        response = QuestionStatisticsResponse(
            country_code=country_code,
            user_id=user_id,
            total_submissions=total_submissions,
            questions=questions_stats
        )

        # Log the full response being sent to frontend
        print(f"[QUESTION STATS] Sending response with {len(response.questions)} questions")
        import json
        print(f"[QUESTION STATS] Full response data:")
        print(json.dumps({
            "country_code": response.country_code,
            "user_id": response.user_id,
            "total_submissions": response.total_submissions,
            "questions": [
                {
                    "question_number": q.question_number,
                    "question_text": q.question_text[:80] + "..." if len(q.question_text) > 80 else q.question_text,
                    "answer_distribution": {
                        "yes": q.answer_distribution.yes,
                        "no": q.answer_distribution.no,
                        "neutral": q.answer_distribution.neutral,
                        "skipped": q.answer_distribution.skipped,
                    },
                    "user_answer": q.user_answer,
                    "total_responses": q.total_responses,
                }
                for q in response.questions
            ]
        }, indent=2, ensure_ascii=False))

        return response

    except Exception as e:
        print(f"[QUESTION STATS] Error generating question statistics: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate question statistics: {str(e)}"
        )


