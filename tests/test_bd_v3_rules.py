from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.v3_rule_engine import _read_rulebook, build_v3_result


def test_rulebook_contains_only_normalized_rule_sheets():
    rules = _read_rulebook()
    assert "1. Structure Node_Rule" in rules
    assert "2. Project Structure_Rule" in rules
    assert "3. Product Mapping_Rule" in rules
    assert "사업구도" not in rules


def test_v3_returns_exactly_three_excel_supported_products():
    result = build_v3_result(
        demo_v2_result(),
        "신축 공장 스마트팩토리 IoT automation energy monitoring expansion",
    )
    assert len(result.product_top3) == 3
    assert all(item.excel_match_count > 0 for item in result.product_top3)
    assert all(item.matched_rules for item in result.product_top3)


def test_closed_stops_stakeholder_and_product_recommendations():
    result = build_v3_result(demo_v2_result(closed=True), "closed project")
    assert result.status == "closed"
    assert result.priority_1 == []
    assert result.questions_to_ask == []
    assert result.product_top3 == []
