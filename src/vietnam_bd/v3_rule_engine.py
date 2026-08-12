from __future__ import annotations

import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .models import BDV2AnalysisResult
from .models_v3 import (
    BDV3AnalysisResult, V3ProductRecommendation, V3ProjectFact, V3Question,
    V3RelationshipMap, V3StakeholderTarget, V3StructureNode, V3StructureRelation,
    V3TalkingPoint,
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
    return "confirmed" if credibility == "confirmed" else "inferred" if credibility in {"likely", "hypothesis"} else "unknown"


def _priority(value: str) -> int | None:
    try:
        parsed = int(float(value))
        return parsed if parsed in {1, 2, 3} else None
    except (TypeError, ValueError):
        return None


def _structure(v2: BDV2AnalysisResult, text: str) -> tuple[str | None, str, str, list[str]]:
    claims = " ".join(x.claim + " " + x.rationale for x in v2.context.business_structure)
    combined = (claims + " " + text).lower()
    evidence = [x.claim for x in v2.context.business_structure if x.credibility != "unknown"]
    epc_owner = any(k in combined for k in ("epc invest", "epc equity", "epc ownership", "epc가 투자", "epc 지분"))
    fi = any(k in combined for k in ("financial investor", "private equity", " pef", " fi ", "재무적 투자"))
    if epc_owner:
        return ("S4" if fi else "S3", "EPC Owner 참여 + FI" if fi else "EPC Owner 참여", "inferred", evidence)
    if fi:
        return "S2", "Owner + FI / EPC 시공만", "inferred", evidence
    owner_known = any("end client" in x.claim.lower() or "owner" in x.claim.lower() for x in v2.context.business_structure)
    if owner_known and any(k in combined for k in ("epc", "gc", "construction")):
        return "S1", "Owner 전액 투자 / EPC 시공만", "inferred", evidence
    return None, "Not confirmed", "unknown", evidence


def _stage(v2: BDV2AnalysisResult) -> tuple[str | None, str]:
    value = v2.context.business_stage.claim
    if value in {"사업기획", "타당성 조사"}: return "ST1", "초기 기획"
    if value in {"Master Plan", "설계 - SD (기본)", "설계 - DD (기본)", "설계 - CD (기본)"}: return "ST2", "설계 및 발주"
    if value in {"건설 인허가", "시공"}: return "ST3", "시공"
    if value in {"운영 인허가", "프로젝트 종료"}: return "ST4", "준공 및 영업"
    return None, "Unknown"


def build_v3_result(v2: BDV2AnalysisResult, seed: str, extracted: str = "") -> BDV3AnalysisResult:
    rules = _read_rulebook()
    combined = f"{seed}\n{extracted}".lower()
    structure_id, structure_name, structure_status, structure_evidence = _structure(v2, combined)
    stage_id, stage_group = _stage(v2)
    actors = v2.relationship_map.actors
    role_aliases = {"OWNER_HQ": ("owner", "hq"), "OWNER_LOCAL": ("owner", "local"), "EPC": ("epc",), "DESIGN": ("design", "architect", "engineering"), "FI": ("investor", "capital", "pef")}
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
    relationship = V3RelationshipMap(structure_id=structure_id, structure_name=structure_name, status=structure_status, evidence=structure_evidence, nodes=nodes, relations=relations)

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
        node_id = "OWNER_HQ" if stakeholder == "Project Owner" and location == "HQ" else "OWNER_LOCAL" if stakeholder == "Project Owner" else "DESIGN" if stakeholder == "Design/Engineering" else stakeholder.upper()
        company, status, evidence = companies.get(node_id, (None, "unknown", []))
        if stakeholder == "Project Owner" and location == "HQ" and not company: continue
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
    questions.extend([V3Question(question="현재 확정된 제품 Spec과 아직 열려 있는 Scope는 무엇입니까?", information_goal="Spec-in 가능 범위", reason="제안 가능한 제품과 납품 시점을 확정합니다.", converts="inference"), V3Question(question="Vendor shortlist와 최종 기술·구매 승인권자는 누구입니까?", information_goal="실제 의사결정권자", reason="접근 경로와 경쟁 구도를 확인합니다.", converts="unknown")])
    status = v2.bd_decision.decision
    if status == "closed": targets, questions, products = [], [], []
    return BDV3AnalysisResult(opportunity_title=v2.opportunity_title, executive_summary=v2.executive_summary, status=status, status_reason=v2.bd_decision.rationale, building_type=V3ProjectFact(value=building.claim, status=_status(building.credibility), evidence=building.source_labels), project_stage=V3ProjectFact(value=v2.context.business_stage.claim, status=_status(v2.context.business_stage.credibility), evidence=v2.context.business_stage.source_labels), customer_needs=needs, relationship_map=relationship, priority_1=[x for x in targets if x.priority == 1], priority_2=[x for x in targets if x.priority == 2], priority_3=[x for x in targets if x.priority == 3], stakeholder_unknowns=unknowns, questions_to_ask=questions[:8], talking_points=[V3TalkingPoint(product=p.product, scenario=p.suggested_scenario, customer_need=p.customer_need, project_stage=stage_group) for p in products], customer_need_top_signals=needs[:3], product_top3=products, decision_trace_excel="중복 Match Count로 Excel 후보군과 기본 Priority를 결정했습니다.", decision_trace_ai="기사·입력 텍스트의 직접 맥락은 Excel 후보군 안에서만 동률과 우선순위를 보정했습니다.", evidence=v2.evidence, source_summary=v2.source_summary, limitations=v2.limitations, v2_snapshot=v2)
