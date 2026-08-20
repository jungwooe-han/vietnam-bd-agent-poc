from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from src.common.llm_json import strip_code_fences

from .research_models import (
    DeepResearchResult,
    ContextReadiness,
    EvidenceSource,
    QuickResearchResult,
    ResearchProjectLocation,
    ResearchBundle,
    ResearchEvidence,
    ResearchRoundResult,
    SeedUnderstanding,
)
from .rule_engine import RuleEngineResult, evaluate_context
from .research_contribution import (
    record_quick_research_contribution,
    record_round_research_contribution,
)
from .telemetry import measured_step, record_ai_response, record_retry
from .relationship_taxonomy import normalize_relationship_type

from .context_interpreter import (
    combine_rule_and_ai_context,
    interpret_context_with_ai,
)


ProgressCallback = Callable[[str, dict[str, Any]], None]


def _emit_progress(callback: ProgressCallback | None, event: str, **details: Any) -> None:
    if callback:
        callback(event, details)

# =========================================================
# 2. OpenAI Client
# =========================================================

def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    return OpenAI(api_key=api_key)


def _get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-mini")


def _extract_response_text(response: Any) -> str:
    if getattr(response, "output_text", None):
        return response.output_text

    return str(response)


def _schema_instruction(model_cls: type[BaseModel]) -> str:
    return (
        "\n\n[REQUIRED JSON SCHEMA]\n"
        + json.dumps(
            model_cls.model_json_schema(),
            ensure_ascii=False,
        )
    )


def _run_web_research(
    *,
    instructions: str,
    prompt: str,
    result_model: type[BaseModel],
    use_web: bool = True,
) -> BaseModel:

    client = _get_client()

    request: dict[str, Any] = {
        "model": _get_model(),
        "instructions": instructions,
        "input": prompt + _schema_instruction(result_model),
    }
    if use_web:
        request["tools"] = [{"type": "web_search"}]

    response = client.responses.create(**request)

    record_ai_response(response, web_search_enabled=use_web)
    raw = strip_code_fences(
        _extract_response_text(response)
    )

    try:
        return result_model.model_validate_json(raw)

    except ValidationError as first_error:

        record_retry()
        repair = client.responses.create(
            model=_get_model(),
            instructions=(
                "Repair the supplied content into valid JSON "
                "matching the given schema. "
                "Return JSON only. "
                "Do not add new facts."
            ),
            input=(
                f"SCHEMA:\n"
                f"{json.dumps(result_model.model_json_schema(), ensure_ascii=False)}"
                f"\n\nCONTENT:\n{raw}"
                f"\n\nVALIDATION ERROR:\n{first_error}"
            ),
        )

        record_ai_response(repair)
        repaired = strip_code_fences(
            _extract_response_text(repair)
        )

        return result_model.model_validate_json(repaired)


# =========================================================
# 2.5 Seed Understanding
# =========================================================

SEED_UNDERSTANDING_SYSTEM = """
Understand the supplied BD seed before research. Extract only what is present or
reasonably identifiable from the input. Do not perform web research and do not
invent names. Normalize company/project aliases and return valid JSON only.
"""


def understand_seed(
    seed: str,
    extracted: str = "",
    user_context: str = "",
) -> SeedUnderstanding:
    prompt = f"""
[SEED]
{seed}

[EXTRACTED SOURCE]
{extracted or "No extracted content."}

[USER PROVIDED CONTEXT]
{user_context or "No additional user context."}

Structure company, project, location, aliases, owner candidate, core search
entities, and facts directly supported by this input.
"""
    return _run_web_research(
        instructions=SEED_UNDERSTANDING_SYSTEM,
        prompt=prompt,
        result_model=SeedUnderstanding,
        use_web=False,
    )


# =========================================================
# 3. Quick Research
# =========================================================

QUICK_RESEARCH_SYSTEM = """
You are a B2B manufacturing project researcher.

Your first objective is NOT to produce a full business development report.

Your objective is to determine enough factual context to decide:

1. What project is being discussed?
2. What is the current project stage?
3. What type of construction/project is it?
4. What customer needs are explicitly or contextually visible?
5. What is already known about the project decision ecosystem?
6. Is this opportunity early enough to justify deeper research?
7. What is the most specific project site location directly supported by evidence?
8. What project-specific public milestones are visible across past and recent news?

RESEARCH PRINCIPLES

- Search beyond the user's original URL or text.
- Use the input only as a starting clue.
- Search the company, project, location and related recent announcements.
- Search backward for earlier official announcements and reliable news that show
  how this exact project progressed over time.
- Prefer primary sources, company announcements, government sources,
  industrial park sources and reliable business media.
- Pay special attention to TIME.

Example:
"construction will begin next year"
does NOT mean the project is currently under construction.

- Separate:
  confirmed
  likely
  hypothesis
  unknown

- Do not invent EPC, GC, architect, consultant, owner or vendor names.
- Do not infer a specific industrial park, address, or coordinate from province-level context.
- Populate project_location only from explicit source statements.
- Use precision=exact_site only for an explicit project address/site, industrial_park
  only when the source names that park, and partial for district/city/province/country.
- Include latitude/longitude only when coordinates are explicitly present in a source
  or verified source metadata. Put that support in coordinate_evidence.
- If the current project ecosystem is not publicly confirmed,
  leave it unknown.
- Treat one real-world event reported by multiple sources as one milestone.
  Keep all supporting source URLs, but do not repeat paraphrases of the event.
- Timeline evidence must be specific to this project. Do not treat general campus,
  company or market history as project progress.
- Keep this phase lightweight.
- Do NOT yet conduct extensive historical EPC or peer benchmark research.
- Return valid JSON only.
"""


