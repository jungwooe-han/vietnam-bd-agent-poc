def strip_code_fences(text: str) -> str:
    return text.replace("```json", "").replace("```", "").strip()
