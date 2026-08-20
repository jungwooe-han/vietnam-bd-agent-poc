from __future__ import annotations

import unittest

from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.osp_matching import load_osp_records, match_osp_cases
from src.vietnam_bd.v3_rule_engine import build_v3_result


class OSPMatchingTest(unittest.TestCase):
    def test_osp_workbook_rows_are_loaded_with_sales_fields(self) -> None:
        records = load_osp_records()

        self.assertEqual(len(records), 50)
        self.assertTrue(all(record.osp and record.opportunity and record.owner for record in records))
        self.assertGreaterEqual({record.status for record in records}, {"Closed Won", "Closed Lost"})
        self.assertTrue(all(record.created_at for record in records))

    def test_osp_matching_returns_five_plus_ten_with_friendly_reasons(self) -> None:
        result = build_v3_result(
            demo_v2_result(),
            "Vietnam semiconductor R&D laboratory new-build opportunity in Bac Ninh",
        )
        result.opportunity_title = "Vietnam semiconductor R&D laboratory"
        result.v2_snapshot.project_intelligence.project_location.province = "Bac Ninh"

        matches = match_osp_cases(result, limit=15)

        self.assertEqual(len(matches[:5]), 5)
        self.assertEqual(len(matches[5:15]), 10)
        self.assertTrue(all(match.record.owner for match in matches))
        self.assertTrue(all(match.reasons for match in matches))
        self.assertTrue(all("점수" not in " ".join(match.reasons) for match in matches))

    def test_stage_and_customer_need_do_not_change_osp_ranking(self) -> None:
        base = build_v3_result(demo_v2_result(), "Vietnam electronics factory expansion")
        changed = base.model_copy(deep=True)
        changed.project_stage.value = "프로젝트 종료"
        changed.customer_needs = [
            item.model_copy(update={"value": "완전히 다른 고객 과제"})
            for item in changed.customer_needs
        ]

        base_ids = [match.record.osp for match in match_osp_cases(base, limit=15)]
        changed_ids = [match.record.osp for match in match_osp_cases(changed, limit=15)]

        self.assertEqual(changed_ids, base_ids)
