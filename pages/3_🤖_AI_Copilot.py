import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
import math
import os
import re
from datetime import datetime

from utils.db import get_mongodb_client, save_audit_log, get_audit_logs
from utils.data_processing import (
    get_account_network_nodes,
    get_account_blacklist_profile,
    get_db,
    get_sankey_flow_data,
)
from utils.ai import get_api_key, is_ai_configured, query_gemma_model, get_gemma_model_list
from utils.styles import inject_global_styles
from utils.sidebar import render_global_sidebar
from utils.translation import t

# ---------------------------------------------------------
# Page Config
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Copilot | Financial Fraud Detection",
    page_icon="🤖",
    layout="wide"
)

conn = get_db()
inject_global_styles()

st.markdown(
    f"""
    <div class="panel-header">
        <h2 class="panel-title">{t("ai_copilot_title")}</h2>
        <p class="panel-desc">{t("ai_copilot_desc")}</p>
    </div>
    """,
    unsafe_allow_html=True
)

render_global_sidebar()

# ---------------------------------------------------------
# AI Credentials & Model Config
# ---------------------------------------------------------
st.subheader(f"🔑 {t('google_creds')}")
col_key, col_model = st.columns(2)
with col_key:
    api_key_input = st.text_input(t("google_api_key_label"), type="password", help=t("google_api_key_help"), key="global_api_key_input")
    if api_key_input:
        st.session_state["google_api_key"] = api_key_input
        st.success(t("api_key_updated"))

with col_model:
    gemma_models = get_gemma_model_list(api_key_input if api_key_input else st.session_state.get("google_api_key", ""))
    selected_model = st.selectbox(t("gemma_model_select"), gemma_models, index=0, key="global_model_select")
    st.session_state["selected_model"] = selected_model

st.write("---")

