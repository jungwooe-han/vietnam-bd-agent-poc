from __future__ import annotations

import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .models import (
    BDV2AnalysisResult,
    CanonicalRelationship,
    DecisionInfluence,
    EntityIdentity,
    ProjectParticipation,
)
from .models_v3 import (
    BDV3AnalysisResult, V3ProductRecommendation, V3ProjectFact, V3Question,
    V3RelationshipMap, V3StakeholderTarget, V3StructureNode, V3StructureRelation,
    V3TalkingPoint,
)
from .relationship_taxonomy import (
    CORPORATE_RELATIONSHIPS,
    ROLE_DECISION_INFLUENCE,
    canonical_entity_id,
    normalize_relationship_type,
)


RULEBOOK_PATH = Path(__file__).resolve().parents[2] / "md (1).xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL_NS = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _read_rulebook(path: Path = RULEBOOK_PATH) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall("p:Relationship", REL_NS)}
        output: dict[str, list[dict[str, str]]] = {}
        for sheet in workbook.findall(".//m:sheet", NS):
            name = sheet.attrib["name"]
            if not re.match(r"^[123]\. .+_Rule$", name):
                continue
            target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            root = ET.fromstring(archive.read(target))
            rows: list[list[str]] = []
            for row in root.findall(".//m:sheetData/m:row", NS):
                cells: dict[int, str] = {}
                for cell in row.findall("m:c", NS):
                    ref = cell.attrib["r"]
                    col = 0
                    for char in re.match(r"[A-Z]+", ref).group(0):
                        col = col * 26 + ord(char) - 64
                    value = cell.find("m:v", NS)
                    text = "" if value is None else value.text or ""
                    if cell.attrib.get("t") == "s" and text:
                        text = shared[int(text)]
                    cells[col - 1] = text
                if cells:
                    rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
            header_index = next((i for i, row in enumerate(rows) if any(str(x).endswith("_ID") or x in {"Rule_ID", "Structure_ID", "Stage_ID", "Signal_ID"} for x in row)), 0)
            headers = rows[header_index]
            output[name] = [{headers[i]: row[i] if i < len(row) else "" for i in range(len(headers)) if headers[i]} for row in rows[header_index + 1:] if any(row)]
        return output


def _status(credibility: str) -> str:
    return {
        "confirmed": "confirmed",
        "likely": "likely",
        "hypothesis": "candidate",
        "candidate": "candidate",
    }.get(credibility, "unknown")


def _priority(value: str) -> int | None:
    try:
        parsed = int(float(value))
        return parsed if parsed in {1, 2, 3} else None
    except (TypeError, ValueError):
        return None


def _legacy_roles(role: str) -> list[str]:
    text = role.casefold().replace("-", " ").replace("_", " ")
    matches = (
        ("project owner", "PROJECT_OWNER"), ("owner", "PROJECT_OWNER"),
        ("end client", "END_CLIENT"), ("investor", "INVESTOR"),
        ("sponsor", "SPONSOR"), ("developer", "DEVELOPER"), ("host", "HOST"),
        ("co development", "CO_DEVELOPMENT_PARTNER"), ("strategic partner", "STRATEGIC_PARTNER"),
        ("architect", "ARCHITECT"), ("design", "ENGINEERING_CONSULTANT"),
        ("engineering consultant", "ENGINEERING_CONSULTANT"), ("pm / cm", "PM_CM"),
        ("pm cm", "PM_CM"), ("epc", "EPC"), ("general contractor", "GENERAL_CONTRACTOR"),
        ("gc ", "GENERAL_CONTRACTOR"), ("mep", "MEP_CONTRACTOR"),
        ("technology", "TECHNOLOGY_PROVIDER"), ("solution", "SOLUTION_PROVIDER"),
        ("equipment", "EQUIPMENT_SUPPLIER"), ("supplier", "EQUIPMENT_SUPPLIER"),
        ("vendor", "VENDOR"), ("operator", "OPERATOR"),
        ("government", "GOVERNMENT_PARTNER"), ("authority", "REGULATORY_AUTHORITY"),
        ("industrial park", "INDUSTRIAL_PARK"), ("landlord", "LANDLORD"),
    )
    roles = [canonical for token, canonical in matches if token in text]
    return list(dict.fromkeys(roles)) or ["OTHER"]


def _legacy_organization_type(role: str) -> str:
    text = role.casefold()
    if any(token in text for token in ("government", "authority")):
        return "PUBLIC_INSTITUTION"
    if any(token in text for token in ("technology", "solution")):
        return "TECHNOLOGY_COMPANY"
    if any(token in text for token in ("architect", "engineering", "epc", "pm / cm")):
        return "ENGINEERING_COMPANY"
    if any(token in text for token in ("contractor", "mep")):
        return "CONSTRUCTION_COMPANY"
    if any(token in text for token in ("investor", "capital", "pef")):
        return "FINANCIAL_INSTITUTION"
    if "industrial park" in text:
        return "INDUSTRIAL_PARK_DEVELOPER"
    return "PRIVATE_COMPANY"


