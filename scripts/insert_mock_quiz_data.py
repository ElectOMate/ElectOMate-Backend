"""
Script to insert mock quiz submissions into the database.

This creates a realistic distribution of quiz scores with many submissions.
"""
import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from em_backend.database.models import QuizResult, QuizResultAnswer

# Database URL (using 'postgres' as host inside Docker container)
DATABASE_URL = "postgresql+psycopg://postgres:postgres@postgres:5432/em_dev"

# Quiz questions
QUIZ_QUESTIONS = {
    1: "What is the main legislative body in Germany?",
    2: "Who elects the German Chancellor?",
    3: "How many federal states (Bundesländer) does Germany have?",
    4: "What is the minimum percentage a party needs to enter the Bundestag?",
    5: "Which institution represents the federal states at the national level?",
}

QUIZ_OPTIONS = {
    1: ["The Bundesrat", "The Bundestag", "The Federal Constitutional Court", "The Federal President"],
    2: ["The people directly", "The Bundestag", "The Bundesrat", "The Federal Convention"],
    3: ["12", "14", "16", "18"],
    4: ["3%", "5%", "7%", "10%"],
    5: ["The Bundestag", "The Federal Constitutional Court", "The Bundesrat", "The Federal Government"],
}

CORRECT_ANSWERS = {
    1: 1,  # The Bundestag
    2: 1,  # The Bundestag
    3: 2,  # 16
    4: 1,  # 5%
    5: 2,  # The Bundesrat
}


def generate_quiz_score_distribution(num_submissions=500):
    """
    Generate quiz scores following a realistic distribution.

    Most people score between 60-100%, with a peak around 80%.
    """
    scores = []

    # Generate scores with a skewed normal distribution
    for _ in range(num_submissions):
        # Use beta distribution to get scores skewed towards higher values
        # Beta(5, 2) gives a distribution skewed towards 1.0
        beta_value = random.betavariate(5, 2)

        # Convert to score (0-5 questions)
        score_count = int(beta_value * 5)

        # Add some randomness
        if random.random() < 0.1:  # 10% chance of lower scores
            score_count = random.randint(0, 3)

        scores.append(score_count)

    return scores


async def insert_mock_quiz_submissions(num_submissions=500):
    """Insert mock quiz submissions into the database."""

    print(f"Inserting {num_submissions} mock quiz submissions...")

    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Generate score distribution
    score_counts = generate_quiz_score_distribution(num_submissions)

    # Base timestamp (start from 30 days ago)
    base_time = datetime.now() - timedelta(days=30)

    async with async_session() as session:
        # Use Chile country code directly
        country_code = "CL"
        print(f"Using country code: {country_code}")

        # Check if we already have data
        result = await session.execute(select(QuizResult))
        existing_count = len(result.scalars().all())

        if existing_count > 0:
            print(f"Found {existing_count} existing quiz submissions. Deleting them first...")
            await session.execute(text("DELETE FROM quiz_result_answer_table"))
            await session.execute(text("DELETE FROM quiz_result_table"))
            await session.commit()

        for i, correct_count in enumerate(score_counts):
            # Generate timestamp (spread submissions over 30 days)
            timestamp = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            submission_id = str(uuid4())
            score = int((correct_count / 5) * 100)

            # Create QuizResult with Chile country_code
            quiz_result = QuizResult(
                submission_id=submission_id,
                submitted_at=timestamp,
                score=score,
                correct_count=correct_count,
                total_questions=5,
                country_code=country_code,
            )

            # Generate answers for this submission
            correct_questions = random.sample(list(CORRECT_ANSWERS.keys()), correct_count)

            for question_id in QUIZ_QUESTIONS.keys():
                is_correct = question_id in correct_questions

                if is_correct:
                    selected_option = CORRECT_ANSWERS[question_id]
                else:
                    # Select a wrong answer
                    wrong_options = [0, 1, 2, 3]
                    wrong_options.remove(CORRECT_ANSWERS[question_id])
                    selected_option = random.choice(wrong_options)

                selected_letter = chr(65 + selected_option)  # 0->A, 1->B, etc.

                quiz_answer = QuizResultAnswer(
                    question_number=question_id,
                    question_text=QUIZ_QUESTIONS[question_id],
                    selected_answer=selected_letter,
                    selected_answer_text=QUIZ_OPTIONS[question_id][selected_option],
                    is_correct=is_correct,
                )
                quiz_result.answers.append(quiz_answer)

            session.add(quiz_result)

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{num_submissions} submissions inserted")
                await session.commit()

        # Final commit
        await session.commit()
        print(f"✅ Successfully inserted {num_submissions} mock quiz submissions!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(insert_mock_quiz_submissions(500))
