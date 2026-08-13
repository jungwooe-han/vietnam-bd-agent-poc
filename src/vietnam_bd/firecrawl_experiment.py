from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import requests

from .priority_sources import PRIORITY_SOURCES
from .research_contribution import normalize_evidence_claim, normalize_source_url


FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v2"


@dataclass
class FirecrawlSource:
    url: str
    title: str = ""
    description: str = ""
    domain: str = ""
    source_tier: int = 2
    source_type: str = "general_web"
    evidence_claim: str = ""


@dataclass
class FirecrawlStageMetrics:
    name: str
    duration_seconds: float = 0.0
    search_calls: int = 0
    results: int = 0
    unique_sources: int = 0
    evidence: int = 0
    new_sources: int = 0
    new_evidence: int = 0


@dataclass
class FirecrawlPriorityExperimentResult:
    query: str
    provider: str = "firecrawl"
    research_path: str = "priority_then_general"
    priority_sources: list[FirecrawlSource] = field(default_factory=list)
    general_sources: list[FirecrawlSource] = field(default_factory=list)
    priority: FirecrawlStageMetrics = field(
        default_factory=lambda: FirecrawlStageMetrics(name="Priority Source Search")
    )
    general: FirecrawlStageMetrics = field(
        default_factory=lambda: FirecrawlStageMetrics(name="General Web Search")
    )
    primary_missing: list[str] = field(default_factory=list)
    general_resolved: list[str] = field(default_factory=list)
    final_missing: list[str] = field(default_factory=list)
    general_search_skipped: bool = False
    general_search_skip_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary_text(self) -> str:
        lines = [
            "PRIORITY SOURCE RESEARCH",
            "",
            "Priority Source Search",
            f"- Search calls: {self.priority.search_calls}",
            f"- Results: {self.priority.results}",
            f"- Unique sources: {self.priority.unique_sources}",
            f"- Evidence: {self.priority.evidence}",
            f"- Time: {self.priority.duration_seconds:.1f} sec",
            "",
            "After Priority Search",
            "- Missing gaps: " + (", ".join(self.primary_missing) or "none"),
        ]
        if self.general_search_skipped:
            lines.extend([
                "",
                "General Web Search",
                "- Skipped: yes",
                f"- Reason: {self.general_search_skip_reason}",
            ])
        else:
            lines.extend([
                "",
                "General Web Search",
                f"- Search calls: {self.general.search_calls}",
                f"- Results: {self.general.results}",
                f"- New sources: {self.general.new_sources}",
                f"- New evidence: {self.general.new_evidence}",
                f"- Time: {self.general.duration_seconds:.1f} sec",
                "- Resolved: " + (", ".join(self.general_resolved) or "not evaluated"),
                "",
                "Final missing",
                "- " + (", ".join(self.final_missing) or "none"),
            ])
        return "\n".join(lines)


SearchRunner = Callable[[str, tuple[str, ...] | None, int], list[dict[str, Any]]]


