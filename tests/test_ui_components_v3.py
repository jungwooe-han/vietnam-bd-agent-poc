from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest

from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.models import EvidenceItem, IntelligenceItem, ProjectLocation, TimelineItem
from src.vietnam_bd.localization_v3 import ui
from src.vietnam_bd.ui_components_v3 import (
    STAGE_LABELS,
    _compact_fact_value,
    _confirmed_project_owner_node,
    _contact_strategy_summary,
    _display_value,
    _evidence_label,
    _location_map_rows,
    _location_search_query,
    _location_zoom,
    _public_progress_events,
    _sales_stage_guidance,
    _source_popover,
    _source_rows,
    _stage_index,
    _unknown_roles_for_stage,
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

        guide, _ = _sales_stage_guidance(result)

        self.assertIn("현재 프로젝트", guide)
        self.assertIn("지금은", guide)
        self.assertNotIn("Lifecycle=", guide)
        self.assertNotIn("공개 근거", guide)
        self.assertNotIn("Evidence", guide)

    def test_stage_guidance_varies_for_three_sales_contexts(self) -> None:
        planning = build_v3_result(demo_v2_result(), "planning")
        planning.project_stage.value = "사업기획"
        planning.v2_snapshot.context.business_stage.claim = "사업기획"

        design = build_v3_result(demo_v2_result(), "design")
        construction = build_v3_result(
            demo_v2_result(decision="monitor"), "construction"
        )

        planning_guide, _ = _sales_stage_guidance(planning)
        design_guide, _ = _sales_stage_guidance(design)
        construction_guide, _ = _sales_stage_guidance(construction)

        self.assertIn("EPC 선정 현황", planning_guide)
        self.assertIn("사양 확정 일정", design_guide)
        self.assertIn("미발주 패키지", construction_guide)
        self.assertEqual(len({planning_guide, design_guide, construction_guide}), 3)
        for guide in (planning_guide, design_guide, construction_guide):
            self.assertLessEqual(guide.count("."), 3)

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

    def test_contact_strategy_summary_uses_natural_sales_language(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo")

        summary = _contact_strategy_summary(result)

        self.assertIn("이야기해 보세요", summary)
        self.assertIn("발주 일정", summary)
        self.assertIn("제안이 참여할 수 있는 지점", summary)
        self.assertNotIn("열려 있는 범위", summary)
        self.assertNotIn("권한", summary)

    def test_overview_owner_prefers_confirmed_relationship_map_owner(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo")
        result.v2_snapshot.project_intelligence.owner_summary = "Wrong summary company"
        owner = _confirmed_project_owner_node(result)

        self.assertIsNotNone(owner)
        self.assertNotEqual(owner.company, "Wrong summary company")
        self.assertIn("PROJECT_OWNER", owner.roles)

    def test_legacy_provenance_links_urls_to_matching_publishers(self) -> None:
        rules, rows = _source_rows(
            [
                "rule:신축",
                "Vietnam News",
                "Vietnam News (Viet Nam News)",
                "NIC — Vietnam Innovation Tech Investment Report",
            ],
            [
                "https://vietnamnews.vn/economy/article.html",
                "https://nic.gov.vn/report.pdf",
            ],
            ["2026-08-14", "2024-04"],
        )

        self.assertEqual(rules, ["신축"])
        self.assertEqual(rows, [
            ("Vietnam News", "https://vietnamnews.vn/economy/article.html", "2026-08-14"),
            ("NIC — Vietnam Innovation Tech Investment Report", "https://nic.gov.vn/report.pdf", "2024-04"),
        ])

    def test_popover_hides_internal_rules_and_repeated_summary(self) -> None:
        item = EvidenceItem(
            claim="신축",
            credibility="likely",
            rationale="test",
            source_labels=["rule:신축", "Vietnam News"],
            source_urls=["", "https://vietnamnews.vn/project"],
            source_dates=["", "2026-08-14"],
        )

        rendered = _source_popover(item)

        self.assertNotIn("rule:신축", rendered)
        self.assertNotIn("판단 규칙", rendered)
        self.assertNotIn("근거 요약", rendered)
        self.assertIn("https://vietnamnews.vn/project", rendered)

    def test_check_lead_requires_an_external_reference(self) -> None:
        item = EvidenceItem(claim="미확정", credibility="unknown", rationale="test")
        linked = IntelligenceItem(
            claim="유사 프로젝트에서 기존 시설 Fit-out이 확인됨",
            credibility="hypothesis",
            source_urls=["https://example.com/case"],
            evidence_labels=["유사 프로젝트"],
        )
        unlinked = linked.model_copy(update={"source_urls": []})

        self.assertIn("확인해볼 단서", _source_popover(item, hypothesis=linked))
        self.assertIn("https://example.com/case", _source_popover(item, hypothesis=linked))
        self.assertNotIn("확인해볼 단서", _source_popover(item, hypothesis=unlinked))

    def test_public_progress_groups_duplicate_reporting_of_one_event(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo")
        result.v2_snapshot.project_intelligence.project_timeline = [
            TimelineItem(
                milestone="NIC and Thermo Fisher signed an MoU.",
                date_or_period="2026-08-14",
                credibility="confirmed",
                evidence_labels=["Vietnam News"],
                source_urls=["https://example.com/news"],
            ),
            TimelineItem(
                milestone="The parties announced an MoU and implementation roadmap.",
                date_or_period="2026-08-14",
                credibility="confirmed",
                evidence_labels=["NIC"],
                source_urls=["https://example.com/official"],
            ),
            TimelineItem(
                milestone="No public evidence of construction start.",
                date_or_period="2026-08-14",
                credibility="confirmed",
            ),
            TimelineItem(
                milestone="NIC Hòa Lạc is an existing/operational NIC campus.",
                date_or_period="2024-04",
                credibility="confirmed",
            ),
        ]

        events = _public_progress_events(result)

        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]["sources"]), 2)

    def test_unknown_role_layer_is_stage_based_and_bounded(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo")
        result.project_stage.value = "사업기획"

        roles = _unknown_roles_for_stage(result)

        self.assertGreaterEqual(len(roles), 3)
        self.assertLessEqual(len(roles), 5)
        self.assertTrue(any("PM" in role for role, _note in roles))

    def test_map_requires_verified_coordinate_pair(self) -> None:
        unknown = ProjectLocation(
            industrial_park="Yen Phong II-C Industrial Park",
            precision="industrial_park",
            status="confirmed",
        )
        confirmed = unknown.model_copy(update={"latitude": 21.18, "longitude": 106.02})

        self.assertEqual(_location_map_rows(unknown), [])
        self.assertEqual(_location_map_rows(confirmed), [{"lat": 21.18, "lon": 106.02}])
        self.assertEqual(_location_zoom(confirmed), 11)
        self.assertIn("Yen Phong II-C", _location_search_query(unknown))

    def test_opportunity_page_renders_streamlit_map_for_verified_location(self) -> None:
        source = """
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.models import ProjectLocation
from src.vietnam_bd.ui_components_v3 import render_page_1_opportunity_v3
from src.vietnam_bd.v3_rule_engine import build_v3_result

result = build_v3_result(demo_v2_result(), "demo")
result.v2_snapshot.project_intelligence.project_location = ProjectLocation(
    site_name="Demo Factory",
    industrial_park="Yen Phong II-C Industrial Park",
    province="Bac Ninh",
    country="Vietnam",
    latitude=21.18,
    longitude=106.02,
    precision="industrial_park",
    status="confirmed",
    confidence="high",
    evidence_summary="Official source confirms the industrial park.",
    evidence_labels=["Official source"],
    source_urls=["https://example.com/location"],
    coordinate_evidence_labels=["Official metadata"],
    coordinate_source_urls=["https://example.com/coordinates"],
)
render_page_1_opportunity_v3(result)
"""

        app = AppTest.from_string(source).run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any(
            "좌표 근거가 확인된 위치만 표시합니다" in item.value
            for item in app.markdown
        ))

    def test_location_name_renders_reference_map_without_coordinates(self) -> None:
        source = """
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.models import ProjectLocation
from src.vietnam_bd.ui_components_v3 import render_page_1_opportunity_v3
from src.vietnam_bd.v3_rule_engine import build_v3_result

result = build_v3_result(demo_v2_result(), "demo")
result.v2_snapshot.project_intelligence.project_location = ProjectLocation(
    site_name="NIC Hòa Lạc",
    industrial_park="Hòa Lạc Hi-Tech Park",
    city="Hà Nội",
    country="Vietnam",
    precision="industrial_park",
    status="confirmed",
    confidence="high",
    evidence_labels=["Official source"],
    source_urls=["https://example.com/location"],
)
render_page_1_opportunity_v3(result)
"""

        app = AppTest.from_string(source).run(timeout=20)

        self.assertFalse(app.exception)
        self.assertTrue(any(
            "공개된 장소명을 기준으로 표시한 참고 위치" in item.value
            for item in app.markdown
        ))

    def test_relationship_map_renders_verified_nodes_and_separate_gaps(self) -> None:
        source = '''
from tests.test_relationship_map_entity_first import nic_thermo_v2_map
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.ui_components_v3 import render_page_1_opportunity_v3
from src.vietnam_bd.v3_rule_engine import build_v3_result

v2 = demo_v2_result()
v2.context.business_structure = []
v2.relationship_map = nic_thermo_v2_map()
render_page_1_opportunity_v3(build_v3_result(v2, "NIC Thermo Fisher MOU"))
'''

        app = AppTest.from_string(source).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(any("Project Layer" in item.value for item in app.markdown))
        self.assertTrue(any("아직 확인되지 않은 역할" in item.value for item in app.markdown))
        self.assertFalse(any("Research Gaps" in item.value for item in app.markdown))
        self.assertFalse(any("Not identified" in item.value and "<svg" in item.value for item in app.markdown))

    def test_strategy_page_renders_internal_owner_and_five_plus_ten_osp_cases(self) -> None:
        source = '''
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.ui_components_v3 import render_page_2_strategy_v3
from src.vietnam_bd.v3_rule_engine import build_v3_result

result = build_v3_result(demo_v2_result(), "Vietnam electronics factory expansion")
render_page_2_strategy_v3(result)
'''

        app = AppTest.from_string(source).run(timeout=30)
        markdown = "\n".join(item.value for item in app.markdown)

        self.assertFalse(app.exception)
        self.assertIn("과거 유사 OSP", markdown)
        self.assertIn("내부 담당자", markdown)
        self.assertIn("사업단계와 고객 과제는 유사도 판단에 사용하지 않습니다", markdown)
        self.assertEqual(markdown.count("<div class='v3-osp-card'>"), 15)
        self.assertIn("data-tooltip=", markdown)
        self.assertIn("제품 조합", markdown)
        self.assertIn("종료일", markdown)
        self.assertNotIn("v3-osp-reasons", markdown)
        self.assertTrue(any("유사 사례 더보기 · 10개" in item.label for item in app.expander))


if __name__ == "__main__":
    unittest.main()
