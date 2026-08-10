from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import ContextClassification, SFDCMatch, SFDCOpportunity


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sfdc_sample_opportunities.json"


@lru_cache(maxsize=1)
def load_sample_opportunities(path: Path = DATA_PATH) -> list[SFDCOpportunity]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SFDCOpportunity.model_validate(item) for item in payload["records"]]


def match_sample_opportunities(
    account: str,
    context: ContextClassification,
    workstreams: list[str],
    limit: int = 5,
) -> list[SFDCMatch]:
    query = " ".join([
        account,
        context.building_type.claim,
        *(item.claim for item in context.customer_needs),
        *workstreams,
    ]).casefold()
    query_tokens = {token for token in query.replace("/", " ").replace("-", " ").split() if len(token) >= 2}
    ranked = []
    for record in load_sample_opportunities():
        record_tokens = set(f"{record.account} {record.vertical}".casefold().split())
        overlap = query_tokens & record_tokens
        account_match = bool(account and account.casefold() in record.account.casefold())
        score = min(100, len(overlap) * 20 + (45 if account_match else 0))
        reason = "동일/유사 Account" if account_match else "Context와 Vertical 키워드 유사"
        ranked.append(SFDCMatch(record=record, similarity_reason=reason, match_score=score))
    ranked.sort(key=lambda item: (-item.match_score, item.record.oppty))
    return ranked[:limit]
