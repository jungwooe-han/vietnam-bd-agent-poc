SCHEMA = """
[
  {
    "company": "기업명",
    "location": "구체적 지역/성",
    "industry": "업종",
    "signal_type": "신호 유형",
    "signal_date": "YYYY-MM 또는 확인 가능한 시점",
    "evidence": "왜 이것이 사업 기회 신호인지 2문장 이내",
    "source": "출처 매체/기관명",
    "score": 0,
    "approach": {
      "decision_maker": {
        "value": "",
        "confidence": "확인됨|추정|정보없음",
        "basis": ""
      },
      "timing": {
        "value": "",
        "confidence": "확인됨|추정|정보없음",
        "basis": ""
      },
      "competitor_status": {
        "value": "",
        "confidence": "확인됨|추정|정보없음",
        "basis": ""
      }
    }
  }
]
"""


def build_scan_prompt(region, industry, time_window, keyword="", source_only=False, domain_list=None):
    domain_list = domain_list or []

    source_rule = ""
    if source_only:
        source_rule = (
            "web_search는 아래 지정 신뢰 소스 안에서만 조사하세요.\n"
            f"지정 소스: {', '.join(domain_list)}\n"
        )

    keyword_rule = f"- 추가 키워드: {keyword}\n" if keyword else ""

    return f"""
당신은 베트남 제조업 B2B 영업 인텔리전스 리서처입니다.
web_search 도구를 사용해 실제 공개 근거를 찾으세요.

{source_rule}
조건:
- 지역: {region}
- 업종 포커스: {industry}
- 기간: {time_window}
{keyword_rule}

찾아야 할 신호 유형:
FDI 투자 승인, 신규 공장 착공/증설, 산업단지 부지 계약, 대규모 채용 급증,
신규 생산라인 발표, RFP/조달 신호, 관련 전시회/컨퍼런스 참가 발표 등.

최대 6개의 리드만 아래 JSON 배열 형식으로 출력하세요.
마크다운이나 추가 설명은 출력하지 마세요.

{SCHEMA}

중요:
- 실제 검색 결과 근거가 없는 리드는 만들지 마세요.
- 근거가 부족하면 리드 수를 줄이세요.
- 확인된 사실만 confidence="확인됨".
- 정황상 추론은 confidence="추정" 및 basis에 추론근거 작성.
- 단서가 없으면 confidence="정보없음", value="확인 필요".
"""


def build_verify_prompt(lead):
    return f"""
당신은 팩트체커입니다.
아래 기업에 대한 기존 주장을 독립적으로 web_search해서 다시 검증하세요.
기존 주장을 그대로 믿지 마세요.

기업: {lead.get("company","")}
지역: {lead.get("location","")}
기존 주장:
{lead.get("approach",{})}

각 항목에 대해:
- 독립 근거와 일치: "교차확인됨"
- 모순/상이: "불일치"
- 근거 없음: "정보없음"

아래 JSON 객체만 출력:
{{
  "decision_maker": {{ "value": "", "confidence": "교차확인됨|불일치|정보없음", "basis": "" }},
  "timing": {{ "value": "", "confidence": "교차확인됨|불일치|정보없음", "basis": "" }},
  "competitor_status": {{ "value": "", "confidence": "교차확인됨|불일치|정보없음", "basis": "" }}
}}
"""


def build_timeline_prompt(lead):
    return f"""
당신은 B2B 영업 인텔리전스 리서처입니다.
web_search로 아래 기업의 최신 뉴스/공시/발표를 찾으세요.

기업: {lead.get("company","")}
지역: {lead.get("location","")}
업종: {lead.get("industry","")}

기존 타임라인:
{lead.get("timeline",[])}

기존과 겹치지 않는 새로운 사건만 최대 5개.
없으면 [].

JSON 배열만 출력:
[
  {{ "date": "YYYY-MM 또는 가능한 만큼", "headline": "1문장", "source": "출처" }}
]
"""


def build_email_prompt(lead, note=""):
    approach = lead.get("approach") or {}
    decision = (approach.get("decision_maker") or {}).get("value", "")
    return f"""
당신은 삼성전자 B2B 영업 담당자를 대신해 잠재 고객에게 보낼 첫 컨택 이메일 초안을 작성합니다.

대상 기업: {lead.get("company","")}
지역: {lead.get("location","")}
업종: {lead.get("industry","")}
포착된 사업 신호: {lead.get("evidence","")}
신호 유형: {lead.get("signal_type","")} ({lead.get("signal_date","")})
추정 담당자/의사결정 구조: {decision or "알 수 없음"}
영업사원의 개인 메모: {note or "없음"}

작성 규칙:
- 영어
- 150단어 이내
- 과장된 세일즈 톤 지양
- 공개 정보 기반으로 왜 지금 연락하는지 맥락 제공
- 구체 제품 나열보다 협력 가능성 제안
- 짧은 통화/미팅 제안으로 마무리
- Subject 포함
- 이메일 본문만 출력
"""
