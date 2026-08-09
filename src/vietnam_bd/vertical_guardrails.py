from __future__ import annotations

from dataclasses import dataclass

from .models import ContextClassification


@dataclass(frozen=True)
class WorkstreamGuardrail:
    """Replaceable rule configuration, not a finalized product taxonomy."""

    name: str
    need_signals: tuple[str, ...] = ()
    building_signals: tuple[str, ...] = ()
    stage_signals: tuple[str, ...] = ()
    structure_signals: tuple[str, ...] = ()


# Provisional business-level candidates. Replace this tuple when the governed
# Vertical taxonomy is approved; reasoning code does not depend on these names.
DEFAULT_WORKSTREAM_GUARDRAILS: tuple[WorkstreamGuardrail, ...] = (
    WorkstreamGuardrail(
        name="Facility / Energy",
        need_signals=("전력", "energy", "re100", "opex", "고온", "습도", "운영 안정"),
        building_signals=("신축", "증축", "리모델링"),
        stage_signals=("사업기획", "타당성", "master plan", "설계", "건설 인허가", "시공"),
        structure_signals=("end client", "gc / epc"),
    ),
    WorkstreamGuardrail(
        name="Smart Building / Operations",
        need_signals=("dx", "디지털", "스마트", "운영", "tco"),
        building_signals=("신축", "리모델링", "스마트화", "증축"),
        stage_signals=("사업기획", "타당성", "master plan", "설계", "시공"),
        structure_signals=("end client", "lead architect", "gc / epc"),
    ),
    WorkstreamGuardrail(
        name="Safety / Compliance",
        need_signals=("소방", "인허가", "compliance", "고온", "염해"),
        building_signals=("신축", "리모델링", "증축"),
        stage_signals=("사업기획", "타당성", "master plan", "설계", "건설 인허가"),
        structure_signals=("end client", "lead architect", "government"),
    ),
    WorkstreamGuardrail(
        name="Frontline Mobility",
        need_signals=("현장 모바일", "러기드", "인력 dx", "디지털화"),
        building_signals=("스마트화",),
        stage_signals=("시공", "운영 인허가"),
        structure_signals=("end client", "gc / epc"),
    ),
)


def allowed_workstream_candidates(
    context: ContextClassification,
    catalog: tuple[WorkstreamGuardrail, ...] = DEFAULT_WORKSTREAM_GUARDRAILS,
) -> list[str]:
    """Return guardrail candidates; final relevance remains an AI decision."""

    values = {
        "need": " ".join(item.claim for item in context.customer_needs).casefold(),
        "building": context.building_type.claim.casefold(),
        "stage": context.business_stage.claim.casefold(),
        "structure": " ".join(item.claim for item in context.business_structure).casefold(),
    }

    candidates: list[str] = []
    for rule in catalog:
        axes = (
            (values["need"], rule.need_signals),
            (values["building"], rule.building_signals),
            (values["stage"], rule.stage_signals),
            (values["structure"], rule.structure_signals),
        )
        if any(any(signal.casefold() in value for signal in signals) for value, signals in axes):
            candidates.append(rule.name)
    return candidates
