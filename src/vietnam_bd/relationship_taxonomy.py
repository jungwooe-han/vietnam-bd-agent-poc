from __future__ import annotations

import re
from dataclasses import dataclass


ORGANIZATION_TYPES = (
    "PUBLIC_INSTITUTION",
    "PRIVATE_COMPANY",
    "STATE_OWNED_ENTERPRISE",
    "FINANCIAL_INSTITUTION",
    "INDUSTRIAL_PARK_DEVELOPER",
    "ENGINEERING_COMPANY",
    "CONSTRUCTION_COMPANY",
    "TECHNOLOGY_COMPANY",
    "RESEARCH_INSTITUTION",
    "OTHER",
    "UNKNOWN",
)

PROJECT_ROLES = (
    "PROJECT_OWNER", "END_CLIENT", "INVESTOR", "SPONSOR",
    "DEVELOPER", "HOST", "CO_DEVELOPMENT_PARTNER", "STRATEGIC_PARTNER",
    "ARCHITECT", "ENGINEERING_CONSULTANT", "PM_CM", "EPC",
    "GENERAL_CONTRACTOR", "MEP_CONTRACTOR", "TECHNOLOGY_PROVIDER",
    "SOLUTION_PROVIDER", "EQUIPMENT_SUPPLIER", "VENDOR", "OPERATOR",
    "FACILITY_MANAGER", "MAINTENANCE_PROVIDER", "GOVERNMENT_PARTNER",
    "REGULATORY_AUTHORITY", "INDUSTRIAL_PARK", "LANDLORD", "OTHER",
)

DECISION_DOMAINS = (
    "PROJECT_GOVERNANCE", "BUDGET_INVESTMENT", "SITE_LAND", "DESIGN",
    "TECHNICAL_SPECIFICATION", "EQUIPMENT_SELECTION", "VENDOR_SELECTION",
    "PROCUREMENT", "CONSTRUCTION", "OPERATION", "REGULATORY_APPROVAL",
    "PARTNERSHIP_APPROVAL",
)

RELATIONSHIP_TYPES = (
    "OWNS", "INVESTS_IN", "SPONSORS", "AWARDS_CONTRACT_TO", "EPC_CONTRACT",
    "DESIGN_CONTRACT", "SUPPLY_CONTRACT", "OM_CONTRACT", "CO_DEVELOPMENT",
    "STRATEGIC_PARTNERSHIP", "MOU", "JOINT_VENTURE", "TECHNOLOGY_PROVISION",
    "EQUIPMENT_SUPPLY", "SOLUTION_PROVISION", "HOSTS", "PROVIDES_LAND",
    "LEASES_TO", "REGULATES", "APPROVES", "SUPERVISES", "SUBSIDIARY_OF",
    "LOCAL_ARM_OF", "PARENT_OF", "LOCATED_IN", "OTHER",
)

CORPORATE_RELATIONSHIPS = {"SUBSIDIARY_OF", "LOCAL_ARM_OF", "PARENT_OF"}


@dataclass(frozen=True)
class LegacyEntityMapping:
    organization_type: str
    roles: tuple[str, ...] = ()
    organization_scope: str = "unknown"


