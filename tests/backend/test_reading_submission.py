import uuid
import pytest

from app.models.passage import Passage
from app.models.reading_question import ReadingQuestion
from app.models.reading_test import ReadingTest

def test_submit_reading_test(
    client,
    auth_headers,
    reading_test,
):
    # Get the test first so we know the question IDs.
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    questions = [
        question
        for passage in data["passages"]
        for question in passage["questions"]
    ]

    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    answers = [
        {
            "question_id": questions[0]["id"],
            "answer": "Ethiopia",
        },
        {
            "question_id": questions[1]["id"],
            "answer": "TRUE",
        },
        {
            "question_id": questions[2]["id"],
            "answer": "communication and work",
        },
    ]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={"answers": answers},
    )

    assert response.status_code == 200

    result = response.json()

    assert "attempt_id" in result
    assert result["attempt_id"] == attempt_id
    assert result["score"] == 3
    assert result["total_questions"] == 3
    assert result["band_score"] == 9.0


def test_submit_reading_test_rejects_unknown_question(
    client,
    auth_headers,
    reading_test,
):
    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": str(uuid.uuid4()),
                    "answer": "Ethiopia",
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "does not belong to this test" in response.json()["detail"]


def test_submit_reading_test_rejects_duplicate_answers(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    question_id = data["passages"][0]["questions"][0]["id"]

    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "Ethiopia",
                },
                {
                    "question_id": question_id,
                    "answer": "India",
                },
            ]
        },
    )

    assert response.status_code == 400
    assert "Duplicate answer" in response.json()["detail"]


def test_get_reading_attempts(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    test_data = response.json()

    question_id = test_data["passages"][0]["questions"][0]["id"]

    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "Ethiopia",
                },
            ]
        },
    )

    assert response.status_code == 200

    response = client.get(
        "/api/v1/reading/attempts",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1

    attempt = data[0]

    assert "attempt_id" in attempt
    assert "reading_test_id" in attempt
    assert "score" in attempt
    assert "total_questions" in attempt
    assert "band_score" in attempt
    assert "submitted_at" in attempt

    assert attempt["attempt_id"] == attempt_id
    assert attempt["reading_test_id"] == str(reading_test)
    assert attempt["total_questions"] == 3


def test_get_reading_attempts_requires_authentication(
    client,
):
    response = client.get("/api/v1/reading/attempts")

    assert response.status_code in (401, 403)


def test_submit_reading_test_rejects_empty_submission(
    client,
    auth_headers,
    reading_test,
):
    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": []
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one answer is required"


def test_submit_reading_test_allows_partial_submission(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    questions = [
        question
        for passage in data["passages"]
        for question in passage["questions"]
    ]

    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "answer": "Ethiopia",
                },
            ]
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["attempt_id"] == attempt_id
    assert result["score"] == 1
    assert result["total_questions"] == 3
    assert result["band_score"] == 4.5


def test_reading_attempts_are_isolated_between_users(
    client,
    auth_headers,
    second_auth_headers,
    reading_test,
):
    # User A gets the test.
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    question_id = data["passages"][0]["questions"][0]["id"]

    # User A starts an attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # User A submits an attempt.
    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "Ethiopia",
                }
            ]
        },
    )

    assert response.status_code == 200

    # User B checks attempt history.
    response = client.get(
        "/api/v1/reading/attempts",
        headers=second_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    # User B must not see User A's attempt.
    assert data == []


def test_user_can_submit_reading_test_multiple_times(
    client,
    auth_headers,
    reading_test,
):
    # Get the test and question ID.
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    question_id = data["passages"][0]["questions"][0]["id"]

    # First attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    first_attempt_id = start_response.json()["attempt_id"]

    # First submission.
    response = client.post(
        f"/api/v1/reading/attempts/{first_attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "Ethiopia",
                }
            ]
        },
    )

    assert response.status_code == 200

    assert response.json()["attempt_id"] == first_attempt_id

    # Second attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    second_attempt_id = start_response.json()["attempt_id"]

    # Second submission.
    response = client.post(
        f"/api/v1/reading/attempts/{second_attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "India",
                }
            ]
        },
    )

    assert response.status_code == 200

    assert response.json()["attempt_id"] == second_attempt_id

    # Both submissions must have different attempts.
    assert first_attempt_id != second_attempt_id

    # Check attempt history.
    response = client.get(
        "/api/v1/reading/attempts",
        headers=auth_headers,
    )

    assert response.status_code == 200

    attempts = response.json()

    assert len(attempts) == 2

    attempt_ids = {
        attempt["attempt_id"]
        for attempt in attempts
    }

    assert first_attempt_id in attempt_ids
    assert second_attempt_id in attempt_ids


def test_get_reading_attempt_details(
    client,
    auth_headers,
    reading_test,
):
    # Start the reading attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # Get the test questions.
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    questions = [
        question
        for passage in data["passages"]
        for question in passage["questions"]
    ]

    # Submit the attempt.
    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "answer": "Ethiopia",
                },
                {
                    "question_id": questions[1]["id"],
                    "answer": "FALSE",
                },
                {
                    "question_id": questions[2]["id"],
                    "answer": "communication and work",
                },
            ]
        },
    )

    assert response.status_code == 200

    # Get attempt details.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    result = response.json()

    assert result["attempt_id"] == attempt_id
    assert result["reading_test_id"] == str(reading_test)
    assert result["score"] == 2
    assert result["total_questions"] == 3
    assert result["band_score"] == 6.5
    assert "submitted_at" in result

    assert len(result["answers"]) == 3


