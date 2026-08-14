from __future__ import annotations

import unittest

from src.vietnam_bd.models import ContextClassification, EvidenceItem
from src.vietnam_bd.research import _attach_context_provenance
from src.vietnam_bd.research_models import EvidenceSource, QuickResearchResult, ResearchEvidence


def evidence_item(claim: str, labels: list[str] | None = None) -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        credibility="likely",
        rationale="test",
        source_labels=labels or [],
    )


class ContextProvenanceTest(unittest.TestCase):
    def test_source_label_url_and_date_stay_aligned(self) -> None:
        context = ContextClassification(
            customer_needs=[],
            building_type=evidence_item("신축", ["rule:신축", "AI attribution"]),
            business_stage=evidence_item("미확정"),
            business_structure=[],
        )
        quick = QuickResearchResult(building_type_signals=[
            ResearchEvidence(
                claim="Project wording",
                credibility="likely",
                source_name="Vietnam News",
                source_url="https://vietnamnews.vn/project",
                sources=[
                    EvidenceSource(
                        name="Vietnam News (Viet Nam News)",
                        url="https://vietnamnews.vn/project",
                        published_date="2026-08-14",
                    ),
                    EvidenceSource(
                        name="NIC report",
                        url="https://nic.gov.vn/report.pdf",
                        published_date="2024-04",
                    ),
                ],
            )
        ])

        enriched = _attach_context_provenance(context, quick).building_type

        self.assertEqual(enriched.source_labels, ["rule:신축", "Vietnam News", "NIC report"])
        self.assertEqual(enriched.source_urls, ["", "https://vietnamnews.vn/project", "https://nic.gov.vn/report.pdf"])
        self.assertEqual(enriched.source_dates, ["", "2026-08-14", "2024-04"])


if __name__ == "__main__":
    unittest.main()
