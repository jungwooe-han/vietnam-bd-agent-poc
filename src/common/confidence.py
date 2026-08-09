_CONFIRMED = {"label": "확인됨", "css_class": "confirmed", "icon": "✅"}
_ESTIMATED = {"label": "추정", "css_class": "estimated", "icon": "🔎"}
_HYPOTHESIS = {"label": "가설", "css_class": "hypothesis", "icon": "💡"}
_UNKNOWN = {"label": "정보없음", "css_class": "unknown", "icon": "❓"}
_CROSS_VERIFIED = {"label": "교차확인됨", "css_class": "crossverified", "icon": "🔗"}
_CONFLICT = {"label": "불일치", "css_class": "conflict", "icon": "⚠️"}

_LOOKUP = {
    "confirmed": _CONFIRMED,
    "확인됨": _CONFIRMED,
    "likely": _ESTIMATED,
    "estimated": _ESTIMATED,
    "추정": _ESTIMATED,
    "hypothesis": _HYPOTHESIS,
    "가설": _HYPOTHESIS,
    "unknown": _UNKNOWN,
    "정보없음": _UNKNOWN,
    "cross_verified": _CROSS_VERIFIED,
    "교차확인됨": _CROSS_VERIFIED,
    "conflict": _CONFLICT,
    "불일치": _CONFLICT,
}


def label(value: str) -> str:
    return _LOOKUP.get(value, _UNKNOWN)["label"]


def css_class(value: str) -> str:
    return _LOOKUP.get(value, _UNKNOWN)["css_class"]


def icon(value: str) -> str:
    return _LOOKUP.get(value, _UNKNOWN)["icon"]
