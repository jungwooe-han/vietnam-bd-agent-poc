from __future__ import annotations

import json
import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from .models import (
    ContextClassification,
    EvidenceItem,
    StageGate,
)
from .research_models import QuickResearchResult
from .rule_engine import (
    RuleEngineResult,
    build_stage_gate,
)


Credibility = Literal[
    "confirmed",
    "likely",
    "hypothesis",
    "unknown",
]


# =========================================================
# 1. AI Context Interpretation Model
# =========================================================

class AIContextItem(BaseModel):
    value: str
    credibility: Credibility
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class AIContextInterpretation(BaseModel):

    customer_needs: list[AIContextItem] = Field(
        default_factory=list,
        max_length=8,
    )

    building_type: AIContextItem

    business_stage: AIContextItem

    business_structure: list[AIContextItem] = Field(
        default_factory=list,
        max_length=8,
    )


# =========================================================
# 2. 허용 분류체계
# md.xlsx 기준
# =========================================================

ALLOWED_BUILDING_TYPES = [
    "신축",
    "리모델링",
    "수평증축",
    "수직증축",
    "스마트화",
    "미확정",
]


ALLOWED_BUSINESS_STAGES = [
    "사업기획",
    "타당성 조사",
    "Master Plan",
    "설계 - SD (기본)",
    "설계 - DD (기본)",
    "설계 - CD (기본)",
    "건설 인허가",
    "시공",
    "운영 인허가",
    "프로젝트 종료",
    "미확정",
]


ALLOWED_CUSTOMER_NEEDS = [
    "전력 안정성 / Energy Security",
    "소방·인허가 Compliance",
    "고온다습·염해 환경 대응",
    "RE100 / ESG / OPEX 절감",
    "Fast-Track / 조기 SOP",
    "향후 확장 / 모듈형 설계",
    "현지 A/S / 운영 안정성",
    "현지 인력 DX / 운영 디지털화",
    "현장 모바일 / 러기드 디바이스",
    "CAPEX / TCO 최적화",
]


ALLOWED_STRUCTURE = [
    "End Client",
    "PEF / Capital Structure",
    "Lead Architect",
    "GC / EPC",
    "Government Involvement",
]


# =========================================================
# 3. OpenAI
# =========================================================

def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다."
        )

    return OpenAI(api_key=api_key)


def _get_model() -> str:
    return os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini",
    )


# =========================================================
# 4. AI Context Interpretation
# =========================================================

SYSTEM_PROMPT = """
You are a B2B manufacturing project context classifier.

You are NOT allowed to invent a new classification system.

You must map evidence ONLY into the categories supplied by the user.

Important principles:

1. Understand meaning, not just keywords.

Example:
"structural works are progressing"
can indicate construction even if the word
"construction" is absent.

2. TIME matters.

Example:
"construction will begin next year"
does NOT mean the current stage is construction.

3. Prefer the most CURRENT project status.

Historical milestones must not override
newer evidence.

4. Separate evidence quality:

confirmed
= the project status or fact is explicitly supported

likely
= strong contextual evidence supports it

hypothesis
= plausible interpretation requiring validation

unknown
= insufficient evidence

5. Never invent EPC, architect, owner,
vendor, project phase or customer needs.

Return JSON only.
"""


