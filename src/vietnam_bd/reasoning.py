from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

from src.common.llm_json import strip_code_fences

from .models import (
    AccessibilityFactor,
    BDV2AnalysisResult,
    BDV2Stakeholder,
    BusinessDevelopmentDecision,
    CanWeEnter,
    EvidenceItem,
    ExcludedWorkstream,
    InformationToConfirm,
    MeetingTalkingPoints,
    MustKnowItem,
    NextBestAction,
    IntelligenceItem,
    PartnerPattern,
    ProjectActor,
    ProjectIntelligence,
    ProjectRelationship,
    ProposalHypothesis,
    RelationshipDecisionMap,
    StakeholderMeetingPlan,
    TimelineItem,
    WorkstreamRecommendation,
)
from .dx_portfolio import DXPortfolioMatch, match_dx_portfolio
from .research_models import ResearchBundle, ResearchEvidence
from .rule_engine import RuleEngineResult
from .sfdc_sample import match_sample_opportunities
from .v2_prompts import commercial_prompt, engagement_prompt, workstream_prompt
from .vertical_guardrails import DEFAULT_WORKSTREAM_GUARDRAILS, WorkstreamGuardrail, allowed_workstream_candidates


class WorkstreamReasoning(BaseModel):
    workstreams: list[WorkstreamRecommendation] = Field(default_factory=list, max_length=3)
    excluded_workstreams: list[ExcludedWorkstream] = Field(default_factory=list, max_length=5)


class CommercialReasoning(BaseModel):
    can_we_enter: CanWeEnter
    information_to_confirm: list[InformationToConfirm] = Field(default_factory=list, max_length=6)
    stakeholders: list[BDV2Stakeholder] = Field(default_factory=list, max_length=6)


class EngagementReasoning(BaseModel):
    talking_points: MeetingTalkingPoints
    next_best_actions: list[NextBestAction] = Field(default_factory=list, max_length=3)


ResultT = TypeVar("ResultT", bound=BaseModel)
StructuredRunner = Callable[[str, type[ResultT]], ResultT]


def _response_text(response: Any) -> str:
    return response.output_text if getattr(response, "output_text", None) else str(response)


def _default_runner(prompt: str, result_model: type[ResultT]) -> ResultT:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    schema = json.dumps(result_model.model_json_schema(), ensure_ascii=False)
    response = client.responses.create(
        model=model,
        instructions="Perform one bounded BD reasoning step. Return valid JSON only.",
        input=f"{prompt}\n\n[REQUIRED JSON SCHEMA]\n{schema}",
    )
    raw = strip_code_fences(_response_text(response))
    try:
        return result_model.model_validate_json(raw)
    except ValidationError as first_error:
        repair = client.responses.create(
            model=model,
            instructions="Repair content to the schema. Return JSON only and add no facts.",
            input=f"SCHEMA:\n{schema}\n\nCONTENT:\n{raw}\n\nERROR:\n{first_error}",
        )
        return result_model.model_validate_json(strip_code_fences(_response_text(repair)))


def _research_groups(bundle: ResearchBundle) -> Iterable[ResearchEvidence]:
    quick = bundle.quick
    for group in (
        quick.stage_signals,
        quick.customer_need_signals,
        quick.building_type_signals,
        quick.business_structure_signals,
        quick.recent_project_signals,
    ):
        yield from group
    if bundle.deep:
        deep = bundle.deep
        for group in (
            deep.project_facts,
            deep.historical_projects,
            deep.project_ecosystem,
            deep.ecosystem_candidates,
            deep.peer_benchmarks,
            deep.buying_signals,
            deep.competitor_signals,
        ):
            yield from group


def _evidence_items(bundle: ResearchBundle) -> list[EvidenceItem]:
    result: list[EvidenceItem] = []
    seen: set[tuple[str, str]] = set()
    for item in _research_groups(bundle):
        source_identity = "|".join(
            source.url or source.independence_key or source.name for source in item.sources
        ) or item.source_url or item.source_name
        key = (item.claim, source_identity)
        if key in seen:
            continue
        seen.add(key)
        labels = list(dict.fromkeys(
            label
            for label in (
                item.source_name,
                item.source_url,
                *(source.name for source in item.sources),
                *(source.url for source in item.sources),
            )
            if label
        ))
        result.append(
            EvidenceItem(
                claim=item.claim,
                credibility=item.credibility,
                rationale=item.rationale or "Research evidence",
                source_labels=labels,
                source_urls=list(dict.fromkeys(
                    value for value in (item.source_url, *(source.url for source in item.sources)) if value
                )),
                source_dates=list(dict.fromkeys(source.published_date for source in item.sources if source.published_date)),
                source_conflicts=[source.name for source in item.sources if source.stance == "contradicts"],
            )
        )
    return result[:15]


