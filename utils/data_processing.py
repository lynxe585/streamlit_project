import streamlit as st
import pandas as pd
import duckdb
from utils.db import get_duckdb_connection, initialize_database

def get_db():
    """ Helper to ensure DB is initialized and returned """
    return initialize_database()

def get_overall_metrics():
    """
    Get summary statistics for the home page.
    Uses DuckDB to perform aggregations.
    """
    conn = get_db()
    query = """
        SELECT 
            COUNT(*) as total_txns,
            SUM(amount) as total_volume,
            AVG(risk_score) as avg_risk,
            COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END) as high_risk_txns,
            COUNT(CASE WHEN status = 'Flagged' THEN 1 END) as flagged_txns,
            SUM(CASE WHEN risk_score >= 0.7 THEN amount ELSE 0 END) as high_risk_volume,
            SUM(CASE WHEN status = 'Flagged' THEN amount ELSE 0 END) as value_saved,
            SUM(CASE WHEN scam_category != 'None' AND status = 'Cleared' THEN amount ELSE 0 END) as actual_loss
        FROM transactions
    """
    return conn.query(query).to_df()

def get_scam_category_distribution():
    """
    Get volume and count distribution by scam category.
    """
    conn = get_db()
    query = """
        SELECT 
            scam_category,
            COUNT(*) as txn_count,
            SUM(amount) as total_amount,
            AVG(risk_score) as avg_risk
        FROM transactions
        GROUP BY scam_category
        ORDER BY total_amount DESC
    """
    return conn.query(query).to_df()

def get_daily_transaction_trends(start_date=None, end_date=None):
    """
    Get daily transaction counts and amounts.
    """
    conn = get_db()
    
    where_clause = ""
    params = []
    if start_date and end_date:
        where_clause = "WHERE CAST(timestamp AS DATE) BETWEEN ? AND ?"
        params.extend([start_date, end_date])
        
    query = f"""
        SELECT 
            CAST(timestamp AS DATE) as txn_date,
            COUNT(*) as txn_count,
            SUM(amount) as total_amount,
            SUM(CASE WHEN risk_score >= 0.7 THEN amount ELSE 0 END) as high_risk_amount,
            COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END) as high_risk_count
        FROM transactions
        {where_clause}
        GROUP BY txn_date
        ORDER BY txn_date ASC
    """
    if params:
        return conn.execute(query, params).df()
    return conn.query(query).to_df()

def get_geographical_risk():
    """
    Aggregate risk scores and volumes by country location.
    """
    conn = get_db()
    query = """
        SELECT 
            location,
            COUNT(*) as txn_count,
            SUM(amount) as total_amount,
            AVG(risk_score) as avg_risk_score,
            COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END) as high_risk_count
        FROM transactions
        GROUP BY location
        ORDER BY total_amount DESC
    """
    return conn.query(query).to_df()

def get_data_source_distribution():
    """
    Get distribution of records by data source (Snowflake/MongoDB/Local).
    """
    conn = get_db()
    # Check if data_source column exists
    try:
        query = """
            SELECT 
                data_source,
                COUNT(*) as record_count,
                SUM(amount) as total_amount,
                AVG(risk_score) as avg_risk,
                COUNT(CASE WHEN status = 'Flagged' THEN 1 END) as flagged_count
            FROM transactions
            GROUP BY data_source
            ORDER BY record_count DESC
        """
        return conn.query(query).to_df()
    except Exception:
        return pd.DataFrame()

def get_high_risk_transactions(limit=10, min_risk=0.7):
    """
    Retrieve top flagged or highest-risk transactions.
    Joins the blacklist table for enrichment.
    """
    conn = get_db()
    query = f"""
        SELECT 
            t.transaction_id,
            t.sender_id,
            t.sender_name,
            t.receiver_id,
            t.receiver_name,
            t.amount,
            t.timestamp,
            t.risk_score,
            t.status,
            t.scam_category,
            t.location,
            bs.device_id as sender_device,
            bs.ip_address as sender_ip,
            bs.status as sender_blacklist_status,
            br.device_id as receiver_device,
            br.ip_address as receiver_ip,
            br.status as receiver_blacklist_status
        FROM transactions t
        LEFT JOIN blacklist bs ON t.sender_id = bs.account_id
        LEFT JOIN blacklist br ON t.receiver_id = br.account_id
        WHERE t.risk_score >= ?
        ORDER BY t.risk_score DESC, t.amount DESC
        LIMIT ?
    """
    return conn.execute(query, [min_risk, limit]).df()