LEGACY_ENTITY_MAPPINGS: dict[str, LegacyEntityMapping] = {
    "company": LegacyEntityMapping("PRIVATE_COMPANY", ("OTHER",)),
    "project": LegacyEntityMapping("OTHER", ("OTHER",), "project_company"),
    "owner": LegacyEntityMapping("PRIVATE_COMPANY", ("PROJECT_OWNER",)),
    "end_client": LegacyEntityMapping("PRIVATE_COMPANY", ("END_CLIENT",)),
    "investor": LegacyEntityMapping("FINANCIAL_INSTITUTION", ("INVESTOR",)),
    "sponsor": LegacyEntityMapping("PRIVATE_COMPANY", ("SPONSOR",)),
    "developer": LegacyEntityMapping("PRIVATE_COMPANY", ("DEVELOPER",)),
    "host": LegacyEntityMapping("OTHER", ("HOST",)),
    "co_development_partner": LegacyEntityMapping("PRIVATE_COMPANY", ("CO_DEVELOPMENT_PARTNER",)),
    "strategic_partner": LegacyEntityMapping("PRIVATE_COMPANY", ("STRATEGIC_PARTNER",)),
    "technology_partner": LegacyEntityMapping(
        "TECHNOLOGY_COMPANY",
        ("TECHNOLOGY_PROVIDER", "SOLUTION_PROVIDER", "EQUIPMENT_SUPPLIER"),
    ),
    "solution_partner": LegacyEntityMapping("TECHNOLOGY_COMPANY", ("SOLUTION_PROVIDER",)),
    "hq": LegacyEntityMapping("PRIVATE_COMPANY", (), "global_hq"),
    "local_subsidiary": LegacyEntityMapping("PRIVATE_COMPANY", (), "local_entity"),
    "architect": LegacyEntityMapping("ENGINEERING_COMPANY", ("ARCHITECT",)),
    "consultant": LegacyEntityMapping("ENGINEERING_COMPANY", ("ENGINEERING_CONSULTANT",)),
    "pm_cm": LegacyEntityMapping("ENGINEERING_COMPANY", ("PM_CM",)),
    "epc": LegacyEntityMapping("ENGINEERING_COMPANY", ("EPC",)),
    "gc": LegacyEntityMapping("CONSTRUCTION_COMPANY", ("GENERAL_CONTRACTOR",)),
    "mep": LegacyEntityMapping("CONSTRUCTION_COMPANY", ("MEP_CONTRACTOR",)),
    "operator": LegacyEntityMapping("PRIVATE_COMPANY", ("OPERATOR",)),
    "vendor": LegacyEntityMapping("PRIVATE_COMPANY", ("VENDOR",)),
    "supplier": LegacyEntityMapping("PRIVATE_COMPANY", ("EQUIPMENT_SUPPLIER",)),
    "authority": LegacyEntityMapping(
        "PUBLIC_INSTITUTION", ("GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY")
    ),
    "industrial_park": LegacyEntityMapping(
        "INDUSTRIAL_PARK_DEVELOPER", ("INDUSTRIAL_PARK", "LANDLORD")
    ),
    "location": LegacyEntityMapping("OTHER", ("OTHER",)),
    "other": LegacyEntityMapping("OTHER", ("OTHER",)),
}


ROLE_DECISION_INFLUENCE: dict[str, tuple[tuple[str, str], ...]] = {
    "PROJECT_OWNER": (("PROJECT_GOVERNANCE", "HIGH"), ("BUDGET_INVESTMENT", "HIGH"), ("VENDOR_SELECTION", "MEDIUM")),
    "END_CLIENT": (("PROJECT_GOVERNANCE", "HIGH"), ("TECHNICAL_SPECIFICATION", "MEDIUM"), ("OPERATION", "HIGH")),
    "INVESTOR": (("BUDGET_INVESTMENT", "HIGH"), ("PROJECT_GOVERNANCE", "MEDIUM")),
    "SPONSOR": (("BUDGET_INVESTMENT", "HIGH"), ("PROJECT_GOVERNANCE", "HIGH")),
    "DEVELOPER": (("PROJECT_GOVERNANCE", "HIGH"), ("SITE_LAND", "HIGH"), ("PROCUREMENT", "MEDIUM")),
    "HOST": (("SITE_LAND", "HIGH"), ("PARTNERSHIP_APPROVAL", "HIGH")),
    "CO_DEVELOPMENT_PARTNER": (("PARTNERSHIP_APPROVAL", "HIGH"), ("TECHNICAL_SPECIFICATION", "MEDIUM")),
    "STRATEGIC_PARTNER": (("PARTNERSHIP_APPROVAL", "HIGH"),),
    "ARCHITECT": (("DESIGN", "HIGH"), ("TECHNICAL_SPECIFICATION", "HIGH")),
    "ENGINEERING_CONSULTANT": (("DESIGN", "HIGH"), ("TECHNICAL_SPECIFICATION", "HIGH")),
    "PM_CM": (("PROJECT_GOVERNANCE", "MEDIUM"), ("PROCUREMENT", "MEDIUM"), ("CONSTRUCTION", "MEDIUM")),
    "EPC": (("DESIGN", "HIGH"), ("PROCUREMENT", "HIGH"), ("CONSTRUCTION", "HIGH"), ("VENDOR_SELECTION", "HIGH")),
    "GENERAL_CONTRACTOR": (("CONSTRUCTION", "HIGH"), ("PROCUREMENT", "MEDIUM")),
    "MEP_CONTRACTOR": (("TECHNICAL_SPECIFICATION", "MEDIUM"), ("CONSTRUCTION", "HIGH"), ("EQUIPMENT_SELECTION", "MEDIUM")),
    "TECHNOLOGY_PROVIDER": (("TECHNICAL_SPECIFICATION", "HIGH"), ("EQUIPMENT_SELECTION", "HIGH")),
    "SOLUTION_PROVIDER": (("TECHNICAL_SPECIFICATION", "HIGH"), ("EQUIPMENT_SELECTION", "MEDIUM")),
    "EQUIPMENT_SUPPLIER": (("EQUIPMENT_SELECTION", "HIGH"), ("VENDOR_SELECTION", "MEDIUM")),
    "VENDOR": (("VENDOR_SELECTION", "MEDIUM"), ("PROCUREMENT", "LOW")),
    "OPERATOR": (("OPERATION", "HIGH"), ("TECHNICAL_SPECIFICATION", "MEDIUM")),
    "FACILITY_MANAGER": (("OPERATION", "HIGH"),),
    "MAINTENANCE_PROVIDER": (("OPERATION", "MEDIUM"),),
    "GOVERNMENT_PARTNER": (("PARTNERSHIP_APPROVAL", "HIGH"), ("REGULATORY_APPROVAL", "MEDIUM")),
    "REGULATORY_AUTHORITY": (("REGULATORY_APPROVAL", "HIGH"),),
    "INDUSTRIAL_PARK": (("SITE_LAND", "HIGH"), ("REGULATORY_APPROVAL", "MEDIUM")),
    "LANDLORD": (("SITE_LAND", "HIGH"),),
}


