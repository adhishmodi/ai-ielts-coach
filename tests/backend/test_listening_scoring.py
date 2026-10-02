import pytest

from app.services.listening import (
    calculate_listening_band,
    calculate_listening_score,
    calculate_question_score,
    get_accepted_answers,
    is_answer_correct,
    normalize_answer,
    validate_question_type,
)


def test_normalize_answer():
    assert normalize_answer("  Hello   WORLD  ") == "hello world"


def test_accepted_answers_support_alternatives():
    assert get_accepted_answers("yes | yep") == ["yes", "yep"]


def test_answer_matching_is_case_insensitive():
    assert is_answer_correct("  PATEL ", "patel") is True


def test_answer_matching_rejects_blank():
    assert is_answer_correct("   ", "patel") is False


def test_supported_listening_question_types():
    assert validate_question_type("multiple_choice") is True
    assert validate_question_type("form_completion") is True
    assert validate_question_type("unknown") is False


def test_question_score():
    assert calculate_question_score(
        "Delivery", "delivery", "multiple_choice"
    ) == 1
    assert calculate_question_score(
        "Collection", "delivery", "multiple_choice"
    ) == 0


def test_question_score_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unsupported question type"):
        calculate_question_score("x", "x", "unknown")


def test_calculate_listening_score():
    answers = {"1": "A", "2": "wrong", "3": "C"}
    questions = {
        "1": {"correct_answer": "A", "question_type": "multiple_choice"},
        "2": {"correct_answer": "B", "question_type": "short_answer"},
        "3": {"correct_answer": "C", "question_type": "matching"},
    }
    assert calculate_listening_score(answers, questions) == 2


@pytest.mark.parametrize(
    ("score", "total", "expected"),
    [
        (40, 40, 9.0),
        (38, 40, 8.5),
        (35, 40, 8.0),
        (30, 40, 7.0),
        (26, 40, 6.0),
        (20, 40, 5.5),
        (0, 40, 1.0),
    ],
)
def test_calculate_listening_band(score, total, expected):
    assert calculate_listening_band(score, total) == expected


def test_listening_band_rejects_invalid_total():
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_listening_band(0, 0)


def test_listening_band_rejects_invalid_score():
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_listening_band(-1, 40)

    with pytest.raises(ValueError, match="greater than total"):
        calculate_listening_band(41, 40)
