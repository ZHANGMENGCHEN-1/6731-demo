"""共享视觉样式；仅负责布局和外观。"""
import streamlit as st

NOTICE = "CCASS Participant 持仓反映的是券商、托管机构等参与者层面的结算后持仓，不等于最终实益拥有人，也不代表实时成交方向。本页面仅用于观察不同日期之间的持仓位置变化。"


def apply_styles(assistant=False):
    width = "860px" if assistant else "1280px"
    st.html("""
<style>
:root { --cc-ink:#172b32; --cc-muted:#73818a; --cc-accent:#16766b; }
.stApp { background:#fff; color:var(--cc-ink); }
[data-testid="stHeader"] { background:rgba(255,255,255,.94); }
.stMainBlockContainer { max-width:WIDTH; padding-top:2.5rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#f7f8fa; border-right:1px solid #e9edf0; }
[data-testid="stSidebar"] > div:first-child { padding-top:1.7rem; }
[data-testid="stSidebar"] hr { border-color:#e6eaee; margin:1.3rem 0; }
.cc-brand { display:flex; gap:11px; align-items:center; margin:0 0 30px; }
.cc-brand-icon { background:#173c37; color:#fff; border-radius:11px; padding:10px 12px; font-size:19px; }
.cc-brand strong { display:block; font-size:17px; letter-spacing:.3px; }
.cc-brand small { color:#829098; font-size:11px; letter-spacing:1.5px; }
.cc-section { color:#8b969e; font-size:11px; letter-spacing:1.5px; margin:0 0 10px; }
.cc-status { background:#fff; border:1px solid #e7ecec; border-radius:12px; padding:16px; margin:10px 0 20px; }
.cc-status strong { color:#34786a; font-size:13px; font-weight:500; }
.cc-status p { color:#849098; font-size:12px; margin:7px 0 0; }
[data-testid="stSidebar"] .stButton button { justify-content:flex-start; border:0; border-radius:9px; min-height:43px; padding:10px 14px; box-shadow:none; }
[data-testid="stSidebar"] .stButton button[kind="secondary"] { background:transparent; color:#596970; }
[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover { background:#eaeef0; color:#172b32; }
[data-testid="stSidebar"] .stButton button[kind="primary"] { background:#e5efec; color:#176b5e; font-weight:600; }
.cc-hero { margin:25px 0 28px; }
.cc-eyebrow { color:#78868c; font-size:11px; font-weight:600; letter-spacing:2px; margin-bottom:15px; }
.cc-hero h1 { color:#172b32; font-size:clamp(26px,3vw,36px); line-height:1.45; letter-spacing:-.8px; padding:0; margin:0 0 12px; font-weight:600; }
.cc-hero p { color:#829097; font-size:15px; line-height:1.8; margin:0; }
.cc-badge { display:inline-block; border:1px solid #e1e9e5; background:#f5faf7; color:#658276; border-radius:20px; padding:4px 10px; font-size:11px; margin-top:18px; }
.cc-notice { background:#fafaf7; border:1px solid #ebede4; border-left:3px solid #b8bea1; border-radius:8px; padding:12px 16px; color:#7c806e; font-size:12px; line-height:1.8; margin:12px 0 20px; }
.cc-helper { color:#8b969b; font-size:12px; margin:5px 0 12px; }
[class*="st-key-suggestion_"] button { border:1px solid #e7ecec; background:#fff; border-radius:12px; padding:14px 18px; min-height:52px; justify-content:flex-start; color:#42565d; box-shadow:0 2px 6px #18383003; transition:background .15s,border-color .15s; }
[class*="st-key-suggestion_"] button:hover { background:#f5faf8; border-color:#afc8bf; color:#176b5e; }
[class*="st-key-suggestion_"] button p { text-align:left; width:100%; font-size:14px; line-height:1.65; }
[class*="st-key-suggestion_"] button p::after { content:'↗'; float:right; color:#a2b3ad; padding-left:12px; }
[data-testid="stChatMessage"] { background:transparent; border:0; padding:18px 10px; border-radius:16px; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background:#f4f7f6; }
[data-testid="stChatMessage"] p { line-height:1.85; font-size:15px; }
[data-testid="stChatInput"] { border:1px solid #dfe7e4; border-radius:22px; background:#fafcfb; box-shadow:0 4px 20px #17493808; }
[data-testid="stBottom"] { background:#fff; }
[data-testid="stBottomBlockContainer"] { max-width:860px; padding-bottom:1.2rem; }
[data-testid="stMetric"] { padding:18px 20px; background:#f8faf9; border:1px solid #e8eeeb; border-radius:12px; }
[data-testid="stMetricLabel"] { color:#82908e; }
[data-testid="stMetricValue"] { color:#24463c; font-size:27px; }
h2 { font-weight:600!important; font-size:21px!important; color:#254239!important; }
h3 { font-weight:600!important; font-size:18px!important; }
[data-testid="stDataFrame"] { border-radius:10px; }
[data-testid="stExpander"] { border-color:#e8edeb; border-radius:12px; }
@media(max-width:640px) {
  .stMainBlockContainer { padding-top:1rem; padding-left:1rem; padding-right:1rem; }
  .cc-hero { margin-top:12px; }
  [class*="st-key-suggestion_"] button { padding:12px; }
}
</style>
""".replace("WIDTH", width))


def render_notice():
    st.html(f'<div class="cc-notice">{NOTICE}</div>')
