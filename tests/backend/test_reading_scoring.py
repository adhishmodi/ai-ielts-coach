import pytest

from app.services.reading import (
    SUPPORTED_QUESTION_TYPES,
    calculate_question_score,
    calculate_reading_band,
    calculate_reading_score,
    calculate_reading_score_by_question_type,
    get_accepted_answers,
    is_answer_correct,
    normalize_answer,
    validate_question_type,
)


def test_normalize_answer():
    assert normalize_answer("  Hello   WORLD  ") == "hello world"


def test_calculate_reading_score():
    answers = {
        "q1": "Paris",
        "q2": "London",
        "q3": "Rome",
    }

    correct_answers = {
        "q1": "Paris",
        "q2": "London",
        "q3": "Madrid",
    }

    assert calculate_reading_score(answers, correct_answers) == 2


def test_multiple_accepted_answers():
    answers = {
        "q1": "United Kingdom",
        "q2": "UK",
        "q3": "France",
    }

    correct_answers = {
        "q1": "UK|United Kingdom",
        "q2": "UK|United Kingdom",
        "q3": "France",
    }

    assert calculate_reading_score(answers, correct_answers) == 3


def test_accepted_answers_are_case_insensitive():
    assert is_answer_correct("united kingdom", "UK|United Kingdom")
    assert is_answer_correct("UK", "UK|United Kingdom")


def test_accepted_answers_ignore_whitespace():
    assert is_answer_correct(
        "  United   Kingdom ",
        "UK|United Kingdom",
    )


def test_get_accepted_answers():
    assert get_accepted_answers(
        "UK|United Kingdom|Great Britain"
    ) == [
        "uk",
        "united kingdom",
        "great britain",
    ]


def test_invalid_answer_is_not_correct():
    assert not is_answer_correct(
        "United States",
        "UK|United Kingdom",
    )


def test_empty_answer_is_incorrect():
    assert not is_answer_correct("", "UK|United Kingdom")


def test_missing_correct_answer():
    assert calculate_reading_score(
        {"q1": "Paris"},
        {},
    ) == 0


def test_supported_question_types():
    expected_types = {
        "multiple_choice",
        "true_false",
        "true_false_not_given",
        "yes_no_not_given",
        "short_answer",
        "matching",
    }

    assert SUPPORTED_QUESTION_TYPES == expected_types


@pytest.mark.parametrize(
    "question_type",
    [
        "multiple_choice",
        "true_false",
        "true_false_not_given",
        "yes_no_not_given",
        "short_answer",
        "matching",
    ],
)
def test_validate_supported_question_type(question_type):
    assert validate_question_type(question_type)


def test_validate_unsupported_question_type():
    assert not validate_question_type("essay")


def test_multiple_choice_scoring():
    assert calculate_question_score(
        user_answer="B",
        correct_answer="B",
        question_type="multiple_choice",
    ) == 1

    assert calculate_question_score(
        user_answer="C",
        correct_answer="B",
        question_type="multiple_choice",
    ) == 0


def test_true_false_scoring():
    assert calculate_question_score(
        user_answer="TRUE",
        correct_answer="True",
        question_type="true_false",
    ) == 1


def test_true_false_not_given_scoring():
    assert calculate_question_score(
        user_answer="NOT GIVEN",
        correct_answer="NOT GIVEN",
        question_type="true_false_not_given",
    ) == 1


def test_yes_no_not_given_scoring():
    assert calculate_question_score(
        user_answer="YES",
        correct_answer="yes",
        question_type="yes_no_not_given",
    ) == 1


def test_short_answer_scoring():
    assert calculate_question_score(
        user_answer="new york",
        correct_answer="New York",
        question_type="short_answer",
    ) == 1


def test_matching_scoring():
    assert calculate_question_score(
        user_answer="C",
        correct_answer="C",
        question_type="matching",
    ) == 1


def test_multiple_accepted_answers_with_question_type():
    assert calculate_question_score(
        user_answer="United Kingdom",
        correct_answer="UK|United Kingdom",
        question_type="short_answer",
    ) == 1


def test_unsupported_question_type_raises_error():
    with pytest.raises(ValueError):
        calculate_question_score(
            user_answer="A",
            correct_answer="A",
            question_type="unknown_type",
        )


def test_calculate_reading_score_by_question_type():
    answers = {
        "q1": "B",
        "q2": "TRUE",
        "q3": "United Kingdom",
        "q4": "C",
    }

    questions = {
        "q1": {
            "correct_answer": "B",
            "question_type": "multiple_choice",
        },
        "q2": {
            "correct_answer": "TRUE",
            "question_type": "true_false",
        },
        "q3": {
            "correct_answer": "UK|United Kingdom",
            "question_type": "short_answer",
        },
        "q4": {
            "correct_answer": "C",
            "question_type": "matching",
        },
    }

    assert calculate_reading_score_by_question_type(
        answers,
        questions,
    ) == 4


def test_calculate_reading_score_by_question_type_ignores_unknown_question():
    assert calculate_reading_score_by_question_type(
        {"q1": "A", "unknown": "B"},
        {
            "q1": {
                "correct_answer": "A",
                "question_type": "multiple_choice",
            }
        },
    ) == 1


def test_band_score_for_full_score():
    assert calculate_reading_band(40, 40) == 9.0


def test_band_score_for_partial_test():
    assert calculate_reading_band(1, 3) == 4.5


def test_band_score_rejects_invalid_total():
    with pytest.raises(ValueError):
        calculate_reading_band(1, 0)


def test_band_score_rejects_negative_score():
    with pytest.raises(ValueError):
        calculate_reading_band(-1, 40)


def test_band_score_rejects_score_above_total():
    with pytest.raises(ValueError):
        calculate_reading_band(41, 40)
