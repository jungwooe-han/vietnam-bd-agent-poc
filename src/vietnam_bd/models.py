from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


Credibility = Literal["confirmed", "likely", "hypothesis", "unknown"]
StageGateStatus = Literal["targeting", "golden_time", "local_action", "closed", "unknown"]
ResearchDepth = Literal["deep", "limited", "stop"]
Level = Literal["high", "medium", "low", "unknown"]


def _bounded_strings(value: object, limit: int) -> object:
    if not isinstance(value, list):
        return value
    return list(dict.fromkeys(item for item in value if isinstance(item, str) and item))[:limit]


class EvidenceItem(BaseModel):
    claim: str
    credibility: Credibility
    rationale: str
    source_labels: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list, max_length=10)
    source_dates: list[str] = Field(default_factory=list, max_length=10)
    source_conflicts: list[str] = Field(default_factory=list, max_length=5)


# Existing BD result models. Keep these names stable for analysis.py, demo, and UI.
class Stakeholder(BaseModel):
    role: str
    priority: Literal["primary", "secondary", "optional"]
    why_meet: str
    information_to_get: list[str] = Field(default_factory=list)


class DiscoveryQuestion(BaseModel):
    question: str
    why_it_matters: str
    decision_enabled: str
    if_yes: str
    if_no_or_unknown: str


class PortfolioRecommendation(BaseModel):
    lead_domain: str
    lead_reason: str
    supporting_domains: list[str] = Field(default_factory=list, max_length=4)
    conversation_entry: str
    relevant_capabilities: list[str] = Field(default_factory=list, max_length=6)
    caution: str


class SimilarCase(BaseModel):
    case_id: str
    title: str
    similarity_reason: str
    internal_owner: str | None = None
    lesson_learned: str | None = None


class AnalysisResult(BaseModel):
    opportunity_title: str
    executive_summary: str
    why_opportunity_now: str
    current_stage: str
    stage_basis: str
    business_objective: EvidenceItem
    decision_drivers: list[EvidenceItem] = Field(default_factory=list, max_length=4)
    customer_needs: list[EvidenceItem] = Field(default_factory=list, max_length=6)
    critical_unknowns: list[str] = Field(default_factory=list, max_length=6)
    portfolio: PortfolioRecommendation
    stakeholders: list[Stakeholder] = Field(default_factory=list, max_length=5)
    priority_questions: list[DiscoveryQuestion] = Field(default_factory=list, min_length=3, max_length=5)
    next_steps: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    similar_cases: list[SimilarCase] = Field(default_factory=list, max_length=3)
    source_summary: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# BD v2 models. The final result has a distinct name so the legacy path stays intact.
class ContextClassification(BaseModel):
    customer_needs: list[EvidenceItem] = Field(default_factory=list, max_length=8)
    building_type: EvidenceItem
    business_stage: EvidenceItem
    business_structure: list[EvidenceItem] = Field(default_factory=list, max_length=8)


class StageGate(BaseModel):
    status: StageGateStatus
    research_depth: ResearchDepth
    active_pursuit: Literal["active", "limited", "stop"] = "active"
    historical_intelligence: Literal["deep", "limited", "none"] = "none"
    rationale: str
    remaining_window: str
    recommended_focus: str


class GroundedCapability(BaseModel):
    capability: str
    rationale: str
    context_basis: list[str] = Field(default_factory=list, max_length=6)
    evidence_labels: list[str] = Field(default_factory=list, max_length=6)
    credibility: Credibility
    caution: str = ""


class WorkstreamRecommendation(BaseModel):
    rank: int = Field(ge=1, le=3)
    workstream: str
    why_relevant: str
    context_basis: list[str] = Field(default_factory=list, max_length=6)
    possible_capabilities: list[str] = Field(default_factory=list, max_length=6)
    grounded_capabilities: list[GroundedCapability] = Field(default_factory=list, max_length=4)
    caution: str = ""


class ExcludedWorkstream(BaseModel):
    workstream: str
    reason: str


class AccessibilityFactor(BaseModel):
    level: Level
    rationale: str
    evidence_labels: list[str] = Field(default_factory=list)


class CanWeEnter(BaseModel):
    timing: AccessibilityFactor
    access: AccessibilityFactor
    openness: AccessibilityFactor
    fit: AccessibilityFactor
    overall_view: str