def build_quick_research_prompt(
    seed: str,
    extracted: str = "",
    user_context: str = "",
    seed_understanding: SeedUnderstanding | None = None,
) -> str:

    return f"""
[INPUT SEED]
{seed}

[EXTRACTED SOURCE]
{extracted or "No extracted source content."}

[USER PROVIDED CONTEXT]
{user_context or "No additional user context."}

[SEED UNDERSTANDING]
{seed_understanding.model_dump_json(indent=2) if seed_understanding else "Not supplied."}

Perform QUICK RESEARCH.

Search beyond the supplied source.

Focus on information required to classify:

- customer needs
- building/project type
- current business/project stage
- business structure / ecosystem
- project site location, using the most specific directly supported level
- public project chronology: earliest announcement, MoU, planning, site, design,
  permit, contractor award, construction, procurement, completion and operation

For project_location, search and structure these levels without guessing:

- exact project site or address
- industrial park / industrial zone
- district / city
- province / region
- country

Vietnamese location terms may include industrial park, industrial zone, IP, IZ,
factory site, plant site, project site, khu cong nghiep, province, and district.

Especially determine whether the project appears to be:

- planning / feasibility
- master planning
- SD
- DD
- CD
- permitting / groundbreaking
- construction
- commissioning
- completed / operational

Use CURRENT project status rather than historical milestones.

Return concise evidence.
"""


def quick_research(
    seed: str,
    extracted: str = "",
    user_context: str = "",
    seed_understanding: SeedUnderstanding | None = None,
) -> QuickResearchResult:

    return _run_web_research(
        instructions=QUICK_RESEARCH_SYSTEM,
        prompt=build_quick_research_prompt(
            seed=seed,
            extracted=extracted,
            user_context=user_context,
            seed_understanding=seed_understanding,
        ),
        result_model=QuickResearchResult,
    )


def _source_keys(evidence: ResearchEvidence) -> set[str]:
    keys = {source.url or source.independence_key or source.name for source in evidence.sources}
    if evidence.source_url or evidence.source_name:
        keys.add(evidence.source_url or evidence.source_name)
    return {key.strip().casefold() for key in keys if key.strip()}


def _all_quick_evidence(result: QuickResearchResult) -> list[ResearchEvidence]:
    return [
        *result.stage_signals,
        *result.customer_need_signals,
        *result.building_type_signals,
        *result.business_structure_signals,
        *result.recent_project_signals,
        *result.project_location.evidence,
        *result.project_location.coordinate_evidence,
    ]


def assess_context_readiness(
    seed_understanding: SeedUnderstanding,
    result: QuickResearchResult,
) -> ContextReadiness:
    company_or_project = bool(
        result.company.strip() or result.project_name.strip()
        or seed_understanding.company.strip() or seed_understanding.project.strip()
    )
    stage_evidence = any(item.credibility != "unknown" for item in result.stage_signals)
    chronology_pattern = re.compile(
        r"\b(?:19|20)\d{2}\b|current|currently|now|today|recent|현재|최근|완료|예정|착공|준공|운영",
        re.IGNORECASE,
    )
    chronology = any(
        any(source.published_date.strip() for source in item.sources)
        or bool(chronology_pattern.search(f"{item.claim} {item.rationale}"))
        for item in [*result.stage_signals, *result.recent_project_signals]
    )
    all_evidence = _all_quick_evidence(result)
    sources = set().union(*(_source_keys(item) for item in all_evidence)) if all_evidence else set()
    minimum_sources = len(sources) >= 2
    strong_stage_claims = {
        item.claim.strip().casefold()
        for item in result.stage_signals
        if item.credibility in {"confirmed", "likely"} and item.claim.strip()
    }
    conflict = len(strong_stage_claims) > 1 or any(
        source.stance == "contradicts" for item in all_evidence for source in item.sources
    )
    missing = []
    if not company_or_project:
        missing.append("company_or_project")
    if not stage_evidence:
        missing.append("stage_evidence")
    if not chronology:
        missing.append("chronology_evidence")
    if not minimum_sources:
        missing.append("minimum_sources")
    if conflict:
        missing.append("major_conflict_resolution")
    return ContextReadiness(
        ready=not missing,
        company_or_project_identified=company_or_project,
        stage_evidence_present=stage_evidence,
        chronology_evidence_present=chronology,
        minimum_sources_present=minimum_sources,
        major_conflict_present=conflict,
        missing_requirements=missing,
        source_count=len(sources),
    )


def _merge_evidence_lists(*groups: list[ResearchEvidence]) -> list[ResearchEvidence]:
    return _consolidate_group(list(groups))


