from __future__ import annotations

import unittest

from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.models import IntelligenceItem
from src.vietnam_bd.localization_v3 import ui
from src.vietnam_bd.ui_components_v3 import (
    STAGE_LABELS,
    _compact_fact_value,
    _decision_guidance,
    _display_value,
    _evidence_label,
    _stage_index,
    _user_copy,
)
from src.vietnam_bd.v3_rule_engine import build_v3_result


class OpportunityUIHelpersTest(unittest.TestCase):
    def test_nine_stage_journey_maps_backend_taxonomy(self) -> None:
        stages = (
            "사업기획",
            "타당성 조사",
            "Master Plan",
            "설계 - SD (기본)",
            "설계 - DD (기본)",
            "설계 - CD (기본)",
            "건설 인허가",
            "시공",
            "운영 인허가",
            "프로젝트 종료",
        )

        self.assertEqual(len(STAGE_LABELS), 9)
        self.assertEqual([_stage_index(stage) for stage in stages], [0, 1, 2, 3, 4, 5, 6, 7, 8, 8])

    def test_unknown_values_are_not_rendered_as_facts(self) -> None:
        for value in (None, "", "UNKNOWN", "Not confirmed", "-"):
            self.assertEqual(_display_value(value), "Not identified")

    def test_why_now_is_sales_guidance_not_engine_flags(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo")

        guide, _ = _decision_guidance(result)

        self.assertIn("현재 사업단계", guide)
        self.assertIn("접촉", guide)
        self.assertNotIn("Lifecycle=", guide)

    def test_overview_fact_values_are_compact_but_keep_source_claim(self) -> None:
        item = IntelligenceItem(
            claim="Project area: ~249.8 hectares; Total approved investment: VND 3.73 trillion (site: Dien Tien).",
            credibility="confirmed",
        )

        self.assertEqual(_compact_fact_value(item, "location"), "Dien Tien")
        self.assertEqual(_compact_fact_value(item, "investment"), "VND 3.73 trillion")
        self.assertEqual(_compact_fact_value(item, "scale"), "~249.8 hectares")

    def test_user_facing_copy_hides_engine_language(self) -> None:
        copy = _user_copy("Excel 규칙과 AI Context로 Vendor Spec과 Scope를 확인")

        self.assertEqual(copy, "분류 규칙과 문맥 근거로 공급사 사양과 범위를 확인")
        self.assertEqual(_evidence_label("confirmed"), "확인된 근거")
        self.assertEqual(_evidence_label("hypothesis"), "확인 필요 가설")

    def test_primary_navigation_uses_sales_language(self) -> None:
        self.assertEqual(ui("ko", "opportunity_tab"), "기회 개요")
        self.assertEqual(ui("ko", "strategy_tab"), "접촉 전략")
        self.assertEqual(ui("ko", "meeting_tab"), "미팅 준비")


if __name__ == "__main__":
    unittest.main()