def _ensure_canonical_relationship_map(v2: BDV2AnalysisResult) -> None:
    relmap = v2.relationship_map
    if relmap.entities:
        return
    current_project_text = " ".join([
        v2.opportunity_title,
        v2.executive_summary,
    ]).casefold()
    entity_ids: dict[str, str] = {}
    for actor in relmap.actors:
        if not actor.organization or actor.organization.upper() == "UNKNOWN":
            continue
        entity_id = canonical_entity_id(actor.organization)
        entity_ids[actor.actor_id] = entity_id
        role_text = actor.role.casefold()
        scope = (
            "global_hq" if role_text.strip() in {"hq", "owner hq"} or "global hq" in role_text
            else "local_entity" if "local" in role_text or "subsidiary" in role_text
            else "unknown"
        )
        status = actor.actor_status
        relmap.entities.append(EntityIdentity(
            entity_id=entity_id,
            canonical_name=actor.organization,
            organization_type=_legacy_organization_type(actor.role),
            organization_scope=scope,
            status=status,
            evidence_labels=actor.evidence_labels,
            source_urls=actor.source_urls,
            source_dates=actor.source_dates,
            legacy_entity_types=[actor.role],
        ))
        roles = _legacy_roles(actor.role)
        organization_key = actor.organization.casefold().split("(", 1)[0].strip()
        directly_mentioned = bool(
            len(organization_key) >= 4
            and re.search(rf"(?<!\w){re.escape(organization_key)}(?!\w)", current_project_text)
        )
        partnership_signal = any(token in current_project_text for token in (
            "memorandum of understanding", "mou", "co-development", "joint roadmap", "joint development"
        ))
        technology_signal = any(token in current_project_text for token in (
            "technology", "equipment", "laboratory", "lab"
        ))
        if directly_mentioned and roles == ["OTHER"] and partnership_signal and technology_signal:
            roles = ["CO_DEVELOPMENT_PARTNER", "TECHNOLOGY_PROVIDER", "EQUIPMENT_SUPPLIER"]
            relmap.entities[-1].organization_type = "TECHNOLOGY_COMPANY"
        if any(token in actor.organization.casefold() for token in (
            "national innovation centre", "national innovation center"
        )):
            roles = list(dict.fromkeys([*roles, "HOST", "GOVERNMENT_PARTNER"]))
            relmap.entities[-1].organization_type = "PUBLIC_INSTITUTION"
        decision_role = bool(set(roles) & {
            "PROJECT_OWNER", "END_CLIENT", "INVESTOR", "SPONSOR", "DEVELOPER",
            "HOST", "CO_DEVELOPMENT_PARTNER", "STRATEGIC_PARTNER", "ARCHITECT",
            "ENGINEERING_CONSULTANT", "PM_CM", "EPC", "GENERAL_CONTRACTOR",
            "TECHNOLOGY_PROVIDER", "SOLUTION_PROVIDER", "EQUIPMENT_SUPPLIER",
            "OPERATOR", "GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY",
            "INDUSTRIAL_PARK", "LANDLORD",
        })
        participation_temporal = actor.temporal_scope
        role_status = status
        if actor.temporal_scope == "current" and not directly_mentioned and not decision_role:
            participation_temporal = "candidate"
            role_status = "candidate"
        if roles != ["OTHER"] or scope == "unknown":
            relmap.participations.append(ProjectParticipation(
                project_id=relmap.project_id,
                entity_id=entity_id,
                roles=roles,
                role_statuses={role: role_status for role in roles},
                temporal_scope=participation_temporal,
                evidence_labels=actor.evidence_labels,
                source_urls=actor.source_urls,
                source_dates=actor.source_dates,
            ))
            for role in roles:
                for domain, influence in ROLE_DECISION_INFLUENCE.get(role, ()):
                    relmap.decision_influences.append(DecisionInfluence(
                        entity_id=entity_id,
                        domain=domain,
                        influence=influence,
                        status=role_status,
                        rationale=f"Migrated from legacy role {actor.role}.",
                        evidence_labels=actor.evidence_labels,
                    ))
    for relation in relmap.relationships:
        from_id = entity_ids.get(relation.from_actor_id)
        to_id = entity_ids.get(relation.to_actor_id)
        if not from_id or not to_id or from_id == to_id:
            continue
        relationship_type, basis = normalize_relationship_type(
            relation.relationship_type, relation.description
        )
        relmap.canonical_relationships.append(CanonicalRelationship(
            from_entity_id=from_id,
            to_entity_id=to_id,
            relationship_type=relationship_type,
            relationship_basis=basis,
            description=relation.description or relation.relationship_type,
            status=_status(relation.credibility),
            temporal_scope=relation.temporal_scope,
            evidence_labels=relation.evidence_labels,
            source_urls=relation.source_urls,
            source_dates=relation.source_dates,
        ))
    owner_participation = next((
        item for item in relmap.participations
        if "PROJECT_OWNER" in item.roles and item.temporal_scope == "current"
        and item.role_statuses.get("PROJECT_OWNER") in {"confirmed", "likely"}
    ), None)
    partner_participation = next((
        item for item in relmap.participations
        if "CO_DEVELOPMENT_PARTNER" in item.roles and item.temporal_scope == "current"
        and item.role_statuses.get("CO_DEVELOPMENT_PARTNER") in {"confirmed", "likely"}
    ), None)
    partnership_signal = any(token in current_project_text for token in (
        "memorandum of understanding", "mou", "co-development", "joint roadmap", "joint development"
    ))
    if owner_participation and partner_participation and partnership_signal and not any(
        relation.relationship_type in {"CO_DEVELOPMENT", "MOU"}
        for relation in relmap.canonical_relationships
    ):
        owner_entity = next(entity for entity in relmap.entities if entity.entity_id == owner_participation.entity_id)
        partner_entity = next(entity for entity in relmap.entities if entity.entity_id == partner_participation.entity_id)
        shared_urls = list(set(owner_entity.source_urls) & set(partner_entity.source_urls))
        relationship_status = "confirmed" if shared_urls else "likely"
        relmap.canonical_relationships.append(CanonicalRelationship(
            from_entity_id=owner_entity.entity_id,
            to_entity_id=partner_entity.entity_id,
            relationship_type="CO_DEVELOPMENT",
            relationship_basis="MOU",
            description="Legacy migration from a directly supported MoU / joint-development summary.",
            status=relationship_status,
            temporal_scope="current",
            evidence_labels=list(dict.fromkeys([*owner_entity.evidence_labels, *partner_entity.evidence_labels]))[:8],
            source_urls=shared_urls[:8],
        ))
    relmap.research_gaps = list(dict.fromkeys([
        *relmap.research_gaps,
        *[f"{item} — Not confirmed" for item in relmap.unknown_critical_actors],
    ]))[:12]


def _entity_alias_keys(entity: EntityIdentity) -> set[str]:
    """Return conservative identity keys for spelling/suffix variants.

    This intentionally does not attempt fuzzy company matching. It only folds
    common legal suffixes, Tech/Technology, slash-separated aliases, and word
    order in government-authority labels.
    """

    values = [entity.canonical_name, *entity.aliases]
    keys: set[str] = set()
    suffixes = {
        "co", "company", "corp", "corporation", "inc", "incorporated",
        "ltd", "limited", "llc", "jsc", "tnhh",
    }
    government_words = {"ubnd", "authority", "authorities", "provincial", "province", "of", "the"}
    for value in values:
        for alias in re.split(r"\s*/\s*", value):
            normalized = re.sub(r"\btech\b", "technology", alias.casefold())
            tokens = re.findall(r"[a-z0-9]+", normalized)
            tokens = [token for token in tokens if token not in suffixes]
            if not tokens:
                continue
            if "ubnd" in tokens or "authorities" in tokens or "authority" in tokens:
                place = sorted(token for token in tokens if token not in government_words)
                keys.add("government:" + "-".join(place))
            else:
                keys.add("company:" + "-".join(tokens))
    return keys


def _merge_status(values: list[str]) -> str:
    return next((status for status in ("confirmed", "likely", "candidate", "unknown") if status in values), "unknown")


