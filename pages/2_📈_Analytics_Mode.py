import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
import networkx as nx

from utils.db import initialize_database, get_duckdb_connection
from utils.data_processing import (
    get_high_risk_transactions,
    get_shared_merchant_network,
    get_risk_pattern_analysis,
    get_db,
    detect_circular_loops,
    get_suspicious_accounts_velocity,
    get_hourly_velocity_heatmap,
)
from utils.styles import inject_global_styles
from utils.sidebar import render_global_sidebar
from utils.translation import t

pd.set_option("styler.render.max_elements", 2_000_000)

st.set_page_config(
    page_title="Analytics Mode | Financial Fraud Detection",
    page_icon="📈",
    layout="wide"
)

conn = get_db()
inject_global_styles()
render_global_sidebar()

lang_curr = st.session_state.get("language", "TH")

st.markdown(
    f"""
    <div class="panel-header">
        <h2 class="panel-title">{t("analytics_title")}</h2>
        <p class="panel-desc">{t("analytics_desc")}</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------
st.sidebar.header(t("search_filters"))
amount_range    = st.sidebar.slider(t("filter_amount"), 0, 500_000, (100, 300_000))
risk_threshold  = st.sidebar.slider(t("filter_min_risk"), 0.0, 1.0, 0.1, step=0.05)

@st.cache_data(ttl=600)
def get_filter_options(column_name):
    try:
        df = conn.execute(
            f"SELECT DISTINCT {column_name} FROM transactions WHERE {column_name} IS NOT NULL ORDER BY {column_name}"
        ).df()
        return df[column_name].tolist()
    except Exception:
        return []

categories        = ["All"] + get_filter_options("scam_category")
selected_categories = st.sidebar.multiselect(t("filter_scam_typology"), categories, default=["All"])

locations         = ["All"] + get_filter_options("location")
selected_locations  = st.sidebar.multiselect(t("filter_destinations"), locations, default=["All"])

statuses          = ["All"] + get_filter_options("status")
selected_statuses   = st.sidebar.multiselect(t("filter_status"), statuses, default=["All"])

# ---------------------------------------------------------
# Build SQL WHERE clause
# ---------------------------------------------------------
where_clauses = [
    f"amount BETWEEN {amount_range[0]} AND {amount_range[1]}",
    f"risk_score >= {risk_threshold}"
]
if "All" not in selected_categories and selected_categories:
    cat_list = ", ".join([f"'{c}'" for c in selected_categories])
    where_clauses.append(f"scam_category IN ({cat_list})")
if "All" not in selected_locations and selected_locations:
    loc_list = ", ".join([f"'{l}'" for l in selected_locations])
    where_clauses.append(f"location IN ({loc_list})")
if "All" not in selected_statuses and selected_statuses:
    stat_list = ", ".join([f"'{s}'" for s in selected_statuses])
    where_clauses.append(f"status IN ({stat_list})")

where_sql = "WHERE " + " AND ".join(where_clauses)

filtered_query = f"""
    SELECT transaction_id, sender_id, sender_name, receiver_id, receiver_name,
           amount, timestamp, risk_score, status, scam_category, location
    FROM transactions
    {where_sql}
    ORDER BY timestamp DESC
    LIMIT 5000
"""
df_filtered = conn.query(filtered_query).to_df()

# ---------------------------------------------------------
# Transactions Table
# ---------------------------------------------------------
with st.expander(t("view_tx_data"), expanded=False):
    st.markdown(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
            <h4 style="margin:0;">{t("found_matching_tx").format(count=len(df_filtered))}</h4></div>""",
        unsafe_allow_html=True
    )
    search_term = st.text_input(t("search_placeholder"), "")
    if search_term:
        search_pattern = f"%{search_term}%"
        df_filtered = conn.execute(
            """SELECT * FROM df_filtered WHERE sender_id ILIKE ? OR receiver_id ILIKE ?
               OR sender_name ILIKE ? OR receiver_name ILIKE ?""",
            [search_pattern]*4
        ).df()
        st.write(t("filtered_records").format(count=len(df_filtered)))

    st.dataframe(
        df_filtered, use_container_width=True,
        column_config={
            "amount":     st.column_config.NumberColumn("Amount",     format="$%.2f"),
            "risk_score": st.column_config.NumberColumn("Risk Score", format="%.2f"),
        }
    )



# =============================================================
# Tabs
# -------------------------------------------------------------
tabs = st.tabs([
    t("tab_network_risk"),
    t("tab_loop_detection"),
    t("tab_velocity_analysis"),
    t("tab_anomaly_detection"),
])

