from __future__ import annotations

import unittest
from unittest.mock import patch

from src.vietnam_bd.engine import ProjectAnalysisInput, analyze_project
from src.vietnam_bd.firecrawl_provider import (
    _collect,
    build_firecrawl_query,
    build_location_query,
    location_needs_supplement,
)
from src.vietnam_bd.research_models import ResearchProjectLocation, SeedUnderstanding
from src.vietnam_bd.telemetry import AnalysisTelemetry, activate, deactivate


class FirecrawlProviderTest(unittest.TestCase):
    class Client:
        def __init__(self, failures=()):
            self.failures = set(failures)

        def search(self, query, domains, limit):
            return [
                {"url": f"https://example.com/{index}", "description": f"claim {index}"}
                for index in range(3)
            ]

        def scrape(self, url):
            if url in self.failures:
                raise TimeoutError("failed")
            return {"markdown": f"content for {url}"}

    def collect(self, failures=()):
        telemetry = AnalysisTelemetry(engine="BD v3", research_provider="firecrawl")
        token = activate(telemetry)
        try:
            result = _collect(self.Client(failures), "query", domains=None, general=True)
        finally:
            deactivate(token)
        return result, telemetry

    def test_one_failed_scrape_keeps_other_sources(self) -> None:
        (documents, urls), telemetry = self.collect({"https://example.com/1"})
        self.assertEqual(len(documents), 2)
        self.assertEqual(len(urls), 2)
        self.assertEqual(telemetry.scrape_attempted_count, 3)
        self.assertEqual(telemetry.scrape_success_count, 2)
        self.assertEqual(telemetry.scrape_failure_count, 1)
        self.assertNotIn("https://example.com/1", urls)

    def test_first_failed_scrape_continues(self) -> None:
        (documents, _), _telemetry = self.collect({"https://example.com/0"})
        self.assertEqual([item["url"] for item in documents], [
            "https://example.com/1", "https://example.com/2"
        ])

    def test_last_failed_scrape_keeps_prior_successes(self) -> None:
        (documents, _), _telemetry = self.collect({"https://example.com/2"})
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[-1]["url"], "https://example.com/1")

    def test_all_failed_scrapes_raise_provider_error(self) -> None:
        with self.assertRaises(RuntimeError):
            self.collect({f"https://example.com/{index}" for index in range(3)})

    def test_existing_is_default_provider(self) -> None:
        self.assertEqual(ProjectAnalysisInput(seed="x").research_provider, "existing")

    def test_query_reuses_multilingual_seed_aliases(self) -> None:
        understanding = SeedUnderstanding(
            company="VSIP",
            project="VSIP Danang Industrial Park",
            location="Dien Ban Bac",
            aliases=["Khu công nghiệp VSIP Đà Nẵng", "Điện Bàn Bắc"],
        )
        query = build_firecrawl_query("seed", understanding)
        self.assertIn("VSIP Danang Industrial Park", query)
        self.assertIn("Khu công nghiệp VSIP Đà Nẵng", query)
        self.assertIn("Điện Bàn Bắc", query)

    def test_location_query_uses_project_and_vietnam_site_terms(self) -> None:
        understanding = SeedUnderstanding(
            company="Samsung Electronics",
            project="New semiconductor plant",
            location="Bac Ninh Vietnam",
        )

        query = build_location_query("seed", understanding)

        self.assertIn("Samsung Electronics", query)
        self.assertIn("New semiconductor plant", query)
        self.assertIn("industrial park", query)
        self.assertIn("khu cong nghiep", query)
        self.assertIn("project site", query)

    def test_location_supplement_is_bounded_to_insufficient_results(self) -> None:
        self.assertTrue(location_needs_supplement(ResearchProjectLocation()))
        self.assertTrue(location_needs_supplement(ResearchProjectLocation(
            province="Bac Ninh", precision="province", status="partial",
        )))
        self.assertFalse(location_needs_supplement(ResearchProjectLocation(
            industrial_park="Yen Phong II-C Industrial Park",
            precision="industrial_park",
            status="confirmed",
        )))

    def test_research_provider_dispatch_does_not_change_existing_default(self) -> None:
        from src.vietnam_bd import research
        bundle = object()
        rule = object()
        with patch("src.vietnam_bd.firecrawl_provider.research_opportunity_firecrawl", return_value=(bundle, rule)) as mocked:
            result = research.research_opportunity("seed", research_provider="firecrawl")
        self.assertEqual(result, (bundle, rule))
        mocked.assert_called_once()

    def test_unknown_provider_is_rejected_instead_of_falling_back(self) -> None:
        input_data = ProjectAnalysisInput(seed="x")
        input_data.research_provider = "unknown"  # type: ignore[assignment]
        with self.assertRaises(ValueError):
            analyze_project(input_data)



if __name__ == "__main__":
    unittest.main()