class InformationToConfirm(BaseModel):
    topic: str
    why_it_matters: str
    action_if_confirmed: str
    action_if_not_confirmed: str
    suggested_way_to_check: str


class BDV2Stakeholder(BaseModel):
    actor_id: str = ""
    role: str
    organization_or_candidate: str | None = None
    priority: Literal["primary", "secondary", "optional"]
    credibility: Credibility
    why_meet: str
    information_to_get: list[str] = Field(default_factory=list, max_length=5)
    evidence_labels: list[str] = Field(default_factory=list, max_length=6)
    rationale: str = ""

    @field_validator("evidence_labels", mode="before")
    @classmethod
    def bound_evidence_labels(cls, value: object) -> object:
        return _bounded_strings(value, 6)


class TalkingPoint(BaseModel):
    question: str
    information_goal: str
    why_it_matters: str
    next_action_if_positive: str
    next_action_if_negative_or_unknown: str


class MeetingTalkingPoints(BaseModel):
    open: list[TalkingPoint] = Field(default_factory=list, max_length=4)
    power: list[TalkingPoint] = Field(default_factory=list, max_length=4)
    win: list[TalkingPoint] = Field(default_factory=list, max_length=4)


class NextBestAction(BaseModel):
    action: str
    target: str
    purpose: str
    done_criteria: str
    priority: Literal["now", "next", "later"]


class BDV2SimilarCase(BaseModel):
    case_id: str
    title: str
    similarity_reason: str
    internal_owner: str | None = None
    lesson_learned: str | None = None


class BusinessDevelopmentDecision(BaseModel):
    decision: Literal["now", "monitor", "closed"]
    headline: str
    rationale: str
    context_basis: list[str] = Field(default_factory=list, max_length=8)
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    action_direction: str
    trigger_to_reassess: str = ""
    priority_window: bool = False
    intervention_possible: bool = False
    scope_open: bool = False
    dx_addressable: bool = False
    evidence_sufficient: bool = False


class IntelligenceItem(BaseModel):
    claim: str
    credibility: Credibility
    rationale: str = ""
    evidence_labels: list[str] = Field(default_factory=list, max_length=10)
    source_urls: list[str] = Field(default_factory=list, max_length=10)
    source_dates: list[str] = Field(default_factory=list, max_length=10)
    temporal_scope: Literal["current", "historical", "candidate", "unknown"] = "unknown"

    @field_validator("evidence_labels", "source_urls", "source_dates", mode="before")
    @classmethod
    def bound_provenance(cls, value: object) -> object:
        return _bounded_strings(value, 10)


class ProjectActor(BaseModel):
    actor_id: str
    role: str
    organization: str
    temporal_scope: Literal["current", "historical", "candidate", "unknown"]
    actor_status: Literal["confirmed", "likely", "candidate", "unknown"] = "unknown"
    participation_status: str
    credibility: Credibility
    rationale: str = ""
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[str] = Field(default_factory=list, max_length=8)
    source_dates: list[str] = Field(default_factory=list, max_length=8)
    confirmation_needed: str = ""

    @field_validator("evidence_labels", "source_urls", "source_dates", mode="before")
    @classmethod
    def bound_provenance(cls, value: object) -> object:
        return _bounded_strings(value, 8)


class ProjectRelationship(BaseModel):
    from_actor_id: str
    to_actor_id: str
    relationship_type: str
    description: str = ""
    temporal_scope: Literal["current", "historical", "candidate", "unknown"]
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[str] = Field(default_factory=list, max_length=8)
    source_dates: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("evidence_labels", "source_urls", "source_dates", mode="before")
    @classmethod
    def bound_provenance(cls, value: object) -> object:
        return _bounded_strings(value, 8)


class RelationshipDecisionMap(BaseModel):
    actors: list[ProjectActor] = Field(default_factory=list, max_length=20)
    relationships: list[ProjectRelationship] = Field(default_factory=list, max_length=30)
    decision_structure_summary: str = ""
    unknown_critical_actors: list[str] = Field(default_factory=list, max_length=10)


class PartnerPattern(BaseModel):
    partner: str
    role: str
    historical_project_count: int = Field(default=0, ge=0)
    pattern_summary: str
    current_participation: Literal["confirmed", "likely", "unconfirmed", "not_found"] = "unconfirmed"
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list)


class TimelineItem(BaseModel):
    milestone: str
    date_or_period: str
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list)


