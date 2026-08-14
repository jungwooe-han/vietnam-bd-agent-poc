from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

from .research_models import (
    DeepResearchResult,
    DiscoveredEntity,
    QuickResearchResult,
    ResearchEvidence,
    ResearchRoundResult,
)
from .telemetry import current


TRACKING_PARAMETERS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "msclkid", "ref", "ref_src",
}


def normalize_evidence_claim(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def normalize_source_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value if "://" in value else "https://" + value)
    except ValueError:
        return value.casefold().rstrip("/")
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    port = f":{parsed.port}" if parsed.port else ""
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/") or "/"
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_PARAMETERS
    ]
    suffix = "?" + urlencode(sorted(query)) if query else ""
    return f"{host}{port}{path}{suffix}"


def quick_evidence(result: QuickResearchResult) -> list[ResearchEvidence]:
    return [
        *result.stage_signals,
        *result.customer_need_signals,
        *result.building_type_signals,
        *result.business_structure_signals,
        *result.recent_project_signals,
    ]


def deep_evidence(result: DeepResearchResult) -> list[ResearchEvidence]:
    return [
        *result.project_facts,
        *result.historical_projects,
        *result.project_ecosystem,
        *result.ecosystem_candidates,
        *result.peer_benchmarks,
        *result.buying_signals,
        *result.competitor_signals,
    ]


def quick_entities(result: QuickResearchResult) -> list[tuple[str, str]]:
    entities: list[tuple[str, str]] = []
    if result.company.strip():
        entities.append(("company", result.company))
    if result.project_name.strip():
        entities.append(("project", result.project_name))
    groups = (
        ("project_stage", result.stage_signals),
        ("customer_need", result.customer_need_signals),
        ("building_type", result.building_type_signals),
        ("business_structure", result.business_structure_signals),
        ("timeline", result.recent_project_signals),
    )
    entities.extend((kind, item.claim) for kind, items in groups for item in items if item.claim.strip())
    return entities


def round_entities(result: ResearchRoundResult) -> list[DiscoveredEntity]:
    return [item for item in result.discovered_entities if item.name.strip()]


def record_quick_research_contribution(
    stage: str,
    result: QuickResearchResult,
    *,
    primary_missing: list[str] | None = None,
    missing_after: list[str] | None = None,
) -> None:
    record_research_contribution(
        stage,
        quick_evidence(result),
        quick_entities(result),
        primary_missing=primary_missing,
        missing_after=missing_after,
    )


def record_round_research_contribution(stage: str, result: ResearchRoundResult) -> None:
    record_research_contribution(stage, deep_evidence(result.findings), round_entities(result))


def record_research_contribution(
    stage: str,
    evidence: Iterable[ResearchEvidence],
    entities: Iterable[tuple[str, str] | DiscoveredEntity],
    *,
    primary_missing: list[str] | None = None,
    missing_after: list[str] | None = None,
) -> None:
    telemetry = current()
    if telemetry is None:
        return
    evidence_list = list(evidence)
    evidence_keys = {normalize_evidence_claim(item.claim) for item in evidence_list if item.claim.strip()}
    source_keys = {
        normalized
        for item in evidence_list
        for value in (item.source_url, *(source.url for source in item.sources))
        if (normalized := normalize_source_url(value))
    }
    entity_keys = {
        _entity_key(item)
        for item in entities
        if _entity_key(item)[1]
    }
    duplicate_evidence = evidence_keys & telemetry._seen_research_evidence
    duplicate_sources = source_keys & telemetry._seen_research_sources
    duplicate_entities = entity_keys & telemetry._seen_research_entities
    missing_before = list(primary_missing or [])
    still_missing = list(missing_after or [])
    resolved = [item for item in missing_before if item not in set(still_missing)]
    item: dict[str, Any] = {
        "stage": stage,
        "evidence_count": len(evidence_list),
        "unique_evidence_in_stage": len(evidence_keys),
        "new_evidence_count": len(evidence_keys - telemetry._seen_research_evidence),
        "duplicate_evidence_count": len(duplicate_evidence),
        "evidence_duplication_rate": _percentage(len(duplicate_evidence), len(evidence_keys)),
        "source_count": len(source_keys),
        "new_source_count": len(source_keys - telemetry._seen_research_sources),
        "duplicate_source_count": len(duplicate_sources),
        "source_duplication_rate": _percentage(len(duplicate_sources), len(source_keys)),
        "entity_count": len(entity_keys),
        "new_entity_count": len(entity_keys - telemetry._seen_research_entities),
        "duplicate_entity_count": len(duplicate_entities),
        "final_output_evidence_count": 0,
    }
    if primary_missing is not None:
        item.update({
            "primary_missing": missing_before,
            "supplementary_resolved": resolved,
            "still_missing": still_missing,
        })
    telemetry.research_contribution.append(item)
    telemetry._research_evidence_by_stage[stage] = evidence_keys
    telemetry._seen_research_evidence.update(evidence_keys)
    telemetry._seen_research_sources.update(source_keys)
    telemetry._seen_research_entities.update(entity_keys)


def record_final_output_contribution(result: Any) -> None:
    telemetry = current()
    if telemetry is None:
        return
    final_keys = {
        normalize_evidence_claim(item.claim)
        for item in getattr(result, "evidence", [])
        if getattr(item, "claim", "").strip()
    }
    for item in telemetry.research_contribution:
        stage_keys = telemetry._research_evidence_by_stage.get(item["stage"], set())
        item["final_output_evidence_count"] = len(stage_keys & final_keys)


def _entity_key(item: tuple[str, str] | DiscoveredEntity) -> tuple[str, str]:
    if isinstance(item, DiscoveredEntity):
        canonical_roles = ",".join(sorted(item.project_roles))
        kind = f"{item.organization_type}:{canonical_roles}" if item.organization_type != "UNKNOWN" or canonical_roles else item.entity_type
        name = item.name
    else:
        kind, name = item
    return kind.casefold().strip(), normalize_evidence_claim(name)


def _percentage(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0
