# backend/tests/test_workflow.py
"""Full workflow integration test: create test -> add questions -> add options -> activate -> respond -> analytics."""


def test_full_workflow(client):
    # 1. Create a test
    res = client.post("/api/v1/tests", json={"name": "My Test", "description": "A test"})
    assert res.status_code == 201
    test = res.json()
    test_id = test["id"]
    slug = test["slug"]
    assert test["status"] == "draft"

    # 2. Add a question
    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Which design?", "followup_required": True},
    )
    assert res.status_code == 201
    question = res.json()
    question_id = question["id"]

    # 3. Add options using source_type=url (no image files needed in test)
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option A", "source_type": "url", "source_url": "https://example.com/a", "order": "0"},
    )
    assert res.status_code == 201
    opt_a = res.json()
    option_a_id = opt_a["id"]
    assert opt_a["source_type"] == "url"
    assert opt_a["source_url"] == "https://example.com/a"

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option B", "source_type": "url", "source_url": "https://example.com/b", "order": "1"},
    )
    assert res.status_code == 201
    option_b_id = res.json()["id"]

    # 4. Activate the test
    res = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert res.status_code == 200
    assert res.json()["status"] == "active"

    # 5. Cannot add questions to active test
    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Another question"},
    )
    assert res.status_code == 403

    # 6. Respondent gets the test
    res = client.get(f"/api/v1/respond/{slug}")
    assert res.status_code == 200
    assert res.json()["name"] == "My Test"
    assert len(res.json()["questions"]) == 1

    # 7. Submit answer
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-1",
            "question_id": question_id,
            "option_id": option_a_id,
            "followup_text": "I liked it",
        },
    )
    assert res.status_code == 201

    # 8. Duplicate answer rejected (IntegrityError-based)
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-1",
            "question_id": question_id,
            "option_id": option_b_id,
            "followup_text": "Changed my mind",
        },
    )
    assert res.status_code == 409

    # 9. Second respondent
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-2",
            "question_id": question_id,
            "option_id": option_b_id,
            "followup_text": "Better colors",
        },
    )
    assert res.status_code == 201

    # 10. Analytics
    res = client.get(f"/api/v1/tests/{test_id}/analytics")
    assert res.status_code == 200
    analytics = res.json()
    assert analytics["total_sessions"] == 2
    assert analytics["total_answers"] == 2
    assert analytics["completed_sessions"] == 2
    assert analytics["completion_rate"] == 100.0
    assert len(analytics["questions"]) == 1
    q_analytics = analytics["questions"][0]
    assert q_analytics["total_votes"] == 2
    votes = {o["label"]: o["votes"] for o in q_analytics["options"]}
    assert votes["Option A"] == 1
    assert votes["Option B"] == 1

    # 11. CSV export
    res = client.get(f"/api/v1/tests/{test_id}/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    csv_text = res.text
    assert "Which design?" in csv_text
    assert "Option A" in csv_text

    # 12. Close the test
    res = client.patch(f"/api/v1/tests/{test_id}", json={"status": "closed"})
    assert res.status_code == 200
    assert res.json()["status"] == "closed"

    # 13. Respondent cannot submit to closed test
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-3",
            "question_id": question_id,
            "option_id": option_a_id,
            "followup_text": "Too late",
        },
    )
    assert res.status_code == 403
