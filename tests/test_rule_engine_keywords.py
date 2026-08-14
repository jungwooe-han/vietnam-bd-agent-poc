from __future__ import annotations

import unittest

from src.vietnam_bd.rule_engine import evaluate_context


class RuleKeywordBoundaryTest(unittest.TestCase):
    def test_startups_does_not_trigger_ups_need(self) -> None:
        result = evaluate_context("The laboratory will serve businesses, start-ups and universities.")

        self.assertNotIn(
            "전력 안정성 / Energy Security",
            [item.claim for item in result.context.customer_needs],
        )

    def test_standalone_ups_triggers_energy_security(self) -> None:
        result = evaluate_context("The facility requires a UPS for power continuity.")

        self.assertIn(
            "전력 안정성 / Energy Security",
            [item.claim for item in result.context.customer_needs],
        )


if __name__ == "__main__":
    unittest.main()
