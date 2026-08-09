from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from apps.lead_sensing_app import render as render_lead_sensing
from apps.vietnam_bd_app import render as render_vietnam_bd

st.set_page_config(
    page_title="AI크루 콘솔",
    page_icon="🧭",
    layout="wide",
)

lead_sensing_page = st.Page(
    render_lead_sensing, title="리드 센싱", icon="📡", url_path="lead-sensing", default=True
)
vietnam_bd_page = st.Page(
    render_vietnam_bd, title="BD Agent", icon="🧭", url_path="vietnam-bd"
)

nav = st.navigation([lead_sensing_page, vietnam_bd_page])
nav.run()

if st.session_state.pop("_nav_to_bd", False):
    st.switch_page(vietnam_bd_page)