# ─────────────────────────────────────────────────────────────
# TAB 0: Fraud Network & Risk Patterns
# ─────────────────────────────────────────────────────────────
with tabs[0]:
    st.write(f"### {t('tab_network_risk')}")

    # Shared Merchant Network
    st.write(f"#### {t('high_risk_merchant_concentration')}")
    df_merchants, df_edges = get_shared_merchant_network(where_sql)

    if not df_merchants.empty and not df_edges.empty:
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        total_fraud_vol = df_merchants["total_fraud_volume"].sum()
        vol_str = f"${total_fraud_vol/1e6:.2f}M" if total_fraud_vol >= 1e6 else f"${total_fraud_vol:,.0f}"

        for col, label, val, sub, clr in [
            (col_kpi1, t("risky_merchants"),    len(df_merchants), "with ≥2 flagged senders" if st.session_state.get("language", "TH") == "EN" else "ที่มีผู้โอนกลุ่มเสี่ยง ≥2 ราย", "#F43F5E"),
            (col_kpi2, t("flagged_connections"), len(df_edges),    "sender → merchant links" if st.session_state.get("language", "TH") == "EN" else "การเชื่อมโยง ผู้ส่ง → ร้านค้า", "#F59E0B"),
            (col_kpi3, t("fraud_volume"),        vol_str,          "through risky merchants" if st.session_state.get("language", "TH") == "EN" else "ผ่านร้านค้ากลุ่มเสี่ยง",  "#A855F7"),
        ]:

            with col:
                st.markdown(
                    f"""<div style="background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.08);
                        border-radius:8px;padding:15px;text-align:center;">
                        <h4 style="color:{clr};margin:0;">{label}</h4>
                        <div style="font-size:2.2rem;font-weight:800;color:#F8FAFC;">{val}</div>
                        <span style="font-size:0.8rem;color:#94A3B8;">{sub}</span></div>""",
                    unsafe_allow_html=True
                )

        st.write("")
        col_chart, col_graph = st.columns(2)

        with col_chart:
            fig_bar = px.bar(
                df_merchants.head(10),
                x="merchant_name", y="unique_flagged_senders",
                color="avg_risk", color_continuous_scale=["#F59E0B", "#EF4444"],
                hover_data=["fraud_txn_count", "total_fraud_volume"],
                labels={"merchant_name": "Merchant" if st.session_state.get("language", "TH") == "EN" else "ร้านค้า", "unique_flagged_senders": "Unique Flagged Senders" if st.session_state.get("language", "TH") == "EN" else "ผู้ส่งกลุ่มเสี่ยงที่ไม่ซ้ำ", "avg_risk": "Avg Risk" if st.session_state.get("language", "TH") == "EN" else "ความเสี่ยงเฉลี่ย"}
            )
            fig_bar.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, tickangle=-35),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)", title="Flagged Senders" if st.session_state.get("language", "TH") == "EN" else "ผู้ส่งกลุ่มเสี่ยง"),
                height=500, margin=dict(l=20, r=20, t=20, b=80)
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_graph:
            # Create a Concentric Circle (Shell) Network Graph
            merchants_in_graph = df_edges["merchant_id"].unique().tolist()[:12]
            edge_sub = df_edges[df_edges["merchant_id"].isin(merchants_in_graph)]

            G = nx.DiGraph()
            for _, row in edge_sub.iterrows():
                G.add_edge(row["sender_id"], row["merchant_id"], weight=row["txn_count"])

            m_nodes = [n for n in G.nodes() if n in merchants_in_graph]
            s_nodes = [n for n in G.nodes() if n not in merchants_in_graph]
            
            # Use shell layout: Merchants in the inner circle, Senders in the outer circle
            pos = nx.shell_layout(G, [m_nodes, s_nodes])

            fig_net = go.Figure()
            for u, v in G.edges():
                x0, y0 = pos[u]; x1, y1 = pos[v]
                fig_net.add_trace(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None], mode="lines",
                    line=dict(width=1, color="rgba(239,68,68,0.25)"),
                    hoverinfo="none", showlegend=False
                ))

            lang_curr = st.session_state.get("language", "TH")
            if m_nodes:
                fig_net.add_trace(go.Scatter(
                    x=[pos[n][0] for n in m_nodes], y=[pos[n][1] for n in m_nodes],
                    mode="markers+text",
                    marker=dict(size=28, color="#EF4444", line=dict(width=2, color="#FFF")),
                    text=[n[:15] for n in m_nodes], textposition="bottom center",
                    textfont=dict(size=10, color="#F8FAFC"),
                    hovertext=[f"Merchant: {n}" if lang_curr == "EN" else f"ร้านค้า: {n}" for n in m_nodes], hoverinfo="text",
                    name="Risky Merchants" if lang_curr == "EN" else "ร้านค้าเสี่ยงสูง"
                ))
            if s_nodes:
                fig_net.add_trace(go.Scatter(
                    x=[pos[n][0] for n in s_nodes], y=[pos[n][1] for n in s_nodes],
                    mode="markers+text",
                    marker=dict(size=12, color="#F59E0B", line=dict(width=1, color="#FFF")),
                    text=[n[:12] for n in s_nodes], textposition="top center",
                    textfont=dict(size=8, color="#94A3B8"),
                    hovertext=[f"Sender: {n}" if lang_curr == "EN" else f"ผู้โอน: {n}" for n in s_nodes], hoverinfo="text",
                    name="Flagged Senders" if lang_curr == "EN" else "ผู้ส่งกลุ่มเสี่ยง"
                ))

            fig_net.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(visible=False, range=[-1.2, 1.2]),
                yaxis=dict(visible=False, range=[-1.2, 1.2], scaleanchor="x", scaleratio=1),
                height=500, margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.info("No shared merchant fraud patterns detected under current filter criteria." if st.session_state.get("language", "TH") == "EN" else "ไม่พบเครือข่ายร้านค้าฉ้อโกงร่วมภายใต้เกณฑ์ตัวกรองปัจจุบัน")

    # Risk Pattern Analysis
    st.write("---")
    st.write(f"#### {t('risk_pattern_analysis')}")
    df_risk_dist, df_category = get_risk_pattern_analysis(where_sql)

    if not df_risk_dist.empty:
        flagged_row = df_risk_dist[df_risk_dist["status"] == "Flagged"]
        cleared_row = df_risk_dist[df_risk_dist["status"] == "Cleared"]
        flagged_count = int(flagged_row["txn_count"].iloc[0]) if not flagged_row.empty else 0
        flagged_avg   = float(flagged_row["avg_amount"].iloc[0]) if not flagged_row.empty else 0
        cleared_avg   = float(cleared_row["avg_amount"].iloc[0]) if not cleared_row.empty else 0
        total_txns    = int(df_risk_dist["txn_count"].sum())
        fraud_pct     = (flagged_count / total_txns * 100) if total_txns > 0 else 0
        ratio         = flagged_avg / cleared_avg if cleared_avg > 0 else 0

        r1, r2, r3 = st.columns(3)
        for col, label, val, sub, clr in [
            (r1, t("flagged_txns_label"),  f"{flagged_count:,}",     f"{fraud_pct:.1f}% " + ("of all" if lang_curr == "EN" else "ของทั้งหมด"),      "#F43F5E"),
            (r2, t("avg_flagged_amount"),    f"${flagged_avg:,.0f}",   "per flagged transaction" if lang_curr == "EN" else "ต่อธุรกรรมที่ระงับ",        "#F59E0B"),
            (r3, t("fraud_clean_ratio"),     f"{ratio:.1f}x",          "flagged avg vs cleared avg" if lang_curr == "EN" else "เทียบความเสี่ยงสูงกับปกติ",     "#6366F1"),
        ]:
            with col:
                st.markdown(
                    f"""<div style="background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.08);
                        border-radius:8px;padding:15px;text-align:center;">
                        <h4 style="color:{clr};margin:0;">{label}</h4>
                        <div style="font-size:2.2rem;font-weight:800;color:#F8FAFC;">{val}</div>
                        <span style="font-size:0.8rem;color:#94A3B8;">{sub}</span></div>""",
                    unsafe_allow_html=True
                )

        st.write("")
        col_bar, col_box = st.columns(2)
        color_map = {"Flagged": "#EF4444", "Pending": "#F59E0B", "Cleared": "#10B981"}

        def fmt_amt(x):
            if x >= 1e9: return f"{x/1e9:.1f}B"
            if x >= 1e6: return f"{x/1e6:.1f}M"
            if x >= 1e3: return f"{x/1e3:.1f}K"
            return str(int(x))

        df_risk_dist["text_label"] = df_risk_dist["total_volume"].apply(fmt_amt)

        with col_bar:
            st.write(f"##### {t('tx_volume_by_status')}")
            fig_status = px.bar(
                df_risk_dist, x="status", y="total_volume",
                text="text_label",
                labels={"total_volume": "Total Volume ($)" if lang_curr == "EN" else "มูลค่าเงินรวม ($)", "status": "Status" if lang_curr == "EN" else "สถานะ"}
            )
            colors_status = [color_map.get(s, "#3B82F6") for s in df_risk_dist['status']]
            fig_status.update_traces(
                marker_color=colors_status,
                textposition="outside"
            )
            fig_status.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)", title="Total Volume ($)" if lang_curr == "EN" else "มูลค่าเงินรวม ($)"),
                height=350, margin=dict(l=20, r=20, t=10, b=10)
            )
            st.plotly_chart(fig_status, use_container_width=True)

        with col_box:
            st.write(f"##### {t('avg_tx_amount_by_status')}")
            fig_avg = px.bar(
                df_risk_dist, x="status", y="avg_amount",
                text_auto="$,.0f",
                labels={"avg_amount": "Average Amount ($)" if lang_curr == "EN" else "ค่าเฉลี่ยต่อธุรกรรม ($)", "status": "Status" if lang_curr == "EN" else "สถานะ"}
            )
            colors_avg = [color_map.get(s, "#3B82F6") for s in df_risk_dist['status']]
            fig_avg.update_traces(
                marker_color=colors_avg
            )
            fig_avg.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)", title="Average Amount ($)" if lang_curr == "EN" else "ค่าเฉลี่ยต่อธุรกรรม ($)"),
                height=350, margin=dict(l=20, r=20, t=10, b=10)
            )
            st.plotly_chart(fig_avg, use_container_width=True)

    if not df_category.empty:
        st.write("---")
        st.write(f"##### {t('fraud_volume_by_category')}")
        fig_cat = px.scatter(
            df_category, x="avg_risk", y="total_volume",
            size="total_txns", color="scam_category",
            hover_name="scam_category", text="scam_category", size_max=60,
            labels={"avg_risk": "Average Risk Score" if lang_curr == "EN" else "คะแนนความเสี่ยงเฉลี่ย", "total_volume": "Total Volume ($)" if lang_curr == "EN" else "มูลค่ารวม ($)", "total_txns": "Transaction Count" if lang_curr == "EN" else "จำนวนธุรกรรม"}
        )
        fig_cat.update_traces(textposition="top center", textfont=dict(size=11, color="#F8FAFC"))
        fig_cat.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)", type="log"),
            showlegend=False, height=400, margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_cat, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# TAB 1: Circular Loop Detection (NEW — 2.2)
# ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.write(f"### {t('circular_fund_flow_title')}")
    st.write(t("circular_fund_flow_desc"))

    with st.spinner("กำลังตรวจจับ Circular Loops ด้วย DuckDB Self-Join..." if lang_curr == "TH" else "Detecting circular loops using DuckDB..."):
        df_loops, df_loop_summary = detect_circular_loops()

    if df_loops.empty:
        st.info(
            "ไม่พบ Circular Loops ในข้อมูลปัจจุบัน — ลองตรวจสอบการกรองหรือชุดข้อมูลอื่น" if lang_curr == "TH" else "No circular money loops detected under current filters."
        )
    else:
        # KPI Summary
        direct_loops = len(df_loops[df_loops["loop_type"] == "direct_loop"]) if "loop_type" in df_loops.columns else 0
        three_hops   = len(df_loops[df_loops["loop_type"] == "three_hop"])  if "loop_type" in df_loops.columns else 0
        total_loop_amt = (df_loops["amount_ab"].sum() + df_loops["amount_bc"].sum())

        kc1, kc2, kc3 = st.columns(3)
        for col, label, val, sub, clr in [
            (kc1, t("direct_loops"), f"{direct_loops:,}", "2-hop circular transfers" if lang_curr == "EN" else "ธุรกรรมหมุนเวียนโอนกลับทางตรง",      "#F43F5E"),
            (kc2, t("three_hop_loops"), f"{three_hops:,}", "extended layering chains" if lang_curr == "EN" else "เครือข่ายบัญชีม้า 3 ขั้น",       "#F59E0B"),
            (kc3, t("total_loop_volume"),      f"${total_loop_amt:,.0f}" if total_loop_amt < 1e6 else f"${total_loop_amt/1e6:.2f}M",
             "cumulative amount in loops" if lang_curr == "EN" else "ยอดเงินโอนรวมในเครือข่ายนี้", "#A855F7"),
        ]:
            with col:
                st.markdown(
                    f"""<div style="background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.08);
                        border-radius:8px;padding:15px;text-align:center;">
                        <h4 style="color:{clr};margin:0;">{label}</h4>
                        <div style="font-size:2rem;font-weight:800;color:#F8FAFC;">{val}</div>
                        <span style="font-size:0.8rem;color:#94A3B8;">{sub}</span></div>""",
                    unsafe_allow_html=True
                )

        st.write("")
        graph_col, table_col = st.columns([3, 2])

        with graph_col:
            st.write(f"#### {t('circular_loop_network_graph')}")
            st.caption(t("circular_graph_caption"))

            # Build networkx directed graph from loops
            G_loop = nx.DiGraph()
            for _, row in df_loops.iterrows():
                G_loop.add_edge(row["node_a"], row["node_b"], weight=float(row.get("amount_ab", 1)))
                G_loop.add_edge(row["node_b"], row["node_c"] if pd.notna(row.get("node_c")) else row["node_a"],
                                weight=float(row.get("amount_bc", 1)))

            if len(G_loop.nodes()) > 0:
                pos_loop = nx.spring_layout(G_loop, seed=7, k=3.0)

                fig_loop = go.Figure()

                # Draw edges with arrows (annotated)
                max_w = max([d.get("weight", 1) for _, _, d in G_loop.edges(data=True)] or [1])
                for u, v, data in G_loop.edges(data=True):
                    x0, y0 = pos_loop[u]; x1, y1 = pos_loop[v]
                    w = data.get("weight", 1)
                    lw = 1 + (w / max_w) * 4
                    fig_loop.add_trace(go.Scatter(
                        x=[x0, x1, None], y=[y0, y1, None],
                        mode="lines",
                        line=dict(width=lw, color="rgba(248, 68, 68, 0.5)"),
                        hoverinfo="none", showlegend=False
                    ))
                    # Arrowhead annotation
                    fig_loop.add_annotation(
                        ax=x0, ay=y0, x=x1, y=y1,
                        xref="x", yref="y", axref="x", ayref="y",
                        showarrow=True, arrowhead=2, arrowsize=1.2,
                        arrowwidth=lw * 0.8, arrowcolor="rgba(239,68,68,0.7)"
                    )

                # Node colors: in cycle = red, others = orange
                all_loop_nodes = list(G_loop.nodes())
                try:
                    cycles = list(nx.simple_cycles(G_loop))
                    cycle_nodes = {n for c in cycles for n in c}
                except Exception:
                    cycle_nodes = set()

                node_colors = ["#EF4444" if n in cycle_nodes else "#F59E0B" for n in all_loop_nodes]
                node_sizes  = [24 if n in cycle_nodes else 16 for n in all_loop_nodes]

                fig_loop.add_trace(go.Scatter(
                    x=[pos_loop[n][0] for n in all_loop_nodes],
                    y=[pos_loop[n][1] for n in all_loop_nodes],
                    mode="markers+text",
                    marker=dict(size=node_sizes, color=node_colors, line=dict(width=2, color="#FFF")),
                    text=[n[:16] for n in all_loop_nodes],
                    textposition="top center",
                    textfont=dict(size=8, color="#F8FAFC"),
                    hovertext=[f"Account: {n}<br>In Loop: {'✅' if n in cycle_nodes else '🔶'}" for n in all_loop_nodes],
                    hoverinfo="text",
                    name="Loop Nodes"
                ))

                fig_loop.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=480, margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig_loop, use_container_width=True)
            else:
                st.info("ไม่สามารถวาด graph ได้ — ไม่มี node ใน loop" if lang_curr == "TH" else "Cannot render graph — no nodes in loop")

        with table_col:
            st.write(f"#### {t('loop_participants_summary')}")
            if not df_loop_summary.empty:
                df_loop_summary_display = df_loop_summary.copy()
                df_loop_summary_display["total_out"] = df_loop_summary_display["total_out"].apply(
                    lambda x: f"${x:,.2f}"
                )
                df_loop_summary_display["avg_risk"] = df_loop_summary_display["avg_risk"].apply(
                    lambda x: f"{x:.3f}"
                )
                df_loop_summary_display = df_loop_summary_display.rename(columns={
                    "sender_id": "Account ID",
                    "out_txns":  "Outbound Txns" if lang_curr == "EN" else "จำนวนโอนออก",
                    "total_out": "Total Sent" if lang_curr == "EN" else "ยอดเงินโอนออก",
                    "avg_risk":  "Avg Risk" if lang_curr == "EN" else "ความเสี่ยงเฉลี่ย"
                })
                st.dataframe(df_loop_summary_display, use_container_width=True, height=300)

            # Raw loop details
            st.write(f"#### {t('detected_loop_edges')}")
            display_cols = [c for c in ["node_a", "node_b", "node_c", "amount_ab", "amount_bc", "loop_type"] if c in df_loops.columns]
            df_loops_display = df_loops[display_cols].head(50).copy()
            if "amount_ab" in df_loops_display.columns:
                df_loops_display["amount_ab"] = df_loops_display["amount_ab"].apply(lambda x: f"${x:,.2f}")
            if "amount_bc" in df_loops_display.columns:
                df_loops_display["amount_bc"] = df_loops_display["amount_bc"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df_loops_display, use_container_width=True, height=200)
            st.download_button(
                "📥 Export CSV" if lang_curr == "EN" else "📥 ส่งออกไฟล์ CSV",
                df_loops.to_csv(index=False),
                "circular_loops.csv",
                "text/csv"
            )

