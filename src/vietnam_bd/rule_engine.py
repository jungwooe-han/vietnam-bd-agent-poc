from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel

from .models import ContextClassification, EvidenceItem, StageGate


UNKNOWN = "미확정"

CUSTOMER_NEED_RULES: dict[str, tuple[str, ...]] = {
    "전력 안정성 / Energy Security": ("정전", "전력 안정", "전력 품질", "비상 전원", "무정전", "ups"),
    "소방·인허가 Compliance": ("소방", "화재", "인허가", "규제", "컴플라이언스", "준법"),
    "고온다습·염해 환경 대응": ("고온", "고습", "습도", "부식", "염해"),
    "RE100 / ESG / OPEX 절감": ("re100", "esg", "탄소", "에너지 절감", "전력 절감", "opex", "운영비"),
    "Fast-Track / 조기 SOP": ("fast-track", "fast track", "패스트트랙", "조기 sop", "조기 가동", "긴급 준공"),
    "향후 확장 / 모듈형 설계": ("향후 증설", "추가 증설", "모듈러", "확장성", "단계별 증설"),
    "현지 A/S / 운영 안정성": ("현지 a/s", "로컬 a/s", "유지보수", "운영 안정", "서비스 대응"),
    "현지 인력 DX / 운영 디지털화": ("dx", "디지털 전환", "스마트 운영", "자동화", "원격 관리"),
    "현장 모바일 / 러기드 디바이스": ("러기드", "태블릿", "현장 모빌리티", "모바일 작업"),
    "CAPEX / TCO 최적화": ("capex", "tco", "초기 투자비", "총소유비용", "원가 절감"),
}

BUILDING_TYPE_RULES: dict[str, tuple[str, ...]] = {
    "신축": ("신축", "신규 공장", "새 공장", "greenfield", "착공 예정"),
    "리모델링": ("리모델링", "개보수", "renovation", "retrofit", "리트로핏"),
    "수평증축": ("수평 증축", "수평증축", "동 증설", "옆 부지 증설"),
    "수직증축": ("수직 증축", "수직증축", "층 증축", "상부 증축"),
    "스마트화": ("스마트 팩토리", "스마트공장", "스마트화", "디지털 공장"),
}

BUSINESS_STAGE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("프로젝트 종료", ("프로젝트 종료", "공사 완료", "준공 완료", "사업 종료")),
    ("운영 인허가", ("운영 인허가", "사용 승인", "가동 승인", "운영 허가")),
    ("시공", ("시공 중", "공사 중", "건설 중", "construction underway")),
    ("건설 인허가", ("건설 인허가", "건축 허가", "착공 허가", "construction permit")),
    ("설계 - CD (기본)", ("cd 설계", "construction document", "실시설계", "상세 설계")),
    ("설계 - DD (기본)", ("dd 설계", "design development", "기본설계 진행")),
    ("설계 - SD (기본)", ("sd 설계", "schematic design", "개념설계")),
    ("Master Plan", ("master plan", "마스터 플랜", "마스터플랜")),
    ("타당성 조사", ("타당성 조사", "사업성 검토", "feasibility study", "feasibility")),
    ("사업기획", ("사업기획", "투자 검토", "투자 계획", "사업 계획")),
]

BUSINESS_STRUCTURE_RULES: dict[str, tuple[str, ...]] = {
    "End Client": ("end client", "발주처", "사업주", "project owner", "최종 고객"),
    "PEF / Capital Structure": ("pef", "사모펀드", "투자자", "자본 구조", "capital structure"),
    "Lead Architect": ("lead architect", "설계사", "건축사", "architect"),
    "GC / EPC": ("gc", "epc", "종합건설", "시공사", "general contractor"),
    "Government Involvement": ("정부", "지자체", "산업단지 관리", "공공기관", "정부 승인"),
}


class RuleEngineResult(BaseModel):
    context: ContextClassification
    stage_gate: StageGate


def _matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    lowered = text.casefold()
    matches = []
    for keyword in keywords:
        normalized = keyword.casefold()
        if re.fullmatch(r"[a-z0-9][a-z0-9 .+/#-]*", normalized):
            pattern = rf"(?<![a-z0-9-]){re.escape(normalized)}(?![a-z0-9-])"
            matched = bool(re.search(pattern, lowered))
        else:
            matched = normalized in lowered
        if matched:
            matches.append(keyword)
    return matches


