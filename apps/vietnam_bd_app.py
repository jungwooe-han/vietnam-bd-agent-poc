from __future__ import annotations

import json
import os

import streamlit as st

from src.vietnam_bd.engine import ProjectAnalysisInput, analyze_project
from src.vietnam_bd.history import get_analysis, list_analyses, save_analysis
from src.vietnam_bd.localization_v3 import ui
from src.vietnam_bd.ui_components import (
    inject_css,
    render_dx,
    render_internal,
    render_meeting,
    render_next_steps,
    render_overview,
    render_qualification,
)
from src.vietnam_bd.ui_components_v2 import (
    render_page_1_opportunity,
    render_page_2_strategy,
    render_page_3_meeting,
    render_research_trace,
)
from src.vietnam_bd.ui_components_v3 import (
    inject_v3_css,
    render_page_1_opportunity_v3,
    render_page_2_strategy_v3,
    render_page_3_meeting_v3,
)


def _render_entry_hero() -> None:
    st.markdown(
        """
        <section class="bd-entry-hero">
          <div class="bd-entry-eyebrow">VIETNAM MANUFACTURING · BD INTELLIGENCE</div>
          <h1>Find the opportunity<br>behind the news.</h1>
          <p>뉴스에서 사업기회를 발견하고, Samsung DX 관점의 다음 영업 행동까지 연결합니다.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _project_context() -> str:
    building_types = st.session_state.get("bd_building_types", [])
    project_stages = st.session_state.get("bd_project_stages", [])
    context = []
    if building_types:
        context.append("건축 유형: " + ", ".join(building_types))
    if project_stages:
        context.append("프로젝트 단계: " + ", ".join(project_stages))
    research_intent = st.session_state.get("bd_research_intent", "").strip()
    if research_intent:
        context.append("추가 확인이 필요한 정보 (Research Intent / Information Gap): " + research_intent)
    return "\n".join(context)


def render():
    inject_css()

    if "bd_stage" not in st.session_state:
        st.session_state.bd_stage = "input"
    if "bd_result" not in st.session_state:
        st.session_state.bd_result = None
    if "bd_seed" not in st.session_state:
        st.session_state.bd_seed = ""
    if "bd_engine" not in st.session_state:
        st.session_state.bd_engine = "BD v3"
    if "bd_result_version" not in st.session_state:
        st.session_state.bd_result_version = "legacy"
    if "bd_v2_research_trace" not in st.session_state:
        st.session_state.bd_v2_research_trace = {}
    if "bd_history_id" not in st.session_state:
        st.session_state.bd_history_id = None

    if st.session_state.bd_engine == "BD v3" or st.session_state.bd_result_version == "v3":
        inject_v3_css()

    if st.session_state.bd_stage not in {"input", "context"}:
        st.markdown(
            "<div class='hero'><h1>Vietnam Manufacturing BD Agent</h1>"
            "<p>아는 정보나 뉴스를 넣으면, 사업기회 관점으로 확장하고 첫 미팅에서 무엇을 알아와야 할지 안내합니다.</p></div>",
            unsafe_allow_html=True,
        )

    with st.sidebar:
        if st.button("＋ 새 분석", use_container_width=True):
            for key in (
                "bd_stage",
                "bd_result",
                "bd_seed",
                "bd_questions",
                "bd_building_types",
                "bd_project_stages",
                "bd_research_intent",
                "bd_uploaded_bytes",
                "bd_uploaded_name",
                "bd_handoff_company",
                "bd_result_version",
                "bd_v2_research_trace",
                "bd_history_id",
            ):
                st.session_state.pop(key, None)
            st.rerun()

        with st.expander("저장된 분석 이력", expanded=False):
            history_items = list_analyses()
            if not history_items:
                st.caption("아직 저장된 분석이 없습니다.")
            for item in history_items:
                created_label = item.created_at.replace("T", " ")[:16]
                if st.button(
                    f"{item.title}\n{created_label} · {item.result_version}",
                    key=f"bd_history_{item.history_id}",
                    use_container_width=True,
                ):
                    saved = get_analysis(item.history_id)
                    if saved is not None:
                        st.session_state.bd_seed = saved.seed
                        st.session_state.bd_result = saved.result
                        st.session_state.bd_result_version = saved.result_version
                        st.session_state.bd_v2_research_trace = saved.research_trace
                        st.session_state.bd_history_id = saved.history_id
                        st.session_state.bd_stage = "result"
                        st.rerun()

        with st.expander("고급 설정", expanded=False):
            engine = st.radio("분석 엔진", ["BD v3", "BD v2", "기존 BD"], key="bd_engine")
            demo_mode = st.checkbox("데모 모드", value=not bool(os.getenv("OPENAI_API_KEY")))
            st.caption("데모 모드는 API 호출 없이 예시 결과를 표시합니다.")
            closed_demo = st.checkbox("Closed 데모", value=False) if engine in {"BD v2", "BD v3"} and demo_mode else False
            developer_mode = st.checkbox("개발 모드 · Research Trace", value=False) if engine in {"BD v2", "BD v3"} else False

    if st.session_state.bd_stage == "input":
        _render_entry_hero()
        if st.session_state.get("bd_handoff_company"):
            st.info(f"📡 리드 센싱에서 전달된 기업: {st.session_state.bd_handoff_company} — 아래 내용을 확인하고 필요하면 보완하세요.")

        with st.container(key="bd_entry_composer"):
            seed = st.text_area(
                "분석할 뉴스",
                value=st.session_state.bd_seed,
                height=150,
                placeholder="뉴스 URL 또는 기사 내용을 입력하세요",
                label_visibility="collapsed",
            )
            spacer_col, upload_col, action_col = st.columns([4.5, 1.5, 1.7], vertical_alignment="center")
            spacer_col.empty()
            with upload_col.popover("＋ PDF 첨부", use_container_width=True):
                uploaded = st.file_uploader(
                    "PDF/TXT/MD 파일",
                    type=["pdf", "txt", "md"],
                    label_visibility="collapsed",
                )
            analyze_clicked = action_col.button("Analyze →", type="primary", use_container_width=True)

        st.markdown(
            '<div class="bd-entry-outcomes">사업단계 · 미팅 전략 · 토킹 포인트 · 확인 필요사항</div>'
            '<div class="bd-entry-privacy">공개 정보 또는 가명 데이터를 사용하세요. 실제 회사 기밀정보는 입력하지 마세요.</div>',
            unsafe_allow_html=True,
        )

        if analyze_clicked:
            if not seed.strip() and uploaded is None:
                st.warning("텍스트, URL 또는 파일 중 하나를 입력하세요.")
            else:
                st.session_state.bd_seed = seed
                st.session_state.bd_uploaded_bytes = uploaded.getvalue() if uploaded else None
                st.session_state.bd_uploaded_name = uploaded.name if uploaded else None
                st.session_state.bd_stage = "context"
                st.rerun()

    elif st.session_state.bd_stage == "context":
        _render_entry_hero()
        with st.container(key="bd_project_context"):
            st.markdown(
                '<div class="bd-context-head"><h2>알고 계신 내용을 공유해주세요</h2>'
                '<p>모든 항목은 선택사항입니다. 비워둔 채 분석해도 됩니다.</p></div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="bd-context-label">건축 유형</div>', unsafe_allow_html=True)
            with st.container(key="bd_building_choices"):
                st.pills(
                    "건축 유형",
                    ["신축", "리모델링", "증축", "스마트공장"],
                    selection_mode="multi",
                    key="bd_building_types",
                    label_visibility="collapsed",
                )

            st.markdown('<div class="bd-context-label bd-context-section">프로젝트 단계</div>', unsafe_allow_html=True)
            with st.container(key="bd_stage_choices"):
                st.pills(
                    "프로젝트 단계",
                    ["초기 기획", "설계 및 발주", "인허가", "시공"],
                    selection_mode="multi",
                    key="bd_project_stages",
                    label_visibility="collapsed",
                )

            st.markdown(
                '<div class="bd-context-question">'
                '<h3>알고 있는 정보와 특별히 확인하고 싶은 내용을 자유롭게 작성해주세요.</h3>'
                '<p>사업주, 시공사, 설계사 등 현재 파악된 정보가 많을수록 분석이 정교해지며, '
                '궁금한 내용을 함께 알려주시면 <strong>해당 정보에 초점을 맞춰 더 깊이 탐색합니다.</strong></p>'
                '</div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                "추가로 확인하고 싶은 정보",
                key="bd_research_intent",
                height=112,
                placeholder="예) 사업주는 삼성전자로 확인했지만 시공사는 아직 파악되지 않았습니다. 삼성전자가 과거 유사 프로젝트에서 어떤 시공사와 협업했는지 알고 싶습니다.",
                label_visibility="collapsed",
            )

            back_col, action_col = st.columns([1, 2.2], vertical_alignment="center")
            back_clicked = back_col.button("← 이전", use_container_width=True)
            analyze_context_clicked = action_col.button("분석 실행 →", type="primary", use_container_width=True)

        if back_clicked:
            st.session_state.bd_stage = "input"
            st.rerun()
        if analyze_context_clicked:
            guided = _project_context()

            if engine in {"BD v2", "BD v3"}:
                status = st.status(f"{engine} 분석을 시작합니다.", expanded=True)

                def progress(event: str, details: dict) -> None:
                    if event == "seed_understanding":
                        status.write("Seed 이해 중")
                    elif event == "context_research":
                        status.write("기본 Context 조사 중")
                    elif event == "context_research_supplement":
                        status.write(f"Context 보완 조사 {details['attempt']}/{details['maximum']} · {', '.join(details.get('missing', []))}")
                    elif event == "context_arbitration":
                        status.write("사업단계와 4축 Context 판단 중")
                    elif event == "stage_gate":
                        status.write(
                            f"Stage Gate: {details['status']} · Research: {details['research_depth']} · Pursuit: {details['active_pursuit']}"
                        )
                    elif event == "research_round":
                        mode_label = {
                            "deep": "심층 조사",
                            "limited": "제한 조사",
                            "historical": "Historical 조사",
                        }.get(details["mode"], details["mode"])
                        status.write(
                            f"{mode_label} Round {details['round']}/{details['total_rounds']} · {details['focus']}"
                        )
                    elif event == "research_round_complete":
                        status.write(
                            f"Round {details['round']}/{details['total_rounds']} 완료 · "
                            f"신규 Entity {details['discovered_entities']} · 남은 Gap {details['remaining_gaps']}"
                        )
                    elif event == "sales_reasoning":
                        status.write("영업 분석 생성 중")
                    elif event == "complete":
                        status.update(label=f"{engine} 상세 분석 완료", state="complete", expanded=False)

                try:
                    analysis_run = analyze_project(
                        ProjectAnalysisInput(
                            seed=st.session_state.bd_seed,
                            engine=engine,
                            guided_answers=guided,
                            uploaded_name=st.session_state.get("bd_uploaded_name"),
                            uploaded_bytes=st.session_state.get("bd_uploaded_bytes"),
                            demo_mode=demo_mode,
                            closed_demo=closed_demo,
                        ),
                        progress_callback=progress,
                    )
                    result = analysis_run.result
                    st.session_state.bd_v2_research_trace = analysis_run.research_trace
                    if demo_mode:
                        status.write("Mock v2 전체 결과 생성 완료")
                        status.update(label=f"{engine} 데모 분석 완료", state="complete", expanded=False)
                    st.session_state.bd_result = result.model_dump()
                    st.session_state.bd_result_version = analysis_run.result_version
                    st.session_state.bd_history_id = save_analysis(
                        seed=st.session_state.bd_seed,
                        result_version=st.session_state.bd_result_version,
                        result=st.session_state.bd_result,
                        research_trace=st.session_state.bd_v2_research_trace,
                    )
                    st.session_state.bd_stage = "result"
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    status.update(label=f"{engine} 분석 실패", state="error", expanded=True)
                    st.error(f"{engine} 분석에 실패했습니다: {exc}")
                    st.info("사이드바에서 BD v2 또는 기존 BD 엔진으로 언제든 전환할 수 있습니다.")
            else:
                try:
                    with st.spinner("기존 BD 분석을 실행 중..."):
                        analysis_run = analyze_project(
                            ProjectAnalysisInput(
                                seed=st.session_state.bd_seed,
                                engine="기존 BD",
                                guided_answers=guided,
                                uploaded_name=st.session_state.get("bd_uploaded_name"),
                                uploaded_bytes=st.session_state.get("bd_uploaded_bytes"),
                                demo_mode=demo_mode,
                            )
                        )
                        result = analysis_run.result
                    st.session_state.bd_result = result.model_dump()
                    st.session_state.bd_result_version = analysis_run.result_version
                    st.session_state.bd_history_id = save_analysis(
                        seed=st.session_state.bd_seed,
                        result_version="legacy",
                        result=st.session_state.bd_result,
                    )
                    st.session_state.bd_stage = "result"
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"기존 BD 분석에 실패했습니다: {exc}")
                    st.info("사이드바에서 데모 모드를 켜면 기존 UI와 결과 구조를 확인할 수 있습니다.")

    else:
        if st.session_state.bd_result_version == "v3":
            from src.vietnam_bd.models_v3 import BDV3AnalysisResult

            language = "ko"
            result = BDV3AnalysisResult.model_validate(st.session_state.bd_result)
            page1, page2, page3 = st.tabs([ui(language, "opportunity_tab"), ui(language, "strategy_tab"), ui(language, "meeting_tab")])
            with page1: render_page_1_opportunity_v3(result, language)
            with page2: render_page_2_strategy_v3(result, language)
            with page3: render_page_3_meeting_v3(result, language)
            if developer_mode and st.session_state.get("bd_v2_research_trace"):
                render_research_trace(st.session_state.bd_v2_research_trace)
        elif st.session_state.bd_result_version == "v2":
            from src.vietnam_bd.models import BDV2AnalysisResult

            result = BDV2AnalysisResult.model_validate(st.session_state.bd_result)
            page1, page2, page3 = st.tabs(["1. Opportunity", "2. Strategy", "3. Meeting"])
            with page1:
                render_page_1_opportunity(result)
            with page2:
                render_page_2_strategy(result)
            with page3:
                render_page_3_meeting(result)
            if developer_mode and st.session_state.get("bd_v2_research_trace"):
                render_research_trace(st.session_state.bd_v2_research_trace)
        else:
            from src.vietnam_bd.models import AnalysisResult

            result = AnalysisResult.model_validate(st.session_state.bd_result)
            render_overview(result)

            tab1, tab2, tab3, tab4, tab5 = st.tabs(["기회 해석", "DX 관점", "미팅", "내부 사례", "Next Step"])
            with tab1:
                render_qualification(result)
            with tab2:
                render_dx(result)
            with tab3:
                render_meeting(result)
            with tab4:
                render_internal(result)
            with tab5:
                render_next_steps(result)

        st.download_button(
            "분석 결과 JSON 다운로드",
            data=json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
            file_name=f"opportunity_analysis_{st.session_state.bd_result_version}.json",
            mime="application/json",
            use_container_width=True,
        )
