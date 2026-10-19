"""暖白 / 墨色 / 酒红主题，仅负责展示。"""
import streamlit as st

NOTICE = "CCASS Participant 持仓反映的是券商、托管机构等参与者层面的结算后持仓，不等于最终实益拥有人，也不代表实时成交方向。本页面仅用于观察不同日期之间的持仓位置变化。"


def apply_styles(assistant=False):
    width = "860px" if assistant else "1280px"
    st.html("""
<style>
:root { --cc-ink:#25282c; --cc-muted:#645f59; --cc-accent:#803b4b; }
.stApp { background:#f5f2ed; color:var(--cc-ink); }
[data-testid="stHeader"] { background:rgba(245,242,237,.97); }
.stMainBlockContainer { max-width:WIDTH; padding-top:5rem; padding-bottom:3rem; }
h1,h2,h3 { color:#25282c!important; }
[data-testid="stHeadingWithActionElements"] h1 { font-size:28px; line-height:1.4; font-weight:600; }
h2 { font-weight:600!important; font-size:21px!important; }
h3 { font-weight:600!important; font-size:18px!important; }
[data-testid="stCaptionContainer"] { color:#645f59; }
a { color:#803b4b; }
.st-key-top_navigation { padding:8px 0 18px; border-bottom:1px solid #d4ccc2; margin-bottom:12px; }
.st-key-top_navigation button { border-radius:8px; min-height:44px; font-weight:600; }
.st-key-top_navigation button[kind="primary"] { background:#803b4b; color:#fff; border:1px solid #803b4b; }
.st-key-top_navigation button[kind="secondary"] { background:#fff; color:#46413c; border:1px solid #d4ccc2; }
.st-key-top_navigation button[kind="secondary"]:hover { background:#f0e5e7; border-color:#a47782; }
[data-testid="stSidebar"] { background:#ebe5dc; border-right:1px solid #d4ccc2; }
[data-testid="stSidebar"] > div:first-child { padding-top:1.7rem; }
[data-testid="stSidebar"] hr { border-color:#d4ccc2; margin:1.3rem 0; }
.cc-brand { display:flex; gap:11px; align-items:center; margin:0 0 30px; }
.cc-brand-icon { background:#803b4b; color:#fff; border-radius:9px; padding:10px 12px; font-size:19px; }
.cc-brand strong { display:block; font-size:17px; letter-spacing:.3px; }
.cc-brand small,.cc-section { color:#645f59; font-size:11px; letter-spacing:1.5px; }
.cc-section { margin:0 0 10px; }
.cc-status { background:#fff; border:1px solid #d4ccc2; border-radius:10px; padding:16px; margin:10px 0 20px; }
.cc-status strong { color:#803b4b; font-size:13px; font-weight:600; }
.cc-status p { color:#645f59; font-size:12px; margin:7px 0 0; }
[data-testid="stSidebar"] .stButton button { justify-content:flex-start; border-radius:8px; min-height:43px; padding:10px 14px; box-shadow:none; }
[data-testid="stSidebar"] .stButton button[kind="secondary"] { background:transparent; color:#46413c; border:1px solid #c8beb2; }
[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover { background:#f8f5ef; }
[data-testid="stSidebar"] .stButton button[kind="primary"] { background:#803b4b; color:#fff; border-color:#803b4b; }
.cc-hero { margin:25px 0 28px; }
.cc-eyebrow { color:#645f59; font-size:11px; letter-spacing:2px; margin-bottom:15px; }
.cc-hero h1 { font-size:clamp(26px,3vw,36px); line-height:1.45; letter-spacing:-.8px; padding:0; margin:0 0 12px; font-weight:600; }
.cc-hero p { color:#645f59; font-size:15px; line-height:1.8; margin:0; }
.cc-badge { display:inline-block; border:1px solid #d8bcc3; background:#f3e9ec; color:#743545; border-radius:20px; padding:4px 10px; font-size:11px; margin-top:18px; }
.cc-notice { background:#eee8df; border:1px solid #d4ccc2; border-left:3px solid #a68a62; border-radius:8px; padding:12px 16px; color:#5c5143; font-size:12px; line-height:1.8; margin:12px 0 20px; }
.cc-helper { color:#645f59; font-size:12px; margin:5px 0 12px; }
[class*="st-key-suggestion_"] button { background:#fff; border:1px solid #d4ccc2; border-radius:10px; padding:14px 18px; min-height:52px; justify-content:flex-start; color:#34312e; }
[class*="st-key-suggestion_"] button:hover { background:#f3e9ec; border-color:#a47782; color:#743545; }
[class*="st-key-suggestion_"] button p { text-align:left; width:100%; font-size:14px; line-height:1.65; }
[class*="st-key-suggestion_"] button p::after { content:'↗'; float:right; color:#803b4b; padding-left:12px; }
[data-testid="stChatMessage"] { background:transparent; border:0; padding:18px 10px; border-radius:12px; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background:#eae2d8; }
[data-testid="stChatMessage"] p { line-height:1.85; font-size:15px; }
[data-testid="stChatInput"] { border:1px solid #b9aa9b; border-radius:18px; background:#fff; }
[data-testid="stBottom"] { background:#f5f2ed; }
[data-testid="stBottomBlockContainer"] { max-width:860px; padding-bottom:1.2rem; }
[data-testid="stMetric"] { padding:18px 20px; background:#fff; border:1px solid #d4ccc2; border-top:3px solid #a68a62; border-radius:10px; }
[data-testid="stMetricLabel"] { color:#645f59; font-weight:500; }
[data-testid="stMetricValue"] { color:#25282c; font-size:30px; font-weight:700; }
.st-key-home_summary { background:#fff; border:1px solid #d4ccc2; border-left:4px solid #803b4b; border-radius:10px; padding:20px; }
[data-baseweb="tab"][aria-selected="true"] { color:#803b4b; font-weight:700; }
[data-baseweb="tab-highlight"] { background:#803b4b; }
[data-testid="stForm"] { background:#fff; border-color:#d4ccc2; }
[data-testid="stDataFrame"] { border-radius:8px; }
[data-testid="stExpander"] { border-color:#c8beb2; border-radius:10px; }
@media(max-width:640px) {
  .stMainBlockContainer { padding-top:4.5rem; padding-left:1rem; padding-right:1rem; }
  [data-testid="stHeadingWithActionElements"] h1 { font-size:24px; }
  .cc-hero { margin-top:12px; }
  [class*="st-key-suggestion_"] button { padding:12px; }
}
</style>
""".replace("WIDTH", width))


def render_notice():
    st.html(f'<div class="cc-notice">{NOTICE}</div>')
