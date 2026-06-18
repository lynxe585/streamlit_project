import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from utils.styles import inject_global_styles, render_kpi_card
from utils.sidebar import render_global_sidebar
from utils.db import initialize_database, get_connection_status, get_duckdb_connection
from utils.data_processing import (
    get_overall_metrics,
    get_daily_transaction_trends_ranged,
    get_high_risk_transactions,
    get_scam_category_distribution,
    get_data_source_distribution,
    get_geographical_risk,
)
from utils.translation import t

# ---------------------------------------------------------
# Streamlit Page Config
# ---------------------------------------------------------
st.set_page_config(
    page_title="Financial Fraud & Scam Detection Network",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Global Styles
# ---------------------------------------------------------
inject_global_styles()

# ---------------------------------------------------------
# Sidebar & DB Init
# ---------------------------------------------------------
render_global_sidebar()

# ---------------------------------------------------------
# Connection Error Banner
# ---------------------------------------------------------
conn_status = get_connection_status()
if not conn_status["snowflake_connected"] and not conn_status["mongodb_connected"]:
    st.warning(
        "⚠️ **ไม่มี Cloud Data Source ที่เชื่อมต่อสำเร็จ** — "
        "กรุณาตรวจสอบ Snowflake และ MongoDB credentials ใน `.streamlit/secrets.toml` "
        "แอปกำลังทำงานด้วยข้อมูลว่าง (ตรวจสอบ Connection Status ใน Sidebar)",
        icon="🔌"
    )

# ---------------------------------------------------------
# Auto-refresh every 30 seconds
# ---------------------------------------------------------
count = st_autorefresh(interval=30000, limit=None, key="exec_dash_autorefresh")

# ---------------------------------------------------------
# Page Title
# ---------------------------------------------------------
st.title(t("exec_dashboard_title"))

start_date = None
end_date   = None

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Load Metrics
# ---------------------------------------------------------
metrics_df = get_overall_metrics()
if not metrics_df.empty:
    m = metrics_df.iloc[0]
    total_txns      = m["total_txns"]
    total_volume    = m["total_volume"]
    avg_risk        = m["avg_risk"]
    high_risk_txns  = m["high_risk_txns"]
    flagged_txns    = m["flagged_txns"]
    high_risk_volume= m["high_risk_volume"]
    value_saved     = m.get("value_saved", 0)
    actual_loss     = m.get("actual_loss", 0)
else:
    total_txns = total_volume = avg_risk = high_risk_txns = flagged_txns = high_risk_volume = 0
    value_saved = actual_loss = 0

def format_short(num):
    if num >= 1e9: return f"${num/1e9:.2f}B"
    if num >= 1e6: return f"${num/1e6:.2f}M"
    if num >= 1e3: return f"${num/1e3:.1f}K"
    return f"${num:.2f}"

# ---------------------------------------------------------
# KPI Cards Row
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(t("kpi_total_txns"), f"{int(total_txns):,}", t("kpi_processed"))
with col2:
    render_kpi_card(t("kpi_total_volume"), format_short(total_volume), t("kpi_value_transacted"))
with col3:
    render_kpi_card(t("kpi_avg_risk"), f"{avg_risk * 100:.1f}%", t("kpi_system_wide_risk"))
with col4:
    render_kpi_card(t("kpi_high_risk_alerts"), f"{int(high_risk_txns):,}", t("kpi_threshold_alerts"),
                    border_color="#EF4444", bg_color_rgba="rgba(239, 68, 68, 0.05)", text_color="#EF4444")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# ROI + Gauge Row
# ---------------------------------------------------------
st.subheader(t("business_impact"))
roi_col1, roi_col2, roi_col3 = st.columns([1, 1, 2])

with roi_col1:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 3px solid #10B981; background: rgba(16, 185, 129, 0.05); min-height: 100px; padding: 15px;">
            <div class="metric-value" style="color: #10B981; font-size: 1.8rem;">{format_short(value_saved)}</div>
            <div class="metric-label" style="font-size: 0.8rem;">{t("value_saved")}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with roi_col2:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 3px solid #EF4444; background: rgba(239, 68, 68, 0.05); min-height: 100px; padding: 15px;">
            <div class="metric-value" style="color: #EF4444; font-size: 1.8rem;">{format_short(actual_loss)}</div>
            <div class="metric-label" style="font-size: 0.8rem;">{t("actual_loss")}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 2.6 — Gauge Chart: System Risk Level
with roi_col3:
    gauge_val = round(avg_risk * 100, 1)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=gauge_val,
        delta={"reference": 15, "suffix": "%", "increasing": {"color": "#EF4444"}, "decreasing": {"color": "#10B981"}},
        number={"suffix": "%", "font": {"size": 36, "color": "#F8FAFC"}},
        title={"text": t("system_risk_level"), "font": {"size": 13, "color": "#94A3B8"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94A3B8", "tickfont": {"color": "#94A3B8"}},
            "bar": {"color": "#6366F1", "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30],  "color": "rgba(16, 185, 129, 0.15)"},
                {"range": [30, 70], "color": "rgba(245, 158, 11, 0.15)"},
                {"range": [70, 100],"color": "rgba(239, 68, 68, 0.15)"},
            ],
            "threshold": {
                "line": {"color": "#F43F5E", "width": 3},
                "thickness": 0.75,
                "value": 70
            }
        }
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=150,
        margin=dict(l=30, r=30, t=20, b=0),
        font={"color": "#94A3B8"}
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

# ---------------------------------------------------------
# 7.1 — Fraud Detection Funnel Chart
# ---------------------------------------------------------
st.markdown("---")
funnel_col, trend_col = st.columns(2)

with funnel_col:
    st.subheader(t("fraud_funnel_title"))
    detection_rate = (flagged_txns / total_txns * 100) if total_txns > 0 else 0
    false_neg_rate  = (actual_loss / value_saved * 100) if value_saved > 0 else 0

    lang = st.session_state.get("language", "TH")
    funnel_labels = [
        "All Transactions" if lang == "EN" else "ธุรกรรมทั้งหมด",
        "High Risk Flagged" if lang == "EN" else "ตรวจพบความเสี่ยงสูง",
        "Confirmed Fraud" if lang == "EN" else "ยืนยันการฉ้อโกง",
        "False Negatives (Missed)" if lang == "EN" else "ความเสียหายที่เล็ดลอด"
    ]
    funnel_values = [
        int(total_txns),
        int(high_risk_txns),
        int(flagged_txns),
        max(1, int(flagged_txns * 0.02))
    ]
    funnel_colors = ["#6366F1", "#F59E0B", "#EF4444", "#64748B"]

    def format_funnel_num(n):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.1f}k"
        return str(n)

    funnel_text = [
        f"{format_funnel_num(v)} ({v/max(1, funnel_values[0]):.0%})"
        for v in funnel_values
    ]

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_labels,
        x=funnel_values,
        text=funnel_text,
        textinfo="text",
        marker={"color": funnel_colors},
        connector={"line": {"color": "rgba(255,255,255,0.1)", "width": 1}},
        textfont={"color": "#F8FAFC", "size": 12}
    ))
    fig_funnel.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=280,
        font={"color": "#94A3B8"}
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

