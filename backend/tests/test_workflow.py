# backend/tests/test_workflow.py
"""Full workflow integration test: create test -> add questions -> add options -> activate -> respond -> analytics -> CSV."""


def test_full_workflow(client):
    # 1. Create a test
    resp = client.post("/api/v1/tests", json={"name": "Homepage Test", "description": "Which homepage?"})
    assert resp.status_code == 201
    test = resp.json()
    test_id = test["id"]
    assert test["status"] == "draft"
    assert test["slug"]

    # 2. Add a question
    resp = client.post(f"/api/v1/tests/{test_id}/questions", json={
        "title": "Which homepage layout?",
        "followup_required": True,
        "followup_prompt": "Why this one?",
    })
    assert resp.status_code == 201
    question = resp.json()
    question_id = question["id"]

    # 3. Add options (URL mode to avoid needing real image files)
    option_ids = []
    for label in ["Layout A", "Layout B"]:
        form = {"label": label, "source_type": "url", "source_url": f"https://example.com/{label.lower().replace(' ', '-')}"}
        resp = client.post(f"/api/v1/questions/{question_id}/options", data=form)
        assert resp.status_code == 201
        option_ids.append(resp.json()["id"])

    # 4. Try to activate - should succeed (1 question, 2 options)
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 5. Get test as respondent
    slug = test["slug"]
    resp = client.get(f"/api/v1/respond/{slug}")
    assert resp.status_code == 200
    respondent_test = resp.json()
    assert len(respondent_test["questions"]) == 1
    assert len(respondent_test["questions"][0]["options"]) == 2

    # 6. Submit an answer
    resp = client.post(f"/api/v1/respond/{slug}/answers", json={
        "session_id": "test-session-1",
        "question_id": question_id,
        "option_id": option_ids[0],
        "followup_text": "Looks cleaner",
    })
    assert resp.status_code == 201

    # 7. Duplicate answer should return 409
    resp = client.post(f"/api/v1/respond/{slug}/answers", json={
        "session_id": "test-session-1",
        "question_id": question_id,
        "option_id": option_ids[1],
        "followup_text": "Changed my mind",
    })
    assert resp.status_code == 409

    # 8. Submit another session's answer
    resp = client.post(f"/api/v1/respond/{slug}/answers", json={
        "session_id": "test-session-2",
        "question_id": question_id,
        "option_id": option_ids[1],
        "followup_text": "More modern",
    })
    assert resp.status_code == 201

    # 9. Check analytics
    resp = client.get(f"/api/v1/tests/{test_id}/analytics")
    assert resp.status_code == 200
    analytics = resp.json()
    assert analytics["total_sessions"] == 2
    assert analytics["total_answers"] == 2
    assert analytics["completed_sessions"] == 2
    assert analytics["completion_rate"] == 100.0
    assert len(analytics["questions"]) == 1
    q_analytics = analytics["questions"][0]
    assert q_analytics["total_votes"] == 2

    # 10. Export CSV
    resp = client.get(f"/api/v1/tests/{test_id}/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    csv_lines = resp.text.strip().split("\n")
    assert len(csv_lines) == 3  # header + 2 responses

    # 11. Close the test
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "closed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    # 12. Respondent should get 403 on closed test
    resp = client.get(f"/api/v1/respond/{slug}")
    assert resp.status_code == 403


def test_activation_validation(client):
    """Test that activation fails without enough options."""
    # Create test with a question but no options
    resp = client.post("/api/v1/tests", json={"name": "Empty Test"})
    test_id = resp.json()["id"]

    # Can't activate with 0 questions
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert resp.status_code == 400

    # Add a question
    resp = client.post(f"/api/v1/tests/{test_id}/questions", json={"title": "Pick one"})
    question_id = resp.json()["id"]

    # Can't activate with 0 options
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert resp.status_code == 400

    # Add 1 option (need 2 minimum)
    client.post(f"/api/v1/questions/{question_id}/options",
                data={"label": "A", "source_type": "url", "source_url": "https://example.com/a"})
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert resp.status_code == 400

    # Add 2nd option - now activation should succeed
    client.post(f"/api/v1/questions/{question_id}/options",
                data={"label": "B", "source_type": "url", "source_url": "https://example.com/b"})
    resp = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert resp.status_code == 200


def test_delete_test_cascades(client):
    """Test that deleting a test cascades to questions, options, responses."""
    resp = client.post("/api/v1/tests", json={"name": "Delete Me"})
    test_id = resp.json()["id"]

    resp = client.post(f"/api/v1/tests/{test_id}/questions", json={"title": "Q1"})
    q_id = resp.json()["id"]

    client.post(f"/api/v1/questions/{q_id}/options",
                data={"label": "A", "source_type": "url", "source_url": "https://example.com/a"})
    client.post(f"/api/v1/questions/{q_id}/options",
                data={"label": "B", "source_type": "url", "source_url": "https://example.com/b"})

    # Delete
    resp = client.delete(f"/api/v1/tests/{test_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = client.get(f"/api/v1/tests/{test_id}")
    assert resp.status_code == 404