class ProjectIntelligence(BaseModel):
    owner_summary: str = ""
    current_project_facts: list[IntelligenceItem] = Field(default_factory=list, max_length=15)
    historical_projects: list[IntelligenceItem] = Field(default_factory=list, max_length=15)
    project_ecosystem: list[IntelligenceItem] = Field(default_factory=list, max_length=15)
    ecosystem_candidates: list[IntelligenceItem] = Field(default_factory=list, max_length=15)
    repeated_partner_patterns: list[PartnerPattern] = Field(default_factory=list, max_length=10)
    project_timeline: list[TimelineItem] = Field(default_factory=list, max_length=12)
    open_scopes: list[IntelligenceItem] = Field(default_factory=list, max_length=10)
    watch_signals: list[str] = Field(default_factory=list, max_length=10)
    next_trigger: str = ""
    unresolved_gaps: list[str] = Field(default_factory=list, max_length=15)
    source_conflicts: list[str] = Field(default_factory=list, max_length=10)


class StakeholderMeetingPlan(BaseModel):
    actor_id: str = ""
    stakeholder_role: str
    why_meet: str
    information_to_obtain: list[str] = Field(default_factory=list, max_length=6)
    open: list[TalkingPoint] = Field(default_factory=list, max_length=3)
    power: list[TalkingPoint] = Field(default_factory=list, max_length=3)
    win: list[TalkingPoint] = Field(default_factory=list, max_length=3)


class MustKnowItem(BaseModel):
    rank: int = Field(ge=1, le=3)
    question: str
    why_it_matters: str
    decision_impact: list[Literal["scope", "actor", "buying_route", "workstream", "decision"]] = Field(default_factory=list)
    actor_ids: list[str] = Field(default_factory=list, max_length=5)
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    suggested_way_to_check: str

    @field_validator("evidence_labels", mode="before")
    @classmethod
    def bound_evidence_labels(cls, value: object) -> object:
        return _bounded_strings(value, 8)


class ProposalHypothesis(BaseModel):
    rank: int = Field(ge=1, le=3)
    workstream: str
    capability: str
    hypothesis: str
    mode: Literal["actionable", "conditional"]
    conditions_to_confirm: list[str] = Field(default_factory=list, max_length=4)
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    portfolio_source_url: str = ""

    @field_validator("evidence_labels", mode="before")
    @classmethod
    def bound_evidence_labels(cls, value: object) -> object:
        return _bounded_strings(value, 8)


class SFDCOpportunity(BaseModel):
    oppty: str
    account: str
    vertical: str
    size: str
    owner: str


class SFDCMatch(BaseModel):
    record: SFDCOpportunity
    similarity_reason: str
    match_score: int = Field(ge=0, le=100)


class BDV2AnalysisResult(BaseModel):
    opportunity_title: str
    executive_summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=15)
    context: ContextClassification
    stage_gate: StageGate
    workstreams: list[WorkstreamRecommendation] = Field(default_factory=list, max_length=3)
    excluded_workstreams: list[ExcludedWorkstream] = Field(default_factory=list, max_length=5)
    can_we_enter: CanWeEnter
    information_to_confirm: list[InformationToConfirm] = Field(default_factory=list, max_length=6)
    stakeholders: list[BDV2Stakeholder] = Field(default_factory=list, max_length=6)
    talking_points: MeetingTalkingPoints
    next_best_actions: list[NextBestAction] = Field(default_factory=list, max_length=3)
    similar_cases: list[BDV2SimilarCase] = Field(default_factory=list, max_length=3)
    source_summary: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    # Every v2 result has exactly one business decision. Keeping this required
    # avoids an unnecessary Optional/Union at the structured-output root.
    bd_decision: BusinessDevelopmentDecision
    project_intelligence: ProjectIntelligence = Field(default_factory=ProjectIntelligence)
    relationship_map: RelationshipDecisionMap = Field(default_factory=RelationshipDecisionMap)
    stakeholder_meeting_plans: list[StakeholderMeetingPlan] = Field(default_factory=list, max_length=6)
    must_know_top3: list[MustKnowItem] = Field(default_factory=list, max_length=3)
    proposal_hypotheses: list[ProposalHypothesis] = Field(default_factory=list, max_length=3)
    sample_sfdc_matches: list[SFDCMatch] = Field(default_factory=list, max_length=5)
