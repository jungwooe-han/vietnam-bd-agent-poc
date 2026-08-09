from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

Credibility = Literal["confirmed", "likely", "hypothesis", "unknown"]


class EvidenceItem(BaseModel):
    claim: str
    credibility: Credibility
    rationale: str
    source_labels: list[str] = Field(default_factory=list)


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