def _payload(bundle: ResearchBundle, rule_result: RuleEngineResult, seed: str) -> dict[str, Any]:
    return {
        "seed": seed,
        "quick_research": bundle.quick.model_dump(mode="json"),
        "detailed_research": bundle.deep.model_dump(mode="json") if bundle.deep else None,
        "final_context": rule_result.context.model_dump(mode="json"),
        "stage_gate": rule_result.stage_gate.model_dump(mode="json"),
        "active_pursuit": bundle.active_pursuit,
        "historical_intelligence": bundle.historical_intelligence,
        "research_rounds": [item.model_dump(mode="json") for item in bundle.research_rounds],
    }


def _labels(item: ResearchEvidence) -> tuple[list[str], list[str], list[str]]:
    labels = list(dict.fromkeys(
        label for label in (
            item.source_name, *(source.name for source in item.sources)
        ) if label
    ))
    urls = list(dict.fromkeys(
        value for value in (
            item.source_url, *(source.url for source in item.sources)
        ) if value
    ))
    dates = list(dict.fromkeys(source.published_date for source in item.sources if source.published_date))
    return labels, urls, dates


def _intelligence_item(item: ResearchEvidence, temporal_scope: str) -> IntelligenceItem:
    labels, urls, dates = _labels(item)
    return IntelligenceItem(
        claim=item.claim,
        credibility=item.credibility,
        rationale=item.rationale,
        evidence_labels=labels,
        source_urls=urls,
        source_dates=dates,
        temporal_scope=temporal_scope,
    )


def build_project_intelligence(bundle: ResearchBundle) -> ProjectIntelligence:
    deep = bundle.deep
    if not deep:
        return ProjectIntelligence(
            owner_summary=bundle.quick.company,
            unresolved_gaps=[gap.topic for rnd in bundle.research_rounds for gap in rnd.research_gaps],
        )
    conflicts = []
    for item in _research_groups(bundle):
        if any(source.stance == "contradicts" for source in item.sources):
            conflicts.append(item.claim)
    entity_names = {
        entity.name: entity.entity_type
        for rnd in bundle.research_rounds
        for entity in rnd.discovered_entities
    }
    historical_text = " ".join(item.claim for item in deep.historical_projects).casefold()
    patterns = []
    for name, role in entity_names.items():
        count = historical_text.count(name.casefold())
        if count:
            patterns.append(PartnerPattern(
                partner=name,
                role=role,
                historical_project_count=count,
                pattern_summary=f"Historical research mentions {name} in {count} project claim(s).",
                current_participation="unconfirmed",
                credibility="hypothesis",
                evidence_labels=[],
            ))
    timeline = []
    for item in [*bundle.quick.stage_signals, *bundle.quick.recent_project_signals]:
        labels, _, dates = _labels(item)
        if dates:
            timeline.append(TimelineItem(
                milestone=item.claim,
                date_or_period=dates[0],
                credibility=item.credibility,
                evidence_labels=labels,
            ))
    open_keywords = ("unawarded", "open", "미발주", "미선정", "change order", "add-on", "추가 범위")
    open_items = [
        item for item in [*deep.project_facts, *deep.buying_signals]
        if any(keyword in item.claim.casefold() for keyword in open_keywords)
    ]
    gaps = list(dict.fromkeys(
        [*deep.unresolved_topics]
        + [gap.topic for rnd in bundle.research_rounds for gap in rnd.research_gaps]
    ))
    watch = list(dict.fromkeys(
        [gap.topic for rnd in bundle.research_rounds for gap in rnd.research_gaps if gap.critical]
        + [query.purpose for rnd in bundle.research_rounds for query in rnd.follow_up_queries]
    ))[:10]
    return ProjectIntelligence(
        owner_summary=deep.company or bundle.quick.company,
        current_project_facts=[_intelligence_item(item, "current") for item in deep.project_facts],
        historical_projects=[_intelligence_item(item, "historical") for item in deep.historical_projects],
        project_ecosystem=[_intelligence_item(item, "current") for item in deep.project_ecosystem],
        ecosystem_candidates=[_intelligence_item(item, "candidate") for item in deep.ecosystem_candidates],
        repeated_partner_patterns=patterns[:10],
        project_timeline=timeline[:12],
        open_scopes=[_intelligence_item(item, "current") for item in open_items],
        watch_signals=watch,
        next_trigger=watch[0] if watch else "",
        unresolved_gaps=gaps[:15],
        source_conflicts=list(dict.fromkeys(conflicts))[:10],
    )


