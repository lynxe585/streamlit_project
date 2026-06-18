import streamlit as st
from utils.styles import inject_global_styles, render_kpi_card
from utils.sidebar import render_global_sidebar
from utils.translation import t

st.set_page_config(
    page_title="Project Overview | Fraud Detection",
    page_icon="📖",
    layout="wide"
)

inject_global_styles()
render_global_sidebar(show_config=False)

# ------------------------------------------------------------------
# Hero Banner
# ------------------------------------------------------------------
st.markdown(
    f"""
    <div class="banner-container">
        <div class="banner-title">{t("home_title")}</div>
        <div class="banner-subtitle">
            {t("home_subtitle")}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------------
# Quick Navigation Cards
# ------------------------------------------------------------------
st.markdown(f'<div class="section-title">{t("quick_nav")}</div>', unsafe_allow_html=True)
nav1, nav2, nav3 = st.columns(3)

nav_style = """
    background: {bg};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 28px 22px;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
    height: 230px;
    display: block;
    text-decoration: none;
    color: inherit;
"""

# Inject CSS for hover effect
st.markdown("""
<style>
.nav-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    filter: brightness(1.2);
}
</style>
""", unsafe_allow_html=True)

for col, icon, title, desc, bg, border, page_path, url_path in [
    (nav1, "📊", t("nav_dashboard_title"),
     t("nav_dashboard_desc"),
     "rgba(99,102,241,0.07)", "rgba(99,102,241,0.35)",
     "pages/1_📊_Executive_Dashboard.py", "Executive_Dashboard"),
    (nav2, "📈", t("nav_analytics_title"),
     t("nav_analytics_desc"),
     "rgba(59,130,246,0.07)", "rgba(59,130,246,0.35)",
     "pages/2_📈_Analytics_Mode.py", "Analytics_Mode"),
    (nav3, "🤖", t("nav_copilot_title"),
     t("nav_copilot_desc"),
     "rgba(168,85,247,0.07)", "rgba(168,85,247,0.35)",
     "pages/3_🤖_AI_Copilot.py", "AI_Copilot"),
]:
    with col:
        st.markdown(
            f"""
            <a href="{url_path}" target="_self" style="text-decoration: none;">
                <div class="nav-card" style="{nav_style.format(bg=bg, border=border)}">
                    <div style="font-size:2.8rem;">{icon}</div>
                    <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin:10px 0 6px 0;">{title}</div>
                    <div style="font-size:0.82rem;color:#94A3B8;line-height:1.5;">{desc}</div>
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# System Architecture Diagram (Enterprise Fraud Intelligence Pipeline)
# ------------------------------------------------------------------
st.markdown(
    f"""
    <div style="text-align: center; margin: 40px 0 20px 0;">
        <h3 style="letter-spacing: 0.2em; text-transform: uppercase; font-weight: 800; color: #F8FAFC;">
            {t("pipeline_title")}
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)

def _pipeline_card(icon, title, items, border_color):
    items_html = "<br>".join([f"<span style='color:#94A3B8;font-size:0.8rem;'>{item}</span>" for item in items])
    return f"""
    <div style="background: rgba(15, 23, 42, 0.6); border-top: 3px solid {border_color}; border-radius: 8px; padding: 16px; margin-bottom: 16px; min-height: 100px; display: flex; gap: 15px; align-items: flex-start; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 1.8rem; line-height: 1;">{icon}</div>
        <div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 4px;">{title}</div>
            <div style="line-height: 1.4;">{items_html}</div>
        </div>
    </div>
    """

def _pipeline_section_header(title):
    return f"""
    <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.05); border-radius: 20px; padding: 6px 16px; display: inline-block; margin-bottom: 20px; text-align: center; width: 100%;">
        <span style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #94A3B8;">{title}</span>
    </div>
    """

def _pipeline_arrow(label):
    return f"""
    <div style="display: flex; align-items: center; justify-content: center; height: 480px; flex-direction: column; gap: 5px;">
        <div style="font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #F8FAFC;">{label}</div>
        <div style="color: #A855F7; font-size: 1.5rem; line-height: 1; text-shadow: 0 0 10px rgba(168,85,247,0.8);">▶</div>
    </div>
    """

col_src, col_arr1, col_proc, col_arr2, col_out = st.columns([2.5, 0.8, 2.5, 0.8, 2.5])

with col_src:
    src_html = f"""
    <div style="background: rgba(10, 15, 30, 0.4); border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; min-height: 480px;">
        {_pipeline_section_header(t("pipeline_sources"))}
        {_pipeline_card("❄️", "Snowflake DWH", ["Batch Tables:", "SYNTHETIC_FRAUD", "CREDIT_CARD_FRAUD"], "#06B6D4")}
        {_pipeline_card("🍃", "MongoDB Atlas", ["Live DB:", "Transactions & Accounts"], "#10B981")}
    </div>
    """
    st.markdown(src_html, unsafe_allow_html=True)

with col_arr1:
    st.markdown(_pipeline_arrow(t("pipeline_ingests")), unsafe_allow_html=True)

with col_proc:
    proc_html = f"""
    <div style="background: rgba(10, 15, 30, 0.4); border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; min-height: 480px;">
        {_pipeline_section_header(t("pipeline_compute"))}
        {_pipeline_card("🦆", "DuckDB", ["In-Memory OLAP", "Fast Vectorized SQL"], "#FBBF24")}
        {_pipeline_card("🐼", "Pandas", ["Transformation", "Data Aggregation"], "#38BDF8")}
    </div>
    """
    st.markdown(proc_html, unsafe_allow_html=True)

with col_arr2:
    st.markdown(_pipeline_arrow(t("pipeline_serves")), unsafe_allow_html=True)

with col_out:
    out_html = f"""
    <div style="background: rgba(10, 15, 30, 0.4); border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; min-height: 480px;">
        {_pipeline_section_header(t("pipeline_intelligence"))}
        {_pipeline_card("✨", "Google Gemini", ["Gemma 2 9B-IT", "GenAI Forensic Analysis"], "#A855F7")}
        {_pipeline_card("🎯", "Streamlit App", ["Executive Dashboard", "Interactive Copilot"], "#EF4444")}
        {_pipeline_card("📋", "Audit Logs DB", ["MongoDB", "Automated SARs Saved"], "#10B981")}
    </div>
    """
    st.markdown(out_html, unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Issues & Motivation
# ------------------------------------------------------------------
st.markdown(f'<div class="section-title">{t("issues_motivation_title")}</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="content-box">
        {t("issues_motivation_desc")}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Objective
# ------------------------------------------------------------------
st.markdown(f'<div class="section-title">{t("objective_title")}</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="content-box">
        {t("objective_desc")}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Tech Stack
# ------------------------------------------------------------------
st.markdown(f'<div class="section-title">{t("tech_stack_title")}</div>', unsafe_allow_html=True)

tech_items = [
    ("🐍", "Python 3.11+",        "Core language"),
    ("🎈", "Streamlit ≥1.35",     "Multi-page web app framework"),
    ("🦆", "DuckDB ≥1.0",         "In-memory OLAP analytical engine"),
    ("❄️", "Snowflake",            "Cloud data warehouse (FRAUD_DB)"),
    ("🍃", "MongoDB Atlas",        "NoSQL document store (blacklist, audit_logs)"),
    ("📊", "Plotly ≥5.20",         "Interactive charts & network graphs"),
    ("🤖", "Google Gemma / Gemini","LLM for SAR generation & AI chatbot"),
    ("🐼", "Pandas ≥2.0",          "Data wrangling & schema mapping"),
    ("🔢", "NumPy ≥1.24",          "Vectorized risk score computation"),
]

cols = st.columns(5)
for i, (icon, name, desc) in enumerate(tech_items):
    with cols[i % 5]:
        st.markdown(
            f"""
            <div style="background:rgba(30,41,59,0.45);border:1px solid rgba(255,255,255,0.07);
                        border-radius:10px;padding:14px 12px;text-align:center;margin-bottom:12px;">
                <div style="font-size:1.8rem;">{icon}</div>
                <div style="font-size:0.88rem;font-weight:700;color:#F8FAFC;margin:6px 0 3px 0;">{name}</div>
                <div style="font-size:0.72rem;color:#64748B;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<br><br>", unsafe_allow_html=True)