def _normalize_canonical_relationship_map(v2: BDV2AnalysisResult) -> None:
    """Normalize duplicate identities and prevent contract-scope role inflation."""

    relmap = v2.relationship_map
    if not relmap.entities:
        return

    # Merge only entities sharing a conservative normalized alias key.
    groups: list[list[EntityIdentity]] = []
    group_keys: list[set[str]] = []
    for entity in relmap.entities:
        keys = _entity_alias_keys(entity)
        match_index = next((index for index, known in enumerate(group_keys) if keys & known), None)
        if match_index is None:
            groups.append([entity])
            group_keys.append(set(keys))
        else:
            groups[match_index].append(entity)
            group_keys[match_index].update(keys)

    entity_remap: dict[str, str] = {}
    merged_entities: list[EntityIdentity] = []
    scope_order = {"local_entity": 0, "global_hq": 1, "regional_hq": 2, "project_company": 3, "unknown": 4}
    for group in groups:
        preferred = min(
            group,
            key=lambda item: (
                "/" in item.canonical_name,
                scope_order.get(item.organization_scope, 9),
                len(item.canonical_name),
            ),
        )
        preferred_id = (
            canonical_entity_id(preferred.canonical_name)
            if preferred.entity_id in {"org:unknown", "unknown", ""}
            else preferred.entity_id
        )
        for entity in group:
            entity_remap[entity.entity_id] = preferred_id
        merged_entities.append(preferred.model_copy(update={
            "entity_id": preferred_id,
            "aliases": list(dict.fromkeys(
                alias for entity in group
                for alias in [entity.canonical_name, *entity.aliases]
                if alias != preferred.canonical_name
            ))[:10],
            "status": _merge_status([entity.status for entity in group]),
            "evidence_labels": list(dict.fromkeys(label for entity in group for label in entity.evidence_labels))[:8],
            "source_urls": list(dict.fromkeys(url for entity in group for url in entity.source_urls))[:8],
            "source_dates": list(dict.fromkeys(value for entity in group for value in entity.source_dates))[:8],
            "legacy_entity_types": list(dict.fromkeys(value for entity in group for value in entity.legacy_entity_types))[:8],
        }))
    relmap.entities = merged_entities

    participation_groups: dict[tuple[str, str], list[ProjectParticipation]] = defaultdict(list)
    for item in relmap.participations:
        item.entity_id = entity_remap.get(item.entity_id, item.entity_id)
        participation_groups[(item.project_id, item.entity_id)].append(item)
    merged_participations: list[ProjectParticipation] = []
    for (_project_id, _entity_id), items in participation_groups.items():
        first = items[0]
        roles = list(dict.fromkeys(role for item in items for role in item.roles))
        role_statuses = {
            role: _merge_status([
                item.role_statuses.get(role, "unknown") for item in items if role in item.roles
            ])
            for role in roles
        }
        merged_participations.append(first.model_copy(update={
            "roles": roles,
            "role_statuses": role_statuses,
            "temporal_scope": "current" if any(item.temporal_scope == "current" for item in items) else first.temporal_scope,
            "evidence_labels": list(dict.fromkeys(label for item in items for label in item.evidence_labels))[:8],
            "source_urls": list(dict.fromkeys(url for item in items for url in item.source_urls))[:8],
            "source_dates": list(dict.fromkeys(value for item in items for value in item.source_dates))[:8],
        }))
    relmap.participations = merged_participations

    for relation in relmap.canonical_relationships:
        relation.from_entity_id = entity_remap.get(relation.from_entity_id, relation.from_entity_id)
        relation.to_entity_id = entity_remap.get(relation.to_entity_id, relation.to_entity_id)
    entity_lookup = {entity.entity_id: entity for entity in relmap.entities}
    for relation in relmap.canonical_relationships:
        if relation.relationship_type != "SUBSIDIARY_OF":
            continue
        source = entity_lookup.get(relation.from_entity_id)
        target = entity_lookup.get(relation.to_entity_id)
        if source and target and source.organization_scope in {"global_hq", "regional_hq"} and target.organization_scope == "local_entity":
            relation.from_entity_id, relation.to_entity_id = relation.to_entity_id, relation.from_entity_id
    relation_groups: dict[tuple[str, str, str], list[CanonicalRelationship]] = defaultdict(list)
    for relation in relmap.canonical_relationships:
        if relation.from_entity_id != relation.to_entity_id:
            relation_groups[(relation.from_entity_id, relation.to_entity_id, relation.relationship_type)].append(relation)
    relmap.canonical_relationships = [
        items[0].model_copy(update={
            "status": _merge_status([item.status for item in items]),
            "evidence_labels": list(dict.fromkeys(label for item in items for label in item.evidence_labels))[:8],
            "source_urls": list(dict.fromkeys(url for item in items for url in item.source_urls))[:8],
            "source_dates": list(dict.fromkeys(value for item in items for value in item.source_dates))[:8],
        })
        for items in relation_groups.values()
    ]

    for influence in relmap.decision_influences:
        influence.entity_id = entity_remap.get(influence.entity_id, influence.entity_id)
    influence_groups: dict[tuple[str, str], list[DecisionInfluence]] = defaultdict(list)
    for influence in relmap.decision_influences:
        influence_groups[(influence.entity_id, influence.domain)].append(influence)
    relmap.decision_influences = [
        items[0].model_copy(update={"status": _merge_status([item.status for item in items])})
        for items in influence_groups.values()
    ]

    # A bounded M&E / fit-out award supports an MEP contractor role, not an
    # EPC or general-contractor role unless the source explicitly says so.
    scoped_contractors: set[str] = set()
    for relation in relmap.canonical_relationships:
        text = f"{relation.relationship_basis} {relation.description}".casefold()
        scoped = any(token in text for token in ("m&e", "mep", "mechanical & electrical", "mechanical and electrical", "fit-out", "fit out"))
        explicit_epc_or_gc = bool(re.search(r"\bepc\b|general contractor|engineering[, /-]+procurement[, /-]+construction", text))
        if relation.relationship_type == "AWARDS_CONTRACT_TO" and scoped and not explicit_epc_or_gc:
            scoped_contractors.add(relation.to_entity_id)
    for item in relmap.participations:
        if item.entity_id not in scoped_contractors:
            continue
        old_roles = set(item.roles)
        if not old_roles.intersection({"EPC", "GENERAL_CONTRACTOR"}):
            continue
        roles = [role for role in item.roles if role not in {"EPC", "GENERAL_CONTRACTOR"}]
        roles.append("MEP_CONTRACTOR")
        statuses = [item.role_statuses.get(role, "unknown") for role in old_roles]
        item.roles = list(dict.fromkeys(roles))
        item.role_statuses = {
            **{role: status for role, status in item.role_statuses.items() if role in item.roles},
            "MEP_CONTRACTOR": _merge_status(statuses),
        }

    # Research discovery is broader than current-project participation. Keep
    # ecosystem leads in the source model, but demote them from the confirmed
    # decision map unless evidence ties them directly to this project.
    entity_lookup = {entity.entity_id: entity for entity in relmap.entities}
    candidate_entities: set[str] = set()
    person_title_pattern = re.compile(
        r"\b(deputy prime minister|prime minister|minister|vice minister|chairman|president|director general|mr|ms|dr)\b",
        re.IGNORECASE,
    )
    candidate_signals = (
        "intended user", "potential user", "representative universities",
        "named participant / collaborator", "user at forum", "participants / intended users",
        "authorized distributor", "distributor channel", "distributor pages",
        "authorized lines", "maintenance/warranty agent", "local channel",
        "event attendee", "meeting with", "delegation",
    )
    direct_project_signals = (
        "mou signatory", "memorandum of understanding", "mou", "co-development",
        "project owner", "developer", "contract award",
        "awarded contract", "site location", "environmental permit", "land agreement",
    )
    relation_text_by_entity: dict[str, list[str]] = defaultdict(list)
    for relation in relmap.canonical_relationships:
        text = " ".join([
            relation.relationship_basis,
            relation.description,
            *relation.evidence_labels,
        ]).casefold()
        relation_text_by_entity[relation.from_entity_id].append(text)
        relation_text_by_entity[relation.to_entity_id].append(text)
    for item in relmap.participations:
        entity = entity_lookup.get(item.entity_id)
        if not entity:
            continue
        evidence_text = " ".join([
            entity.canonical_name,
            *entity.evidence_labels,
            *item.evidence_labels,
            *relation_text_by_entity.get(item.entity_id, []),
        ]).casefold()
        looks_like_person = bool(person_title_pattern.search(entity.canonical_name))
        broad_ecosystem_only = (
            any(signal in evidence_text for signal in candidate_signals)
            and not any(signal in evidence_text for signal in direct_project_signals)
        )
        if looks_like_person or broad_ecosystem_only:
            candidate_entities.add(item.entity_id)
            item.temporal_scope = "candidate"
            item.role_statuses = {role: "candidate" for role in item.roles}

    for relation in relmap.canonical_relationships:
        text = " ".join([
            relation.relationship_basis,
            relation.description,
            *relation.evidence_labels,
        ]).casefold()
        meeting_only_investment = (
            relation.relationship_type == "INVESTS_IN"
            and any(token in text for token in ("meeting", "delegation", "political engagement", "facilitation"))
            and not any(token in text for token in ("equity", "shareholding", "capital contribution", "investment amount", "funding"))
        )
        ecosystem_relation = (
            relation.from_entity_id in candidate_entities
            or relation.to_entity_id in candidate_entities
            or any(token in text for token in ("intended partners", "intended users", "distributor channel", "authorized distributor"))
        )
        if meeting_only_investment or ecosystem_relation:
            relation.status = "candidate"
            relation.temporal_scope = "candidate"

    confirmed_roles = {
        role for item in relmap.participations if item.temporal_scope == "current"
        for role in item.roles if item.role_statuses.get(role) in {"confirmed", "likely"}
    }
    gap_role_tokens = {
        "investor": "INVESTOR", "project owner": "PROJECT_OWNER", "owner": "PROJECT_OWNER",
        "epc": "EPC", "general contractor": "GENERAL_CONTRACTOR", "operator": "OPERATOR",
        "design": "ENGINEERING_CONSULTANT", "engineering": "ENGINEERING_CONSULTANT",
    }
    relmap.research_gaps = [
        gap for gap in relmap.research_gaps
        if not any(token in gap.casefold() and role in confirmed_roles for token, role in gap_role_tokens.items())
    ][:12]


