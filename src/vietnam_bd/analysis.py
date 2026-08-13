from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from src.common.llm_json import strip_code_fences

from .models import AnalysisResult
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .telemetry import record_ai_response, record_retry


def _schema_instruction() -> str:
    schema = AnalysisResult.model_json_schema()
    return "\n[REQUIRED JSON SCHEMA]\n" + json.dumps(schema, ensure_ascii=False)


def _extract_response_text(response: Any) -> str:
    if getattr(response, "output_text", None):
        return response.output_text
    return str(response)


def analyze_opportunity(seed: str, extracted: str, guided_answers: str, internal_cases: str) -> AnalysisResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    enable_web = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"

    user_prompt = build_user_prompt(seed, extracted, guided_answers, internal_cases) + _schema_instruction()
    request: dict[str, Any] = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": user_prompt,
    }
    if enable_web:
        request["tools"] = [{"type": "web_search"}]

    response = client.responses.create(**request)
    record_ai_response(response, web_search_enabled=enable_web)
    raw = strip_code_fences(_extract_response_text(response))

    try:
        return AnalysisResult.model_validate_json(raw)
    except ValidationError as first_error:
        record_retry()
        repair = client.responses.create(
            model=model,
            instructions="Repair the supplied content into valid JSON matching the given schema. Return JSON only. Do not add facts.",
            input=f"SCHEMA:\n{json.dumps(AnalysisResult.model_json_schema(), ensure_ascii=False)}\n\nCONTENT:\n{raw}\n\nVALIDATION ERROR:\n{first_error}",
        )
        record_ai_response(repair)
        return AnalysisResult.model_validate_json(strip_code_fences(_extract_response_text(repair)))