def search_account_transactions(account_id):
    """
    Retrieve all transactions associated with a specific account.
    """
    conn = get_db()
    query = f"""
        SELECT 
            t.transaction_id,
            t.sender_id,
            t.sender_name,
            t.receiver_id,
            t.receiver_name,
            t.amount,
            t.timestamp,
            t.risk_score,
            t.status,
            t.scam_category,
            t.location,
            bs.device_id as sender_device,
            bs.ip_address as sender_ip,
            br.device_id as receiver_device,
            br.ip_address as receiver_ip
        FROM transactions t
        LEFT JOIN blacklist bs ON t.sender_id = bs.account_id
        LEFT JOIN blacklist br ON t.receiver_id = br.account_id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.timestamp DESC
    """
    return conn.execute(query, [account_id, account_id]).df()

def get_account_blacklist_profile(account_id):
    """
    Fetch blacklist details for a specific account.
    """
    conn = get_db()
    query = f"""
        SELECT 
            account_id,
            device_id,
            ip_address,
            status,
            reason,
            reported_date
        FROM blacklist
        WHERE account_id = ?
    """
    df = conn.execute(query, [account_id]).df()
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def get_shared_merchant_network(where_sql=""):
    """
    Find merchants that have multiple flagged/high-risk senders transacting with them.
    This reveals potential fraud rings using the same merchant as a drop point.
    Returns: (df_merchants, df_edges)
      - df_merchants: merchants with >=2 unique flagged senders
      - df_edges: individual edges (sender -> merchant) for graph visualization
    """
    conn = get_db()
    
    base_query = f"(SELECT * FROM transactions {where_sql})" if where_sql else "transactions"
    
    # Find risky merchants: those receiving from multiple flagged senders
    merchant_query = f"""
        SELECT 
            receiver_id AS merchant_id,
            receiver_name AS merchant_name,
            COUNT(DISTINCT sender_id) AS unique_flagged_senders,
            COUNT(*) AS fraud_txn_count,
            SUM(amount) AS total_fraud_volume,
            AVG(risk_score) AS avg_risk
        FROM {base_query}
        WHERE risk_score >= 0.7
        GROUP BY receiver_id, receiver_name
        HAVING COUNT(DISTINCT sender_id) >= 2
        ORDER BY unique_flagged_senders DESC
        LIMIT 15
    """
    
    df_merchants = conn.query(merchant_query).to_df()
    
    if df_merchants.empty:
        return df_merchants, pd.DataFrame()
    
    # Get the edges (sender -> merchant) for the top risky merchants
    merchant_ids = df_merchants['merchant_id'].tolist()
    merchant_list = ", ".join([f"'{m}'" for m in merchant_ids])
    
    edges_query = f"""
        SELECT 
            sender_id,
            sender_name,
            receiver_id AS merchant_id,
            receiver_name AS merchant_name,
            SUM(amount) AS total_amount,
            COUNT(*) AS txn_count,
            MAX(risk_score) AS max_risk,
            MAX(timestamp) AS last_txn_time
        FROM {base_query}
        WHERE receiver_id IN ({merchant_list})
          AND risk_score >= 0.7
        GROUP BY sender_id, sender_name, receiver_id, receiver_name
        ORDER BY total_amount DESC
    """
    
    df_edges = conn.query(edges_query).to_df()
    
    return df_merchants, df_edges


def get_risk_pattern_analysis(where_sql=""):
    """
    Analyze transaction risk patterns:
    1. Amount distribution by risk status (Flagged vs Cleared)
    2. Temporal fraud patterns (fraud rate by time period)
    Returns: (df_risk_dist, df_temporal)
    """
    conn = get_db()
    
    base_query = f"(SELECT * FROM transactions {where_sql})" if where_sql else "transactions"
    
    # 1. Risk distribution: amount statistics per status
    risk_dist_query = f"""
        SELECT 
            status,
            COUNT(*) AS txn_count,
            AVG(amount) AS avg_amount,
            MEDIAN(amount) AS median_amount,
            MIN(amount) AS min_amount,
            MAX(amount) AS max_amount,
            SUM(amount) AS total_volume,
            AVG(risk_score) AS avg_risk_score
        FROM {base_query}
        GROUP BY status
        ORDER BY avg_risk_score DESC
    """
    
    df_risk_dist = conn.query(risk_dist_query).to_df()
    
    # 2. Scam Category Analysis: risk and volume by category
    category_query = f"""
        SELECT 
            scam_category,
            COUNT(*) AS total_txns,
            SUM(amount) AS total_volume,
            AVG(amount) AS avg_amount,
            AVG(risk_score) AS avg_risk,
            MAX(risk_score) AS max_risk
        FROM {base_query}
        WHERE scam_category != 'None' AND scam_category IS NOT NULL
        GROUP BY scam_category
        ORDER BY total_volume DESC
    """
    
    df_category = conn.query(category_query).to_df()
    
    return df_risk_dist, df_category

