"""暖白 / 墨色 / 酒红主题，仅负责展示。"""
import streamlit as st

NOTICE = "CCASS Participant 持仓反映的是券商、托管机构等参与者层面的结算后持仓，不等于最终实益拥有人，也不代表实时成交方向。本页面仅用于观察不同日期之间的持仓位置变化。"


def apply_styles(assistant=False):
    width = "1600px" if assistant else "1280px"
    st.html("""
<style>
:root { --cc-ink:#25282c; --cc-muted:#645f59; --cc-accent:#803b4b; --cc-title-size:16px; --cc-text-size:13px; }
.stApp { background:#f5f2ed; color:var(--cc-ink); }
[data-testid="stHeader"] { visibility:hidden; height:0; background:transparent; }
[data-testid="stToolbar"], [data-testid="stAppDeployButton"] { display:none!important; }
[data-testid="stSidebarCollapsedControl"] { visibility:visible; position:fixed; top:8px; left:8px; z-index:1000001; }
.stMainBlockContainer { max-width:WIDTH; padding-top:1.5rem; padding-bottom:3rem; }
h1,h2,h3 { color:#25282c!important; }
[data-testid="stHeadingWithActionElements"] h1 { font-size:28px; line-height:1.4; font-weight:600; }
h2,h3,h4 { font-weight:600!important; font-size:var(--cc-title-size)!important; line-height:1.5!important; }
[data-testid="stCaptionContainer"] { color:#645f59; }
a { color:#803b4b; }
.st-key-top_navigation { position:fixed; top:0; left:0; right:0; width:100%; height:54px; box-sizing:border-box; z-index:999990; padding:4px 24px 0 60px; background:#fff; border-bottom:1px solid #e6e0d8; margin:0; }
.stMainBlockContainer:has(.st-key-top_navigation) {padding-top:64px;}
.cc-nav-logo {display:flex;align-items:center;gap:8px;height:42px;white-space:nowrap;}
.cc-nav-logo span {color:#803b4b;font-size:27px;line-height:1;}
.cc-nav-logo strong {font-size:19px;letter-spacing:1px;color:#25282c;}
[data-testid="stSidebar"] {z-index:1000000;}
.st-key-top_navigation button { border-radius:0; height:46px; min-height:46px; font-weight:700; padding:10px 4px; justify-content:center; box-shadow:none!important; white-space:nowrap; }
.st-key-top_navigation button p {font-weight:700!important;}
.st-key-top_navigation button[kind="primary"] { background:transparent; color:#803b4b; border:0; border-bottom:3px solid #803b4b; }
.st-key-top_navigation button[kind="secondary"] { background:transparent; color:#46413c; border:0; border-bottom:3px solid transparent; }
.st-key-top_navigation button[kind="secondary"]:hover { background:transparent; color:#803b4b; border-bottom-color:#d8bcc3; }
[data-testid="stPopoverBody"]:is(:has(.st-key-nav_ccass_changes),:has(.st-key-nav_broker_history)) {width:220px!important;min-width:0!important;max-width:calc(100vw - 24px)!important;padding:5px!important;border-radius:0!important;background:#fff!important;}
[data-testid="stPopoverBody"]:is(:has(.st-key-nav_ccass_changes),:has(.st-key-nav_broker_history)) [data-testid="stVerticalBlock"] {gap:0!important;}
.st-key-nav_ccass_changes button,.st-key-nav_broker_history button {background:#fff!important;color:#25282c!important;border:0!important;border-radius:0!important;box-shadow:none!important;min-height:34px!important;height:auto!important;padding:7px 12px!important;justify-content:flex-start!important;}
.st-key-nav_ccass_changes button p,.st-key-nav_broker_history button p {font-size:13px!important;font-weight:400!important;line-height:1.5!important;}
.st-key-nav_ccass_changes button:hover,.st-key-nav_broker_history button:hover,
.st-key-nav_ccass_changes button:focus-visible,.st-key-nav_broker_history button:focus-visible {background:#ebe5dc!important;}
:is(.st-key-nav_trade_ticker,.st-key-nav_comparison) button {background:#fff!important;color:#25282c!important;border:0!important;border-radius:0!important;box-shadow:none!important;min-height:34px!important;height:auto!important;padding:7px 12px!important;justify-content:flex-start!important;}
:is(.st-key-nav_trade_ticker,.st-key-nav_comparison) button p {font-size:13px!important;font-weight:400!important;line-height:1.5!important;}
:is(.st-key-nav_trade_ticker,.st-key-nav_comparison) button:hover,:is(.st-key-nav_trade_ticker,.st-key-nav_comparison) button:focus-visible {background:#ebe5dc!important;}
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
.st-key-assistant_section {background:#fff;border:1px solid #e6e0d8;border-radius:12px;padding:18px 20px;box-shadow:0 2px 10px rgba(37,40,44,.025);}
.st-key-assistant_section .cc-hero {margin-top:4px;}
.st-key-assistant_content {max-width:796px;width:100%;margin-left:auto;margin-right:auto;}
.st-key-assistant_messages {background:#fff;overscroll-behavior-y:contain;scrollbar-gutter:stable;}
.st-key-assistant_composer {background:#fff;border-top:1px solid #e6e0d8;padding-top:12px;flex-shrink:0;}
.st-key-assistant_composer [data-testid="stChatInput"] {position:relative;bottom:auto;width:100%;}
.stMainBlockContainer:has(.st-key-assistant_section) {padding-bottom:10px;}
.st-key-assistant_section {height:calc(100dvh - 84px)!important;max-height:calc(100dvh - 84px)!important;min-height:0;box-sizing:border-box;overflow:hidden;}
.st-key-assistant_section > [data-testid="stLayoutWrapper"] {height:100%!important;min-height:0;}
.st-key-assistant_content {
  display:grid!important;grid-template-rows:minmax(0,1fr) auto;
  height:calc(100dvh - 122px)!important;max-height:calc(100dvh - 122px)!important;
  min-height:0;overflow:hidden;gap:12px;flex:none!important;
}
.st-key-assistant_content > [data-testid="stLayoutWrapper"]:has(> .st-key-assistant_messages) {
  height:100%!important;min-height:0;overflow:hidden;flex:none!important;
}
.st-key-assistant_messages {height:100%!important;min-height:0;overflow-y:auto;}
.st-key-assistant_content > [data-testid="stLayoutWrapper"]:has(> .st-key-assistant_composer) {
  height:auto!important;flex:0 0 auto!important;
}
.stMainBlockContainer:has(.st-key-participant_workspace) {max-width:1600px;}
.st-key-participant_workspace {background:#fff;border:1px solid #e6e0d8;border-radius:12px;padding:18px 20px;box-shadow:0 2px 10px rgba(37,40,44,.025);}
.stMainBlockContainer:has(.st-key-multi_participant_workspace) {max-width:1600px;}
.st-key-multi_participant_workspace {background:#fff;border:1px solid #e6e0d8;border-radius:12px;padding:18px 20px;box-shadow:0 2px 10px rgba(37,40,44,.025);box-sizing:border-box;min-width:0;}
.st-key-multi_participant_workspace [data-testid="stVegaLiteChart"] {background:#fff;max-width:100%;box-sizing:border-box;}
.st-key-multi_participant_workspace [data-testid="stDataFrame"] {background:#fff;border:1px solid #d4ccc2;border-radius:8px;overflow:hidden;}
.st-key-multi_participant_workspace div:has(> input),.st-key-multi_participant_workspace input {background:#fff!important;}
.st-key-multi_participant_workspace [data-testid="stSelectbox"]:hover div:has(> input) {background:#ebe5dc!important;}
.st-key-ccass_change_overview {background:#fff;border:1px solid #e6e0d8;border-radius:12px;padding:18px 20px;margin-top:12px;}
.st-key-ccass_change_overview [data-testid="stDataFrame"] {border:1px solid #d4ccc2;border-radius:8px;overflow:hidden;}
.st-key-participant_workspace .st-key-ccass_change_overview {border:0;box-shadow:none;padding:0;margin-top:4px;}
.st-key-participant_workspace .st-key-broker_history {border:0;box-shadow:none;padding:0;margin-top:4px;}
.st-key-participant_workspace [data-testid="stForm"] {background:#fff;}
.st-key-broker_history [data-testid="stDateInput"] input,
.st-key-broker_history [data-testid="stDateInput"] div:has(> input) {background:#fff!important;border-color:#d4ccc2!important;}
.st-key-broker_history [data-testid="stDateInput"]:hover input,
.st-key-broker_history [data-testid="stDateInput"]:hover [data-baseweb="input"],
.st-key-broker_history [data-testid="stDateInput"]:hover div:has(> input) {background:#ebe5dc!important;border-color:#b9aa94!important;}
.st-key-broker_history [data-testid="stDateInputField"] {background:#fff!important;border-color:#d4ccc2!important;transition:background-color .15s;}
.st-key-broker_history [data-testid="stDateInputField"]:hover,
.st-key-broker_history [data-testid="stDateInputField"]:focus-within {background:#ebe5dc!important;border-color:#b9aa94!important;}
.st-key-broker_history [data-testid="stDateInputField"] [role="group"],
.st-key-broker_history [data-testid="stDateInputField"] [role="spinbutton"] {background:transparent!important;color:#171717!important;}
.st-key-participant_workspace [data-baseweb="select"] > div,
.st-key-participant_workspace [data-baseweb="input"] {background:#fff!important;border-color:#d4ccc2!important;}
.st-key-participant_workspace input {background:#fff!important;color:#171717!important;}
.st-key-trend_participant [data-baseweb="select"],
.st-key-trend_participant [data-baseweb="select"] div,
.st-key-trend_participant [role="combobox"],
.st-key-trend_participant input {background-color:#fff!important;color:#171717!important;}
.st-key-trend_participant div:has(> input),
.st-key-participant_workspace [data-testid="stSelectbox"] div:has(> input) {background-color:#fff!important;border-color:#d4ccc2!important;}
.st-key-participant_workspace .st-key-trend_participant input,
.st-key-participant_workspace .st-key-trend_participant [role="combobox"],
.st-key-participant_workspace .st-key-trend_participant div:has(> input),
.st-key-participant_workspace .st-key-trend_participant [data-baseweb="select"] > div {background:#fff!important;border-color:#d4ccc2!important;color:#171717!important;}
.st-key-participant_workspace .st-key-trend_participant:hover input,
.st-key-participant_workspace .st-key-trend_participant:hover [role="combobox"],
.st-key-participant_workspace .st-key-trend_participant:hover div:has(> input),
.st-key-participant_workspace .st-key-trend_participant:hover [data-baseweb="select"] > div {background:#ebe5dc!important;border-color:#b9aa94!important;}
.st-key-participant_workspace [data-testid="stExpander"] summary {background:#fff!important;transition:background-color .15s;}
.st-key-participant_workspace [data-testid="stExpander"] summary:hover {background:#ebe5dc!important;}
body:has(.st-key-participant_workspace) [data-testid="stSelectboxVirtualDropdown"],
body:has(.st-key-participant_workspace) [data-testid="stSelectboxVirtualDropdown"] [role="option"] {background:#fff!important;color:#171717;}
body:has(.st-key-participant_workspace) [data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused],
body:has(.st-key-participant_workspace) [data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered] {background:#ebe5dc!important;}
.st-key-participant_workspace {box-sizing:border-box;min-width:0;}
.st-key-participant_workspace [data-testid="stVegaLiteChart"] {background:#fff;border:0;border-radius:8px;padding:0;box-sizing:border-box;width:100%;max-width:100%;min-width:0;box-shadow:inset 0 0 0 1px #d4ccc2;}
body:has(.st-key-participant_workspace) [data-baseweb="popover"] [role="listbox"],
body:has(.st-key-participant_workspace) [data-baseweb="popover"] [role="option"] {background:#fff;color:#171717;}
body:has(.st-key-participant_workspace) [data-baseweb="popover"] [role="option"]:hover,
body:has(.st-key-participant_workspace) [data-baseweb="popover"] [role="option"][aria-selected="true"] {background:#ebe5dc;}
.st-key-participant_workspace [data-testid="stDataFrame"] {background:#fff;border:1px solid #d4ccc2;border-radius:8px;box-shadow:0 2px 5px rgba(25,35,45,.05);overflow:hidden;}
[data-testid="stMetric"] { padding:18px 20px; background:#fff; border:1px solid #d4ccc2; border-top:3px solid #a68a62; border-radius:10px; }
[data-testid="stMetricLabel"] { color:#645f59; font-weight:500; }
[data-testid="stMetricValue"] { color:#25282c; font-size:30px; font-weight:700; }
.st-key-home_summary { background:#fff; border:1px solid #d4ccc2; border-left:4px solid #803b4b; border-radius:10px; padding:20px; }
[data-baseweb="tab"][aria-selected="true"] { color:#803b4b; font-weight:700; }
[data-baseweb="tab-highlight"] { background:#803b4b; }
[data-testid="stForm"] { background:#fff; border-color:#d4ccc2; }
[data-testid="stDataFrame"] { border-radius:8px; }
[data-testid="stDataFrame"] {
  --gdg-bg-header:#ebe5dc; --gdg-bg-header-hovered:#e2d7c7;
  --gdg-bg-header-has-focus:#e2d7c7; --gdg-border-color:#d4ccc2;
}
[data-testid="stSelectbox"]:hover [data-baseweb="select"] > div,
[data-testid="stMultiSelect"]:hover [data-baseweb="select"] > div,
[data-testid="stDateInput"]:hover [data-baseweb="input"],
[data-testid="stExpander"] summary:hover {background:#ebe5dc!important;border-color:#b9aa94!important;}
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused],
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered],
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"] {background:#ebe5dc!important;}
[data-testid="stExpander"] { border-color:#c8beb2; border-radius:10px; }
.stMainBlockContainer [data-testid="stCaptionContainer"],
.stMainBlockContainer [data-testid="stCaptionContainer"] p,
.stMainBlockContainer [data-testid="stMarkdownContainer"] > p,
.stMainBlockContainer [data-testid="stWidgetLabel"] p,
.cc-helper,.cc-notice,.cc-hero p,.cc-badge {font-size:var(--cc-text-size)!important;line-height:1.65;}
.stMainBlockContainer [data-testid="stMarkdownContainer"] > p:has(> strong:only-child) > strong {font-size:var(--cc-title-size);font-weight:600;}
.st-key-top_navigation button p {font-size:var(--cc-title-size)!important;}
@media(max-width:640px) {
  .stMainBlockContainer { padding-top:1.5rem; padding-left:1rem; padding-right:1rem; }
  [data-testid="stHeadingWithActionElements"] h1 { font-size:24px; }
  .cc-hero { margin-top:12px; }
  [class*="st-key-suggestion_"] button { padding:12px; }
}
</style>
""".replace("WIDTH", width))


def render_notice():
    st.html(f'<div class="cc-notice">{NOTICE}</div>')
