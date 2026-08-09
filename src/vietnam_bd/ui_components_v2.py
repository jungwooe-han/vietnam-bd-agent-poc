from __future__ import annotations

import json

import streamlit as st

from src.common import confidence

from .models import BDV2AnalysisResult, EvidenceItem, IntelligenceItem, TalkingPoint


STAGES = [
    "사업기획", "타당성 조사", "Master Plan", "설계 - SD (기본)", "설계 - DD (기본)",
    "설계 - CD (기본)", "건설 인허가", "시공", "운영 인허가", "프로젝트 종료",
]


def inject_v2_css() -> None:
    st.markdown("""
    <style>
      .v2-kicker{font-size:.72rem;font-weight:800;letter-spacing:.09em;color:#687086;text-transform:uppercase}
      .v2-card{border:1px solid #e4e8f2;border-radius:16px;padding:14px 16px;background:#fff;min-height:116px;box-shadow:0 3px 12px rgba(20,40,120,.05)}
      .v2-value{font-size:1.18rem;font-weight:800;color:#1428a0;margin:.3rem 0}.v2-muted{font-size:.82rem;color:#667085}
      .v2-decision{border-radius:18px;padding:18px 20px;background:linear-gradient(120deg,#101c4c,#1428a0);color:white;margin:12px 0 18px}
      .v2-decision h2{color:white;margin:.15rem 0}.v2-badge{display:inline-block;padding:3px 9px;border-radius:999px;background:#eef1ff;color:#1428a0;font-size:.72rem;font-weight:800}
      .v2-brief{border-left:5px solid #1428a0;background:#f6f8ff;border-radius:12px;padding:14px 17px;margin:10px 0 18px}
      .v2-stage{display:flex;gap:3px;align-items:flex-start;overflow-x:auto;padding:8px 0 14px}.v2-step{min-width:76px;text-align:center;font-size:.68rem;color:#98a0b3}.v2-dot{height:8px;background:#d9deea;border-radius:9px;margin-bottom:6px}.v2-step.done .v2-dot{background:#7686d5}.v2-step.current{font-weight:800;color:#1428a0}.v2-step.current .v2-dot{height:12px;background:#1428a0;margin-top:-2px}
      .actor-current{color:#1428a0}.actor-historical{color:#667085}.actor-candidate{color:#9a6700}
      @media(max-width:720px){.v2-card{min-height:auto}.v2-stage{gap:2px}.v2-step{min-width:60px}}
    </style>
    """, unsafe_allow_html=True)


def _compact_card(label: str, value: str, credibility: str, evidence_count: int = 0) -> None:
    st.markdown(
        f"<div class='v2-card'><div class='v2-kicker'>{label}</div><div class='v2-value'>{value or 'Unknown'}</div>"
        f"<span class='v2-badge'>{credibility.upper()}</span><div class='v2-muted'>Evidence {evidence_count}</div></div>",
        unsafe_allow_html=True,
    )


def _evidence_detail(title: str, items: list[EvidenceItem]) -> None:
    with st.expander(f"{title} 근거 보기"):
        if not items:
            st.info("표시할 근거가 없습니다.")
        for item in items:
            st.markdown(f"**{confidence.icon(item.credibility)} {item.claim}** · `{confidence.label(item.credibility)}`")
            st.caption(item.rationale)
            if item.source_labels:
                st.caption("Source: " + " · ".join(item.source_labels))


def _stage_progress(current: str) -> None:
    st.markdown("#### PROJECT STAGE")
    if current not in STAGES:
        st.info("현재 사업 단계가 확정되지 않아 lifecycle 위치를 표시하지 않습니다.")
        return
    current_index = STAGES.index(current)
    steps = []
    for index, stage in enumerate(STAGES):
        css = "current" if index == current_index else "done" if index < current_index else ""
        short = stage.replace("설계 - ", "").replace(" (기본)", "")
        steps.append(f"<div class='v2-step {css}'><div class='v2-dot'></div><div>{index+1}</div><div>{short}</div></div>")
    st.markdown("<div class='v2-stage'>" + "".join(steps) + "</div>", unsafe_allow_html=True)


