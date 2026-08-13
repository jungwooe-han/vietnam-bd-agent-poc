from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Literal
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel

from .analysis import analyze_opportunity
from .analysis_v2 import analyze_opportunity_v2
from .analysis_v3 import analyze_opportunity_v3
from .demo_data import demo_result
from .demo_data_v2 import demo_v2_result
from .ingestion import build_extracted_context
from .internal_cases import load_internal_cases
from .research import ProgressCallback
from .research_contribution import record_final_output_contribution
from .telemetry import AnalysisTelemetry, activate, deactivate, measured_step, write_summary
from .v3_rule_engine import build_v3_result


EngineName = Literal["BD v3", "BD v2", "기존 BD"]
LOGGER = logging.getLogger(__name__)


@dataclass
class ProjectAnalysisInput:
    seed: str
    engine: EngineName = "BD v3"
    guided_answers: str = ""
    uploaded_name: str | None = None
    uploaded_bytes: bytes | None = None
    demo_mode: bool = False
    closed_demo: bool = False
    research_provider: Literal["existing", "firecrawl"] = "existing"
    experiment_id: str = ""


@dataclass
class ProjectAnalysisRun:
    result: BaseModel
    result_version: Literal["v3", "v2", "legacy"]
    research_trace: dict[str, Any] = field(default_factory=dict)
    extraction_notes: list[str] = field(default_factory=list)
    telemetry: AnalysisTelemetry | None = None


class _UploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def analyze_project(
    input_data: ProjectAnalysisInput,
    *,
    progress_callback: ProgressCallback | None = None,
    telemetry_log_path: str | None = None,
) -> ProjectAnalysisRun:
    """Run the complete BD analysis without importing or depending on Streamlit."""

    if input_data.research_provider not in {"existing", "firecrawl"}:
        raise ValueError(f"Unsupported research provider: {input_data.research_provider}")

    telemetry = AnalysisTelemetry(
        engine=input_data.engine,
        research_provider=input_data.research_provider,
        experiment_id=input_data.experiment_id,
        input_identifier=sha256(input_data.seed.encode("utf-8")).hexdigest()[:16],
    )
    token = activate(telemetry)
    error: Exception | None = None
    trace: dict[str, Any] = {}
    try:
        with measured_step("Input parsing"):
            seed = input_data.seed
            guided = input_data.guided_answers
            uploaded = (
                _UploadedFile(input_data.uploaded_name, input_data.uploaded_bytes)
                if input_data.uploaded_name and input_data.uploaded_bytes is not None
                else None
            )

        with measured_step("Article / URL extraction"):
            extracted, notes = build_extracted_context(seed, uploaded)

        if input_data.engine == "기존 BD":
            with measured_step("Legacy analysis"):
                internal = load_internal_cases()
                result = demo_result() if input_data.demo_mode else analyze_opportunity(
                    seed, extracted, guided, internal
                )
            version: Literal["v3", "v2", "legacy"] = "legacy"
        else:
            trace_callback = lambda value: trace.update(value)
            if input_data.demo_mode:
                with measured_step("Demo result building"):
                    base = demo_v2_result(closed=input_data.closed_demo)
                    result = (
                        build_v3_result(base, seed, extracted + "\n" + guided)
                        if input_data.engine == "BD v3" else base
                    )
            elif input_data.engine == "BD v3":
                result = analyze_opportunity_v3(
                    seed,
                    extracted=extracted,
                    user_context=guided,
                    progress_callback=progress_callback,
                    trace_callback=trace_callback,
                    research_provider=input_data.research_provider,
                )
            else:
                result = analyze_opportunity_v2(
                    seed,
                    extracted=extracted,
                    user_context=guided,
                    progress_callback=progress_callback,
                    trace_callback=trace_callback,
                    research_provider=input_data.research_provider,
                )
            version = "v3" if input_data.engine == "BD v3" else "v2"

        if notes:
            result.source_summary.extend(notes)
        record_final_output_contribution(result)
        return ProjectAnalysisRun(
            result=result,
            result_version=version,
            research_trace=trace,
            extraction_notes=notes,
            telemetry=telemetry,
        )
    except Exception as exc:
        error = exc
        raise
    finally:
        telemetry.finish(error)
        try:
            write_summary(telemetry, telemetry_log_path)
        except Exception:  # noqa: BLE001 - telemetry must never break analysis
            LOGGER.exception("Failed to persist BD analysis telemetry")
        deactivate(token)


def compare_research_providers(
    seed: str,
    engine: EngineName = "BD v3",
    **input_kwargs: Any,
) -> dict[str, Any]:
    """Run paired full-pipeline analyses and return a side-by-side experiment record."""
    experiment_id = uuid4().hex
    existing = analyze_project(ProjectAnalysisInput(
        seed=seed, engine=engine, research_provider="existing",
        experiment_id=experiment_id, **input_kwargs,
    ))
    firecrawl = analyze_project(ProjectAnalysisInput(
        seed=seed, engine=engine, research_provider="firecrawl",
        experiment_id=experiment_id, **input_kwargs,
    ))
    from .provider_comparison import build_provider_comparison, write_provider_comparison
    comparison = build_provider_comparison(existing, firecrawl, experiment_id=experiment_id)
    write_provider_comparison(comparison)
    return {"existing": existing, "firecrawl": firecrawl, "comparison": comparison}