def _classify_structure(v2: BDV2AnalysisResult) -> tuple[str, str, str, list[str]]:
    relmap = v2.relationship_map
    roles_by_entity = {item.entity_id: set(item.roles) for item in relmap.participations}
    all_roles = {role for roles in roles_by_entity.values() for role in roles}
    epc_entities = {entity_id for entity_id, roles in roles_by_entity.items() if "EPC" in roles}
    entities = {entity.entity_id: entity for entity in relmap.entities}
    investor_present = any(
        "INVESTOR" in roles
        and entities.get(entity_id)
        and entities[entity_id].organization_type == "FINANCIAL_INSTITUTION"
        for entity_id, roles in roles_by_entity.items()
    )
    epc_invests = any(
        relation.from_entity_id in epc_entities
        and relation.relationship_type in {"INVESTS_IN", "OWNS"}
        and relation.status in {"confirmed", "likely"}
        and relation.temporal_scope == "current"
        for relation in relmap.canonical_relationships
    )
    epc_contract = bool(epc_entities) and any(
        relation.relationship_type in {"EPC_CONTRACT", "AWARDS_CONTRACT_TO"}
        and relation.status in {"confirmed", "likely"}
        and relation.temporal_scope == "current"
        for relation in relmap.canonical_relationships
    )
    if epc_invests:
        pattern = "S4" if investor_present else "S3"
    elif investor_present:
        pattern = "S2"
    elif "PROJECT_OWNER" in all_roles and epc_contract:
        pattern = "S1"
    elif relmap.entities:
        pattern = "OTHER"
    else:
        pattern = "UNKNOWN"
    labels = {
        "S1": "Owner-funded / EPC delivery",
        "S2": "Owner + financial investor",
        "S3": "EPC investment participation",
        "S4": "EPC + financial investor participation",
        "OTHER": "Other confirmed project structure",
        "UNKNOWN": "Not confirmed",
    }
    evidence = list(dict.fromkeys(
        label for entity in relmap.entities for label in entity.evidence_labels
    ))[:12]
    relmap.structure_pattern = pattern
    status = "confirmed" if pattern in {"S1", "S2", "S3", "S4"} else "partial" if pattern == "OTHER" else "unknown"
    return pattern, labels[pattern], status, evidence


def _structure(v2: BDV2AnalysisResult, text: str) -> tuple[str | None, str, str, list[str]]:
    del text  # Pattern classification never reads free-text seed content.
    _ensure_canonical_relationship_map(v2)
    return _classify_structure(v2)


def _stage(v2: BDV2AnalysisResult) -> tuple[str | None, str]:
    value = v2.context.business_stage.claim
    if value in {"사업기획", "타당성 조사"}: return "ST1", "초기 기획"
    if value in {"Master Plan", "설계 - SD (기본)", "설계 - DD (기본)", "설계 - CD (기본)"}: return "ST2", "설계 및 발주"
    if value in {"건설 인허가", "시공"}: return "ST3", "시공"
    if value in {"운영 인허가", "프로젝트 종료"}: return "ST4", "준공 및 영업"
    return None, "Unknown"


