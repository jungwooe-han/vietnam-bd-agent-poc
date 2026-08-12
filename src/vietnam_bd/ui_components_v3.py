from __future__ import annotations

import html

import streamlit as st

from .models_v3 import BDV3AnalysisResult, V3StakeholderTarget
from .localization_v3 import ui


def inject_v3_css() -> None:
    st.markdown(
        """
        <style>
        :root{--navy:#000;--blue:#000;--violet:#000;--ink:#000;--muted:#707070;--line:#ddd;--soft:#f7f7f7}
        html,body,[class*="css"],.stApp{font-family:"SamsungOneKorean","Apple SD Gothic Neo",Arial,sans-serif!important}
        .stApp{background:#fff;color:#000}
        [data-testid="stHeader"]{background:transparent;height:0}[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
        .block-container{max-width:1500px;padding:0 3rem 4rem!important}
        [data-testid="stSidebar"]{background:#f7f7f7;border-right:1px solid #ddd;min-width:300px;max-width:300px}
        [data-testid="stSidebar"] *{color:#000}[data-testid="stSidebar"] h3{color:#000;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:#707070;font-size:.75rem;font-weight:700}
        [data-testid="stSidebar"] button,[data-testid="stSidebar"] .stButton button{height:40px;padding:9px 24px;border:1px solid #000;background:#000;color:#fff;border-radius:20px;font-size:14px;font-weight:700;box-shadow:none}
        [data-testid="stSidebar"] .stButton button p,[data-testid="stSidebar"] .stButton button span{color:#fff!important}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton{margin:.42rem 0}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button{width:100%;height:auto;min-height:66px;padding:12px 14px;background:#fff;color:#000;border:1px solid #ddd;border-radius:16px;justify-content:flex-start;align-items:flex-start;text-align:left;box-shadow:none}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button:hover{background:#f2f2f2;color:#000;border-color:#aaa}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button p,[data-testid="stSidebar"] [data-testid="stExpander"] .stButton button span{width:100%;margin:0;color:#000!important;font-size:.76rem;font-weight:600;line-height:1.38;text-align:left;white-space:pre-line;overflow-wrap:anywhere}
        .stButton>button,.stDownloadButton>button{min-height:40px;padding:9px 24px;border:1px solid #000;background:#000;color:#fff;border-radius:20px;font-size:14px;font-weight:700;box-shadow:none}.stButton>button:hover,.stDownloadButton>button:hover{background:#222;color:#fff;border-color:#222}
        [data-testid="stExpander"]{background:#fff;border:1px solid #ddd;border-radius:20px;box-shadow:none;overflow:hidden}
        [data-testid="stTextArea"] textarea,[data-testid="stFileUploader"] section{border-color:#ddd;border-radius:20px;background:#f7f7f7;box-shadow:none}
        .hero{margin:0 -3rem!important;padding:24px 3rem!important;border-radius:0!important;background:#fff!important;border:0!important;border-bottom:1px solid #ddd!important;box-shadow:none!important;display:flex;align-items:center;justify-content:space-between}
        .hero h1{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif!important;font-size:1.35rem!important;color:#000!important;margin:0!important}.hero h1:before{content:'BD';display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;margin-right:14px;border-radius:50%;background:#000;color:#fff;font-size:.72rem;vertical-align:middle}
        .hero p{display:none!important}.hero:after{content:'OPPORTUNITY  ·  STRATEGY  ·  MEETING';color:#707070;font-size:.72rem;letter-spacing:.08em}
        [data-testid="stTabs"]{margin-top:24px}[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:32px;background:#fff;border:0;border-bottom:1px solid #ddd;padding:0;border-radius:0;box-shadow:none}
        [data-testid="stTabs"] button[role="tab"]{border-radius:0;padding:4px 0 12px;font-size:18px;font-weight:700;color:#707070;background:transparent;box-shadow:none}
        [data-testid="stTabs"] button[aria-selected="true"]{background:transparent;color:#000;box-shadow:none}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"]{display:block;background:#000;height:2px}
        .v3-head{display:flex;justify-content:space-between;gap:18px;margin:32px 0;padding:0;background:#fff;border:0;border-radius:0;box-shadow:none}.v3-head h1{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;margin:0;color:#000;letter-spacing:-.02em}.v3-head p{margin:.5rem 0 0;color:#707070;font-size:16px;line-height:1.33}
        .v3-eyebrow,.v3-label{font-size:.69rem;letter-spacing:.1em;font-weight:700;color:#707070;text-transform:uppercase}.v3-step{width:40px;height:40px;border-radius:20px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;box-shadow:none}
        .v3-gate{display:grid;grid-template-columns:150px 1fr auto;align-items:center;gap:24px;border-radius:20px;padding:28px 32px;color:#000;margin-bottom:24px;box-shadow:none;min-height:104px;border:1px solid #ddd}.v3-gate.now{background:#edf8f1}.v3-gate.monitor{background:#fff7df}.v3-gate.closed{background:#fff0ef}.v3-gate-status{font-size:1.75rem;font-weight:700}.v3-gate-copy{font-size:16px;line-height:1.45;color:#333}
        .v3-section{display:flex;justify-content:space-between;align-items:center;margin:24px 0 10px}.v3-section h3{font-size:.92rem;margin:0;color:#1d2945}.v3-section span{color:#7b849a}
        .v3-card{border:0;background:#f7f7f7;border-radius:20px;padding:32px;box-shadow:none;height:100%;min-height:148px}.v3-card:hover{border:0;box-shadow:none}.v3-value{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;color:#000;margin:12px 0 18px}
        .v3-chip{display:inline-flex;padding:6px 12px;border-radius:40px;font-size:.7rem;font-weight:700;background:#eee;color:#000}.v3-chip.strong,.v3-chip.confirmed{background:#e5f5eb;color:#087a42}.v3-chip.medium,.v3-chip.inferred,.v3-chip.likely{background:#fff1c8;color:#805500}.v3-chip.weak,.v3-chip.unknown,.v3-chip.hypothesis{background:#e8e8e8;color:#707070}
        .v3-ai{border:0;background:#f7f7f7;border-radius:20px;padding:32px;margin:8px 0 28px;box-shadow:none}.v3-ai-title{font-size:.72rem;letter-spacing:.1em;font-weight:700;color:#707070;margin-bottom:12px}.v3-ai-copy{color:#000;font-size:16px;line-height:1.5}
        .v3-tier{display:inline-flex;padding:6px 14px;border-radius:40px;background:#000;color:#fff;font-size:.7rem;font-weight:700;margin:4px 0 12px}.v3-role{color:#707070;font-size:.76rem;font-weight:700}.v3-company{font-size:18px;font-weight:700;color:#000;margin:8px 0 16px}.v3-meta{display:grid;grid-template-columns:92px 1fr;gap:9px 12px;font-size:.8rem}.v3-meta b{color:#707070}.v3-meta span{color:#000}
        .v3-question{display:grid;grid-template-columns:36px 1fr;gap:16px;border:0;border-radius:20px;padding:20px;background:#f7f7f7;margin-bottom:12px}.v3-number{width:32px;height:32px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.75rem}.v3-question-title{font-size:15px;font-weight:700;color:#000}.v3-question-sub{font-size:.75rem;color:#707070;margin-top:7px}
        .v3-talk{border:0;background:#f7f7f7;border-radius:20px;padding:20px;margin-bottom:12px}.v3-talk b{color:#000;font-size:.8rem}.v3-talk p,.v3-product-copy{font-size:14px;color:#404040;line-height:1.5;margin-top:10px}.v3-signals{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 20px}.v3-signal{padding:7px 14px;border-radius:40px;background:#f1f1f1;color:#000;font-size:.75rem;font-weight:700}
        .v3-product{border:0;background:#f7f7f7;border-radius:20px;padding:32px;height:100%;box-shadow:none}.v3-rank{font-size:.7rem;font-weight:700;color:#707070}.v3-product-name{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;color:#000;margin:8px 0 14px}
        .v3-map-shell{background:#f7f7f7;border:0;border-radius:20px;padding:24px 32px 12px;box-shadow:none}
        .v3-map-legend{display:flex;justify-content:flex-end;gap:14px;color:#7b8497;font-size:11px;padding:2px 4px 4px}.v3-map-legend i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
        @media(max-width:760px){.v3-head{flex-direction:column}.v3-gate{grid-template-columns:1fr}.v3-meta{grid-template-columns:1fr}.block-container{padding-left:1rem;padding-right:1rem}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe(value: object) -> str:
    return html.escape(str(value or "Not confirmed"))


def _badge(value: str, language: str = "ko") -> str:
    state = _safe(value).lower()
    label = ui(language, state) if state in {"confirmed", "inferred", "unknown"} else state.upper()
    return f"<span class='v3-chip {state}'>{_safe(label).upper()}</span>"


def _header(step: int, eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='v3-head'><div><div class='v3-eyebrow'>{_safe(eyebrow)}</div><h1>{_safe(title)}</h1><p>{_safe(subtitle)}</p></div><div class='v3-step'>{step}</div></div>", unsafe_allow_html=True)


def _section(title: str, meta: str = "") -> None:
    st.markdown(f"<div class='v3-section'><h3>{_safe(title)}</h3><span class='v3-label'>{_safe(meta)}</span></div>", unsafe_allow_html=True)


def _relationship_map(result: BDV3AnalysisResult, language: str) -> None:
    relmap = result.relationship_map
    _section(ui(language, "relationship_map"), f"{relmap.structure_id or 'UNKNOWN'} / Excel Rule Engine")
    if not relmap.nodes:
        st.info("Not enough direct evidence to classify the project structure as S1-S4. No company has been fabricated.")
        return
    width, node_w, node_h = 960, 222, 82
    max_layer = max(node.layer for node in relmap.nodes)
    height = max(400, 112 + max_layer * 128)
    x_positions = {"LEFT": 145, "CENTER": 480, "RIGHT": 815}
    coords: dict[str, tuple[int, int]] = {}
    for node in relmap.nodes:
        coords[node.node_id] = (x_positions.get(node.position.upper(), 480), 50 + (node.layer - 1) * 128)
    svg = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Project relationship map">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#707070"/></marker></defs>']
    for edge in relmap.relations:
        if edge.from_node not in coords or edge.to_node not in coords:
            continue
        x1, y1 = coords[edge.from_node]; x2, y2 = coords[edge.to_node]
        start_y, end_y = y1 + node_h, y2
        if abs(y2 - y1) < 20:
            x1 = x1 + node_w / 2 if x1 < x2 else x1 - node_w / 2
            x2 = x2 - node_w / 2 if x1 < x2 else x2 + node_w / 2
            start_y = end_y = y1 + node_h / 2
        dash = ' stroke-dasharray="7 6"' if edge.line_type == "DASHED" else ""
        arrows = ' marker-end="url(#arrow)"' if edge.direction != "NONE" else ""
        if edge.direction == "BOTH": arrows += ' marker-start="url(#arrow)"'
        mid_x, mid_y = (x1 + x2) / 2, (start_y + end_y) / 2
        svg.append(f'<path d="M{x1},{start_y} C{x1},{mid_y} {x2},{mid_y} {x2},{end_y}" fill="none" stroke="#7890bd" stroke-width="1.7"{dash}{arrows}/>')
        svg.append(f'<rect x="{mid_x-58}" y="{mid_y-10}" width="116" height="20" rx="10" fill="#f7f9fd"/><text x="{mid_x}" y="{mid_y+4}" text-anchor="middle" font-size="10" font-weight="600" fill="#66748f">{_safe(edge.label)}</text>')
    palette = {"confirmed": ("#eef5ff", "#3566d6", "#d7e4ff"), "inferred": ("#fff8e8", "#a66b00", "#f0dfb4"), "likely": ("#fff8e8", "#a66b00", "#f0dfb4"), "unknown": ("#f6f7f9", "#7a8495", "#e0e4e9")}
    for node in relmap.nodes:
        x, y = coords[node.node_id]; left = x - node_w / 2
        bg, accent, border = palette.get(node.status, palette["unknown"])
        role, company = _safe(node.role), _safe(node.company or "Not confirmed")
        svg.append(f'<g><rect x="{left}" y="{y}" width="{node_w}" height="{node_h}" rx="20" fill="#fff" stroke="{border}"/><rect x="{left}" y="{y}" width="5" height="{node_h}" rx="3" fill="{accent}"/><circle cx="{left+27}" cy="{y+27}" r="15" fill="{bg}"/><text x="{left+27}" y="{y+31}" text-anchor="middle" font-size="10" font-weight="700" fill="{accent}">{role[:2].upper()}</text><text x="{left+51}" y="{y+24}" font-size="11" font-weight="700" fill="#707070">{role}</text><text x="{left+51}" y="{y+46}" font-size="14" font-weight="700" fill="#000">{company[:24]}</text><rect x="{left+51}" y="{y+56}" width="74" height="17" rx="8.5" fill="{bg}"/><text x="{left+88}" y="{y+68}" text-anchor="middle" font-size="9" font-weight="700" fill="{accent}">{node.status.upper()}</text></g>')
    svg.append("</svg>")
    legend = f"<div class='v3-map-legend'><span><i style='background:#3566d6'></i>{ui(language, 'confirmed')}</span><span><i style='background:#d99a27'></i>{ui(language, 'inferred')}</span><span><i style='background:#a5adba'></i>{ui(language, 'unknown')}</span></div>"
    st.markdown("<div class='v3-map-shell'>" + legend + "".join(svg) + "</div>", unsafe_allow_html=True)
    st.caption(f"{relmap.structure_name} / {_safe(relmap.status).upper()}")
    with st.expander(ui(language, "relationship_evidence")):
        for node in relmap.nodes:
            st.markdown(f"- **{node.role} / {node.company or 'Not confirmed'}** / `{node.status}`")
        for edge in relmap.relations:
            st.markdown(f"- `{edge.from_node} -> {edge.to_node}` / {edge.label} / `{edge.status}`")


def render_page_1_opportunity_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(1, ui(language, "opportunity_eyebrow"), ui(language, "opportunity_title"), result.opportunity_title)
    state = _safe(result.status).lower()
    st.markdown(f"<div class='v3-gate {state}'><div class='v3-gate-status'>{state.upper()}</div><div class='v3-gate-copy'>{_safe(result.status_reason)}</div><div>{'STOP' if state == 'closed' else 'ACTIVE'}</div></div>", unsafe_allow_html=True)
    _section(ui(language, "key_facts"), ui(language, "evidence_aware"))
    facts = [(ui(language, "building_type"), result.building_type.value, result.building_type.status), (ui(language, "project_stage"), result.project_stage.value, result.project_stage.status), (ui(language, "project_structure"), result.relationship_map.structure_name, result.relationship_map.status)]
    for col, (label, value, status) in zip(st.columns(3), facts):
        with col:
            st.markdown(f"<div class='v3-card'><div class='v3-label'>{_safe(label)}</div><div class='v3-value'>{_safe(value)}</div>{_badge(status, language)}</div>", unsafe_allow_html=True)
    _relationship_map(result, language)
    if result.customer_needs:
        _section(ui(language, "need_signals"))
        st.markdown("<div class='v3-signals'>" + "".join(f"<span class='v3-signal'>{_safe(item.value)}</span>" for item in result.customer_needs[:5]) + "</div>", unsafe_allow_html=True)


def _target_card(target: V3StakeholderTarget, language: str) -> None:
    functions = " / ".join(target.target_function) or "Not confirmed"
    st.markdown(f"<div class='v3-card'><div class='v3-role'>{_safe(target.role)}</div><div class='v3-company'>{_safe(target.company)}</div><div class='v3-meta'><b>{ui(language, 'target_function')}</b><span>{_safe(functions)}</span><b>{ui(language, 'person')}</b><span>{_safe(target.person)}</span><b>{ui(language, 'evidence')}</b><span>{_badge(target.evidence_strength, language)}</span></div></div>", unsafe_allow_html=True)
    with st.expander(ui(language, "why_priority")):
        st.write(target.reason)
        if target.evidence:
            st.caption("Evidence: " + " / ".join(target.evidence))


def render_page_2_strategy_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(2, ui(language, "strategy_eyebrow"), ui(language, "strategy_title"), ui(language, "strategy_subtitle"))
    if result.status == "closed":
        st.error("WHO TO MEET: N/A / Project is classified as CLOSED.")
        return
    roles = ", ".join(item.role for item in result.priority_1) or "No P1 stakeholder confirmed"
    summary = "권한, 미확정 범위, 다음 사양 결정 시점을 먼저 확인한 뒤 제품 제안을 준비하십시오." if language == "ko" else "Validate authority, open scope, and the next specification decision before preparing a product proposal."
    st.markdown(f"<div class='v3-ai'><div class='v3-ai-title'>{ui(language, 'ai_strategy').upper()}</div><div class='v3-ai-copy'>{ui(language, 'meet_first')}: <b>{_safe(roles)}</b>. {summary}</div></div>", unsafe_allow_html=True)
    for priority, targets in ((1, result.priority_1), (2, result.priority_2)):
        st.markdown(f"<div class='v3-tier'>PRIORITY {priority}</div>", unsafe_allow_html=True)
        if not targets:
            st.info("No target in this tier is supported by the available evidence.")
            continue
        for col, target in zip(st.columns(min(3, len(targets))), targets):
            with col:
                _target_card(target, language)
        st.write("")
    if result.stakeholder_unknowns:
        with st.expander(f"Not confirmed / {len(result.stakeholder_unknowns)}"):
            for item in result.stakeholder_unknowns:
                st.markdown(f"- {item}")


def render_page_3_meeting_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(3, ui(language, "meeting_eyebrow"), ui(language, "meeting_title"), ui(language, "meeting_subtitle"))
    if result.status == "closed":
        st.error("CLOSED / Follow-up questions, talking points, and product recommendations are limited.")
        return
    prep = "실제 의사결정권, 미확정 사양, EPC 영향력, Vendor 기준과 다음 구매 결정 시점에 집중하십시오." if language == "ko" else "Focus on decision authority, open specification scope, EPC influence, vendor criteria, and the timing of the next buying decision."
    st.markdown(f"<div class='v3-ai'><div class='v3-ai-title'>{ui(language, 'ai_meeting').upper()}</div><div class='v3-ai-copy'>{prep}</div></div>", unsafe_allow_html=True)
    left, right = st.columns([1.12, .88])
    with left:
        _section(ui(language, "questions"), ui(language, "prioritized"))
        for index, item in enumerate(result.questions_to_ask, 1):
            st.markdown(f"<div class='v3-question'><div class='v3-number'>{index}</div><div><div class='v3-question-title'>{_safe(item.question)}</div><div class='v3-question-sub'>{_safe(item.information_goal)} / {item.converts.upper()} TO FACT</div></div></div>", unsafe_allow_html=True)
    with right:
        _section(ui(language, "talking_points"), ui(language, "short_scenarios"))
        for item in result.talking_points:
            st.markdown(f"<div class='v3-talk'><b>{_safe(item.product)}</b><p>{_safe(item.scenario)}</p></div>", unsafe_allow_html=True)
    _section(ui(language, "top_signals"))
    if result.customer_need_top_signals:
        st.markdown("<div class='v3-signals'>" + "".join(f"<span class='v3-signal'>{_safe(item.value)}</span>" for item in result.customer_need_top_signals) + "</div>", unsafe_allow_html=True)
    else:
        st.info("No confirmed customer-need signal is available yet.")
    _section(ui(language, "products"), "Excel 70 / AI Context 30")
    for col, product in zip(st.columns(3), result.product_top3):
        with col:
            st.markdown(f"<div class='v3-product'><div class='v3-rank'>TOP {product.rank}</div><div class='v3-product-name'>{_safe(product.product)}</div>{_badge(product.evidence_strength, language)}<div class='v3-product-copy'><b>{ui(language, 'why')}</b><br>{_safe(product.why)}<br><br><b>{ui(language, 'customer_need')}</b><br>{_safe(product.customer_need)}<br><br><b>{ui(language, 'scenario')}</b><br>{_safe(product.suggested_scenario)}</div></div>", unsafe_allow_html=True)
            with st.expander(ui(language, "decision_trace")):
                st.write(f"Excel Match Count: {product.excel_match_count}")
                for rule in product.matched_rules:
                    st.caption(rule)
                if product.context_evidence:
                    st.caption("AI Context: " + " / ".join(product.context_evidence))
    with st.expander(ui(language, "overall_trace")):
        st.markdown("**Excel 70**  \n" + result.decision_trace_excel)
        st.markdown("**AI Context 30**  \n" + result.decision_trace_ai)
