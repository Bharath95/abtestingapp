# backend/app/services/image_service.py
import shutil
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image
from app.config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_PIXELS, MEDIA_DIR, THUMBNAIL_MAX_WIDTH


def validate_image(file: UploadFile) -> None:
    """Validate image file type."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF.",
        )


async def save_image(file: UploadFile, test_id: int) -> tuple[str, str]:
    """Save uploaded image and generate thumbnail. Returns (uuid_filename, original_filename).

    Reads file in a bounded manner to prevent memory bombs, then validates
    with Image.verify() to reject spoofed non-image files. Checks pixel count
    to prevent decompression bombs. Skips thumbnail generation for GIFs to
    preserve animation.
    """
    validate_image(file)

    # Read file content with bounded read to prevent memory bomb.
    content = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size is {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB.",
        )

    # Generate UUID filename
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".png"
    uuid_name = f"{uuid.uuid4()}{ext}"
    thumb_name = f"thumb_{uuid_name}"

    # Create test directory
    test_dir = MEDIA_DIR / str(test_id)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Save original
    original_path = test_dir / uuid_name
    original_path.write_bytes(content)

    # Validate with Pillow's Image.verify() to reject spoofed files
    try:
        with Image.open(original_path) as img:
            img.verify()
    except Exception:
        original_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="File is not a valid image.",
        )

    # Decompression bomb guard: check pixel count after verify passes
    try:
        with Image.open(original_path) as img:
            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                original_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Image dimensions too large ({width}x{height}). Maximum is {MAX_IMAGE_PIXELS} pixels.",
                )
    except HTTPException:
        raise
    except Exception:
        original_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Failed to read image dimensions.",
        )

    # Generate thumbnail (skip for GIFs to preserve animation)
    is_gif = ext in {".gif"}
    if not is_gif:
        try:
            with Image.open(original_path) as img:
                if img.width > THUMBNAIL_MAX_WIDTH:
                    ratio = THUMBNAIL_MAX_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((THUMBNAIL_MAX_WIDTH, new_height), Image.LANCZOS)
                    img_resized.save(test_dir / thumb_name)
                else:
                    # Image is already small enough, copy as thumbnail
                    shutil.copy2(original_path, test_dir / thumb_name)
        except Exception:
            # If thumbnail generation fails, copy the original
            shutil.copy2(original_path, test_dir / thumb_name)
    # For GIFs, no thumbnail is generated; serve the original directly.

    return uuid_name, file.filename or "unknown"


def delete_image(test_id: int, filename: str) -> None:
    """Delete image and its thumbnail from disk."""
    test_dir = MEDIA_DIR / str(test_id)
    original = test_dir / filename
    thumbnail = test_dir / f"thumb_{filename}"
    if original.exists():
        original.unlink()
    if thumbnail.exists():
        thumbnail.unlink()


def delete_test_media(test_id: int) -> None:
    """Delete entire media directory for a test."""
    test_dir = MEDIA_DIR / str(test_id)
    if test_dir.exists():
        shutil.rmtree(test_dir)


def get_image_url(test_id: int, filename: str | None) -> str | None:
    """Construct the URL path for an image."""
    if not filename:
        return None
    return f"/media/{test_id}/{filename}"


def get_thumbnail_url(test_id: int, filename: str | None) -> str | None:
    """Construct the URL path for a thumbnail. For GIFs, returns the original URL."""
    if not filename:
        return None
    if filename.lower().endswith(".gif"):
        return f"/media/{test_id}/{filename}"
    return f"/media/{test_id}/thumb_{filename}"