def canonical_entity_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return f"org:{slug or 'unknown'}"


def legacy_entity_mapping(entity_type: str, name: str = "") -> LegacyEntityMapping:
    mapping = LEGACY_ENTITY_MAPPINGS.get(entity_type, LegacyEntityMapping("UNKNOWN", ("OTHER",)))
    lowered = name.casefold()
    if any(token in lowered for token in ("national innovation centre", "national innovation center", "ministry", "authority", "government")):
        roles = tuple(dict.fromkeys((*mapping.roles, "GOVERNMENT_PARTNER")))
        return LegacyEntityMapping("PUBLIC_INSTITUTION", roles, mapping.organization_scope)
    return mapping


def normalize_relationship_type(value: str, description: str = "") -> tuple[str, str]:
    text = f"{value} {description}".casefold()
    rules = (
        (("subsidiary",), "SUBSIDIARY_OF", "Corporate registry / ownership"),
        (("local arm", "local entity of"), "LOCAL_ARM_OF", "Corporate registry / ownership"),
        (("parent of",), "PARENT_OF", "Corporate registry / ownership"),
        (("joint venture", " jv "), "JOINT_VENTURE", "Joint venture"),
        (("co-development", "co development", "joint roadmap", "joint development"), "CO_DEVELOPMENT", "MOU" if "mou" in text else "Partnership announcement"),
        (("mou", "memorandum of understanding"), "MOU", "MOU"),
        (("strategic partnership",), "STRATEGIC_PARTNERSHIP", "Partnership announcement"),
        (("epc contract", "epc award"), "EPC_CONTRACT", "Contract / award"),
        (("design contract", "architect appointment"), "DESIGN_CONTRACT", "Contract / appointment"),
        (("supply contract", "supply agreement"), "SUPPLY_CONTRACT", "Contract / agreement"),
        (("o&m", "om contract", "operation and maintenance"), "OM_CONTRACT", "Contract / agreement"),
        (("award", "contract to"), "AWARDS_CONTRACT_TO", "Contract / award"),
        (("technology provision", "technology provider"), "TECHNOLOGY_PROVISION", "Technology agreement"),
        (("equipment supply", "equipment supplier"), "EQUIPMENT_SUPPLY", "Supply agreement"),
        (("solution provision", "solution provider"), "SOLUTION_PROVISION", "Solution agreement"),
        (("provides land", "land provision"), "PROVIDES_LAND", "Land agreement"),
        (("leases to", "lease"), "LEASES_TO", "Lease"),
        (("hosts", "hosted by"), "HOSTS", "Site / host agreement"),
        (("invest", "equity"), "INVESTS_IN", "Investment / equity"),
        (("sponsor",), "SPONSORS", "Sponsorship"),
        (("owns", "ownership"), "OWNS", "Ownership"),
        (("regulates",), "REGULATES", "Regulatory mandate"),
        (("approves", "approval"), "APPROVES", "Regulatory approval"),
        (("supervises",), "SUPERVISES", "Supervision mandate"),
        (("located in",), "LOCATED_IN", "Location evidence"),
    )
    for tokens, relationship_type, basis in rules:
        if any(token in text for token in tokens):
            return relationship_type, basis
    return "OTHER", ""


def canonical_node_role(roles: list[str]) -> str:
    order = {role: index for index, role in enumerate(PROJECT_ROLES)}
    return " / ".join(sorted(dict.fromkeys(roles), key=lambda role: order.get(role, 999))) or "OTHER"

