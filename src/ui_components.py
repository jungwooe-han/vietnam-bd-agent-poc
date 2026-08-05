from __future__ import annotations

import streamlit as st

from .models import AnalysisResult, EvidenceItem

LABEL = {"confirmed": "확인", "likely": "가능성 높음", "hypothesis": "검증 가설", "unknown": "미확인"}
ICON = {"confirmed": "✅", "likely": "🔎", "hypothesis": "💡", "unknown": "❓"}


def inject_css() -> None:
    st.markdown("""
    <style>
      .block-container {max-width: 1050px; padding-top: 1.3rem; padding-bottom: 4rem;}
      .hero {padding: 1.25rem 1.4rem; border-radius: 18px; background: linear-gradient(135deg,#0d1b52,#1428a0); color:white; margin-bottom:1rem;}
      .hero h1 {font-size:1.65rem; margin:0 0 .35rem 0; color:white;}
      .hero p {margin:0; opacity:.9;}
      .summary-card {background:white; border:1px solid #e7e9f1; border-radius:16px; padding:1rem 1.1rem; margin:.55rem 0; box-shadow:0 2px 10px rgba(20,40,160,.05);}
      .mini-label {font-size:.78rem; color:#697086; font-weight:700; text-transform:uppercase; letter-spacing:.04em;}
      .big-value {font-size:1.05rem; font-weight:700; margin-top:.2rem;}
      div[data-testid="stExpander"] {border:1px solid #e7e9f1; border-radius:14px; background:white;}
      .stButton > button {border-radius:12px; font-weight:700; min-height:2.8rem;}
      @media (max-width: 640px) {
        .block-container {padding-left:.8rem; padding-right:.8rem; padding-top:.7rem;}
        .hero {padding:1rem; border-radius:14px;}
        .hero h1 {font-size:1.35rem;}
      }
    </style>
    """, unsafe_allow_html=True)


def evidence_line(item: EvidenceItem) -> None:
    st.markdown(f"**{ICON[item.credibility]} {item.claim}** · `{LABEL[item.credibility]}`")
    st.caption(item.rationale)
    if item.source_labels:
        st.caption("근거: " + " · ".join(item.source_labels))


def render_overview(result: AnalysisResult) -> None:
    st.markdown(f"<div class='hero'><h1>{result.opportunity_title}</h1><p>{result.executive_summary}</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='summary-card'><div class='mini-label'>현재 단계</div><div class='big-value'>{result.current_stage}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='summary-card'><div class='mini-label'>Lead Domain</div><div class='big-value'>{result.portfolio.lead_domain}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='summary-card'><div class='mini-label'>즉시 Action</div><div class='big-value'>{result.next_steps[0]}</div></div>", unsafe_allow_html=True)
    st.subheader("왜 지금 사업기회인가")
    st.write(result.why_opportunity_now)
    st.caption("단계 판단 근거: " + result.stage_basis)


def render_qualification(result: AnalysisResult) -> None:
    st.subheader("Opportunity Qualification")
    st.markdown("#### Business Objective")
    evidence_line(result.business_objective)
    st.markdown("#### Decision Drivers")
    for item in result.decision_drivers:
        evidence_line(item)
    st.markdown("#### Customer Needs")
    for item in result.customer_needs:
        evidence_line(item)
    st.markdown("#### 아직 모르는 핵심 정보")
    for x in result.critical_unknowns:
        st.markdown(f"- {x}")


def render_dx(result: AnalysisResult) -> None:
    p = result.portfolio
    st.subheader("Samsung DX Perspective")
    st.info(f"**Lead:** {p.lead_domain}\n\n{p.lead_reason}")
    if p.supporting_domains:
        st.markdown("**Supporting Domains:** " + " · ".join(p.supporting_domains))
    st.markdown("#### 어떤 이야기로 시작할까")
    st.write(p.conversation_entry)
    st.markdown("#### 연결 가능한 역량")
    for x in p.relevant_capabilities:
        st.markdown(f"- {x}")
    st.warning(p.caution)


def render_meeting(result: AnalysisResult) -> None:
    st.subheader("Meeting Intelligence")
    st.markdown("#### 누구를 만나야 하나")
    for person in result.stakeholders:
        with st.expander(f"{person.role} · {person.priority}"):
            st.write(person.why_meet)
            st.markdown("**반드시 확보할 정보**")
            for x in person.information_to_get:
                st.markdown(f"- {x}")
    st.markdown("#### 핵심 질문")
    for idx, q in enumerate(result.priority_questions, 1):
        with st.expander(f"{idx}. {q.question}", expanded=idx == 1):
            st.markdown(f"**왜 중요한가**  \n{q.why_it_matters}")
            st.markdown(f"**무엇을 판단할 수 있나**  \n{q.decision_enabled}")
            st.markdown(f"**YES라면**  \n{q.if_yes}")
            st.markdown(f"**NO/미확인이라면**  \n{q.if_no_or_unknown}")


def render_internal(result: AnalysisResult) -> None:
    st.subheader("Internal Intelligence")
    if not result.similar_cases:
        st.info("Internal library not connected. 더미데이터가 추가되면 유사 사업기회와 내부 Owner를 연결합니다.")
        return
    for case in result.similar_cases:
        with st.expander(case.title):
            st.write(case.similarity_reason)
            if case.internal_owner:
                st.markdown(f"**문의할 Owner:** {case.internal_owner}")
            if case.lesson_learned:
                st.markdown(f"**Lesson Learned:** {case.lesson_learned}")


def render_next_steps(result: AnalysisResult) -> None:
    st.subheader("Next Step Navigator")
    for idx, step in enumerate(result.next_steps, 1):
        st.markdown(f"<div class='summary-card'><div class='mini-label'>STEP {idx}</div><div class='big-value'>{step}</div></div>", unsafe_allow_html=True)
    if result.limitations:
        with st.expander("분석 한계"):
            for x in result.limitations:
                st.markdown(f"- {x}")
    if result.source_summary:
        with st.expander("참고한 출처/맥락"):
            for x in result.source_summary:
                st.markdown(f"- {x}")
