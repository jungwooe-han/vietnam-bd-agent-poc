from __future__ import annotations

import json
import os

import streamlit as st
from dotenv import load_dotenv

from src.analysis import analyze_opportunity
from src.demo_data import demo_result
from src.guided_questions import generate_guided_questions
from src.ingestion import build_extracted_context
from src.internal_cases import load_internal_cases
from src.ui_components import (
    inject_css,
    render_dx,
    render_internal,
    render_meeting,
    render_next_steps,
    render_overview,
    render_qualification,
)

load_dotenv()
st.set_page_config(page_title="Vietnam BD Agent", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
inject_css()

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "result" not in st.session_state:
    st.session_state.result = None
if "seed" not in st.session_state:
    st.session_state.seed = ""

st.markdown("<div class='hero'><h1>Vietnam Manufacturing BD Agent</h1><p>아는 정보나 뉴스를 넣으면, 사업기회 관점으로 확장하고 첫 미팅에서 무엇을 알아와야 할지 안내합니다.</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 설정")
    demo_mode = st.checkbox("데모 모드", value=not bool(os.getenv("OPENAI_API_KEY")))
    st.caption("데모 모드는 API 호출 없이 예시 결과를 표시합니다.")
    if st.button("새 Opportunity"):
        st.session_state.clear()
        st.rerun()

if st.session_state.stage == "input":
    seed = st.text_area(
        "니가 아는 정보를 입력해",
        value=st.session_state.seed,
        height=230,
        placeholder="뉴스 전문, URL, 고객에게 들은 내용, 프로젝트 메모를 자유롭게 붙여넣으세요.\n예: 삼성전기가 베트남에서 MLCC 관련 생산라인 투자를 검토 중이다...",
    )
    uploaded = st.file_uploader("또는 PDF/TXT 첨부", type=["pdf", "txt", "md"])
    st.caption("POC에는 실제 회사 기밀정보를 입력하지 마세요. 더미·가명 데이터만 사용합니다.")

    if st.button("사업기회 분석 시작", type="primary", use_container_width=True):
        if not seed.strip() and uploaded is None:
            st.warning("텍스트, URL 또는 파일 중 하나를 입력하세요.")
        else:
            st.session_state.seed = seed
            st.session_state.uploaded_bytes = uploaded.getvalue() if uploaded else None
            st.session_state.uploaded_name = uploaded.name if uploaded else None
            st.session_state.questions = generate_guided_questions(seed)
            st.session_state.stage = "guided"
            st.rerun()

elif st.session_state.stage == "guided":
    st.subheader("알고 있는 것만 더 알려줘")
    st.caption("모르면 비워둬도 됩니다. 입력 내용에 따라 필요한 질문만 표시됩니다.")
    answers = []
    for idx, question in enumerate(st.session_state.questions):
        answer = st.text_input(question, key=f"guided_{idx}", placeholder="모름 / 확인 필요")
        if answer.strip():
            answers.append(f"Q: {question}\nA: {answer}")

    c1, c2 = st.columns(2)
    if c1.button("이전", use_container_width=True):
        st.session_state.stage = "input"
        st.rerun()
    if c2.button("분석 실행", type="primary", use_container_width=True):
        with st.spinner("관련 맥락을 찾고 사업개발 관점으로 해석 중..."):
            uploaded_proxy = None
            if st.session_state.get("uploaded_bytes"):
                class UploadedProxy:
                    def __init__(self, name: str, data: bytes):
                        self.name = name
                        self._data = data
                    def getvalue(self) -> bytes:
                        return self._data
                uploaded_proxy = UploadedProxy(st.session_state.uploaded_name, st.session_state.uploaded_bytes)

            extracted, notes = build_extracted_context(st.session_state.seed, uploaded_proxy)
            guided = "\n\n".join(answers)
            internal = load_internal_cases()
            try:
                result = demo_result() if demo_mode else analyze_opportunity(st.session_state.seed, extracted, guided, internal)
                if notes:
                    result.source_summary.extend(notes)
                st.session_state.result = result.model_dump()
                st.session_state.stage = "result"
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"분석에 실패했습니다: {exc}")
                st.info("사이드바에서 데모 모드를 켜면 UI와 결과 구조를 바로 확인할 수 있습니다.")

else:
    from src.models import AnalysisResult
    result = AnalysisResult.model_validate(st.session_state.result)
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
        file_name="opportunity_analysis.json",
        mime="application/json",
        use_container_width=True,
    )