# ---------------------------------------------------------
# 2.1 — Daily Transaction Trend (connected to Date Range)
# ---------------------------------------------------------
with trend_col:
    st.subheader(t("daily_trend_title"))
    trend_df = get_daily_transaction_trends_ranged(start_date, end_date)

    if not trend_df.empty:
        fig_trend = go.Figure()

        # Total volume area
        fig_trend.add_trace(go.Scatter(
            x=trend_df["txn_date"], y=trend_df["total_amount"],
            name="Total Volume ($)" if lang == "EN" else "ปริมาณการโอนรวม ($)",
            mode="lines",
            line=dict(color="#6366F1", width=2),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.1)",
            yaxis="y2"
        ))
        # High-risk volume area
        fig_trend.add_trace(go.Scatter(
            x=trend_df["txn_date"], y=trend_df["high_risk_amount"],
            name="High-Risk Volume ($)" if lang == "EN" else "ปริมาณความเสี่ยงสูง ($)",
            mode="lines",
            line=dict(color="#EF4444", width=2, dash="dot"),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.07)",
            yaxis="y2"
        ))
        # Transaction count bars
        fig_trend.add_trace(go.Bar(
            x=trend_df["txn_date"], y=trend_df["txn_count"],
            name="Txn Count" if lang == "EN" else "จำนวนธุรกรรม",
            marker_color="rgba(99, 102, 241, 0.3)",
            yaxis="y"
        ))

        fig_trend.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=280,
            margin=dict(l=20, r=20, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(title="Txn Count" if lang == "EN" else "จำนวนธุรกรรม", gridcolor="rgba(255,255,255,0.07)", side="left"),
            yaxis2=dict(title="Volume ($)" if lang == "EN" else "ปริมาณการโอน ($)", overlaying="y", side="right", showgrid=False),
            barmode="overlay"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No transaction trend data available for the selected date range.")


# ---------------------------------------------------------
# Chart Row: Transaction Type + High Risk Feed
# ---------------------------------------------------------
st.markdown("---")
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader(t("tx_volume_risk_type"))
    conn = get_duckdb_connection()
    try:
        type_df = conn.query("""
            SELECT
                transaction_type,
                SUM(amount) as total_amount,
                SUM(CASE WHEN risk_score >= 0.7 THEN amount ELSE 0 END) as high_risk_amount
            FROM transactions
            GROUP BY transaction_type
            ORDER BY total_amount DESC
        """).to_df()

        if not type_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=type_df["transaction_type"], x=type_df["total_amount"],
                name="Total Volume ($)" if lang == "EN" else "ยอดเงินรวม ($)", marker_color="#6366F1", orientation="h"
            ))
            fig.add_trace(go.Bar(
                y=type_df["transaction_type"], x=type_df["high_risk_amount"],
                name="High Risk Volume ($)" if lang == "EN" else "ยอดเงินความเสี่ยงสูง ($)", marker_color="#EF4444", orientation="h"
            ))
            fig.update_layout(
                template="plotly_dark", barmode="group",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=False, title="Transaction Type" if lang == "EN" else "ประเภทธุรกรรม", autorange="reversed"),
                xaxis=dict(title="Volume ($) [Log Scale]" if lang == "EN" else "ปริมาณธุรกรรม ($) [Log Scale]", type="log", gridcolor="rgba(255,255,255,0.1)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=10, b=10), height=380
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction data available.")
    except Exception:
        st.warning("Chart data unavailable.")

with right_col:
    st.subheader(t("realtime_feed"))
    high_risk_df = get_high_risk_transactions(limit=5)

    if not high_risk_df.empty:
        for _, row in high_risk_df.iterrows():
            badge_class = "badge-high" if row["risk_score"] >= 0.85 else "badge-med"
            st.markdown(
                f"""
                <div style="background: rgba(30,41,59,0.3); border: 1px solid rgba(255,255,255,0.05);
                            border-radius: 8px; padding: 12px; margin-bottom: 10px;
                            display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; color: #F8FAFC;">
                            {row['sender_id']} ➡️ {row['receiver_id']}
                        </div>
                        <div style="font-size: 0.8rem; color: #94A3B8;">
                            {"Amount" if lang == "EN" else "ยอดเงิน"}: <strong style="color: #F8FAFC;">${row['amount']:,.2f}</strong>
                            | {"Category" if lang == "EN" else "ประเภทคดี"}: {row['scam_category']}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="{badge_class}">Risk: {row['risk_score']*100:.1f}%</span>
                        <div style="font-size: 0.8rem; color: #EF4444; font-weight: 600; margin-top: 5px;">
                            {row['status']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.download_button("📥 Export CSV" if lang == "EN" else "📥 ส่งออกไฟล์ CSV", high_risk_df.to_csv(index=False), "high_risk_feed.csv", "text/csv")
    else:
        st.info("No high-risk transactions detected.")

# ---------------------------------------------------------
# Donut (3.4 fix: add absolute values) + Geographic Map
# ---------------------------------------------------------
st.markdown("---")
cat_col, loc_col = st.columns(2)

with cat_col:
    st.subheader(t("scam_typologies"))
    cat_df = get_scam_category_distribution()
    cat_scam_df = cat_df[cat_df["scam_category"] != "None"]

    if not cat_scam_df.empty:
        # 3.4 — Add formatted amount labels
        cat_scam_df = cat_scam_df.copy()
        cat_scam_df["label_text"] = cat_scam_df["total_amount"].apply(
            lambda x: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K"
        )
        cat_scam_df["hover_text"] = cat_scam_df.apply(
            lambda r: f"<b>{r['scam_category']}</b><br>Volume: {r['label_text']}<br>Txns: {r['txn_count']:,}<br>Avg Risk: {r['avg_risk']:.2f}",
            axis=1
        )
        # Legend label includes amount so user can read without hovering
        cat_scam_df["legend_label"] = cat_scam_df.apply(
            lambda r: f"{r['scam_category']}  ({r['label_text']})", axis=1
        )

        # Pull all slices slightly to force connector lines
        pull_vals = [0.08] * len(cat_scam_df)

        fig_pie = go.Figure(go.Pie(
            labels=cat_scam_df["legend_label"],
            values=cat_scam_df["total_amount"],
            hole=0.45,
            hovertext=cat_scam_df["hover_text"],
            hoverinfo="text",
            text=cat_scam_df["label_text"],
            # Add spaces before/after text to push the bounding box outward, forcing a line
            texttemplate=" %{text} ",
            textposition="outside",
            textfont=dict(size=12, color="#CBD5E1"),
            pull=pull_vals,
            rotation=0, # Reset rotation so the big slice is anchored naturally
            direction="clockwise",
            marker=dict(
                colors=px.colors.sequential.Sunsetdark[:len(cat_scam_df)],
                line=dict(color="rgba(0,0,0,0.3)", width=1)
            )
        ))
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=150, r=60, t=40, b=40),
            height=460,
            uniformtext=dict(minsize=10, mode=False),
            legend=dict(
                orientation="v", x=-0.1, xanchor="right", y=0.5, yanchor="middle",
                font=dict(size=11, color="#CBD5E1"),
                bgcolor="rgba(0,0,0,0)"
            )
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No fraud classifications available.")

with loc_col:
    st.subheader(t("geographic_risk"))
    geo_df = get_geographical_risk()

    # Country code → ISO-3 mapping for choropleth
    iso3_map = {
        "TH": "THA", "SG": "SGP", "KH": "KHM", "MM": "MMR",
        "HK": "HKG", "IN": "IND", "ID": "IDN", "CN": "CHN",
        "JP": "JPN", "AU": "AUS", "US": "USA"
    }
    lat_lon = {
        "TH": (13.7, 100.5), "SG": (1.35, 103.82), "KH": (11.55, 104.92),
        "MM": (16.87, 96.19), "HK": (22.32, 114.17), "IN": (20.59, 78.96),
        "ID": (-0.79, 113.92), "CN": (35.86, 104.2), "JP": (36.2, 138.25),
        "AU": (-25.27, 133.78), "US": (37.09, -95.71)
    }

    if not geo_df.empty:
        geo_df = geo_df.copy()
        geo_df["lat"] = geo_df["location"].map(lambda c: lat_lon.get(c, (0, 0))[0])
        geo_df["lon"] = geo_df["location"].map(lambda c: lat_lon.get(c, (0, 0))[1])
        geo_df["iso3"] = geo_df["location"].map(iso3_map)

        def fmt_amt(x):
            if x >= 1e9: return f"{x/1e9:.1f}B"
            if x >= 1e6: return f"{x/1e6:.1f}M"
            return f"{x/1e3:.0f}K"

        geo_df["hover"] = geo_df.apply(
            lambda r: f"<b>{r['location']}</b><br>Volume: ${fmt_amt(r['total_amount'])}<br>Txns: {r['txn_count']:,}<br>Avg Risk: {r['avg_risk_score']:.2f}",
            axis=1
        )

        fig_map = px.scatter_geo(
            geo_df,
            lat="lat", lon="lon",
            size="total_amount",
            color="avg_risk_score",
            color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"],
            range_color=[0, 1],
            hover_name="location",
            custom_data=["hover"],
            size_max=50,
            projection="natural earth"
        )
        fig_map.update_traces(
            hovertemplate="%{customdata[0]}<extra></extra>",
            marker=dict(line=dict(width=1, color="#0E1117"))
        )
        fig_map.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            geo=dict(
                bgcolor="rgba(14,17,23,0.9)",
                landcolor="rgba(30,41,59,0.8)",
                oceancolor="rgba(14,17,23,0.6)",
                showocean=True,
                showland=True,
                showcountries=True,
                countrycolor="rgba(255,255,255,0.1)",
                showframe=False,
                coastlinecolor="rgba(255,255,255,0.15)"
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            height=420,
            coloraxis_colorbar=dict(
                title=dict(text="Avg Risk" if lang == "EN" else "ความเสี่ยงเฉลี่ย", font=dict(color="#94A3B8")),
                tickfont=dict(color="#94A3B8")
            )
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No geographic transaction data available.")

# ---------------------------------------------------------
# Scatter + Density Contour (3.2) + Merchant Table
# ---------------------------------------------------------
st.markdown("---")
st.subheader(t("risk_profiling_title"))
risk_col, table_col = st.columns([1, 1])

conn = get_duckdb_connection()

if conn:
    with risk_col:
        st.markdown(f"**{t('tx_val_vs_risk')}**")
        try:
            scatter_df = conn.query("""
                SELECT amount, risk_score, scam_category, status
                FROM transactions
                WHERE risk_score >= 0.3
                USING SAMPLE 1000
            """).to_df()

            if not scatter_df.empty:
                fig_scatter = px.scatter(
                    scatter_df,
                    x="risk_score", y="amount",
                    color="status",
                    size="amount",
                    hover_data=["scam_category"],
                    color_discrete_map={"Flagged": "#EF4444", "Pending": "#F59E0B", "Cleared": "#10B981"},
                    labels={
                        "risk_score": "Risk Score (0.0-1.0)" if lang == "EN" else "คะแนนความเสี่ยง (0.0-1.0)", 
                        "amount": "Transaction Amount ($)" if lang == "EN" else "มูลค่าธุรกรรม ($)"
                    }
                )
                # 3.2 — Add density contour overlay
                fig_scatter.add_trace(go.Histogram2dContour(
                    x=scatter_df["risk_score"],
                    y=scatter_df["amount"],
                    colorscale=[[0, "rgba(99,102,241,0)"], [1, "rgba(99,102,241,0.35)"]],
                    showscale=False,
                    ncontours=8,
                    contours=dict(showlabels=False),
                    line=dict(width=0.5, color="rgba(99,102,241,0.4)"),
                    name="Density" if lang == "EN" else "ความหนาแน่น",
                    hoverinfo="skip"
                ))
                fig_scatter.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=10, b=10), height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Not enough data for scatter plot.")
        except Exception as e:
            st.warning(f"Scatter plot unavailable: {e}")

    with table_col:
        st.markdown(f"**{t('top_suspicious_merchants')}**")
        try:
            mule_df = conn.query("""
                SELECT
                    receiver_id,
                    COUNT(*) as txn_count,
                    SUM(amount) as total_volume,
                    AVG(risk_score) as avg_risk
                FROM transactions
                WHERE risk_score >= 0.7
                GROUP BY receiver_id
                HAVING COUNT(*) > 1
                ORDER BY avg_risk DESC
                LIMIT 8
            """).to_df()

            if not mule_df.empty:
                mule_df = mule_df.rename(columns={
                    "receiver_id": "Merchant / Receiver ID" if lang == "EN" else "ID ผู้รับ / ร้านค้า",
                    "txn_count": "Total Txns" if lang == "EN" else "จำนวนครั้ง",
                    "total_volume": "Total Volume ($)" if lang == "EN" else "ยอดเงินรวม ($)",
                    "avg_risk": "Avg Risk" if lang == "EN" else "ความเสี่ยงเฉลี่ย"
                })
                rank_col_name = "Rank" if lang == "EN" else "อันดับ"
                mule_df.insert(0, rank_col_name, range(1, len(mule_df) + 1))
                mule_df["Total Volume ($)" if lang == "EN" else "ยอดเงินรวม ($)"] = mule_df["Total Volume ($)" if lang == "EN" else "ยอดเงินรวม ($)"].apply(lambda x: f"${x:,.2f}")
                mule_df["Avg Risk" if lang == "EN" else "ความเสี่ยงเฉลี่ย"] = mule_df["Avg Risk" if lang == "EN" else "ความเสี่ยงเฉลี่ย"].apply(lambda x: f"{x:.2f}")

                table_html = mule_df.to_html(classes="custom-table", index=False)
                html_str = f"""<style>
.custom-table {{width:100%;border-collapse:collapse;color:#E2E8F0;font-size:0.95rem;text-align:left;}}
.custom-table thead th {{background-color:rgba(30,41,59,0.8);color:#94A3B8;text-transform:uppercase;font-size:0.8rem;padding:12px 15px;border-bottom:1px solid rgba(255,255,255,0.1);}}
.custom-table tbody td {{padding:12px 15px;border-bottom:1px solid rgba(255,255,255,0.05);background-color:rgba(15,23,42,0.4);}}
.custom-table tbody tr:hover td {{background-color:rgba(30,41,59,0.6);}}
</style>
<div style="border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);box-shadow:0 4px 15px rgba(0,0,0,0.2);">
    {table_html}
</div>"""
                st.markdown(html_str, unsafe_allow_html=True)
            else:
                st.info("No high-risk accounts found.")
        except Exception as e:
            st.warning(f"Failed to load suspicious accounts: {e}")

st.markdown("<br><br>", unsafe_allow_html=True)

