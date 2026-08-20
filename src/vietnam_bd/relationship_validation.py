from __future__ import annotations

import re
from dataclasses import dataclass

from .research_models import DiscoveredEntity, DiscoveredRelationship


STATUS_ORDER = {"unknown": 0, "candidate": 1, "likely": 2, "confirmed": 3}


def entity_identity_keys(name: str, aliases: list[str] | None = None) -> set[str]:
    """Conservative identity keys for legal-name and harmless spelling variants."""

    suffixes = {
        "co", "company", "corp", "corporation", "inc", "incorporated",
        "ltd", "limited", "llc", "jsc", "tnhh",
    }
    keys: set[str] = set()
    for value in [name, *(aliases or [])]:
        for acronym in re.findall(r"\(([A-Z][A-Z0-9]{1,7})\)", value):
            keys.add("acronym:" + acronym.casefold())
        for alias in re.split(r"\s*/\s*", value):
            normalized = re.sub(r"\btech\b", "technology", alias.casefold())
            tokens = [token for token in re.findall(r"[a-z0-9]+", normalized) if token not in suffixes]
            if tokens:
                if "ubnd" in tokens or "authorities" in tokens or "authority" in tokens:
                    ignored = {"ubnd", "authority", "authorities", "provincial", "province", "of", "the"}
                    keys.add("government:" + "-".join(sorted(token for token in tokens if token not in ignored)))
                else:
                    keys.add("-".join(tokens))
    return keys


@dataclass(frozen=True)
class ParticipationAssessment:
    temporal_scope: str
    role_statuses: dict[str, str]
    reason: str


def assess_project_participation(
    entity: DiscoveredEntity,
    roles: list[str],
    *,
    in_candidate_research: bool = False,
    in_historical_research: bool = False,
) -> ParticipationAssessment:
    evidence = " ".join([
        entity.name,
        entity.participation_basis,
        entity.role_evidence,
        *entity.evidence_labels,
    ]).casefold()
    has_source = bool(entity.source_urls or entity.evidence_labels)
    base_status = (
        "confirmed" if entity.credibility == "confirmed" and has_source
        else "likely" if entity.credibility in {"confirmed", "likely"} and has_source
        else "candidate" if entity.credibility == "hypothesis"
        else "unknown"
    )
    person = bool(re.search(
        r"\b(deputy prime minister|prime minister|minister|vice minister|chairman|director general|mr|ms|dr)\b",
        entity.name,
        re.IGNORECASE,
    ))
    broad_only = any(token in evidence for token in (
        "intended user", "potential user", "user at forum", "participant at forum",
        "named participant / collaborator", "authorized distributor", "distributor channel",
        "authorized lines", "meeting with", "delegation",
    ))
    direct = entity.project_specific is True or any(token in evidence for token in (
        "mou signatory", "memorandum of understanding", "signed mou", "project owner",
        "developer", "contract award", "awarded contract", "appointed", "selected",
        "site location", "environmental permit", "land agreement",
    ))
    if in_historical_research:
        temporal, base_status, reason = "historical", "candidate", "Historical relationship only"
    elif in_candidate_research or entity.participation_status in {"candidate", "reference_only"}:
        temporal, base_status, reason = "candidate", "candidate", "Research candidate/reference only"
    elif person:
        temporal, base_status, reason = "candidate", "candidate", "Person is not an organization node"
    elif broad_only and not direct:
        temporal, base_status, reason = "candidate", "candidate", "Ecosystem mention without direct project participation"
    elif entity.project_specific is False:
        temporal, base_status, reason = "candidate", "candidate", "Source is not project-specific"
    else:
        temporal, reason = "current", "Project-specific evidence available" if direct else "Role evidence requires validation"

    statuses: dict[str, str] = {}
    for role in roles:
        status = base_status
        if role == "EPC" and not re.search(r"\bepc\b.*\b(contract|award|appointed|selected)\b|\b(contract|award|appointed|selected)\b.*\bepc\b", evidence):
            status = min_status(status, "candidate")
        elif role == "GENERAL_CONTRACTOR" and "general contractor" not in evidence:
            status = min_status(status, "candidate")
        elif role == "MEP_CONTRACTOR" and not any(token in evidence for token in ("m&e", "mep", "mechanical & electrical", "fit-out", "fit out")):
            status = min_status(status, "candidate")
        elif role == "INVESTOR" and not any(token in evidence for token in ("equity", "shareholding", "capital contribution", "investment amount", "funding", "investor")):
            status = min_status(status, "candidate")
        elif role in {"VENDOR", "EQUIPMENT_SUPPLIER"} and any(token in evidence for token in ("authorized distributor", "distributor channel", "authorized lines")) and not direct:
            status = min_status(status, "candidate")
        elif role == "END_CLIENT" and any(token in evidence for token in ("intended user", "potential user", "user at forum")):
            status = min_status(status, "candidate")
        statuses[role] = status
    if statuses and not any(value in {"confirmed", "likely"} for value in statuses.values()):
        temporal = "candidate" if temporal == "current" else temporal
    return ParticipationAssessment(temporal, statuses, reason)


def assess_relationship(relation: DiscoveredRelationship, relationship_type: str) -> tuple[str, str, str]:
    evidence = " ".join([
        relation.relationship_basis,
        relation.description,
        relation.role_evidence,
        *relation.evidence_labels,
    ]).casefold()
    has_source = bool(relation.source_urls or relation.evidence_labels)
    status = (
        "confirmed" if relation.credibility == "confirmed" and has_source
        else "likely" if relation.credibility in {"confirmed", "likely"} and has_source
        else "candidate" if relation.credibility == "hypothesis"
        else "unknown"
    )
    temporal = relation.temporal_scope
    if relation.project_specific is False:
        return relationship_type, "candidate", "candidate"
    if relationship_type == "INVESTS_IN" and any(token in evidence for token in ("meeting", "delegation", "facilitation")) and not any(token in evidence for token in ("equity", "shareholding", "capital contribution", "investment amount", "funding")):
        return "OTHER", "candidate", "candidate"
    if relationship_type in {"EQUIPMENT_SUPPLY", "SUPPLY_CONTRACT"} and any(token in evidence for token in ("authorized distributor", "distributor channel")) and relation.project_specific is not True:
        return relationship_type, "candidate", "candidate"
    if relationship_type == "STRATEGIC_PARTNERSHIP" and any(token in evidence for token in ("intended partner", "intended user", "potential user")):
        return relationship_type, "candidate", "candidate"
    return relationship_type, status, temporal


def min_status(current: str, ceiling: str) -> str:
    return current if STATUS_ORDER.get(current, 0) <= STATUS_ORDER[ceiling] else ceiling