# ─────────────────────────────────────────────────────────────
# TAB 2: Velocity / Burst Analysis (NEW — 2.3)
# ─────────────────────────────────────────────────────────────
with tabs[2]:
    st.write(f"### {t('velocity_burst_title')}")
    st.write(t("velocity_burst_desc"))

    v_col1, v_col2 = st.columns([1, 3], vertical_alignment="bottom")
    with v_col1:
        min_burst = st.number_input(t("min_tx_day_threshold"), min_value=1, max_value=50, value=5, step=1)
    with v_col2:
        st.info(t("velocity_info_msg"))

    burst_df = get_suspicious_accounts_velocity(min_txns_per_day=min_burst)

    if not burst_df.empty:
        # KPIs
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            st.markdown(
                f"""<div style="background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.2);
                    border-radius:8px;padding:15px;text-align:center;">
                    <h4 style="color:#F43F5E;margin:0;">{"Burst Accounts" if lang_curr == "EN" else "บัญชีความถี่สูง"}</h4>
                    <div style="font-size:2rem;font-weight:800;color:#F8FAFC;">{burst_df['sender_id'].nunique()}</div>
                    <span style="font-size:0.8rem;color:#94A3B8;">{"unique accounts flagged" if lang_curr == "EN" else "จำนวนบัญชีที่พบ"}</span></div>""",
                unsafe_allow_html=True
            )
        with vc2:
            st.markdown(
                f"""<div style="background:rgba(245,158,11,0.05);border:1px solid rgba(245,158,11,0.2);
                    border-radius:8px;padding:15px;text-align:center;">
                    <h4 style="color:#F59E0B;margin:0;">{"Max Txns/Day" if lang_curr == "EN" else "สูงสุดต่อวัน"}</h4>
                    <div style="font-size:2rem;font-weight:800;color:#F8FAFC;">{int(burst_df['transaction_count'].max())}</div>
                    <span style="font-size:0.8rem;color:#94A3B8;">{"peak burst recorded" if lang_curr == "EN" else "สถิติจำนวนครั้งสูงสุด"}</span></div>""",
                unsafe_allow_html=True
            )
        with vc3:
            burst_vol = burst_df["total_amount"].sum()
            burst_vol_str = f"${burst_vol/1e6:.2f}M" if burst_vol >= 1e6 else f"${burst_vol:,.0f}"
            st.markdown(
                f"""<div style="background:rgba(99,102,241,0.05);border:1px solid rgba(99,102,241,0.2);
                    border-radius:8px;padding:15px;text-align:center;">
                    <h4 style="color:#6366F1;margin:0;">{"Burst Volume" if lang_curr == "EN" else "ยอดเงินธุรกรรมพุ่ง"}</h4>
                    <div style="font-size:2rem;font-weight:800;color:#F8FAFC;">{burst_vol_str}</div>
                    <span style="font-size:0.8rem;color:#94A3B8;">{"total in burst transactions" if lang_curr == "EN" else "ยอดรวมของกลุ่มนี้"}</span></div>""",
                unsafe_allow_html=True
            )

        st.write("")
        bar_col, tbl_col = st.columns([2, 1])

        with bar_col:
            st.write(f"#### {t('top_burst_accounts')}")
            top_burst = burst_df.groupby("sender_id").agg(
                max_txns=("transaction_count", "max"),
                total_amt=("total_amount", "sum"),
                max_risk=("max_risk_score", "max"),
                days_active=("txn_date", "count")
            ).reset_index().sort_values("max_txns", ascending=False).head(15)

            fig_burst = px.bar(
                top_burst,
                x="sender_id", y="max_txns",
                color="max_risk",
                color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"],
                range_color=[0, 1],
                hover_data=["total_amt", "days_active"],
                labels={"sender_id": "Account ID", "max_txns": "Max Txns/Day" if lang_curr == "EN" else "จำนวนสูงสุดต่อวัน", "max_risk": "Max Risk Score" if lang_curr == "EN" else "ความเสี่ยงสูงสุด"}
            )
            fig_burst.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, tickangle=-40),
                yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                height=380, margin=dict(l=20, r=20, t=10, b=80)
            )
            st.plotly_chart(fig_burst, use_container_width=True)

        with tbl_col:
            st.write(f"#### {t('burst_account_details')}")
            burst_display = burst_df.copy()
            burst_display["total_amount"] = burst_display["total_amount"].apply(lambda x: f"${x:,.2f}")
            burst_display["max_risk_score"] = burst_display["max_risk_score"].apply(lambda x: f"{x:.3f}")
            st.dataframe(
                burst_display[["sender_id", "txn_date", "transaction_count", "total_amount", "max_risk_score"]].rename(columns={
                    "sender_id": "Account" if lang_curr == "EN" else "บัญชี", "txn_date": "Date" if lang_curr == "EN" else "วันที่",
                    "transaction_count": "Txns" if lang_curr == "EN" else "จำนวนครั้ง", "total_amount": "Volume" if lang_curr == "EN" else "ยอดเงิน", "max_risk_score": "Max Risk" if lang_curr == "EN" else "ความเสี่ยงสูงสุด"
                }),
                use_container_width=True, height=380
            )
    else:
        st.info(f"ไม่พบบัญชีที่มีธุรกรรม ≥ {min_burst} ครั้งต่อวัน ลองลด threshold ลง" if lang_curr == "TH" else f"No accounts found with ≥ {min_burst} transactions/day. Try lowering the threshold.")

    # 2.7 — Fraud Temporal: Bubble Map + Hourly Trend
    st.write("---")
    st.write(f"#### {t('fraud_temporal_analysis')}")
    st.write(t("fraud_temporal_caption"))

    heatmap_df = get_hourly_velocity_heatmap()

    if not heatmap_df.empty:
        options = ["Flagged Transactions", "All Transactions", "Total Volume ($)"] if lang_curr == "EN" else ["ธุรกรรมที่ระงับ (Flagged)", "ธุรกรรมทั้งหมด", "ยอดรวมเงินโอน ($)"]
        heat_toggle = st.radio(
            "แสดงข้อมูล:" if lang_curr == "TH" else "Show data:", options,
            horizontal=True, key="heatmap_toggle"
        )
        col_map = {
            options[0]: "flagged_count",
            options[1]: "txn_count",
            options[2]: "total_amount"
        }
        heat_col = col_map[heat_toggle]

        dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if lang_curr == "EN" else ["จันทร์", "อังคาร", "พุธ", "พฤหัสฯ", "ศุกร์", "เสาร์", "อาทิตย์"]
        dow_eng_map = {"Mon": "จันทร์", "Tue": "อังคาร", "Wed": "พุธ", "Thu": "พฤหัสฯ", "Fri": "ศุกร์", "Sat": "เสาร์", "Sun": "อาทิตย์"}

        # ─── Bubble Chart: Hour × Day ───
        bubble_df = heatmap_df.copy()
        bubble_df["hour_label"] = bubble_df["hour_of_day"].apply(lambda h: f"{h:02d}:00")
        if lang_curr == "TH":
            bubble_df["day_name_mapped"] = bubble_df["day_name"].map(dow_eng_map)
            bubble_df["day_num"] = bubble_df["day_name_mapped"].map({d: i for i, d in enumerate(dow_order)})
            y_axis_col = "day_name_mapped"
        else:
            bubble_df["day_num"] = bubble_df["day_name"].map({d: i for i, d in enumerate(dow_order)})
            y_axis_col = "day_name"
            
        max_val = bubble_df[heat_col].max() if bubble_df[heat_col].max() > 0 else 1

        # Format text for hover
        if heat_col == "total_amount":
            bubble_df["text_val"] = bubble_df[heat_col].apply(lambda v: f"${int(v):,}")
        else:
            bubble_df["text_val"] = bubble_df[heat_col].apply(lambda v: str(int(v)))

        fig_bubble = go.Figure()

        fig_bubble.add_trace(go.Scatter(
            x=bubble_df["hour_of_day"],
            y=bubble_df[y_axis_col],
            mode="markers",
            marker=dict(
                size=bubble_df[heat_col].apply(lambda v: max(8, (v / max_val) * 50)),
                color=bubble_df[heat_col],
                colorscale=[
                    [0.0, "#1E293B"],
                    [0.3, "#3B82F6"],
                    [0.6, "#8B5CF6"],
                    [0.8, "#F59E0B"],
                    [1.0, "#EF4444"]
                ],
                showscale=True,
                colorbar=dict(
                    title=dict(text="", font=dict(color="#94A3B8")),
                    tickfont=dict(color="#94A3B8"),
                    thickness=10, len=0.9
                ),
                line=dict(width=1, color="rgba(255,255,255,0.15)"),
                opacity=0.9
            ),
            text=bubble_df["text_val"],
            customdata=bubble_df[y_axis_col],
            hovertemplate="<b>%{customdata} — %{x}:00</b><br>" + heat_toggle + ": %{text}<extra></extra>"
        ))

        fig_bubble.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=50),
            height=340,
            xaxis=dict(
                showgrid=True, gridcolor="rgba(148,163,184,0.05)",
                tickmode="array",
                tickvals=list(range(24)),
                ticktext=[f"{h:02d}:00" for h in range(24)],
                tickangle=-45,
                tickfont=dict(size=10, color="#94A3B8"),
                title=dict(text="Hour of Day" if lang_curr == "EN" else "ชั่วโมงในแต่ละวัน", font=dict(color="#64748B", size=11)),
                range=[-0.8, 23.8]
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(148,163,184,0.05)",
                categoryorder="array", categoryarray=list(reversed(dow_order)),
                tickfont=dict(size=12, color="#CBD5E1"),
                title=dict(text="Day of Week" if lang_curr == "EN" else "วันในหนึ่งสัปดาห์", font=dict(color="#64748B", size=11))
            )
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

        # ─── Hourly Trend Area Chart (summary below) ───
        hourly_totals = heatmap_df.groupby("hour_of_day", as_index=False)[heat_col].sum()
        all_hours = pd.DataFrame({"hour_of_day": list(range(24))})
        hourly_totals = all_hours.merge(hourly_totals, on="hour_of_day", how="left").fillna(0)

        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=hourly_totals["hour_of_day"],
            y=hourly_totals[heat_col],
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.15)",
            line=dict(color="#6366F1", width=2, shape="spline"),
            mode="lines+markers",
            marker=dict(size=5, color="#6366F1"),
            hovertemplate="<b>%{x}:00</b><br>Total: %{y:,.0f}<extra></extra>"
        ))
        fig_area.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=5, b=10),
            height=140,
            xaxis=dict(
                showgrid=False,
                tickmode="array",
                tickvals=list(range(24)),
                ticktext=[f"{h}h" for h in range(24)],
                tickfont=dict(size=9, color="#64748B")
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(148,163,184,0.06)", zeroline=False,
                tickfont=dict(color="#64748B", size=9),
                title=dict(text="Total" if lang_curr == "EN" else "รวม", font=dict(color="#64748B", size=10))
            ),
            showlegend=False
        )
        st.caption(t("hourly_trend_caption"))
        st.plotly_chart(fig_area, use_container_width=True)

    else:
        st.info("ไม่มีข้อมูลเพียงพอสำหรับการวิเคราะห์ — กรุณาโหลด dataset ที่มีข้อมูล timestamp" if lang_curr == "TH" else "Insufficient data for temporal analysis — please load a dataset containing timestamps.")

