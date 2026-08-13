from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from .analysis_v2 import analyze_opportunity_v2
from .models_v3 import BDV3AnalysisResult
from .research import ProgressCallback
from .v3_rule_engine import build_v3_result
from .telemetry import measured_step


def analyze_opportunity_v3(seed: str, extracted: str = "", user_context: str = "", progress_callback: ProgressCallback | None = None, trace_callback: Callable[[dict[str, Any]], None] | None = None, research_provider: Literal["existing", "firecrawl"] = "existing") -> BDV3AnalysisResult:
    v2 = analyze_opportunity_v2(seed, extracted, user_context, progress_callback, trace_callback, research_provider)
    with measured_step("V3 output mapping"):
        return build_v3_result(v2, seed, extracted + "\n" + user_context)