def build_relationship_map(bundle: ResearchBundle, intelligence: ProjectIntelligence) -> RelationshipDecisionMap:
    owner_name = (
        (bundle.seed_understanding.owner_candidate if bundle.seed_understanding else "")
        or bundle.quick.company or intelligence.owner_summary or "Owner / End Client"
    )
    owner_evidence = [
        item for item in [*bundle.quick.recent_project_signals, *(bundle.deep.project_facts if bundle.deep else [])]
        if owner_name.casefold() in f"{item.claim} {item.rationale}".casefold()
    ]
    owner_labels = list(dict.fromkeys(label for item in owner_evidence for label in _labels(item)[0]))
    owner_urls = list(dict.fromkeys(url for item in owner_evidence for url in _labels(item)[1]))
    owner_dates = list(dict.fromkeys(date for item in owner_evidence for date in _labels(item)[2]))
    actors = [ProjectActor(
        actor_id="owner",
        role="Owner / End Client",
        organization=owner_name,
        temporal_scope="current",
        actor_status="confirmed" if owner_urls else "likely" if owner_labels else "unknown",
        participation_status="Project owner / check direct evidence",
        credibility="confirmed" if owner_urls else "likely" if owner_labels else "unknown",
        rationale="Seed and account research owner context.",
        evidence_labels=owner_labels,
        source_urls=owner_urls,
        source_dates=owner_dates,
        confirmation_needed="Confirm legal project owner" if not owner_urls else "",
    )]
    relationships = []
    used_ids = {"owner"}
    role_relation = {
        "architect": "설계 계약", "consultant": "자문 / 설계 지원", "epc": "EPC 발주",
        "gc": "공사 발주", "vendor": "Package / Solution 공급", "authority": "인허가 관계",
        "company": "사업 참여", "project": "사업 주체", "owner": "투자 / 의사결정",
    }
    role_labels = {
        "hq": "HQ", "owner": "Owner / End Client", "local_subsidiary": "Local Subsidiary",
        "architect": "Architect", "consultant": "PM / CM", "pm_cm": "PM / CM",
        "epc": "EPC", "gc": "GC", "mep": "MEP", "vendor": "Key Vendor",
        "authority": "Authority",
    }
    candidate_names = " ".join(item.claim for item in intelligence.ecosystem_candidates).casefold()
    historical_names = " ".join(item.claim for item in intelligence.historical_projects).casefold()
    for rnd in bundle.research_rounds:
        for entity in rnd.discovered_entities:
            if not entity.name.strip() or entity.name.casefold() == owner_name.casefold():
                continue
            base_id = "actor_" + "".join(ch if ch.isalnum() else "_" for ch in entity.name.casefold()).strip("_")
            actor_id = base_id or f"actor_{len(actors)}"
            if actor_id in used_ids:
                continue
            used_ids.add(actor_id)
            name_key = entity.name.casefold()
            temporal = "candidate" if name_key in candidate_names else "historical" if name_key in historical_names else "current"
            credibility = entity.credibility
            if temporal in {"candidate", "historical"}:
                credibility = "hypothesis"
                actor_status = "candidate"
            elif not entity.evidence_labels and not entity.source_urls:
                credibility = "unknown"
                actor_status = "unknown"
            elif credibility == "confirmed" and not entity.source_urls:
                credibility = "likely"
                actor_status = "likely"
            else:
                actor_status = "confirmed" if credibility == "confirmed" else "likely" if credibility == "likely" else "unknown"
            actors.append(ProjectActor(
                actor_id=actor_id,
                role=role_labels.get(entity.entity_type, entity.entity_type.replace("_", " ").title()),
                organization=entity.name,
                temporal_scope=temporal,
                actor_status=actor_status,
                participation_status=(
                    "Current project participation unconfirmed" if temporal != "current"
                    else "Current project participant / verify relationship"
                ),
                credibility=credibility,
                rationale="Discovered during iterative research.",
                evidence_labels=entity.evidence_labels,
                source_urls=entity.source_urls,
                source_dates=entity.source_dates,
                confirmation_needed=(f"Confirm whether {entity.name} is the current {role_labels.get(entity.entity_type, entity.entity_type)}" if actor_status != "confirmed" else ""),
            ))
            relationships.append(ProjectRelationship(
                from_actor_id="owner",
                to_actor_id=actor_id,
                relationship_type=role_relation.get(entity.entity_type, "사업 관계"),
                description="Relationship derived from research entity; detailed contract status requires evidence review.",
                temporal_scope=temporal,
                credibility=credibility,
                evidence_labels=entity.evidence_labels,
                source_urls=entity.source_urls,
                source_dates=entity.source_dates,
            ))
    present_roles = {
        actor.role for actor in actors
        if actor.temporal_scope == "current" and actor.actor_status in {"confirmed", "likely"}
    }
    for role in ("HQ", "Local Subsidiary", "Architect", "PM / CM", "EPC", "GC", "MEP", "Key Vendor", "Authority"):
        if role in present_roles:
            continue
        actor_id = "unknown_" + role.casefold().replace(" / ", "_").replace(" ", "_")
        actors.append(ProjectActor(
            actor_id=actor_id,
            role=role,
            organization="UNKNOWN",
            temporal_scope="unknown",
            actor_status="unknown",
            participation_status="Research did not identify the current organization.",
            credibility="unknown",
            rationale="No current-project evidence identified this role.",
            confirmation_needed=f"Confirm current {role}",
        ))
    return RelationshipDecisionMap(
        actors=actors[:20],
        relationships=relationships[:30],
        decision_structure_summary=f"Owner-centered map with {max(0, len(actors)-1)} discovered actor(s).",
        unknown_critical_actors=[gap for gap in intelligence.unresolved_gaps if any(x in gap.casefold() for x in ("epc", "gc", "architect", "consultant"))][:10],
    )


