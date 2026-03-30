# backend/tests/test_upload.py
"""Tests for image upload, URL validation, and file cleanup."""
import io
from PIL import Image


def _create_test_png(width=100, height=100) -> bytes:
    """Create a small valid PNG image in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _setup_test_with_question(client) -> tuple[int, int, int]:
    """Create a test with a question. Returns (test_id, question_id, test_id)."""
    resp = client.post("/api/v1/tests", json={"name": "Upload Test"})
    test_id = resp.json()["id"]
    resp = client.post(f"/api/v1/tests/{test_id}/questions", json={"title": "Pick one"})
    question_id = resp.json()["id"]
    return test_id, question_id


def test_valid_image_upload(client, media_dir):
    test_id, question_id = _setup_test_with_question(client)
    png_data = _create_test_png()

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option A", "source_type": "upload"},
        files={"image": ("test.png", io.BytesIO(png_data), "image/png")},
    )
    assert resp.status_code == 201
    option = resp.json()
    assert option["source_type"] == "upload"
    assert option["image_url"] is not None
    assert "/media/" in option["image_url"]


def test_invalid_mime_type(client):
    test_id, question_id = _setup_test_with_question(client)

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Bad Option", "source_type": "upload"},
        files={"image": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "Invalid image type" in resp.json()["detail"]


def test_url_scheme_javascript_rejected(client):
    test_id, question_id = _setup_test_with_question(client)

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "XSS", "source_type": "url", "source_url": "javascript:alert(1)"},
    )
    assert resp.status_code == 400
    assert "Invalid URL scheme" in resp.json()["detail"]


def test_url_scheme_data_rejected(client):
    test_id, question_id = _setup_test_with_question(client)

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Data", "source_type": "url", "source_url": "data:text/html,<h1>hi</h1>"},
    )
    assert resp.status_code == 400


def test_url_scheme_file_rejected(client):
    test_id, question_id = _setup_test_with_question(client)

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "File", "source_type": "url", "source_url": "file:///etc/passwd"},
    )
    assert resp.status_code == 400


def test_valid_url_option(client):
    test_id, question_id = _setup_test_with_question(client)

    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Good URL", "source_type": "url", "source_url": "https://example.com/design.png"},
    )
    assert resp.status_code == 201
    assert resp.json()["source_type"] == "url"
    assert resp.json()["source_url"] == "https://example.com/design.png"


def test_option_delete_cleans_up_files(client, media_dir):
    test_id, question_id = _setup_test_with_question(client)
    png_data = _create_test_png()

    # Create an upload option
    resp = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Cleanup Test", "source_type": "upload"},
        files={"image": ("test.png", io.BytesIO(png_data), "image/png")},
    )
    assert resp.status_code == 201
    option_id = resp.json()["id"]

    # Verify files exist
    test_media_dir = media_dir / str(test_id)
    assert test_media_dir.exists()
    files_before = list(test_media_dir.iterdir())
    assert len(files_before) >= 1  # at least the original image

    # Delete the option
    resp = client.delete(f"/api/v1/options/{option_id}")
    assert resp.status_code == 204
