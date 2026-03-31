# backend/app/services/analytics_service.py
import csv
import io
from collections import defaultdict
from sqlmodel import Session, func, select, distinct
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.response import AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
from app.services.image_service import get_image_url
from app.utils import sanitize_csv_cell


def compute_analytics(test: Test, session: Session) -> AnalyticsResponse:
    """Compute analytics for a test using batch-fetch to avoid N+1 queries."""
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_ids = [q.id for q in questions]
    if not question_ids:
        return AnalyticsResponse(
            test_id=test.id,
            test_name=test.name,
            total_sessions=0,
            total_answers=0,
            completed_sessions=0,
            completion_rate=0.0,
            questions=[],
        )

    # Batch-fetch all responses for this test in a single query
    all_responses = session.exec(
        select(Response).where(
            Response.screen_question_id.in_(question_ids)
        )
    ).all()

    # Batch-fetch all options for this test's questions in a single query
    all_options = session.exec(
        select(Option).where(
            Option.screen_question_id.in_(question_ids)
        ).order_by(Option.order)
    ).all()

    # Build lookup structures
    options_by_question: dict[int, list[Option]] = defaultdict(list)
    for o in all_options:
        options_by_question[o.screen_question_id].append(o)

    responses_by_question: dict[int, list[Response]] = defaultdict(list)
    all_session_ids: set[str] = set()
    for r in all_responses:
        responses_by_question[r.screen_question_id].append(r)
        all_session_ids.add(r.session_id)

    total_sessions = len(all_session_ids)
    total_answers = len(all_responses)

    # Compute completion rate: sessions that answered ALL questions
    num_questions = len(questions)
    if total_sessions > 0 and num_questions > 0:
        session_question_counts: dict[str, int] = defaultdict(int)
        for r in all_responses:
            session_question_counts[r.session_id] += 1
        completed_sessions = sum(
            1 for count in session_question_counts.values()
            if count >= num_questions
        )
    else:
        completed_sessions = 0

    completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # Build per-question analytics
    question_analytics = []
    for q in questions:
        q_responses = responses_by_question.get(q.id, [])
        q_options = options_by_question.get(q.id, [])
        total_votes = len(q_responses)

        votes_by_option: dict[int, int] = defaultdict(int)
        followups_by_option: dict[int, list[Response]] = defaultdict(list)
        for r in q_responses:
            votes_by_option[r.option_id] += 1
            if r.followup_text:
                followups_by_option[r.option_id].append(r)

        option_analytics = []
        max_votes = max(votes_by_option.values(), default=0)

        for o in q_options:
            votes = votes_by_option.get(o.id, 0)
            percentage = round((votes / total_votes * 100), 1) if total_votes > 0 else 0.0

            option_analytics.append(
                OptionAnalytics(
                    option_id=o.id,
                    label=o.label,
                    source_type=o.source_type,
                    image_url=get_image_url(test.id, o.image_filename),
                    source_url=o.source_url,
                    votes=votes,
                    percentage=percentage,
                    is_winner=(votes == max_votes and max_votes > 0),
                    followup_texts=[
                        FollowUpEntry(text=r.followup_text, created_at=r.created_at)
                        for r in followups_by_option.get(o.id, [])
                    ],
                )
            )

        question_analytics.append(
            QuestionAnalytics(
                question_id=q.id,
                title=q.title,
                total_votes=total_votes,
                options=option_analytics,
            )
        )

    return AnalyticsResponse(
        test_id=test.id,
        test_name=test.name,
        total_sessions=total_sessions,
        total_answers=total_answers,
        completed_sessions=completed_sessions,
        completion_rate=completion_rate,
        questions=question_analytics,
    )


def generate_csv(test: Test, session: Session) -> str:
    """Generate CSV export with sanitized cells and batch-fetched data.

    All string cells are sanitized for CSV injection (cells starting with
    =, +, -, @ are prefixed with a single quote).

    Uses batch-fetch for both options and responses to avoid N+1 queries.
    """
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_ids = [q.id for q in questions]

    # Pre-fetch all options into a lookup dictionary (single query)
    all_options = session.exec(
        select(Option).where(Option.screen_question_id.in_(question_ids))
    ).all() if question_ids else []
    option_lookup = {o.id: o for o in all_options}

    # Batch-fetch all responses for all questions (single query)
    all_responses = session.exec(
        select(Response)
        .where(Response.screen_question_id.in_(question_ids))
        .order_by(Response.created_at)
    ).all() if question_ids else []

    # Group responses by question
    responses_by_question: dict[int, list[Response]] = defaultdict(list)
    for r in all_responses:
        responses_by_question[r.screen_question_id].append(r)

    # Build question lookup for titles
    question_lookup = {q.id: q for q in questions}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["respondent_name", "question_title", "option_label", "followup_text", "session_id", "responded_at"])

    for q in questions:
        q_responses = responses_by_question.get(q.id, [])
        for r in q_responses:
            option = option_lookup.get(r.option_id)
            writer.writerow([
                sanitize_csv_cell(r.respondent_name or "Anonymous"),
                sanitize_csv_cell(q.title),
                sanitize_csv_cell(option.label if option else "Unknown"),
                sanitize_csv_cell(r.followup_text or ""),
                sanitize_csv_cell(r.session_id),
                r.created_at.isoformat(),
            ])

    return output.getvalue()