def _has_supported_open_scope(intelligence: ProjectIntelligence) -> bool:
    return any(
        item.credibility in {"confirmed", "likely"} and bool(item.evidence_labels or item.source_urls)
        for item in intelligence.open_scopes
    )


def _has_supported_closure(intelligence: ProjectIntelligence) -> bool:
    closure_terms = ("awarded", "completed", "operational", "operation permit", "수주", "발주 완료", "준공", "운영")
    return any(
        item.credibility in {"confirmed", "likely"}
        and bool(item.evidence_labels or item.source_urls)
        and any(term in f"{item.claim} {item.rationale}".casefold() for term in closure_terms)
        for item in [*intelligence.current_project_facts, *intelligence.project_ecosystem]
    )


def decide_business_development(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    intelligence: ProjectIntelligence,
    dx_matches: list[DXPortfolioMatch],
) -> BusinessDevelopmentDecision:
    status = rule_result.stage_gate.status
    stage = rule_result.context.business_stage
    stage_supported = stage.credibility in {"confirmed", "likely"} and bool(stage.source_labels)
    intervention_possible = status in {"targeting", "golden_time", "local_action"}
    scope_open = _has_supported_open_scope(intelligence)
    if status in {"targeting", "golden_time"} and not scope_open:
        scope_open = bool(
            intelligence.current_project_facts
            and rule_result.context.business_structure
            and any(item.source_labels for item in rule_result.context.business_structure)
        )
    dx_addressable = bool(dx_matches)
    evidence_sufficient = bool(
        stage_supported
        and any(match.evidence_labels for match in dx_matches)
        and (scope_open or status == "closed")
    )
    closed_supported = status == "closed" and stage_supported and _has_supported_closure(intelligence)
    if closed_supported:
        decision, headline, direction = "closed", "CLOSED · Active Pursuit Stop", "현재건 공략을 중단하고 참여·발주 구조를 다음 기회에 활용"
    elif intervention_possible and scope_open and dx_addressable and evidence_sufficient:
        decision, headline, direction = "now", "NOW · ACTIONABLE WINDOW", "확인된 Scope와 구매경로를 기준으로 즉시 개입"
    else:
        decision, headline, direction = "monitor", "MONITOR · Wait for Trigger", "Actor 선정·Tender·인허가 등 진입 Trigger 추적"
    context = rule_result.context
    basis = [context.building_type.claim, context.business_stage.claim]
    basis.extend(item.claim for item in context.business_structure[:3])
    basis.extend(item.claim for item in context.customer_needs[:3])
    labels = list(dict.fromkeys(
        context.building_type.source_labels + context.business_stage.source_labels
        + [label for item in context.business_structure + context.customer_needs for label in item.source_labels]
    ))
    return BusinessDevelopmentDecision(
        decision=decision,
        headline=headline,
        rationale=(
            f"Lifecycle={status}; intervention={intervention_possible}; scope_open={scope_open}; "
            f"dx_addressable={dx_addressable}; evidence_sufficient={evidence_sufficient}; "
            f"closed_evidence={closed_supported}. {rule_result.stage_gate.rationale}"
        ),
        context_basis=basis[:8],
        evidence_labels=labels[:8],
        action_direction=direction,
        trigger_to_reassess=intelligence.next_trigger,
        priority_window=decision == "now",
        intervention_possible=intervention_possible,
        scope_open=scope_open,
        dx_addressable=dx_addressable,
        evidence_sufficient=evidence_sufficient,
    )


