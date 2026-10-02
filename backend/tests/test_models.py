from app.models.reading_test import ReadingTest
from app.models.passage import Passage
from app.models.reading_question import ReadingQuestion
from app.models.listening_test import ListeningTest
from app.models.listening_section import ListeningSection
from app.models.listening_question import ListeningQuestion
from app.models.writing_test import WritingTest
from app.models.writing_task import WritingTask
from app.models.writing_submission import WritingSubmission
from app.models.writing_evaluation import WritingEvaluation

def test_reading_relationships():
    test=ReadingTest(title="T",difficulty="medium",time_limit_minutes=60)
    passage=Passage(title="P",content="text",order=1)
    question=ReadingQuestion(question_text="Q",question_type="short_answer",correct_answer="yes",order=1)
    passage.questions.append(question); test.passages.append(passage)
    assert passage.reading_test is test and question.passage is passage

def test_listening_relationships():
    test=ListeningTest(title="T",difficulty="medium",time_limit_minutes=40)
    section=ListeningSection(title="S",order=1)
    question=ListeningQuestion(question_text="Q",question_type="short_answer",correct_answer="yes",order=1)
    section.questions.append(question); test.sections.append(section)
    assert section.listening_test is test and question.section is section

def test_writing_relationships():
    test=WritingTest(title="T",test_type="academic",difficulty="medium",time_limit_minutes=60)
    task=WritingTask(task_number=1,task_type="graph",prompt="P",minimum_words=150,order=1)
    test.tasks.append(task)
    assert task.writing_test is test

def test_writing_submission_defaults():
    s=WritingSubmission(response_text="hello",word_count=1)
    assert s.response_text=="hello" and s.word_count==1

def test_writing_evaluation_defaults():
    e=WritingEvaluation(evaluated_by="ai")
    assert e.evaluated_by=="ai"
