from __future__ import annotations

import unittest

from src.vietnam_bd.reasoning import build_project_location
from src.vietnam_bd.research import merge_quick_research
from src.vietnam_bd.research_models import (
    DeepResearchResult,
    EvidenceSource,
    QuickResearchResult,
    ResearchBundle,
    ResearchEvidence,
    ResearchProjectLocation,
)


def evidence(claim: str, *, credibility: str = "confirmed") -> ResearchEvidence:
    return ResearchEvidence(
        claim=claim,
        credibility=credibility,
        rationale="Official project statement",
        sources=[EvidenceSource(
            name="Official source",
            url="https://example.com/location",
            source_type="official",
        )],
    )


def bundle(location: ResearchProjectLocation) -> ResearchBundle:
    return ResearchBundle(
        quick=QuickResearchResult(
            company="Samsung Electronics",
            project_name="New Factory",
            project_location=location,
        ),
        research_mode="deep",
        stage_gate_status="targeting",
        stage_gate_reason="test",
        deep=DeepResearchResult(company="Samsung Electronics"),
    )


class ProjectLocationTest(unittest.TestCase):
    def test_confirmed_industrial_park_keeps_verified_coordinates(self) -> None:
        location = build_project_location(bundle(ResearchProjectLocation(
            site_name="New Factory",
            industrial_park="Yen Phong II-C Industrial Park",
            province="Bac Ninh",
            country="Vietnam",
            latitude=21.18,
            longitude=106.02,
            precision="industrial_park",
            status="confirmed",
            confidence="high",
            evidence=[evidence(
                "The factory will be located in Yen Phong II-C Industrial Park, Bac Ninh."
            )],
            coordinate_evidence=[evidence(
                "Official location metadata provides coordinates 21.18, 106.02."
            )],
        )))

        self.assertEqual(location.status, "confirmed")
        self.assertEqual(location.precision, "industrial_park")
        self.assertEqual((location.latitude, location.longitude), (21.18, 106.02))
        self.assertEqual(
            [(item.subject, item.object) for item in location.relationships],
            [
                ("New Factory", "Yen Phong II-C Industrial Park"),
                ("Yen Phong II-C Industrial Park", "Bac Ninh"),
                ("Bac Ninh", "Vietnam"),
            ],
        )

    def test_province_only_is_partial_even_with_confirmed_source(self) -> None:
        location = build_project_location(bundle(ResearchProjectLocation(
            province="Bac Ninh",
            country="Vietnam",
            precision="province",
            status="confirmed",
            confidence="high",
            evidence=[evidence("The project will be developed in Bac Ninh Province.")],
        )))

        self.assertEqual(location.status, "partial")
        self.assertEqual(location.precision, "province")

    def test_unverified_coordinates_are_removed(self) -> None:
        location = build_project_location(bundle(ResearchProjectLocation(
            industrial_park="Yen Phong II-C Industrial Park",
            latitude=21.18,
            longitude=106.02,
            precision="industrial_park",
            status="confirmed",
            evidence=[evidence("The factory is in Yen Phong II-C Industrial Park.")],
        )))

        self.assertIsNone(location.latitude)
        self.assertIsNone(location.longitude)

    def test_location_without_evidence_remains_unknown(self) -> None:
        location = build_project_location(bundle(ResearchProjectLocation(
            industrial_park="Guessed Industrial Park",
            precision="industrial_park",
            status="confirmed",
        )))

        self.assertEqual(location.status, "unknown")
        self.assertEqual(location.precision, "unknown")

    def test_location_merge_prefers_more_specific_supported_result(self) -> None:
        base = QuickResearchResult(project_location=ResearchProjectLocation(
            province="Bac Ninh",
            precision="province",
            status="confirmed",
            evidence=[evidence("The project is in Bac Ninh Province.")],
        ))
        supplement = QuickResearchResult(project_location=ResearchProjectLocation(
            industrial_park="Yen Phong II-C Industrial Park",
            precision="industrial_park",
            status="partial",
            evidence=[evidence("The project site is Yen Phong II-C Industrial Park.")],
        ))

        merged = merge_quick_research(base, supplement)

        self.assertEqual(merged.project_location.precision, "industrial_park")


if __name__ == "__main__":
    unittest.main()