def get_account_network_nodes(account_id, max_depth=1):
    """
    Query all connected transaction paths for a specific node.
    """
    conn = get_db()
    if max_depth == 1:
        query = """
            SELECT *
            FROM transactions
            WHERE sender_id = ? OR receiver_id = ?
            ORDER BY amount DESC
        """
        return conn.execute(query, [account_id, account_id]).df()
    else:
        # Get 2-hop transactions
        query = """
            WITH Hop1 AS (
                SELECT sender_id AS acc FROM transactions WHERE receiver_id = ?
                UNION
                SELECT receiver_id AS acc FROM transactions WHERE sender_id = ?
                UNION
                SELECT CAST(? AS VARCHAR) AS acc
            )
            SELECT * FROM transactions
            WHERE sender_id IN (SELECT acc FROM Hop1)
               OR receiver_id IN (SELECT acc FROM Hop1)
            ORDER BY amount DESC
            LIMIT 500
        """
        return conn.execute(query, [account_id, account_id, account_id]).df()


# ---------------------------------------------------------
# New: Daily Transaction Trend (for 2.1 & Date Range filter)
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_daily_transaction_trends_ranged(start_date=None, end_date=None):
    """
    Returns daily transaction counts, total amounts and high-risk amounts.
    Optionally filtered by a date range.
    """
    conn = get_db()
    if start_date and end_date:
        query = """
            SELECT
                CAST(timestamp AS DATE) AS txn_date,
                COUNT(*)                              AS txn_count,
                SUM(amount)                           AS total_amount,
                SUM(CASE WHEN risk_score >= 0.7 THEN amount ELSE 0 END) AS high_risk_amount,
                COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END)           AS high_risk_count
            FROM transactions
            WHERE CAST(timestamp AS DATE) BETWEEN ? AND ?
            GROUP BY txn_date
            ORDER BY txn_date ASC
        """
        return conn.execute(query, [str(start_date), str(end_date)]).df()
    else:
        query = """
            SELECT
                CAST(timestamp AS DATE) AS txn_date,
                COUNT(*)                              AS txn_count,
                SUM(amount)                           AS total_amount,
                SUM(CASE WHEN risk_score >= 0.7 THEN amount ELSE 0 END) AS high_risk_amount,
                COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END)           AS high_risk_count
            FROM transactions
            GROUP BY txn_date
            ORDER BY txn_date ASC
        """
        return conn.query(query).to_df()


# ---------------------------------------------------------
# New: Circular Loop Detection (for 2.2)
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def detect_circular_loops():
    """
    Detects potential circular money laundering loops using a 2-hop self-join.
    A loop: A -> B -> A (direct), or A -> B -> C -> A (3-hop via intermediate).
    Returns (df_loop_edges, df_loop_summary).
    """
    conn = get_db()

    # 2-hop loops: A -> B -> A
    two_hop_query = """
        SELECT
            t1.sender_id   AS node_a,
            t1.receiver_id AS node_b,
            t2.receiver_id AS node_c,
            t1.amount      AS amount_ab,
            t2.amount      AS amount_bc,
            t1.timestamp   AS time_ab,
            t2.timestamp   AS time_bc,
            t1.risk_score  AS risk_ab,
            t2.risk_score  AS risk_bc,
            'direct_loop'  AS loop_type
        FROM transactions t1
        JOIN transactions t2
          ON t1.receiver_id = t2.sender_id
         AND t2.receiver_id = t1.sender_id
         AND t1.transaction_id <> t2.transaction_id
        WHERE t1.risk_score >= 0.4 OR t2.risk_score >= 0.4
        LIMIT 200
    """

    # 3-hop loops: A -> B -> C -> A
    three_hop_query = """
        SELECT
            t1.sender_id   AS node_a,
            t1.receiver_id AS node_b,
            t2.receiver_id AS node_c,
            t1.amount      AS amount_ab,
            t2.amount      AS amount_bc,
            t1.timestamp   AS time_ab,
            t2.timestamp   AS time_bc,
            t1.risk_score  AS risk_ab,
            t2.risk_score  AS risk_bc,
            'three_hop'    AS loop_type
        FROM transactions t1
        JOIN transactions t2
          ON t1.receiver_id = t2.sender_id
         AND t1.sender_id <> t2.receiver_id
        JOIN transactions t3
          ON t2.receiver_id = t3.sender_id
         AND t3.receiver_id = t1.sender_id
        WHERE (t1.risk_score >= 0.5 OR t2.risk_score >= 0.5 OR t3.risk_score >= 0.5)
        LIMIT 200
    """

    try:
        df_two = conn.query(two_hop_query).to_df()
    except Exception:
        df_two = pd.DataFrame()

    try:
        df_three = conn.query(three_hop_query).to_df()
    except Exception:
        df_three = pd.DataFrame()

    df_loops = pd.concat([df_two, df_three], ignore_index=True)

    if df_loops.empty:
        return df_loops, pd.DataFrame()

    # Summary: unique nodes involved in loops
    loop_nodes = set(df_loops["node_a"].tolist() + df_loops["node_b"].tolist())
    if "node_c" in df_loops.columns:
        loop_nodes.update(df_loops["node_c"].dropna().tolist())

    summary_query = f"""
        SELECT
            sender_id,
            COUNT(*) AS out_txns,
            SUM(amount) AS total_out,
            AVG(risk_score) AS avg_risk
        FROM transactions
        WHERE sender_id IN ({','.join([f"'{n}'" for n in loop_nodes])})
        GROUP BY sender_id
        ORDER BY avg_risk DESC
    """
    try:
        df_summary = conn.query(summary_query).to_df()
    except Exception:
        df_summary = pd.DataFrame()

    return df_loops, df_summary


