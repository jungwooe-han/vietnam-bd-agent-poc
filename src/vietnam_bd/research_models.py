from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Credibility = Literal["confirmed", "likely", "hypothesis", "unknown"]


class EvidenceSource(BaseModel):
    name: str
    url: str = ""
    published_date: str = ""
    source_type: Literal["official", "government", "company", "media", "industry", "other"] = "other"
    stance: Literal["supports", "contradicts", "mentions"] = "supports"
    independence_key: str = ""


class ResearchEvidence(BaseModel):
    claim: str
    credibility: Credibility
    source_name: str = ""
    source_url: str = ""
    rationale: str = ""
    sources: list[EvidenceSource] = Field(default_factory=list)


class SeedFact(BaseModel):
    claim: str
    source_label: str = "input"


class SeedUnderstanding(BaseModel):
    company: str = ""
    project: str = ""
    location: str = ""
    aliases: list[str] = Field(default_factory=list, max_length=10)
    owner_candidate: str = ""
    core_search_entities: list[str] = Field(default_factory=list, max_length=12)
    seed_facts: list[SeedFact] = Field(default_factory=list, max_length=15)


class QuickResearchResult(BaseModel):
    company: str = ""
    project_name: str = ""
    current_project_summary: str = ""
    stage_signals: list[ResearchEvidence] = Field(default_factory=list)
    customer_need_signals: list[ResearchEvidence] = Field(default_factory=list)
    building_type_signals: list[ResearchEvidence] = Field(default_factory=list)
    business_structure_signals: list[ResearchEvidence] = Field(default_factory=list)
    recent_project_signals: list[ResearchEvidence] = Field(default_factory=list)
    source_summary: list[str] = Field(default_factory=list)


class DeepResearchResult(BaseModel):
    company: str = ""
    project_facts: list[ResearchEvidence] = Field(default_factory=list)
    historical_projects: list[ResearchEvidence] = Field(default_factory=list)
    project_ecosystem: list[ResearchEvidence] = Field(default_factory=list)
    ecosystem_candidates: list[ResearchEvidence] = Field(default_factory=list)
    peer_benchmarks: list[ResearchEvidence] = Field(default_factory=list)
    buying_signals: list[ResearchEvidence] = Field(default_factory=list)
    competitor_signals: list[ResearchEvidence] = Field(default_factory=list)
    unresolved_topics: list[str] = Field(default_factory=list)
    source_summary: list[str] = Field(default_factory=list)


class DiscoveredEntity(BaseModel):
    name: str
    entity_type: Literal["company", "project", "owner", "architect", "consultant", "epc", "gc", "vendor", "location", "other"]
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list)


class ResearchGap(BaseModel):
    topic: str
    critical: bool = False
    sales_impact: str = ""


class FollowUpQuery(BaseModel):
    query: str
    purpose: str
    target_entities: list[str] = Field(default_factory=list)


class ClaimToVerify(BaseModel):
    claim: str
    reason: str


class ResearchRoundResult(BaseModel):
    round_number: int = Field(ge=1, le=3)
    focus: str
    findings: DeepResearchResult
    discovered_entities: list[DiscoveredEntity] = Field(default_factory=list, max_length=20)
    research_gaps: list[ResearchGap] = Field(default_factory=list, max_length=12)
    follow_up_queries: list[FollowUpQuery] = Field(default_factory=list, max_length=8)
    claims_to_verify: list[ClaimToVerify] = Field(default_factory=list, max_length=10)
    new_evidence: list[str] = Field(default_factory=list, max_length=20)
    changes_sales_action: bool = True
    termination_reason: str = ""


class ContextReadiness(BaseModel):
    ready: bool
    company_or_project_identified: bool
    stage_evidence_present: bool
    chronology_evidence_present: bool
    minimum_sources_present: bool
    major_conflict_present: bool
    missing_requirements: list[str] = Field(default_factory=list)
    source_count: int = 0


class ResearchBundle(BaseModel):
    quick: QuickResearchResult
    research_mode: Literal["deep", "limited", "stop"]
    stage_gate_status: str
    stage_gate_reason: str
    deep: DeepResearchResult | None = None
    active_pursuit: Literal["active", "limited", "stop"] = "active"
    historical_intelligence: Literal["deep", "limited", "none"] = "none"
    seed_understanding: SeedUnderstanding | None = None
    context_readiness: ContextReadiness | None = None
    research_rounds: list[ResearchRoundResult] = Field(default_factory=list, max_length=3)