def test_get_reading_attempt_details_contains_answer_information(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    questions = [
        question
        for passage in data["passages"]
        for question in passage["questions"]
    ]

    # Start the attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # Submit the attempt.
    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "answer": "Ethiopia",
                },
                {
                    "question_id": questions[1]["id"],
                    "answer": "FALSE",
                },
                {
                    "question_id": questions[2]["id"],
                    "answer": "communication and work",
                },
            ]
        },
    )

    assert response.status_code == 200

    # Get details.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    answers = response.json()["answers"]

    first_answer = next(
        answer
        for answer in answers
        if answer["question_id"] == questions[0]["id"]
    )

    assert first_answer["question_text"] == "Where did coffee originate?"
    assert first_answer["question_type"] == "multiple_choice"
    assert first_answer["user_answer"] == "Ethiopia"
    assert first_answer["correct_answer"] == "Ethiopia"
    assert first_answer["is_correct"] is True


def test_get_reading_attempt_details_marks_incorrect_answers(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    questions = [
        question
        for passage in data["passages"]
        for question in passage["questions"]
    ]

    # Start the attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # Submit incorrect answers.
    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": questions[0]["id"],
                    "answer": "India",
                },
                {
                    "question_id": questions[1]["id"],
                    "answer": "FALSE",
                },
                {
                    "question_id": questions[2]["id"],
                    "answer": "wrong answer",
                },
            ]
        },
    )

    assert response.status_code == 200

    # Get attempt details.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    answers = response.json()["answers"]

    for answer in answers:
        assert answer["is_correct"] is False


def test_get_reading_attempt_details_rejects_unknown_attempt(
    client,
    auth_headers,
):
    unknown_attempt_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/reading/attempts/{unknown_attempt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading attempt not found"


def test_get_reading_attempt_details_requires_authentication(
    client,
):
    unknown_attempt_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/reading/attempts/{unknown_attempt_id}"
    )

    assert response.status_code in (401, 403)


def test_reading_attempt_details_are_isolated_between_users(
    client,
    auth_headers,
    second_auth_headers,
    reading_test,
):
    # User A starts an attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # User B tries to access User A's attempt.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=second_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading attempt not found"


def test_reading_attempt_details_do_not_expose_extra_fields(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        f"/api/v1/reading/tests/{reading_test}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    question_id = data["passages"][0]["questions"][0]["id"]

    # Start the attempt.
    start_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert start_response.status_code == 200

    attempt_id = start_response.json()["attempt_id"]

    # Submit the attempt.
    response = client.post(
        f"/api/v1/reading/attempts/{attempt_id}/submit",
        headers=auth_headers,
        json={
            "answers": [
                {
                    "question_id": question_id,
                    "answer": "Ethiopia",
                }
            ]
        },
    )

    assert response.status_code == 200

    # Get details.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    result = response.json()

    assert set(result.keys()) == {
        "attempt_id",
        "reading_test_id",
        "score",
        "total_questions",
        "band_score",
        "submitted_at",
        "answers",
    }

    for answer in result["answers"]:
        assert set(answer.keys()) == {
            "question_id",
            "question_text",
            "question_type",
            "user_answer",
            "correct_answer",
            "is_correct",
        }


def test_start_reading_test(
    client,
    auth_headers,
    reading_test,
):
    response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert response.status_code == 200

    result = response.json()

    assert "attempt_id" in result
    assert "reading_test_id" in result
    assert "started_at" in result

    assert result["reading_test_id"] == str(reading_test)
    assert result["attempt_id"] is not None
    assert result["started_at"] is not None


def test_start_reading_test_rejects_unknown_test(
    client,
    auth_headers,
):
    unknown_test_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/reading/tests/{unknown_test_id}/start",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading test not found"


def test_start_reading_test_requires_authentication(
    client,
    reading_test,
):
    response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start"
    )

    assert response.status_code in (401, 403)


def test_start_reading_test_creates_separate_attempts(
    client,
    auth_headers,
    reading_test,
):
    first_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert first_response.status_code == 200

    first_attempt_id = first_response.json()["attempt_id"]

    second_response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert second_response.status_code == 200

    second_attempt_id = second_response.json()["attempt_id"]

    assert first_attempt_id != second_attempt_id


def test_start_reading_test_attempt_belongs_to_current_user(
    client,
    auth_headers,
    second_auth_headers,
    reading_test,
):
    response = client.post(
        f"/api/v1/reading/tests/{reading_test}/start",
        headers=auth_headers,
    )

    assert response.status_code == 200

    attempt_id = response.json()["attempt_id"]

    # Another user must not be able to access the attempt.
    response = client.get(
        f"/api/v1/reading/attempts/{attempt_id}",
        headers=second_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading attempt not found"
