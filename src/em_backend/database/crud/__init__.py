from em_backend.crud.base import CRUDBase
from em_backend.database.models import (
    Candidate,
    Country,
    Document,
    Election,
    Party,
    ProposedQuestion,
)

country = CRUDBase(Country)
election = CRUDBase(Election)
party = CRUDBase(Party)
candidate = CRUDBase(Candidate)
document = CRUDBase(Document)
proposed_question = CRUDBase(ProposedQuestion)
