from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator
from uuid import uuid4


LOGGER = logging.getLogger("vietnam_bd.telemetry")
_ACTIVE_RUN: ContextVar["AnalysisTelemetry | None"] = ContextVar("bd_active_telemetry", default=None)


@dataclass
class StepMetrics:
    name: str
    started_at: str
    ended_at: str = ""
    duration_seconds: float = 0.0
    ai_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    search_calls: int = 0
    external_api_calls: int = 0
    firecrawl_search_calls: int = 0
    firecrawl_scrape_calls: int = 0
    firecrawl_general_search_calls: int = 0
    retries: int = 0
    error: bool = False
    error_type: str = ""


@dataclass
class AnalysisTelemetry:
    engine: str
    research_provider: str = "existing"
    experiment_id: str = ""
    input_identifier: str = ""
    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: str = field(default_factory=lambda: _utc_now())
    ended_at: str = ""
    duration_seconds: float = 0.0
    steps: list[StepMetrics] = field(default_factory=list)
    research_contribution: list[dict[str, Any]] = field(default_factory=list)
    scrape_attempted_count: int = 0
    scrape_success_count: int = 0
    scrape_failure_count: int = 0
    failed_scrape_urls: list[dict[str, str]] = field(default_factory=list)
    error: bool = False
    error_type: str = ""
    _started_perf: float = field(default_factory=perf_counter, repr=False)
    _step_stack: list[StepMetrics] = field(default_factory=list, repr=False)
    _seen_research_evidence: set[str] = field(default_factory=set, repr=False)
    _seen_research_sources: set[str] = field(default_factory=set, repr=False)
    _seen_research_entities: set[tuple[str, str]] = field(default_factory=set, repr=False)
    _research_evidence_by_stage: dict[str, set[str]] = field(default_factory=dict, repr=False)

    @contextmanager
    def step(self, name: str) -> Iterator[StepMetrics]:
        metric = StepMetrics(name=name, started_at=_utc_now())
        started = perf_counter()
        self.steps.append(metric)
        self._step_stack.append(metric)
        try:
            yield metric
        except Exception as exc:
            metric.error = True
            metric.error_type = type(exc).__name__
            self.error = True
            self.error_type = type(exc).__name__
            raise
        finally:
            metric.ended_at = _utc_now()
            metric.duration_seconds = round(perf_counter() - started, 4)
            self._step_stack.pop()

    def current_step(self) -> StepMetrics | None:
        return self._step_stack[-1] if self._step_stack else None

    def finish(self, error: Exception | None = None) -> None:
        self.ended_at = _utc_now()
        self.duration_seconds = round(perf_counter() - self._started_perf, 4)
        if error is not None:
            self.error = True
            self.error_type = type(error).__name__

    def totals(self) -> dict[str, int | float | bool]:
        return {
            "duration_seconds": self.duration_seconds,
            "ai_calls": sum(item.ai_calls for item in self.steps),
            "input_tokens": sum(item.input_tokens for item in self.steps),
            "output_tokens": sum(item.output_tokens for item in self.steps),
            "search_calls": sum(item.search_calls for item in self.steps),
            "external_api_calls": sum(item.external_api_calls for item in self.steps),
            "retries": sum(item.retries for item in self.steps),
            "error": self.error,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "engine": self.engine,
            "research_provider": self.research_provider,
            "experiment_id": self.experiment_id,
            "input_identifier": self.input_identifier,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "steps": [asdict(item) for item in self.steps],
            "research_contribution": self.research_contribution,
            "firecrawl_scrape": {
                "scrape_attempted_count": self.scrape_attempted_count,
                "scrape_success_count": self.scrape_success_count,
                "scrape_failure_count": self.scrape_failure_count,
                "failed_scrape_urls": self.failed_scrape_urls,
                "scrape_failure_types": sorted({
                    item["error_type"] for item in self.failed_scrape_urls
                }),
            },
            "research_contribution_totals": self.research_contribution_totals(),
            "totals": self.totals(),
            "error_type": self.error_type,
        }

    def summary_text(self) -> str:
        lines = []
        for item in self.steps:
            details = []
            if item.ai_calls:
                details.append(f"AI {item.ai_calls}")
            if item.search_calls:
                details.append(f"search {item.search_calls}")
            if item.external_api_calls:
                details.append(f"external {item.external_api_calls}")
            if item.retries:
                details.append(f"retry {item.retries}")
            if item.error:
                details.append("ERROR")
            suffix = " / " + " / ".join(details) if details else ""
            lines.append(f"{item.name}: {item.duration_seconds:.1f} sec{suffix}")
        totals = self.totals()
        lines.extend([
            "",
            f"TOTAL: {self.duration_seconds:.1f} sec",
            f"AI calls: {totals['ai_calls']}",
            f"Search calls: {totals['search_calls']}",
        ])
        if self.research_contribution:
            lines.extend(["", "RESEARCH CONTRIBUTION"])
            for item in self.research_contribution:
                lines.extend([
                    "",
                    item["stage"],
                    f"- Evidence: {item['evidence_count']}",
                    f"- New Evidence: {item['new_evidence_count']}",
                    f"- Evidence Duplication: {item['evidence_duplication_rate']:.1f}%",
                    f"- Sources: {item['source_count']}",
                    f"- New Sources: {item['new_source_count']}",
                    f"- Source Duplication: {item['source_duplication_rate']:.1f}%",
                    f"- Entities: {item['entity_count']}",
                    f"- New Entities: {item['new_entity_count']}",
                    f"- Final-output usage: {item.get('final_output_evidence_count', 0)}",
                ])
                if item.get("primary_missing") is not None:
                    lines.extend([
                        "- Primary missing: " + (", ".join(item["primary_missing"]) or "none"),
                        "- Supplementary resolved: " + (
                            ", ".join(item["supplementary_resolved"]) or "none"
                        ),
                        "- Still missing: " + (", ".join(item["still_missing"]) or "none"),
                        f"- Missing gaps resolved: {len(item['supplementary_resolved'])}/"
                        f"{len(item['primary_missing'])}",
                    ])
            contribution_totals = self.research_contribution_totals()
            lines.extend([
                "",
                "Research total",
                f"- Unique evidence: {contribution_totals['unique_evidence_count']}",
                f"- Duplicate evidence: {contribution_totals['duplicate_evidence_count']}",
                f"- Unique sources: {contribution_totals['unique_source_count']}",
                f"- Duplicate sources: {contribution_totals['duplicate_source_count']}",
            ])
        return "\n".join(lines)

    def research_contribution_totals(self) -> dict[str, int]:
        return {
            "unique_evidence_count": len(self._seen_research_evidence),
            "duplicate_evidence_count": sum(
                item["duplicate_evidence_count"] for item in self.research_contribution
            ),
            "unique_source_count": len(self._seen_research_sources),
            "duplicate_source_count": sum(
                item["duplicate_source_count"] for item in self.research_contribution
            ),
            "unique_entity_count": len(self._seen_research_entities),
            "duplicate_entity_count": sum(
                item["duplicate_entity_count"] for item in self.research_contribution
            ),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def activate(telemetry: AnalysisTelemetry) -> Token:
    return _ACTIVE_RUN.set(telemetry)


def deactivate(token: Token) -> None:
    _ACTIVE_RUN.reset(token)


def current() -> AnalysisTelemetry | None:
    return _ACTIVE_RUN.get()


@contextmanager
def measured_step(name: str) -> Iterator[StepMetrics | None]:
    telemetry = current()
    if telemetry is None:
        yield None
        return
    with telemetry.step(name) as metric:
        yield metric


def record_ai_response(response: Any, *, web_search_enabled: bool = False) -> None:
    metric = _current_metric()
    if metric is None:
        return
    metric.ai_calls += 1
    usage = getattr(response, "usage", None)
    metric.input_tokens += int(_usage_value(usage, "input_tokens") or 0)
    metric.output_tokens += int(_usage_value(usage, "output_tokens") or 0)
    if web_search_enabled:
        output = getattr(response, "output", None) or []
        metric.search_calls += sum(
            1 for item in output
            if "web_search" in str(
                item.get("type", "") if isinstance(item, dict) else getattr(item, "type", "")
            ).casefold()
        )


def record_external_api_call(count: int = 1) -> None:
    metric = _current_metric()
    if metric is not None:
        metric.external_api_calls += count


def record_firecrawl_call(*, operation: str, general: bool = False, count: int = 1) -> None:
    metric = _current_metric()
    if metric is None:
        return
    metric.external_api_calls += count
    if operation == "search":
        metric.firecrawl_search_calls += count
        if general:
            metric.firecrawl_general_search_calls += count
    elif operation == "scrape":
        metric.firecrawl_scrape_calls += count


def record_firecrawl_scrape_outcome(
    *, url: str, succeeded: bool, error_type: str = ""
) -> None:
    telemetry = current()
    if telemetry is None:
        return
    telemetry.scrape_attempted_count += 1
    if succeeded:
        telemetry.scrape_success_count += 1
    else:
        telemetry.scrape_failure_count += 1
        telemetry.failed_scrape_urls.append({
            "url": url,
            "error_type": error_type or "UnknownError",
        })


def record_retry(count: int = 1) -> None:
    metric = _current_metric()
    if metric is not None:
        metric.retries += count


def write_summary(telemetry: AnalysisTelemetry, path: str | Path | None = None) -> Path:
    configured = path or os.getenv("BD_TELEMETRY_LOG", "data/analysis_telemetry.jsonl")
    output_path = Path(configured)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(telemetry.to_dict(), ensure_ascii=False) + "\n")
    LOGGER.info("BD analysis telemetry\n%s", telemetry.summary_text())
    return output_path


def _current_metric() -> StepMetrics | None:
    telemetry = current()
    return telemetry.current_step() if telemetry else None


def _usage_value(usage: Any, key: str) -> Any:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(key)
    return getattr(usage, key, None)
