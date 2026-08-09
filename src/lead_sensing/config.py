import os

import streamlit as st


def get_anthropic_api_key() -> str:
    """
    Local:
      ANTHROPIC_API_KEY=...
    Streamlit Cloud:
      Settings > Secrets 에
      ANTHROPIC_API_KEY="..."
    """
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        key = ""

    return key or os.getenv("ANTHROPIC_API_KEY", "")


def get_model_name() -> str:
    try:
        return st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    except Exception:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
