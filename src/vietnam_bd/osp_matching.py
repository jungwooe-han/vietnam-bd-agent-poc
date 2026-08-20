from __future__ import annotations

import math
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

from .models_v3 import BDV3AnalysisResult


OSP_WORKBOOK_PATH = Path(__file__).resolve().parents[2] / "md (1).xlsx"
OSP_SHEET_NAME = "0. OSP Data"
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


@dataclass(frozen=True)
class OSPRecord:
    osp: str
    opportunity: str
    products: str
    owner: str
    amount_usd: float
    created_at: date | None
    end_date: date | None
    status: str
    opportunity_type: str
    industry: str
    subindustry: str
    region: str
    facility_type: str
    project_type: str
    product_tags: tuple[str, ...]
    size_band: str


@dataclass(frozen=True)
class OSPMatch:
    record: OSPRecord
    reasons: tuple[str, ...]
    matched_fields: tuple[str, ...]
    rank_score: float


def _column_index(reference: str) -> int:
    value = 0
    for char in re.match(r"[A-Z]+", reference).group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def _sheet_rows(path: Path, sheet_name: str) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(".//m:t", NS))
                for item in root.findall("m:si", NS)
            ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            relation.attrib["Id"]: relation.attrib["Target"]
            for relation in rels.findall("p:Relationship", REL_NS)
        }
        sheet = next(
            item for item in workbook.findall(".//m:sheet", NS)
            if item.attrib["name"] == sheet_name
        )
        target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
        target = target if target.startswith("xl/") else f"xl/{target}"
        root = ET.fromstring(archive.read(target))
        rows: list[list[str]] = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            cells: dict[int, str] = {}
            for cell in row.findall("m:c", NS):
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    text = "".join(node.text or "" for node in cell.findall(".//m:t", NS))
                else:
                    value = cell.find("m:v", NS)
                    text = "" if value is None else value.text or ""
                    if cell_type == "s" and text:
                        text = shared[int(text)]
                cells[_column_index(cell.attrib["r"])] = text.strip()
            if cells:
                rows.append([cells.get(index, "") for index in range(max(cells) + 1)])
        return rows


def _excel_date(value: str) -> date | None:
    try:
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(value).date()
        except (TypeError, ValueError):
            return None


def _number(value: str) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return 0.0


@lru_cache(maxsize=4)
def _load_osp_records_cached(path_string: str, modified_ns: int) -> tuple[OSPRecord, ...]:
    del modified_ns
    rows = _sheet_rows(Path(path_string), OSP_SHEET_NAME)
    header_index = next(index for index, row in enumerate(rows) if "OSP" in row)
    headers = rows[header_index]
    records: list[OSPRecord] = []
    for row in rows[header_index + 1 :]:
        values = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
            if header
        }
        if not values.get("OSP"):
            continue
        records.append(OSPRecord(
            osp=values["OSP"],
            opportunity=values.get("Account / Project", ""),
            products=values.get("제품군", ""),
            owner=values.get("담당자", ""),
            amount_usd=_number(values.get("규모(USD)", "")),
            created_at=_excel_date(values.get("OSP Create Day", "")),
            end_date=_excel_date(values.get("End Date", "")),
            status=values.get("Status", ""),
            opportunity_type=values.get("Opportunity Type", ""),
            industry=values.get("산업군", ""),
            subindustry=values.get("세부산업", ""),
            region=values.get("지역", ""),
            facility_type=values.get("시설유형", ""),
            project_type=values.get("프로젝트유형", ""),
            product_tags=tuple(tag.strip() for tag in values.get("제품태그", "").split("|") if tag.strip()),
            size_band=values.get("규모구간", ""),
        ))
    return tuple(records)


def load_osp_records(path: Path = OSP_WORKBOOK_PATH) -> list[OSPRecord]:
    if not path.exists():
        return []
    return list(_load_osp_records_cached(str(path.resolve()), path.stat().st_mtime_ns))


def _normal_project_type(value: str) -> str:
    text = value.casefold().replace(" ", "")
    if any(token in text for token in ("수평증축", "수직증축", "증축", "expansion")):
        return "증설"
    if any(token in text for token in ("리모델링", "스마트화", "retrofit", "renovation", "upgrade")):
        return "리모델링"
    if any(token in text for token in ("신축", "newbuild", "newsite")):
        return "신축"
    return ""


