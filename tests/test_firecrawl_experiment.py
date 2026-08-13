from __future__ import annotations

import unittest

from src.vietnam_bd.firecrawl_experiment import run_priority_source_experiment
from src.vietnam_bd.priority_sources import PRIORITY_SOURCES


class FirecrawlPriorityExperimentTest(unittest.TestCase):
    def test_priority_domains_are_configured_separately(self) -> None:
        self.assertEqual(len(PRIORITY_SOURCES), 8)
        self.assertIn("vir.com.vn", PRIORITY_SOURCES)
        self.assertIn("vsip.com", PRIORITY_SOURCES)

    def test_priority_then_targeted_general_and_deduplication(self) -> None:
        calls = []

        def runner(query, domains, limit):
            calls.append((query, domains, limit))
            if domains:
                return [
                    {
                        "url": "https://www.vir.com.vn/project/?utm_source=x#story",
                        "title": "Project",
                        "description": "VSIP project approved",
                    }
                ]
            return [
                {
                    "url": "http://vir.com.vn/project",
                    "title": "duplicate URL",
                    "description": "VSIP project approved",
                },
                {
                    "url": "https://vnexpress.net/project",
                    "title": "Independent source",
                    "description": "EPC remains unknown",
                },
            ]

        result = run_priority_source_experiment(
            "VSIP Danang Industrial Park",
            missing_intelligence=["EPC", "Designer"],
            search_runner=runner,
        )

        self.assertEqual(calls[0][1], PRIORITY_SOURCES)
        self.assertIsNone(calls[1][1])
        self.assertIn("EPC Designer", calls[1][0])
        self.assertEqual(result.priority_sources[0].source_tier, 1)
        self.assertEqual(result.priority_sources[0].source_type, "priority")
        self.assertEqual(len(result.general_sources), 1)
        self.assertEqual(result.general_sources[0].source_tier, 2)
        self.assertEqual(result.general.new_sources, 1)
        self.assertIn("PRIORITY SOURCE RESEARCH", result.summary_text())
        self.assertIn("EPC, Designer", result.summary_text())

    def test_general_search_is_skipped_when_priority_is_sufficient(self) -> None:
        calls = []

        def runner(query, domains, limit):
            calls.append(domains)
            return [
                {"url": "https://vir.com.vn/a", "description": "claim a"},
                {"url": "https://baodautu.vn/b", "description": "claim b"},
            ]

        result = run_priority_source_experiment(
            "VSIP Danang", search_runner=runner, minimum_priority_sources=2
        )
        self.assertTrue(result.general_search_skipped)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
