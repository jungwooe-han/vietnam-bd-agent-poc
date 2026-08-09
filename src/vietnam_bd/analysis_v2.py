from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import BDV2AnalysisResult
from .reasoning import reason_opportunity_v2
from .research import ProgressCallback, _emit_progress, research_opportunity


def analyze_opportunity_v2(
    seed: str,
    extracted: str = "",
    user_context: str = "",
    progress_callback: ProgressCallback | None = None,
    trace_callback: Callable[[dict[str, Any]], None] | None = None,
) -> BDV2AnalysisResult:
    """Run the complete BD v2 pipeline without changing the legacy BD entrypoint."""

    research_bundle, rule_result = research_opportunity(
        seed=seed,
        extracted=extracted,
        user_context=user_context,
        progress_callback=progress_callback,
    )
    if trace_callback:
        trace_callback(research_bundle.model_dump(mode="json"))
    _emit_progress(progress_callback, "sales_reasoning")
    result = reason_opportunity_v2(
        research_bundle,
        rule_result,
        seed=seed,
    )
    _emit_progress(progress_callback, "complete")
    return result
