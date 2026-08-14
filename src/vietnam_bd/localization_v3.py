from __future__ import annotations

UI_TEXT = {
    "ko": {
        "opportunity_tab": "기회 개요", "strategy_tab": "접촉 전략", "meeting_tab": "미팅 준비",
        "opportunity_eyebrow": "기회 요약", "opportunity_title": "어떤 프로젝트가 진행 중인가요?",
        "strategy_eyebrow": "접촉 대상", "strategy_title": "누구에게 먼저 접근할까요?",
        "strategy_subtitle": "확인된 영향력과 접근 가능성을 기준으로 접촉 대상을 정리했습니다.",
        "meeting_eyebrow": "미팅 준비", "meeting_title": "첫 미팅에서 무엇을 확인할까요?",
        "meeting_subtitle": "가설을 사실로 확인할 질문과 대화 주제를 정리했습니다.",
        "key_facts": "핵심 프로젝트 정보", "evidence_aware": "근거 기반", "building_type": "건축 유형",
        "project_stage": "사업 단계", "project_structure": "사업 구조", "relationship_map": "핵심 관계자와 의사결정 구조",
        "relationship_evidence": "관계자 판단 근거 보기", "need_signals": "고객 과제 신호", "ai_strategy": "접촉 전략 요약",
        "meet_first": "먼저 접촉할 대상", "priority": "우선순위", "target_function": "확인할 담당 부서",
        "person": "담당자", "evidence": "근거 수준", "why_priority": "우선 접촉 이유 보기",
        "not_confirmed": "미확인", "questions": "꼭 확인할 질문", "prioritized": "중요도 순",
        "talking_points": "제안 대화 주제", "short_scenarios": "대화 예시", "ai_meeting": "이번 미팅의 목표",
        "top_signals": "고객 과제 신호", "products": "검토할 솔루션", "why": "적합한 이유",
        "customer_need": "연결되는 고객 과제", "scenario": "대화 시작점", "decision_trace": "추천 근거 보기",
        "overall_trace": "전체 추천 근거 보기", "confirmed": "확인됨", "inferred": "정황상 유력", "unknown": "미확인",
    },
}


def ui(language: str, key: str) -> str:
    return UI_TEXT["ko"].get(key, key)