def _render_relationship_map(result: BDV2AnalysisResult) -> None:
    st.markdown("#### RELATIONSHIP / DECISION MAP")
    relationship_map = result.relationship_map
    if not relationship_map.actors:
        st.info("Research evidence로 확인된 Actor가 없습니다.")
        return
    actor_ids = {actor.actor_id for actor in relationship_map.actors}
    lines = ["digraph G {", 'rankdir="LR";', 'graph [bgcolor="transparent", pad="0.2"];', 'node [shape="box", style="rounded,filled", fontname="Arial", fontsize="10"];']
    for actor in relationship_map.actors:
        color = {"current": "#dfe6ff", "historical": "#eef0f4", "candidate": "#fff1c7"}[actor.temporal_scope]
        label = f"{actor.role}\\n{actor.organization}\\n{actor.temporal_scope} · {actor.credibility}".replace('"', "'")
        lines.append(f'"{actor.actor_id}" [label="{label}", fillcolor="{color}"];')
    for edge in relationship_map.relationships:
        if edge.from_actor_id in actor_ids and edge.to_actor_id in actor_ids:
            style = "dashed" if edge.temporal_scope != "current" else "solid"
            label = f"{edge.relationship_type}\\n{edge.temporal_scope}/{edge.credibility}".replace('"', "'")
            lines.append(f'"{edge.from_actor_id}" -> "{edge.to_actor_id}" [label="{label}", style="{style}", fontsize="9"];')
    lines.append("}")
    try:
        st.graphviz_chart("\n".join(lines), use_container_width=True)
    except Exception:  # noqa: BLE001
        for actor in relationship_map.actors:
            st.markdown(f"- **{actor.role}: {actor.organization}** · {actor.temporal_scope} / {actor.credibility}")
    with st.expander("Relationship provenance"):
        for actor in relationship_map.actors:
            st.markdown(f"**{actor.role} · {actor.organization}** — {actor.temporal_scope} / {actor.credibility}")
            st.caption(actor.participation_status + (f" · {actor.rationale}" if actor.rationale else ""))
            if actor.evidence_labels:
                st.caption("Evidence: " + " · ".join(actor.evidence_labels))
        for edge in relationship_map.relationships:
            st.markdown(f"- `{edge.from_actor_id}` → `{edge.to_actor_id}` · {edge.relationship_type} · {edge.temporal_scope}/{edge.credibility}")


def render_page_1_opportunity(result: BDV2AnalysisResult) -> None:
    inject_v2_css()
    st.markdown("<div class='v2-kicker'>PAGE 1 · OPPORTUNITY DECISION</div>", unsafe_allow_html=True)
    st.title(result.opportunity_title)
    factors = (("TIMING", result.can_we_enter.timing), ("ACCESS", result.can_we_enter.access), ("FIT", result.can_we_enter.fit))
    cols = st.columns(3)
    for col, (label, factor) in zip(cols, factors):
        with col:
            _compact_card(label, factor.level, factor.level, len(factor.evidence_labels))
            with st.expander("근거"):
                st.caption(factor.rationale)
                if factor.evidence_labels:
                    st.caption(" · ".join(factor.evidence_labels))

    st.markdown("#### 4-AXIS OPPORTUNITY CONTEXT")
    context = result.context
    structure_value = " · ".join(item.claim for item in context.business_structure[:2]) or "Unknown"
    needs_value = " · ".join(item.claim for item in context.customer_needs[:2]) or "Unknown"
    context_cards = (
        ("건축 유형", context.building_type.claim, context.building_type.credibility, len(context.building_type.source_labels)),
        ("사업 단계", context.business_stage.claim, context.business_stage.credibility, len(context.business_stage.source_labels)),
        ("사업 구도", structure_value, context.business_structure[0].credibility if context.business_structure else "unknown", sum(len(x.source_labels) for x in context.business_structure)),
        ("고객 니즈", needs_value, context.customer_needs[0].credibility if context.customer_needs else "unknown", sum(len(x.source_labels) for x in context.customer_needs)),
    )
    cols = st.columns(4)
    for col, card in zip(cols, context_cards):
        with col:
            _compact_card(*card)
    _evidence_detail("4축 Context", [context.building_type, context.business_stage, *context.business_structure, *context.customer_needs])
    _stage_progress(context.business_stage.claim)

    decision = result.bd_decision
    if decision:
        st.markdown(
            f"<div class='v2-decision'><div class='v2-kicker' style='color:#cbd3ff'>BUSINESS DEVELOPMENT DECISION</div>"
            f"<h2>{decision.headline}</h2><div>{decision.action_direction}</div></div>",
            unsafe_allow_html=True,
        )
        with st.expander("판단 근거"):
            st.write(decision.rationale)
            st.markdown("**Context Basis:** " + " · ".join(decision.context_basis))
            if decision.evidence_labels:
                st.caption("Evidence: " + " · ".join(decision.evidence_labels))
    briefing = result.executive_summary.strip().replace("\n", " ")
    st.markdown(f"<div class='v2-brief'><div class='v2-kicker'>EXECUTIVE BRIEFING</div><b>{briefing[:600]}</b></div>", unsafe_allow_html=True)
    _render_relationship_map(result)


