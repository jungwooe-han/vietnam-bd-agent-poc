from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.vietnam_bd.dx_portfolio import match_dx_portfolio
from src.vietnam_bd.models import (
    BDV2Stakeholder,
    ContextClassification,
    EvidenceItem,
    IntelligenceItem,
    ProjectIntelligence,
    RelationshipDecisionMap,
    StageGate,
    BusinessDevelopmentDecision,
)
from pydantic import ValidationError
from src.vietnam_bd.reasoning import (
    align_stakeholders_to_relationship_map,
    build_must_know_top3,
    build_project_intelligence,
    build_proposal_hypotheses,
    build_relationship_map,
    decide_business_development,
)
from src.vietnam_bd.research_models import (
    DeepResearchResult,
    DiscoveredEntity,
    EvidenceSource,
    QuickResearchResult,
    ResearchBundle,
    ResearchEvidence,
    ResearchRoundResult,
)
from src.vietnam_bd.rule_engine import RuleEngineResult
from src.vietnam_bd.sfdc_sample import load_sample_opportunities, match_sample_opportunities


def evidence(claim: str, credibility: str = "likely", labels: list[str] | None = None) -> EvidenceItem:
    return EvidenceItem(claim=claim, credibility=credibility, rationale="test", source_labels=labels or [])


def rule(stage: str, gate: str, *, need: bool = True, supported: bool = True) -> RuleEngineResult:
    labels = ["current-project-source"] if supported else []
    context = ContextClassification(
        customer_needs=[evidence("RE100 / ESG / OPEX 절감", labels=labels)] if need else [evidence("미확정", "unknown")],
        building_type=evidence("신축", labels=labels),
        business_stage=evidence(stage, labels=labels),
        business_structure=[evidence("End Client", labels=labels)] if supported else [],
    )
    depth = "deep" if gate in {"targeting", "golden_time"} else "limited"
    return RuleEngineResult(context=context, stage_gate=StageGate(
        status=gate,
        research_depth=depth,
        active_pursuit="limited" if gate == "local_action" else "active",
        rationale="test gate",
        remaining_window="test",
        recommended_focus="test",
    ))


def bundle(*, deep: DeepResearchResult | None = None, rounds: list[ResearchRoundResult] | None = None) -> ResearchBundle:
    return ResearchBundle(
        quick=QuickResearchResult(company="VinFast", project_name="Factory"),
        research_mode="limited",
        stage_gate_status="local_action",
        stage_gate_reason="test",
        deep=deep,
        research_rounds=rounds or [],
    )


def open_intelligence() -> ProjectIntelligence:
    return ProjectIntelligence(open_scopes=[IntelligenceItem(
        claim="DX facility package remains open",
        credibility="likely",
        rationale="current tender",
        evidence_labels=["current-tender"],
        source_urls=["https://example.com/tender"],
        temporal_scope="current",
    )])


class FinalDecisionTest(unittest.TestCase):
    def test_user_decision_schema_accepts_only_three_states(self) -> None:
        with self.assertRaises(ValidationError):
            BusinessDevelopmentDecision(
                decision="needs_confirm",
                headline="invalid",
                rationale="invalid",
                action_direction="invalid",
            )

    def test_golden_time_without_dx_scope_evidence_is_monitor(self) -> None:
        rules = rule("설계 - DD (기본)", "golden_time", need=False, supported=False)
        decision = decide_business_development(bundle(), rules, ProjectIntelligence(), [])
        self.assertEqual(decision.decision, "monitor")

    def test_targeting_without_entry_conditions_is_monitor(self) -> None:
        rules = rule("사업기획", "targeting", supported=False)
        matches = match_dx_portfolio(rules.context)
        decision = decide_business_development(bundle(), rules, ProjectIntelligence(), matches)
        self.assertEqual(decision.decision, "monitor")

    def test_local_action_with_supported_dx_scope_is_now(self) -> None:
        rules = rule("시공", "local_action")
        matches = match_dx_portfolio(rules.context)
        decision = decide_business_development(bundle(), rules, open_intelligence(), matches)
        self.assertEqual(decision.decision, "now")
        self.assertTrue(decision.scope_open)
        self.assertTrue(decision.dx_addressable)
        self.assertTrue(decision.evidence_sufficient)

    def test_construction_with_open_dx_scope_is_not_closed(self) -> None:
        rules = rule("시공", "local_action")
        decision = decide_business_development(
            bundle(), rules, open_intelligence(), match_dx_portfolio(rules.context),
        )
        self.assertNotEqual(decision.decision, "closed")

    def test_closed_requires_supported_completion_or_award_evidence(self) -> None:
        rules = rule("프로젝트 종료", "closed")
        rules.stage_gate.active_pursuit = "stop"
        matches = match_dx_portfolio(rules.context)
        unsupported = decide_business_development(bundle(), rules, ProjectIntelligence(), matches)
        self.assertEqual(unsupported.decision, "monitor")
        intelligence = ProjectIntelligence(current_project_facts=[IntelligenceItem(
            claim="Relevant package award completed",
            credibility="confirmed",
            rationale="official award",
            evidence_labels=["award notice"],
            source_urls=["https://example.com/award"],
            temporal_scope="current",
        )])
        supported = decide_business_development(bundle(), rules, intelligence, matches)
        self.assertEqual(supported.decision, "closed")