def interpret_context_with_ai(
    quick: QuickResearchResult,
) -> AIContextInterpretation:

    client = _get_client()

    prompt = f"""
Below is QUICK RESEARCH collected for a manufacturing opportunity.

QUICK RESEARCH:

{quick.model_dump_json(indent=2)}

Classify the project using ONLY these categories.

CUSTOMER NEEDS:
{json.dumps(ALLOWED_CUSTOMER_NEEDS, ensure_ascii=False)}

BUILDING TYPE:
{json.dumps(ALLOWED_BUILDING_TYPES, ensure_ascii=False)}

BUSINESS STAGE:
{json.dumps(ALLOWED_BUSINESS_STAGES, ensure_ascii=False)}

BUSINESS STRUCTURE:
{json.dumps(ALLOWED_STRUCTURE, ensure_ascii=False)}

For each classification:

- cite the evidence used
- explain why
- consider chronology
- do not infer beyond available evidence

If insufficient:
use "미확정" or credibility="unknown".
"""

    response = client.responses.create(
        model=_get_model(),
        instructions=SYSTEM_PROMPT,
        input=(
            prompt
            + "\n\nRETURN JSON MATCHING THIS SCHEMA:\n"
            + json.dumps(
                AIContextInterpretation.model_json_schema(),
                ensure_ascii=False,
            )
        ),
    )

    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return AIContextInterpretation.model_validate_json(raw)
    except ValidationError as first_error:
        schema = json.dumps(AIContextInterpretation.model_json_schema(), ensure_ascii=False)
        try:
            repair = client.responses.create(
                model=_get_model(),
                instructions=(
                    "Repair the supplied malformed JSON to exactly match the schema. "
                    "Return valid JSON only. Preserve supported facts and add no new facts."
                ),
                input=f"SCHEMA:\n{schema}\n\nMALFORMED CONTENT:\n{raw}\n\nVALIDATION ERROR:\n{first_error}",
            )
            repaired = repair.output_text.strip()
            if repaired.startswith("```"):
                repaired = repaired.replace("```json", "").replace("```", "").strip()
            return AIContextInterpretation.model_validate_json(repaired)
        except Exception:  # noqa: BLE001 - preserve deterministic fallback on any repair failure
            # AI formatting failure must not abort the deterministic Rule Engine path.
            unknown = AIContextItem(
                value="미확정",
                credibility="unknown",
                rationale="AI context JSON could not be validated; Rule Engine evidence retained.",
                evidence=[],
            )
            return AIContextInterpretation(
                customer_needs=[],
                building_type=unknown,
                business_stage=unknown.model_copy(deep=True),
                business_structure=[],
            )


# =========================================================
# 5. Evidence 변환 Helper
# =========================================================

def _to_evidence(
    item: AIContextItem,
) -> EvidenceItem:

    return EvidenceItem(
        claim=item.value,
        credibility=item.credibility,
        rationale=item.rationale,
        source_labels=item.evidence,
    )


# =========================================================
# 6. 사업단계 Arbitration
#
# Rule과 AI가 충돌했을 때
# 무조건 한쪽이 이기는 구조가 아니다.
# =========================================================

STAGE_ORDER = {
    "사업기획": 1,
    "타당성 조사": 2,
    "Master Plan": 3,
    "설계 - SD (기본)": 4,
    "설계 - DD (기본)": 5,
    "설계 - CD (기본)": 6,
    "건설 인허가": 7,
    "시공": 8,
    "운영 인허가": 9,
    "프로젝트 종료": 10,
    "미확정": 0,
}