def merge_quick_research(base: QuickResearchResult, supplement: QuickResearchResult) -> QuickResearchResult:
    precision_rank = {
        "unknown": 0, "country": 1, "region": 2, "province": 3,
        "city": 4, "district": 5, "industrial_park": 6, "exact_site": 7,
    }
    status_rank = {"unknown": 0, "partial": 1, "confirmed": 2}

    def location_score(location: ResearchProjectLocation) -> tuple[int, int, int, int]:
        supported = sum(item.credibility in {"confirmed", "likely"} for item in location.evidence)
        return int(supported > 0), precision_rank[location.precision], status_rank[location.status], supported

    project_location = max(
        (base.project_location, supplement.project_location), key=location_score,
    )
    return QuickResearchResult(
        company=supplement.company or base.company,
        project_name=supplement.project_name or base.project_name,
        current_project_summary=supplement.current_project_summary or base.current_project_summary,
        stage_signals=_merge_evidence_lists(base.stage_signals, supplement.stage_signals),
        customer_need_signals=_merge_evidence_lists(base.customer_need_signals, supplement.customer_need_signals),
        building_type_signals=_merge_evidence_lists(base.building_type_signals, supplement.building_type_signals),
        business_structure_signals=_merge_evidence_lists(base.business_structure_signals, supplement.business_structure_signals),
        recent_project_signals=_merge_evidence_lists(base.recent_project_signals, supplement.recent_project_signals),
        project_location=project_location,
        source_summary=list(dict.fromkeys(base.source_summary + supplement.source_summary)),
    )


def supplement_context_research(
    seed: str,
    extracted: str,
    user_context: str,
    seed_understanding: SeedUnderstanding,
    current: QuickResearchResult,
    readiness: ContextReadiness,
) -> QuickResearchResult:
    prompt = f"""
[SEED]
{seed}

[EXTRACTED SOURCE]
{extracted or "No extracted source content."}

[USER PROVIDED CONTEXT]
{user_context or "No additional user context."}

[SEED UNDERSTANDING]
{seed_understanding.model_dump_json(indent=2)}

[CURRENT CONTEXT RESEARCH]
{current.model_dump_json(indent=2)}

[MISSING OR CONFLICTING REQUIREMENTS]
{json.dumps(readiness.missing_requirements, ensure_ascii=False)}

Perform a focused supplementary web research pass. Resolve only the listed
readiness gaps, prioritize current direct sources and chronology, and return new
or corrective evidence. Include source URLs and publication dates when available.
"""
    return _run_web_research(
        instructions=QUICK_RESEARCH_SYSTEM,
        prompt=prompt,
        result_model=QuickResearchResult,
    )


# =========================================================
# 4. Quick Research → Rule Engine용 Text
# =========================================================

def quick_research_to_rule_text(
    seed: str,
    extracted: str,
    result: QuickResearchResult,
    user_context: str = "",
) -> str:

    sections: list[str] = [
        "[ORIGINAL SEED]",
        seed or "",
        "",
        "[EXTRACTED SOURCE]",
        extracted or "",
        "",
        "[USER PROVIDED CONTEXT]",
        user_context or "",
        "",
        "[QUICK RESEARCH SUMMARY]",
        result.current_project_summary or "",
    ]

    groups = [
        ("STAGE SIGNALS", result.stage_signals),
        ("CUSTOMER NEED SIGNALS", result.customer_need_signals),
        ("BUILDING TYPE SIGNALS", result.building_type_signals),
        ("BUSINESS STRUCTURE SIGNALS", result.business_structure_signals),
        ("RECENT PROJECT SIGNALS", result.recent_project_signals),
    ]

    for title, evidence_list in groups:

        sections.append("")
        sections.append(f"[{title}]")

        for evidence in evidence_list:

            sections.append(
                " | ".join(
                    [
                        evidence.claim,
                        f"credibility={evidence.credibility}",
                        evidence.rationale,
                        evidence.source_name,
                    ]
                )
            )

    return "\n".join(sections)


def _attach_context_provenance(context, quick: QuickResearchResult):
    """Attach source metadata to the four final context axes after arbitration."""

    def enrich(item, evidence_group: list[ResearchEvidence]):
        # Keep each label, URL and publication date on the same row. Flattening
        # these fields independently made rule labels point to unrelated URLs
        # and left valid source names looking unlinked in the UI.
        rows: dict[str, tuple[str, str, str]] = {}

        def add_source(label: str, url: str = "", date: str = "") -> None:
            clean_label = label.strip()
            clean_url = url.strip()
            clean_date = date.strip()
            if not clean_label and not clean_url:
                return
            key = clean_url.casefold() or f"label:{clean_label.casefold()}"
            current = rows.get(key)
            if current is None:
                rows[key] = (clean_label or clean_url, clean_url, clean_date)
                return
            current_label, current_url, current_date = current
            best_label = current_label
            if clean_label and (not current_label or len(clean_label) < len(current_label)):
                best_label = clean_label
            rows[key] = (best_label, current_url or clean_url, current_date or clean_date)

        for evidence in evidence_group:
            matching_date = next(
                (
                    source.published_date
                    for source in evidence.sources
                    if evidence.source_url and source.url == evidence.source_url and source.published_date
                ),
                "",
            )
            add_source(evidence.source_name, evidence.source_url, matching_date)
            for source in evidence.sources:
                add_source(source.name, source.url, source.published_date)

        provenance = list(rows.values())
        rule_labels = [label for label in item.source_labels if label.startswith("rule:")]
        available = max(0, 10 - len(rule_labels))
        provenance = provenance[:available]
        labels = [*rule_labels, *(label for label, _url, _date in provenance)]
        urls = [*("" for _label in rule_labels), *(url for _label, url, _date in provenance)]
        dates = [*("" for _label in rule_labels), *(date for _label, _url, date in provenance)]
        conflicts = list(dict.fromkeys(
            evidence.claim for evidence in evidence_group if any(source.stance == "contradicts" for source in evidence.sources)
        ))
        return item.model_copy(update={
            "source_labels": labels,
            "source_urls": urls,
            "source_dates": dates,
            "source_conflicts": conflicts[:5],
        })

    return context.model_copy(update={
        "business_stage": enrich(context.business_stage, quick.stage_signals),
        "building_type": enrich(context.building_type, quick.building_type_signals),
        "customer_needs": [enrich(item, quick.customer_need_signals) for item in context.customer_needs],
        "business_structure": [enrich(item, quick.business_structure_signals) for item in context.business_structure],
    })