def build_must_know_top3(
    bundle: ResearchBundle,
    decision: BusinessDevelopmentDecision,
    relationship_map: RelationshipDecisionMap,
    dx_matches: list[DXPortfolioMatch],
) -> list[MustKnowItem]:
    if decision.decision == "closed":
        return []
    candidates: list[MustKnowItem] = []

    def limited_labels(labels: list[str]) -> list[str]:
        return list(dict.fromkeys(label for label in labels if label))[:8]

    role_priority = {"EPC": 0, "Architect": 1, "PM / CM": 2, "GC": 3, "MEP": 4, "Owner / End Client": 5, "Local Subsidiary": 6, "Key Vendor": 7}
    uncertain_actors = sorted(
        (actor for actor in relationship_map.actors if actor.actor_status != "confirmed" and actor.role not in {"HQ", "Authority"}),
        key=lambda actor: (role_priority.get(actor.role, 99), actor.actor_id),
    )
    actor_limit = 2 if dx_matches else 3
    for actor in uncertain_actors[:actor_limit]:
        question = actor.confirmation_needed or f"현재 프로젝트의 {actor.role} 조직은 어디인가?"
        candidates.append(MustKnowItem(
            rank=1,
            question=question,
            why_it_matters="이 Actor의 확정 여부가 접촉 대상과 구매경로를 변경합니다.",
            decision_impact=["actor", "buying_route", "decision"],
            actor_ids=[actor.actor_id],
            evidence_labels=limited_labels(actor.evidence_labels),
            suggested_way_to_check=f"Owner PM 또는 조달 조직에 {actor.role} 선정 상태와 책임 범위를 확인합니다.",
        ))
    for match in dx_matches:
        for question in match.must_know_candidates[:2]:
            related = [
                actor.actor_id for actor in relationship_map.actors
                if actor.role.casefold() in " ".join(match.target_roles).casefold()
            ][:3]
            candidates.append(MustKnowItem(
                rank=1,
                question=question,
                why_it_matters="답에 따라 DX 판매 Scope, Workstream 또는 제안 구체화 여부가 달라집니다.",
                decision_impact=["scope", "workstream", "decision"],
                actor_ids=related,
                evidence_labels=limited_labels(match.evidence_labels),
                suggested_way_to_check="관련 Owner/EPC 설계·구매 담당자에게 Scope와 발주 상태를 확인합니다.",
            ))
    for gap in [gap for rnd in bundle.research_rounds for gap in rnd.research_gaps if gap.critical]:
        candidates.append(MustKnowItem(
            rank=1,
            question=gap.topic,
            why_it_matters=gap.sales_impact or "답에 따라 최종 BD 행동이 달라집니다.",
            decision_impact=["decision"],
            suggested_way_to_check="현재 프로젝트의 직접 관계자 또는 공식 조달 자료로 확인합니다.",
        ))
    unique: list[MustKnowItem] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.question.casefold().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item.model_copy(update={"rank": len(unique) + 1}))
        if len(unique) == 3:
            break
    return unique


