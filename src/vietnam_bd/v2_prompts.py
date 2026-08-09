from __future__ import annotations

import json
from typing import Any


COMMON_GROUNDING = """
Use only supplied research evidence and final four-axis context. Never invent a
company, person, relationship, project fact, date, amount, vendor, or decision
maker. Mark every stakeholder confirmed, likely, hypothesis, or unknown and cite
evidence labels. Return JSON only matching the supplied schema.
"""


def workstream_prompt(payload: dict[str, Any], candidates: list[str]) -> str:
    return COMMON_GROUNDING + f"""

Select at most three workstreams. The Rule layer is only a Vertical guardrail.
You may select ONLY from ALLOWED_CANDIDATES and may exclude any candidate when
evidence is insufficient. Do not add a new Vertical. Rank by actual relevance
across customer needs, building type, business stage, and business structure.
Do not recommend every product. Capabilities/products may appear only after the
workstream is justified and must be limited to evidence-relevant examples.
Put capabilities only in grounded_capabilities. Every capability requires a
rationale, context_basis, evidence_labels, and credibility. Leave both capability
lists empty when research/context evidence does not support a capability. Do not
use possible_capabilities for generic product suggestions.

ALLOWED_CANDIDATES:
{json.dumps(candidates, ensure_ascii=False)}

INPUT:
{json.dumps(payload, ensure_ascii=False)}
"""


def commercial_prompt(payload: dict[str, Any], closed: bool) -> str:
    closed_rule = (
        "The project is CLOSED. Active pursuit has stopped. Assess Timing as Low, "
        "do not imply a current sales opening, and use stakeholders only to describe "
        "historical participants or check candidates for future learning."
        if closed
        else "Assess the current commercial entry route."
    )
    return COMMON_GROUNDING + f"""

{closed_rule}
Assess Timing, Access, Openness, and Fit using only High, Medium, Low, or Unknown;
never use numeric scores. Each factor needs rationale and evidence labels.
Generate only information-to-confirm items whose answer changes Go/No-Go, target,
workstream priority, research depth, sales approach, or next action. Do not invent
a named person. Historical partners are hypotheses unless directly confirmed.

INPUT:
{json.dumps(payload, ensure_ascii=False)}
"""


def engagement_prompt(payload: dict[str, Any]) -> str:
    return COMMON_GROUNDING + f"""

Create meeting intelligence in OPEN, POWER, and WIN groups. Every talking point
must include question, information goal, why it matters, next action if positive,
and next action if negative or unknown. Create at most three Next Best Actions;
each needs action, target, purpose, done criteria, and priority. Avoid vague actions.

INPUT:
{json.dumps(payload, ensure_ascii=False)}
"""