# =========================================================
# 5. Deep Research
# =========================================================

RELATIONSHIP_TAXONOMY_GUIDANCE = """
RELATIONSHIP DATA RULES

- Treat entity identity, organization type, project roles, decision influence,
  and relationships as separate concepts.
- Populate organization_type and multi-value project_roles for every supported
  organization. entity_type is deprecated compatibility data only.
- Use canonical relationship_type values from the response schema. Keep source
  wording in description and legal/document basis in relationship_basis.
- An entity may have multiple roles. Never emit compound display roles such as
  "Project Owner / Host" or "Technology / Co-development Partner".
- HQ/local are organization_scope values, never project roles. Do not invent a
  local entity from a Vietnam project location alone.
- Entity, role and relationship confidence are independent. Candidate or
  historical participation must not become a confirmed current role.
"""

DEEP_RESEARCH_SYSTEM = """
You are a senior B2B opportunity research analyst.

The opportunity has already passed a first-stage screening.

Your job is to research the ACCOUNT and PROJECT deeply enough
to help a salesperson understand the commercial battlefield.

Do NOT simply summarize the current article.

Research outward from the current project.

You should look for:

1. Current project facts
   - investment
   - site
   - capacity
   - schedule
   - production
   - project phase

2. Public project progress chronology
   - search past official announcements and reliable news about this exact project
   - capture dated changes in stage, site, design, permit, award, construction,
     procurement, completion or operation
   - consolidate duplicate reporting of the same event into one event with
     multiple source URLs
   - exclude general company, campus or market history from the project timeline

3. Historical projects by the same owner/company
   - previous factories
   - previous expansions
   - previous Vietnam or regional projects

4. Project ecosystem
   - architect
   - design consultant
   - PM/CM
   - EPC
   - GC
   - major engineering partners

5. Historical ecosystem relationships
   If the CURRENT project does not reveal EPC / GC / architect:
   research prior projects by the same owner.

6. Candidate ecosystem
   Candidate does NOT mean confirmed.

   Example logic:
   - Current EPC is not public.
   - Company used Firm A repeatedly on similar projects.
   - Firm A may therefore be worth checking.

   Such information must be labelled likely or hypothesis,
   never confirmed.

7. Peer benchmark
   Research comparable manufacturing projects when useful.

8. Buying signals
   - hiring
   - capacity expansion
   - tender activity
   - energy / ESG requirements
   - operational issues
   - schedule pressure

9. Competitor / incumbent signals
   only when public evidence exists.

EVIDENCE RULES

confirmed:
direct factual support from credible source

likely:
multiple contextual signals support the interpretation

hypothesis:
commercial hypothesis requiring field validation

unknown:
insufficient evidence

Never fabricate names, relationships, amounts or dates.

Return valid JSON only.
""" + RELATIONSHIP_TAXONOMY_GUIDANCE


def build_deep_research_prompt(
    seed: str,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
) -> str:

    return f"""
[ORIGINAL OPPORTUNITY]
{seed}

[QUICK RESEARCH]
{quick.model_dump_json(indent=2)}

[RULE CLASSIFICATION]
{rule_result.context.model_dump_json(indent=2)}

[STAGE GATE]
{rule_result.stage_gate.model_dump_json(indent=2)}

Perform DEEP RESEARCH for this opportunity.

Do not repeat the quick research unnecessarily.

Go deeper into:

- current project ecosystem
- dated public progress history for this exact project, searching older as well as
  recent official announcements and news
- owner's historical projects
- historical architect / EPC / GC relationships
- peer benchmarks where useful
- buying signals
- publicly visible competitor/incumbent signals

If a current EPC/GC/architect is unknown,
look for historical relationships and produce CHECK CANDIDATES,
not fake confirmed facts.

Focus on facts that can change sales action.
"""


def deep_research(
    seed: str,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
) -> DeepResearchResult:

    return _run_web_research(
        instructions=DEEP_RESEARCH_SYSTEM,
        prompt=build_deep_research_prompt(
            seed=seed,
            quick=quick,
            rule_result=rule_result,
        ),
        result_model=DeepResearchResult,
    )


