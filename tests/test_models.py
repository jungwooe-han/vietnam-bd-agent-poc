from src.demo_data import demo_result


def test_demo_result_valid():
    result = demo_result()
    assert 3 <= len(result.priority_questions) <= 5
    assert len(result.next_steps) == 3
    assert result.portfolio.lead_domain
