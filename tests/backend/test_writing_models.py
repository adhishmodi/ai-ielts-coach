import pytest

from app.models.writing_evaluation import WritingEvaluation
from app.models.writing_submission import WritingSubmission
from app.models.writing_task import WritingTask
from app.models.writing_test import WritingTest


def test_writing_test_relationships():
    test = WritingTest(title="Test", test_type="academic", difficulty="medium", time_limit_minutes=60)
    task = WritingTask(
        task_number=1,
        task_type="graph",
        prompt="Prompt",
        minimum_words=150,
        order=1,
    )
    test.tasks.append(task)
    assert task.writing_test is test
    assert test.tasks[0] is task


def test_writing_submission_relationships():
    submission = WritingSubmission(response_text="hello", word_count=1)
    assert submission.response_text == "hello"
    assert submission.word_count == 1


def test_writing_evaluation_defaults():
    evaluation = WritingEvaluation(evaluated_by="ai")
    assert evaluation.evaluated_by == "ai"


@pytest.mark.parametrize(
    ("task_type", "minimum_words"),
    [("graph", 150), ("chart", 150), ("table", 150), ("process", 150),
     ("map", 150), ("letter", 150), ("essay", 250), ("combined", 150)],
)
def test_supported_writing_task_configuration(task_type, minimum_words):
    task = WritingTask(
        task_number=1,
        task_type=task_type,
        prompt="Prompt",
        minimum_words=minimum_words,
        order=1,
    )
    assert task.task_type == task_type
    assert task.minimum_words == minimum_words
