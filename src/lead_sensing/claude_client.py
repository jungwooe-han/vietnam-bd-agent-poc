import json
from typing import Any

import requests

from src.common.llm_json import strip_code_fences

from .config import get_anthropic_api_key, get_model_name


ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def _extract_text(data: dict) -> str:
    blocks = data.get("content", [])
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(texts).strip()


def call_claude(
    prompt: str,
    *,
    max_tokens: int = 4000,
    use_web_search: bool = False,
    allowed_domains: list[str] | None = None,
) -> tuple[str, dict]:
    api_key = get_anthropic_api_key()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 없습니다. .env 또는 Streamlit Secrets에 키를 등록해주세요."
        )

    body: dict[str, Any] = {
        "model": get_model_name(),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    if use_web_search:
        tool: dict[str, Any] = {
            "type": "web_search_20250305",
            "name": "web_search",
        }
        if allowed_domains:
            tool["allowed_domains"] = allowed_domains
        body["tools"] = [tool]

    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        json=body,
        timeout=180,
    )

    try:
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"Anthropic 응답 파싱 실패: HTTP {response.status_code}") from e

    if not response.ok or data.get("error"):
        message = data.get("error", {}).get("message") or f"HTTP {response.status_code}"
        raise RuntimeError(f"Anthropic API 오류: {message}")

    return _extract_text(data), data


def parse_json_array(text: str) -> list[dict]:
    cleaned = strip_code_fences(text)
    first = cleaned.find("[")
    last = cleaned.rfind("]")
    if first == -1 or last == -1:
        raise RuntimeError("모델 응답에서 JSON 배열을 찾지 못했습니다.")
    try:
        return json.loads(cleaned[first:last + 1])
    except json.JSONDecodeError as e:
        raise RuntimeError("모델 응답 JSON 파싱에 실패했습니다.") from e


def parse_json_object(text: str) -> dict:
    cleaned = strip_code_fences(text)
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first == -1 or last == -1:
        raise RuntimeError("모델 응답에서 JSON 객체를 찾지 못했습니다.")
    try:
        return json.loads(cleaned[first:last + 1])
    except json.JSONDecodeError as e:
        raise RuntimeError("모델 응답 JSON 파싱에 실패했습니다.") from e
