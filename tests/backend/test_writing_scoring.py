import pytest

from app.services.writing import (
    RuleBasedWritingEvaluator,
    calculate_task_band,
    calculate_writing_overall_band,
    count_words,
    is_valid_band,
    round_to_ielts_band,
    validate_band,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("hello", 1),
        ("hello world", 2),
        ("  hello   world  ", 2),
        ("hello\nworld\nagain", 3),
        ("Hello, world!", 2),
        ("first paragraph\n\nsecond paragraph", 4),
    ],
)
def test_count_words(text, expected):
    assert count_words(text) == expected


@pytest.mark.parametrize("value", [0.0, 4.5, 5.0, 6.5, 9.0])
def test_valid_bands(value):
    assert is_valid_band(value) is True
    assert validate_band(value) == value


@pytest.mark.parametrize("value", [-0.5, 9.5, 5.25, 6.1])
def test_invalid_bands(value):
    assert is_valid_band(value) is False
    with pytest.raises(ValueError):
        validate_band(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(5.24, 5.0), (5.25, 5.5), (5.74, 5.5), (5.75, 6.0), (8.99, 9.0)],
)
def test_ielts_rounding(value, expected):
    assert round_to_ielts_band(value) == expected


def test_task_band_averages_four_criteria():
    assert calculate_task_band(6.0, 6.5, 7.0, 6.5) == 6.5


def test_task_band_rejects_invalid_criteria():
    with pytest.raises(ValueError):
        calculate_task_band(6.0, 6.25, 7.0, 6.5)


def test_task_two_has_double_weight():
    assert calculate_writing_overall_band(6.0, 7.0) == 6.5
    assert calculate_writing_overall_band(7.0, 6.0) == 6.5


def test_overall_band_rounding():
    assert calculate_writing_overall_band(6.5, 7.5) == 7.0


def test_overall_band_rejects_invalid_values():
    with pytest.raises(ValueError):
        calculate_writing_overall_band(6.25, 7.0)


def test_rule_based_evaluator_is_deterministic():
    evaluator = RuleBasedWritingEvaluator()
    result = evaluator.evaluate(" ".join(["word"] * 250), "Write an essay.")
    assert result.overall_band == 5.0
    assert result.evaluated_by == "system"
    assert result.strengths
    assert result.improvements
