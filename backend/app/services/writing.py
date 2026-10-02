import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


def count_words(text: str) -> int:
    if not text or not text.strip():
        return 0
    return len(re.findall(r"\S+", text.strip()))


def is_valid_band(value: float) -> bool:
    return 0.0 <= value <= 9.0 and math.isclose(value * 2, round(value * 2), abs_tol=1e-9)


def validate_band(value: float) -> float:
    value = float(value)
    if not is_valid_band(value):
        raise ValueError("Band score must be between 0.0 and 9.0 in 0.5 increments")
    return value


def round_to_ielts_band(value: float) -> float:
    value = max(0.0, min(9.0, float(value)))
    return math.floor(value * 2 + 0.5) / 2


def calculate_task_band(
    task_response_or_achievement: float,
    coherence: float,
    lexical: float,
    grammar: float,
) -> float:
    values = [
        validate_band(task_response_or_achievement),
        validate_band(coherence),
        validate_band(lexical),
        validate_band(grammar),
    ]
    return round_to_ielts_band(sum(values) / 4)


def calculate_writing_overall_band(task1_band: float, task2_band: float) -> float:
    validate_band(task1_band)
    validate_band(task2_band)
    return round_to_ielts_band((task1_band + task2_band * 2) / 3)


@dataclass(frozen=True)
class WritingEvaluationResult:
    task_response_band: float
    coherence_band: float
    lexical_band: float
    grammar_band: float
    overall_band: float
    feedback: str
    strengths: list[str]
    improvements: list[str]
    evaluated_by: str = "ai"


class WritingEvaluator(ABC):
    @abstractmethod
    def evaluate(self, submission_text: str, task_prompt: str) -> WritingEvaluationResult:
        raise NotImplementedError


class RuleBasedWritingEvaluator(WritingEvaluator):
    def evaluate(self, submission_text: str, task_prompt: str) -> WritingEvaluationResult:
        words = count_words(submission_text)
        base = 5.0 if words >= 250 else 4.5 if words >= 150 else 4.0
        return WritingEvaluationResult(
            task_response_band=base,
            coherence_band=base,
            lexical_band=base,
            grammar_band=base,
            overall_band=base,
            feedback="Rule-based placeholder evaluation. Replace with an AI evaluator in a later module.",
            strengths=["Response was submitted successfully."],
            improvements=["Add a detailed AI evaluation for criterion-level feedback."],
            evaluated_by="system",
        )