def _canonical_v3_relationship_map(v2: BDV2AnalysisResult) -> V3RelationshipMap:
    _ensure_canonical_relationship_map(v2)
    _normalize_canonical_relationship_map(v2)
    pattern, pattern_name, _, evidence = _classify_structure(v2)
    relmap = v2.relationship_map
    entities = {entity.entity_id: entity for entity in relmap.entities}
    participations = {item.entity_id: item for item in relmap.participations}
    visible_statuses = {"confirmed", "likely"}
    corporate_relations = [
        relation for relation in relmap.canonical_relationships
        if relation.relationship_type in CORPORATE_RELATIONSHIPS
        and relation.status in visible_statuses
    ]
    corporate_entity_ids = {
        entity_id
        for relation in corporate_relations
        for entity_id in (relation.from_entity_id, relation.to_entity_id)
        if entity_id in entities and entities[entity_id].status in visible_statuses
    }
    visible_project_entity_ids = {
        item.entity_id for item in relmap.participations
        if item.entity_id in entities
        and item.temporal_scope == "current"
        and any(item.role_statuses.get(role, "unknown") in visible_statuses for role in item.roles)
    }
    # One organization should appear once. If a corporate entity also has a
    # current project role, its project node carries both that role and the
    # corporate hierarchy edge.
    corporate_entity_ids -= visible_project_entity_ids

    def readable(value: str) -> str:
        special = {"PM_CM": "PM / CM", "EPC": "EPC", "MEP_CONTRACTOR": "MEP Contractor"}
        return special.get(value, value.replace("_", " ").title())

    def strongest(statuses: list[str]) -> str:
        for status in ("confirmed", "likely", "candidate", "unknown"):
            if status in statuses:
                return status
        return "unknown"

    def relationship_label(relation: CanonicalRelationship) -> str:
        text = f"{relation.relationship_basis} {relation.description}".casefold()
        if relation.relationship_type == "AWARDS_CONTRACT_TO":
            if any(token in text for token in ("m&e", "mep", "mechanical & electrical", "mechanical and electrical", "fit-out", "fit out")):
                return "M&E / Fit-out 계약"
            return "공사·용역 계약"
        if relation.relationship_type == "CO_DEVELOPMENT" and "mou" in text:
            return "공동 개발 · MOU"
        labels = {
            "SUBSIDIARY_OF": "현지 자회사",
            "PARENT_OF": "모회사",
            "LOCAL_ARM_OF": "현지 법인",
            "EPC_CONTRACT": "EPC 계약",
            "DESIGN_CONTRACT": "설계 계약",
            "SUPPLY_CONTRACT": "공급 계약",
            "MOU": "MOU",
            "CO_DEVELOPMENT": "공동 개발",
            "INVESTS_IN": "투자",
            "OWNS": "소유",
            "HOSTS": "사업 부지 제공",
            "REGULATES": "인허가·감독",
            "APPROVES": "승인",
        }
        return labels.get(relation.relationship_type, readable(relation.relationship_type))

    nodes: list[V3StructureNode] = []
    corporate_node_ids: dict[str, str] = {}
    project_node_ids: dict[str, str] = {}
    position_cycle = ("LEFT", "CENTER", "RIGHT")

    for index, entity_id in enumerate(sorted(
        corporate_entity_ids,
        key=lambda item: ({"global_hq": 0, "regional_hq": 1, "local_entity": 2, "project_company": 3}.get(entities[item].organization_scope, 4), entities[item].canonical_name),
    )):
        entity = entities[entity_id]
        node_id = f"corporate:{entity_id}"
        corporate_node_ids[entity_id] = node_id
        corporate_role = "Parent Company" if entity.organization_scope in {"global_hq", "regional_hq"} else "Local Entity"
        nodes.append(V3StructureNode(
            node_id=node_id,
            entity_id=entity_id,
            role=corporate_role,
            roles=[corporate_role],
            company=entity.canonical_name,
            organization_type=entity.organization_type,
            organization_scope=entity.organization_scope,
            layer_type="corporate",
            temporal_scope="current",
            layer=1 + index // 3,
            position=position_cycle[index % 3],
            required=False,
            status=entity.status,
            evidence=entity.evidence_labels,
        ))

    project_participations = [
        item for item in relmap.participations
        if item.entity_id in entities
        and entities[item.entity_id].status in visible_statuses
        and item.temporal_scope == "current"
        and item.roles
        and any(item.role_statuses.get(role, "unknown") in visible_statuses for role in item.roles)
        and not (
            set(item.roles) == {"OTHER"}
            and (
                entities[item.entity_id].organization_scope == "project_company"
                or "listed company" in entities[item.entity_id].canonical_name.casefold()
                or "ticker" in entities[item.entity_id].canonical_name.casefold()
            )
        )
    ]
    project_start_layer = 1 + (max((node.layer for node in nodes), default=0) if nodes else 0)
    role_order = {
        role: index for index, role in enumerate((
            "PROJECT_OWNER", "END_CLIENT", "INVESTOR", "SPONSOR", "DEVELOPER", "HOST",
            "CO_DEVELOPMENT_PARTNER", "STRATEGIC_PARTNER", "ARCHITECT",
            "ENGINEERING_CONSULTANT", "PM_CM", "EPC", "GENERAL_CONTRACTOR",
            "MEP_CONTRACTOR", "TECHNOLOGY_PROVIDER", "SOLUTION_PROVIDER",
            "EQUIPMENT_SUPPLIER", "VENDOR", "OPERATOR", "FACILITY_MANAGER",
            "MAINTENANCE_PROVIDER", "GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY",
            "INDUSTRIAL_PARK", "LANDLORD", "OTHER",
        ))
    }
    project_participations.sort(key=lambda item: min(role_order.get(role, 999) for role in item.roles))
    for index, participation in enumerate(project_participations):
        entity = entities[participation.entity_id]
        roles = sorted(dict.fromkeys(participation.roles), key=lambda role: role_order.get(role, 999))
        node_id = f"project:{entity.entity_id}"
        project_node_ids[entity.entity_id] = node_id
        role_statuses = {role: participation.role_statuses.get(role, "unknown") for role in roles}
        nodes.append(V3StructureNode(
            node_id=node_id,
            entity_id=entity.entity_id,
            role=" · ".join(readable(role) for role in roles),
            roles=roles,
            company=entity.canonical_name,
            organization_type=entity.organization_type,
            organization_scope=entity.organization_scope,
            layer_type="project",
            role_statuses=role_statuses,
            temporal_scope=participation.temporal_scope,
            layer=project_start_layer + index // 3,
            position=position_cycle[index % 3],
            required=False,
            status=strongest(list(role_statuses.values())),
            evidence=list(dict.fromkeys([*entity.evidence_labels, *participation.evidence_labels])),
        ))

    relations: list[V3StructureRelation] = []
    for relation in relmap.canonical_relationships:
        if relation.status not in visible_statuses:
            continue
        if relation.relationship_type in CORPORATE_RELATIONSHIPS:
            from_node = corporate_node_ids.get(relation.from_entity_id) or project_node_ids.get(relation.from_entity_id)
            to_node = corporate_node_ids.get(relation.to_entity_id) or project_node_ids.get(relation.to_entity_id)
        else:
            from_node = project_node_ids.get(relation.from_entity_id)
            to_node = project_node_ids.get(relation.to_entity_id)
        if not from_node or not to_node or from_node == to_node:
            continue
        label = relationship_label(relation)
        relations.append(V3StructureRelation(
            from_node=from_node,
            to_node=to_node,
            relation_type=relation.relationship_type,
            line_type="SOLID" if relation.status == "confirmed" else "DASHED",
            direction="FORWARD",
            label=label,
            relationship_basis=relation.relationship_basis,
            description=relation.description,
            temporal_scope=relation.temporal_scope,
            status=relation.status,
            evidence=relation.evidence_labels,
        ))

    supported_count = sum(node.status in visible_statuses for node in nodes)
    map_status = "unconfirmed" if not supported_count else "partial" if relmap.research_gaps or pattern in {"OTHER", "UNKNOWN"} else "confirmed"
    return V3RelationshipMap(
        structure_id=pattern,
        structure_name=pattern_name,
        status=map_status,
        evidence=evidence,
        nodes=nodes,
        relations=relations,
        research_gaps=relmap.research_gaps,
    )