# ---------------------------------------------------------
# New: Velocity / Burst Detection (for 2.3)
# migrated from data_processor.py
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_suspicious_accounts_velocity(min_txns_per_day=5, top_n=20):
    """
    Returns accounts with burst transaction activity (>= min_txns_per_day in a single day).
    """
    conn = get_db()
    query = f"""
        SELECT
            sender_id,
            CAST(timestamp AS DATE) AS txn_date,
            COUNT(*)                AS transaction_count,
            SUM(amount)             AS total_amount,
            MAX(risk_score)         AS max_risk_score,
            COUNT(DISTINCT location) AS unique_locations
        FROM transactions
        GROUP BY sender_id, txn_date
        HAVING COUNT(*) >= {min_txns_per_day}
        ORDER BY transaction_count DESC, total_amount DESC
        LIMIT {top_n}
    """
    try:
        return conn.query(query).to_df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_hourly_velocity_heatmap():
    """
    Returns a pivot-ready DataFrame: rows=day-of-week, cols=hour, values=flagged txn count.
    """
    conn = get_db()
    query = """
        SELECT
            DAYOFWEEK(CAST(timestamp AS TIMESTAMP)) AS dow,
            HOUR(CAST(timestamp AS TIMESTAMP))      AS hour_of_day,
            COUNT(*) AS txn_count,
            COUNT(CASE WHEN risk_score >= 0.7 THEN 1 END) AS flagged_count,
            SUM(amount) AS total_amount
        FROM transactions
        GROUP BY dow, hour_of_day
        ORDER BY dow, hour_of_day
    """
    try:
        df = conn.query(query).to_df()
        # Map dow numbers to names (DuckDB: 0=Sunday)
        dow_map = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
        df["day_name"] = df["dow"].map(dow_map)
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------
# New: Sankey Diagram data (for 2.5)
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_sankey_flow_data(account_id, max_nodes=15):
    """
    Returns (labels, sources, targets, values, colors) for a Sankey diagram
    showing money flow through the selected account and its counterparts.
    """
    conn = get_db()
    query = """
        SELECT
            sender_id, sender_name,
            receiver_id, receiver_name,
            SUM(amount) AS total_amount,
            AVG(risk_score) AS avg_risk,
            COUNT(*) AS txn_count
        FROM transactions
        WHERE sender_id = ? OR receiver_id = ?
        GROUP BY sender_id, sender_name, receiver_id, receiver_name
        ORDER BY total_amount DESC
        LIMIT ?
    """
    try:
        df = conn.execute(query, [account_id, account_id, max_nodes * 2]).df()
    except Exception:
        return [], [], [], [], []

    if df.empty:
        return [], [], [], [], []

    # Build unique node list
    senders = df[["sender_id", "sender_name"]].rename(columns={"sender_id": "id", "sender_name": "label"})
    receivers = df[["receiver_id", "receiver_name"]].rename(columns={"receiver_id": "id", "receiver_name": "label"})
    nodes_df = pd.concat([senders, receivers]).drop_duplicates("id").reset_index(drop=True)
    node_index = {row["id"]: i for i, row in nodes_df.iterrows()}

    labels = nodes_df["label"].tolist()
    sources, targets, values, colors = [], [], [], []

    for _, row in df.iterrows():
        s_idx = node_index.get(row["sender_id"])
        t_idx = node_index.get(row["receiver_id"])
        if s_idx is None or t_idx is None:
            continue
        sources.append(s_idx)
        targets.append(t_idx)
        values.append(float(row["total_amount"]))
        risk = float(row["avg_risk"])
        if risk >= 0.7:
            colors.append("rgba(239, 68, 68, 0.6)")
        elif risk >= 0.4:
            colors.append("rgba(245, 158, 11, 0.5)")
        else:
            colors.append("rgba(59, 130, 246, 0.4)")

    return labels, sources, targets, values, colors