# ---------------------------------------------------------
# Transactions Explorer
# ---------------------------------------------------------
with st.expander(t("view_tx_data"), expanded=False):
    search_term = st.text_input(t("search_placeholder"), "", key="search_copilot_all_tx")
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = f"""
            SELECT transaction_id, sender_id, sender_name, receiver_id, receiver_name,
                   amount, timestamp, risk_score, status, scam_category, location
            FROM transactions 
            WHERE sender_id ILIKE '{search_pattern}' OR receiver_id ILIKE '{search_pattern}'
               OR sender_name ILIKE '{search_pattern}' OR receiver_name ILIKE '{search_pattern}'
            ORDER BY timestamp DESC LIMIT 5000
        """
    else:
        query = """
            SELECT transaction_id, sender_id, sender_name, receiver_id, receiver_name,
                   amount, timestamp, risk_score, status, scam_category, location
            FROM transactions 
            ORDER BY timestamp DESC LIMIT 5000
        """
        
    if conn is not None:
        try:
            df_all_tx = conn.execute(query).df()
            st.markdown(
                f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <h4 style="margin:0;">{t("found_matching_tx").format(count=len(df_all_tx))}</h4></div>""",
                unsafe_allow_html=True
            )
            st.dataframe(
                df_all_tx, use_container_width=True,
                column_config={
                    "amount":     st.column_config.NumberColumn("Amount",     format="$%.2f"),
                    "risk_score": st.column_config.NumberColumn("Risk Score", format="%.2f"),
                }
            )
        except Exception as e:
            st.error(f"Error loading transactions: {e}")

st.write("---")

# ---------------------------------------------------------
# Select Account Form
# ---------------------------------------------------------
st.write(f"### {t('send_to_copilot_desc')}")
col1, col2 = st.columns([3, 1])
with col1:
    escalate_account = st.text_input(t("account_id_input_placeholder"), key="escalate_acc_input")
with col2:
    st.write(""); st.write("")
    if st.button(t("btn_send_copilot"), use_container_width=True):
        if escalate_account:
            if conn is not None:
                try:
                    acc_txns = conn.query(f"SELECT * FROM transactions WHERE sender_id = '{escalate_account}' OR receiver_id = '{escalate_account}' ORDER BY timestamp DESC LIMIT 500").to_df()
                    if not acc_txns.empty:
                        st.session_state["selected_fraud_case"] = {
                            "account_id": escalate_account,
                            "transactions": acc_txns
                        }
                        st.success(t("msg_send_success").format(account=escalate_account))
                    else:
                        st.error(t("msg_send_error"))
                except Exception as e:
                    st.error(f"Database Error: {e}")
            else:
                st.error("No database connection available.")
        else:
            st.warning(t("msg_send_warning"))

st.write("---")
# ---------------------------------------------------------
# Step 1: Check Session State
# ---------------------------------------------------------
if "selected_fraud_case" not in st.session_state or not st.session_state["selected_fraud_case"]:
    st.info(t("warn_no_case_selected"))
    st.stop()

case_info        = st.session_state["selected_fraud_case"]
selected_account = case_info["account_id"]
tx_history       = case_info["transactions"]



# ---------------------------------------------------------
# Send Data to AI Copilot
# ---------------------------------------------------------
selected_model = st.session_state.get("selected_model", "gemma-4-26b-a4b-it")

# ---------------------------------------------------------
# Case Header & Blacklist
# ---------------------------------------------------------
col_title, col_brief = st.columns([2, 1])
with col_title:
    st.write(f"### {t('investigating_file').format(account=selected_account)}")
with col_brief:
    if not tx_history.empty:
        max_risk = tx_history["risk_score"].max()
        st.write(f"**Max Risk:** `{max_risk * 100:.1f}%` | **Txns:** `{len(tx_history)}`")

blacklist_profile = get_account_blacklist_profile(selected_account)
if blacklist_profile:
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown(
            f"""
            <div class="blacklist-card">
                <span style="color:#EF4444;font-weight:800;font-size:0.85rem;text-transform:uppercase;">
                    {t("blacklist_status").format(status=blacklist_profile['status'])}
                </span>
                <div style="font-size:1.1rem;font-weight:700;color:#F8FAFC;margin-top:5px;">
                    {t("account_label").format(account_id=blacklist_profile['account_id'])}
                </div>
                <div style="margin-top:8px;color:#E2E8F0;font-size:0.9rem;">
                    <b>{t("reason_label")}</b> {blacklist_profile['reason']}<br>
                    <b>{t("reported_label")}</b> {blacklist_profile['reported_date']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_right:
        st.markdown(
            f"""
            <div class="blacklist-card" style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);">
                <span style="color:#F59E0B;font-weight:800;font-size:0.85rem;text-transform:uppercase;">
                    {t("network_credentials_title")}
                </span>
                <div style="margin-top:8px;color:#E2E8F0;font-size:0.9rem;">
                    💾 <b>{t("device_id_label")}</b>
                    <code style="background:#1E293B;padding:2px 6px;border-radius:4px;color:#F8FAFC;">
                        {blacklist_profile['device_id']}
                    </code><br>
                    🌐 <b>{t("ip_address_label")}</b>
                    <code style="background:#1E293B;padding:2px 6px;border-radius:4px;color:#F8FAFC;">
                        {blacklist_profile['ip_address']}
                    </code>
                </div>
                <div style="margin-top:8px;font-size:0.75rem;color:#94A3B8;">
                    {t("fetched_realtime_mongodb")}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------------------------------
# Step 2: Visualization Panel — Network + Sankey + Table
# ---------------------------------------------------------
st.write("---")
left_panel, right_panel = st.columns([1, 1])

with left_panel:
    st.write(f"#### {t('counterparty_network')}")
    network_df = get_account_network_nodes(selected_account)

    if not network_df.empty:
        nodes = list(set(network_df["sender_id"].tolist() + network_df["receiver_id"].tolist()))
        if selected_account in nodes:
            # Use networkx for better layout
            G_net = nx.DiGraph()
            for _, row in network_df.iterrows():
                G_net.add_edge(row["sender_id"], row["receiver_id"],
                               weight=float(row["amount"]))

            pos_net = nx.spring_layout(G_net, seed=42, k=2.0)
            # Ensure selected_account is at center
            if selected_account in pos_net:
                pos_net[selected_account] = (0.0, 0.0)

            fig_net = go.Figure()

            for u, v in G_net.edges():
                x0, y0 = pos_net.get(u, (0, 0))
                x1, y1 = pos_net.get(v, (0, 0))
                fig_net.add_trace(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None], mode="lines",
                    line=dict(width=1.5, color="rgba(168,85,247,0.35)"),
                    hoverinfo="none", showlegend=False
                ))
                fig_net.add_annotation(
                    ax=x0, ay=y0, x=x1, y=y1,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1,
                    arrowwidth=1.2, arrowcolor="rgba(168,85,247,0.5)"
                )

            node_colors = []
            node_sizes  = []
            for n in nodes:
                if n == selected_account:
                    node_colors.append("#A855F7"); node_sizes.append(28)
                elif "SUS" in n:
                    node_colors.append("#EF4444"); node_sizes.append(20)
                elif "MULE" in n:
                    node_colors.append("#F59E0B"); node_sizes.append(20)
                else:
                    node_colors.append("#3B82F6"); node_sizes.append(16)

            fig_net.add_trace(go.Scatter(
                x=[pos_net.get(n, (0,0))[0] for n in nodes],
                y=[pos_net.get(n, (0,0))[1] for n in nodes],
                mode="markers+text",
                marker=dict(size=node_sizes, color=node_colors,
                            line=dict(width=2, color="#FFFFFF")),
                text=[n[:14] for n in nodes],
                textposition="top center",
                textfont=dict(size=8, color="#F8FAFC"),
                hovertext=[f"{t('hover_account')}: {n}" for n in nodes],
                hoverinfo="text", name="Entities"
            ))

            fig_net.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=280, margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_net, use_container_width=True)
        else:
            st.info(t("no_connections"))
    else:
        st.info(t("no_network_data"))

# 2.5 — Sankey Diagram (Money Flow)
with right_panel:
    st.write(f"#### {t('money_flow_sankey')}")
    labels, sources, targets, values, link_colors = get_sankey_flow_data(selected_account)

    if labels and sources:
        # Color nodes: selected = purple, others = blue
        node_colors_sankey = [
            "#A855F7" if lbl == selected_account else "#3B82F6"
            for lbl in labels
        ]
        fig_sankey = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(
                pad=12, thickness=18,
                line=dict(color="rgba(255,255,255,0.1)", width=0.5),
                label=[lbl[:20] for lbl in labels],
                color=node_colors_sankey,
                hovertemplate="%{label}<extra></extra>"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate="Flow: $%{value:,.0f}<extra></extra>"
            )
        ))
        fig_sankey.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E2E8F0", size=10),
            height=280,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_sankey, use_container_width=True)
        st.caption(t("sankey_caption"))
    else:
        st.info(t("no_sankey_data"))



# ---------------------------------------------------------
# Step 3: AI Audit — using utils/ai.py (4.2 refactor)
# ---------------------------------------------------------
st.write("---")
st.write(f"### {t('explainable_ai_audit').replace('Gemma AI', selected_model).replace('Gemma Model', selected_model)}")

# Build transaction context string (shared between tabs)
# Use 1-hop network data (direct transactions only) to prevent AI hallucination
extended_tx_df = get_account_network_nodes(selected_account, max_depth=1)
tx_records     = extended_tx_df.to_dict(orient="records")
tx_context_str = ""
for r in tx_records[:50]: # Limit to 50 direct transactions
    tx_context_str += (
        f"- TxID: {r.get('transaction_id', 'N/A')} | "
        f"Sender: {r['sender_id']} ({r.get('sender_name', '')}) -> "
        f"Receiver: {r['receiver_id']} ({r.get('receiver_name', '')}) | "
        f"Amount: ${r['amount']:,} | Risk: {r['risk_score']} | "
        f"Status: {r.get('status', 'N/A')} | Category: {r.get('scam_category', 'None')} | Location: {r.get('location', 'N/A')}\n"
    )

tab_sar, tab_chat = st.tabs([t("tab_sar"), t("tab_chat")])

with tab_sar:
    if st.session_state.get("language", "TH") == "TH":
        sar_system = (
            "You are an expert Financial Intelligence Unit (FIU) Lead Investigator and Forensic Auditor. "
            "Your role is to analyze transaction logs to detect scams, money laundering, and mule account networks. "
            "Write a DETAILED Suspicious Activity Report (SAR) in Thai using a highly professional and structured tone. "
            "CRITICAL: The report MUST be detailed, covering at least 3 comprehensive paragraphs and bullet points. "
            "Output ONLY the final report. No thinking steps or reasoning."
        )
        sar_prompt = f"""โปรดวิเคราะห์พฤติกรรมการโอนเงินของบัญชีนี้: **{selected_account}**
รายการธุรกรรมที่เกี่ยวข้อง (จาก DuckDB query):

{tx_context_str}

สร้าง Suspicious Activity Report (SAR) เป็นภาษาไทย ครอบคลุม:
1. ความเสี่ยงโดยรวมและประเภทพฤติกรรม (บัญชีม้า / เจ้าของบัญชี / Organizer)
2. ข้อพิรุธหลักที่พบ (การโอนถี่ผิดปกติ, cross-border สู่ประเทศเสี่ยง, circular loops)
3. ข้อเสนอแนะ 3 ขั้นตอน (freeze, KYC, FIU report)
"""
    else:
        sar_system = (
            "You are an expert Financial Intelligence Unit (FIU) Lead Investigator and Forensic Auditor. "
            "Your role is to analyze transaction logs to detect scams, money laundering, and mule account networks. "
            "Write a DETAILED Suspicious Activity Report (SAR) in English using a highly professional and structured tone. "
            "CRITICAL: The report MUST be detailed, covering at least 3 comprehensive paragraphs and bullet points. "
            "Output ONLY the final report. No thinking steps or reasoning."
        )
        sar_prompt = f"""Please analyze the transaction behavior of this account: **{selected_account}**
Related transactions (from DuckDB query):

{tx_context_str}

Generate a Suspicious Activity Report (SAR) in English covering:
1. Overall risk and behavior type (Mule Account / Account Owner / Organizer)
2. Key suspicious activities found (abnormally high velocity, cross-border transfers to high-risk countries, circular loops)
3. 3-step recommendation (freeze, KYC, FIU report)
"""

    if st.button(t("btn_run_ai_analysis"), use_container_width=True):
        if is_ai_configured():
            # 7.2 — AI Streaming using st.write_stream
            st.write(f"#### {t('generated_sar_title')}")

            report_box = st.empty()
            accumulated = ""

            with st.spinner(t("spinner_ai_analysis").replace("Gemma AI", selected_model).replace("Gemma Model", selected_model)):
                raw = query_gemma_model(sar_prompt, sar_system, selected_model)
                # Clean thinking tags if model outputs them
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                # Escape HTML brackets to prevent invisible text from <Account_ID>
                raw = raw.replace("<", "&lt;").replace(">", "&gt;")

            # Simulate streaming display word-by-word for UX
            words = raw.split(" ")
            for i, word in enumerate(words):
                accumulated += word + " "
                if i % 8 == 0:  # update every 8 words to avoid too many rerenders
                    report_box.markdown(
                        f"""<div class="sar-report-box">{accumulated}</div>""",
                        unsafe_allow_html=True
                    )
            report_box.markdown(
                f"""<div class="sar-report-box">{accumulated}</div>""",
                unsafe_allow_html=True
            )

            st.session_state["generated_sar_text"]  = accumulated.strip()
            st.session_state["report_account_id"]   = selected_account
            st.rerun()
        else:
            # Demo fallback
            from utils.ai import _generate_demo_response
            report_text = _generate_demo_response(sar_prompt, t("demo_mode_warning"))
            st.session_state["generated_sar_text"] = report_text
            st.session_state["report_account_id"]  = selected_account
            st.rerun()

    # Show previously generated report
    if (
        "generated_sar_text" in st.session_state
        and st.session_state.get("report_account_id") == selected_account
    ):
        st.write(f"#### {t('generated_sar_title')}")
        st.markdown(f"""<div class="sar-report-box">{st.session_state['generated_sar_text']}</div>""", unsafe_allow_html=True)
        if st.button(t("btn_save_report_mongodb"), use_container_width=True):
            success = save_audit_log(
                account_id=selected_account,
                query="Automated SAR",
                report_text=st.session_state["generated_sar_text"]
            )
            if success:
                st.success(t("msg_save_report_success"))
            else:
                st.error(t("msg_save_report_error"))

    st.write("---")
    past_logs = get_audit_logs(selected_account)
    with st.expander(t("past_investigations").format(count=len(past_logs))):
        if past_logs:
            for pl in past_logs:
                st.markdown(
                    f"""
                    <div class="audit-log-card">
                        <div style="display:flex;justify-content:space-between;align-items:center;
                                    border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:5px;margin-bottom:10px;">
                            <span style="color:#A855F7;font-weight:bold;">🔍 {pl['query']}</span>
                            <span style="font-size:0.8rem;color:#94A3B8;">🕒 {pl['timestamp']}</span>
                        </div>
                        <div style="font-size:0.9rem;line-height:1.5;color:#E2E8F0;white-space:pre-wrap;">
                            {pl['report']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info(t("no_prior_investigations"))

with tab_chat:
    st.write(f"#### {t('ai_database_agent')}")
    st.write(t("chat_description"))

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if st.session_state.get("chat_account_id") != selected_account:
        st.session_state.chat_messages = []
        st.session_state.chat_account_id = selected_account

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(t("chat_placeholder")):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if st.session_state.get("language", "TH") == "TH":
            chat_system = (
                "You are a Data-Centric AI Database Agent. "
                "Analyze the provided transaction records to answer the user's questions accurately. "
                "Write responses in Thai using a professional and helpful tone. "
                "CRITICAL: You must output your response in strict JSON format. Do not write any markdown outside the JSON block. "
                "Use the following structure:\n"
                "{\n"
                '  "reasoning": "your internal step-by-step thinking (in English or Thai)",\n'
                '  "final_answer": "your complete final answer directed to the user in Thai"\n'
                "}"
            )
        else:
            chat_system = (
                "You are a Data-Centric AI Database Agent. "
                "Analyze the provided transaction records to answer the user's questions accurately. "
                "Write responses in English using a professional and helpful tone. "
                "CRITICAL: You must output your response in strict JSON format. Do not write any markdown outside the JSON block. "
                "Use the following structure:\n"
                "{\n"
                '  "reasoning": "your internal step-by-step thinking (in English)",\n'
                '  "final_answer": "your complete final answer directed to the user in English"\n'
                "}"
            )

        chat_prompt = f"""Transaction Records for Account: {selected_account}
{tx_context_str}

User Question: {prompt}
"""

        with st.chat_message("assistant"):
            if not is_ai_configured():
                response_text = t("chatbot_demo_msg")
                st.markdown(response_text)
            else:
                with st.spinner(t("spinner_analyzing")):
                    raw_response = query_gemma_model(chat_prompt, chat_system, selected_model)
                    
                    # Try to parse JSON to cleanly extract final answer
                    import json
                    import re
                    
                    try:
                        # Find the first { and last } to handle cases where LLM wraps JSON in markdown block ```json ... ```
                        json_str = raw_response[raw_response.find("{") : raw_response.rfind("}") + 1]
                        parsed = json.loads(json_str)
                        response_text = parsed.get("final_answer", raw_response)
                    except Exception:
                        # Fallback if JSON parsing fails completely
                        response_text = raw_response.replace("```json", "").replace("```", "").strip()
                        
                    if "Available Models on this API Key" in response_text:
                        response_text = t("invalid_api_key_err")
                        
                    st.markdown(response_text)

        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

    if len(st.session_state.chat_messages) > 0:
        st.write("---")
        if st.button(t("btn_save_chat"), use_container_width=True, key="save_chat"):
            transcript = "\n\n".join([
                f"**{'User' if m['role'] == 'user' else 'AI Agent'}**: {m['content']}"
                for m in st.session_state.chat_messages
            ])
            success = save_audit_log(
                account_id=selected_account,
                query="Interactive Chatbot Session",
                report_text=transcript
            )
            if success:
                st.success(t("msg_save_chat_success"))
            else:
                st.error(t("msg_save_chat_error"))