def build_v3_result(v2: BDV2AnalysisResult, seed: str, extracted: str = "") -> BDV3AnalysisResult:
    _ensure_canonical_relationship_map(v2)
    _normalize_canonical_relationship_map(v2)
    result = _build_v3_result_legacy(v2, seed, extracted)
    result.relationship_map = _canonical_v3_relationship_map(v2)
    _reconcile_owner_target(result)
    _reconcile_stage_questions(result)
    result.stakeholder_unknowns = list(dict.fromkeys([
        *result.stakeholder_unknowns,
        *v2.relationship_map.research_gaps,
    ]))[:12]
    return result


def _reconcile_owner_target(result: BDV3AnalysisResult) -> None:
    """Prefer the supported local project owner as the first external target."""

    owner_nodes = [
        node for node in result.relationship_map.nodes
        if node.layer_type == "project"
        and "PROJECT_OWNER" in node.roles
        and node.status in {"confirmed", "likely"}
        and node.company
    ]
    if not owner_nodes:
        return
    owner = min(
        owner_nodes,
        key=lambda node: (
            node.organization_scope != "local_entity",
            node.organization_scope == "global_hq",
            node.company,
        ),
    )
    result.v2_snapshot.project_intelligence.owner_summary = owner.company
    strength = "strong" if owner.status == "confirmed" else "medium"
    target = V3StakeholderTarget(
        stakeholder_type="PROJECT_OWNER",
        role="Project Owner · 현지 사업 주체" if owner.organization_scope == "local_entity" else "Project Owner",
        company=owner.company,
        target_function=["Investment / Project Management", "Local Procurement"],
        priority=1,
        evidence_strength=strength,
        reason="현재 프로젝트의 직접 사업 주체로 확인되어 투자·발주 구조와 현지 의사결정 경로를 가장 먼저 확인할 대상입니다.",
        evidence=owner.evidence[:8],
    )
    others = [item for item in result.priority_1 if item.stakeholder_type != "PROJECT_OWNER"]
    result.priority_1 = [target, *others][:3]


def _reconcile_stage_questions(result: BDV3AnalysisResult) -> None:
    """Ask about remaining commercial openings once a scoped contractor is known."""

    stage = result.project_stage.value
    confirmed_roles = {
        role for node in result.relationship_map.nodes
        if node.status in {"confirmed", "likely"}
        for role in node.roles
    }
    scoped_execution_partner = bool(confirmed_roles.intersection({"MEP_CONTRACTOR", "GENERAL_CONTRACTOR"}))
    full_epc_confirmed = "EPC" in confirmed_roles
    if stage not in {"건설 인허가", "시공"} or not scoped_execution_partner or full_epc_confirmed:
        return
    result.questions_to_ask = [
        V3Question(
            question="현재 M&E와 Fit-out 외에 아직 발주되지 않았거나 공급사가 정해지지 않은 설비는 무엇입니까?",
            information_goal="지금 참여할 수 있는 공급 범위 확인",
            reason="이미 계약된 공사 범위와 아직 참여 가능한 패키지를 구분합니다.",
            converts="unknown",
        ),
        V3Question(
            question="남은 설비의 사양과 공급사 선정은 프로젝트 오너와 계약사 중 어느 조직이 주도합니까?",
            information_goal="실제 기술·구매 의사결정자 확인",
            reason="남은 패키지의 실제 접촉 대상과 승인 경로를 정합니다.",
            converts="unknown",
        ),
        V3Question(
            question="생산 개시 전까지 예정된 주요 발주 일정과 공급사 등록 절차는 어떻게 됩니까?",
            information_goal="참여 시점과 진입 절차 확인",
            reason="제안 준비 시점과 공급사 등록에 필요한 조치를 정합니다.",
            converts="unknown",
        ),
        V3Question(
            question="초기 가동 이후 생산라인 증설이나 자동화·에너지·시설 운영 관련 추가 투자 계획이 있습니까?",
            information_goal="현재 공사 이후의 신규 투자 기회 확인",
            reason="현재 패키지가 닫혀 있어도 후속 증설과 운영 투자 기회를 찾습니다.",
            converts="inference",
        ),
    ]


