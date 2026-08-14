from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .models import BDV2AnalysisResult, EvidenceItem


V3EvidenceStatus = Literal["confirmed", "likely", "candidate", "inferred", "unknown"]
# Persisted BD v3 records span both the original status vocabulary
# ("inferred") and the entity-first relationship map vocabulary
# ("partial" / "unconfirmed"). Keep all values readable so shared history
# survives schema upgrades.
V3RelationshipMapStatus = Literal[
    "confirmed", "inferred", "partial", "unconfirmed", "unknown"
]
V3Strength = Literal["strong", "medium", "weak"]


class V3ProjectFact(BaseModel):
    value: str
    status: V3EvidenceStatus
    evidence: list[str] = Field(default_factory=list)


class V3StructureNode(BaseModel):
    node_id: str
    entity_id: str | None = None
    role: str
    roles: list[str] = Field(default_factory=list, max_length=12)
    company: str | None = None
    organization_type: str = "UNKNOWN"
    organization_scope: str = "unknown"
    layer_type: Literal["corporate", "project"] = "project"
    role_statuses: dict[str, str] = Field(default_factory=dict)
    temporal_scope: Literal["current", "historical", "candidate", "unknown"] = "unknown"
    layer: int
    position: str
    required: bool
    status: V3EvidenceStatus = "unknown"
    evidence: list[str] = Field(default_factory=list)


class V3StructureRelation(BaseModel):
    from_node: str
    to_node: str
    relation_type: str
    line_type: str
    direction: str
    label: str
    relationship_basis: str = ""
    description: str = ""
    temporal_scope: Literal["current", "historical", "candidate", "unknown"] = "unknown"
    status: V3EvidenceStatus = "unknown"
    evidence: list[str] = Field(default_factory=list)


class V3RelationshipMap(BaseModel):
    structure_id: str | None = None
    structure_name: str = "Not confirmed"
    status: V3RelationshipMapStatus = "unconfirmed"
    evidence: list[str] = Field(default_factory=list)
    nodes: list[V3StructureNode] = Field(default_factory=list)
    relations: list[V3StructureRelation] = Field(default_factory=list)
    research_gaps: list[str] = Field(default_factory=list, max_length=12)


class V3StakeholderTarget(BaseModel):
    stakeholder_type: str
    role: str
    company: str | None = None
    target_function: list[str] = Field(default_factory=list, max_length=2)
    person: str | None = None
    priority: Literal[1, 2, 3]
    evidence_strength: V3Strength
    reason: str
    evidence: list[str] = Field(default_factory=list)


class V3Question(BaseModel):
    question: str
    information_goal: str
    reason: str
    converts: Literal["unknown", "inference"]


class V3ProductRecommendation(BaseModel):
    rank: int = Field(ge=1, le=3)
    product: str
    evidence_strength: V3Strength
    why: str
    customer_need: str
    suggested_scenario: str
    excel_match_count: int
    matched_rules: list[str] = Field(default_factory=list)
    context_evidence: list[str] = Field(default_factory=list)


class V3TalkingPoint(BaseModel):
    product: str
    scenario: str
    customer_need: str
    project_stage: str


class BDV3AnalysisResult(BaseModel):
    version: Literal["v3"] = "v3"
    opportunity_title: str
    executive_summary: str
    status: Literal["now", "monitor", "closed"]
    status_reason: str
    building_type: V3ProjectFact
    project_stage: V3ProjectFact
    customer_needs: list[V3ProjectFact] = Field(default_factory=list)
    relationship_map: V3RelationshipMap
    priority_1: list[V3StakeholderTarget] = Field(default_factory=list)
    priority_2: list[V3StakeholderTarget] = Field(default_factory=list)
    priority_3: list[V3StakeholderTarget] = Field(default_factory=list)
    stakeholder_unknowns: list[str] = Field(default_factory=list)
    questions_to_ask: list[V3Question] = Field(default_factory=list)
    talking_points: list[V3TalkingPoint] = Field(default_factory=list, max_length=3)
    customer_need_top_signals: list[V3ProjectFact] = Field(default_factory=list, max_length=3)
    product_top3: list[V3ProductRecommendation] = Field(default_factory=list, max_length=3)
    decision_trace_excel: str = ""
    decision_trace_ai: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    source_summary: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    v2_snapshot: BDV2AnalysisResult
