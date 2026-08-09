from .claude_client import (
    call_claude,
    parse_json_array,
    parse_json_object,
)
from .prompts import (
    build_email_prompt,
    build_scan_prompt,
    build_timeline_prompt,
    build_verify_prompt,
)

DEFAULT_SOURCES = [
    {"domain": "vir.com.vn", "label": "Vietnam Investment Review", "checked": True},
    {"domain": "vietnam-briefing.com", "label": "Vietnam Briefing", "checked": True},
    {"domain": "fia.mpi.gov.vn", "label": "베트남 기획투자부 FDI", "checked": True},
    {"domain": "vietnamnews.vn", "label": "Vietnam News", "checked": True},
    {"domain": "e.vnexpress.net", "label": "VnExpress International", "checked": True},
    {"domain": "hanoitimes.vn", "label": "Hanoi Times", "checked": False},
    {"domain": "baodautu.vn", "label": "베트남 투자보 (Bao Dau Tu)", "checked": False},
    {"domain": "vsip.com", "label": "VSIP 산업단지", "checked": False},
]


def _normalize_lead(lead: dict) -> dict:
    # Claude Artifact의 snake_case 필드를 그대로 유지
    lead.setdefault("company", "미상 기업")
    lead.setdefault("location", "")
    lead.setdefault("industry", "")
    lead.setdefault("signal_type", "신호 미상")
    lead.setdefault("signal_date", "")
    lead.setdefault("evidence", "")
    lead.setdefault("source", "미상")
    lead.setdefault("score", 0)
    lead.setdefault("approach", {})
    lead.setdefault("timeline", [
        {
            "date": lead.get("signal_date", ""),
            "headline": lead.get("evidence", ""),
            "source": lead.get("source", ""),
        }
    ])
    return lead


def scan_leads(region, industry, time_window, keyword, mode, allowed_domains):
    if mode == "키워드 검색":
        prompt = build_scan_prompt(region, industry, time_window, keyword, False, [])
        text, _ = call_claude(prompt, max_tokens=8000, use_web_search=True)
        return [_normalize_lead(x) for x in parse_json_array(text)]

    if mode == "신뢰 소스 전체 스캔":
        prompt = build_scan_prompt(region, industry, time_window, "", True, allowed_domains)
        text, _ = call_claude(
            prompt,
            max_tokens=8000,
            use_web_search=True,
            allowed_domains=allowed_domains,
        )
        return [_normalize_lead(x) for x in parse_json_array(text)]

    # "둘 다"은 순차 실행으로 단순화.
    # 추후 병렬 실행 또는 async로 교체 가능.
    keyword_prompt = build_scan_prompt(region, industry, time_window, keyword, False, [])
    source_prompt = build_scan_prompt(region, industry, time_window, "", True, allowed_domains)

    kw_text, _ = call_claude(keyword_prompt, max_tokens=8000, use_web_search=True)
    src_text, _ = call_claude(
        source_prompt,
        max_tokens=8000,
        use_web_search=True,
        allowed_domains=allowed_domains,
    )

    merged = {}
    for lead in parse_json_array(kw_text) + parse_json_array(src_text):
        lead = _normalize_lead(lead)
        key = lead.get("company", "").strip().lower()
        if key and key not in merged:
            merged[key] = lead
    return list(merged.values())


def verify_lead(lead):
    text, _ = call_claude(
        build_verify_prompt(lead),
        max_tokens=2500,
        use_web_search=True,
    )
    return parse_json_object(text)


def update_timeline(lead):
    text, _ = call_claude(
        build_timeline_prompt(lead),
        max_tokens=2500,
        use_web_search=True,
    )
    return parse_json_array(text)


def build_bd_handoff_seed(lead: dict, note: str = "") -> str:
    approach = lead.get("approach") or {}

    def _line(label, field):
        field = field or {}
        value = field.get("value") or "확인 필요"
        basis = field.get("basis") or ""
        return f"- {label}: {value}" + (f" ({basis})" if basis else "")

    lines = [
        "[리드 센싱에서 전달된 기업 정보]",
        f"기업명: {lead.get('company', '미상 기업')}",
        f"지역: {lead.get('location', '')}",
        f"업종: {lead.get('industry', '')}",
        f"포착된 신호: {lead.get('signal_type', '')} ({lead.get('signal_date', '')})",
        f"신호 근거: {lead.get('evidence', '')}",
        f"출처: {lead.get('source', '')}",
        "",
        "접근 전략 메모:",
        _line("의사결정 구조", approach.get("decision_maker")),
        _line("접근 타이밍", approach.get("timing")),
        _line("경쟁사 동향", approach.get("competitor_status")),
    ]
    if note:
        lines += ["", f"영업 메모: {note}"]
    return "\n".join(lines)


def draft_email(lead, note=""):
    text, _ = call_claude(
        build_email_prompt(lead, note),
        max_tokens=1200,
        use_web_search=False,
    )
    return text.strip()
