from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.vietnam_bd.models import EvidenceItem
from src.vietnam_bd.research_contribution import (
    normalize_source_url,
    record_final_output_contribution,
    record_quick_research_contribution,
    record_round_research_contribution,
)
from src.vietnam_bd.research_models import (
    DeepResearchResult,
    DiscoveredEntity,
    EvidenceSource,
    QuickResearchResult,
    ResearchEvidence,
    ResearchRoundResult,
)
from src.vietnam_bd.telemetry import AnalysisTelemetry, activate, deactivate


def evidence(claim: str, url: str) -> ResearchEvidence:
    return ResearchEvidence(
        claim=claim,
        credibility="confirmed",
        source_name="source",
        source_url=url,
        sources=[EvidenceSource(name="source", url=url)],
    )


class ResearchContributionTest(unittest.TestCase):
    def test_url_normalization_is_intentionally_bounded(self) -> None:
        left = normalize_source_url("https://www.example.com/project/?utm_source=x#details")
        right = normalize_source_url("http://example.com/project")
        self.assertEqual(left, right)

    def test_duplicate_and_new_contribution_and_gap_resolution(self) -> None:
        telemetry = AnalysisTelemetry(engine="BD v3")
        token = activate(telemetry)
        try:
            primary = QuickResearchResult(
                company="ACME",
                project_name="Factory A",
                stage_signals=[evidence("Construction started", "https://www.example.com/a/?utm_source=x")],
            )
            supplement = QuickResearchResult(
                company="ACME",
                project_name="Factory A",
                stage_signals=[
                    evidence("  construction   STARTED ", "http://example.com/a#news"),
                    evidence("EPC selected", "https://example.com/b?gclid=tracking"),
                ],
            )
            record_quick_research_contribution("Primary context research", primary)
            record_quick_research_contribution(
                "Supplementary context research 1",
                supplement,
                primary_missing=["stage_evidence", "minimum_sources"],
                missing_after=["minimum_sources"],
            )
            record_final_output_contribution(SimpleNamespace(evidence=[
                EvidenceItem(
                    claim="EPC selected", credibility="confirmed", rationale="test"
                )
            ]))
        finally:
            deactivate(token)

        primary_metric, supplement_metric = telemetry.research_contribution
        self.assertEqual(primary_metric["new_source_count"], 1)
        self.assertEqual(supplement_metric["duplicate_evidence_count"], 1)
        self.assertEqual(supplement_metric["new_evidence_count"], 1)
        self.assertEqual(supplement_metric["duplicate_source_count"], 1)
        self.assertEqual(supplement_metric["new_source_count"], 1)
        self.assertEqual(supplement_metric["duplicate_entity_count"], 3)
        self.assertEqual(supplement_metric["new_entity_count"], 1)
        self.assertEqual(supplement_metric["supplementary_resolved"], ["stage_evidence"])
        self.assertEqual(supplement_metric["still_missing"], ["minimum_sources"])
        self.assertEqual(supplement_metric["final_output_evidence_count"], 1)
        summary = telemetry.summary_text()
        self.assertIn("Primary missing: stage_evidence, minimum_sources", summary)
        self.assertIn("Supplementary resolved: stage_evidence", summary)
        self.assertIn("Still missing: minimum_sources", summary)

    def test_research_round_uses_structured_discovered_entities(self) -> None:
        telemetry = AnalysisTelemetry(engine="BD v3")
        token = activate(telemetry)
        try:
            round_result = ResearchRoundResult(
                round_number=1,
                focus="remaining scope",
                findings=DeepResearchResult(
                    project_ecosystem=[evidence("ABC is EPC", "https://example.com/epc")]
                ),
                discovered_entities=[
                    DiscoveredEntity(name="ABC", entity_type="epc", credibility="confirmed")
                ],
            )
            record_round_research_contribution("Limited research round 1", round_result)
        finally:
            deactivate(token)

        metric = telemetry.research_contribution[0]
        self.assertEqual(metric["evidence_count"], 1)
        self.assertEqual(metric["entity_count"], 1)
        self.assertEqual(metric["new_entity_count"], 1)

    def test_existing_telemetry_fields_remain_present(self) -> None:
        telemetry = AnalysisTelemetry(engine="BD v3")
        payload = telemetry.to_dict()
        for key in ("run_id", "engine", "started_at", "ended_at", "steps", "totals", "error_type"):
            self.assertIn(key, payload)
        self.assertIn("research_contribution", payload)


if __name__ == "__main__":
    unittest.main()
