from __future__ import annotations

import json
import os

import streamlit as st

from src.vietnam_bd.analysis import analyze_opportunity
from src.vietnam_bd.analysis_v2 import analyze_opportunity_v2
from src.vietnam_bd.analysis_v3 import analyze_opportunity_v3
from src.vietnam_bd.demo_data import demo_result
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.guided_questions import generate_guided_questions
from src.vietnam_bd.history import get_analysis, list_analyses, save_analysis
from src.vietnam_bd.ingestion import build_extracted_context
from src.vietnam_bd.internal_cases import load_internal_cases
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

    if st.session_state.bd_stage != "input":
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
            source_col, upload_col, action_col = st.columns([4.5, 1.5, 1.7], vertical_alignment="center")
            source_col.markdown(
                '<div class="bd-entry-modes"><span class="active">URL</span><span>Text</span></div>',
                unsafe_allow_html=True,
            )
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
                st.session_state.bd_questions = generate_guided_questions(seed)
                st.session_state.bd_stage = "guided"
                st.rerun()

    elif st.session_state.bd_stage == "guided":
        st.subheader("알고 있는 것만 더 알려줘")
        st.caption("모르면 비워둬도 됩니다. 입력 내용에 따라 필요한 질문만 표시됩니다.")
        answers = []
        for idx, question in enumerate(st.session_state.bd_questions):
            answer = st.text_input(question, key=f"bd_guided_{idx}", placeholder="모름 / 확인 필요")
            if answer.strip():
                answers.append(f"Q: {question}\nA: {answer}")

        c1, c2 = st.columns(2)
        if c1.button("이전", use_container_width=True):
            st.session_state.bd_stage = "input"
            st.rerun()
        if c2.button("분석 실행", type="primary", use_container_width=True):
            uploaded_proxy = None
            if st.session_state.get("bd_uploaded_bytes"):
                class UploadedProxy:
                    def __init__(self, name: str, data: bytes):
                        self.name = name
                        self._data = data

                    def getvalue(self) -> bytes:
                        return self._data

                uploaded_proxy = UploadedProxy(st.session_state.bd_uploaded_name, st.session_state.bd_uploaded_bytes)

            extracted, notes = build_extracted_context(st.session_state.bd_seed, uploaded_proxy)
            guided = "\n\n".join(answers)
            internal = load_internal_cases()

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
                    base_result = demo_v2_result(closed=closed_demo) if demo_mode else None
                    if engine == "BD v3":
                        from src.vietnam_bd.v3_rule_engine import build_v3_result
                        result = build_v3_result(base_result, st.session_state.bd_seed, extracted + "\n" + guided) if demo_mode else analyze_opportunity_v3(
                            st.session_state.bd_seed,
                            extracted=extracted,
                            user_context=guided,
                            progress_callback=progress,
                            trace_callback=lambda trace: st.session_state.update(bd_v2_research_trace=trace),
                        )
                    else:
                        result = base_result if demo_mode else analyze_opportunity_v2(
                            st.session_state.bd_seed,
                            extracted=extracted,
                            user_context=guided,
                            progress_callback=progress,
                            trace_callback=lambda trace: st.session_state.update(bd_v2_research_trace=trace),
                        )
                    if demo_mode:
                        status.write("Mock v2 전체 결과 생성 완료")
                        status.update(label=f"{engine} 데모 분석 완료", state="complete", expanded=False)
                    if notes:
                        result.source_summary.extend(notes)
                    st.session_state.bd_result = result.model_dump()
                    st.session_state.bd_result_version = "v3" if engine == "BD v3" else "v2"
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
                        result = (
                            demo_result()
                            if demo_mode
                            else analyze_opportunity(st.session_state.bd_seed, extracted, guided, internal)
                        )
                    if notes:
                        result.source_summary.extend(notes)
                    st.session_state.bd_result = result.model_dump()
                    st.session_state.bd_result_version = "legacy"
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