# =========================================================
# 6. Limited Research
# =========================================================

LIMITED_RESEARCH_SYSTEM = """
You are a B2B project researcher evaluating a late-stage opportunity.

The project appears to have passed its main early specification window.

Do NOT perform broad deep research.

Only investigate whether commercially actionable openings remain.

Focus on:

- unawarded packages
- late procurement
- GC/EPC purchasing routes
- change orders
- retrofit or add-on scope
- operations / maintenance opportunities
- future expansion phases

If there is no credible remaining opening, say so.

Do not invent opportunities.

Return valid JSON only.
""" + RELATIONSHIP_TAXONOMY_GUIDANCE

HISTORICAL_INTELLIGENCE_SYSTEM = """
You are a B2B project researcher studying a closed project for future learning.

Active pursuit of the current project has stopped. Do not invent a remaining
sales opening and do not recommend products. Conduct LIMITED historical
intelligence research only. Where public evidence permits, identify End Client,
Architect or Design Consultant, EPC, GC, major Vendor or Solution Provider,
investment size, key dates, procurement structure, historical project partners,
and repeated owner-partner patterns. Clearly distinguish confirmed, likely,
hypothesis, and unknown. Return valid JSON only.
""" + RELATIONSHIP_TAXONOMY_GUIDANCE


def limited_research(
    seed: str,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
) -> DeepResearchResult:

    prompt = f"""
[OPPORTUNITY]
{seed}

[QUICK RESEARCH]
{quick.model_dump_json(indent=2)}

[STAGE GATE]
{rule_result.stage_gate.model_dump_json(indent=2)}

Conduct LIMITED RESEARCH only.

Determine whether any realistic remaining sales entry point exists.

Do not perform broad historical research unless needed to identify
a remaining procurement route.
"""

    return _run_web_research(
        instructions=LIMITED_RESEARCH_SYSTEM,
        prompt=prompt,
        result_model=DeepResearchResult,
    )


def historical_intelligence_research(
    seed: str,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
) -> DeepResearchResult:
    prompt = f"""
[CLOSED PROJECT]
{seed}

[QUICK RESEARCH]
{quick.model_dump_json(indent=2)}

[FINAL CONTEXT]
{rule_result.context.model_dump_json(indent=2)}

Build limited historical intelligence for future opportunities. Do not produce
active-pursuit recommendations for this project.
"""
    return _run_web_research(
        instructions=HISTORICAL_INTELLIGENCE_SYSTEM,
        prompt=prompt,
        result_model=DeepResearchResult,
    )


# =========================================================
# 6.5 Bounded Iterative Research
# =========================================================

ROUND_FOCUS = {
    "deep": (
        "Current project, dated public progress history, current stage, schedule, investment and current ecosystem",
        "Owner history, prior EPC/GC/Architect relationships, useful peer benchmarks, and verification of current-project participation",
    ),
    "limited": (
        "Remaining unawarded scope, procurement route, change orders and add-on openings",
        "Verify the remaining opening, responsible buyer and current award status",
    ),
    "historical": (
        "Closed-project participants, award structure, investment and key dates",
        "Owner history, repeated partner patterns and cross-check of project participation",
    ),
}


def _deep_evidence(result: DeepResearchResult) -> list[ResearchEvidence]:
    return [
        *result.project_facts,
        *result.historical_projects,
        *result.project_ecosystem,
        *result.ecosystem_candidates,
        *result.peer_benchmarks,
        *result.buying_signals,
        *result.competitor_signals,
    ]


def _expanded_sources(item: ResearchEvidence) -> list[EvidenceSource]:
    sources = list(item.sources)
    if (item.source_name or item.source_url) and not any(
        source.url == item.source_url and source.name == item.source_name for source in sources
    ):
        sources.append(EvidenceSource(name=item.source_name or item.source_url, url=item.source_url))
    return sources


def _consolidate_group(
    groups: list[list[ResearchEvidence]],
    *,
    historical_candidate: bool = False,
) -> list[ResearchEvidence]:
    grouped: dict[str, list[ResearchEvidence]] = {}
    for item in (entry for group in groups for entry in group):
        grouped.setdefault(re.sub(r"\s+", " ", item.claim.strip().casefold()), []).append(item)

    consolidated = []
    rank = {"unknown": 0, "hypothesis": 1, "likely": 2, "confirmed": 3}
    by_rank = {value: key for key, value in rank.items()}
    for items in grouped.values():
        sources: list[EvidenceSource] = []
        seen_sources: set[tuple[str, str, str]] = set()
        for item in items:
            for source in _expanded_sources(item):
                key = (source.url, source.independence_key, source.name)
                if key not in seen_sources:
                    seen_sources.add(key)
                    sources.append(source)
        support = [source for source in sources if source.stance == "supports"]
        contradictions = [source for source in sources if source.stance == "contradicts"]
        independent = {
            source.independence_key or source.url or source.name
            for source in support
            if source.independence_key or source.url or source.name
        }
        best = max((rank[item.credibility] for item in items), default=0)
        if any(source.source_type in {"official", "government", "company"} for source in support):
            best = max(best, rank["confirmed"])
        elif len(independent) >= 2:
            best = max(best, rank["likely"])
        if contradictions:
            best = max(rank["unknown"], best - 1)
        if historical_candidate:
            best = min(best, rank["hypothesis"])
        primary = support[0] if support else (sources[0] if sources else None)
        consolidated.append(
            ResearchEvidence(
                claim=items[0].claim,
                credibility=by_rank[best],
                source_name=primary.name if primary else items[0].source_name,
                source_url=primary.url if primary else items[0].source_url,
                rationale=" / ".join(dict.fromkeys(item.rationale for item in items if item.rationale)),
                sources=sources,
            )
        )
    return consolidated


