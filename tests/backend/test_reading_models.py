from app.models.passage import Passage
from app.models.reading_question import ReadingQuestion
from app.models.reading_test import ReadingTest


def test_create_reading_test():
    reading_test = ReadingTest(
        title="IELTS Academic Reading Test 1",
        description="Practice reading test",
        difficulty="medium",
        time_limit_minutes=60,
    )

    assert reading_test.title == "IELTS Academic Reading Test 1"
    assert reading_test.description == "Practice reading test"
    assert reading_test.difficulty == "medium"
    assert reading_test.time_limit_minutes == 60


def test_reading_test_fields():
    reading_test = ReadingTest(
        title="IELTS Reading Test",
        description="Academic reading practice",
        difficulty="hard",
        time_limit_minutes=60,
    )

    assert reading_test.title == "IELTS Reading Test"
    assert reading_test.description == "Academic reading practice"
    assert reading_test.difficulty == "hard"
    assert reading_test.time_limit_minutes == 60


def test_create_passage():
    reading_test = ReadingTest(title="Reading Test")

    passage = Passage(
        reading_test=reading_test,
        title="The History of Coffee",
        content="Coffee has a long and interesting history.",
        order=1,
    )

    assert passage.title == "The History of Coffee"
    assert passage.content == "Coffee has a long and interesting history."
    assert passage.order == 1
    assert passage.reading_test is reading_test
    assert passage in reading_test.passages


def test_create_reading_question():
    passage = Passage(
        reading_test=ReadingTest(title="Reading Test"),
        title="Passage 1",
        content="This is a sample passage.",
        order=1,
    )

    question = ReadingQuestion(
        passage=passage,
        question_text="What is the main idea?",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answer="B",
        explanation="The passage clearly states that B is the main idea.",
        order=1,
    )

    assert question.question_text == "What is the main idea?"
    assert question.question_type == "multiple_choice"
    assert question.options == ["A", "B", "C", "D"]
    assert question.correct_answer == "B"
    assert question.explanation == (
        "The passage clearly states that B is the main idea."
    )
    assert question.order == 1
    assert question.passage is passage
    assert question in passage.questions


def test_reading_test_has_passages():
    reading_test = ReadingTest(title="Reading Test")

    passage1 = Passage(
        title="Passage 1",
        content="First passage.",
        order=1,
    )

    passage2 = Passage(
        title="Passage 2",
        content="Second passage.",
        order=2,
    )

    reading_test.passages.extend([passage1, passage2])

    assert len(reading_test.passages) == 2
    assert reading_test.passages[0] is passage1
    assert reading_test.passages[1] is passage2

    assert passage1.reading_test is reading_test
    assert passage2.reading_test is reading_test


def test_passage_has_questions():
    passage = Passage(
        reading_test=ReadingTest(title="Reading Test"),
        title="Passage 1",
        content="Sample content.",
        order=1,
    )

    question1 = ReadingQuestion(
        question_text="Question 1",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        order=1,
    )

    question2 = ReadingQuestion(
        question_text="Question 2",
        question_type="true_false",
        correct_answer="TRUE",
        order=2,
    )

    passage.questions.extend([question1, question2])

    assert len(passage.questions) == 2
    assert passage.questions[0] is question1
    assert passage.questions[1] is question2

    assert question1.passage is passage
    assert question2.passage is passage


def test_question_options_can_be_none():
    passage = Passage(
        reading_test=ReadingTest(title="Reading Test"),
        title="Passage 1",
        content="Sample content.",
        order=1,
    )

    question = ReadingQuestion(
        passage=passage,
        question_text="Is this statement true?",
        question_type="true_false",
        options=None,
        correct_answer="TRUE",
        order=1,
    )

    assert question.options is None


def test_question_explanation_can_be_none():
    passage = Passage(
        reading_test=ReadingTest(title="Reading Test"),
        title="Passage 1",
        content="Sample content.",
        order=1,
    )

    question = ReadingQuestion(
        passage=passage,
        question_text="What is the answer?",
        question_type="short_answer",
        correct_answer="coffee",
        explanation=None,
        order=1,
    )

    assert question.explanation is None


def test_reading_test_can_have_multiple_passages_and_questions():
    reading_test = ReadingTest(
        title="Complete IELTS Reading Test",
        difficulty="hard",
    )

    passage1 = Passage(
        reading_test=reading_test,
        title="Passage 1",
        content="First passage content.",
        order=1,
    )

    passage2 = Passage(
        reading_test=reading_test,
        title="Passage 2",
        content="Second passage content.",
        order=2,
    )

    question1 = ReadingQuestion(
        passage=passage1,
        question_text="Question 1",
        question_type="multiple_choice",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        order=1,
    )

    question2 = ReadingQuestion(
        passage=passage1,
        question_text="Question 2",
        question_type="true_false",
        correct_answer="TRUE",
        order=2,
    )

    question3 = ReadingQuestion(
        passage=passage2,
        question_text="Question 3",
        question_type="short_answer",
        correct_answer="Paris",
        order=1,
    )

    assert len(reading_test.passages) == 2
    assert len(passage1.questions) == 2
    assert len(passage2.questions) == 1

    assert question1.passage is passage1
    assert question2.passage is passage1
    assert question3.passage is passage2


def test_question_order_is_independent_per_passage():
    reading_test = ReadingTest(title="Reading Test")

    passage1 = Passage(
        reading_test=reading_test,
        title="Passage 1",
        content="First passage.",
        order=1,
    )

    passage2 = Passage(
        reading_test=reading_test,
        title="Passage 2",
        content="Second passage.",
        order=2,
    )

    question1 = ReadingQuestion(
        passage=passage1,
        question_text="Question 1",
        question_type="short_answer",
        correct_answer="A",
        order=1,
    )

    question2 = ReadingQuestion(
        passage=passage2,
        question_text="Question 1",
        question_type="short_answer",
        correct_answer="B",
        order=1,
    )

    assert question1.order == 1
    assert question2.order == 1
    assert question1.passage is passage1
    assert question2.passage is passage2
