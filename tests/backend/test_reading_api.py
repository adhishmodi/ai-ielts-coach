import uuid

def test_get_reading_tests_requires_authentication(client):
    response = client.get("/api/v1/reading/tests")

    assert response.status_code == 401


def test_get_reading_tests_with_authentication(
    client,
    auth_headers,
    reading_test,
):
    response = client.get(
        "/api/v1/reading/tests",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    matching_tests = [
        test for test in data
        if test["id"] == str(reading_test)
    ]

    assert len(matching_tests) == 1

    test = matching_tests[0]

    assert test["title"] == "IELTS Academic Reading Practice"
    assert test["difficulty"] == "medium"
    assert test["time_limit_minutes"] == 60


def test_get_specific_reading_test(
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

    assert data["id"] == str(reading_test)
    assert data["title"] == "IELTS Academic Reading Practice"

    assert len(data["passages"]) == 2

    assert data["passages"][0]["title"] == "The History of Coffee"
    assert data["passages"][1]["title"] == "Modern Technology"


def test_reading_test_contains_questions(
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

    passage1 = data["passages"][0]
    passage2 = data["passages"][1]

    assert len(passage1["questions"]) == 2
    assert len(passage2["questions"]) == 1

    assert passage1["questions"][0]["question_text"] == (
        "Where did coffee originate?"
    )

    assert passage2["questions"][0]["question_text"] == (
        "What has technology changed?"
    )


def test_reading_questions_do_not_expose_answers(
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

    for passage in data["passages"]:
        for question in passage["questions"]:
            assert "correct_answer" not in question
            assert "explanation" not in question


def test_multiple_choice_question_contains_options(
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

    question = data["passages"][0]["questions"][0]

    assert question["question_type"] == "multiple_choice"

    assert question["options"] == [
        "Ethiopia",
        "India",
        "Brazil",
        "France",
    ]


def test_true_false_question_can_have_no_options(
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

    question = data["passages"][0]["questions"][1]

    assert question["question_type"] == "true_false"
    assert question["options"] is None


def test_reading_test_not_found(
    client,
    auth_headers,
):
    random_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/reading/tests/{random_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Reading test not found"


def test_invalid_reading_test_id(
    client,
    auth_headers,
):
    response = client.get(
        "/api/v1/reading/tests/not-a-uuid",
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_reading_test_order(
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

    assert data["passages"][0]["order"] == 1
    assert data["passages"][1]["order"] == 2

    assert data["passages"][0]["questions"][0]["order"] == 1
    assert data["passages"][0]["questions"][1]["order"] == 2
