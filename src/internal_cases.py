from __future__ import annotations

import json
from pathlib import Path


def load_internal_cases(path: str = "data/dummy_opportunities.json") -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)
