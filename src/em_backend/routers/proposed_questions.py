from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import proposed_question as proposed_question_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    ProposedQuestionCreate,
    ProposedQuestionResponse,
    ProposedQuestionUpdate,
    ProposedQuestionWithParty,
)

router = APIRouter(prefix="/proposed-questions", tags=["proposed-questions"])


@router.post("/", response_model=ProposedQuestionResponse)
async def create_proposed_question(
    question_in: ProposedQuestionCreate,
    db: AsyncSession = Depends(get_database_session),
) -> ProposedQuestionResponse:
    """Create a new proposed question."""
    try:
        question = await proposed_question_crud.create(
            db, obj_in=question_in.model_dump()
        )
        await db.commit()
        return ProposedQuestionResponse.model_validate(question)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=list[ProposedQuestionResponse])
async def read_proposed_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[ProposedQuestionResponse]:
    """Retrieve proposed questions with pagination."""
    questions = await proposed_question_crud.get_multi(db, skip=skip, limit=limit)
    return [ProposedQuestionResponse.model_validate(question) for question in questions]


@router.get("/{question_id}", response_model=ProposedQuestionResponse)
async def read_proposed_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ProposedQuestionResponse:
    """Retrieve a specific proposed question by ID."""
    question = await proposed_question_crud.get(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")
    return ProposedQuestionResponse.model_validate(question)


@router.get("/{question_id}/with-party", response_model=ProposedQuestionWithParty)
async def read_proposed_question_with_party(
    question_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ProposedQuestionWithParty:
    """Retrieve a specific proposed question with party information."""
    question = await proposed_question_crud.get_with_relationships(
        db, id=question_id, relationships=["party"]
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")
    return ProposedQuestionWithParty.model_validate(question)


@router.put("/{question_id}", response_model=ProposedQuestionResponse)
async def update_proposed_question(
    question_id: UUID,
    question_in: ProposedQuestionUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> ProposedQuestionResponse:
    """Update a proposed question."""
    question = await proposed_question_crud.get(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")

    try:
        update_data = question_in.model_dump(exclude_unset=True)
        updated_question = await proposed_question_crud.update(
            db, db_obj=question, obj_in=update_data
        )
        await db.commit()
        return ProposedQuestionResponse.model_validate(updated_question)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{question_id}")
async def delete_proposed_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete a proposed question."""
    question = await proposed_question_crud.remove(db, id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Proposed question not found")

    try:
        await db.commit()
        return {"message": "Proposed question deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
