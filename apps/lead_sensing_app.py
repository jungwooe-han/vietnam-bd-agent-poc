import streamlit as st

from src.lead_sensing.lead_sensing import (
    DEFAULT_SOURCES,
    build_bd_handoff_seed,
    draft_email,
    scan_leads,
    update_timeline,
    verify_lead,
)
from src.lead_sensing.storage import init_state, merge_pipeline
from src.lead_sensing.ui import inject_css, render_lead_card


def render():
    inject_css()
    init_state()

    st.markdown(
        """
        <div class="eyebrow"><span class="dot"></span>SIGNAL SENSING · VIETNAM MANUFACTURING</div>
        <h1>베트남 제조업 리드 센싱 콘솔</h1>
        <div class="sub">
          투자 승인·산업단지·채용 신호를 스캔해 경쟁사보다 먼저 유망 리드를 찾고,
          공략 우선순위와 접근 방식을 제안합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### 스캔 범위")
        c1, c2 = st.columns(2)
        with c1:
            region = st.selectbox(
                "지역",
                [
                    "전체",
                    "박닌(Bac Ninh)",
                    "타이응우옌(Thai Nguyen)",
                    "하이퐁(Hai Phong)",
                    "빈증(Binh Duong)",
                    "동나이(Dong Nai)",
                    "호치민(Ho Chi Minh)",
                    "하노이(Hanoi)",
                ],
            )
            keyword = st.text_input("키워드 (선택)", placeholder="예: 신규 공장, 라인 증설, RFP")
        with c2:
            industry = st.selectbox(
                "업종 포커스",
                [
                    "전자/전자부품 제조",
                    "반도체/디스플레이 관련 제조",
                    "가전/생활가전 제조",
                    "자동차부품 제조",
                    "일반 제조업 전반",
                ],
            )
            time_window = st.selectbox(
                "기간",
                ["최근 1개월", "최근 3개월", "최근 6개월"],
                index=1,
            )

    with st.container(border=True):
        st.markdown("### 스캔 방식")
        mode = st.radio(
            "방식",
            ["키워드 검색", "신뢰 소스 전체 스캔", "둘 다 (병합)"],
            horizontal=True,
            label_visibility="collapsed",
        )

        domain_list = []
        if mode != "키워드 검색":
            st.caption("체크한 사이트만 훑어서, 조건에 맞는 신호가 있으면 키워드 없이도 골라냅니다.")
            source_cols = st.columns(2)
            for idx, src in enumerate(st.session_state.sources):
                with source_cols[idx % 2]:
                    checked = st.checkbox(
                        f"{src['label']} ({src['domain']})",
                        value=src.get("checked", True),
                        key=f"src_{idx}",
                    )
                    st.session_state.sources[idx]["checked"] = checked
            domain_list = [s["domain"] for s in st.session_state.sources if s.get("checked")]

            with st.expander("신뢰 소스 추가"):
                new_source = st.text_input("도메인", placeholder="예: baodautu.vn", key="new_source")
                if st.button("소스 추가"):
                    domain = new_source.strip().replace("https://", "").replace("http://", "").rstrip("/")
                    if domain and domain not in [s["domain"] for s in st.session_state.sources]:
                        st.session_state.sources.append({"domain": domain, "label": domain, "checked": True})
                        st.rerun()

    scan_clicked = st.button("스캔 시작", type="primary", use_container_width=True)

    if scan_clicked:
        if mode != "키워드 검색" and not domain_list:
            st.error("신뢰 소스 스캔을 쓰려면 최소 1개 이상의 소스를 체크해주세요.")
        else:
            with st.spinner("리드 스캔 중입니다. 검색 범위에 따라 시간이 걸릴 수 있습니다."):
                try:
                    incoming = scan_leads(
                        region=region,
                        industry=industry,
                        time_window=time_window,
                        keyword=keyword,
                        mode=mode,
                        allowed_domains=domain_list,
                    )
                    merged, new_keys = merge_pipeline(st.session_state.leads, incoming)
                    st.session_state.leads = merged
                    st.session_state.last_new_keys = new_keys
                    st.success(
                        f"스캔 완료 · 이번에 신규 {len(new_keys)}건 · 전체 파이프라인 {len(merged)}건"
                    )
                except Exception as e:
                    st.error(f"스캔 중 오류가 발생했습니다: {e}")

    st.markdown(
        """
        <div class="legend">
          <span class="conf-badge confirmed">확인됨</span> 검색에서 직접 근거를 찾은 사실
          &nbsp;&nbsp;<span class="conf-badge estimated">추정</span> 정황상 추론
          &nbsp;&nbsp;<span class="conf-badge unknown">정보없음</span> 직접 확인 필요
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.leads:
        st.info("아직 스캔 결과가 없습니다. 위 조건을 설정하고 스캔을 시작하세요.")
    else:
        h1, h2, h3 = st.columns([2, 1, 1])
        with h1:
            st.caption(f"파이프라인 {len(st.session_state.leads)}건")
        with h2:
            bookmarked_only = st.checkbox("★ 즐겨찾기만", value=False)
        with h3:
            if st.button("파이프라인 초기화"):
                st.session_state.leads = []
                st.session_state.bookmarks = set()
                st.session_state.notes = {}
                st.rerun()

        leads = sorted(st.session_state.leads, key=lambda x: x.get("score", 0), reverse=True)
        if bookmarked_only:
            leads = [
                x for x in leads
                if x.get("company", "").strip().lower() in st.session_state.bookmarks
            ]

        for lead in leads:
            key = lead.get("company", "unknown").strip().lower()

            event = render_lead_card(
                lead=lead,
                bookmarked=key in st.session_state.bookmarks,
                note=st.session_state.notes.get(key, ""),
                is_new=key in st.session_state.last_new_keys,
            )

            if event["bookmark_changed"]:
                if key in st.session_state.bookmarks:
                    st.session_state.bookmarks.remove(key)
                else:
                    st.session_state.bookmarks.add(key)
                st.rerun()

            if event["note"] is not None:
                st.session_state.notes[key] = event["note"]

            if event["status"]:
                st.session_state.status_map[key] = event["status"]

            if event["verify"]:
                with st.spinner(f"{lead.get('company')} 이중 검증 중..."):
                    verified = verify_lead(lead)
                    lead["approach"] = verified
                    st.rerun()

            if event["timeline_update"]:
                with st.spinner(f"{lead.get('company')} 타임라인 업데이트 중..."):
                    new_items = update_timeline(lead)
                    if new_items:
                        lead.setdefault("timeline", []).extend(new_items)
                    st.rerun()

            if event["draft_email"]:
                with st.spinner(f"{lead.get('company')} 첫 컨택 메일 작성 중..."):
                    lead["email_draft"] = draft_email(
                        lead,
                        note=st.session_state.notes.get(key, ""),
                    )
                    st.rerun()

            if event["handoff_bd"]:
                st.session_state.bd_seed = build_bd_handoff_seed(
                    lead, note=st.session_state.notes.get(key, "")
                )
                st.session_state.bd_stage = "input"
                for k in ("bd_result", "bd_questions", "bd_uploaded_bytes", "bd_uploaded_name"):
                    st.session_state.pop(k, None)
                st.session_state.bd_handoff_company = lead.get("company", "")
                st.session_state["_nav_to_bd"] = True