def _build_v3_result_legacy(v2: BDV2AnalysisResult, seed: str, extracted: str = "") -> BDV3AnalysisResult:
    rules = _read_rulebook()
    combined = f"{seed}\n{extracted}".lower()
    structure_id, structure_name, structure_status, structure_evidence = _structure(v2, combined)
    stage_id, stage_group = _stage(v2)
    actors = v2.relationship_map.actors
    role_aliases = {"PROJECT_OWNER": ("owner", "end client"), "EPC": ("epc",), "DESIGN": ("design", "architect", "engineering"), "INVESTOR": ("investor", "capital", "pef")}
    companies: dict[str, tuple[str, str, list[str]]] = {}
    for node_id, aliases in role_aliases.items():
        actor = next((a for a in actors if any(k in (a.role + " " + a.organization).lower() for k in aliases) and a.organization), None)
        if actor:
            companies[node_id] = (actor.organization, _status(actor.credibility), actor.evidence_labels)
    nodes, relations = [], []
    if structure_id:
        for row in rules["1. Structure Node_Rule"]:
            if row.get("Structure_ID") != structure_id: continue
            company, status, evidence = companies.get(row["Node_ID"], (None, "unknown", []))
            nodes.append(V3StructureNode(node_id=row["Node_ID"], role=row["Stakeholder"], company=company, layer=int(float(row["Layer"])), position=row["Position"], required=row["Required"] == "Y", status=status, evidence=evidence))
        known_ids = {n.node_id for n in nodes}
        for row in rules["1. Structure Relation_Rule"]:
            if row.get("Structure_ID") == structure_id and row["From_Node"] in known_ids and row["To_Node"] in known_ids:
                a, b = next(n for n in nodes if n.node_id == row["From_Node"]), next(n for n in nodes if n.node_id == row["To_Node"])
                status = "confirmed" if a.status == b.status == "confirmed" else "inferred" if a.status != "unknown" and b.status != "unknown" else "unknown"
                relations.append(V3StructureRelation(from_node=row["From_Node"], to_node=row["To_Node"], relation_type=row["Relation_Type"], line_type=row["Line_Type"], direction=row["Direction"], label=row["Label"], status=status, evidence=list(dict.fromkeys(a.evidence + b.evidence))))

    # Entity-first fallback and enrichment: S1-S4 is a classification result,
    # never a prerequisite for preserving supported current-project actors.
    current_project_text = " ".join([
        v2.opportunity_title,
        v2.executive_summary,
        *[item.claim for item in v2.project_intelligence.current_project_facts],
    ]).casefold()
    decision_role_tokens = (
        "owner", "end client", "host", "partner", "investor", "sponsor",
        "developer", "epc", "contractor", "construction", "design", "engineering",
        "architect", "pm / cm", "operator", "government", "authority",
        "industrial park", "landlord",
    )

    def is_current_project_actor(actor) -> bool:
        if actor.organization == "UNKNOWN" or actor.temporal_scope != "current":
            return False
        if actor.actor_status not in {"confirmed", "likely"}:
            return False
        role_text = actor.role.casefold()
        organization_key = actor.organization.casefold().split("(", 1)[0].strip()
        directly_mentioned = bool(
            len(organization_key) >= 4
            and re.search(
                rf"(?<!\w){re.escape(organization_key)}(?!\w)", current_project_text
            )
        )
        decision_role = any(token in role_text for token in decision_role_tokens)
        return directly_mentioned or decision_role

    supported_actors = [actor for actor in actors if is_current_project_actor(actor)]
    critical_unknowns = [
        actor for actor in actors
        if actor.organization == "UNKNOWN"
        and any(token in actor.role.casefold() for token in ("epc", "architect", "design", "operator"))
    ]
    actor_to_node: dict[str, str] = {}
    company_to_node = {
        (node.company or "").casefold(): node.node_id for node in nodes if node.company
    }
    for actor in supported_actors:
        existing_id = company_to_node.get(actor.organization.casefold())
        if existing_id:
            actor_to_node[actor.actor_id] = existing_id
            continue
        layer = 1 if any(token in actor.role.casefold() for token in ("owner", "end client")) else 2
        same_layer_count = sum(node.layer == layer for node in nodes)
        position = ("LEFT", "CENTER", "RIGHT")[same_layer_count % 3]
        display_role = actor.role
        nodes.append(V3StructureNode(
            node_id=actor.actor_id,
            role=display_role,
            company=actor.organization,
            layer=layer,
            position=position,
            required=False,
            status=_status(actor.credibility),
            evidence=actor.evidence_labels,
        ))
        actor_to_node[actor.actor_id] = actor.actor_id
    for actor in critical_unknowns:
        if actor.actor_id in {node.node_id for node in nodes}:
            continue
        same_layer_count = sum(node.layer == 3 for node in nodes)
        nodes.append(V3StructureNode(
            node_id=actor.actor_id,
            role=actor.role,
            company=None,
            layer=3,
            position=("LEFT", "CENTER", "RIGHT")[same_layer_count % 3],
            required=True,
            status="unknown",
            evidence=[],
        ))
        actor_to_node[actor.actor_id] = actor.actor_id

    required_gap_roles = {
        "EPC": ("epc",),
        "Design / Engineering Consultant": ("architect", "design", "engineering"),
        "Operator": ("operator",),
    }
    for role, aliases in required_gap_roles.items():
        if any(any(alias in node.role.casefold() for alias in aliases) for node in nodes):
            continue
        node_id = "unknown_" + role.casefold().replace(" / ", "_").replace(" ", "_")
        same_layer_count = sum(node.layer == 3 for node in nodes)
        nodes.append(V3StructureNode(
            node_id=node_id,
            role=role,
            company=None,
            layer=3,
            position=("LEFT", "CENTER", "RIGHT")[same_layer_count % 3],
            required=True,
            status="unknown",
            evidence=[],
        ))

    known_relation_keys = {(item.from_node, item.to_node, item.label) for item in relations}
    known_node_ids = {node.node_id for node in nodes}
    for relation in v2.relationship_map.relationships:
        from_node = actor_to_node.get(relation.from_actor_id, relation.from_actor_id)
        to_node = actor_to_node.get(relation.to_actor_id, relation.to_actor_id)
        if from_node not in known_node_ids or to_node not in known_node_ids or from_node == to_node:
            continue
        relation_label = relation.relationship_type
        relation_evidence_text = " ".join(relation.evidence_labels).casefold()
        if "mou" in relation_evidence_text and "mou" in current_project_text:
            relation_label = "MoU / Joint roadmap development"
        key = (from_node, to_node, relation_label)
        if key in known_relation_keys:
            continue
        relation_status = _status(relation.credibility)
        relations.append(V3StructureRelation(
            from_node=from_node,
            to_node=to_node,
            relation_type=relation_label,
            line_type="SOLID" if relation_status == "confirmed" else "DASHED",
            direction="FORWARD",
            label=relation_label,
            status=relation_status,
            evidence=relation.evidence_labels,
        ))
        known_relation_keys.add(key)

    supported_node_count = sum(
        1 for node in nodes if node.status in {"confirmed", "inferred"} and node.company
    )
    unknown_node_count = sum(1 for node in nodes if node.status == "unknown" or not node.company)
    map_status = (
        "unconfirmed" if supported_node_count == 0
        else "partial" if structure_id is None or unknown_node_count
        else "confirmed"
    )
    relationship = V3RelationshipMap(
        structure_id=structure_id,
        structure_name=structure_name if structure_id else "Partial / Unclassified",
        status=map_status,
        evidence=list(dict.fromkeys(
            structure_evidence
            + [label for actor in supported_actors for label in actor.evidence_labels]
        )),
        nodes=nodes,
        relations=relations,
    )

    priorities: dict[str, tuple[int, str]] = {}
    target_meta: dict[str, tuple[str, str]] = {}
    if structure_id:
        for row in rules["2. Project Structure_Rule"]:
            row_priority = _priority(row.get("Priority", ""))
            if row.get("Structure_ID") == structure_id and row.get("Include") == "Y" and row_priority is not None:
                key = row["Stakeholder"] + ":" + row.get("Location", "-")
                priorities[key] = (row_priority, row["Rule_Description"])
                target_meta[key] = (row["Stakeholder"], row.get("Location", "-"))
    if stage_id in {"ST1", "ST2"}:
        for row in rules["2. Project Stage_Rule"]:
            if row.get("Stage_ID") == stage_id and row.get("Include") == "Y":
                key = row["Stakeholder"] + ":" + row.get("Location", "-")
                candidate = (_priority(row["Priority"]), row["Rule_Description"])
                if key not in priorities or candidate[0] < priorities[key][0]: priorities[key] = candidate
                target_meta[key] = (row["Stakeholder"], row.get("Location", "-"))
    targets, unknowns = [], []
    for key, (priority, reason) in priorities.items():
        stakeholder, location = target_meta[key]
        node_id = "PROJECT_OWNER" if stakeholder == "Project Owner" else "DESIGN" if stakeholder == "Design/Engineering" else stakeholder.upper()
        company, status, evidence = companies.get(node_id, (None, "unknown", []))
        role = stakeholder + (f" — {location}" if location != "-" else "")
        functions = ["Investment / Project Management"] if stakeholder == "Project Owner" else ["Project Management / Procurement"] if stakeholder == "EPC" else ["Engineering / Specification"] if stakeholder == "Design/Engineering" else []
        targets.append(V3StakeholderTarget(stakeholder_type=node_id, role=role, company=company, target_function=functions, priority=priority, evidence_strength="strong" if status == "confirmed" else "medium" if status == "inferred" else "weak", reason=reason, evidence=evidence))
        if not company: unknowns.append(f"{role} company not confirmed")

    building = v2.context.building_type
    facts = {"Building_Type": building.claim, "Project_Stage": stage_group}
    facility = "공장" if any(k in combined for k in ("factory", "plant", "공장", "manufactur")) else "오피스동" if any(k in combined for k in ("office", "오피스")) else "기숙사동" if any(k in combined for k in ("dorm", "기숙사")) else None
    if facility: facts["Facility_Type"] = facility
    needs = [V3ProjectFact(value=x.claim, status=_status(x.credibility), evidence=x.source_labels) for x in v2.context.customer_needs]
    need_values = []
    for need in v2.context.customer_needs:
        n = need.claim.lower()
        if any(k in n for k in ("energy", "opex", "전력", "운영비")): need_values.append("Energy & OPEX")
        if any(k in n for k in ("digital", "dx", "smart", "스마트", "인력")): need_values.append("Digital Transformation")
        if any(k in n for k in ("regulation", "environment", "climate", "규제", "기후")): need_values.append("Regulation & Environment")
        if any(k in n for k in ("fast", "scal", "확장", "조기")): need_values.append("Fast-Track & Scalability")
    counts, matched = Counter(), defaultdict(list)
    for row in rules["3. Product Mapping_Rule"]:
        if row.get("Include") == "Y" and (facts.get(row["Dimension"]) == row["Condition"] or (row["Dimension"] == "Customer_Need" and row["Condition"] in need_values)):
            counts[row["Product"]] += 1; matched[row["Product"]].append(row["Rule_ID"] + " " + row["Condition"])
    if building.claim == "스마트화":
        for row in rules["3. Product Signal_Rule"]:
            if row.get("Include") == "Y" and row["Signal"] == "스마트화": counts[row["Product"]] += 1; matched[row["Product"]].append(row["Signal_ID"] + " 스마트화")
    context_terms = {"IoT 솔루션": ("iot", "sensor", "monitor", "automation", "스마트"), "러기드/탭": ("workforce", "field", "현장", "작업자"), "중앙공조": ("cleanroom", "energy", "temperature", "humidity", "공조"), "SAC": ("hvac", "air condition", "냉방"), "사이니지": ("display", "dashboard", "visual", "사이니지")}
    bonuses = {p: sum(1 for term in context_terms.get(p, ()) if term in combined) for p in counts}
    ranked = sorted(counts, key=lambda p: (-counts[p], -bonuses[p], p))[:3] if v2.bd_decision.decision != "closed" else []
    products = []
    for rank, product in enumerate(ranked, 1):
        evidence = [term for term in context_terms.get(product, ()) if term in combined]
        strength = "strong" if evidence and counts[product] >= 2 else "medium" if counts[product] >= 2 else "weak"
        need = need_values[0] if need_values else (v2.context.customer_needs[0].claim if v2.context.customer_needs else "Need not confirmed")
        products.append(V3ProductRecommendation(rank=rank, product=product, evidence_strength=strength, why=f"Excel 규칙 {counts[product]}개가 일치" + (f"하고 기사 맥락({', '.join(evidence[:3])})이 보강합니다." if evidence else "합니다."), customer_need=need, suggested_scenario=f"{stage_group} 단계에서 {need} 과제를 기준으로 {product} 적용 범위와 미확정 Spec을 함께 확인합니다.", excel_match_count=counts[product], matched_rules=matched[product], context_evidence=evidence))
    questions = []
    if stage_id is None: questions.append(V3Question(question="현재 프로젝트의 공식 단계와 다음 의사결정 일정은 언제입니까?", information_goal="사업단계 확정", reason="접촉 대상과 Spec-in 가능 시점을 바꿉니다.", converts="unknown"))
    if structure_id is None: questions.append(V3Question(question="투자 주체와 EPC의 투자·지분 참여 관계는 어떻게 구성되어 있습니까?", information_goal="사업구도 확정", reason="EPC의 P1 여부를 결정합니다.", converts="unknown"))
    if not companies.get("DESIGN"): questions.append(V3Question(question="설계·Engineering 파트너가 선정되었으며 현재 Spec에 영향력을 행사하고 있습니까?", information_goal="설계 영향 주체 확인", reason="기술 사양 접점과 P2 타깃을 확정합니다.", converts="unknown"))
    if not companies.get("EPC"): questions.append(V3Question(question="EPC는 선정되었고 시공만 담당합니까, 투자 의사결정에도 참여합니까?", information_goal="EPC 역할 확인", reason="EPC의 접촉 Priority를 결정합니다.", converts="unknown"))
    questions.extend([V3Question(question="현재 확정된 제품 사양과 아직 결정되지 않은 공급 범위는 무엇입니까?", information_goal="사양 반영 가능 범위", reason="제안 가능한 제품과 납품 시점을 확정합니다.", converts="inference"), V3Question(question="공급사 후보 목록과 최종 기술·구매 승인권자는 누구입니까?", information_goal="실제 의사결정권자", reason="접근 경로와 경쟁 구도를 확인합니다.", converts="unknown")])
    status = v2.bd_decision.decision
    if status == "closed": targets, questions, products = [], [], []
    return BDV3AnalysisResult(opportunity_title=v2.opportunity_title, executive_summary=v2.executive_summary, status=status, status_reason=v2.bd_decision.rationale, building_type=V3ProjectFact(value=building.claim, status=_status(building.credibility), evidence=building.source_labels), project_stage=V3ProjectFact(value=v2.context.business_stage.claim, status=_status(v2.context.business_stage.credibility), evidence=v2.context.business_stage.source_labels), customer_needs=needs, relationship_map=relationship, priority_1=[x for x in targets if x.priority == 1], priority_2=[x for x in targets if x.priority == 2], priority_3=[x for x in targets if x.priority == 3], stakeholder_unknowns=unknowns, questions_to_ask=questions[:8], talking_points=[V3TalkingPoint(product=p.product, scenario=p.suggested_scenario, customer_need=p.customer_need, project_stage=stage_group) for p in products], customer_need_top_signals=needs[:3], product_top3=products, decision_trace_excel="중복 Match Count로 Excel 후보군과 기본 Priority를 결정했습니다.", decision_trace_ai="기사·입력 텍스트의 직접 맥락은 Excel 후보군 안에서만 동률과 우선순위를 보정했습니다.", evidence=v2.evidence, source_summary=v2.source_summary, limitations=v2.limitations, v2_snapshot=v2)
