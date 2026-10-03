SUPPORTED_QUESTION_TYPES = {
    "multiple_choice",
    "true_false",
    "true_false_not_given",
    "yes_no_not_given",
    "short_answer",
    "sentence_completion",
    "summary_completion",
    "matching",
}


def normalize_answer(answer: str) -> str:
    """Normalize case and whitespace for answer comparison."""
    return " ".join(answer.strip().lower().split())


def get_accepted_answers(correct_answer: str) -> list[str]:
    """
    Return normalized accepted answers.

    Multiple accepted answers may be separated with '|'.
    """
    return [
        normalized
        for answer in correct_answer.split("|")
        if (normalized := normalize_answer(answer))
    ]


def is_answer_correct(
    user_answer: str,
    correct_answer: str,
) -> bool:
    """Return True when the user's answer matches an accepted answer."""
    normalized_user_answer = normalize_answer(user_answer)

    if not normalized_user_answer:
        return False

    return normalized_user_answer in get_accepted_answers(correct_answer)


def validate_question_type(question_type: str) -> bool:
    """Return True when the question type is supported."""
    return question_type in SUPPORTED_QUESTION_TYPES


def calculate_question_score(
    user_answer: str,
    correct_answer: str,
    question_type: str,
) -> int:
    """Score one supported Reading question."""
    if not validate_question_type(question_type):
        raise ValueError(
            f"Unsupported question type: {question_type}"
        )

    return int(is_answer_correct(user_answer, correct_answer))


def calculate_reading_score(
    answers: dict[str, str],
    correct_answers: dict[str, str],
) -> int:
    """Calculate the number of correct answers."""
    score = 0

    for question_id, user_answer in answers.items():
        correct_answer = correct_answers.get(question_id)

        if correct_answer is None:
            continue

        if is_answer_correct(user_answer, correct_answer):
            score += 1

    return score


def calculate_reading_score_by_question_type(
    answers: dict[str, str],
    questions: dict[str, dict[str, str]],
) -> int:
    """
    Calculate Reading score using question metadata.

    Unknown question IDs are ignored; the API validates question ownership.
    """
    score = 0

    for question_id, user_answer in answers.items():
        question = questions.get(question_id)

        if question is None:
            continue

        correct_answer = question.get("correct_answer")
        question_type = question.get("question_type")

        if correct_answer is None or question_type is None:
            continue

        score += calculate_question_score(
            user_answer=user_answer,
            correct_answer=correct_answer,
            question_type=question_type,
        )

    return score


def calculate_reading_band(
    score: int,
    total_questions: int,
) -> float:
    """Convert an Academic Reading score to an IELTS-style band."""
    if total_questions <= 0:
        raise ValueError("total_questions must be greater than zero")

    if score < 0:
        raise ValueError("score cannot be negative")

    if score > total_questions:
        raise ValueError(
            "score cannot be greater than total_questions"
        )

    scaled_score = round((score / total_questions) * 40)
    scaled_score = max(0, min(40, scaled_score))

    band_map = {
        40: 9.0,
        39: 9.0,
        38: 8.5,
        37: 8.5,
        36: 8.0,
        35: 8.0,
        34: 7.5,
        33: 7.5,
        32: 7.5,
        31: 7.0,
        30: 7.0,
        29: 6.5,
        28: 6.5,
        27: 6.5,
        26: 6.0,
        25: 6.0,
        24: 6.0,
        23: 6.0,
        22: 5.5,
        21: 5.5,
        20: 5.5,
        19: 5.5,
        18: 5.0,
        17: 5.0,
        16: 5.0,
        15: 5.0,
        14: 4.5,
        13: 4.5,
        12: 4.0,
        11: 4.0,
        10: 4.0,
        9: 4.0,
        8: 3.5,
        7: 3.5,
        6: 3.5,
        5: 3.0,
        4: 3.0,
        3: 2.5,
        2: 2.5,
        1: 1.0,
        0: 1.0,
    }

    return band_map[scaled_score]