def build_proposal_hypotheses(
    decision: BusinessDevelopmentDecision,
    dx_matches: list[DXPortfolioMatch],
    must_knows: list[MustKnowItem],
) -> list[ProposalHypothesis]:
    if decision.decision == "closed":
        return []
    proposals = []
    conditions = [item.question for item in must_knows[:2]]
    for match in dx_matches:
        if not match.evidence_labels:
            continue
        workstream = match.workstreams[0] if match.workstreams else match.capability
        proposals.append(ProposalHypothesis(
            rank=len(proposals) + 1,
            workstream=workstream,
            capability=match.capability,
            hypothesis=(
                f"확인된 고객 Need와 Scope를 기반으로 {match.capability} 관점의 공략안을 구체화합니다."
                if decision.decision == "now"
                else f"현재 Research 기준 {match.capability} 적용 가능성이 있으나 Scope·구매경로·Actor 확인 후 구체화합니다."
            ),
            mode="actionable" if decision.decision == "now" else "conditional",
            conditions_to_confirm=[] if decision.decision == "now" else conditions,
            evidence_labels=list(dict.fromkeys(label for label in match.evidence_labels if label))[:8],
            portfolio_source_url=match.source_url,
        ))
        if len(proposals) == 3:
            break
    return proposals


def align_stakeholders_to_relationship_map(
    stakeholders: list[BDV2Stakeholder],
    relationship_map: RelationshipDecisionMap,
    must_knows: list[MustKnowItem],
) -> list[BDV2Stakeholder]:
    required_ids = list(dict.fromkeys(actor_id for item in must_knows for actor_id in item.actor_ids))
    actor_by_id = {actor.actor_id: actor for actor in relationship_map.actors}
    aligned: list[BDV2Stakeholder] = []
    for actor_id in required_ids:
        actor = actor_by_id.get(actor_id)
        if not actor:
            continue
        existing = next((item for item in stakeholders if item.role.casefold() == actor.role.casefold()), None)
        aligned.append(BDV2Stakeholder(
            actor_id=actor.actor_id,
            role=actor.role,
            organization_or_candidate=None if actor.organization == "UNKNOWN" else actor.organization,
            priority=existing.priority if existing else "primary" if not aligned else "secondary",
            credibility=actor.credibility,
            why_meet=existing.why_meet if existing else "Must Know 확인을 통해 Scope와 구매경로를 결정합니다.",
            information_to_get=existing.information_to_get if existing else [item.question for item in must_knows if actor_id in item.actor_ids][:5],
            evidence_labels=actor.evidence_labels,
            rationale=actor.rationale,
        ))
    return aligned[:6]


def _validated_workstreams(result: WorkstreamReasoning, candidates: list[str]) -> WorkstreamReasoning:
    allowed = set(candidates)
    selected: list[WorkstreamRecommendation] = []
    seen: set[str] = set()
    for item in result.workstreams:
        if item.workstream not in allowed or item.workstream in seen:
            continue
        if not item.why_relevant.strip() or not item.context_basis:
            continue
        grounded = [
            capability for capability in item.grounded_capabilities
            if capability.rationale.strip() and capability.context_basis and capability.evidence_labels
        ][:4]
        seen.add(item.workstream)
        selected.append(item.model_copy(update={
            "rank": len(selected) + 1,
            "possible_capabilities": [],
            "grounded_capabilities": grounded,
        }))
        if len(selected) == 3:
            break
    excluded = [item for item in result.excluded_workstreams if item.workstream in allowed and item.workstream not in seen][:5]
    return WorkstreamReasoning(workstreams=selected, excluded_workstreams=excluded)


def select_workstreams(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    *,
    seed: str = "",
    runner: StructuredRunner = _default_runner,
    catalog: tuple[WorkstreamGuardrail, ...] = DEFAULT_WORKSTREAM_GUARDRAILS,
    decision: BusinessDevelopmentDecision | None = None,
    intelligence: ProjectIntelligence | None = None,
) -> WorkstreamReasoning:
    candidates = allowed_workstream_candidates(rule_result.context, catalog)
    if decision and decision.decision in {"monitor", "closed"}:
        return WorkstreamReasoning(
            excluded_workstreams=[
                ExcludedWorkstream(workstream=name, reason="Closed project: active pursuit stopped.")
                for name in candidates[:5]
            ]
        )
    if not candidates:
        return WorkstreamReasoning()
    payload = _payload(bundle, rule_result, seed)
    if decision:
        payload["business_development_decision"] = decision.model_dump(mode="json")
    if intelligence:
        payload["project_intelligence"] = intelligence.model_dump(mode="json")
    result = runner(workstream_prompt(payload, candidates), WorkstreamReasoning)
    return _validated_workstreams(result, candidates)