def merge_deep_research(rounds: list[ResearchRoundResult]) -> DeepResearchResult:
    findings = [research_round.findings for research_round in rounds]
    if not findings:
        return DeepResearchResult()
    return DeepResearchResult(
        company=next((item.company for item in reversed(findings) if item.company), ""),
        project_facts=_consolidate_group([item.project_facts for item in findings]),
        historical_projects=_consolidate_group([item.historical_projects for item in findings]),
        project_ecosystem=_consolidate_group([item.project_ecosystem for item in findings]),
        ecosystem_candidates=_consolidate_group(
            [item.ecosystem_candidates for item in findings], historical_candidate=True
        ),
        peer_benchmarks=_consolidate_group([item.peer_benchmarks for item in findings]),
        buying_signals=_consolidate_group([item.buying_signals for item in findings]),
        competitor_signals=_consolidate_group([item.competitor_signals for item in findings]),
        unresolved_topics=list(dict.fromkeys(topic for item in findings for topic in item.unresolved_topics)),
        source_summary=list(dict.fromkeys(source for item in findings for source in item.source_summary)),
    )


def _round_prompt(
    *,
    mode: str,
    round_number: int,
    focus: str,
    seed: str,
    user_context: str,
    seed_understanding: SeedUnderstanding,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
    previous_rounds: list[ResearchRoundResult],
    query_budget_remaining: int,
) -> str:
    prior = [
        {
            "round_number": item.round_number,
            "focus": item.focus,
            "new_evidence": item.new_evidence[:10],
            "discovered_entities": [
                {
                    "name": entity.name,
                    "organization_type": entity.organization_type,
                    "project_roles": entity.project_roles,
                    "legacy_entity_type": entity.entity_type,
                    "credibility": entity.credibility,
                    "project_specific": entity.project_specific,
                    "participation_status": entity.participation_status,
                    "participation_basis": entity.participation_basis,
                    "role_evidence": entity.role_evidence,
                }
                for entity in item.discovered_entities[:10]
            ],
            "discovered_relationships": [
                {
                    "from_entity": relation.from_entity,
                    "to_entity": relation.to_entity,
                    "relationship_type": relation.canonical_relationship_type or normalize_relationship_type(relation.relationship_type, relation.description)[0],
                    "relationship_basis": relation.relationship_basis,
                    "credibility": relation.credibility,
                    "project_specific": relation.project_specific,
                    "role_evidence": relation.role_evidence,
                }
                for relation in item.discovered_relationships[:10]
            ],
            "critical_gaps": [gap.topic for gap in item.research_gaps if gap.critical][:8],
            "follow_up_queries": [query.query for query in item.follow_up_queries[:6]],
            "claims_to_verify": [claim.claim for claim in item.claims_to_verify[:6]],
        }
        for item in previous_rounds
    ]
    quick_context = {
        "company": quick.company,
        "project_name": quick.project_name,
        "current_project_summary": quick.current_project_summary,
        "evidence": [
            {
                "claim": item.claim,
                "credibility": item.credibility,
                "source_url": item.source_url or next((source.url for source in item.sources if source.url), ""),
            }
            for item in _all_quick_evidence(quick)[:24]
        ],
    }
    return f"""
[MODE] {mode}
[ROUND] {round_number}
[ROUND FOCUS] {focus}
[QUERY BUDGET REMAINING] {query_budget_remaining}

[SEED]
{seed}

[USER PROVIDED CONTEXT]
{user_context or "No additional user context."}

[SEED UNDERSTANDING]
{seed_understanding.model_dump_json(indent=2)}

[CONTEXT RESEARCH]
{json.dumps(quick_context, ensure_ascii=False)}

[FINAL CONTEXT AND STAGE GATE]
{rule_result.model_dump_json(indent=2)}

[PREVIOUS ROUNDS]
{json.dumps(prior, ensure_ascii=False)}

Research only this round's focus. Use previous discovered entities, gaps,
follow-up queries and claims to verify. Return findings plus newly discovered
entities, explicitly evidenced relationships, remaining gaps, bounded follow-up
queries and claims requiring cross-check. Entity status and relationship status
are independent: preserve a supported entity even when its relationship is not
confirmed. Create a confirmed relationship only when a source directly supports
both endpoints and the relationship type (for example, a signed MoU or awarded
contract). A historical relationship alone must remain hypothesis and must not be
stated as current-project participation. Include multiple sources per claim when
available and mark contradicting sources. Do not exceed the query budget.

For every discovered entity, explicitly set project_specific,
participation_status, participation_basis, and role_evidence. A search mention,
event attendance, executive meeting, general authorized-distributor status,
historical partnership, or intended-user reference is not current-project
participation. Mark those candidate or reference_only. For each role, role_evidence
must state the project-specific sentence supporting that exact role.

Guardrails: meeting is not investment; distributor status is not a project
vendor; M&E/fit-out is not full EPC; intended user is not confirmed End Client;
technology partner is not Project Owner; industrial-park location is not Project
Owner. For every discovered relationship set project_specific and role_evidence.
Only a source directly linking both endpoints and the relationship may be current.
"""