class RelationshipIntegrityTest(unittest.TestCase):
    def _map(self):
        historical = ResearchEvidence(
            claim="ABC Engineering was EPC on a prior owner project",
            credibility="confirmed",
            rationale="historical award",
            sources=[EvidenceSource(name="Historical award", url="https://example.com/history")],
        )
        rnd = ResearchRoundResult(
            round_number=1,
            focus="actors",
            findings=DeepResearchResult(),
            discovered_entities=[
                DiscoveredEntity(name="ABC Engineering", entity_type="epc", credibility="confirmed", evidence_labels=["Historical award"], source_urls=["https://example.com/history"]),
                DiscoveredEntity(name="Current PM Co", entity_type="pm_cm", credibility="likely", evidence_labels=["Current project article"]),
                DiscoveredEntity(name="Unsupported GC", entity_type="gc", credibility="likely"),
            ],
        )
        b = bundle(deep=DeepResearchResult(historical_projects=[historical]), rounds=[rnd])
        intelligence = build_project_intelligence(b)
        return b, build_relationship_map(b, intelligence)

    def test_historical_partner_never_becomes_current_confirmed(self) -> None:
        _, relationship_map = self._map()
        actor = next(item for item in relationship_map.actors if item.organization == "ABC Engineering")
        self.assertEqual(actor.actor_status, "candidate")
        self.assertEqual(actor.temporal_scope, "historical")
        self.assertNotEqual(actor.credibility, "confirmed")

    def test_likely_requires_current_project_evidence(self) -> None:
        _, relationship_map = self._map()
        supported = next(item for item in relationship_map.actors if item.organization == "Current PM Co")
        unsupported = next(item for item in relationship_map.actors if item.organization == "Unsupported GC")
        self.assertEqual(supported.actor_status, "likely")
        self.assertEqual(unsupported.actor_status, "unknown")

    def test_actor_who_to_meet_and_must_know_share_actor_id(self) -> None:
        b, relationship_map = self._map()
        rules = rule("시공", "local_action")
        decision = decide_business_development(b, rules, ProjectIntelligence(), match_dx_portfolio(rules.context))
        must_knows = build_must_know_top3(b, decision, relationship_map, match_dx_portfolio(rules.context))
        stakeholders = align_stakeholders_to_relationship_map([], relationship_map, must_knows)
        must_actor_ids = {actor_id for item in must_knows for actor_id in item.actor_ids}
        self.assertTrue(must_actor_ids)
        self.assertTrue(all(item.actor_id in must_actor_ids for item in stakeholders))


class ProposalAndInternalDataTest(unittest.TestCase):
    def test_long_research_provenance_is_bounded_at_output_models(self) -> None:
        rules = rule("사업기획", "targeting")
        matches = match_dx_portfolio(rules.context)
        self.assertTrue(matches)
        matches[0].evidence_labels = [f"source-{index}" for index in range(20)]
        decision = decide_business_development(bundle(), rules, ProjectIntelligence(), matches)
        must_knows = build_must_know_top3(
            bundle(), decision, RelationshipDecisionMap(), matches,
        )
        proposals = build_proposal_hypotheses(decision, matches, must_knows)
        self.assertTrue(must_knows)
        self.assertTrue(proposals)
        self.assertLessEqual(len(must_knows[0].evidence_labels), 8)
        self.assertLessEqual(len(proposals[0].evidence_labels), 8)

    def test_monitor_keeps_conditional_proposal_hypothesis(self) -> None:
        rules = rule("사업기획", "targeting")
        matches = match_dx_portfolio(rules.context)
        decision = decide_business_development(bundle(), rules, ProjectIntelligence(), matches)
        proposals = build_proposal_hypotheses(decision, matches, [])
        self.assertEqual(decision.decision, "monitor")
        self.assertTrue(proposals)
        self.assertTrue(all(item.mode == "conditional" for item in proposals))

    def test_sfdc_sample_is_separate_from_research_evidence(self) -> None:
        records = load_sample_opportunities()
        self.assertEqual(len(records), 50)
        rules = rule("설계 - DD (기본)", "golden_time")
        matches = match_sample_opportunities("VinFast", rules.context, ["Facility Energy"])
        self.assertTrue(matches)
        external = build_project_intelligence(bundle())
        serialized_external = external.model_dump_json()
        self.assertNotIn(matches[0].record.oppty, serialized_external)
        metadata = json.loads(Path("data/sfdc_sample_opportunities.json").read_text(encoding="utf-8"))["metadata"]
        self.assertTrue(metadata["synthetic"])
        self.assertFalse(metadata["external_research_evidence"])


if __name__ == "__main__":
    unittest.main()
