from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from .models import ContextClassification


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "dx_portfolio_knowledge.json"


class DXPortfolioMatch(BaseModel):
    portfolio_id: str
    capability: str
    workstreams: list[str] = Field(default_factory=list)
    matched_needs: list[str] = Field(default_factory=list)
    applicable_scopes: list[str] = Field(default_factory=list)
    buying_routes: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    must_know_candidates: list[str] = Field(default_factory=list)
    source_url: str = ""
    evidence_labels: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def load_dx_portfolio_knowledge(path: Path = DATA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(value: str) -> set[str]:
    normalized = value.casefold().replace("/", " ").replace("-", " ")
    return {token for token in normalized.split() if len(token) >= 2}


def match_dx_portfolio(context: ContextClassification) -> list[DXPortfolioMatch]:
    knowledge = load_dx_portfolio_knowledge()
    need_items = [item for item in context.customer_needs if item.credibility != "unknown"]
    need_text = " ".join(item.claim for item in need_items)
    need_tokens = _tokens(need_text)
    alias_groups = {
        "energy": {"energy", "re100", "esg", "opex", "전력", "에너지", "절감"},
        "facility": {"facility", "운영", "설비", "공조", "hvac", "환경"},
        "mobility": {"mobility", "mobile", "모바일", "러기드", "태블릿", "현장"},
        "digital": {"digital", "dx", "디지털", "스마트", "자동화"},
        "workplace": {"workplace", "office", "업무", "오피스", "근무"},
    }
    expanded_tokens = set(need_tokens)
    for aliases in alias_groups.values():
        if aliases & need_tokens:
            expanded_tokens.update(aliases)
    results: list[DXPortfolioMatch] = []
    for entry in knowledge.get("portfolio", []):
        intel = entry.get("bd_intelligence", {})
        terms = intel.get("dx_relevant_needs", []) + intel.get("applicable_scopes", [])
        matched = [term for term in terms if _tokens(term) & expanded_tokens]
        if not matched:
            continue
        labels = list(dict.fromkeys(label for item in need_items for label in item.source_labels))
        results.append(DXPortfolioMatch(
            portfolio_id=entry["id"],
            capability=entry["official"]["name"],
            workstreams=intel.get("workstream_candidates", []),
            matched_needs=matched,
            applicable_scopes=intel.get("applicable_scopes", []),
            buying_routes=intel.get("typical_buying_routes", []),
            target_roles=intel.get("typical_buyers_influencers", []),
            must_know_candidates=intel.get("must_know_candidates", []),
            source_url=entry["official"].get("source_url", ""),
            evidence_labels=labels,
        ))
    return results