class FirecrawlClient:
    def __init__(self, api_key: str | None = None, timeout: int = 90):
        self.api_key = (api_key or os.getenv("FIRECRAWL_API_KEY", "")).strip()
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is not configured.")

    def search(
        self, query: str, domains: tuple[str, ...] | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "sources": [{"type": "web"}, {"type": "news"}],
        }
        if domains:
            body["includeDomains"] = list(domains)
        response = requests.post(
            f"{FIRECRAWL_BASE_URL}/search",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return [*data.get("web", []), *data.get("news", [])]

    def scrape(self, url: str) -> dict[str, Any]:
        response = requests.post(
            f"{FIRECRAWL_BASE_URL}/scrape",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"url": url, "formats": ["markdown"]},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("data", {})


def run_priority_source_experiment(
    query: str,
    *,
    missing_intelligence: list[str] | None = None,
    search_runner: SearchRunner | None = None,
    minimum_priority_sources: int = 2,
    limit: int = 10,
) -> FirecrawlPriorityExperimentResult:
    """Run an isolated Firecrawl A/B collector without changing the BD engine."""

    runner = search_runner or FirecrawlClient().search
    result = FirecrawlPriorityExperimentResult(
        query=query, primary_missing=list(missing_intelligence or [])
    )
    started = perf_counter()
    priority_raw = runner(query, PRIORITY_SOURCES, limit)
    result.priority.duration_seconds = round(perf_counter() - started, 4)
    result.priority.search_calls = 1
    result.priority.results = len(priority_raw)
    result.priority_sources = _deduplicate_sources(priority_raw, priority=True)
    result.priority.unique_sources = len(result.priority_sources)
    result.priority.evidence = _evidence_count(result.priority_sources)
    result.priority.new_sources = result.priority.unique_sources
    result.priority.new_evidence = result.priority.evidence

    if result.priority.unique_sources >= minimum_priority_sources and not result.primary_missing:
        result.general_search_skipped = True
        result.general_search_skip_reason = "Priority sources met the configured sufficiency check."
        return result

    general_query = build_targeted_general_query(query, result.primary_missing)
    started = perf_counter()
    general_raw = runner(general_query, None, limit)
    result.general.duration_seconds = round(perf_counter() - started, 4)
    result.general.search_calls = 1
    result.general.results = len(general_raw)
    result.general_sources = _deduplicate_sources(
        general_raw,
        priority=False,
        exclude_urls={item.url for item in result.priority_sources},
        exclude_claims={item.evidence_claim for item in result.priority_sources},
    )
    result.general.unique_sources = len(result.general_sources)
    result.general.evidence = _evidence_count(result.general_sources)
    result.general.new_sources = result.general.unique_sources
    result.general.new_evidence = result.general.evidence
    # Do not infer resolved gaps from snippets. Existing ContextReadiness can
    # populate these fields later without introducing a second rule system.
    result.final_missing = list(result.primary_missing)
    return result


def build_targeted_general_query(query: str, missing: list[str]) -> str:
    targets = " ".join(item.replace("_", " ") for item in missing if item.strip())
    return f"{query} {targets}".strip()


def write_experiment_result(
    result: FirecrawlPriorityExperimentResult,
    path: str | Path = "data/firecrawl_ab_results.jsonl",
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
    return output


def _deduplicate_sources(
    items: list[dict[str, Any]],
    *,
    priority: bool,
    exclude_urls: set[str] | None = None,
    exclude_claims: set[str] | None = None,
) -> list[FirecrawlSource]:
    blocked_urls = {normalize_source_url(item) for item in (exclude_urls or set())}
    blocked_claims = {
        normalize_evidence_claim(item) for item in (exclude_claims or set()) if item
    }
    seen_urls: set[str] = set()
    seen_claims: set[str] = set()
    output: list[FirecrawlSource] = []
    for item in items:
        url = str(item.get("url") or "").strip()
        normalized_url = normalize_source_url(url)
        description = str(item.get("description") or item.get("snippet") or "").strip()
        claim = normalize_evidence_claim(description)
        if not normalized_url or normalized_url in seen_urls or normalized_url in blocked_urls:
            continue
        if claim and (claim in seen_claims or claim in blocked_claims):
            continue
        seen_urls.add(normalized_url)
        if claim:
            seen_claims.add(claim)
        domain = (urlsplit(url).hostname or "").casefold()
        if domain.startswith("www."):
            domain = domain[4:]
        output.append(FirecrawlSource(
            url=url,
            title=str(item.get("title") or ""),
            description=description,
            domain=domain,
            source_tier=1 if priority else 2,
            source_type="priority" if priority else "general_web",
            evidence_claim=description,
        ))
    return output


def _evidence_count(items: list[FirecrawlSource]) -> int:
    return len({
        normalize_evidence_claim(item.evidence_claim)
        for item in items if item.evidence_claim
    })
