import streamlit as st
from utils.db import initialize_database, get_connection_status
from utils.translation import t

def render_global_sidebar(show_config=True):
    """
    Renders the global sidebar configuration panel.
    Initializes databases and sets up session states.
    """

    # Language Selector
    if "language" not in st.session_state:
        st.session_state["language"] = "TH"

    st.sidebar.subheader("🌐 Language / ภาษา")
    selected_lang = st.sidebar.radio(
        "Select Language",
        ["ไทย (TH)", "English (EN)"],
        index=0 if st.session_state["language"] == "TH" else 1,
        label_visibility="collapsed",
        key="lang_radio_select"
    )
    new_lang = "TH" if "ไทย" in selected_lang else "EN"
    if st.session_state["language"] != new_lang:
        st.session_state["language"] = new_lang
        # Clear AI output cache to force regeneration in the new language
        st.session_state.pop("generated_sar_text", None)
        st.session_state.pop("chat_messages", None)
        st.rerun()

    if show_config:
        st.sidebar.title(t("config_panel"))

    use_cloud = True

    if show_config:
        # Dataset Selection
        dataset_select = st.sidebar.selectbox(
            t("select_dataset"),
            ["All Sources", "Snowflake: Synthetic Fraud", "Snowflake: Credit Card Fraud", "MongoDB: Card Transactions", "MongoDB: Mock Transactions"],
            key="global_dataset_select"
        )

        if st.sidebar.button(t("reload_cache")):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.sidebar.success(t("cache_cleared"))
    else:
        dataset_select = st.session_state.get("current_dataset", "All Sources")

    # Detect changes to force reload
    if "current_dataset" not in st.session_state:
        st.session_state["current_dataset"] = dataset_select
    if "current_use_cloud" not in st.session_state:
        st.session_state["current_use_cloud"] = use_cloud

    force_reload = False
    if st.session_state["current_dataset"] != dataset_select or st.session_state["current_use_cloud"] != use_cloud:
        force_reload = True
        st.cache_data.clear()
        st.cache_resource.clear() # Force reconnect to databases if they previously failed
        st.session_state["current_dataset"] = dataset_select
        st.session_state["current_use_cloud"] = use_cloud

    # Initialize DuckDB tables
    try:
        initialize_database(dataset_name=dataset_select, force_reload=force_reload, use_cloud=use_cloud)
    except Exception as e:
        st.sidebar.error(f"Failed to initialize database: {e}")

    # ---------------------------------------------------------
    # Connection Status Panel
    # ---------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader(t("connection_status"))

    conn_status = get_connection_status()

    # Snowflake Status
    if conn_status["snowflake_connected"]:
        st.sidebar.markdown(f'<span class="conn-badge conn-ok">{t("snowflake_connected")}</span>', unsafe_allow_html=True)
    else:
        sf_err = conn_status.get("snowflake_error", "Unknown")
        st.sidebar.markdown(f'<span class="conn-badge conn-fail">{t("snowflake_disconnected")}</span>', unsafe_allow_html=True)
        if sf_err:
            st.sidebar.caption(f"Error: {sf_err[:80]}")

    # MongoDB Status
    if conn_status["mongodb_connected"]:
        st.sidebar.markdown(f'<span class="conn-badge conn-ok">{t("mongodb_connected")}</span>', unsafe_allow_html=True)
    else:
        mongo_err = conn_status.get("mongodb_error", "Unknown")
        st.sidebar.markdown(f'<span class="conn-badge conn-fail">{t("mongodb_disconnected")}</span>', unsafe_allow_html=True)
        if mongo_err:
            st.sidebar.caption(f"Error: {mongo_err[:80]}")

    # Data Source Loaded Info
    load_status = conn_status.get("data_sources_loaded", {})
    if load_status:
        st.sidebar.markdown(f"**{t('data_loaded')}**")
        for source, count in load_status.items():
            st.sidebar.caption(f"• {source}: {count:,} records")