def _validate_stakeholders(items: list[BDV2Stakeholder]) -> list[BDV2Stakeholder]:
    validated = []
    for item in items[:6]:
        if item.credibility == "confirmed" and not item.evidence_labels:
            item = item.model_copy(update={"credibility": "hypothesis"})
        validated.append(item)
    return validated


def assess_commercial_entry(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    workstreams: WorkstreamReasoning,
    *,
    seed: str = "",
    runner: StructuredRunner = _default_runner,
    decision: BusinessDevelopmentDecision | None = None,
    intelligence: ProjectIntelligence | None = None,
) -> CommercialReasoning:
    payload = _payload(bundle, rule_result, seed)
    payload["selected_workstreams"] = workstreams.model_dump(mode="json")
    if decision:
        payload["business_development_decision"] = decision.model_dump(mode="json")
    if intelligence:
        payload["project_intelligence"] = intelligence.model_dump(mode="json")
    closed = bool(decision and decision.decision == "closed")
    result = runner(commercial_prompt(payload, closed), CommercialReasoning)
    result.stakeholders = _validate_stakeholders(result.stakeholders)
    if closed:
        result.can_we_enter.timing = AccessibilityFactor(
            level="low",
            rationale="Closed project: current-project active pursuit has stopped.",
            evidence_labels=rule_result.context.business_stage.source_labels,
        )
        result.can_we_enter.overall_view = "Active pursuit stopped; retain limited historical intelligence for future opportunities."
        result.information_to_confirm = []
    return result


def build_engagement_intelligence(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    workstreams: WorkstreamReasoning,
    commercial: CommercialReasoning,
    *,
    seed: str = "",
    runner: StructuredRunner = _default_runner,
    decision: BusinessDevelopmentDecision | None = None,
    intelligence: ProjectIntelligence | None = None,
) -> EngagementReasoning:
    if decision and decision.decision in {"monitor", "closed"}:
        return EngagementReasoning(talking_points=MeetingTalkingPoints())
    payload = _payload(bundle, rule_result, seed)
    payload["selected_workstreams"] = workstreams.model_dump(mode="json")
    payload["commercial_entry"] = commercial.model_dump(mode="json")
    if decision:
        payload["business_development_decision"] = decision.model_dump(mode="json")
    if intelligence:
        payload["project_intelligence"] = intelligence.model_dump(mode="json")
    result = runner(engagement_prompt(payload), EngagementReasoning)
    if not result.talking_points.open or not result.talking_points.power or not result.talking_points.win:
        raise ValueError("Active-pursuit meeting intelligence requires OPEN, POWER, and WIN talking points.")
    result.next_best_actions = result.next_best_actions[:3]
    return result


def enforce_stage_gate_output(result: BDV2AnalysisResult) -> BDV2AnalysisResult:
    """Apply deterministic output policy after all probabilistic reasoning.

    Prompts guide the model, but the stage gate is a business rule and must also
    be enforced on the structured result returned to API/UI callers.
    """

    gate = result.stage_gate
    decision = result.bd_decision.decision

    if decision == "closed":
        stopped_entry = CanWeEnter(
            timing=AccessibilityFactor(
                level="low",
                rationale="현재 프로젝트는 종료 단계이므로 능동 공략 시점이 지났습니다.",
                evidence_labels=result.context.business_stage.source_labels,
            ),
            access=AccessibilityFactor(
                level="unknown",
                rationale="현재 건의 신규 진입 경로는 평가하지 않습니다.",
                evidence_labels=[],
            ),
            openness=AccessibilityFactor(
                level="low",
                rationale="현재 프로젝트의 미확정 범위를 전제로 영업 기회를 만들지 않습니다.",
                evidence_labels=result.context.business_stage.source_labels,
            ),
            fit=AccessibilityFactor(
                level="unknown",
                rationale="현재 건의 적합성 평가는 중단하고 향후 O&M·리트로핏·증설을 별도 기회로 다룹니다.",
                evidence_labels=[],
            ),
            overall_view="현재 프로젝트 Active Pursuit 중단. 제한된 과거 정보만 다음 기회에 활용합니다.",
        )
        return result.model_copy(update={
            "workstreams": [],
            "information_to_confirm": [],
            "stakeholders": [],
            "talking_points": MeetingTalkingPoints(),
            "next_best_actions": [],
            "stakeholder_meeting_plans": [],
            "can_we_enter": stopped_entry,
        })

    if decision == "monitor":
        # Monitoring may retain decision-changing unknowns and role-level check
        # targets, but must not leak active-pursuit recommendations.
        return result.model_copy(update={
            "workstreams": [],
            "talking_points": MeetingTalkingPoints(),
            "next_best_actions": [],
            "stakeholder_meeting_plans": [],
        })

    return result


