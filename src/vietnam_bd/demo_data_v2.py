from __future__ import annotations

from .models import (
    AccessibilityFactor,
    BDV2AnalysisResult,
    BDV2Stakeholder,
    BusinessDevelopmentDecision,
    CanWeEnter,
    ContextClassification,
    EvidenceItem,
    GroundedCapability,
    IntelligenceItem,
    InformationToConfirm,
    MeetingTalkingPoints,
    MustKnowItem,
    NextBestAction,
    PartnerPattern,
    ProjectActor,
    ProjectIntelligence,
    ProjectRelationship,
    ProposalHypothesis,
    RelationshipDecisionMap,
    StageGate,
    TalkingPoint,
    WorkstreamRecommendation,
)
from .sfdc_sample import match_sample_opportunities


def _evidence(claim: str, credibility: str = "likely") -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        credibility=credibility,
        rationale="Mock Research Evidence for v2 UI validation.",
        source_labels=["Demo source"],
    )


def _factor(level: str, rationale: str) -> AccessibilityFactor:
    return AccessibilityFactor(level=level, rationale=rationale, evidence_labels=["Demo source"])


def _talking(question: str) -> TalkingPoint:
    return TalkingPoint(
        question=question,
        information_goal="현재 의사결정 상태 확인",
        why_it_matters="답에 따라 접촉 대상과 다음 행동이 달라집니다.",
        next_action_if_positive="관련 기술 담당자와 후속 검토를 진행합니다.",
        next_action_if_negative_or_unknown="잠금 상태와 대체 진입 경로를 확인합니다.",
    )


