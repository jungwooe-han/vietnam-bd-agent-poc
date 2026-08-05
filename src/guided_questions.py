from __future__ import annotations


def generate_guided_questions(seed: str) -> list[str]:
    text = (seed or "").lower()
    questions: list[str] = []

    base = [
        "신규 공장인지 기존 공장 증설인지 알고 있나요?",
        "공장 위치 또는 산업단지를 알고 있나요?",
        "현재 프로젝트 단계(검토·설계·착공·설비선정 등)를 알고 있나요?",
        "Engineering/EPC/설치사 중 확인된 업체가 있나요?",
    ]
    questions.extend(base)

    if any(k in text for k in ["반도체", "semiconductor", "mlcc", "전자부품", "electronics"]):
        questions.extend([
            "클린룸·유틸리티·정밀 공조 범위가 포함되는지 알고 있나요?",
            "생산능력, 수율, 품질 안정성 중 어떤 목표가 강조됐나요?",
        ])
    elif any(k in text for k in ["식품", "food", "음료", "냉동", "cold"]):
        questions.extend([
            "냉장·냉동·콜드체인 또는 위생 인증 범위가 포함되나요?",
            "에너지비, 품질·위생, 생산 자동화 중 어떤 이슈가 언급됐나요?",
        ])
    elif any(k in text for k in ["자동차", "automotive", "배터리", "battery"]):
        questions.extend([
            "생산라인 자동화·품질 추적·작업자 안전 중 어떤 범위가 포함되나요?",
            "본사 표준사양과 현지 의사결정 중 어느 쪽 영향이 큰지 알고 있나요?",
        ])
    else:
        questions.extend([
            "이번 투자의 핵심 목표가 생산량·품질·에너지·인력 중 무엇인지 알고 있나요?",
            "고객이 직접 언급한 운영상 어려움이나 KPI가 있나요?",
        ])

    return questions[:6]
