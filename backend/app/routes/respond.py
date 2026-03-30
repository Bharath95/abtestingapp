# backend/app/routes/respond.py
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.test import RespondentTest
from app.schemas.response import AnswerCreate
from app.routes.tests import _build_test_with_questions
from app.limiter import limiter
from app.config import RATE_LIMIT_RESPONDENT

router = APIRouter(prefix="/api/v1/respond", tags=["respondent"])


@router.get("/{slug}", response_model=RespondentTest)
def get_test_for_respondent(slug: str, session: SessionDep):
    test = session.exec(select(Test).where(Test.slug == slug)).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "active":
        raise HTTPException(status_code=403, detail="This test is not currently accepting responses.")

    # Use the shared helper to build nested test data
    question_list = _build_test_with_questions(test, session)

    return RespondentTest(
        id=test.id,
        name=test.name,
        description=test.description,
        questions=question_list,
    )


@router.post("/{slug}/answers", status_code=201)
@limiter.limit(RATE_LIMIT_RESPONDENT)
def submit_answer(slug: str, data: AnswerCreate, session: SessionDep, request: Request):
    """Submit one answer. Rate limited per IP to prevent flooding.

    The @limiter.limit() decorator requires the `request: Request` parameter
    to extract the client IP. The decorator must come AFTER @router.post()
    in reading order (i.e., it is the inner decorator).
    """
    test = session.exec(select(Test).where(Test.slug == slug)).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "active":
        raise HTTPException(status_code=403, detail="This test is not currently accepting responses.")

    # Validate question belongs to this test
    question = session.get(ScreenQuestion, data.question_id)
    if not question or question.test_id != test.id:
        raise HTTPException(status_code=400, detail="Question does not belong to this test.")

    # Validate option belongs to this question
    option = session.get(Option, data.option_id)
    if not option or option.screen_question_id != data.question_id:
        raise HTTPException(status_code=400, detail="Option does not belong to this question.")

    # Validate followup if required
    if question.followup_required and not data.followup_text:
        raise HTTPException(status_code=400, detail="Follow-up text is required for this question.")

    # Insert and catch IntegrityError for duplicate submissions (race-safe)
    response = Response(
        screen_question_id=data.question_id,
        option_id=data.option_id,
        session_id=data.session_id,
        followup_text=data.followup_text,
    )
    session.add(response)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Already answered this question in this session.")

    return {"status": "saved"}
