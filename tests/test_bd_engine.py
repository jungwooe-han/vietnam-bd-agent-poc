from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.vietnam_bd.engine import ProjectAnalysisInput, analyze_project
from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.telemetry import AnalysisTelemetry, activate, deactivate, record_ai_response
from src.vietnam_bd.v3_rule_engine import build_v3_result


class ProjectEngineTest(unittest.TestCase):
    def test_demo_v2_runs_without_streamlit_and_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "telemetry.jsonl"
            run = analyze_project(
                ProjectAnalysisInput(seed="Demo opportunity", engine="BD v2", demo_mode=True),
                telemetry_log_path=str(log_path),
            )

            self.assertEqual(run.result_version, "v2")
            self.assertTrue(run.result.opportunity_title)
            self.assertIsNotNone(run.telemetry)
            self.assertEqual(
                [step.name for step in run.telemetry.steps],
                ["Input parsing", "Article / URL extraction", "Demo result building"],
            )
            payload = json.loads(log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(payload["engine"], "BD v2")
            self.assertFalse(payload["totals"]["error"])

    def test_ai_usage_and_web_search_calls_are_counted(self) -> None:
        class Usage:
            input_tokens = 120
            output_tokens = 30

        class Response:
            usage = Usage()
            output = [{"type": "web_search_call"}, {"type": "message"}]

        telemetry = AnalysisTelemetry(engine="BD v2")
        token = activate(telemetry)
        try:
            with telemetry.step("Research"):
                record_ai_response(Response(), web_search_enabled=True)
        finally:
            deactivate(token)
            telemetry.finish()

        metric = telemetry.steps[0]
        self.assertEqual(metric.ai_calls, 1)
        self.assertEqual(metric.input_tokens, 120)
        self.assertEqual(metric.output_tokens, 30)
        self.assertEqual(metric.search_calls, 1)

    def test_demo_v3_result_is_unchanged_by_engine_wrapper(self) -> None:
        seed = "Demo factory opportunity"
        expected = build_v3_result(demo_v2_result(), seed, "\n")
        with tempfile.TemporaryDirectory() as directory:
            run = analyze_project(
                ProjectAnalysisInput(seed=seed, engine="BD v3", demo_mode=True),
                telemetry_log_path=str(Path(directory) / "telemetry.jsonl"),
            )
        self.assertEqual(run.result.model_dump(), expected.model_dump())


if __name__ == "__main__":
    unittest.main()
