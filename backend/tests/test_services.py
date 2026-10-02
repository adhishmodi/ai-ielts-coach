import pytest
from app.services.reading import normalize_answer, get_accepted_answers, is_answer_correct, validate_question_type, calculate_question_score, calculate_reading_score, calculate_reading_score_by_question_type, calculate_reading_band
from app.services.listening import normalize_answer as ln, get_accepted_answers as la, is_answer_correct as lc, validate_question_type as lt, calculate_question_score as lqs, calculate_listening_score, calculate_listening_band
from app.services.writing import count_words, is_valid_band, validate_band, round_to_ielts_band, calculate_task_band, calculate_writing_overall_band, RuleBasedWritingEvaluator

@pytest.mark.parametrize("v,e",[(" Paris ","paris"),("A   B","a b"),("",""),("  ",""),("Hello\nworld","hello world")])
def test_reading_normalize(v,e): assert normalize_answer(v)==e
@pytest.mark.parametrize("v,e",[("Paris|Rome",["paris","rome"]),(" A | B ",["a","b"]),("",[]),("a||b",["a","b"])])
def test_reading_accepted(v,e): assert get_accepted_answers(v)==e
@pytest.mark.parametrize("u,c,e",[("Paris","paris",True),(" PARIS ","paris",True),("Rome","paris|london",False),("","paris",False),("a  b","a b",True)])
def test_reading_correct(u,c,e): assert is_answer_correct(u,c) is e
@pytest.mark.parametrize("k",["multiple_choice","matching","sentence_completion","summary_completion","short_answer","true_false_not_given"])
def test_reading_types(k): assert validate_question_type(k)
@pytest.mark.parametrize("k",["bad","","MCQ","unknown"])
def test_reading_bad_types(k): assert not validate_question_type(k)
@pytest.mark.parametrize("s,t,b",[(40,40,9.0),(39,40,9.0),(38,40,8.5),(35,40,8.0),(30,40,7.0),(26,40,6.0),(22,40,5.5),(18,40,5.0),(14,40,4.5),(10,40,4.0),(5,40,3.0),(0,40,1.0)])
def test_reading_band(s,t,b): assert calculate_reading_band(s,t)==b
@pytest.mark.parametrize("s,t",[(0,0),(-1,10),(11,10)])
def test_reading_band_invalid(s,t):
    with pytest.raises(ValueError): calculate_reading_band(s,t)
def test_reading_scores(): assert calculate_reading_score({"1":"Paris","2":"wrong","3":"blue"},{"1":"paris","2":"right","3":"blue"})==2
def test_reading_unknown_ignored(): assert calculate_reading_score({"x":"yes"},{"1":"yes"})==0
def test_reading_scores_by_type():
    q={"1":{"correct_answer":"yes","question_type":"short_answer"},"2":{"correct_answer":"no","question_type":"multiple_choice"}}
    assert calculate_reading_score_by_question_type({"1":"YES","2":"no"},q)==2
def test_reading_question_score():
    assert calculate_question_score("yes","yes","short_answer")==1
    assert calculate_question_score("no","yes","short_answer")==0
    with pytest.raises(ValueError): calculate_question_score("yes","yes","bad")
@pytest.mark.parametrize("v,e",[(" London ","london"),("A   B","a b"),("","")])
def test_listening_normalize(v,e): assert ln(v)==e
@pytest.mark.parametrize("v,e",[("London|Paris",["london","paris"]),("a||b",["a","b"]),("",[])])
def test_listening_accepted(v,e): assert la(v)==e
@pytest.mark.parametrize("u,c,e",[("London","london",True),(" london ","london",True),("Paris","London",False),("","London",False)])
def test_listening_correct(u,c,e): assert lc(u,c) is e
@pytest.mark.parametrize("k",["multiple_choice","matching","form_completion","sentence_completion","note_completion","short_answer","map_labeling"])
def test_listening_types(k): assert lt(k)
@pytest.mark.parametrize("k",["bad","","MCQ"])
def test_listening_bad_types(k): assert not lt(k)
def test_listening_scores():
    q={"1":{"correct_answer":"yes","question_type":"short_answer"},"2":{"correct_answer":"no","question_type":"multiple_choice"}}
    assert calculate_listening_score({"1":"YES","2":"wrong","3":"x"},q)==1
@pytest.mark.parametrize("s,t,b",[(40,40,9.0),(35,40,8.0),(30,40,7.0),(26,40,6.0),(20,40,5.5),(10,40,4.0),(0,40,1.0)])
def test_listening_band(s,t,b): assert calculate_listening_band(s,t)==b
@pytest.mark.parametrize("s,t",[(0,0),(-1,10),(41,40)])
def test_listening_band_invalid(s,t):
    with pytest.raises(ValueError): calculate_listening_band(s,t)
def test_listening_question_score():
    assert lqs("yes","yes","short_answer")==1
    assert lqs("no","yes","short_answer")==0
    with pytest.raises(ValueError): lqs("yes","yes","bad")
@pytest.mark.parametrize("v,e",[("",0),("   ",0),("hello",1),("hello world",2),("one\ntwo\nthree",3),(" one  two ",2)])
def test_word_count(v,e): assert count_words(v)==e
@pytest.mark.parametrize("v",[0,0.5,1,4,8.5,9])
def test_valid_band(v): assert is_valid_band(v) and validate_band(v)==v
@pytest.mark.parametrize("v",[-1,0.25,9.1,4.25,10])
def test_invalid_band(v):
    assert not is_valid_band(v)
    with pytest.raises(ValueError): validate_band(v)
@pytest.mark.parametrize("v,e",[(4.24,4.0),(4.25,4.5),(4.49,4.5),(4.75,5.0),(9.9,9.0),(-1,0.0)])
def test_rounding(v,e): assert round_to_ielts_band(v)==e
def test_task_band(): assert calculate_task_band(6,6,6,6)==6.0 and calculate_task_band(6,7,7,6)==6.5
def test_task_band_invalid():
    with pytest.raises(ValueError): calculate_task_band(6.25,6,6,6)
def test_writing_weighting(): assert calculate_writing_overall_band(6,7)==6.5
def test_writing_weighting_invalid():
    with pytest.raises(ValueError): calculate_writing_overall_band(6.2,7)
def test_rule_based_evaluator():
    r=RuleBasedWritingEvaluator().evaluate(" ".join(["word"]*250),"prompt")
    assert r.overall_band==5.0 and r.evaluated_by=="system"
