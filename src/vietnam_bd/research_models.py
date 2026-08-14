from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Credibility = Literal["confirmed", "likely", "hypothesis", "unknown"]
LocationPrecision = Literal["exact_site", "industrial_park", "district", "city", "province", "region", "country", "unknown"]
LocationStatus = Literal["confirmed", "partial", "unknown"]


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


class ResearchProjectLocation(BaseModel):
    site_name: str = ""
    address: str = ""
    industrial_park: str = ""
    district: str = ""
    city: str = ""
    province: str = ""
    region: str = ""
    country: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    precision: LocationPrecision = "unknown"
    status: LocationStatus = "unknown"
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    evidence: list[ResearchEvidence] = Field(default_factory=list, max_length=8)
    coordinate_evidence: list[ResearchEvidence] = Field(default_factory=list, max_length=4)
    source_labels: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[str] = Field(default_factory=list, max_length=8)


class QuickResearchResult(BaseModel):
    company: str = ""
    project_name: str = ""
    current_project_summary: str = ""
    stage_signals: list[ResearchEvidence] = Field(default_factory=list)
    customer_need_signals: list[ResearchEvidence] = Field(default_factory=list)
    building_type_signals: list[ResearchEvidence] = Field(default_factory=list)
    business_structure_signals: list[ResearchEvidence] = Field(default_factory=list)
    recent_project_signals: list[ResearchEvidence] = Field(default_factory=list)
    project_location: ResearchProjectLocation = Field(default_factory=ResearchProjectLocation)
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
    # Deprecated compatibility input. New research should populate canonical
    # organization_type and project_roles instead.
    entity_type: Literal[
        "company", "project", "owner", "end_client", "investor", "sponsor",
        "developer", "host", "co_development_partner", "strategic_partner",
        "technology_partner", "solution_partner", "hq", "local_subsidiary",
        "architect", "consultant", "pm_cm", "epc", "gc", "mep", "operator",
        "vendor", "supplier", "authority", "industrial_park", "location", "other",
    ] = "other"
    aliases: list[str] = Field(default_factory=list, max_length=10)
    organization_type: Literal[
        "PUBLIC_INSTITUTION", "PRIVATE_COMPANY", "STATE_OWNED_ENTERPRISE",
        "FINANCIAL_INSTITUTION", "INDUSTRIAL_PARK_DEVELOPER", "ENGINEERING_COMPANY",
        "CONSTRUCTION_COMPANY", "TECHNOLOGY_COMPANY", "RESEARCH_INSTITUTION",
        "OTHER", "UNKNOWN",
    ] = "UNKNOWN"
    organization_scope: Literal[
        "global_hq", "regional_hq", "local_entity", "project_company", "unknown"
    ] = "unknown"
    country: str = ""
    website: str = ""
    project_roles: list[Literal[
        "PROJECT_OWNER", "END_CLIENT", "INVESTOR", "SPONSOR", "DEVELOPER", "HOST",
        "CO_DEVELOPMENT_PARTNER", "STRATEGIC_PARTNER", "ARCHITECT",
        "ENGINEERING_CONSULTANT", "PM_CM", "EPC", "GENERAL_CONTRACTOR",
        "MEP_CONTRACTOR", "TECHNOLOGY_PROVIDER", "SOLUTION_PROVIDER",
        "EQUIPMENT_SUPPLIER", "VENDOR", "OPERATOR", "FACILITY_MANAGER",
        "MAINTENANCE_PROVIDER", "GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY",
        "INDUSTRIAL_PARK", "LANDLORD", "OTHER",
    ]] = Field(default_factory=list, max_length=12)
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list, max_length=8)
    source_dates: list[str] = Field(default_factory=list, max_length=8)


class DiscoveredRelationship(BaseModel):
    from_entity: str
    to_entity: str
    relationship_type: str
    canonical_relationship_type: Literal[
        "OWNS", "INVESTS_IN", "SPONSORS", "AWARDS_CONTRACT_TO", "EPC_CONTRACT",
        "DESIGN_CONTRACT", "SUPPLY_CONTRACT", "OM_CONTRACT", "CO_DEVELOPMENT",
        "STRATEGIC_PARTNERSHIP", "MOU", "JOINT_VENTURE", "TECHNOLOGY_PROVISION",
        "EQUIPMENT_SUPPLY", "SOLUTION_PROVISION", "HOSTS", "PROVIDES_LAND",
        "LEASES_TO", "REGULATES", "APPROVES", "SUPERVISES", "SUBSIDIARY_OF",
        "LOCAL_ARM_OF", "PARENT_OF", "LOCATED_IN", "OTHER",
    ] | None = None
    relationship_basis: str = ""
    description: str = ""
    temporal_scope: Literal["current", "historical", "candidate", "unknown"] = "current"
    credibility: Credibility
    evidence_labels: list[str] = Field(default_factory=list, max_length=8)
    source_urls: list[str] = Field(default_factory=list, max_length=8)
    source_dates: list[str] = Field(default_factory=list, max_length=8)


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
    discovered_relationships: list[DiscoveredRelationship] = Field(default_factory=list, max_length=30)
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
