from __future__ import annotations

import html
import re
from urllib.parse import quote_plus, urlparse

import streamlit as st

from .models import ProjectLocation
from .models_v3 import BDV3AnalysisResult, V3StakeholderTarget
from .localization_v3 import ui


def inject_v3_css() -> None:
    st.markdown(
        """
        <style>
        :root{--navy:#000;--blue:#000;--violet:#000;--ink:#000;--muted:#707070;--line:#ddd;--soft:#f7f7f7}
        html,body,[class*="css"],.stApp{font-family:"SamsungOneKorean","Apple SD Gothic Neo",Arial,sans-serif!important}
        .stApp{background:#fff;color:#000}
        [data-testid="stHeader"]{background:transparent;height:0}[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
        .block-container{max-width:1500px;padding:0 3rem 4rem!important}
        [data-testid="stSidebar"]{background:#f7f7f7;border-right:1px solid #ddd;min-width:300px;max-width:300px}
        [data-testid="stSidebar"] *{color:#000}[data-testid="stSidebar"] h3{color:#000;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:#707070;font-size:.75rem;font-weight:700}
        [data-testid="stSidebar"] button,[data-testid="stSidebar"] .stButton button{height:40px;padding:9px 24px;border:1px solid #000;background:#000;color:#fff;border-radius:20px;font-size:14px;font-weight:700;box-shadow:none}
        [data-testid="stSidebar"] .stButton button p,[data-testid="stSidebar"] .stButton button span{color:#fff!important}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton{margin:.42rem 0}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button{width:100%;height:auto;min-height:66px;padding:12px 14px;background:#fff;color:#000;border:1px solid #ddd;border-radius:16px;justify-content:flex-start;align-items:flex-start;text-align:left;box-shadow:none}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button:hover{background:#f2f2f2;color:#000;border-color:#aaa}
        [data-testid="stSidebar"] [data-testid="stExpander"] .stButton button p,[data-testid="stSidebar"] [data-testid="stExpander"] .stButton button span{width:100%;margin:0;color:#000!important;font-size:.76rem;font-weight:600;line-height:1.38;text-align:left;white-space:pre-line;overflow-wrap:anywhere}
        .stButton>button,.stDownloadButton>button{min-height:40px;padding:9px 24px;border:1px solid #000;background:#000;color:#fff;border-radius:20px;font-size:14px;font-weight:700;box-shadow:none}.stButton>button:hover,.stDownloadButton>button:hover{background:#222;color:#fff;border-color:#222}
        [data-testid="stExpander"]{background:#fff;border:1px solid #ddd;border-radius:20px;box-shadow:none;overflow:hidden}
        [data-testid="stTextArea"] textarea,[data-testid="stFileUploader"] section{border-color:#ddd;border-radius:20px;background:#f7f7f7;box-shadow:none}
        .hero{margin:0 -3rem!important;padding:24px 3rem!important;border-radius:0!important;background:#fff!important;border:0!important;border-bottom:1px solid #ddd!important;box-shadow:none!important;display:flex;align-items:center;justify-content:space-between}
        .hero h1{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif!important;font-size:1.35rem!important;color:#000!important;margin:0!important;padding:0!important}.hero h1:before{content:'BD';display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;margin-right:14px;border-radius:50%;background:#000;color:#fff;font-size:.72rem;vertical-align:middle}
        .hero p{display:none!important}.hero:after{content:'OPPORTUNITY  ·  STRATEGY  ·  MEETING';color:#707070;font-size:.72rem;letter-spacing:.08em}
        [data-testid="stTabs"]{margin-top:24px}[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:32px;background:#fff;border:0;border-bottom:1px solid #ddd;padding:0;border-radius:0;box-shadow:none}
        [data-testid="stTabs"] button[role="tab"]{border-radius:0;padding:4px 0 12px;font-size:18px;font-weight:700;color:#707070;background:transparent;box-shadow:none}
        [data-testid="stTabs"] button[aria-selected="true"]{background:transparent;color:#000;box-shadow:none}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"]{display:block;background:#000;height:2px}
        .v3-head{display:flex;justify-content:space-between;gap:18px;margin:32px 0;padding:0;background:#fff;border:0;border-radius:0;box-shadow:none}.v3-head h1{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;margin:0;color:#000;letter-spacing:-.02em}.v3-head p{margin:.5rem 0 0;color:#707070;font-size:16px;line-height:1.33}
        .v3-eyebrow,.v3-label{font-size:.69rem;letter-spacing:.1em;font-weight:700;color:#707070;text-transform:uppercase}.v3-step{width:40px;height:40px;border-radius:20px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;box-shadow:none}
        .v3-gate{display:grid;grid-template-columns:150px 1fr auto;align-items:center;gap:24px;border-radius:20px;padding:28px 32px;color:#000;margin-bottom:24px;box-shadow:none;min-height:104px;border:1px solid #ddd}.v3-gate.now{background:#edf8f1}.v3-gate.monitor{background:#fff7df}.v3-gate.closed{background:#fff0ef}.v3-gate-status{font-size:1.75rem;font-weight:700}.v3-gate-copy{font-size:16px;line-height:1.45;color:#333}
        .v3-section{display:flex;justify-content:space-between;align-items:center;margin:24px 0 10px}.v3-section h3{font-size:.92rem;margin:0;color:#1d2945}.v3-section span{color:#7b849a}
        .v3-card{border:0;background:#f7f7f7;border-radius:20px;padding:32px;box-shadow:none;height:100%;min-height:148px}.v3-card:hover{border:0;box-shadow:none}.v3-value{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;color:#000;margin:12px 0 18px}
        .v3-chip{display:inline-flex;padding:6px 12px;border-radius:40px;font-size:.7rem;font-weight:700;background:#eee;color:#000}.v3-chip.strong,.v3-chip.confirmed{background:#e5f5eb;color:#087a42}.v3-chip.medium,.v3-chip.inferred,.v3-chip.likely{background:#fff1c8;color:#805500}.v3-chip.weak,.v3-chip.unknown,.v3-chip.hypothesis{background:#e8e8e8;color:#707070}
        .v3-ai{border:0;background:#f7f7f7;border-radius:20px;padding:32px;margin:8px 0 28px;box-shadow:none}.v3-ai-title{font-size:.72rem;letter-spacing:.1em;font-weight:700;color:#707070;margin-bottom:12px}.v3-ai-copy{color:#000;font-size:16px;line-height:1.5}
        .v3-tier{display:inline-flex;padding:6px 14px;border-radius:40px;background:#000;color:#fff;font-size:.7rem;font-weight:700;margin:4px 0 12px}.v3-role{color:#707070;font-size:.76rem;font-weight:700}.v3-company{font-size:18px;font-weight:700;color:#000;margin:8px 0 16px}.v3-meta{display:grid;grid-template-columns:92px 1fr;gap:9px 12px;font-size:.8rem}.v3-meta b{color:#707070}.v3-meta span{color:#000}
        .v3-question{display:grid;grid-template-columns:36px 1fr;gap:16px;border:0;border-radius:20px;padding:20px;background:#f7f7f7;margin-bottom:12px}.v3-number{width:32px;height:32px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.75rem}.v3-question-title{font-size:15px;font-weight:700;color:#000}.v3-question-sub{font-size:.75rem;color:#707070;margin-top:7px}
        .v3-talk{border:0;background:#f7f7f7;border-radius:20px;padding:20px;margin-bottom:12px}.v3-talk b{color:#000;font-size:.8rem}.v3-talk p,.v3-product-copy{font-size:14px;color:#404040;line-height:1.5;margin-top:10px}.v3-signals{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 20px}.v3-signal{padding:7px 14px;border-radius:40px;background:#f1f1f1;color:#000;font-size:.75rem;font-weight:700}
        .v3-product{border:0;background:#f7f7f7;border-radius:20px;padding:32px;height:100%;box-shadow:none}.v3-rank{font-size:.7rem;font-weight:700;color:#707070}.v3-product-name{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:32px;font-weight:700;color:#000;margin:8px 0 14px}
        .v3-map-shell{background:#f7f7f7;border:0;border-radius:20px;padding:24px 32px 12px;box-shadow:none}
        .v3-map-legend{display:flex;justify-content:flex-end;gap:14px;color:#7b8497;font-size:11px;padding:2px 4px 4px}.v3-map-legend i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
        .v3-overview{border-top:2px solid #000;border-bottom:1px solid #ddd;padding:18px 0 16px;margin:0 0 20px}.v3-overview-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr);gap:34px}.v3-project-name{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:24px;line-height:1.25;font-weight:700;letter-spacing:-.03em}.v3-project-summary{font-size:13px;line-height:1.6;color:#444;margin-top:7px;max-width:760px}.v3-overview-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px 22px;margin-top:15px}.v3-kv{min-width:0}.v3-kv-label{color:#777;font-size:9px;line-height:1.3;font-weight:700;letter-spacing:.1em;text-transform:uppercase}.v3-kv-value{color:#000;font-size:13px;line-height:1.45;font-weight:600;margin-top:3px;overflow-wrap:anywhere}.v3-players{border-left:1px solid #ddd;padding-left:25px}.v3-players-title{font-size:10px;font-weight:700;letter-spacing:.13em;margin-bottom:8px}.v3-player{display:grid;grid-template-columns:78px 1fr auto;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid #eee;font-size:11px}.v3-player-role{color:#777;font-weight:700}.v3-player-company{font-weight:600;overflow-wrap:anywhere}.v3-player-state{font-size:8px;letter-spacing:.06em;color:#777}.v3-timeline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid #ddd;margin-top:15px}.v3-milestone{position:relative;padding:11px 12px 0 0}.v3-milestone:before{content:'';position:absolute;top:-3px;left:0;width:6px;height:6px;background:#000;border-radius:50%}.v3-milestone-date{font-size:12px;font-weight:700}.v3-milestone-name{font-size:10px;color:#777;margin-top:3px}.v3-decision{display:grid;grid-template-columns:105px minmax(0,1fr) minmax(180px,.42fr);gap:20px;align-items:start;padding:14px 0 15px 15px;margin:0 0 20px;border-left:3px solid #000;border-bottom:1px solid #ddd}.v3-decision.now{border-left-color:#16794b}.v3-decision.monitor{border-left-color:#a36a00}.v3-decision.closed{border-left-color:#b42318}.v3-decision-status{font-size:20px;font-weight:700}.v3-decision-label{font-size:9px;color:#777;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}.v3-decision-copy{font-size:13px;line-height:1.55}.v3-context-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid #222;border-bottom:1px solid #ddd}.v3-context{padding:13px 16px 12px 0;margin-right:16px;border-right:1px solid #e5e5e5;min-width:0}.v3-context:last-child{border-right:0;margin-right:0}.v3-context-value{font-size:15px;line-height:1.35;font-weight:700;margin:6px 0 8px;overflow-wrap:anywhere}.v3-context-evidence{font-size:10px;line-height:1.45;color:#777;margin-top:7px}
        .v3-overview-grid{grid-template-columns:1fr;gap:0}.v3-kv-label-row{display:flex;align-items:center;gap:6px}.v3-source{position:relative;display:inline-flex}.v3-source>summary{list-style:none;display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border:1px solid #bbb;border-radius:50%;color:#666;font-size:9px;font-weight:700;cursor:pointer}.v3-source>summary::-webkit-details-marker{display:none}.v3-source[open]>summary{background:#000;color:#fff;border-color:#000}.v3-popover{position:absolute;z-index:20;top:22px;left:0;width:min(340px,80vw);padding:13px 14px;border:1px solid #ccc;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.14);font-size:11px;line-height:1.5;color:#333;text-transform:none;letter-spacing:0}.v3-popover-title{font-size:10px;font-weight:700;letter-spacing:.08em;margin-bottom:7px}.v3-source-row{padding:7px 0;border-top:1px solid #eee}.v3-source-row:first-of-type{border-top:0}.v3-source-row a{color:#000;font-weight:700;text-decoration:underline;text-underline-offset:2px}.v3-source-date{color:#777;margin-left:5px}.v3-hypothesis{margin-top:9px;padding:9px;background:#faf7ef;border-left:2px solid #b47a10}.v3-hypothesis b{display:block;color:#8a5a00;font-size:9px;letter-spacing:.06em;margin-bottom:3px}.v3-hypothesis-source{margin-top:6px}.v3-hypothesis-source a{color:#6f4900;font-weight:700;text-decoration:underline;text-underline-offset:2px}.v3-needs{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:16px}.v3-need-label{font-size:9px;font-weight:700;letter-spacing:.1em;color:#777;margin-right:3px}.v3-need{position:relative}.v3-need>summary{list-style:none;display:inline-flex;padding:5px 9px;border:1px solid #ddd;border-radius:3px;background:#fff;color:#000;font-size:10px;font-weight:600;cursor:pointer}.v3-need>summary::-webkit-details-marker{display:none}.v3-need[open]>summary{border-color:#000}.v3-stage-shell{margin:22px 0 24px;padding:16px 0 14px;border-top:1px solid #222;border-bottom:1px solid #ddd}.v3-stage-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:11px}.v3-stage-current{font-size:12px;font-weight:700}.v3-stage-current span{color:#777;font-size:9px;letter-spacing:.08em;margin-right:7px}.v3-stage-bands{display:grid;grid-template-columns:2fr 4fr 2fr 1fr;gap:2px;margin-bottom:4px}.v3-stage-band{padding:4px 5px;text-align:center;font-size:8px;font-weight:700;letter-spacing:.05em}.v3-stage-band.targeting{background:#eef3fb;color:#315b92}.v3-stage-band.golden{background:#fff2c7;color:#805500}.v3-stage-band.local{background:#f1f1f1;color:#555}.v3-stage-band.closed{background:#f7e7e5;color:#8d3029}.v3-stage-track{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:2px}.v3-stage-item{position:relative;min-height:46px;padding:9px 4px 5px;border-top:3px solid #ddd;color:#777;font-size:9px;line-height:1.25;text-align:center}.v3-stage-item.passed{border-color:#777;color:#444}.v3-stage-item.active{border-color:#000;background:#f7f7f7;color:#000;font-weight:700}.v3-stage-item.active:before{content:'';position:absolute;top:-6px;left:50%;transform:translateX(-50%);width:9px;height:9px;border-radius:50%;background:#000}.v3-stage-unknown{font-size:11px;color:#777;padding:8px 0}.v3-decision-guide{font-size:14px;line-height:1.65;color:#111}.v3-decision-facts{margin:9px 0 0;padding:0;list-style:none}.v3-decision-facts li{position:relative;padding:4px 0 4px 13px;color:#555;font-size:11px;line-height:1.45}.v3-decision-facts li:before{content:'·';position:absolute;left:2px;font-weight:700}.v3-map-summary{display:flex;gap:18px;flex-wrap:wrap;padding:9px 0 12px;color:#555;font-size:10px}.v3-map-summary b{color:#000}.v3-map-next{margin-left:auto}.v3-node-scope{font-size:8px;letter-spacing:.05em}
        /* Result pages: editorial report language aligned with the BD entry screen. */
        [data-testid="stTabs"]{max-width:1180px;margin:24px auto 0}[data-testid="stTabs"] button[role="tab"]{padding:4px 0 11px;font-size:14px;font-weight:600}
        .v3-head{align-items:flex-start;gap:24px;margin:36px 0 28px;padding:0 0 22px;border-bottom:1px solid #ddd}.v3-head h1{font-size:30px;line-height:1.18;letter-spacing:-.035em}.v3-head p{max-width:760px;color:#555;font-size:15px;line-height:1.55}.v3-eyebrow,.v3-label{font-size:10px;letter-spacing:.14em}.v3-step{width:32px;height:32px;border-radius:0;border:1px solid #000;background:#fff;color:#000;font-size:12px}
        .v3-gate{grid-template-columns:130px 1fr auto;gap:24px;min-height:88px;margin-bottom:28px;padding:20px 0 20px 20px;border:0;border-left:3px solid #000;border-bottom:1px solid #ddd;border-radius:0;background:#fff!important}.v3-gate.now{border-left-color:#16794b}.v3-gate.monitor{border-left-color:#a36a00}.v3-gate.closed{border-left-color:#b42318}.v3-gate-status{font-size:22px;letter-spacing:-.02em}.v3-gate-copy{font-size:14px;line-height:1.6}
        .v3-section{margin:30px 0 12px;padding-bottom:8px;border-bottom:1px solid #e5e5e5}.v3-section h3{font-size:14px;color:#000}.v3-section span{color:#707070}
        .v3-card{min-height:128px;padding:19px 4px 17px;border:0;border-top:2px solid #000;border-radius:0;background:#fff}.v3-card:hover{border-top:2px solid #000}.v3-value{font-size:21px;line-height:1.35;margin:9px 0 14px}
        .v3-chip{padding:4px 8px;border:1px solid #d5d5d5;border-radius:3px;background:#fff;font-size:9px;letter-spacing:.06em}.v3-chip.strong,.v3-chip.confirmed{background:#fff;color:#176b45;border-color:#a9cdbd}.v3-chip.medium,.v3-chip.inferred,.v3-chip.likely{background:#fff;color:#8a5a00;border-color:#d8c394}.v3-chip.weak,.v3-chip.unknown,.v3-chip.hypothesis{background:#fff;color:#707070;border-color:#d5d5d5}
        .v3-ai{padding:19px 21px;margin:8px 0 28px;border:0;border-left:3px solid #000;border-radius:0;background:#fafafa}.v3-ai-title{font-size:10px;letter-spacing:.14em;margin-bottom:9px}.v3-ai-copy{font-size:14px;line-height:1.65}
        .v3-tier{padding:4px 9px;border-radius:2px;font-size:9px;letter-spacing:.08em;margin:4px 0 10px}.v3-role{font-size:11px}.v3-company{font-size:17px;margin:7px 0 14px}.v3-meta{grid-template-columns:84px 1fr;gap:8px 10px;font-size:12px;line-height:1.45}
        .v3-question{grid-template-columns:28px 1fr;gap:14px;margin:0;padding:15px 2px;border:0;border-bottom:1px solid #e5e5e5;border-radius:0;background:#fff}.v3-number{width:24px;height:24px;border:1px solid #000;border-radius:0;background:#fff;color:#000;font-size:10px}.v3-question-title{font-size:14px;line-height:1.5}.v3-question-sub{font-size:11px;line-height:1.5;margin-top:5px}
        .v3-talk{margin:0;padding:15px 2px;border:0;border-bottom:1px solid #e5e5e5;border-radius:0;background:#fff}.v3-talk b{font-size:12px}.v3-talk p,.v3-product-copy{font-size:12px;line-height:1.65;margin-top:8px}.v3-signals{gap:6px}.v3-signal{padding:5px 9px;border:1px solid #ddd;border-radius:3px;background:#fff;font-size:10px;font-weight:600}
        .v3-product{padding:19px 4px;border:0;border-top:2px solid #000;border-radius:0;background:#fff}.v3-rank{font-size:9px;letter-spacing:.1em}.v3-product-name{font-size:20px;line-height:1.35;margin:7px 0 12px}.v3-map-shell{padding:20px 28px 10px;border:1px solid #ddd;border-radius:0;background:#fff}
        .bd-entry-hero{max-width:760px;margin:0 auto;padding:8vh 20px 32px;text-align:center}.bd-entry-eyebrow{font-size:9px;line-height:13px;font-weight:700;letter-spacing:.16em;color:#707070}.bd-entry-hero h1{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:clamp(38px,4.5vw,61px);line-height:1.02;letter-spacing:-.045em;margin:16px 0 18px;color:#000}.bd-entry-hero p{max-width:540px;margin:0 auto;color:#555;font-size:14px;line-height:1.6;letter-spacing:-.01em}
        .st-key-bd_entry_composer{max-width:720px;margin:0 auto;padding:11px 13px 10px;border:1px solid #d8d8d8;border-radius:20px;background:#fff;box-shadow:0 11px 30px rgba(0,0,0,.07)}.st-key-bd_entry_composer [data-testid="stTextArea"] textarea{min-height:114px!important;padding:10px 8px!important;background:#fff!important;border:0!important;border-radius:0!important;box-shadow:none!important;font-size:14px;line-height:1.55;resize:none}.st-key-bd_entry_composer [data-testid="stTextArea"] textarea:focus{box-shadow:none!important}.st-key-bd_entry_composer [data-testid="stHorizontalBlock"]{align-items:center;gap:8px}.st-key-bd_entry_composer [data-testid="stPopover"] button{min-height:34px;background:#fff;color:#000;border:1px solid #ddd;padding:7px 12px;font-size:11px}.st-key-bd_entry_composer [data-testid="stPopover"] button:hover{background:#f7f7f7;color:#000;border-color:#aaa}.st-key-bd_entry_composer .stButton>button{min-height:36px;border-radius:18px;padding:7px 15px;font-size:12px}
        .st-key-bd_project_context{max-width:720px;margin:0 auto;padding:21px 22px 18px;border:1px solid #d8d8d8;border-radius:20px;background:#fff;box-shadow:0 11px 30px rgba(0,0,0,.07);animation:bd-context-in .24s ease-out both}.bd-context-head{display:flex;align-items:flex-end;justify-content:space-between;gap:19px;margin-bottom:18px}.bd-context-head h2{font-family:"Samsung Sharp Sans","SamsungOneKorean",Arial,sans-serif;font-size:20px;line-height:1.25;letter-spacing:-.025em;margin:0}.bd-context-head p{color:#707070;font-size:10px;line-height:1.45;margin:0;text-align:right}.bd-context-label{font-size:11px;font-weight:700;color:#000;margin:0 0 6px}.bd-context-section{margin-top:12px}.st-key-bd_building_choices [data-testid="stButtonGroup"],.st-key-bd_stage_choices [data-testid="stButtonGroup"]{gap:5px!important;justify-content:flex-start!important}.st-key-bd_building_choices [data-testid="stButtonGroup"] button,.st-key-bd_stage_choices [data-testid="stButtonGroup"] button{min-height:32px!important;padding:6px 11px!important;border-radius:8px!important;font-size:12px!important;font-weight:600!important;white-space:nowrap!important}.bd-context-question{margin:14px 0 6px}.bd-context-question h3{font-size:12px;line-height:1.45;margin:0 0 4px;color:#000}.bd-context-question p{max-width:600px;font-size:10px;line-height:1.55;margin:0;color:#707070}.bd-context-question strong{color:#404040;font-weight:700}.st-key-bd_project_context [data-testid="stTextArea"] textarea{min-height:90px!important;padding:10px 11px!important;border:1px solid #ddd!important;border-radius:10px!important;background:#fff!important;font-size:12px;line-height:1.5;resize:vertical}.st-key-bd_project_context [data-testid="stTextArea"] textarea::placeholder{color:#a0a0a0!important;opacity:1}.st-key-bd_project_context [data-testid="stTextArea"] textarea:focus{border-color:#000!important;box-shadow:0 0 0 1px #000!important}.st-key-bd_project_context .stButton{margin-top:14px}.st-key-bd_project_context .stButton>button{min-height:36px;font-size:12px}.st-key-bd_project_context [data-testid="column"]:first-child .stButton>button{background:#fff;color:#000;border-color:#ddd}.st-key-bd_project_context [data-testid="column"]:first-child .stButton>button:hover{background:#f7f7f7;border-color:#aaa}
        @keyframes bd-context-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        /* Readability pass: preserve the compact editorial layout while making the decision path scannable. */
        [data-testid="stTabs"] button[role="tab"]{font-size:15px;font-weight:650}
        .v3-head{margin:24px 0 20px;padding-bottom:18px}.v3-head h1{font-size:29px;line-height:1.25;padding:0!important}.v3-head p{font-size:15px;line-height:1.55}.v3-eyebrow,.v3-label{font-size:11px;line-height:1.35;letter-spacing:.06em;text-transform:none}
        .v3-section{margin:22px 0 10px;padding-bottom:8px}.v3-section h3{font-size:18px;line-height:1.4;font-weight:700;padding:0!important}.v3-section span{font-size:11px;line-height:1.4;letter-spacing:.04em;text-align:right}
        .v3-card{min-height:0;padding:16px 4px 15px}.v3-chip{min-height:24px;align-items:center;padding:4px 8px;font-size:11px;line-height:1.25;letter-spacing:0}
        .v3-ai{padding:16px 18px;margin:6px 0 22px}.v3-ai-title{font-size:11px;letter-spacing:.05em;margin-bottom:7px}.v3-ai-copy{font-size:14px;line-height:1.65}
        .v3-tier{padding:5px 9px;font-size:11px;letter-spacing:0}.v3-role{font-size:12px;line-height:1.45}.v3-company{font-size:18px;line-height:1.4;margin:6px 0 12px}.v3-meta{font-size:13px;line-height:1.5}
        .v3-question{padding:14px 2px}.v3-question-title{font-size:14px;line-height:1.55}.v3-question-sub{font-size:12px;line-height:1.5}.v3-talk{padding:14px 2px}.v3-talk b{font-size:13px}.v3-talk p,.v3-product-copy{font-size:13px;line-height:1.6}.v3-signal{padding:6px 10px;font-size:11px}.v3-product{padding:16px 4px}.v3-rank{font-size:11px;letter-spacing:0}.v3-product-name{font-size:20px;margin:6px 0 10px}
        .v3-overview{padding:16px 0 14px;margin-bottom:18px}.v3-project-name{font-size:24px;line-height:1.3}.v3-project-summary{max-width:none;font-size:14px;line-height:1.62;margin-top:6px}.v3-overview-facts{gap:10px 22px;margin-top:14px}.v3-kv-label{font-size:11px;line-height:1.35;letter-spacing:.04em;text-transform:none}.v3-kv-value{font-size:14px;line-height:1.5;margin-top:2px}.v3-timeline-head{display:flex;align-items:baseline;gap:10px;margin-top:18px}.v3-timeline-head b{font-size:12px}.v3-timeline-head span{color:#777;font-size:10px}.v3-timeline{grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin-top:8px}.v3-milestone-date{font-size:12px}.v3-milestone-name{font-size:12px;line-height:1.5;color:#666}.v3-milestone-sources{margin-top:6px;font-size:10px;line-height:1.4}.v3-milestone-sources a{color:#333;font-weight:700;text-decoration:underline;text-underline-offset:2px}.v3-need-label{font-size:11px;letter-spacing:.04em}.v3-need>summary{padding:6px 10px;font-size:11px}.v3-popover{font-size:12px;line-height:1.55}.v3-popover-title,.v3-hypothesis b{font-size:11px;letter-spacing:.03em}
        .st-key-v3_project_overview{margin:0 0 18px;padding:16px 0 14px;border-top:2px solid #000;border-bottom:1px solid #ddd}.v3-overview-head{margin-bottom:4px}.st-key-v3_project_overview [data-testid="stHorizontalBlock"]{gap:28px}.st-key-v3_site_location{height:100%;padding:14px;border:1px solid #ddd;background:#fafafa}.v3-site-label{color:#666;font-size:11px;line-height:1.35;font-weight:700;letter-spacing:.04em}.v3-site-title{display:flex;align-items:center;gap:6px;margin-top:7px;color:#000;font-size:17px;line-height:1.4;font-weight:700}.v3-site-place{margin-top:4px;color:#444;font-size:13px;line-height:1.5}.v3-site-level{display:inline-flex;margin-top:10px;padding:4px 7px;border:1px solid #d2d2d2;background:#fff;color:#444;font-size:11px;line-height:1.3;font-weight:600}.v3-site-note{margin-top:9px;color:#666;font-size:12px;line-height:1.5}.v3-site-unknown{padding:18px 0 12px}.v3-site-unknown strong{display:block;color:#222;font-size:15px;line-height:1.45}.v3-site-unknown span{display:block;margin-top:5px;color:#666;font-size:12px;line-height:1.5}.st-key-v3_site_location [data-testid="stMap"]{margin-top:11px}.v3-site-map-caption{margin-top:6px;color:#777;font-size:11px;line-height:1.45}
        .v3-stage-shell{margin:18px 0 22px;padding:18px 20px 16px;border:1px solid #d8d8d8;border-left:4px solid #000;background:#fafafa}.v3-stage-head{align-items:flex-start;gap:20px;margin-bottom:10px}.v3-stage-copy{min-width:0}.v3-stage-label{color:#666;font-size:12px;line-height:1.35;font-weight:600;margin-bottom:3px}.v3-stage-current{display:flex;align-items:center;gap:8px;font-size:24px;line-height:1.25;font-weight:700;letter-spacing:-.025em}.v3-stage-current strong{font-weight:700}.v3-stage-note{margin-top:5px;color:#555;font-size:13px;line-height:1.5}.v3-stage-gate{flex:0 0 auto;max-width:260px;padding:6px 10px;border:1px solid #cfcfcf;background:#fff;color:#222;font-size:11px;line-height:1.35;font-weight:700}.v3-stage-progress{margin:12px 0 7px;color:#555;font-size:12px;line-height:1.4;font-weight:600}.v3-stage-bands{gap:3px;margin-bottom:5px}.v3-stage-band{padding:5px 6px;font-size:10px;line-height:1.35;letter-spacing:0}.v3-stage-track{gap:3px}.v3-stage-item{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:4px;min-height:56px;padding:10px 5px 6px;border-top-width:3px;background:#fff;color:#666;font-size:11px;line-height:1.3;font-weight:500}.v3-stage-item.passed{border-color:#777;background:#f3f3f3;color:#444}.v3-stage-item.active{border-color:#000;background:#111;color:#fff;font-weight:700}.v3-stage-item.active:before{width:10px;height:10px;background:#111;border:2px solid #fff;box-shadow:0 0 0 1px #111}.v3-stage-state{font-size:10px;line-height:1.2;font-weight:700;color:#666}.v3-stage-item.active .v3-stage-state{color:#fff}.v3-stage-item.upcoming .v3-stage-state{color:#315b92}.v3-stage-unknown{font-size:12px;line-height:1.5}
        .v3-decision{grid-template-columns:120px minmax(0,1fr) minmax(190px,.42fr);gap:18px;padding:15px 0 16px 16px;margin-bottom:18px}.v3-decision-label{font-size:11px;line-height:1.4;letter-spacing:.04em;text-transform:none;margin-bottom:5px}.v3-decision-status{font-size:22px;line-height:1.35}.v3-decision-guide{font-size:14px;line-height:1.65}.v3-decision-facts li{font-size:12px;line-height:1.5}.v3-decision-copy{font-size:13px;line-height:1.6}
        .v3-map-shell{padding:16px 20px 9px}.v3-map-summary{gap:16px;padding:8px 0 11px;font-size:12px;line-height:1.5}.v3-map-legend{font-size:12px;line-height:1.4}.v3-map-next{margin-left:auto}
        .bd-entry-hero{padding:6vh 20px 26px}.bd-entry-eyebrow{font-size:11px;line-height:1.4;letter-spacing:.08em}.bd-entry-hero h1{font-size:clamp(40px,3.8vw,48px);line-height:1.12;margin:13px 0 14px;padding:0!important}.bd-entry-hero p{font-size:15px;line-height:1.6}.st-key-bd_entry_composer [data-testid="stPopover"] button{font-size:13px}.st-key-bd_entry_composer .stButton>button{font-size:14px}.bd-entry-outcomes{text-align:center;margin:16px auto 0;color:#555;font-size:12px;line-height:1.5}.bd-entry-privacy{text-align:center;margin:7px auto;color:#6f6f6f;font-size:12px;line-height:1.45}
        .bd-context-head p{font-size:12px}.bd-context-label{font-size:12px}.bd-context-question h3{font-size:14px}.bd-context-question p{font-size:12px}.st-key-bd_project_context [data-testid="stTextArea"] textarea{font-size:13px}.st-key-bd_project_context .stButton>button{font-size:14px}
        @media(prefers-reduced-motion:reduce){.st-key-bd_project_context{animation:none}}
        @media(max-width:900px){.v3-overview-grid{grid-template-columns:1fr}.v3-players{border-left:0;border-top:1px solid #ddd;padding:15px 0 0}.v3-context-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.v3-context:nth-child(2){border-right:0}.v3-decision{grid-template-columns:92px 1fr}.v3-decision-trigger{grid-column:2}}
        @media(max-width:760px){.v3-head{flex-direction:column;margin:22px 0 18px}.v3-head h1{font-size:25px}.v3-gate{grid-template-columns:1fr}.v3-meta{grid-template-columns:1fr}.block-container{padding-left:1rem!important;padding-right:1rem!important}.v3-overview{padding-top:14px}.v3-project-name{font-size:21px}.v3-overview-facts{grid-template-columns:1fr}.st-key-v3_site_location{margin-top:10px}.v3-timeline{grid-template-columns:1fr;border-top:0;border-left:1px solid #ddd;margin-left:3px}.v3-milestone{padding:0 0 13px 15px}.v3-milestone:before{top:5px;left:-3px}.v3-player{grid-template-columns:65px 1fr}.v3-player-state{grid-column:2}.v3-decision{grid-template-columns:1fr;gap:8px;padding-left:12px}.v3-decision-trigger{grid-column:1}.v3-context-grid{grid-template-columns:1fr}.v3-context,.v3-context:nth-child(2){border-right:0;border-bottom:1px solid #eee;margin-right:0;padding-right:0}.bd-entry-hero{padding:6vh 4px 26px}.bd-entry-hero h1{font-size:38px}.bd-entry-hero p{font-size:15px}.st-key-bd_entry_composer{padding:10px 12px 12px;border-radius:20px}.st-key-bd_entry_composer [data-testid="stHorizontalBlock"]{flex-wrap:wrap}.st-key-bd_entry_composer [data-testid="column"]{min-width:100%!important;width:100%!important}.st-key-bd_entry_composer [data-testid="stPopover"] button,.st-key-bd_entry_composer .stButton>button{width:100%}.st-key-bd_project_context{padding:22px 18px 18px;border-radius:20px}.bd-context-head{display:block;margin-bottom:18px}.bd-context-head h2{font-size:21px}.bd-context-head p{text-align:left;margin-top:7px}.st-key-bd_building_choices [data-testid="stButtonGroup"],.st-key-bd_stage_choices [data-testid="stButtonGroup"]{flex-wrap:wrap!important;gap:5px!important}.st-key-bd_building_choices [data-testid="stButtonGroup"] button,.st-key-bd_stage_choices [data-testid="stButtonGroup"] button{min-height:36px!important;padding:6px 11px!important;font-size:12px!important}.st-key-bd_project_context>.stVerticalBlock>div:last-child [data-testid="stHorizontalBlock"]{flex-wrap:nowrap}.bd-entry-outcomes{line-height:1.7;padding:0 24px}}
        @media(max-width:760px){.v3-popover{position:fixed;z-index:999;top:16%;left:16px;right:16px;width:auto;max-height:68vh;overflow:auto}.v3-stage-shell{padding:16px 14px}.v3-stage-head{display:block}.v3-stage-gate{display:inline-block;max-width:none;margin-top:10px}.v3-stage-bands{display:none}.v3-stage-track{grid-template-columns:1fr}.v3-stage-item{min-height:0;flex-direction:row;justify-content:space-between;padding:9px 10px 9px 17px;border-top:0;border-left:3px solid #ddd;text-align:left}.v3-stage-item.active{border-left-color:#000}.v3-stage-item.active:before{top:50%;left:-6px;transform:translateY(-50%)}.v3-decision-facts li{font-size:12px}.v3-map-next{width:100%;margin-left:0}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe(value: object) -> str:
    return html.escape(str(value or "Not confirmed"))


def _safe_emphasis(value: object) -> str:
    """Escape copy while allowing bounded **strong** emphasis."""

    escaped = _safe(value)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _badge(value: str, language: str = "ko") -> str:
    state = _safe(value).lower()
    labels = {
        "strong": "근거 충분",
        "medium": "근거 보통",
        "weak": "근거 제한",
        "confirmed": ui(language, "confirmed"),
        "inferred": ui(language, "inferred"),
        "likely": ui(language, "inferred"),
        "hypothesis": "확인 필요 가설",
        "candidate": "확인 필요 후보",
        "partial": "일부 확인된 위치",
        "unconfirmed": ui(language, "unknown"),
        "unknown": ui(language, "unknown"),
    }
    return f"<span class='v3-chip {state}'>{_safe(labels.get(state, state))}</span>"


def _header(step: int, eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='v3-head'><div><div class='v3-eyebrow'>{_safe(eyebrow)}</div><h1>{_safe(title)}</h1><p>{_safe(subtitle)}</p></div><div class='v3-step'>{step}</div></div>", unsafe_allow_html=True)


def _section(title: str, meta: str = "") -> None:
    st.markdown(f"<div class='v3-section'><h3>{_safe(title)}</h3><span class='v3-label'>{_safe(meta)}</span></div>", unsafe_allow_html=True)


STAGE_LABELS = ("사업기획", "타당성", "MP", "설계(SD)", "설계(DD)", "설계(CD)", "인허가", "시공", "운영종료")


def _matching_fact(items: list[object], keywords: tuple[str, ...]) -> object | None:
    best_item = None
    best_score = 0
    for item in items:
        haystack = f"{getattr(item, 'claim', '')} {getattr(item, 'rationale', '')}".lower()
        score = sum(keyword in haystack for keyword in keywords)
        if score > best_score:
            best_item, best_score = item, score
    return best_item


def _short(value: object, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _compact_fact_value(item: object | None, kind: str) -> str:
    claim = str(getattr(item, "claim", "") or "")
    if not claim:
        return "Not identified"
    if kind == "location":
        match = re.search(r"(?:site|location)\s*:\s*([^).;]+)", claim, flags=re.IGNORECASE)
        return match.group(1).strip() if match else claim
    if kind == "investment":
        values = re.findall(r"(?:VND|USD|US\$|\$)\s*(?:approx\.?\s*)?\d[\d.,–-]*\s*(?:trillion|billion|million|m|bn)?", claim, flags=re.IGNORECASE)
        return " / ".join(dict.fromkeys(value.strip() for value in values)) or "Not identified"
    if kind == "scale":
        match = re.search(
            r"~?\s*[\d.,]+\s*(?:hectares?|ha|sqm|m2|m²|평|units?|lines?|beds?|tons?|mw|gw)",
            claim,
            flags=re.IGNORECASE,
        )
        return match.group(0).strip() if match else "Not identified"
    return claim


def _display_value(value: object) -> str:
    text = str(value or "").strip()
    return "Not identified" if not text or text.lower() in {"unknown", "not confirmed", "n/a", "none", "-"} else text


def _display_label(value: object) -> str:
    text = _display_value(value)
    return "미확인" if text == "Not identified" else text


def _user_copy(value: object) -> str:
    text = _display_label(value)
    replacements = (
        ("Not confirmed", "미확인"),
        ("Not identified", "미확인"),
        ("Excel 규칙", "분류 규칙"),
        ("AI Context", "문맥 근거"),
        ("기사 맥락", "수집된 맥락"),
        ("Vendor", "공급사"),
        ("shortlist", "후보 목록"),
        ("Spec-in", "사양 반영"),
        ("Spec", "사양"),
        ("Scope", "범위"),
        ("Trigger", "확인 신호"),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def _evidence_label(value: object) -> str:
    status = _display_value(value).lower()
    if status == "partial":
        return "일부 확인"
    if status == "unconfirmed":
        return "미확인"
    return {
        "confirmed": "확인된 근거",
        "likely": "정황상 유력",
        "inferred": "정황상 유력",
        "hypothesis": "확인 필요 가설",
        "unknown": "미확인",
        "not identified": "미확인",
    }.get(status, _display_label(value))


def _actor_for(result: BDV3AnalysisResult, aliases: tuple[str, ...]) -> object | None:
    return next(
        (
            actor
            for actor in result.v2_snapshot.relationship_map.actors
            if any(alias in f"{actor.role} {actor.organization}".lower() for alias in aliases)
        ),
        None,
    )


def _source_label_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return host or "원문 출처"


def _best_legacy_source_label(url: str, labels: list[str], used: set[int]) -> str:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    host_parts = [part for part in host.split(".") if part not in {"com", "org", "net", "gov", "vn"}]
    candidates: list[tuple[int, int, int, str]] = []
    for index, label in enumerate(labels):
        compact = re.sub(r"[^a-z0-9]", "", label.casefold())
        if index in used:
            continue
        for part in host_parts:
            if not part or part not in compact:
                continue
            rank = 0 if compact == part else 1 if compact.startswith(part) else 2
            candidates.append((rank, len(label), index, label))
            break
    if candidates:
        _rank, _length, index, label = min(candidates)
        used.add(index)
        return label
    return _source_label_from_url(url)


def _source_rows(labels: list[str], urls: list[str], dates: list[str]) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Return rules and source rows while repairing legacy unpaired provenance."""
    clean_labels = [str(label).strip() for label in labels if str(label).strip()]
    rules = [label.removeprefix("rule:") for label in clean_labels if label.startswith("rule:")]
    source_labels = [label for label in clean_labels if not label.startswith("rule:")]
    aligned = len(clean_labels) == len(urls) and all(
        not label.startswith("rule:") or not str(urls[index]).strip()
        for index, label in enumerate(clean_labels)
    )
    rows: list[tuple[str, str, str]] = []
    if aligned:
        for index, label in enumerate(clean_labels):
            if label.startswith("rule:"):
                continue
            rows.append((label, str(urls[index]).strip(), str(dates[index]).strip() if index < len(dates) else ""))
        return rules, rows

    # Older saved results flattened labels and URLs independently. In that
    # shape, URL order is still reliable but label index is not. Match a
    # publisher label by URL host and suppress duplicate attribution variants.
    used: set[int] = set()
    seen_urls: set[str] = set()
    for index, value in enumerate(urls):
        url = str(value).strip()
        if not url.startswith(("https://", "http://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        label = _best_legacy_source_label(url, source_labels, used)
        date = str(dates[index]).strip() if index < len(dates) else ""
        rows.append((label, url, date))
    if not rows:
        rows.extend((label, "", str(dates[index]).strip() if index < len(dates) else "") for index, label in enumerate(source_labels))
    return rules, rows


def _source_popover(item: object | None, *, hypothesis: object | None = None, summary_label: str = "i", need: bool = False) -> str:
    labels = list(getattr(item, "source_labels", []) or getattr(item, "evidence_labels", []) or [])
    urls = list(getattr(item, "source_urls", []) or [])
    dates = list(getattr(item, "source_dates", []) or [])
    status = _evidence_label(getattr(item, "credibility", None) or getattr(item, "status", None))
    _rules, sources = _source_rows(labels, urls, dates)
    rows = []
    for label, url, date in sources:
        if not str(url).startswith(("https://", "http://")):
            continue
        date_html = f"<span class='v3-source-date'>{_safe(date)}</span>" if date else ""
        source_html = f"<a href='{html.escape(str(url), quote=True)}' target='_blank' rel='noopener noreferrer'>{_safe(label)}</a>"
        rows.append(f"<div class='v3-source-row'>{source_html}{date_html}</div>")
    if not rows:
        rows.append("<div class='v3-source-row'>확인 가능한 원문 링크가 없습니다.</div>")
    hypothesis_html = ""
    if hypothesis is not None:
        hypothesis_claim = _short(getattr(hypothesis, "claim", ""), 200)
        hypothesis_labels = list(getattr(hypothesis, "source_labels", []) or getattr(hypothesis, "evidence_labels", []) or [])
        hypothesis_urls = list(getattr(hypothesis, "source_urls", []) or [])
        hypothesis_dates = list(getattr(hypothesis, "source_dates", []) or [])
        _hypothesis_rules, hypothesis_sources = _source_rows(hypothesis_labels, hypothesis_urls, hypothesis_dates)
        hypothesis_links = []
        for label, url, date in hypothesis_sources:
            if not str(url).startswith(("https://", "http://")):
                continue
            date_html = f"<span class='v3-source-date'>{_safe(date)}</span>" if date else ""
            hypothesis_links.append(
                f"<div class='v3-hypothesis-source'><a href='{html.escape(str(url), quote=True)}' target='_blank' rel='noopener noreferrer'>{_safe(label)}</a>{date_html}</div>"
            )
        if hypothesis_claim and hypothesis_links:
            hypothesis_html = (
                f"<div class='v3-hypothesis'><b>확인해볼 단서</b>{_safe(hypothesis_claim)}"
                f"{''.join(hypothesis_links)}</div>"
            )
    css_class = "v3-need" if need else "v3-source"
    return (
        f"<details class='{css_class}'><summary>{_safe(summary_label)}</summary><div class='v3-popover'>"
        f"<div class='v3-popover-title'>{_safe(status)}</div>{''.join(rows)}{hypothesis_html}</div></details>"
    )


def _hypothesis_for(result: BDV3AnalysisResult, keywords: tuple[str, ...]) -> object | None:
    intelligence = result.v2_snapshot.project_intelligence
    candidate = _matching_fact([*intelligence.ecosystem_candidates, *intelligence.historical_projects], keywords)
    source_urls = list(getattr(candidate, "source_urls", []) or []) if candidate else []
    return candidate if any(str(url).startswith(("https://", "http://")) for url in source_urls) else None


def _kv(label: str, value: object, item: object | None, *, hypothesis: object | None = None) -> str:
    return (
        "<div class='v3-kv'>"
        f"<div class='v3-kv-label-row'><div class='v3-kv-label'>{_safe(label)}</div>{_source_popover(item, hypothesis=hypothesis)}</div>"
        f"<div class='v3-kv-value'>{_safe(_display_value(value))}</div></div>"
    )


LOCATION_PRECISION_LABELS = {
    "exact_site": "정확한 부지 수준까지 위치 확인",
    "industrial_park": "산업단지 수준까지 위치 확인",
    "district": "District 수준까지 위치 확인",
    "city": "도시 수준까지 위치 확인",
    "province": "성·광역 지역 수준까지 위치 확인",
    "region": "권역 수준까지 위치 확인",
    "country": "국가 수준까지 위치 확인",
    "unknown": "위치 수준 미확인",
}


def _location_title(location: ProjectLocation) -> str:
    return next((
        value for value in (
            location.site_name,
            location.address,
            location.industrial_park,
            location.district,
            location.city,
            location.province,
            location.region,
            location.country,
        ) if value
    ), "프로젝트 부지 위치 미확인")


def _location_place(location: ProjectLocation, title: str) -> str:
    values = [
        location.address,
        location.industrial_park,
        location.district,
        location.city,
        location.province,
        location.region,
        location.country,
    ]
    return ", ".join(dict.fromkeys(
        value for value in values if value and value.casefold() != title.casefold()
    ))


def _location_map_rows(location: ProjectLocation) -> list[dict[str, float]]:
    if location.status == "unknown" or location.latitude is None or location.longitude is None:
        return []
    return [{"lat": float(location.latitude), "lon": float(location.longitude)}]


def _location_zoom(location: ProjectLocation) -> int:
    return {
        "exact_site": 14,
        "industrial_park": 11,
        "district": 10,
        "city": 9,
        "province": 7,
        "region": 6,
        "country": 4,
        "unknown": 4,
    }.get(location.precision, 7)


def _location_search_query(location: ProjectLocation) -> str:
    return ", ".join(dict.fromkeys(
        value for value in (
            location.address,
            location.site_name,
            location.industrial_park,
            location.district,
            location.city,
            location.province,
            location.country,
        ) if value
    ))


def _site_location_card(location: ProjectLocation) -> None:
    with st.container(key="v3_site_location"):
        st.markdown("<div class='v3-site-label'>부지 위치</div>", unsafe_allow_html=True)
        if location.status == "unknown":
            st.markdown(
                "<div class='v3-site-unknown'><strong>프로젝트 부지 위치가 아직 확인되지 않았습니다.</strong>"
                "<span>확인된 위치 근거가 추가되면 지도와 함께 표시합니다.</span></div>",
                unsafe_allow_html=True,
            )
            return

        title = _location_title(location)
        place = _location_place(location, title)
        place_html = f"<div class='v3-site-place'>{_safe(place)}</div>" if place else ""
        st.markdown(
            f"<div class='v3-site-title'><span>📍</span><span>{_safe(title)}</span>{_source_popover(location)}</div>"
            f"{place_html}<div class='v3-site-level'>{_safe(LOCATION_PRECISION_LABELS.get(location.precision, '위치 범위 확인'))}</div>",
            unsafe_allow_html=True,
        )
        rows = _location_map_rows(location)
        if rows:
            st.map(
                rows,
                latitude="lat",
                longitude="lon",
                size=75,
                zoom=_location_zoom(location),
                width="stretch",
                height=210,
            )
            st.markdown(
                "<div class='v3-site-map-caption'>좌표 근거가 확인된 위치만 표시합니다. 부지 경계나 길찾기 정보는 제공하지 않습니다.</div>",
                unsafe_allow_html=True,
            )
        else:
            query = _location_search_query(location)
            if query:
                st.iframe(
                    f"https://www.google.com/maps?q={quote_plus(query)}&output=embed",
                    height=210,
                )
                st.markdown(
                    "<div class='v3-site-map-caption'>공개된 장소명을 기준으로 표시한 참고 위치입니다. 정확한 부지 좌표나 경계는 확인되지 않았습니다.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='v3-site-note'>지도에서 검색할 수 있는 위치명이 아직 확인되지 않았습니다.</div>",
                    unsafe_allow_html=True,
                )


def _timeline_event_type(value: str) -> str:
    text = value.casefold()
    categories = (
        ("planning_announcement", ("mou", "memorandum", "roadmap", "협약", "양해각서")),
        ("investment", ("investment", "funding", "투자")),
        ("site", ("site selected", "land allocation", "부지 확정")),
        ("design", ("design release", "architect appointed", "design consultant", "설계 착수", "설계사 선정")),
        ("permit", ("permit filed", "permit approved", "license granted", "인허가")),
        ("contractor", ("epc appointed", "gc appointed", "contract awarded", "contractor appointed", "epc 선정", "시공사 선정")),
        ("construction", ("groundbreaking", "construction start", "broke ground", "착공")),
        ("operation", ("completed", "commissioned", "inaugurated", "준공", "가동", "개소")),
    )
    return next((name for name, markers in categories if any(marker in text for marker in markers)), "progress")


def _timeline_source_rows(result: BDV3AnalysisResult, item: object) -> list[tuple[str, str, str]]:
    labels = list(getattr(item, "evidence_labels", []) or [])
    urls = list(getattr(item, "source_urls", []) or [])
    dates = list(getattr(item, "source_dates", []) or [])
    _rules, rows = _source_rows(labels, urls, dates)
    linked = [row for row in rows if row[1].startswith(("https://", "http://"))]
    if linked:
        return linked

    item_text = f"{getattr(item, 'milestone', '')} {' '.join(labels)}".casefold()
    best_fact = None
    best_score = 0
    for fact in result.v2_snapshot.project_intelligence.current_project_facts:
        fact_text = f"{fact.claim} {' '.join(fact.evidence_labels)}".casefold()
        tokens = {token for token in re.findall(r"[a-z0-9가-힣]{3,}", item_text) if token not in {"project", "news", "vietnam"}}
        score = sum(token in fact_text for token in tokens)
        if score > best_score and any(str(url).startswith(("https://", "http://")) for url in fact.source_urls):
            best_fact, best_score = fact, score
    if best_fact is None:
        return []
    _rules, rows = _source_rows(best_fact.evidence_labels, best_fact.source_urls, best_fact.source_dates)
    return [row for row in rows if row[1].startswith(("https://", "http://"))]


def _public_progress_events(result: BDV3AnalysisResult) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    negative_markers = (
        "no public evidence", "not disclosed", "not announced", "not confirmed",
        "공개 근거 없음", "미공개", "확인되지",
    )
    background_markers = (
        "existing/operational campus", "campus is operational", "general campus",
        "시장 배경", "일반적인 캠퍼스",
    )
    for item in result.v2_snapshot.project_intelligence.project_timeline:
        text = item.milestone.casefold()
        campus_background = "campus" in text and any(marker in text for marker in ("operational", "opened previously", "existing facility"))
        if campus_background or any(marker in text for marker in (*negative_markers, *background_markers)):
            continue
        key = (item.date_or_period, _timeline_event_type(item.milestone))
        rows = _timeline_source_rows(result, item)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "date": item.date_or_period,
                "milestone": item.milestone,
                "credibility": item.credibility,
                "sources": rows,
            }
            continue
        existing_sources = list(existing["sources"])
        seen_urls = {row[1] for row in existing_sources}
        existing_sources.extend(row for row in rows if row[1] not in seen_urls)
        existing["sources"] = existing_sources
        if len(item.milestone) < len(str(existing["milestone"])):
            existing["milestone"] = item.milestone
    return sorted(grouped.values(), key=lambda event: str(event["date"]), reverse=True)[:5]


def _rule_only_customer_need_claims(result: BDV3AnalysisResult) -> set[str]:
    return {
        evidence.claim
        for evidence in result.v2_snapshot.context.customer_needs
        if any(str(label).startswith("rule:") for label in evidence.source_labels)
        and evidence.rationale.startswith("명시적 고객 니즈 키워드 감지")
    }


def _project_overview(result: BDV3AnalysisResult) -> None:
    intelligence = result.v2_snapshot.project_intelligence
    timeline = _public_progress_events(result)
    current_facts = intelligence.current_project_facts
    investment = _matching_fact(current_facts, ("total investment", "capital", "capex", "usd", "vnd", "trillion", "million"))
    scale = _matching_fact(current_facts, ("capacity", "capa", "area", "hectare", "sqm", "m2", "규모", "면적", "생산량"))
    owner = _actor_for(result, ("owner", "developer"))
    building = result.v2_snapshot.context.building_type
    facts_html = "".join(
        [
            _kv("프로젝트 유형", result.building_type.value, building),
            _kv("사업주 / 개발사", intelligence.owner_summary or getattr(owner, "organization", None), owner),
            _kv("투자 규모", _compact_fact_value(investment, "investment"), investment, hypothesis=_hypothesis_for(result, ("investment", "capital", "capex"))),
            _kv("시설 / 생산 규모", _compact_fact_value(scale, "scale"), scale, hypothesis=_hypothesis_for(result, ("capacity", "area", "hectare", "규모"))),
        ]
    )
    if timeline:
        timeline_cards = []
        for event in timeline:
            source_links = " · ".join(
                f"<a href='{html.escape(url, quote=True)}' target='_blank' rel='noopener noreferrer'>{_safe(label)}</a>"
                for label, url, _date in list(event["sources"])[:3]
            )
            source_html = f"<div class='v3-milestone-sources'>{source_links}</div>" if source_links else ""
            timeline_cards.append(
                f"<div class='v3-milestone'><div class='v3-milestone-date'>{_safe(event['date'] or 'Not identified')}</div>"
                f"<div class='v3-milestone-name'>{_safe(event['milestone'])}</div>{source_html}</div>"
            )
        timeline_html = (
            "<div class='v3-timeline-head'><b>공개 확인된 진행 이력</b><span>동일 사건의 반복 보도는 하나로 묶었습니다.</span></div>"
            f"<div class='v3-timeline'>{''.join(timeline_cards)}</div>"
        )
    else:
        timeline_html = ""
    needs = []
    rule_only_claims = _rule_only_customer_need_claims(result)
    for fact, evidence in zip(result.customer_needs, result.v2_snapshot.context.customer_needs):
        if evidence.claim in rule_only_claims:
            continue
        needs.append(_source_popover(evidence, summary_label=fact.value, need=True))
        if len(needs) >= 3:
            break
    needs_html = "<div class='v3-needs'><span class='v3-need-label'>고객이 해결하려는 과제</span>" + ("".join(needs) if needs else "<span class='v3-kv-value'>미확인</span>") + "</div>"
    with st.container(key="v3_project_overview"):
        st.markdown(
            f"<div class='v3-overview-head'><div class='v3-label'>프로젝트 개요</div>"
            f"<div class='v3-project-name'>{_safe(result.opportunity_title)}</div>"
            f"<div class='v3-project-summary'>{_safe(result.executive_summary)}</div></div>",
            unsafe_allow_html=True,
        )
        project_col, location_col = st.columns([2, 1], gap="large")
        with project_col:
            st.markdown(
                f"<div class='v3-overview-facts'>{facts_html}</div>{timeline_html}{needs_html}",
                unsafe_allow_html=True,
            )
        with location_col:
            _site_location_card(intelligence.project_location)


def _stage_index(value: str) -> int | None:
    normalized = str(value or "").lower().replace(" ", "")
    checks = (
        (8, ("운영인허가", "프로젝트종료", "운영종료", "operation", "closed")),
        (7, ("시공", "construction")),
        (6, ("건설인허가", "인허가", "permit")),
        (5, ("설계-cd", "설계(cd)", "cd(")),
        (4, ("설계-dd", "설계(dd)", "dd(")),
        (3, ("설계-sd", "설계(sd)", "sd(")),
        (2, ("masterplan", "mp")),
        (1, ("타당성", "feasibility")),
        (0, ("사업기획", "planning")),
    )
    return next((index for index, tokens in checks if any(token in normalized for token in tokens)), None)


def _stage_journey(result: BDV3AnalysisResult) -> None:
    index = _stage_index(result.project_stage.value)
    gate = result.v2_snapshot.stage_gate.status
    gate_labels = {
        "targeting": "Targeting · 초기 관계 형성",
        "golden_time": "Golden Time · 제안 적기",
        "local_action": "Local Action · 잔여 기회 공략",
        "closed": "Closed · 현재 기회 종료",
        "unknown": "영업 구간 미확인",
    }
    gate_notes = {
        "targeting": "투자 준비 단계 · 의사결정 구조와 초기 요구사항을 확인할 시점",
        "golden_time": "설계 영향 구간 · 사양과 발주 구조에 관여할 우선 시점",
        "local_action": "시공 진행 구간 · 미발주 패키지와 변경 범위에 집중할 시점",
        "closed": "현재 프로젝트 종료 구간 · 운영·리트로핏·후속 확장만 분리 검토",
        "unknown": "근거가 부족해 영업 구간을 확정하지 못했습니다.",
    }
    stage_source = result.v2_snapshot.context.business_stage
    items = []
    for step, label in enumerate(STAGE_LABELS):
        css = "active" if step == index else "passed" if index is not None and step < index else "upcoming"
        state_label = "<span class='v3-stage-state'>현재</span>" if step == index else "<span class='v3-stage-state'>다음</span>" if index is not None and step == index + 1 else ""
        items.append(f"<div class='v3-stage-item {css}'><span>{_safe(label)}</span>{state_label}</div>")
    current = STAGE_LABELS[index] if index is not None else _display_label(result.project_stage.value)
    if index is None:
        progress = "현재 위치 미확인"
    elif index + 1 < len(STAGE_LABELS):
        progress = f"{index + 1} / {len(STAGE_LABELS)} · 다음 단계: {STAGE_LABELS[index + 1]}"
    else:
        progress = f"{index + 1} / {len(STAGE_LABELS)} · 현재 사업 단계의 마지막 구간"
    unknown = "<div class='v3-stage-unknown'>현재 단계를 근거로 확정하지 못해 바에 표시하지 않았습니다.</div>" if index is None else ""
    st.markdown(
        "<div class='v3-stage-shell'>"
        f"<div class='v3-stage-head'><div class='v3-stage-copy'><div class='v3-stage-label'>현재 사업 단계</div><div class='v3-stage-current'><strong>{_safe(current)}</strong>{_source_popover(stage_source)}</div><div class='v3-stage-note'>{_safe(gate_notes.get(gate, gate_notes['unknown']))}</div></div><div class='v3-stage-gate'>{_safe(gate_labels.get(gate, gate_labels['unknown']))}</div></div>"
        f"<div class='v3-stage-progress'>{_safe(progress)}</div>"
        "<div class='v3-stage-bands'><div class='v3-stage-band targeting'>Targeting · 초기 관계 형성</div><div class='v3-stage-band golden'>Golden Time · 제안 적기</div><div class='v3-stage-band local'>Local Action · 잔여 기회</div><div class='v3-stage-band closed'>Closed</div></div>"
        f"<div class='v3-stage-track'>{''.join(items)}</div>{unknown}</div>",
        unsafe_allow_html=True,
    )


def _decision_guidance(result: BDV3AnalysisResult) -> tuple[str, list[str]]:
    stage = _display_value(result.project_stage.value)
    epc = _actor_for(result, ("epc", "general contractor", "gc "))
    epc_name = _display_value(getattr(epc, "organization", None)) if epc else "Not identified"
    if epc_name == "Not identified":
        epc_phrase = "EPC/GC 선정 여부와 담당 조직이 아직 공개 근거로 확인되지 않았습니다."
    else:
        epc_phrase = f"현재 확인된 EPC/GC 후보는 {epc_name}입니다. 참여 범위와 선정 상태는 직접 검증해야 합니다."
    if result.status == "now":
        action = "아직 의사결정 구조와 열려 있는 사양을 확인할 여지가 있으므로, 지금 접촉해 EPC 선정 상태와 다음 발주 시점을 확인하는 것이 좋습니다."
    elif result.status == "monitor":
        action = "즉시 제안하기보다 다음 Trigger를 모니터링하고, 사양·발주 범위가 열리는 시점에 접촉하는 것이 좋습니다."
    else:
        action = "현재 프로젝트의 광범위한 신규 진입은 중단하고 O&M, 리트로핏 또는 후속 확장 기회만 분리해 확인하는 것이 좋습니다."
    guide = f"실제 확인된 최근 사실을 기준으로 현재 사업단계는 ‘{stage}’입니다. {epc_phrase} {action}"
    timeline = result.v2_snapshot.project_intelligence.project_timeline[:2]
    facts = [f"{item.date_or_period}: {_short(item.milestone)}" for item in timeline]
    if not facts:
        facts = [_short(item.claim) for item in result.v2_snapshot.project_intelligence.current_project_facts[:2]]
    return guide, facts


def _sales_stage_guidance(result: BDV3AnalysisResult) -> tuple[str, list[str]]:
    """Create a short sales explanation from existing analysis outputs only."""

    v2 = result.v2_snapshot
    stage_index = _stage_index(result.project_stage.value)
    stage = STAGE_LABELS[stage_index] if stage_index is not None else _display_label(result.project_stage.value)
    known_actors = [
        actor for actor in v2.relationship_map.actors
        if actor.temporal_scope == "current" and actor.actor_status in {"confirmed", "likely"}
    ]
    epc = next(
        (actor for actor in known_actors if any(token in actor.role.casefold() for token in ("epc", "general contractor", "gc"))),
        None,
    )
    epc_name = _display_value(getattr(epc, "organization", None)) if epc else "Not identified"

    gap_parts = [
        *result.relationship_map.research_gaps,
        *v2.relationship_map.research_gaps,
        *v2.relationship_map.unknown_critical_actors,
        *result.stakeholder_unknowns,
        *v2.project_intelligence.unresolved_gaps,
        *(item.topic for item in v2.information_to_confirm),
    ]
    signal_parts = [
        *gap_parts,
        *(item.claim for item in v2.project_intelligence.current_project_facts),
        *(item.claim for item in v2.project_intelligence.open_scopes),
        *v2.project_intelligence.watch_signals,
        v2.project_intelligence.next_trigger,
        v2.can_we_enter.timing.rationale,
        v2.can_we_enter.openness.rationale,
    ]
    gap_text = " ".join(str(part) for part in gap_parts).casefold()
    signal_text = " ".join(str(part) for part in signal_parts).casefold()

    def has(text: str, *tokens: str) -> bool:
        return any(token in text for token in tokens)

    epc_unknown = epc_name == "Not identified" and has(gap_text, "epc", "gc", "contractor", "시공사")
    design_unknown = has(gap_text, "architect", "design", "engineering", "spec", "설계", "사양")
    investment_unknown = has(gap_text, "investment", "funding", "capital", "budget", "투자", "자금", "예산")
    procurement_unknown = has(gap_text, "procurement", "tender", "vendor", "award", "발주", "조달", "구매")
    open_scope = bool(v2.project_intelligence.open_scopes) or has(
        signal_text, "open scope", "remains open", "unawarded", "미발주", "열려"
    )

    if stage_index is None:
        stage_sentence = f"현재 프로젝트 단계는 **{stage}**이며, 다음 의사결정 시점은 아직 확인되지 않았습니다."
    else:
        stage_sentence = f"현재 프로젝트는 **{stage} 단계**로 확인됩니다."

    if result.status == "closed" or stage_index == 8:
        meaning = "현재 프로젝트의 신규 발주 기회는 대부분 종료된 것으로 보여, **운영 이후의 별도 기회로 구분해 볼 필요가 있습니다.**"
        action = "지금은 **O&M·리트로핏 수요와 후속 확장 계획을 확인할 시점**입니다."
    elif stage_index is not None and stage_index >= 7:
        if open_scope or procurement_unknown:
            meaning = "공사가 진행 중이지만 **일부 공급 범위나 조달 주체는 아직 열려 있을 가능성이 있습니다.**"
            action = "지금은 **미발주 패키지와 현장 구매 담당자, 변경 가능 범위를 확인할 시점**입니다."
        else:
            meaning = "주요 설계와 시공 구조가 이미 정해졌을 가능성이 높아 **신규 사양 반영 여지는 제한적일 수 있습니다.**"
            action = "지금은 **현장 변경 요청과 추가 공사 범위가 남아 있는지 확인할 시점**입니다."
    elif stage_index is not None and 3 <= stage_index <= 6:
        if design_unknown:
            meaning = "설계가 진행 중이지만 **주요 사양의 결정 일정과 영향 주체는 아직 확인되지 않았습니다.**"
            action = "지금은 **사양 확정 일정과 설계·기술 승인 담당자를 확인하고 제안 범위를 준비할 시점**입니다."
        elif procurement_unknown or open_scope:
            meaning = "설계 방향은 구체화되고 있으나 **발주 범위와 공급사 선정 절차가 아직 열려 있을 가능성이 있습니다.**"
            action = "지금은 **발주 일정과 공급사 등록·선정 절차를 확인할 시점**입니다."
        elif epc_unknown:
            meaning = "설계 단계에 진입했지만 **EPC/시공사와 실행 책임 조직은 아직 확인되지 않았습니다.**"
            action = "지금은 **EPC 선정 현황과 설계 영향 주체를 확인할 시점**입니다."
        else:
            meaning = f"**EPC/시공사 {epc_name}**가 확인돼 실행 구조가 구체화되고 있습니다."
            action = "지금은 **담당 조직과 조달 일정을 확인해 남은 제안 범위를 좁힐 시점**입니다."
    else:
        if investment_unknown:
            meaning = "사업 구상은 확인됐지만 **투자 승인과 자금 집행 일정은 아직 정해지지 않은 것으로 보입니다.**"
            if epc_unknown:
                action = "지금은 **투자 승인 일정과 실제 의사결정자, EPC 선정 계획을 함께 확인할 시점**입니다."
            else:
                action = "지금은 **투자 승인 일정과 실제 의사결정자를 확인할 시점**입니다."
        elif epc_unknown and design_unknown:
            meaning = "아직 **EPC/시공사와 주요 사양의 결정 주체가 확인되지 않아**, 사업 구조가 확정되기 전일 가능성이 있습니다."
            action = "지금은 **EPC 선정 현황과 사양 결정 일정, 향후 발주 계획을 확인할 적기**입니다."
        elif epc_unknown:
            meaning = "아직 **EPC/시공사와 실행 담당 조직이 확인되지 않아**, 주요 사업 구조가 정해지기 전일 가능성이 있습니다."
            action = "지금은 **EPC 선정 현황과 향후 발주 일정을 확인할 적기**입니다."
        elif design_unknown:
            meaning = "사업 방향은 확인됐지만 **설계·사양을 누가 언제 결정하는지는 아직 확인되지 않았습니다.**"
            action = "지금은 **사양 결정 일정과 영향 주체를 확인해 초기 제안 접점을 만들 시점**입니다."
        else:
            meaning = "초기 사업 구조가 구체화되는 단계로, **아직 관계 형성과 요구사항 반영 여지가 있을 가능성이 있습니다.**"
            action = "지금은 **다음 의사결정 일정과 핵심 관계자의 우선 과제를 확인할 시점**입니다."

    timeline = _public_progress_events(result)[:2]
    facts = [f"{item['date']}: {_short(item['milestone'])}" for item in timeline]
    if not facts:
        facts = [_short(item.claim) for item in v2.project_intelligence.current_project_facts[:2]]
    return " ".join((stage_sentence, meaning, action)), facts


def _node_actor(result: BDV3AnalysisResult, node: object) -> object | None:
    company = _display_value(getattr(node, "company", None))
    actors = result.v2_snapshot.relationship_map.actors
    if company != "Not identified":
        exact = next((actor for actor in actors if _display_value(actor.organization).lower() == company.lower()), None)
        if exact:
            return exact
    role = f"{getattr(node, 'node_id', '')} {getattr(node, 'role', '')}".lower()
    aliases = ("epc",) if "epc" in role else ("design", "architect", "engineering") if any(token in role for token in ("design", "architect", "engineering")) else ("investor", "capital", "fi") if "fi" in role else ("owner",)
    return _actor_for(result, aliases)


def _unknown_roles_for_stage(result: BDV3AnalysisResult) -> list[tuple[str, str]]:
    stage_index = _stage_index(result.project_stage.value)
    known_text = " ".join(
        f"{node.role} {' '.join(node.roles)}" for node in result.relationship_map.nodes
    ).casefold()
    intelligence = result.v2_snapshot.project_intelligence
    signal_text = " ".join([
        *result.relationship_map.research_gaps,
        *result.v2_snapshot.relationship_map.research_gaps,
        *(item.claim for item in intelligence.current_project_facts),
        *(item.claim for item in intelligence.open_scopes),
    ]).casefold()

    def contains_alias(haystack: str, alias: str) -> bool:
        if re.fullmatch(r"[a-z0-9&/]{1,3}", alias):
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", haystack))
        return alias in haystack

    if stage_index is None or stage_index <= 1:
        candidates = [
            ("사업기획 / 실행 PM", "실행 로드맵 책임 조직", ("pm", "roadmap", "project management", "실행"), True),
            ("설계 / Lab Engineering", "설계·통합 범위 책임 조직", ("architect", "design", "engineering", "integrator", "설계"), True),
            ("EPC / GC", "건축·시공 범위가 있을 경우", ("epc", "gc", "contractor", "construction", "시공"), False),
            ("FI / 투자자", "자금 조달·투자 승인 주체", ("investor", "investment", "funding", "capital", "capex", "투자"), False),
            ("시설 운영 주체", "완공 후 운영 책임 조직", ("operator", "facility management", "operation", "운영"), True),
            ("구매 / 사양 결정 주체", "Vendor shortlist와 기술 승인 책임", ("procurement", "specification", "purchasing", "구매", "사양"), True),
        ]
    elif stage_index <= 5:
        candidates = [
            ("PM / CM", "일정·범위 통합 책임", ("pm", "cm", "project management"), True),
            ("Architect / Design", "설계와 사양 영향 주체", ("architect", "design", "설계"), True),
            ("Engineering / Integrator", "기술 통합 책임", ("engineering", "integrator"), True),
            ("EPC / GC", "시공·발주 책임", ("epc", "gc", "contractor", "시공"), True),
            ("구매 / 사양 결정 주체", "Vendor shortlist와 기술 승인 책임", ("procurement", "specification", "구매", "사양"), True),
        ]
    elif stage_index <= 7:
        candidates = [
            ("EPC / GC", "잔여 발주·변경 범위 책임", ("epc", "gc", "contractor"), True),
            ("MEP", "설비 패키지 책임", ("mep",), True),
            ("구매 조직", "미발주 패키지와 Vendor 선정", ("procurement", "purchasing", "구매"), True),
            ("Vendor / Supplier", "주요 장비·솔루션 공급", ("vendor", "supplier", "공급"), True),
            ("현장 운영 책임자", "현장 요구·변경 승인", ("site manager", "site operation", "현장"), True),
        ]
    else:
        candidates = [
            ("Operator", "시설 운영 책임", ("operator", "operation", "운영"), True),
            ("O&M", "유지보수 책임", ("o&m", "maintenance", "유지보수"), True),
            ("Facility Management", "시설 성능·서비스 책임", ("facility management", "fm"), True),
            ("Retrofit 결정 주체", "개보수 투자 승인", ("retrofit", "renovation", "개보수"), True),
        ]

    ranked = []
    for order, (role, note, aliases, always) in enumerate(candidates):
        if any(contains_alias(known_text, alias) for alias in aliases):
            continue
        signal_count = sum(contains_alias(signal_text, alias) for alias in aliases)
        if not always and not signal_count:
            continue
        ranked.append((-signal_count, order, role, note))
    ranked.sort()
    return [(role, note) for _score, _order, role, note in ranked[:5]]


def _relationship_map(result: BDV3AnalysisResult, language: str) -> None:
    relmap = result.relationship_map
    _section(ui(language, "relationship_map"), f"사업 구조 · {_evidence_label(relmap.status)}")
    unknown_roles = _unknown_roles_for_stage(result)
    if not relmap.nodes and not unknown_roles:
        st.info("현재 정보만으로 사업 구조와 확인할 핵심 역할을 정하기 어렵습니다.")
        return
    confirmed_count = sum(node.status in {"confirmed", "likely"} for node in relmap.nodes)
    next_check = unknown_roles[0][0] if unknown_roles else "추가로 확인할 핵심 역할 없음"
    st.markdown(
        f"<div class='v3-map-summary'><span>확인된 관계자 <b>{confirmed_count}명</b></span><span>아직 확인되지 않은 역할 <b>{len(unknown_roles)}개</b></span><span class='v3-map-next'><b>다음 확인 대상</b> · {_safe(next_check)}</span></div>",
        unsafe_allow_html=True,
    )
    width, node_w, node_h = 960, 222, 82
    max_layer = max((node.layer for node in relmap.nodes), default=0)
    x_positions = {"LEFT": 145, "CENTER": 480, "RIGHT": 815}
    coords: dict[str, tuple[int, int]] = {}
    for node in relmap.nodes:
        coords[node.node_id] = (x_positions.get(node.position.upper(), 480), 50 + (node.layer - 1) * 128)
    real_bottom = max((y + node_h for _x, y in coords.values()), default=42)
    unknown_start_y = real_bottom + 96 if unknown_roles else real_bottom
    unknown_rows = (len(unknown_roles) + 2) // 3
    height = max(400, unknown_start_y + unknown_rows * 112 + 44)
    svg = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Project relationship map">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#707070"/></marker></defs>']
    for layer_type, label, fill in (("corporate", "Corporate Layer", "#f6f8fc"), ("project", "Project Layer", "#fbfcfe")):
        layer_nodes = [node for node in relmap.nodes if node.layer_type == layer_type]
        if not layer_nodes:
            continue
        first_y = min(coords[node.node_id][1] for node in layer_nodes)
        last_y = max(coords[node.node_id][1] for node in layer_nodes) + node_h
        svg.append(f'<rect x="12" y="{first_y-34}" width="936" height="{last_y-first_y+50}" rx="18" fill="{fill}"/>')
        svg.append(f'<text x="32" y="{first_y-12}" font-size="12" font-weight="700" fill="#66748f">{label}</text>')
    if unknown_roles:
        ghost_height = unknown_rows * 112 + 18
        svg.append(f'<rect x="12" y="{unknown_start_y-34}" width="936" height="{ghost_height}" rx="18" fill="#fafafa" stroke="#c9cdd4" stroke-dasharray="7 6"/>')
        svg.append(f'<text x="32" y="{unknown_start_y-12}" font-size="12" font-weight="700" fill="#777">아직 확인되지 않은 역할 · 현재 사업단계 기준</text>')
    for edge in relmap.relations:
        if edge.from_node not in coords or edge.to_node not in coords:
            continue
        x1, y1 = coords[edge.from_node]; x2, y2 = coords[edge.to_node]
        start_y, end_y = y1 + node_h, y2
        if abs(y2 - y1) < 20:
            x1 = x1 + node_w / 2 if x1 < x2 else x1 - node_w / 2
            x2 = x2 - node_w / 2 if x1 < x2 else x2 + node_w / 2
            start_y = end_y = y1 + node_h / 2
        dash = ' stroke-dasharray="7 6"' if edge.line_type == "DASHED" else ""
        arrows = ' marker-end="url(#arrow)"' if edge.direction != "NONE" else ""
        if edge.direction == "BOTH": arrows += ' marker-start="url(#arrow)"'
        mid_x, mid_y = (x1 + x2) / 2, (start_y + end_y) / 2
        svg.append(f'<path d="M{x1},{start_y} C{x1},{mid_y} {x2},{mid_y} {x2},{end_y}" fill="none" stroke="#7890bd" stroke-width="1.7"{dash}{arrows}/>')
        svg.append(f'<rect x="{mid_x-58}" y="{mid_y-10}" width="116" height="20" rx="10" fill="#f7f9fd"/><text x="{mid_x}" y="{mid_y+4}" text-anchor="middle" font-size="10" font-weight="600" fill="#66748f">{_safe(edge.label)}</text>')
    palette = {"confirmed": ("#eef5ff", "#3566d6", "#d7e4ff"), "inferred": ("#fff8e8", "#a66b00", "#f0dfb4"), "likely": ("#fff8e8", "#a66b00", "#f0dfb4"), "candidate": ("#f6f7f9", "#7a8495", "#e0e4e9"), "unknown": ("#f6f7f9", "#7a8495", "#e0e4e9")}
    for node in relmap.nodes:
        x, y = coords[node.node_id]; left = x - node_w / 2
        bg, accent, border = palette.get(node.status, palette["unknown"])
        scope = _display_label(getattr(node, "organization_scope", "unknown")).replace("_", " ").title()
        role, company = _safe(node.role), _safe(_display_label(node.company))
        node_status = _evidence_label(node.status)
        svg.append(f'<g><rect x="{left}" y="{y}" width="{node_w}" height="{node_h}" rx="20" fill="#fff" stroke="{border}"/><rect x="{left}" y="{y}" width="5" height="{node_h}" rx="3" fill="{accent}"/><circle cx="{left+27}" cy="{y+27}" r="15" fill="{bg}"/><text x="{left+27}" y="{y+31}" text-anchor="middle" font-size="10" font-weight="700" fill="{accent}">{company[:2].upper()}</text><text x="{left+51}" y="{y+25}" font-size="14" font-weight="700" fill="#000">{company[:24]}</text><text x="{left+51}" y="{y+46}" font-size="10.5" font-weight="650" fill="#66748f">{role[:29]}</text><text x="{left+51}" y="{y+68}" font-size="10" font-weight="600" fill="#7a8495">{_safe(scope)} · {_safe(node_status)}</text></g>')
    ghost_x_positions = (160, 480, 800)
    for index, (role, note) in enumerate(unknown_roles):
        x = ghost_x_positions[index % 3]
        y = unknown_start_y + (index // 3) * 112
        left = x - node_w / 2
        svg.append(
            f'<g><rect x="{left}" y="{y}" width="{node_w}" height="{node_h}" rx="20" fill="#fff" stroke="#aeb4bd" stroke-dasharray="6 5"/>'
            f'<circle cx="{left+27}" cy="{y+27}" r="15" fill="#f1f2f4"/><text x="{left+27}" y="{y+31}" text-anchor="middle" font-size="12" font-weight="700" fill="#777">?</text>'
            f'<text x="{left+51}" y="{y+26}" font-size="13" font-weight="700" fill="#555">{_safe(role[:28])}</text>'
            f'<text x="{left+51}" y="{y+48}" font-size="10" font-weight="600" fill="#777">회사 미확인</text>'
            f'<text x="{left+51}" y="{y+67}" font-size="9.5" fill="#888">{_safe(note[:32])}</text></g>'
        )
    svg.append("</svg>")
    legend = f"<div class='v3-map-legend'><span><i style='background:#3566d6'></i>{ui(language, 'confirmed')}</span><span><i style='background:#d99a27'></i>{ui(language, 'inferred')}</span><span><i style='background:#a5adba'></i>아직 확인되지 않은 역할</span></div>"
    st.markdown("<div class='v3-map-shell'>" + legend + "".join(svg) + "</div>", unsafe_allow_html=True)
    st.caption(f"사업 구조: {relmap.structure_name} · 근거 수준: {_evidence_label(relmap.status)}")
    with st.expander(ui(language, "relationship_evidence")):
        for node in relmap.nodes:
            actor = _node_actor(result, node)
            company = _display_label(node.company)
            scope = _display_label(getattr(node, "organization_scope", "unknown")).replace("_", " ").title()
            st.markdown(f"- **{company}** · {node.role} · {scope} · {_evidence_label(node.status)}")
            labels = list(getattr(actor, "evidence_labels", []) or [])
            urls = list(getattr(actor, "source_urls", []) or [])
            for index, url in enumerate(urls[:3]):
                if str(url).startswith(("https://", "http://")):
                    label = labels[index] if index < len(labels) else f"출처 {index + 1}"
                    st.markdown(f"  - [{label}]({url})")
        for edge in relmap.relations:
            st.markdown(f"- `{edge.from_node} → {edge.to_node}` · {edge.label} · {_evidence_label(edge.status)}")


def render_page_1_opportunity_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(1, ui(language, "opportunity_eyebrow"), ui(language, "opportunity_title"), result.opportunity_title)
    _project_overview(result)
    _stage_journey(result)
    state = _safe(result.status).lower()
    decision = result.v2_snapshot.bd_decision
    trigger = decision.trigger_to_reassess or result.v2_snapshot.project_intelligence.next_trigger or "Not identified"
    guide, recent_facts = _sales_stage_guidance(result)
    facts_html = "".join(f"<li>{_safe(item)}</li>" for item in recent_facts)
    status_label = {"now": "지금 접촉", "monitor": "추적 관찰", "closed": "현재 기회 종료"}.get(state, _display_label(state))
    st.markdown(
        f"<div class='v3-decision {state}'><div><div class='v3-decision-label'>영업 판단</div><div class='v3-decision-status'>{_safe(status_label)}</div></div>"
        f"<div><div class='v3-decision-label'>왜 지금 움직여야 하나요?</div><div class='v3-decision-guide'>{_safe_emphasis(guide)}</div><ul class='v3-decision-facts'>{facts_html}</ul></div>"
        f"<div class='v3-decision-trigger'><div class='v3-decision-label'>다음 확인 신호</div><div class='v3-decision-copy'>{_safe(_display_label(trigger))}</div></div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("영업 판단 근거 보기"):
        st.markdown(f"**판단 근거 요약**  \n{result.status_reason}")
        if decision.context_basis:
            st.markdown("**판단에 사용한 정보**")
            rule_only_claims = _rule_only_customer_need_claims(result)
            for item in decision.context_basis:
                if item in rule_only_claims:
                    continue
                st.markdown(f"- {item}")
        source_count = 0
        for evidence in result.evidence:
            for index, url in enumerate(evidence.source_urls):
                if str(url).startswith(("https://", "http://")):
                    label = evidence.source_labels[index] if index < len(evidence.source_labels) else evidence.claim
                    st.markdown(f"- [{label}]({url})")
                    source_count += 1
                    if source_count >= 5:
                        break
            if source_count >= 5:
                break
    _relationship_map(result, language)


def _target_card(target: V3StakeholderTarget, language: str) -> None:
    functions = " / ".join(target.target_function) or "미확인"
    st.markdown(f"<div class='v3-card'><div class='v3-role'>{_safe(target.role)}</div><div class='v3-company'>{_safe(_display_label(target.company))}</div><div class='v3-meta'><b>{ui(language, 'target_function')}</b><span>{_safe(functions)}</span><b>{ui(language, 'person')}</b><span>{_safe(_display_label(target.person))}</span><b>{ui(language, 'evidence')}</b><span>{_badge(target.evidence_strength, language)}</span></div></div>", unsafe_allow_html=True)
    with st.expander(ui(language, "why_priority")):
        st.write(target.reason)
        if target.evidence:
            st.caption("근거: " + " / ".join(target.evidence))


def render_page_2_strategy_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(2, ui(language, "strategy_eyebrow"), ui(language, "strategy_title"), ui(language, "strategy_subtitle"))
    if result.status == "closed":
        st.error("현재 기회는 종료 단계입니다. 운영·리트로핏·후속 확장 관계자만 별도로 검토하세요.")
        return
    roles = ", ".join(item.role for item in result.priority_1) or "확인된 1순위 접촉 대상 없음"
    summary = "권한, 아직 열려 있는 범위, 다음 사양 결정 시점을 확인한 뒤 제안을 준비하세요."
    strategy_label = "접촉 전략 요약"
    st.markdown(f"<div class='v3-ai'><div class='v3-ai-title'>{strategy_label}</div><div class='v3-ai-copy'>{ui(language, 'meet_first')}: <b>{_safe(roles)}</b>. {summary}</div></div>", unsafe_allow_html=True)
    for priority, targets in ((1, result.priority_1), (2, result.priority_2)):
        st.markdown(f"<div class='v3-tier'>{priority}순위</div>", unsafe_allow_html=True)
        if not targets:
            st.info("현재 근거로 추천할 접촉 대상이 없습니다.")
            continue
        for col, target in zip(st.columns(min(3, len(targets))), targets):
            with col:
                _target_card(target, language)
        st.write("")
    if result.stakeholder_unknowns:
        with st.expander(f"미확인 관계자 {len(result.stakeholder_unknowns)}명"):
            for item in result.stakeholder_unknowns:
                st.markdown(f"- {item}")


def render_page_3_meeting_v3(result: BDV3AnalysisResult, language: str = "ko") -> None:
    inject_v3_css()
    _header(3, ui(language, "meeting_eyebrow"), ui(language, "meeting_title"), ui(language, "meeting_subtitle"))
    if result.status == "closed":
        st.error("현재 기회는 종료 단계입니다. 후속 질문과 제안은 운영·리트로핏·확장 기회로 제한합니다.")
        return
    prep = "실제 의사결정권, 아직 열려 있는 사양, EPC 영향력, 공급사 선정 기준과 다음 구매 결정 시점에 집중하세요."
    meeting_label = "이번 미팅의 목표"
    st.markdown(f"<div class='v3-ai'><div class='v3-ai-title'>{meeting_label}</div><div class='v3-ai-copy'>{prep}</div></div>", unsafe_allow_html=True)
    left, right = st.columns([1.12, .88])
    with left:
        _section(ui(language, "questions"), ui(language, "prioritized"))
        for index, item in enumerate(result.questions_to_ask, 1):
            st.markdown(f"<div class='v3-question'><div class='v3-number'>{index}</div><div><div class='v3-question-title'>{_safe(_user_copy(item.question))}</div><div class='v3-question-sub'>확인 목표 · {_safe(_user_copy(item.information_goal))}</div></div></div>", unsafe_allow_html=True)
    with right:
        _section(ui(language, "talking_points"), ui(language, "short_scenarios"))
        for item in result.talking_points:
            st.markdown(f"<div class='v3-talk'><b>{_safe(item.product)}</b><p>{_safe(_user_copy(item.scenario))}</p></div>", unsafe_allow_html=True)
    _section(ui(language, "top_signals"))
    hidden_rule_only_needs = _rule_only_customer_need_claims(result)
    visible_need_signals = [
        item for item in result.customer_need_top_signals
        if item.value not in hidden_rule_only_needs
    ]
    if visible_need_signals:
        st.markdown("<div class='v3-signals'>" + "".join(f"<span class='v3-signal'>{_safe(_display_label(item.value))}</span>" for item in visible_need_signals) + "</div>", unsafe_allow_html=True)
    else:
        st.info("확인된 고객 과제 신호가 없습니다.")
    _section(ui(language, "products"), "고객 과제와 프로젝트 맥락 기준")
    for col, product in zip(st.columns(3), result.product_top3):
        with col:
            st.markdown(f"<div class='v3-product'><div class='v3-rank'>{product.rank}순위</div><div class='v3-product-name'>{_safe(product.product)}</div>{_badge(product.evidence_strength, language)}<div class='v3-product-copy'><b>{ui(language, 'why')}</b><br>{_safe(_user_copy(product.why))}<br><br><b>{ui(language, 'customer_need')}</b><br>{_safe(_user_copy(product.customer_need))}<br><br><b>{ui(language, 'scenario')}</b><br>{_safe(_user_copy(product.suggested_scenario))}</div></div>", unsafe_allow_html=True)
            with st.expander(ui(language, "decision_trace")):
                st.write(f"분류 규칙 일치 항목: {product.excel_match_count}개")
                for rule in product.matched_rules:
                    st.caption(rule)
                if product.context_evidence:
                    st.caption("문맥 근거: " + " / ".join(product.context_evidence))
    with st.expander(ui(language, "overall_trace")):
        st.markdown("**분류 규칙 기반 근거**  \n" + result.decision_trace_excel)
        st.markdown("**문맥 기반 근거**  \n" + result.decision_trace_ai)
