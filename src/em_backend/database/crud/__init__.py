from em_backend.database.crud.base import CRUDBase
from em_backend.database.models import (
    Candidate,
    Country,
    Document,
    Election,
    Party,
    ProposedQuestion,
    QuizQuestion,
    QuizResult,
    QuizResultAnswer,
    QuizSubmission,
)

country = CRUDBase(Country)
election = CRUDBase(Election)
party = CRUDBase(Party)
candidate = CRUDBase(Candidate)
document = CRUDBase(Document)
proposed_question = CRUDBase(ProposedQuestion)
quiz_question = CRUDBase(QuizQuestion)
quiz_submission = CRUDBase(QuizSubmission)
quiz_result = CRUDBase(QuizResult)
quiz_result_answer = CRUDBase(QuizResultAnswer)
