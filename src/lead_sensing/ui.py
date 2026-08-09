import html

import streamlit as st

from src.common import confidence


def inject_css():
    st.markdown(
        """
        <style>
        :root{
          --bg:#141B24;
          --panel:#1C2531;
          --panel-2:#232D3B;
          --line:#2C3847;
          --amber:#E8A33D;
          --teal:#4FA8A0;
          --coral:#E2574C;
          --text:#EDEFF2;
          --muted:#8CA0B3;
        }
        .stApp {
          background:
            radial-gradient(circle at 15% 0%, rgba(232,163,61,0.06), transparent 40%),
            radial-gradient(circle at 85% 100%, rgba(79,168,160,0.06), transparent 40%),
            var(--bg);
          color:var(--text);
        }
        .block-container { max-width: 920px; padding-top: 24px; }
        .eyebrow {
          font-family: monospace;
          font-size: 11px;
          letter-spacing: .14em;
          color: var(--amber);
          text-transform: uppercase;
          display:flex; align-items:center; gap:8px;
        }
        .dot { width:6px;height:6px;border-radius:50%;background:var(--amber);display:inline-block; }
        h1 { margin-top:6px!important; margin-bottom:4px!important; }
        .sub { color:var(--muted); font-size:13.5px; line-height:1.5; margin-bottom:18px; }
        .legend { font-size:11.5px; color:var(--muted); margin:12px 0; line-height:2; }
        .conf-badge {
          font-family:monospace;font-size:9.5px;padding:1px 6px;border-radius:4px;border:1px solid;
        }
        .confirmed{border-color:var(--teal);color:var(--teal);}
        .estimated{border-color:var(--amber);color:var(--amber);}
        .unknown{border-color:var(--muted);color:var(--muted);}
        .crossverified{border-color:#6FE3A0;color:#6FE3A0;}
        .conflict{border-color:var(--coral);color:var(--coral);}
        .lead-title { font-size: 17px; font-weight: 700; }
        .lead-meta { color:var(--muted); font-family:monospace; font-size:11.5px; }
        .tag {
          display:inline-block;font-family:monospace;font-size:10.5px;
          padding:2px 7px;border-radius:5px;background:var(--panel-2);
          color:var(--muted);border:1px solid var(--line);margin:6px 6px 0 0;
        }
        .evidence { font-size:13.5px; line-height:1.55; margin-top:10px; }
        .source { color:var(--muted); font-size:11.5px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _approach_line(label, field):
    field = field or {}
    value = field.get("value", "확인 필요")
    conf = field.get("confidence", "정보없음")
    basis = field.get("basis", "")
    cls = confidence.css_class(conf)
    out = (
        f"<b>{html.escape(label)}</b> "
        f"<span class='conf-badge {cls}'>{html.escape(conf)}</span><br>"
        f"{html.escape(str(value))}"
    )
    if basis:
        out += f"<br><span class='source'><i>{html.escape(str(basis))}</i></span>"
    return out


def render_lead_card(lead, bookmarked, note, is_new):
    company = lead.get("company", "미상 기업")
    key = company.strip().lower()
    approach = lead.get("approach") or {}

    event = {
        "bookmark_changed": False,
        "note": None,
        "status": None,
        "verify": False,
        "timeline_update": False,
        "draft_email": False,
        "handoff_bd": False,
    }

    with st.container(border=True):
        title_col, score_col = st.columns([5, 1])
        with title_col:
            new_badge = " · NEW" if is_new else ""
            st.markdown(
                f"<div class='lead-title'>{html.escape(company)}{new_badge}</div>"
                f"<div class='lead-meta'>{html.escape(str(lead.get('location','')))} · "
                f"{html.escape(str(lead.get('industry','')))}</div>",
                unsafe_allow_html=True,
            )
        with score_col:
            st.metric("Score", lead.get("score", "-"))

        st.markdown(
            f"<span class='tag'>{html.escape(str(lead.get('signal_type','신호 미상')))}</span>"
            f"<span class='tag'>{html.escape(str(lead.get('signal_date','')))}</span>"
            f"<div class='evidence'>{html.escape(str(lead.get('evidence','')))}</div>"
            f"<div class='source'>출처: {html.escape(str(lead.get('source','미상')))}</div>",
            unsafe_allow_html=True,
        )

        with st.expander("접근 전략 / 근거"):
            st.markdown(
                _approach_line("의사결정 구조", approach.get("decision_maker")),
                unsafe_allow_html=True,
            )
            st.markdown(
                _approach_line("접근 타이밍", approach.get("timing")),
                unsafe_allow_html=True,
            )
            st.markdown(
                _approach_line("경쟁사 동향", approach.get("competitor_status")),
                unsafe_allow_html=True,
            )

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("★ 즐겨찾기 해제" if bookmarked else "☆ 즐겨찾기", key=f"bm_{key}"):
                event["bookmark_changed"] = True
        with b2:
            if st.button("🔍 이중 검증", key=f"verify_{key}"):
                event["verify"] = True
        with b3:
            if st.button("✉️ 메일 초안", key=f"mail_{key}"):
                event["draft_email"] = True
        with b4:
            if st.button("🧭 BD Agent로 넘기기", key=f"bd_handoff_{key}"):
                event["handoff_bd"] = True

        status = st.selectbox(
            "상태",
            ["컨택전", "컨택함", "성사", "보류"],
            key=f"status_{key}",
        )
        event["status"] = status

        new_note = st.text_area(
            "내 메모",
            value=note,
            placeholder="예: 지난주 통화함, 반응 괜찮았음",
            key=f"note_{key}",
        )
        event["note"] = new_note

        if bookmarked:
            with st.expander("타임라인", expanded=False):
                for item in sorted(
                    lead.get("timeline", []),
                    key=lambda x: x.get("date", ""),
                    reverse=True,
                ):
                    st.markdown(
                        f"**{item.get('date','날짜 미상')}** · {item.get('headline','')}"
                        f"<br><span class='source'>출처: {item.get('source','')}</span>",
                        unsafe_allow_html=True,
                    )
                if st.button("타임라인 업데이트", key=f"tl_{key}"):
                    event["timeline_update"] = True

        if lead.get("email_draft"):
            st.text_area(
                "첫 컨택 메일 초안",
                value=lead["email_draft"],
                height=220,
                key=f"email_text_{key}",
            )

    return event