def resolve_business_stage(
    rule_stage: EvidenceItem,
    ai_stage: AIContextItem,
) -> EvidenceItem:

    rule_value = rule_stage.claim
    ai_value = ai_stage.value

    # -----------------------------------------------------
    # 1. 동일 판정
    # -----------------------------------------------------

    if rule_value == ai_value:

        credibility: Credibility = (
            "confirmed"
            if (
                rule_stage.credibility == "confirmed"
                and ai_stage.credibility in ["confirmed", "likely"]
            )
            else ai_stage.credibility
        )

        return EvidenceItem(
            claim=rule_value,
            credibility=credibility,
            rationale=(
                "Rule Engine과 AI 문맥 해석이 동일한 사업단계로 판단. "
                f"Rule: {rule_stage.rationale} / "
                f"AI: {ai_stage.rationale}"
            ),
            source_labels=list(
                dict.fromkeys(
                    rule_stage.source_labels
                    + ai_stage.evidence
                )
            ),
        )

    # -----------------------------------------------------
    # 2. Rule Unknown → AI 사용 가능
    # -----------------------------------------------------

    if rule_value == "미확정":

        return EvidenceItem(
            claim=ai_value,
            credibility=ai_stage.credibility,
            rationale=(
                "Rule Engine에서는 명시적 키워드를 찾지 못했으나 "
                "AI가 문맥과 시점을 기반으로 단계 후보를 판별. "
                + ai_stage.rationale
            ),
            source_labels=ai_stage.evidence,
        )

    # -----------------------------------------------------
    # 3. AI Unknown → Rule 유지
    # -----------------------------------------------------

    if ai_value == "미확정":

        return EvidenceItem(
            claim=rule_value,
            credibility=rule_stage.credibility,
            rationale=(
                "AI 문맥 판정은 미확정이나 "
                "Rule Engine에서 명시적 단계 신호가 확인됨. "
                + rule_stage.rationale
            ),
            source_labels=rule_stage.source_labels,
        )

    # -----------------------------------------------------
    # 4. 서로 다른 단계
    #
    # AI가 strong evidence를 갖고 있고,
    # Rule은 단순 키워드 탐지인 경우 AI 우선.
    #
    # 단 credibility를 confirmed로 올리지 않는다.
    # -----------------------------------------------------

    if ai_stage.credibility in [
        "confirmed",
        "likely",
    ]:

        return EvidenceItem(
            claim=ai_value,
            credibility="likely",
            rationale=(
                f"Rule Engine은 '{rule_value}'로 탐지했으나 "
                f"AI가 시점과 문맥을 포함해 '{ai_value}'로 판단. "
                "키워드 단독 탐지보다 문맥 판정을 우선하되 "
                "충돌이 존재하므로 최종 신뢰도는 likely로 제한. "
                f"AI 근거: {ai_stage.rationale}"
            ),
            source_labels=ai_stage.evidence,
        )

    # -----------------------------------------------------
    # 5. 둘 다 불확실
    # -----------------------------------------------------

    return EvidenceItem(
        claim="미확정",
        credibility="unknown",
        rationale=(
            f"Rule Engine({rule_value})과 "
            f"AI({ai_value}) 판정이 충돌하고 "
            "충분한 직접 근거가 없어 현재 단계 확정 불가"
        ),
        source_labels=[],
    )


# =========================================================
# 7. 고객 니즈 결합
# =========================================================

def resolve_customer_needs(
    rule_items: list[EvidenceItem],
    ai_items: list[AIContextItem],
) -> list[EvidenceItem]:

    result: dict[str, EvidenceItem] = {}

    # Rule 결과
    for item in rule_items:

        if item.claim == "고객 니즈 미확정":
            continue

        result[item.claim] = item

    # AI 결과
    for item in ai_items:

        if item.value not in ALLOWED_CUSTOMER_NEEDS:
            continue

        existing = result.get(item.value)

        if existing:

            result[item.value] = EvidenceItem(
                claim=item.value,
                credibility=(
                    "confirmed"
                    if (
                        existing.credibility == "confirmed"
                        and item.credibility in ["confirmed", "likely"]
                    )
                    else item.credibility
                ),
                rationale=(
                    f"Rule 신호와 AI 문맥 해석이 함께 지지. "
                    f"{item.rationale}"
                ),
                source_labels=item.evidence,
            )

        else:

            result[item.value] = _to_evidence(item)

    if not result:

        return [
            EvidenceItem(
                claim="고객 니즈 미확정",
                credibility="unknown",
                rationale=(
                    "Rule 및 AI 문맥 해석 모두에서 "
                    "충분한 고객 니즈 근거를 확보하지 못함"
                ),
                source_labels=[],
            )
        ]

    return list(result.values())[:8]


# =========================================================
# 8. Building Type 결합
# =========================================================

