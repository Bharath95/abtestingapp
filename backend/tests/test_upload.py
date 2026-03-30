# backend/tests/test_upload.py
"""Tests for image upload, file cleanup, and URL validation."""
import io
from pathlib import Path
from PIL import Image


def _create_test_image(width=100, height=100, format="PNG") -> io.BytesIO:
    """Create a minimal valid test image."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def _setup_draft_test_with_question(client):
    """Helper: create a draft test with one question, return (test_id, question_id)."""
    res = client.post("/api/v1/tests", json={"name": "Upload Test"})
    assert res.status_code == 201
    test_id = res.json()["id"]

    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Upload question"},
    )
    assert res.status_code == 201
    question_id = res.json()["id"]

    return test_id, question_id


def test_valid_image_upload(client, test_media_dir):
    """Step 1: Valid image upload succeeds."""
    test_id, question_id = _setup_draft_test_with_question(client)

    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Uploaded Option", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option = res.json()
    assert option["source_type"] == "upload"
    assert option["image_url"] is not None
    assert option["image_url"].startswith(f"/media/{test_id}/")


def test_invalid_mime_type(client, test_media_dir):
    """Step 2: Invalid MIME type returns 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Bad Option", "source_type": "upload"},
        files={"image": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert res.status_code == 400
    assert "Invalid image type" in res.json()["detail"]


def test_oversized_file(client, test_media_dir):
    """Step 3: Oversized file returns 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create a file larger than 10MB
    large_content = b"x" * (10 * 1024 * 1024 + 1)
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Large Option", "source_type": "upload"},
        files={"image": ("large.png", io.BytesIO(large_content), "image/png")},
    )
    assert res.status_code == 400
    assert "too large" in res.json()["detail"]


def test_source_type_transition_upload_to_url(client, test_media_dir):
    """Step 4: Transition from upload to URL clears image, sets source_url."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create upload option
    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Transition Option", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option_id = res.json()["id"]
    assert res.json()["image_url"] is not None

    # Switch to URL
    res = client.patch(
        f"/api/v1/options/{option_id}",
        data={"source_type": "url", "source_url": "https://example.com/design"},
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "url"
    assert res.json()["source_url"] == "https://example.com/design"
    assert res.json()["image_url"] is None


def test_source_type_transition_url_to_upload(client, test_media_dir):
    """Step 5: Transition from URL to upload clears source_url, sets image."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create URL option
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "URL Option", "source_type": "url", "source_url": "https://example.com/a"},
    )
    assert res.status_code == 201
    option_id = res.json()["id"]

    # Switch to upload
    img_buf = _create_test_image()
    res = client.patch(
        f"/api/v1/options/{option_id}",
        data={"source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "upload"
    assert res.json()["image_url"] is not None
    assert res.json()["source_url"] is None


def test_option_delete_cleans_up_files(client, test_media_dir):
    """Step 6: Deleting an upload option removes files from disk."""
    test_id, question_id = _setup_draft_test_with_question(client)

    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Delete Me", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option = res.json()
    image_url = option["image_url"]  # e.g., /media/1/uuid.png

    # Extract filename from URL
    filename = image_url.split("/")[-1]
    test_dir = test_media_dir / str(test_id)

    # Verify files exist on disk
    assert (test_dir / filename).exists()
    assert (test_dir / f"thumb_{filename}").exists()

    # Delete option
    res = client.delete(f"/api/v1/options/{option['id']}")
    assert res.status_code == 204

    # Verify files removed from disk
    assert not (test_dir / filename).exists()
    assert not (test_dir / f"thumb_{filename}").exists()


def test_url_scheme_javascript_rejected(client, test_media_dir):
    """Step 7: javascript: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "XSS Option", "source_type": "url", "source_url": "javascript:alert(1)"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]


def test_url_scheme_data_rejected(client, test_media_dir):
    """Step 8: data: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Data Option", "source_type": "url", "source_url": "data:text/html,<script>alert(1)</script>"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]


def test_url_scheme_file_rejected(client, test_media_dir):
    """Step 9: file: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "File Option", "source_type": "url", "source_url": "file:///etc/passwd"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]
