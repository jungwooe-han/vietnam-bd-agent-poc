from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from .context_interpreter import combine_rule_and_ai_context, interpret_context_with_ai
from .firecrawl_experiment import FirecrawlClient, build_targeted_general_query, _deduplicate_sources
from .priority_sources import PRIORITY_SOURCES
from .research import (
    DEEP_RESEARCH_SYSTEM,
    HISTORICAL_INTELLIGENCE_SYSTEM,
    LIMITED_RESEARCH_SYSTEM,
    QUICK_RESEARCH_SYSTEM,
    ROUND_FOCUS,
    ProgressCallback,
    _all_quick_evidence,
    _attach_context_provenance,
    _deep_evidence,
    _emit_progress,
    _round_prompt,
    _run_web_research,
    assess_context_readiness,
    build_quick_research_prompt,
    merge_deep_research,
    merge_quick_research,
    quick_research_to_rule_text,
    understand_seed,
)
from .research_contribution import record_quick_research_contribution, record_round_research_contribution
from .research_models import DeepResearchResult, QuickResearchResult, ResearchBundle, ResearchRoundResult, SeedUnderstanding
from .rule_engine import RuleEngineResult, evaluate_context
from .telemetry import measured_step, record_firecrawl_call, record_firecrawl_scrape_outcome


FirecrawlFactory = Callable[[], FirecrawlClient]


def build_firecrawl_query(seed: str, understanding: SeedUnderstanding) -> str:
    """Reuse SeedUnderstanding aliases without introducing another entity resolver."""
    values = [
        understanding.project,
        understanding.company,
        understanding.location,
        understanding.owner_candidate,
        *understanding.aliases,
        *understanding.core_search_entities,
    ]
    unique = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    return " ".join(f'"{value}"' if " " in value else value for value in unique[:8]) or seed


def _collect(
    client: FirecrawlClient,
    query: str,
    *,
    domains: tuple[str, ...] | None,
    general: bool,
    exclude_urls: set[str] | None = None,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], set[str]]:
    label = "Firecrawl general search" if general else "Firecrawl priority search"
    with measured_step(label):
        raw = client.search(query, domains, limit)
        record_firecrawl_call(operation="search", general=general)
    sources = _deduplicate_sources(raw, priority=not general, exclude_urls=exclude_urls)
    documents: list[dict[str, Any]] = []
    urls: set[str] = set()
    # Firecrawl search ranking supplies relevance; scrape only the bounded unique result set.
    for source in sources[:6]:
        with measured_step("Firecrawl URL scrape"):
            record_firecrawl_call(operation="scrape")
            try:
                scraped = client.scrape(source.url)
            except Exception as exc:  # isolate one source failure from the collection
                record_firecrawl_scrape_outcome(
                    url=source.url, succeeded=False, error_type=type(exc).__name__
                )
                continue
            record_firecrawl_scrape_outcome(url=source.url, succeeded=True)
        markdown = str(scraped.get("markdown") or scraped.get("content") or "").strip()
        if not markdown and not source.description:
            continue
        metadata = scraped.get("metadata") if isinstance(scraped.get("metadata"), dict) else {}
        documents.append({
            "title": metadata.get("title") or source.title,
            "url": source.url,
            "description": source.description,
            "published_date": metadata.get("publishedTime") or metadata.get("published_date") or "",
            "content": markdown[:30000],
            "source_type": source.source_type,
            "source_tier": source.source_tier,
        })
        urls.add(source.url)
    if sources and not documents:
        raise RuntimeError("All Firecrawl URL scrapes failed or returned no usable content.")
    return documents, urls


def _documents_context(documents: list[dict[str, Any]]) -> str:
    return json.dumps(documents, ensure_ascii=False)[:120000]


