# backend/app/routes/questions.py
from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.schemas.screen_question import QuestionCreate, QuestionUpdate, QuestionPublic
from app.schemas.option import OptionPublic
from app.services.image_service import get_image_url, delete_image

router = APIRouter(tags=["questions"])


def _require_draft(session: SessionDep, test_id: int) -> Test:
    """Helper: fetch test and verify it is in draft status."""
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "draft":
        raise HTTPException(status_code=403, detail="Cannot modify questions on a non-draft test.")
    return test


def _question_to_public(question: ScreenQuestion, session: SessionDep) -> QuestionPublic:
    """Convert a ScreenQuestion model to its public schema."""
    options = session.exec(
        select(Option).where(Option.screen_question_id == question.id).order_by(Option.order)
    ).all()
    option_list = [
        OptionPublic(
            id=o.id,
            label=o.label,
            source_type=o.source_type,
            image_url=get_image_url(question.test_id, o.image_filename),
            source_url=o.source_url,
            order=o.order,
            created_at=o.created_at,
        )
        for o in options
    ]
    return QuestionPublic(
        id=question.id,
        order=question.order,
        title=question.title,
        followup_prompt=question.followup_prompt,
        followup_required=question.followup_required,
        randomize_options=question.randomize_options,
        options=option_list,
    )


@router.post("/api/v1/tests/{test_id}/questions", response_model=QuestionPublic, status_code=201)
def create_question(test_id: int, data: QuestionCreate, session: SessionDep):
    _require_draft(session, test_id)

    # Auto-assign order as max + 1
    max_order = session.exec(
        select(func.max(ScreenQuestion.order)).where(ScreenQuestion.test_id == test_id)
    ).one()
    next_order = (max_order + 1) if max_order is not None else 0

    question = ScreenQuestion(
        test_id=test_id,
        order=next_order,
        title=data.title,
        followup_prompt=data.followup_prompt,
        followup_required=data.followup_required,
        randomize_options=data.randomize_options,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return _question_to_public(question, session)


@router.patch("/api/v1/questions/{question_id}", response_model=QuestionPublic)
def update_question(question_id: int, data: QuestionUpdate, session: SessionDep):
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    _require_draft(session, question.test_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)
    session.add(question)
    session.commit()
    session.refresh(question)
    return _question_to_public(question, session)


@router.delete("/api/v1/questions/{question_id}", status_code=204)
def delete_question(question_id: int, session: SessionDep):
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    test = _require_draft(session, question.test_id)

    # Clean up image files for all options before cascade delete
    options = session.exec(
        select(Option).where(Option.screen_question_id == question.id)
    ).all()
    files_to_delete = [
        (test.id, o.image_filename)
        for o in options
        if o.image_filename
    ]

    session.delete(question)
    session.commit()

    # Delete image files after DB commit
    for test_id, filename in files_to_delete:
        delete_image(test_id, filename)

    return None
