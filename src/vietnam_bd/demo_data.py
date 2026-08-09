from .models import AnalysisResult


def demo_result() -> AnalysisResult:
    return AnalysisResult.model_validate({
        "opportunity_title": "베트남 전자부품 생산라인 증설 기회",
        "executive_summary": "생산능력 확대가 직접 신호이며, 시설·유틸리티 범위가 포함된다면 삼성 DX 통합 접근 여지가 있습니다. 다만 설계 단계와 발주 구조가 확인되지 않아 첫 미팅은 제안보다 의사결정 구조와 운영 KPI 확인에 집중해야 합니다.",
        "why_opportunity_now": "생산라인 투자는 설비뿐 아니라 공조·에너지·현장 운영·가시화 관련 결정이 함께 발생할 수 있는 시점입니다.",
        "current_stage": "투자 발표 또는 초기 검토 단계로 추정",
        "stage_basis": "입력에는 투자 방향만 있고 설계사·EPC·착공 일정 정보가 없습니다.",
        "business_objective": {"claim": "생산능력 확대", "credibility": "confirmed", "rationale": "입력된 증설 정보에 직접 나타난 목적입니다.", "source_labels": ["사용자 입력"]},
        "decision_drivers": [
            {"claim": "신규 수요 대응", "credibility": "likely", "rationale": "전자부품 생산라인 증설은 통상 고객 수요 증가 또는 공급망 확장과 연결되지만 현장 확인이 필요합니다.", "source_labels": ["산업 맥락"]}
        ],
        "customer_needs": [
            {"claim": "생산 안정성을 해치지 않는 유틸리티 확장", "credibility": "hypothesis", "rationale": "정밀 전자부품 공정은 온습도와 설비 안정성이 중요할 수 있습니다.", "source_labels": ["프로젝트 유형"]},
            {"claim": "현장 운영 가시성 개선", "credibility": "hypothesis", "rationale": "증설 시 운영 복잡도가 증가할 수 있으나 고객 확인 전에는 가설입니다.", "source_labels": ["운영 맥락"]}
        ],
        "critical_unknowns": ["신규 사이트인지 기존 사이트 증설인지", "설계사 및 Engineering 업체", "EPC/설치사 선정 여부", "핵심 운영 KPI", "시설·유틸리티 발주 범위"],
        "portfolio": {
            "lead_domain": "HVAC / Facility Operations",
            "lead_reason": "시설·유틸리티가 실제 투자 범위에 포함되는 경우 생산 안정성과 에너지 효율 대화를 가장 자연스럽게 시작할 수 있습니다.",
            "supporting_domains": ["SmartThings Pro / b.IoT", "MX Rugged / Tablet", "Signage / VXT"],
            "conversation_entry": "제품 설명보다 증설 이후 생산 안정성, 에너지 KPI, 운영 가시성 문제를 먼저 확인하고 관련 레퍼런스로 대화를 시작합니다.",
            "relevant_capabilities": ["정밀 공조", "에너지·설비 통합관제", "현장 모바일 업무", "생산·안전 정보 가시화"],
            "caution": "현재 정보만으로 제품 제안을 확정하지 말고 시설 범위와 의사결정 주체를 먼저 확인해야 합니다."
        },
        "stakeholders": [
            {"role": "공장 Engineering/Facility 책임자", "priority": "primary", "why_meet": "시설 사양과 운영 KPI를 가장 잘 알고 있을 가능성이 큽니다.", "information_to_get": ["유틸리티 범위", "운영 KPI", "설계·사양 결정권"]},
            {"role": "설계사 또는 EPC 프로젝트 책임자", "priority": "secondary", "why_meet": "사양 반영 가능 시점과 실제 영향 구조를 확인할 수 있습니다.", "information_to_get": ["설계 완료도", "벤더 선정 일정", "설치사"]}
        ],
        "priority_questions": [
            {"question": "이번 투자는 신규 사이트입니까, 기존 공장 내 증설입니까?", "why_it_matters": "기존 인프라 연동과 설계 자유도가 크게 달라집니다.", "decision_enabled": "신규 통합 제안과 기존 설비 개선 중 접근 방향을 결정합니다.", "if_yes": "신규 사이트라면 초기 설계 영향력을 확인합니다.", "if_no_or_unknown": "증설이라면 기존 설비·운영 문제와 연동 제약을 확인합니다."},
            {"question": "Engineering과 유틸리티 사양은 누가 결정하고 있습니까?", "why_it_matters": "실질 영향자를 알아야 접촉 순서를 정할 수 있습니다.", "decision_enabled": "고객, 설계사, EPC 중 누구를 우선 공략할지 판단합니다.", "if_yes": "담당 조직과 기술 미팅을 연결합니다.", "if_no_or_unknown": "유사 사이트의 파트너와 내부 Owner를 통해 구조를 확인합니다."},
            {"question": "이번 투자에서 가장 중요한 KPI는 생산량, 품질·수율, 에너지, 인력 중 무엇입니까?", "why_it_matters": "같은 공장 증설이라도 가치제안이 달라집니다.", "decision_enabled": "Lead BU와 대화 주제를 확정합니다.", "if_yes": "확인된 KPI에 맞는 레퍼런스를 준비합니다.", "if_no_or_unknown": "각 KPI의 현재 기준과 개선 목표를 후속 확인합니다."}
        ],
        "next_steps": ["공장 유형·위치·프로젝트 단계를 먼저 확인", "Engineering/EPC/설치사 및 내부 유사 사이트 Owner 탐색", "핵심 KPI 가설을 검증할 첫 미팅 질문 3개 준비"],
        "similar_cases": [],
        "source_summary": ["데모 모드: 실제 웹 검색 미실행"],
        "limitations": ["API 키가 없어 예시 결과를 표시했습니다.", "실제 분석 시 외부 출처와 사용자 입력을 기준으로 다시 생성됩니다."]
    })