def resolve_building_type(
    rule_item: EvidenceItem,
    ai_item: AIContextItem,
) -> EvidenceItem:

    if rule_item.claim == ai_item.value:

        return EvidenceItem(
            claim=rule_item.claim,
            credibility=ai_item.credibility,
            rationale=(
                "Rule과 AI 문맥 판정이 일치. "
                + ai_item.rationale
            ),
            source_labels=ai_item.evidence,
        )

    if rule_item.claim == "미확정":

        return _to_evidence(ai_item)

    if ai_item.value == "미확정":

        return rule_item

    # 충돌 시 AI의 문맥 해석을 쓰되 likely 이하
    return EvidenceItem(
        claim=ai_item.value,
        credibility="likely",
        rationale=(
            f"Rule은 '{rule_item.claim}', "
            f"AI는 '{ai_item.value}'로 판단. "
            "프로젝트 전체 문맥을 반영한 AI 분류를 우선하되 "
            "충돌이 있어 추가 확인 필요. "
            + ai_item.rationale
        ),
        source_labels=ai_item.evidence,
    )


# =========================================================
# 9. Business Structure 결합
# =========================================================

def resolve_business_structure(
    rule_items: list[EvidenceItem],
    ai_items: list[AIContextItem],
) -> list[EvidenceItem]:

    result: dict[str, EvidenceItem] = {
        item.claim: item
        for item in rule_items
    }

    for item in ai_items:

        if item.value not in ALLOWED_STRUCTURE:
            continue

        rule_item = result.get(item.value)

        if (
            rule_item
            and rule_item.credibility == "confirmed"
        ):

            result[item.value] = EvidenceItem(
                claim=item.value,
                credibility="confirmed",
                rationale=(
                    "Rule과 AI Context가 해당 사업구도 요소를 확인. "
                    + item.rationale
                ),
                source_labels=item.evidence,
            )

        else:

            result[item.value] = EvidenceItem(
                claim=item.value,
                credibility=item.credibility,
                rationale=item.rationale,
                source_labels=item.evidence,
            )

    return list(result.values())


# =========================================================
# 10. 최종 Context Arbitration
# =========================================================

def combine_rule_and_ai_context(
    rule_result: RuleEngineResult,
    ai_result: AIContextInterpretation,
) -> tuple[ContextClassification, StageGate]:

    final_stage = resolve_business_stage(
        rule_stage=rule_result.context.business_stage,
        ai_stage=ai_result.business_stage,
    )

    final_building_type = resolve_building_type(
        rule_item=rule_result.context.building_type,
        ai_item=ai_result.building_type,
    )

    final_customer_needs = resolve_customer_needs(
        rule_items=rule_result.context.customer_needs,
        ai_items=ai_result.customer_needs,
    )

    final_business_structure = resolve_business_structure(
        rule_items=rule_result.context.business_structure,
        ai_items=ai_result.business_structure,
    )

    final_context = ContextClassification(
        customer_needs=final_customer_needs,
        building_type=final_building_type,
        business_stage=final_stage,
        business_structure=final_business_structure,
    )

    # AI까지 반영한 최종 Stage로 Stage Gate 재계산
    final_gate = build_stage_gate_from_final_stage(
        final_stage
    )

    return final_context, final_gate


# =========================================================
# 11. 최종 사업단계 → Stage Gate
# =========================================================

def build_stage_gate_from_final_stage(
    stage: EvidenceItem,
) -> StageGate:

    value = stage.claim

    if value in [
        "사업기획",
        "타당성 조사",
    ]:
        level = "Targeting"

    elif value in [
        "Master Plan",
        "설계 - SD (기본)",
        "설계 - DD (기본)",
        "설계 - CD (기본)",
    ]:
        level = "Golden Time"

    elif value in [
        "건설 인허가",
        "시공",
    ]:
        level = "Local Action"

    elif value in [
        "운영 인허가",
        "프로젝트 종료",
    ]:
        level = "Closed"

    else:
        level = "Unknown"

    return build_stage_gate(
        business_stage=stage,
        target_level=level,
    )
