import uuid


def _task_map(response):
    return {task["task_number"]: task for task in response.json()["tasks"]}


def _start(client, auth_headers, test_id):
    response = client.post(
        f"/api/v1/writing/tests/{test_id}/start",
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()["attempt_id"]


def _save_all_tasks(client, auth_headers, test_id, attempt_id):
    test_response = client.get(
        f"/api/v1/writing/tests/{test_id}",
        headers=auth_headers,
    )
    tasks = _task_map(test_response)
    for number, text in [
        (1, " ".join(["academic"] * 150)),
        (2, " ".join(["essay"] * 250)),
    ]:
        response = client.put(
            f"/api/v1/writing/attempts/{attempt_id}/tasks/{tasks[number]['id']}",
            headers=auth_headers,
            json={"response_text": text},
        )
        assert response.status_code == 200


def test_writing_tests_require_authentication(client):
    assert client.get("/api/v1/writing/tests").status_code == 401


def test_get_writing_tests(client, auth_headers, writing_test):
    response = client.get("/api/v1/writing/tests", headers=auth_headers)
    assert response.status_code == 200
    assert any(item["id"] == str(writing_test) for item in response.json())


def test_get_writing_test_contains_tasks(client, auth_headers, writing_test):
    response = client.get(
        f"/api/v1/writing/tests/{writing_test}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["test_type"] == "academic"
    assert [task["task_number"] for task in response.json()["tasks"]] == [1, 2]
    assert response.json()["tasks"][0]["minimum_words"] == 150
    assert response.json()["tasks"][1]["minimum_words"] == 250


def test_get_unknown_writing_test(client, auth_headers):
    response = client.get(
        f"/api/v1/writing/tests/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_start_writing_test(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    detail = client.get(
        f"/api/v1/writing/attempts/{attempt_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "in_progress"
    assert detail.json()["submissions"] == []


def test_start_unknown_writing_test(client, auth_headers):
    response = client.post(
        f"/api/v1/writing/tests/{uuid.uuid4()}/start",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_save_writing_draft_and_word_count(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    test_response = client.get(
        f"/api/v1/writing/tests/{writing_test}",
        headers=auth_headers,
    )
    task_id = _task_map(test_response)[1]["id"]

    response = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"response_text": "one two three four five"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["word_count"] == 5
    assert data["minimum_words"] == 150
    assert data["below_minimum_words"] is True


def test_save_draft_updates_existing_submission(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    task_id = _task_map(
        client.get(f"/api/v1/writing/tests/{writing_test}", headers=auth_headers)
    )[1]["id"]

    first = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"response_text": "one two"},
    )
    second = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"response_text": "one two three four"},
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["submission_id"] == second.json()["submission_id"]
    assert second.json()["word_count"] == 4

    detail = client.get(
        f"/api/v1/writing/attempts/{attempt_id}", headers=auth_headers
    )
    assert len(detail.json()["submissions"]) == 1
    assert detail.json()["submissions"][0]["response_text"] == "one two three four"


def test_save_draft_rejects_unknown_task(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    response = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{uuid.uuid4()}",
        headers=auth_headers,
        json={"response_text": "hello"},
    )
    assert response.status_code == 400


def test_submit_requires_all_tasks(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    task_id = _task_map(
        client.get(f"/api/v1/writing/tests/{writing_test}", headers=auth_headers)
    )[1]["id"]
    client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"response_text": " ".join(["word"] * 150)},
    )
    response = client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Missing tasks" in response.json()["detail"]


def test_submit_writing_test_returns_word_warnings(
    client, auth_headers, writing_test
):
    attempt_id = _start(client, auth_headers, writing_test)
    test_response = client.get(
        f"/api/v1/writing/tests/{writing_test}", headers=auth_headers
    )
    tasks = _task_map(test_response)

    for number, text in [
        (1, " ".join(["word"] * 150)),
        (2, "too short"),
    ]:
        response = client.put(
            f"/api/v1/writing/attempts/{attempt_id}/tasks/{tasks[number]['id']}",
            headers=auth_headers,
            json={"response_text": text},
        )
        assert response.status_code == 200

    response = client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert data["task_word_counts"]["1"] == 150
    assert data["task_word_counts"]["2"] == 2
    assert data["below_minimum_tasks"] == [2]


def test_submitted_attempt_cannot_be_submitted_twice(
    client, auth_headers, writing_test
):
    attempt_id = _start(client, auth_headers, writing_test)
    _save_all_tasks(client, auth_headers, writing_test, attempt_id)

    first = client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    )
    second = client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 400


def test_submitted_attempt_cannot_be_edited(client, auth_headers, writing_test):
    attempt_id = _start(client, auth_headers, writing_test)
    _save_all_tasks(client, auth_headers, writing_test, attempt_id)
    assert client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    ).status_code == 200

    task_id = _task_map(
        client.get(f"/api/v1/writing/tests/{writing_test}", headers=auth_headers)
    )[1]["id"]
    response = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"response_text": "changed"},
    )
    assert response.status_code == 400


def test_attempt_history_contains_current_user_attempt(
    client, auth_headers, writing_test
):
    attempt_id = _start(client, auth_headers, writing_test)
    response = client.get("/api/v1/writing/attempts", headers=auth_headers)
    assert response.status_code == 200
    assert any(item["attempt_id"] == attempt_id for item in response.json())


def test_attempt_ownership_is_enforced(
    client, auth_headers, second_auth_headers, writing_test
):
    attempt_id = _start(client, auth_headers, writing_test)
    response = client.get(
        f"/api/v1/writing/attempts/{attempt_id}",
        headers=second_auth_headers,
    )
    assert response.status_code == 404

    response = client.put(
        f"/api/v1/writing/attempts/{attempt_id}/tasks/{uuid.uuid4()}",
        headers=second_auth_headers,
        json={"response_text": "not allowed"},
    )
    assert response.status_code == 404


def test_attempt_details_include_saved_evaluation_when_present(
    client, auth_headers, writing_test
):
    # The first Writing release does not invoke external AI during submit.
    # This verifies the submission remains available for the later evaluator layer.
    attempt_id = _start(client, auth_headers, writing_test)
    _save_all_tasks(client, auth_headers, writing_test, attempt_id)
    assert client.post(
        f"/api/v1/writing/attempts/{attempt_id}/submit",
        headers=auth_headers,
    ).status_code == 200

    detail = client.get(
        f"/api/v1/writing/attempts/{attempt_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "submitted"
    assert len(detail.json()["submissions"]) == 2
    assert all(item["evaluation"] is None for item in detail.json()["submissions"])


def test_attempt_details_require_authentication(client):
    response = client.get(f"/api/v1/writing/attempts/{uuid.uuid4()}")
    assert response.status_code in (401, 403)
