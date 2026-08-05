from src.guided_questions import generate_guided_questions


def test_questions_are_limited():
    qs = generate_guided_questions("베트남 반도체 공장 증설")
    assert 4 <= len(qs) <= 6
