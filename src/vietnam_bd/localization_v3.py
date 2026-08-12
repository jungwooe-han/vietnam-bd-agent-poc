from __future__ import annotations

UI_TEXT = {
    "ko": {
        "opportunity_tab": "1. 기회", "strategy_tab": "2. 전략", "meeting_tab": "3. 미팅",
        "opportunity_eyebrow": "기회 인텔리전스", "opportunity_title": "무슨 일이 일어나고 있는가?",
        "strategy_eyebrow": "이해관계자 전략", "strategy_title": "누구를 만나야 하는가?",
        "strategy_subtitle": "우선순위는 억지로 나눈 순위가 아니라 동등한 Tier입니다.",
        "meeting_eyebrow": "미팅 워크스페이스", "meeting_title": "무엇을 묻고 말해야 하는가?",
        "meeting_subtitle": "Unknown과 Inference를 실제 영업 Fact로 전환합니다.",
        "key_facts": "핵심 프로젝트 정보", "evidence_aware": "근거 기반", "building_type": "건축 유형",
        "project_stage": "사업 단계", "project_structure": "사업 구조", "relationship_map": "사업 관계도",
        "relationship_evidence": "관계 근거", "need_signals": "고객 니즈 신호", "ai_strategy": "AI 전략 요약",
        "meet_first": "우선 접촉 Tier", "priority": "우선순위", "target_function": "접촉 부서",
        "person": "담당자", "evidence": "근거", "why_priority": "왜 이 우선순위인가?",
        "not_confirmed": "미확인", "questions": "확인 질문", "prioritized": "우선순위순",
        "talking_points": "대화 포인트", "short_scenarios": "짧은 영업 시나리오", "ai_meeting": "AI 미팅 준비",
        "top_signals": "고객 니즈 핵심 신호", "products": "추천 제품 TOP 3", "why": "추천 이유",
        "customer_need": "고객 니즈", "scenario": "제안 시나리오", "decision_trace": "판정 근거",
        "overall_trace": "전체 Excel 70 / AI 30 판정 근거", "confirmed": "확인", "inferred": "추론", "unknown": "미확인",
    },
}


def ui(language: str, key: str) -> str:
    return UI_TEXT["ko"].get(key, key)