def _structure_quick(
    *, seed: str, extracted: str, user_context: str,
    understanding: SeedUnderstanding, documents: list[dict[str, Any]],
    current: QuickResearchResult | None = None, missing: list[str] | None = None,
) -> QuickResearchResult:
    base = build_quick_research_prompt(seed, extracted, user_context, understanding)
    if current is not None:
        base += f"\n\n[CURRENT CONTEXT RESEARCH]\n{current.model_dump_json(indent=2)}"
    if missing:
        base += f"\n\n[MISSING OR CONFLICTING REQUIREMENTS]\n{json.dumps(missing, ensure_ascii=False)}"
    base += (
        "\n\n[FIRECRAWL COLLECTED SOURCES]\n" + _documents_context(documents)
        + "\n\nUse only the supplied seed and collected sources. Do not perform web search or invent missing facts."
    )
    return _run_web_research(
        instructions=QUICK_RESEARCH_SYSTEM, prompt=base,
        result_model=QuickResearchResult, use_web=False,
    )


def _iterative_firecrawl_research(
    *, client: FirecrawlClient, mode: str, seed: str, user_context: str,
    understanding: SeedUnderstanding, quick: QuickResearchResult,
    rule_result: RuleEngineResult, known_urls: set[str],
    progress_callback: ProgressCallback | None,
) -> tuple[DeepResearchResult, list[ResearchRoundResult]]:
    rounds: list[ResearchRoundResult] = []
    known_entities: set[tuple[str, str]] = set()
    known_evidence: set[str] = set()
    used_queries = 0
    for index, focus in enumerate(ROUND_FOCUS[mode], start=1):
        remaining = 6 - used_queries
        if remaining <= 0:
            break
        _emit_progress(progress_callback, "research_round", mode=mode, round=index, total_rounds=len(ROUND_FOCUS[mode]), focus=focus)
        gaps = [gap.topic for item in rounds for gap in item.research_gaps if gap.critical]
        followups = [query.query for item in rounds for query in item.follow_up_queries]
        query = " ".join(filter(None, [build_firecrawl_query(seed, understanding), focus, *(followups[:2] or gaps[:2])]))
        documents, new_urls = _collect(client, query, domains=None, general=True, exclude_urls=known_urls)
        known_urls.update(new_urls)
        used_queries += 1
        with measured_step(f"{mode.title()} research round {index}: {focus}"):
            prompt = _round_prompt(
                mode=mode, round_number=index, focus=focus, seed=seed,
                user_context=user_context, seed_understanding=understanding,
                quick=quick, rule_result=rule_result, previous_rounds=rounds,
                query_budget_remaining=remaining,
            ) + "\n\n[FIRECRAWL COLLECTED SOURCES]\n" + _documents_context(documents) + "\nUse only these collected sources; do not browse or invent facts."
            result = _run_web_research(
                instructions=(HISTORICAL_INTELLIGENCE_SYSTEM if mode == "historical" else LIMITED_RESEARCH_SYSTEM if mode == "limited" else DEEP_RESEARCH_SYSTEM),
                prompt=prompt, result_model=ResearchRoundResult, use_web=False,
            )
            record_round_research_contribution(f"{mode.title()} research round {index}: {focus}", result)
        result.round_number = index
        entity_keys = {(item.name.casefold(), item.entity_type) for item in result.discovered_entities}
        evidence_keys = {re.sub(r"\s+", " ", item.claim.strip().casefold()) for item in _deep_evidence(result.findings)}
        result.new_evidence = [item.claim for item in _deep_evidence(result.findings) if re.sub(r"\s+", " ", item.claim.strip().casefold()) not in known_evidence][:20]
        has_new = bool((entity_keys - known_entities) or (evidence_keys - known_evidence))
        known_entities.update(entity_keys)
        known_evidence.update(evidence_keys)
        rounds.append(result)
        _emit_progress(progress_callback, "research_round_complete", mode=mode, round=index, total_rounds=len(ROUND_FOCUS[mode]), discovered_entities=len(result.discovered_entities), remaining_gaps=len(result.research_gaps))
        if not has_new:
            result.termination_reason = "No new entity or evidence discovered."
            break
        if not result.changes_sales_action:
            result.termination_reason = "Additional research is unlikely to change sales action."
            break
        if not any(gap.critical for gap in result.research_gaps) and not result.follow_up_queries and not result.claims_to_verify:
            result.termination_reason = "Critical gaps and verification tasks are resolved."
            break
    if rounds and not rounds[-1].termination_reason:
        rounds[-1].termination_reason = "Maximum round or query budget reached."
    return merge_deep_research(rounds), rounds