def iterative_research(
    *,
    mode: str,
    seed: str,
    user_context: str = "",
    seed_understanding: SeedUnderstanding,
    quick: QuickResearchResult,
    rule_result: RuleEngineResult,
    max_query_budget: int = 6,
    progress_callback: ProgressCallback | None = None,
) -> tuple[DeepResearchResult, list[ResearchRoundResult]]:
    focuses = ROUND_FOCUS[mode]
    rounds: list[ResearchRoundResult] = []
    known_entities: set[tuple[str, str, tuple[str, ...]]] = set()
    known_relationships: set[tuple[str, str, str]] = set()
    known_evidence: set[str] = set()
    seen_queries: set[str] = set()
    used_query_budget = 0

    for index, focus in enumerate(focuses, start=1):
        remaining = max_query_budget - used_query_budget
        if remaining <= 0:
            break
        _emit_progress(
            progress_callback,
            "research_round",
            mode=mode,
            round=index,
            total_rounds=len(focuses),
            focus=focus,
        )
        with measured_step(f"{mode.title()} research round {index}: {focus}"):
            result = _run_web_research(
                instructions=(
                    HISTORICAL_INTELLIGENCE_SYSTEM if mode == "historical"
                    else LIMITED_RESEARCH_SYSTEM if mode == "limited"
                    else DEEP_RESEARCH_SYSTEM
                ),
                prompt=_round_prompt(
                    mode=mode,
                    round_number=index,
                    focus=focus,
                    seed=seed,
                    user_context=user_context,
                    seed_understanding=seed_understanding,
                    quick=quick,
                    rule_result=rule_result,
                    previous_rounds=rounds,
                    query_budget_remaining=remaining,
                ),
                result_model=ResearchRoundResult,
            )
            record_round_research_contribution(
                f"{mode.title()} research round {index}: {focus}", result
            )
        result.round_number = index
        new_queries = []
        for query in result.follow_up_queries:
            normalized = re.sub(r"\s+", " ", query.query.strip().casefold())
            if normalized and normalized not in seen_queries and used_query_budget < max_query_budget:
                seen_queries.add(normalized)
                used_query_budget += 1
                new_queries.append(query)
        result.follow_up_queries = new_queries

        entity_keys = {
            (item.name.casefold(), item.organization_type, tuple(sorted(item.project_roles)))
            for item in result.discovered_entities
        }
        relationship_keys = {
            (
                item.from_entity.casefold(),
                item.to_entity.casefold(),
                (item.canonical_relationship_type or normalize_relationship_type(item.relationship_type, item.description)[0]).casefold(),
            )
            for item in result.discovered_relationships
        }
        evidence_keys = {re.sub(r"\s+", " ", item.claim.strip().casefold()) for item in _deep_evidence(result.findings)}
        result.new_evidence = [
            item.claim for item in _deep_evidence(result.findings)
            if re.sub(r"\s+", " ", item.claim.strip().casefold()) not in known_evidence
        ][:20]
        has_new_information = bool(
            (entity_keys - known_entities)
            or (relationship_keys - known_relationships)
            or (evidence_keys - known_evidence)
        )
        known_entities.update(entity_keys)
        known_relationships.update(relationship_keys)
        known_evidence.update(evidence_keys)
        rounds.append(result)
        _emit_progress(
            progress_callback,
            "research_round_complete",
            mode=mode,
            round=index,
            total_rounds=len(focuses),
            discovered_entities=len(result.discovered_entities),
            remaining_gaps=len(result.research_gaps),
        )

        critical_gaps = any(gap.critical for gap in result.research_gaps)
        if not has_new_information:
            result.termination_reason = "No new entity or evidence discovered."
            break
        if not result.changes_sales_action:
            result.termination_reason = "Additional research is unlikely to change sales action."
            break
        if not critical_gaps and not result.follow_up_queries and not result.claims_to_verify:
            result.termination_reason = "Critical gaps and verification tasks are resolved."
            break

    if rounds and not rounds[-1].termination_reason:
        rounds[-1].termination_reason = "Maximum round or query budget reached."

    return merge_deep_research(rounds), rounds


# =========================================================
# 7. 전체 Research Orchestration
# =========================================================

