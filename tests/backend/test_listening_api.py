import uuid


def test_listening_tests_require_authentication(client):
    response = client.get("/api/v1/listening/tests")
    assert response.status_code == 401


def test_get_listening_test(client, auth_headers, listening_test):
    response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(listening_test)
    assert data["title"] == "IELTS Academic Listening Practice"
    assert data["time_limit_minutes"] == 40
    assert len(data["sections"]) == 2


def test_listening_questions_do_not_expose_answers(
    client, auth_headers, listening_test
):
    response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    assert response.status_code == 200

    questions = [
        question
        for section in response.json()["sections"]
        for question in section["questions"]
    ]
    assert len(questions) == 4
    for question in questions:
        assert "correct_answer" not in question
        assert "explanation" not in question


def test_listening_question_options_are_returned(
    client, auth_headers, listening_test
):
    response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    questions = [
        question
        for section in response.json()["sections"]
        for question in section["questions"]
    ]
    multiple_choice = next(
        question for question in questions
        if question["question_type"] == "multiple_choice"
    )
    assert multiple_choice["options"] == [
        "Delivery", "Collection", "Repair", "Refund"
    ]


def test_start_listening_test(client, auth_headers, listening_test):
    response = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["listening_test_id"] == str(listening_test)
    assert data["attempt_id"]
    assert data["started_at"]


def test_start_unknown_listening_test(client, auth_headers):
    test_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/listening/tests/{test_id}/start",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_get_in_progress_listening_attempt(
    client, auth_headers, listening_test
):
    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]

    response = client.get(
        f"/api/v1/listening/attempts/{attempt_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] is None
    assert data["band_score"] is None
    assert data["answers"] == []
    assert data["total_questions"] == 4


def test_submit_listening_test(
    client, auth_headers, listening_test
):
    test_response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    questions = [
        question
        for section in test_response.json()["sections"]
        for question in section["questions"]
    ]

    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]

    answers = [
        {"question_id": questions[0]["id"], "answer": "Patel"},
        {"question_id": questions[1]["id"], "answer": "Monday"},
        {"question_id": questions[2]["id"], "answer": "Wrong"},
        {"question_id": questions[3]["id"], "answer": "ID"},
    ]
    response = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={"answers": answers},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 3
    assert data["total_questions"] == 4
    assert data["band_score"] == 7.0


def test_submit_listening_test_rejects_empty_answers(
    client, auth_headers, listening_test
):
    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]
    response = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={"answers": []},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "At least one answer is required"


def test_submit_listening_test_rejects_unknown_question(
    client, auth_headers, listening_test
):
    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]
    response = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {"question_id": str(uuid.uuid4()), "answer": "Patel"}
            ]
        },
    )
    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]


def test_submit_listening_test_rejects_duplicate_answers(
    client, auth_headers, listening_test
):
    test_response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    question_id = test_response.json()["sections"][1]["questions"][0]["id"]

    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]
    response = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {"question_id": question_id, "answer": "Patel"},
                {"question_id": question_id, "answer": "Patel"},
            ]
        },
    )
    assert response.status_code == 400
    assert "Duplicate answer" in response.json()["detail"]


def test_listening_attempt_cannot_be_submitted_twice(
    client, auth_headers, listening_test
):
    test_response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    question_id = test_response.json()["sections"][1]["questions"][0]["id"]

    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]
    payload = {
        "answers": [{"question_id": question_id, "answer": "Patel"}]
    }

    first = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json=payload,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json=payload,
    )
    assert second.status_code == 400
    assert "already been submitted" in second.json()["detail"]


def test_listening_attempts_are_isolated_between_users(
    client, auth_headers, second_auth_headers, listening_test
):
    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]

    response = client.get(
        f"/api/v1/listening/attempts/{attempt_id}",
        headers=second_auth_headers,
    )
    assert response.status_code == 404


def test_get_listening_attempt_details(
    client, auth_headers, listening_test
):
    test_response = client.get(
        f"/api/v1/listening/tests/{listening_test}",
        headers=auth_headers,
    )
    questions = [
        question
        for section in test_response.json()["sections"]
        for question in section["questions"]
    ]

    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]

    response = client.post(
        f"/api/v1/listening/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {"question_id": questions[0]["id"], "answer": "Patel"}
            ]
        },
    )
    assert response.status_code == 200

    details = client.get(
        f"/api/v1/listening/attempts/{attempt_id}",
        headers=auth_headers,
    )
    assert details.status_code == 200
    data = details.json()
    assert data["score"] == 1
    assert len(data["answers"]) == 1
    assert data["answers"][0]["is_correct"] is True
    assert data["answers"][0]["correct_answer"] == "Patel"


def test_get_listening_attempts_includes_in_progress(
    client, auth_headers, listening_test
):
    start = client.post(
        f"/api/v1/listening/tests/{listening_test}/start",
        headers=auth_headers,
    )
    attempt_id = start.json()["attempt_id"]

    response = client.get(
        "/api/v1/listening/attempts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    attempt = next(
        item for item in response.json()
        if item["attempt_id"] == attempt_id
    )
    assert attempt["score"] is None
    assert attempt["total_questions"] == 4


def test_listening_attempt_details_require_authentication(client):
    response = client.get(
        f"/api/v1/listening/attempts/{uuid.uuid4()}"
    )
    assert response.status_code in (401, 403)