def _intelligence_group(title: str, items: list[IntelligenceItem]) -> None:
    st.markdown(f"#### {title}")
    if not items:
        st.caption("확인된 정보 없음")
    for item in items:
        with st.expander(f"{confidence.icon(item.credibility)} {item.claim}"):
            st.write(item.rationale)
            st.caption(f"{item.temporal_scope} · {item.credibility}")
            if item.evidence_labels:
                st.caption("Evidence: " + " · ".join(item.evidence_labels))
            if item.source_urls:
                st.caption("Source: " + " · ".join(item.source_urls))
            if item.source_dates:
                st.caption("Date: " + " · ".join(item.source_dates))


def render_page_2_strategy(result: BDV2AnalysisResult) -> None:
    inject_v2_css()
    st.markdown("<div class='v2-kicker'>PAGE 2 · ACCOUNT / PROJECT STRATEGY</div>", unsafe_allow_html=True)
    intelligence = result.project_intelligence
    st.subheader("Owner / Account Intelligence")
    st.markdown(f"<div class='v2-brief'><b>{intelligence.owner_summary or 'Owner information requires confirmation.'}</b></div>", unsafe_allow_html=True)
    _intelligence_group("Current Project Facts", intelligence.current_project_facts)
    _intelligence_group("Historical Projects", intelligence.historical_projects)
    _intelligence_group("Project Ecosystem", intelligence.project_ecosystem)
    _intelligence_group("Current Check Candidates", intelligence.ecosystem_candidates)
    if intelligence.repeated_partner_patterns:
        st.markdown("#### Repeated Partner Patterns")
        for pattern in intelligence.repeated_partner_patterns:
            st.markdown(f"- **{pattern.partner} · {pattern.role}** — {pattern.pattern_summary} · current: `{pattern.current_participation}`")
    if intelligence.project_timeline:
        st.markdown("#### Project Timeline")
        for item in intelligence.project_timeline:
            st.markdown(f"- **{item.date_or_period}** · {item.milestone} · `{item.credibility}`")
    if intelligence.source_conflicts:
        with st.expander("Source Conflicts"):
            for conflict in intelligence.source_conflicts:
                st.markdown(f"- {conflict}")
    if intelligence.unresolved_gaps:
        with st.expander("Unresolved Research Gaps"):
            for gap in intelligence.unresolved_gaps:
                st.markdown(f"- {gap}")

    mode = result.bd_decision.decision if result.bd_decision else "now"
    if mode in {"now", "needs_confirm"}:
        st.subheader("Evidence-grounded Workstream Top 3")
        st.caption("임시 Vertical guardrail 후보이며 확정 taxonomy가 아닙니다.")
        if not result.workstreams:
            st.info("현재 evidence로 정당화된 Workstream이 없습니다.")
        for item in result.workstreams:
            with st.expander(f"#{item.rank} {item.workstream}", expanded=item.rank == 1):
                st.write(item.why_relevant)
                st.caption("Context: " + " · ".join(item.context_basis))
                if item.grounded_capabilities:
                    st.markdown("**Grounded Capabilities**")
                    for capability in item.grounded_capabilities:
                        st.markdown(f"- **{capability.capability}** · `{capability.credibility}`")
                        st.caption(capability.rationale)
                        st.caption("Basis: " + " · ".join(capability.context_basis))
                        st.caption("Evidence: " + " · ".join(capability.evidence_labels))
    elif mode == "monitor":
        st.subheader("Watch Signal / Next Trigger")
        for signal in intelligence.watch_signals:
            st.markdown(f"- {signal}")
        st.info(f"NEXT TRIGGER · {intelligence.next_trigger or 'Trigger requires definition'}")
    else:
        st.subheader("Historical Intelligence")
        st.info("Active Pursuit는 중단되었습니다. 참여·발주 구조와 반복 Partner를 다음 기회에 활용합니다.")