# ─────────────────────────────────────────────────────────────
# TAB 3: Credit Card Anomaly Detection (3.3 Box/Violin toggle)
# ─────────────────────────────────────────────────────────────
with tabs[3]:
    st.write(f"### {t('tx_amount_anomaly_title')}")
    st.write(t("tx_amount_anomaly_desc"))

    # 3.3 — Box / Violin toggle
    lang_curr = st.session_state.get("language", "TH")
    chart_type = st.radio(t("chart_type_label"), [t("plot_box"), t("plot_violin")], horizontal=True)

    if "Box" in chart_type or "กล่อง" in chart_type:
        fig_box = px.box(
            df_filtered,
            x="status", y="amount", color="status",
            hover_data=["timestamp", "sender_id", "receiver_id", "risk_score", "scam_category"],
            color_discrete_map={"Cleared": "#3B82F6", "Flagged": "#EF4444", "Pending": "#F59E0B"},
            points="outliers",
            labels={"status": "Status" if lang_curr == "EN" else "สถานะ", "amount": "Amount ($)" if lang_curr == "EN" else "มูลค่า ($)"}
        )
        fig_box.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Transaction Status" if lang_curr == "EN" else "สถานะธุรกรรม", showgrid=False),
            yaxis=dict(title="Amount ($)" if lang_curr == "EN" else "มูลค่าธุรกรรม ($)", gridcolor="rgba(255,255,255,0.1)"),
            height=450, margin=dict(l=20, r=20, t=10, b=10),
            showlegend=False
        )
        st.plotly_chart(fig_box, use_container_width=True)

    else:
        fig_violin = px.violin(
            df_filtered,
            x="status", y="amount", color="status",
            box=True, points="outliers",
            hover_data=["risk_score", "scam_category"],
            color_discrete_map={"Cleared": "#3B82F6", "Flagged": "#EF4444", "Pending": "#F59E0B"},
            labels={"status": "Status" if lang_curr == "EN" else "สถานะ", "amount": "Amount ($)" if lang_curr == "EN" else "มูลค่า ($)"}
        )
        fig_violin.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Transaction Status" if lang_curr == "EN" else "สถานะธุรกรรม", showgrid=False),
            yaxis=dict(title="Amount ($)" if lang_curr == "EN" else "มูลค่าธุรกรรม ($)", gridcolor="rgba(255,255,255,0.1)"),
            height=450, margin=dict(l=20, r=20, t=10, b=10),
            showlegend=False
        )
        st.plotly_chart(fig_violin, use_container_width=True)

    # Caption explaining the difference
    if "Violin" in chart_type or "ไวโอลิน" in chart_type:
        st.caption(t("violin_caption"))
    else:
        st.caption(t("box_caption"))