def research_opportunity(
    seed: str,
    extracted: str = "",
    user_context: str = "",
    progress_callback: ProgressCallback | None = None,
    research_provider: Literal["existing", "firecrawl"] = "existing",
) -> tuple[ResearchBundle, RuleEngineResult]:

    if research_provider == "firecrawl":
        from .firecrawl_provider import research_opportunity_firecrawl
        return research_opportunity_firecrawl(
            seed=seed, extracted=extracted, user_context=user_context,
            progress_callback=progress_callback,
        )

    # -----------------------------------------------------
    # STEP 1: Seed Understanding + Context Research
    # -----------------------------------------------------

    _emit_progress(progress_callback, "seed_understanding")
    with measured_step("Seed understanding"):
        seed_understanding = understand_seed(
            seed=seed,
            extracted=extracted,
            user_context=user_context,
        )

    _emit_progress(progress_callback, "context_research")
    with measured_step("Primary context research"):
        quick = quick_research(
            seed=seed,
            extracted=extracted,
            user_context=user_context,
            seed_understanding=seed_understanding,
        )

    readiness = assess_context_readiness(seed_understanding, quick)
    record_quick_research_contribution("Primary context research", quick)
    for attempt in range(1, 2):
        if readiness.ready:
            break
        _emit_progress(
            progress_callback,
            "context_research_supplement",
            attempt=attempt,
            maximum=1,
            missing=readiness.missing_requirements,
        )
        with measured_step(f"Supplementary context research {attempt}"):
            primary_missing = list(readiness.missing_requirements)
            supplement = supplement_context_research(
                seed=seed,
                extracted=extracted,
                user_context=user_context,
                seed_understanding=seed_understanding,
                current=quick,
                readiness=readiness,
            )
        quick = merge_quick_research(quick, supplement)
        readiness = assess_context_readiness(seed_understanding, quick)
        record_quick_research_contribution(
            f"Supplementary context research {attempt}",
            supplement,
            primary_missing=primary_missing,
            missing_after=readiness.missing_requirements,
        )

    # -----------------------------------------------------
    # STEP 2
    # Rule Engine
    # -----------------------------------------------------

    rule_text = quick_research_to_rule_text(
        seed=seed,
        extracted=extracted,
        result=quick,
        user_context=user_context,
    )

    _emit_progress(progress_callback, "context_arbitration")
    with measured_step("Rule engine classification"):
        rule_result = evaluate_context(rule_text)

    # -----------------------------------------------------
    # STEP 2.5
    # AI Context Interpretation
    # -----------------------------------------------------

    with measured_step("AI context interpretation"):
        ai_context = interpret_context_with_ai(
            quick=quick,
        )

    with measured_step("Evidence arbitration and stage gate"):
        final_context, final_stage_gate = combine_rule_and_ai_context(
            rule_result=rule_result,
            ai_result=ai_context,
        )
        final_context = _attach_context_provenance(final_context, quick)

    # Rule + AI를 반영한 최종 Context
    rule_result.context = final_context
    rule_result.stage_gate = final_stage_gate
    _emit_progress(
        progress_callback,
        "stage_gate",
        status=final_stage_gate.status,
        research_depth=final_stage_gate.research_depth,
        active_pursuit=final_stage_gate.active_pursuit,
    )

    depth = final_stage_gate.research_depth

    # -----------------------------------------------------
    # STEP 3
    # Stage Gate
    # -----------------------------------------------------

    if final_stage_gate.status == "closed":

        detailed, rounds = iterative_research(
            mode="historical",
            seed=seed,
            user_context=user_context,
            seed_understanding=seed_understanding,
            quick=quick,
            rule_result=rule_result,
            progress_callback=progress_callback,
        )

        bundle = ResearchBundle(
            quick=quick,
            research_mode="limited",
            stage_gate_status=rule_result.stage_gate.status,
            stage_gate_reason=rule_result.stage_gate.rationale,
            deep=detailed,
            active_pursuit="stop",
            historical_intelligence="limited",
            seed_understanding=seed_understanding,
            context_readiness=readiness,
            research_rounds=rounds,
        )

        return bundle, rule_result

    if depth == "limited":

        detailed, rounds = iterative_research(
            mode="limited",
            seed=seed,
            user_context=user_context,
            seed_understanding=seed_understanding,
            quick=quick,
            rule_result=rule_result,
            progress_callback=progress_callback,
        )

        bundle = ResearchBundle(
            quick=quick,
            research_mode="limited",
            stage_gate_status=rule_result.stage_gate.status,
            stage_gate_reason=rule_result.stage_gate.rationale,
            deep=detailed,
            active_pursuit=final_stage_gate.active_pursuit,
            historical_intelligence=final_stage_gate.historical_intelligence,
            seed_understanding=seed_understanding,
            context_readiness=readiness,
            research_rounds=rounds,
        )

        return bundle, rule_result

    # -----------------------------------------------------
    # STEP 4
    # Deep Research
    # Targeting / Golden Time
    # -----------------------------------------------------

    detailed, rounds = iterative_research(
        mode="deep",
        seed=seed,
        user_context=user_context,
        seed_understanding=seed_understanding,
        quick=quick,
        rule_result=rule_result,
        progress_callback=progress_callback,
    )

    bundle = ResearchBundle(
        quick=quick,
        research_mode="deep",
        stage_gate_status=rule_result.stage_gate.status,
        stage_gate_reason=rule_result.stage_gate.rationale,
        deep=detailed,
        active_pursuit=final_stage_gate.active_pursuit,
        historical_intelligence=final_stage_gate.historical_intelligence,
        seed_understanding=seed_understanding,
        context_readiness=readiness,
        research_rounds=rounds,
    )

    return bundle, rule_result