def _talking(item: TalkingPoint) -> None:
    with st.expander(item.question):
        st.markdown(f"**Information Goal**  \n{item.information_goal}")
        st.markdown(f"**Why It Matters**  \n{item.why_it_matters}")
        st.markdown(f"**If Positive**  \n{item.next_action_if_positive}")
        st.markdown(f"**If Negative / Unknown**  \n{item.next_action_if_negative_or_unknown}")


def render_page_3_meeting(result: BDV2AnalysisResult) -> None:
    inject_v2_css()
    st.markdown("<div class='v2-kicker'>PAGE 3 · MEETING / ACTION</div>", unsafe_allow_html=True)
    mode = result.bd_decision.decision if result.bd_decision else "now"
    if mode == "closed":
        st.error("CLOSED · 현재 프로젝트의 적극적인 Meeting Plan과 NBA는 생성하지 않습니다.")
        _intelligence_group("Awarded / Historical Actors", result.project_intelligence.project_ecosystem)
        return
    st.subheader("Stakeholder Priority")
    plans = {plan.stakeholder_role: plan for plan in result.stakeholder_meeting_plans}
    for index, person in enumerate(result.stakeholders, start=1):
        priority = "HIGH PRIORITY" if index == 1 or person.priority == "primary" else "MEDIUM" if person.priority == "secondary" else "OPTIONAL"
        with st.expander(f"#{index} {person.role} · {priority}", expanded=index == 1):
            st.write(person.why_meet)
            if person.organization_or_candidate:
                st.markdown(f"**Organization / Candidate:** {person.organization_or_candidate}")
            st.caption(f"{person.credibility} · {person.rationale}")
            if person.evidence_labels:
                st.caption("Evidence: " + " · ".join(person.evidence_labels))
            for value in person.information_to_get:
                st.markdown(f"- {value}")
            plan = plans.get(person.role)
            if plan:
                for title, items in (("OPEN", plan.open), ("POWER", plan.power), ("WIN", plan.win)):
                    if items:
                        st.markdown(f"**{title}**")
                        for item in items:
                            st.markdown(f"- {item.question}")
    if mode == "monitor":
        st.subheader("Trigger Confirmation Plan")
        for signal in result.project_intelligence.watch_signals:
            st.markdown(f"- 확인: {signal}")
        st.info(f"NEXT TRIGGER · {result.project_intelligence.next_trigger or '확인 필요'}")
        return
    st.subheader("Research-grounded Talking Points")
    for title, items in (("OPEN", result.talking_points.open), ("POWER", result.talking_points.power), ("WIN", result.talking_points.win)):
        st.markdown(f"#### {title}")
        for item in items:
            _talking(item)
    st.subheader("Next Best Action")
    for item in result.next_best_actions:
        with st.expander(f"{item.priority.upper()} · {item.action}", expanded=item.priority == "now"):
            st.markdown(f"**Target:** {item.target}")
            st.markdown(f"**Purpose:** {item.purpose}")
            st.markdown(f"**Done Criteria:** {item.done_criteria}")


def render_research_trace(trace: dict) -> None:
    with st.expander("Developer · Research Trace", expanded=False):
        readiness = trace.get("context_readiness")
        if readiness:
            st.markdown("**Context Readiness**")
            st.json(readiness)
        for rnd in trace.get("research_rounds", []):
            st.markdown(f"### Round {rnd.get('round_number')} · {rnd.get('focus')}")
            st.caption(f"Termination: {rnd.get('termination_reason') or 'continued'}")
            st.markdown("**New Evidence**")
            st.json(rnd.get("new_evidence", []))
            st.markdown("**Findings**")
            st.json(rnd.get("findings", {}))
            st.markdown("**Discovered Entities**")
            st.json(rnd.get("discovered_entities", []))
            st.markdown("**Research Gaps**")
            st.json(rnd.get("research_gaps", []))
            st.markdown("**Follow-up Queries**")
            st.json(rnd.get("follow_up_queries", []))
            st.markdown("**Claims to Verify**")
            st.json(rnd.get("claims_to_verify", []))


# Compatibility wrappers for callers/tests using the previous v2 component names.
render_v2_overview = render_page_1_opportunity
render_v2_context = render_page_1_opportunity
render_v2_workstreams = render_page_2_strategy
render_v2_evidence = render_page_2_strategy
render_v2_historical_intelligence = render_page_2_strategy
render_v2_can_we_enter = lambda result: None
render_v2_information_to_confirm = lambda result: None
render_v2_stakeholders = render_page_3_meeting
render_v2_meeting_intelligence = render_page_3_meeting
render_v2_next_actions = render_page_3_meeting