def demo_v2_result(*, closed: bool = False, decision: str | None = None) -> BDV2AnalysisResult:
    mode = "closed" if closed else (decision or "now")
    is_closed = mode == "closed"
    is_monitor = mode == "monitor"
    stage_claim = "프로젝트 종료" if is_closed else "시공" if is_monitor else "설계 - DD (기본)"
    context = ContextClassification(
        customer_needs=[_evidence("RE100 / ESG / OPEX 절감")],
        building_type=_evidence("신축"),
        business_stage=_evidence(stage_claim, "confirmed"),
        business_structure=[_evidence("End Client"), _evidence("GC / EPC", "hypothesis")],
    )
    gate = StageGate(
        status="closed" if is_closed else "local_action" if is_monitor else "golden_time",
        research_depth="limited" if is_closed or is_monitor else "deep",
        active_pursuit="stop" if is_closed else "limited" if is_monitor else "active",
        historical_intelligence="limited" if is_closed else "none",
        rationale="Mock stage gate for v2 UI validation.",
        remaining_window="과거 구조 학습" if is_closed else "남은 범위 확인" if is_monitor else "사양 영향 가능 시기",
        recommended_focus="과거 참여사 확인" if is_closed else "구매경로 확인" if is_monitor else "설계·EPC 의사결정 구조",
    )
    stakeholders = [
        BDV2Stakeholder(
            actor_id="epc",
            role="EPC",
            organization_or_candidate="Demo Engineering",
            priority="primary",
            credibility="hypothesis" if is_closed else "likely",
            why_meet="과거 참여 구조 확인" if is_closed else "사업단계와 의사결정 구조 확인",
            information_to_get=[] if is_closed else ["EPC 선정 상태", "사양 결정 일정"],
            evidence_labels=["Demo source"],
            rationale="공개 근거 기반 mock candidate",
        )
    ]
    empty_talking = MeetingTalkingPoints()
    talking = MeetingTalkingPoints(
        open=[_talking("현재 미확정인 설비 범위는 무엇입니까?")],
        power=[_talking("최종 사양 승인 조직은 어디입니까?")],
        win=[_talking("Vendor shortlist 진입 조건은 무엇입니까?")],
    )
    result = BDV2AnalysisResult(
        opportunity_title="Closed Project Historical Intelligence" if is_closed else "Vietnam Factory Expansion Opportunity",
        executive_summary="현재 프로젝트 참여 구조를 다음 기회에 활용합니다." if is_closed else "현재 단계와 EPC 선정 상태를 기준으로 우선 행동을 결정해야 합니다.",
        evidence=[
            _evidence("Demo Owner announced the project", "confirmed"),
            _evidence("Demo Engineering participated in a prior owner project", "hypothesis"),
        ],
        context=context,
        stage_gate=gate,
        workstreams=[] if is_closed or is_monitor else [
            WorkstreamRecommendation(
                rank=1,
                workstream="Facility / Energy",
                why_relevant="에너지 니즈와 신축 설계 단계가 함께 확인됩니다.",
                context_basis=["RE100", "신축", "Master Plan"],
                possible_capabilities=[],
                grounded_capabilities=[GroundedCapability(
                    capability="Energy monitoring capability",
                    rationale="신규 제조시설의 Energy/OPEX 니즈가 확인됩니다.",
                    context_basis=["신축", stage_claim, "RE100 / ESG / OPEX 절감"],
                    evidence_labels=["Demo source"],
                    credibility="likely",
                )],
                caution="임시 guardrail 후보이며 확정 taxonomy가 아닙니다.",
            )
        ],
        excluded_workstreams=[],
        can_we_enter=CanWeEnter(
            timing=_factor("low" if is_closed else "medium" if is_monitor else "high", "현재 단계 기준"),
            access=_factor("unknown", "접점 정보 확인 필요"),
            openness=_factor("low" if is_closed else "unknown" if is_monitor else "medium", "사양 및 발주 상태 기준"),
            fit=_factor("unknown" if is_closed else "medium", "추가 기술 검증 필요"),
            overall_view="Active pursuit stopped; historical learning only." if is_closed else "초기 접촉과 사양 상태 확인이 필요합니다.",
        ),
        information_to_confirm=[] if is_closed else [
            InformationToConfirm(
                topic="EPC가 선정되었는가?",
                why_it_matters="접촉 대상과 진입 경로가 달라집니다.",
                action_if_confirmed="EPC 구매·설계 조직을 확인합니다.",
                action_if_not_confirmed="Owner와 설계 기준을 선점합니다.",
                suggested_way_to_check="Owner PM에게 선정 상태와 일정을 확인합니다.",
            )
        ],
        stakeholders=stakeholders,
        talking_points=empty_talking if is_closed or is_monitor else talking,
        next_best_actions=[] if is_closed or is_monitor else [
            NextBestAction(
                action="EPC 선정 상태 확인",
                target="Owner Project Manager",
                purpose="공략 경로 결정",
                done_criteria="EPC 명칭, 선정 상태, 책임 조직 기록",
                priority="now",
            )
        ],
        similar_cases=[],
        source_summary=["Demo source"],
        limitations=["Mock data for UI validation"],
        bd_decision=BusinessDevelopmentDecision(
            decision=mode,
            headline={"now":"NOW · PRIORITY WINDOW","monitor":"MONITOR · Wait for Trigger","closed":"CLOSED · Active Pursuit Stop"}[mode],
            rationale="Mock decision based on stage and open-scope evidence.",
            context_basis=["신축", stage_claim, "EPC 선정 상태"],
            evidence_labels=["Demo source"],
            action_direction={"now":"설계·Partner 구조에 즉시 개입","monitor":"Tender와 Actor 선정을 추적","closed":"다음 기회를 위한 구조 학습"}[mode],
            trigger_to_reassess="EPC Tender 확인",
            priority_window=mode == "now",
        ),
        project_intelligence=ProjectIntelligence(
            owner_summary="Demo Owner · Vietnam manufacturing account",
            current_project_facts=[IntelligenceItem(claim="Vietnam factory project",credibility="confirmed",rationale="Owner announcement",evidence_labels=["Demo source"],source_urls=["https://example.com/current"],source_dates=["2026-01-01"],temporal_scope="current")],
            historical_projects=[IntelligenceItem(claim="Prior Factory A used Demo Engineering",credibility="confirmed",rationale="Prior award notice",evidence_labels=["Demo historical source"],temporal_scope="historical")],
            ecosystem_candidates=[IntelligenceItem(claim="Demo Engineering current participation unconfirmed",credibility="hypothesis",rationale="Repeated historical partner only",evidence_labels=["Demo historical source"],temporal_scope="candidate")],
            repeated_partner_patterns=[PartnerPattern(partner="Demo Engineering",role="EPC",historical_project_count=2,pattern_summary="2 prior projects",current_participation="unconfirmed",credibility="hypothesis",evidence_labels=["Demo historical source"])],
            open_scopes=[IntelligenceItem(claim="EPC package remains open",credibility="likely",rationale="Current tender notice",evidence_labels=["Demo source"],source_urls=["https://example.com/tender"],temporal_scope="current")] if not is_closed else [],
            watch_signals=["EPC Tender", "Architect selection"],
            next_trigger="EPC Tender 확인",
            unresolved_gaps=["Current EPC", "Architect selection"],
        ),
        relationship_map=RelationshipDecisionMap(
            actors=[
                ProjectActor(actor_id="owner",role="Owner / End Client",organization="Demo Owner",temporal_scope="current",actor_status="confirmed",participation_status="Current owner",credibility="confirmed",evidence_labels=["Demo source"],source_urls=["https://example.com/current"]),
                ProjectActor(actor_id="epc",role="EPC",organization="Demo Engineering",temporal_scope="historical" if is_closed else "candidate",actor_status="candidate",participation_status="Current participation unconfirmed",credibility="hypothesis",evidence_labels=["Demo historical source"]),
            ],
            relationships=[ProjectRelationship(from_actor_id="owner",to_actor_id="epc",relationship_type="Historical EPC award",temporal_scope="historical",credibility="confirmed",evidence_labels=["Demo historical source"])],
            decision_structure_summary="Owner-centered structure; current EPC requires confirmation.",
            unknown_critical_actors=["Current EPC", "Architect"],
        ),
        must_know_top3=[] if is_closed else [MustKnowItem(
            rank=1,
            question="Demo Engineering이 현재 프로젝트 EPC로 최종 선정되었는가?",
            why_it_matters="접촉 대상과 구매경로가 달라집니다.",
            decision_impact=["actor", "buying_route", "decision"],
            actor_ids=["epc"],
            evidence_labels=["Demo historical source"],
            suggested_way_to_check="Owner PM에게 EPC 선정 결과를 확인합니다.",
        )],
        proposal_hypotheses=[] if is_closed else [ProposalHypothesis(
            rank=1,
            workstream="Facility Energy Optimization",
            capability="SmartThings Pro",
            hypothesis=("에너지 운영 Scope 공략안을 구체화합니다." if mode == "now" else "Scope·구매경로 확인 후 에너지 운영 가설을 구체화합니다."),
            mode="actionable" if mode == "now" else "conditional",
            conditions_to_confirm=[] if mode == "now" else ["EPC package 선정 상태"],
            evidence_labels=["Demo source"],
            portfolio_source_url="https://www.samsung.com/sec/business/smartthingspro/",
        )],
    )
    if not is_closed:
        result.sample_sfdc_matches = match_sample_opportunities(
            "Demo Owner", context, ["Facility Energy Optimization"],
        )
    return result
