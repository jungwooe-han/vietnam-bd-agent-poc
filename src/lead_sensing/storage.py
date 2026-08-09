from datetime import datetime, timezone

import streamlit as st

from .lead_sensing import DEFAULT_SOURCES


def init_state():
    defaults = {
        "leads": [],
        "status_map": {},
        "bookmarks": set(),
        "notes": {},
        "sources": [dict(x) for x in DEFAULT_SOURCES],
        "last_new_keys": set(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def merge_pipeline(existing, incoming):
    now = datetime.now(timezone.utc).isoformat()
    result = {}
    new_keys = set()

    for lead in existing:
        key = lead.get("company", "").strip().lower()
        if key:
            result[key] = lead

    for lead in incoming:
        key = lead.get("company", "").strip().lower()
        if not key:
            continue

        previous = result.get(key)
        if previous:
            lead["discovered_at"] = previous.get("discovered_at", now)
            lead["timeline"] = previous.get("timeline", lead.get("timeline", []))
        else:
            lead["discovered_at"] = now
            new_keys.add(key)

        lead["updated_at"] = now
        result[key] = lead

    return list(result.values()), new_keys