def _project_profile(result: BDV3AnalysisResult) -> dict[str, object]:
    intelligence = result.v2_snapshot.project_intelligence
    location = intelligence.project_location
    context = " ".join([
        result.opportunity_title,
        result.executive_summary,
        *(item.claim for item in intelligence.current_project_facts),
    ]).casefold()
    if any(token in context for token in ("semiconductor", "반도체", "chip", "wafer")):
        industry, subindustry = "반도체", "반도체 후공정"
    elif any(token in context for token in ("battery", "배터리", "cell")):
        industry, subindustry = "배터리", "배터리"
    elif any(token in context for token in ("electronics", "전자", "pcb", "display")):
        industry, subindustry = "전자/전기", "전자부품"
    elif any(token in context for token in ("automotive", "자동차", "ev ")):
        industry, subindustry = "자동차", "자동차부품"
    elif any(token in context for token in ("optic", "광학", "material", "소재")):
        industry, subindustry = "첨단소재/광학", "광학부품"
    else:
        industry, subindustry = "", ""

    if any(token in context for token in ("laboratory", " lab", "r&d", "research", "연구")):
        facility_type = "R&D+오피스"
    elif any(token in context for token in ("office", "오피스")) and any(token in context for token in ("factory", "plant", "공장")):
        facility_type = "공장+오피스"
    elif any(token in context for token in ("factory", "plant", "manufactur", "공장", "생산")):
        facility_type = "생산공장"
    else:
        facility_type = ""

    product_text = " ".join(item.product for item in result.product_top3).casefold()
    product_aliases = {
        "중앙공조": ("중앙공조", "hvac", "chiller"),
        "시스템에어컨": ("시스템에어컨", "system air", "air conditioner", "sac"),
        "사이니지": ("사이니지", "signage", "display"),
        "IoT솔루션": ("iot", "sensor", "monitoring", "automation"),
        "러기드폰": ("러기드", "rugged", "field mobility"),
    }
    products = {
        product for product, aliases in product_aliases.items()
        if any(alias in product_text for alias in aliases)
    }
    region = next((value for value in (location.province, location.city, location.region) if value), "")

    amount = 0.0
    for item in intelligence.current_project_facts:
        claim = item.claim
        match = re.search(r"(?:USD|US\$|\$)\s*([\d,.]+)\s*(million|billion|m|bn)?", claim, re.IGNORECASE)
        if not match:
            continue
        amount = float(match.group(1).replace(",", ""))
        unit = (match.group(2) or "").casefold()
        amount *= 1_000_000_000 if unit in {"billion", "bn"} else 1_000_000 if unit in {"million", "m"} else 1
        break
    size_band = "대형" if amount >= 300_000 else "중형" if amount >= 50_000 else "소형" if amount else ""
    return {
        "project_type": _normal_project_type(result.building_type.value),
        "industry": industry,
        "subindustry": subindustry,
        "facility_type": facility_type,
        "products": products,
        "region": region,
        "amount": amount,
        "size_band": size_band,
    }


def _region_match(project_region: str, osp_region: str) -> tuple[float, bool]:
    if not project_region or not osp_region:
        return 0.0, False
    project = project_region.casefold()
    osp = osp_region.casefold()
    if project in osp or osp in project:
        return 2.0, True
    northern = ("hanoi", "ha noi", "bac ninh", "bac giang", "thai nguyen", "vinh phuc", "hai duong", "hai phong", "hung yen", "ha nam")
    southern = ("ho chi minh", "binh duong", "dong nai", "long an")
    for cluster in (northern, southern):
        if any(token in project for token in cluster) and any(token in osp for token in cluster):
            return 0.7, False
    return 0.0, False


def _friendly_reasons(record: OSPRecord, fields: list[str], products: set[str], exact_region: bool) -> tuple[str, ...]:
    reasons: list[str] = []
    if "facility_type" in fields:
        reasons.append(f"{record.facility_type} 중심의 시설 구성이 비슷합니다.")
    if "subindustry" in fields:
        reasons.append(f"같은 {record.subindustry} 분야의 과거 프로젝트입니다.")
    elif "industry" in fields:
        reasons.append(f"{record.industry} 산업의 프로젝트 경험입니다.")
    if "project_type" in fields:
        reasons.append(f"동일하게 {record.project_type} 성격의 사업입니다.")
    if "products" in fields:
        overlap = [tag for tag in record.product_tags if tag in products]
        reasons.append(f"{', '.join(overlap[:2])} 제안 이력이 있습니다.")
    if exact_region:
        reasons.append(f"같은 {record.region} 지역에서 진행된 사례입니다.")
    if "size_band" in fields:
        reasons.append(f"비슷한 {record.size_band} 규모의 Opportunity입니다.")
    return tuple(reasons[:3] or ["베트남 제조 프로젝트의 과거 OSP로 참고할 수 있습니다."])


def match_osp_cases(result: BDV3AnalysisResult, limit: int = 15) -> list[OSPMatch]:
    profile = _project_profile(result)
    products = set(profile["products"])
    ranked: list[OSPMatch] = []
    for record in load_osp_records():
        score = 0.0
        fields: list[str] = []
        if profile["subindustry"] and profile["subindustry"] == record.subindustry:
            score += 3.0
            fields.append("subindustry")
        elif profile["industry"] and profile["industry"] == record.industry:
            score += 2.0
            fields.append("industry")
        if profile["facility_type"] and profile["facility_type"] == record.facility_type:
            score += 2.5
            fields.append("facility_type")
        if profile["project_type"] and profile["project_type"] == record.project_type:
            score += 2.0
            fields.append("project_type")
        overlap = products.intersection(record.product_tags)
        if overlap:
            score += min(2.4, len(overlap) * 1.2)
            fields.append("products")
        region_score, exact_region = _region_match(str(profile["region"]), record.region)
        score += region_score
        if region_score:
            fields.append("region")
        if profile["size_band"] and profile["size_band"] == record.size_band:
            score += 1.5
            fields.append("size_band")
        elif profile["amount"] and record.amount_usd:
            ratio = max(float(profile["amount"]), record.amount_usd) / max(1, min(float(profile["amount"]), record.amount_usd))
            score += max(0.0, 1.0 - math.log10(ratio))
        if record.status.casefold() == "closed won":
            score += 0.15
        if record.end_date:
            score += max(0.0, (record.end_date.year - 2018) * 0.01)
        ranked.append(OSPMatch(
            record=record,
            reasons=_friendly_reasons(record, fields, products, exact_region),
            matched_fields=tuple(fields),
            rank_score=score,
        ))
    ranked.sort(key=lambda item: (-item.rank_score, item.record.osp))
    return ranked[: max(0, limit)]