def research_opportunity_firecrawl(
    seed: str, extracted: str = "", user_context: str = "",
    progress_callback: ProgressCallback | None = None,
    client_factory: FirecrawlFactory = FirecrawlClient,
) -> tuple[ResearchBundle, RuleEngineResult]:
    client = client_factory()
    _emit_progress(progress_callback, "seed_understanding")
    with measured_step("Seed understanding"):
        understanding = understand_seed(seed, extracted, user_context)
    query = build_firecrawl_query(seed, understanding)
    _emit_progress(progress_callback, "context_research")
    documents, known_urls = _collect(client, query, domains=PRIORITY_SOURCES, general=False)
    with measured_step("Primary context research"):
        quick = _structure_quick(seed=seed, extracted=extracted, user_context=user_context, understanding=understanding, documents=documents)
    readiness = assess_context_readiness(understanding, quick)
    record_quick_research_contribution("Primary context research", quick)
    if not readiness.ready:
        primary_missing = list(readiness.missing_requirements)
        _emit_progress(progress_callback, "context_research_supplement", attempt=1, maximum=1, missing=primary_missing)
        targeted = build_targeted_general_query(query, primary_missing)
        extra_documents, extra_urls = _collect(client, targeted, domains=None, general=True, exclude_urls=known_urls)
        known_urls.update(extra_urls)
        with measured_step("Supplementary context research 1"):
            supplement = _structure_quick(seed=seed, extracted=extracted, user_context=user_context, understanding=understanding, documents=extra_documents, current=quick, missing=primary_missing)
        quick = merge_quick_research(quick, supplement)
        readiness = assess_context_readiness(understanding, quick)
        record_quick_research_contribution("Supplementary context research 1", supplement, primary_missing=primary_missing, missing_after=readiness.missing_requirements)

    rule_text = quick_research_to_rule_text(seed, extracted, quick, user_context)
    _emit_progress(progress_callback, "context_arbitration")
    with measured_step("Rule engine classification"):
        rule_result = evaluate_context(rule_text)
    with measured_step("AI context interpretation"):
        ai_context = interpret_context_with_ai(quick=quick)
    with measured_step("Evidence arbitration and stage gate"):
        final_context, final_stage_gate = combine_rule_and_ai_context(rule_result=rule_result, ai_result=ai_context)
        final_context = _attach_context_provenance(final_context, quick)
    rule_result.context = final_context
    rule_result.stage_gate = final_stage_gate
    _emit_progress(progress_callback, "stage_gate", status=final_stage_gate.status, research_depth=final_stage_gate.research_depth, active_pursuit=final_stage_gate.active_pursuit)
    mode = "historical" if final_stage_gate.status == "closed" else "limited" if final_stage_gate.research_depth == "limited" else "deep"
    detailed, rounds = _iterative_firecrawl_research(client=client, mode=mode, seed=seed, user_context=user_context, understanding=understanding, quick=quick, rule_result=rule_result, known_urls=known_urls, progress_callback=progress_callback)
    bundle = ResearchBundle(
        quick=quick,
        research_mode="limited" if mode in {"historical", "limited"} else "deep",
        stage_gate_status=rule_result.stage_gate.status,
        stage_gate_reason=rule_result.stage_gate.rationale,
        deep=detailed,
        active_pursuit="stop" if mode == "historical" else final_stage_gate.active_pursuit,
        historical_intelligence="limited" if mode == "historical" else final_stage_gate.historical_intelligence,
        seed_understanding=understanding,
        context_readiness=readiness,
        research_rounds=rounds,
    )
    return bundle, rule_result
