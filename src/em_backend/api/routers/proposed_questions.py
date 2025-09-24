from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.api.routers.v2 import get_database_session
from em_backend.database.crud import proposed_question as proposed_question_crud
from em_backend.database.models import Party
from em_backend.models.crud import (
    ProposedQuestionCreate,
    ProposedQuestionResponse,
    ProposedQuestionUpdate,
)

router = APIRouter(prefix="/proposed-questions", tags=["proposed-questions"])


@router.post("/")
async def create_proposed_question(
    question_in: ProposedQuestionCreate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProposedQuestionResponse:
    """Create a new proposed question."""
    # Ensure party exists
    party = await db.get(Party, question_in.party_id)

    if party is None:
        raise HTTPException(status_code=404, detail="Party not found.")
    question = await proposed_question_crud.create(
        db, obj_in=question_in.model_dump() | {"party": party}
    )
    return ProposedQuestionResponse.model_validate(question)


@router.get("/")
async def read_proposed_questions(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[ProposedQuestionResponse]:
    """Retrieve proposed questions with pagination."""
    questions = await proposed_question_crud.get_multi(db, skip=skip, limit=limit)
    return [ProposedQuestionResponse.model_validate(question) for question in questions]


@router.get("/{question_id}")
async def read_proposed_question(
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProposedQuestionResponse:
    """Retrieve a specific proposed question by ID."""
    question = await proposed_question_crud.get(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")
    return ProposedQuestionResponse.model_validate(question)


@router.put("/{question_id}")
async def update_proposed_question(
    question_id: UUID,
    question_in: ProposedQuestionUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProposedQuestionResponse:
    """Update a proposed question."""
    question = await proposed_question_crud.get(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")

    update_data = question_in.model_dump(exclude_unset=True)
    updated_question = await proposed_question_crud.update(
        db, db_obj=question, obj_in=update_data
    )
    return ProposedQuestionResponse.model_validate(updated_question)


@router.delete("/{question_id}")
async def delete_proposed_question(
    question_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict[str, str]:
    """Delete a proposed question."""
    question = await proposed_question_crud.remove(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")

    return {"message": "Proposed question deleted successfully"}
