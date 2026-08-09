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
    NextBestAction,
    IntelligenceItem,
    PartnerPattern,
    ProjectActor,
    ProjectIntelligence,
    ProjectRelationship,
    RelationshipDecisionMap,
    StakeholderMeetingPlan,
    TimelineItem,
    WorkstreamRecommendation,
)
from .research_models import ResearchBundle, ResearchEvidence
from .rule_engine import RuleEngineResult
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
    actors = [ProjectActor(
        actor_id="owner",
        role="Owner / End Client",
        organization=owner_name,
        temporal_scope="current",
        participation_status="Project owner / check direct evidence",
        credibility="likely" if owner_name != "Owner / End Client" else "unknown",
        rationale="Seed and account research owner context.",
    )]
    relationships = []
    used_ids = {"owner"}
    role_relation = {
        "architect": "설계 계약", "consultant": "자문 / 설계 지원", "epc": "EPC 발주",
        "gc": "공사 발주", "vendor": "Package / Solution 공급", "authority": "인허가 관계",
        "company": "사업 참여", "project": "사업 주체", "owner": "투자 / 의사결정",
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
            if temporal in {"candidate", "historical"} and credibility == "confirmed":
                credibility = "hypothesis"
            actors.append(ProjectActor(
                actor_id=actor_id,
                role=entity.entity_type.replace("_", " ").title(),
                organization=entity.name,
                temporal_scope=temporal,
                participation_status=(
                    "Current project participation unconfirmed" if temporal != "current"
                    else "Current project participant / verify relationship"
                ),
                credibility=credibility,
                rationale="Discovered during iterative research.",
                evidence_labels=entity.evidence_labels,
            ))
            relationships.append(ProjectRelationship(
                from_actor_id="owner",
                to_actor_id=actor_id,
                relationship_type=role_relation.get(entity.entity_type, "사업 관계"),
                description="Relationship derived from research entity; detailed contract status requires evidence review.",
                temporal_scope=temporal,
                credibility=credibility,
                evidence_labels=entity.evidence_labels,
            ))
    return RelationshipDecisionMap(
        actors=actors[:20],
        relationships=relationships[:30],
        decision_structure_summary=f"Owner-centered map with {max(0, len(actors)-1)} discovered actor(s).",
        unknown_critical_actors=[gap for gap in intelligence.unresolved_gaps if any(x in gap.casefold() for x in ("epc", "gc", "architect", "consultant"))][:10],
    )


def decide_business_development(
    bundle: ResearchBundle,
    rule_result: RuleEngineResult,
    intelligence: ProjectIntelligence,
) -> BusinessDevelopmentDecision:
    status = rule_result.stage_gate.status
    if status == "closed":
        decision, headline, direction = "closed", "CLOSED · Active Pursuit Stop", "현재건 공략을 중단하고 참여·발주 구조를 다음 기회에 활용"
    elif status == "golden_time":
        decision, headline, direction = "now", "NOW · PRIORITY WINDOW", "설계·Spec·Partner 구조에 즉시 영향력 확보"
    elif status == "targeting":
        decision, headline, direction = "now", "NOW · EARLY POSITIONING", "관계 형성과 사업구도 선점"
    elif status == "local_action" and intelligence.open_scopes:
        decision, headline, direction = "needs_confirm", "NEEDS CONFIRM · Remaining Scope", "미발주·구매경로·변경 범위를 우선 확인"
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
        rationale=rule_result.stage_gate.rationale,
        context_basis=basis[:8],
        evidence_labels=labels[:8],
        action_direction=direction,
        trigger_to_reassess=intelligence.next_trigger,
        priority_window=status == "golden_time",
    )


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
    if rule_result.stage_gate.active_pursuit == "stop" or (decision and decision.decision in {"monitor", "closed"}):
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
    closed = rule_result.stage_gate.active_pursuit == "stop"
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
    if rule_result.stage_gate.active_pursuit == "stop" or (decision and decision.decision in {"monitor", "closed"}):
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
    decision = decide_business_development(bundle, rule_result, intelligence)
    workstreams = select_workstreams(
        bundle, rule_result, seed=seed, runner=runner, catalog=catalog,
        decision=decision, intelligence=intelligence,
    )
    commercial = assess_commercial_entry(
        bundle, rule_result, workstreams, seed=seed, runner=runner,
        decision=decision, intelligence=intelligence,
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
    if commercial.stakeholders and decision.decision in {"now", "needs_confirm"}:
        for stakeholder in commercial.stakeholders:
            meeting_plans.append(StakeholderMeetingPlan(
                stakeholder_role=stakeholder.role,
                why_meet=stakeholder.why_meet,
                information_to_obtain=stakeholder.information_to_get,
                open=engagement.talking_points.open,
                power=engagement.talking_points.power,
                win=engagement.talking_points.win,
            ))
    return BDV2AnalysisResult(
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
    )