def reason_opportunity_v2(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    *,
    seed: str = "",
    runner: StructuredRunner = _default_runner,
    catalog: tuple[WorkstreamGuardrail, ...] = DEFAULT_WORKSTREAM_GUARDRAILS,
) -> BDV2AnalysisResult:
    intelligence = build_project_intelligence(bundle)
    relationship_map = build_relationship_map(bundle, intelligence)
    dx_matches = match_dx_portfolio(rule_result.context)
    decision = decide_business_development(bundle, rule_result, intelligence, dx_matches)
    must_knows = build_must_know_top3(bundle, decision, relationship_map, dx_matches)
    proposals = build_proposal_hypotheses(decision, dx_matches, must_knows)
    workstreams = select_workstreams(
        bundle, rule_result, seed=seed, runner=runner, catalog=catalog,
        decision=decision, intelligence=intelligence,
    )
    commercial = assess_commercial_entry(
        bundle, rule_result, workstreams, seed=seed, runner=runner,
        decision=decision, intelligence=intelligence,
    )
    commercial.stakeholders = align_stakeholders_to_relationship_map(
        commercial.stakeholders, relationship_map, must_knows,
    )
    engagement = build_engagement_intelligence(
        bundle, rule_result, workstreams, commercial, seed=seed, runner=runner,
        decision=decision, intelligence=intelligence,
    )
    title = bundle.quick.project_name or bundle.quick.company or seed.strip()[:100] or "BD Opportunity"
    summary = bundle.quick.current_project_summary or rule_result.stage_gate.rationale
    sources = list(dict.fromkeys(bundle.quick.source_summary + (bundle.deep.source_summary if bundle.deep else [])))
    limitations = list(bundle.deep.unresolved_topics if bundle.deep else [])
    if rule_result.stage_gate.active_pursuit == "stop":
        limitations.insert(0, "Closed project: active pursuit outputs are intentionally suppressed.")
    meeting_plans = []
    if commercial.stakeholders and decision.decision == "now":
        for stakeholder in commercial.stakeholders:
            meeting_plans.append(StakeholderMeetingPlan(
                actor_id=stakeholder.actor_id,
                stakeholder_role=stakeholder.role,
                why_meet=stakeholder.why_meet,
                information_to_obtain=stakeholder.information_to_get,
                open=engagement.talking_points.open,
                power=engagement.talking_points.power,
                win=engagement.talking_points.win,
            ))
    result = BDV2AnalysisResult(
        opportunity_title=title,
        executive_summary=summary,
        evidence=_evidence_items(bundle),
        context=rule_result.context,
        stage_gate=rule_result.stage_gate,
        workstreams=workstreams.workstreams,
        excluded_workstreams=workstreams.excluded_workstreams,
        can_we_enter=commercial.can_we_enter,
        information_to_confirm=commercial.information_to_confirm,
        stakeholders=commercial.stakeholders,
        talking_points=engagement.talking_points,
        next_best_actions=engagement.next_best_actions,
        similar_cases=[],
        source_summary=sources,
        limitations=limitations,
        bd_decision=decision,
        project_intelligence=intelligence,
        relationship_map=relationship_map,
        stakeholder_meeting_plans=meeting_plans,
        must_know_top3=must_knows,
        proposal_hypotheses=proposals,
        sample_sfdc_matches=match_sample_opportunities(
            bundle.quick.company,
            rule_result.context,
            [item.workstream for item in proposals],
        ),
    )
    return enforce_stage_gate_output(result)