def _evidence(claim: str, matches: list[str], axis: str) -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        credibility="likely" if matches else "unknown",
        rationale=(
            f"명시적 {axis} 키워드 감지: {', '.join(matches)}"
            if matches
            else f"{axis}을 뒷받침하는 명시적 규칙 신호가 없습니다."
        ),
        source_labels=[f"rule:{keyword}" for keyword in matches],
    )


def _classify_many(text: str, rules: dict[str, tuple[str, ...]], axis: str) -> list[EvidenceItem]:
    results = []
    for claim, keywords in rules.items():
        matches = _matched_keywords(text, keywords)
        if matches:
            results.append(_evidence(claim, matches, axis))
    return results


def _classify_one(text: str, rules: dict[str, tuple[str, ...]], axis: str) -> EvidenceItem:
    candidates = []
    for claim, keywords in rules.items():
        matches = _matched_keywords(text, keywords)
        if matches:
            candidates.append((len(matches), claim, matches))
    if not candidates:
        return _evidence(UNKNOWN, [], axis)
    _, claim, matches = max(candidates, key=lambda item: item[0])
    return _evidence(claim, matches, axis)


def _is_future_construction_reference(text: str) -> bool:
    return bool(
        re.search(
            r"(?:내년|향후|예정|계획).{0,20}(?:착공|시공|공사|건설)|"
            r"(?:착공|시공|공사|건설).{0,20}(?:내년|향후|예정|계획)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _classify_stage(text: str) -> EvidenceItem:
    for stage, keywords in BUSINESS_STAGE_RULES:
        matches = _matched_keywords(text, keywords)
        if not matches:
            continue
        if stage == "시공" and _is_future_construction_reference(text):
            continue
        return _evidence(stage, matches, "사업 단계")
    return _evidence(UNKNOWN, [], "사업 단계")


def build_stage_gate(business_stage: EvidenceItem, target_level: str | None = None) -> StageGate:
    level = (target_level or "").strip().casefold().replace(" ", "_")
    if not level:
        if business_stage.claim in {"사업기획", "타당성 조사"}:
            level = "targeting"
        elif business_stage.claim in {"Master Plan", "설계 - SD (기본)", "설계 - DD (기본)", "설계 - CD (기본)"}:
            level = "golden_time"
        elif business_stage.claim in {"건설 인허가", "시공"}:
            level = "local_action"
        elif business_stage.claim in {"운영 인허가", "프로젝트 종료"}:
            level = "closed"
        else:
            level = "unknown"

    policies = {
        "targeting": ("targeting", "deep", "active", "none", "초기 의사결정 구조와 관계 진입 여지가 남아 있습니다.", "Owner, PM, Architect 후보와 향후 의사결정 구조"),
        "golden_time": ("golden_time", "deep", "active", "none", "사양과 조달 구조에 영향을 줄 수 있는 핵심 시기입니다.", "Architect, PM, EPC/GC, 사양 및 입찰 일정"),
        "local_action": ("local_action", "limited", "limited", "none", "광범위한 조사보다 남아 있는 패키지와 현장 기회 확인이 우선입니다.", "미발주 패키지, 변경계약, 추가 범위와 현장 요구"),
        "closed": ("closed", "limited", "stop", "limited", "현재 프로젝트의 적극 수주 활동은 중단하되 과거 사업 구조는 학습합니다.", "End Client, 설계사, EPC/GC, vendor, 투자 및 일정, 반복 파트너 패턴"),
        "unknown": ("unknown", "limited", "limited", "none", "단계를 확정할 직접 근거가 부족합니다.", "현재 단계와 일정의 직접 확인"),
    }
    status, depth, pursuit, history, window, focus = policies.get(level, policies["unknown"])
    return StageGate(
        status=status,
        research_depth=depth,
        active_pursuit=pursuit,
        historical_intelligence=history,
        rationale=f"사업 단계 '{business_stage.claim}' 기준. {business_stage.rationale}",
        remaining_window=window,
        recommended_focus=focus,
    )


def evaluate_context(text: str) -> RuleEngineResult:
    normalized = text or ""
    customer_needs = _classify_many(normalized, CUSTOMER_NEED_RULES, "고객 니즈")
    if not customer_needs:
        customer_needs = [_evidence("고객 니즈 미확정", [], "고객 니즈")]

    stage = _classify_stage(normalized)
    context = ContextClassification(
        customer_needs=customer_needs[:8],
        building_type=_classify_one(normalized, BUILDING_TYPE_RULES, "건축 유형"),
        business_stage=stage,
        business_structure=_classify_many(normalized, BUSINESS_STRUCTURE_RULES, "사업 구도")[:8],
    )
    return RuleEngineResult(context=context, stage_gate=build_stage_gate(stage))
