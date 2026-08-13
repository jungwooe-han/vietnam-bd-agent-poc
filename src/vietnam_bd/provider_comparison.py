from __future__ import annotations

import json
from pathlib import Path
from typing import Any


COMPARISON_FIELDS: dict[str, tuple[str, ...]] = {
    "Project": ("opportunity_title",),
    "Company / Owner": ("v2_snapshot", "project_intelligence", "owner_summary"),
    "Project Stage": ("project_stage",),
    "Location": ("v2_snapshot", "project_intelligence", "current_project_facts"),
    "Investment": ("v2_snapshot", "project_intelligence", "current_project_facts"),
    "Timeline": ("v2_snapshot", "project_intelligence", "project_timeline"),
    "EPC / Contractor": ("relationship_map", "nodes"),
    "Designer / Consultant": ("relationship_map", "nodes"),
    "Customer Needs": ("customer_needs",),
    "Product Mapping": ("product_top3",),
    "Who to Meet": ("priority_1",),
    "Questions": ("questions_to_ask",),
    "Talking Points": ("talking_points",),
    "Evidence / Citations": ("evidence",),
}


def _read(value: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        if hasattr(value, key):
            value = getattr(value, key)
        elif isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value]
    return value


def _status(left: Any, right: Any) -> str:
    left_missing = left in (None, "", [], {})
    right_missing = right in (None, "", [], {})
    if left_missing and right_missing:
        return "Missing in both"
    if left_missing:
        return "Only Firecrawl"
    if right_missing:
        return "Only Existing"
    return "Same" if left == right else "Different"


def _telemetry(run: Any) -> dict[str, Any]:
    telemetry = run.telemetry
    steps = telemetry.steps if telemetry else []
    totals = telemetry.totals() if telemetry else {}
    return {
        **totals,
        "run_id": telemetry.run_id if telemetry else "",
        "research_time": round(sum(step.duration_seconds for step in steps if "research" in step.name.casefold() or "firecrawl" in step.name.casefold()), 4),
        "priority_search_time": round(sum(step.duration_seconds for step in steps if step.name == "Firecrawl priority search"), 4),
        "general_search_time": round(sum(step.duration_seconds for step in steps if step.name == "Firecrawl general search"), 4),
        "scrape_time": round(sum(step.duration_seconds for step in steps if step.name == "Firecrawl URL scrape"), 4),
        "firecrawl_search_calls": sum(step.firecrawl_search_calls for step in steps),
        "firecrawl_scrape_calls": sum(step.firecrawl_scrape_calls for step in steps),
        "firecrawl_general_search_calls": sum(step.firecrawl_general_search_calls for step in steps),
        "research_contribution": telemetry.research_contribution_totals() if telemetry else {},
    }


def build_provider_comparison(existing: Any, firecrawl: Any, *, experiment_id: str) -> dict[str, Any]:
    fields = {}
    for label, path in COMPARISON_FIELDS.items():
        left = _read(existing.result, path)
        right = _read(firecrawl.result, path)
        fields[label] = {"status": _status(left, right), "existing": left, "firecrawl": right}
    return {
        "experiment_id": experiment_id,
        "engine": existing.telemetry.engine if existing.telemetry else "",
        "input_identifier": existing.telemetry.input_identifier if existing.telemetry else "",
        "existing": _telemetry(existing),
        "firecrawl": _telemetry(firecrawl),
        "bd_output": fields,
    }


def write_provider_comparison(payload: dict[str, Any], path: str | Path = "data/firecrawl_ab_results.jsonl") -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return output
