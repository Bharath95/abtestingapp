# backend/app/routes/options.py
from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from sqlmodel import func, select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.schemas.option import OptionPublic
from app.services.image_service import save_image, delete_image, get_image_url
from app.utils import validate_source_url

router = APIRouter(tags=["options"])


def _require_draft_for_question(session: SessionDep, question_id: int) -> ScreenQuestion:
    """Fetch question and verify its parent test is draft."""
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    test = session.get(Test, question.test_id)
    if not test or test.status != "draft":
        raise HTTPException(status_code=403, detail="Cannot modify options on a non-draft test.")
    return question


def _option_to_public(option: Option, test_id: int) -> OptionPublic:
    return OptionPublic(
        id=option.id,
        label=option.label,
        source_type=option.source_type,
        image_url=get_image_url(test_id, option.image_filename),
        source_url=option.source_url,
        order=option.order,
        created_at=option.created_at,
    )


@router.post("/api/v1/questions/{question_id}/options", response_model=OptionPublic, status_code=201)
async def create_option(
    question_id: int,
    session: SessionDep,
    label: str = Form(..., max_length=200),
    source_type: str = Form(default="upload"),
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    source_url: str | None = Form(default=None),
):
    question = _require_draft_for_question(session, question_id)

    # Enforce max 5 options per question
    current_count = session.exec(
        select(func.count()).where(Option.screen_question_id == question_id)
    ).one()
    if current_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 options per question.")

    # Validate source_type
    if source_type not in ("upload", "url"):
        raise HTTPException(status_code=400, detail="source_type must be 'upload' or 'url'.")

    # Auto-assign order
    if order is None:
        max_order = session.exec(
            select(func.max(Option.order)).where(Option.screen_question_id == question_id)
        ).one()
        order = (max_order or -1) + 1

    image_filename = None
    original_filename = None
    option_source_url = None

    if source_type == "upload":
        if not image or not image.filename:
            raise HTTPException(status_code=400, detail="Image file is required for upload mode.")
        image_filename, original_filename = await save_image(image, question.test_id)
    elif source_type == "url":
        if not source_url or not source_url.strip():
            raise HTTPException(status_code=400, detail="source_url is required for URL mode.")
        option_source_url = validate_source_url(source_url)

    option = Option(
        screen_question_id=question_id,
        label=label,
        source_type=source_type,
        image_filename=image_filename,
        original_filename=original_filename,
        source_url=option_source_url,
        order=order,
    )
    session.add(option)
    session.commit()
    session.refresh(option)
    return _option_to_public(option, question.test_id)


@router.patch("/api/v1/options/{option_id}", response_model=OptionPublic)
async def update_option(
    option_id: int,
    session: SessionDep,
    label: str | None = Form(default=None, max_length=200),
    source_type: str | None = Form(default=None),
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    source_url: str | None = Form(default=None),
):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    # Validate label is not empty if provided
    if label is not None and label.strip() == "":
        raise HTTPException(status_code=400, detail="Label cannot be empty.")
    if label is not None:
        option.label = label

    if order is not None:
        option.order = order

    # Track old image for post-commit cleanup
    old_image_filename = None

    # Handle source_type transitions
    if source_type is not None:
        if source_type not in ("upload", "url"):
            raise HTTPException(status_code=400, detail="source_type must be 'upload' or 'url'.")

        if source_type != option.source_type:
            # Source type is changing
            if source_type == "url":
                # Switching from upload to URL
                if not source_url or not source_url.strip():
                    raise HTTPException(status_code=400, detail="source_url is required for URL mode.")
                validated_url = validate_source_url(source_url)
                old_image_filename = option.image_filename
                option.source_type = "url"
                option.source_url = validated_url
                option.image_filename = None
                option.original_filename = None
            elif source_type == "upload":
                # Switching from URL to upload
                if not image or not image.filename:
                    raise HTTPException(status_code=400, detail="Image file is required for upload mode.")
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
                option.source_type = "upload"
                option.source_url = None
        else:
            # Same source_type, update fields within the same mode
            if source_type == "url" and source_url is not None:
                option.source_url = validate_source_url(source_url)
            if source_type == "upload" and image and image.filename:
                # Save new image first, track old for deletion
                old_image_filename = option.image_filename
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
    else:
        # No source_type change; handle image replacement within current mode
        if image and image.filename:
            if option.source_type == "upload":
                # Save new image first, track old for deletion
                old_image_filename = option.image_filename
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
        if source_url is not None and option.source_type == "url":
            option.source_url = validate_source_url(source_url)

    session.add(option)
    session.commit()
    session.refresh(option)

    # Delete old image files after successful commit
    if old_image_filename:
        delete_image(question.test_id, old_image_filename)

    return _option_to_public(option, question.test_id)


@router.delete("/api/v1/options/{option_id}", status_code=204)
def delete_option(option_id: int, session: SessionDep):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    # Track file for post-commit cleanup
    image_to_delete = option.image_filename

    session.delete(option)
    session.commit()

    # Delete image from disk after DB commit
    if image_to_delete:
        delete_image(question.test_id, image_to_delete)

    return None
