# backend/app/routes/tests.py
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select, distinct
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.test import TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail
from app.schemas.screen_question import QuestionPublic
from app.schemas.option import OptionPublic
from app.services.image_service import delete_test_media, get_image_url

router = APIRouter(prefix="/api/v1/tests", tags=["tests"])


def _build_test_with_questions(test: Test, session, schema_class=TestDetail):
    """Shared helper: load a test with its nested questions and options.

    Used by both get_test (designer) and get_test_for_respondent to avoid
    duplicated query logic. Uses batch-fetch for options (single query for
    all questions) to avoid N+1 queries.
    """
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    if not questions:
        return []

    # Batch-fetch ALL options for ALL questions in a single query
    question_ids = [q.id for q in questions]
    all_options = session.exec(
        select(Option)
        .where(Option.screen_question_id.in_(question_ids))
        .order_by(Option.order)
    ).all()

    # Group options by question ID
    options_by_question: dict[int, list[Option]] = defaultdict(list)
    for o in all_options:
        options_by_question[o.screen_question_id].append(o)

    question_list = []
    for q in questions:
        q_options = options_by_question.get(q.id, [])
        option_list = [
            OptionPublic(
                id=o.id,
                label=o.label,
                source_type=o.source_type,
                image_url=get_image_url(test.id, o.image_filename),
                source_url=o.source_url,
                order=o.order,
                created_at=o.created_at,
            )
            for o in q_options
        ]
        question_list.append(
            QuestionPublic(
                id=q.id,
                order=q.order,
                title=q.title,
                followup_prompt=q.followup_prompt,
                followup_required=q.followup_required,
                randomize_options=q.randomize_options,
                options=option_list,
            )
        )

    return question_list


@router.post("", response_model=TestPublic, status_code=201)
def create_test(data: TestCreate, session: SessionDep):
    test = Test.model_validate(data)
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


@router.get("", response_model=list[TestListItem])
def list_tests(session: SessionDep):
    """List all tests with question and response counts.

    Uses a single query with JOINs and GROUP BY to avoid N+1 queries.
    """
    stmt = (
        select(
            Test,
            func.count(distinct(ScreenQuestion.id)).label("question_count"),
            func.count(distinct(Response.session_id)).label("response_count"),
        )
        .outerjoin(ScreenQuestion, ScreenQuestion.test_id == Test.id)
        .outerjoin(Response, Response.screen_question_id == ScreenQuestion.id)
        .group_by(Test.id)
        .order_by(col(Test.created_at).desc())
    )
    results = session.exec(stmt).all()

    return [
        TestListItem(
            id=test.id,
            slug=test.slug,
            name=test.name,
            description=test.description,
            status=test.status,
            created_at=test.created_at,
            updated_at=test.updated_at,
            question_count=q_count,
            response_count=r_count,
        )
        for test, q_count, r_count in results
    ]


@router.get("/{test_id}", response_model=TestDetail)
def get_test(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    question_list = _build_test_with_questions(test, session)

    return TestDetail(
        id=test.id,
        slug=test.slug,
        name=test.name,
        description=test.description,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        questions=question_list,
    )


VALID_TRANSITIONS = {
    ("draft", "active"),
    ("draft", "closed"),
    ("active", "closed"),
}


@router.patch("/{test_id}", response_model=TestPublic)
def update_test(test_id: int, data: TestUpdate, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    update_data = data.model_dump(exclude_unset=True)

    # Enforce lifecycle rules
    if "status" in update_data:
        new_status = update_data["status"]
        if (test.status, new_status) not in VALID_TRANSITIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{test.status}' to '{new_status}'.",
            )
        # Validate activation requirements
        if new_status == "active":
            questions = session.exec(
                select(ScreenQuestion).where(ScreenQuestion.test_id == test_id)
            ).all()
            if len(questions) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot activate test with no questions.",
                )
            for q in questions:
                option_count = session.exec(
                    select(func.count()).where(Option.screen_question_id == q.id)
                ).one()
                if option_count < 2:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question '{q.title}' needs at least 2 options to activate.",
                    )
                if option_count > 5:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question '{q.title}' has more than 5 options (max 5).",
                    )

    # If test is active or closed, only name/description/status can change
    if test.status in ("active", "closed"):
        allowed = {"name", "description", "status"}
        disallowed = set(update_data.keys()) - allowed
        if disallowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot modify {disallowed} on a {test.status} test.",
            )

    for key, value in update_data.items():
        setattr(test, key, value)
    test.updated_at = datetime.now(timezone.utc)
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


@router.delete("/{test_id}", status_code=204)
def delete_test(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    # Commit DB delete first, then remove files (ensures DB consistency)
    session.delete(test)
    session.commit()
    delete_test_media(test_id)
    return None
