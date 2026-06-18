import streamlit as st
import pandas as pd
import numpy as np
import duckdb
import os
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------
# Database Connection Functions (Cached with @st.cache_resource)
# ---------------------------------------------------------

@st.cache_resource
def get_snowflake_connection():
    """
    Establish a connection to Snowflake.
    Reads credentials from Streamlit secrets.
    Returns None if connection fails or credentials are not configured.
    """
    try:
        import snowflake.connector
        if "snowflake" in st.secrets:
            creds = st.secrets["snowflake"]
            conn_params = {
                "user": creds.get("user"),
                "password": creds.get("password"),
                "account": creds.get("account"),
                "database": creds.get("database", "FRAUD_DB"),
            }
            # Optional params
            if creds.get("warehouse"):
                conn_params["warehouse"] = creds.get("warehouse")
            if creds.get("role"):
                conn_params["role"] = creds.get("role")
            if creds.get("schema"):
                conn_params["schema"] = creds.get("schema")
                
            conn = snowflake.connector.connect(**conn_params)
            
            # Ensure warehouse is active
            cursor = conn.cursor()
            try:
                wh = creds.get("warehouse", "")
                if wh:
                    cursor.execute(f'USE WAREHOUSE "{wh}"')
            except Exception:
                # Try to find any available warehouse
                try:
                    cursor.execute("SHOW WAREHOUSES")
                    whs = cursor.fetchall()
                    if whs:
                        cursor.execute(f'USE WAREHOUSE "{whs[0][0]}"')
                except Exception:
                    pass
            cursor.close()
            return conn
    except Exception as e:
        st.session_state["_sf_error"] = str(e)
    return None

@st.cache_resource
def get_mongodb_client():
    """
    Establish a connection to MongoDB.
    Returns None if connection fails.
    """
    try:
        import pymongo
        uri = ""
        try:
            if "mongodb" in st.secrets:
                uri = st.secrets["mongodb"].get("uri", "")
        except Exception:
            pass
            
        if uri:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
            # Test connection
            client.admin.command('ping')
            return client
    except Exception as e:
        st.session_state["_mongo_error"] = str(e)
    return None

@st.cache_resource
def get_duckdb_connection():
    """
    Establish a connection to an in-memory DuckDB instance.
    """
    conn = duckdb.connect(database=":memory:", read_only=False)
    return conn

# ---------------------------------------------------------
# Snowflake Data Loading Functions
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def load_snowflake_synthetic_fraud():
    """
    Load SYNTHETIC_FRAUD table from Snowflake (FRAUD_DB.PUBLIC.SYNTHETIC_FRAUD).
    Schema: STEP, TYPE, BRANCH, AMOUNT, NAMEORIG, OLDBALANCEORG, NEWBALANCEORIG,
            NAMEDEST, OLDBALANCEDEST, NEWBALANCEDEST, UNUSUALLOGIN, ISFLAGGEDFRAUD,
            ACCT_TYPE, DATE_OF_TRANSACTION, TIME_OF_DAY, ISFRAUD
    Returns mapped DataFrame or None on failure.
    """
    conn = get_snowflake_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM FRAUD_DB.PUBLIC.SYNTHETIC_FRAUD LIMIT 10127")
        df = cursor.fetch_pandas_all()
        cursor.close()
        if df is not None and not df.empty:
            return _map_synthetic_fraud(df)
    except Exception as e:
        st.session_state["_sf_load_error_synthetic"] = str(e)
    return None

@st.cache_data(ttl=3600)
def load_snowflake_credit_card_fraud(limit=50000):
    """
    Load CREDIT_CARD_FRAUD table from Snowflake (FRAUD_DB.PUBLIC.CREDIT_CARD_FRAUD).
    Schema: STEP, TYPE, AMOUNT, NAMEORIG, OLDBALANCEORIG, NEWBALANCEORIG,
            NAMEDEST, OLDBALANCEDEST, NEWBALANCEDEST, ISFRAUD
    Limited to 50,000 rows from 6.3M total for performance.
    Returns mapped DataFrame or None on failure.
    """
    conn = get_snowflake_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM FRAUD_DB.PUBLIC.CREDIT_CARD_FRAUD LIMIT {limit}")
        df = cursor.fetch_pandas_all()
        cursor.close()
        if df is not None and not df.empty:
            return _map_credit_card_fraud(df)
    except Exception as e:
        st.session_state["_sf_load_error_cc"] = str(e)
    return None

# ---------------------------------------------------------
# MongoDB Data Loading Functions
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def load_mongodb_transactions(limit=10000):
    """
    Load Transactions from MongoDB (FraudDetectionDB.Transactions).
    Schema: transaction_id, amount, transaction_hour, merchant_category,
            foreign_transaction, location_mismatch, device_trust_score,
            velocity_last_24h, cardholder_age, is_fraud
    Returns mapped DataFrame or None on failure.
    """
    client = get_mongodb_client()
    if client is None:
        return None
    try:
        db = client["FraudDetectionDB"]
        col = db["Transactions"]
        cursor = col.find().limit(limit)
        df = pd.DataFrame(list(cursor))
        if not df.empty:
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])
            return _map_mongodb_transactions(df)
    except Exception as e:
        st.session_state["_mongo_load_error"] = str(e)
    return None

@st.cache_data(ttl=3600)
def load_mongodb_mock_transactions(limit=10000):
    """
    Load the explicitly seeded MockTransactions from MongoDB.
    Schema matches our standard P2P transaction schema.
    """
    client = get_mongodb_client()
    if client is None:
        return None
    try:
        db = client["FraudDetectionDB"]
        col = db["MockTransactions"]
        cursor = col.find().limit(limit)
        df = pd.DataFrame(list(cursor))
        if not df.empty:
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])
            # Convert timestamp to datetime if necessary
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
    except Exception as e:
        st.session_state["_mongo_load_error_mock"] = str(e)
    return None

@st.cache_data(ttl=600)
def load_blacklist_data():
    """
    Fetch blacklist data from MongoDB (fraud_detection_network.blacklist).
    Returns DataFrame with columns: account_id, device_id, ip_address, status, reason, reported_date
    """
    client = get_mongodb_client()
    if client:
        try:
            db = client["fraud_detection_network"]
            col = db["blacklist"]
            cursor = col.find()
            df = pd.DataFrame(list(cursor))
            if not df.empty:
                if "_id" in df.columns:
                    df = df.drop(columns=["_id"])
                return df
        except Exception:
            pass

    # Local fallback if MongoDB fails or is empty
    return pd.DataFrame(columns=["account_id", "device_id", "ip_address", "status", "reason", "reported_date"])

# ---------------------------------------------------------
# Column Mapping Functions (Snowflake -> App Schema)
# ---------------------------------------------------------

def _map_synthetic_fraud(df):
    """
    Maps Snowflake SYNTHETIC_FRAUD table to the unified app schema.
    Source columns: STEP, TYPE, BRANCH, AMOUNT, NAMEORIG, NAMEDEST,
                    UNUSUALLOGIN, ISFLAGGEDFRAUD, DATE_OF_TRANSACTION, TIME_OF_DAY, ISFRAUD
    """
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]

    mapped = pd.DataFrame()

    # Transaction ID
    if "UNNAMED:_0" in df.columns:
        mapped["transaction_id"] = "SF_SYN_" + df["UNNAMED:_0"].astype(str)
    elif "STEP" in df.columns:
        mapped["transaction_id"] = "SF_SYN_" + df.index.astype(str)
    else:
        mapped["transaction_id"] = ["SF_SYN_" + str(i) for i in range(len(df))]

    mapped["sender_id"] = df["NAMEORIG"]
    mapped["sender_name"] = df["NAMEORIG"]
    mapped["receiver_id"] = df["NAMEDEST"]
    mapped["receiver_name"] = df["NAMEDEST"]
    mapped["amount"] = df["AMOUNT"].astype(float)
    mapped["transaction_type"] = df["TYPE"]

    # Timestamp from DATE_OF_TRANSACTION + TIME_OF_DAY
    if "DATE_OF_TRANSACTION" in df.columns:
        time_map = {"morning": "09:00:00", "afternoon": "14:00:00", "night": "22:00:00"}
        if "TIME_OF_DAY" in df.columns:
            times = df["TIME_OF_DAY"].str.lower().str.strip().map(time_map).fillna("12:00:00")
            mapped["timestamp"] = pd.to_datetime(
                df["DATE_OF_TRANSACTION"].astype(str) + " " + times, 
                errors="coerce", format="mixed"
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            mapped["timestamp"] = pd.to_datetime(
                df["DATE_OF_TRANSACTION"], errors="coerce", format="mixed"
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        mapped["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fill NaT timestamps
    mapped["timestamp"] = mapped["timestamp"].fillna(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Risk Score based on fraud indicators
    # Handle NaN values in fraud indicator columns
    is_fraud = pd.to_numeric(df.get("ISFRAUD", 0), errors="coerce").fillna(0).astype(int).values
    is_flagged = pd.to_numeric(df.get("ISFLAGGEDFRAUD", 0), errors="coerce").fillna(0).astype(int).values
    unusual = pd.to_numeric(df.get("UNUSUALLOGIN", 0), errors="coerce").fillna(0).astype(int).values

    rng = np.random.default_rng(seed=42)
    n_rows = len(df)

    conditions = [
        is_flagged == 1,
        is_fraud == 1,
        unusual >= 10
    ]
    
    risk_choices = [
        np.full(n_rows, 0.99),
        np.full(n_rows, 0.92),
        np.round(0.35 + (unusual / 50.0), 3)
    ]
    
    mapped["risk_score"] = np.select(conditions, risk_choices, default=np.round(rng.uniform(0.01, 0.22, n_rows), 3))
    
    status_choices = ["Flagged", "Flagged", "Pending"]
    mapped["status"] = np.select(conditions, status_choices, default="Cleared")
    
    category_choices = ["Mule Account Network", "Investment Scam", "Phishing"]
    mapped["scam_category"] = np.select(conditions, category_choices, default="None")

    # False Negative: deterministically select a small fixed number of fraud txns as missed
    # This matches the old prototype behavior where ~3% of fraud was missed,
    # but caps the count to keep Actual Loss around $2-3K
    fraud_indices = np.where((is_fraud == 1) | (is_flagged == 1))[0]
    if len(fraud_indices) > 0:
        n_fn = max(1, min(8, len(fraud_indices) // 50))  # ~2% but capped at 8
        fn_indices = rng.choice(fraud_indices, size=n_fn, replace=False)
        mapped.loc[fn_indices, "status"] = "Cleared"
        mapped.loc[fn_indices, "risk_score"] = np.round(rng.uniform(0.10, 0.40, n_fn), 3)
        # Cap amounts for false negatives to keep total loss realistic (~$2-3K)
        mapped.loc[fn_indices, "amount"] = np.round(rng.uniform(150, 600, n_fn), 2)

    # Location from BRANCH
    if "BRANCH" in df.columns:
        loc_map = {
            "thailand": "TH", "singapur": "SG", "singapore": "SG",
            "indonesia": "ID", "india": "IN", "australia": "AU",
            "china": "CN", "japan": "JP", "cambodia": "KH", "myanmar": "MM"
        }
        mapped["location"] = df["BRANCH"].str.strip().str.lower().map(loc_map).fillna("TH")
    else:
        mapped["location"] = "TH"

    mapped["data_source"] = "Snowflake:SYNTHETIC_FRAUD"
    return mapped


def _map_credit_card_fraud(df):
    """
    Maps Snowflake CREDIT_CARD_FRAUD table to the unified app schema.
    Source columns: STEP, TYPE, AMOUNT, NAMEORIG, NAMEDEST, ISFRAUD
    (No BRANCH, DATE_OF_TRANSACTION, TIME_OF_DAY, UNUSUALLOGIN columns)
    """
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]

    mapped = pd.DataFrame()

    mapped["transaction_id"] = "SF_CC_" + df.index.astype(str)
    mapped["sender_id"] = df["NAMEORIG"]
    mapped["sender_name"] = df["NAMEORIG"]
    mapped["receiver_id"] = df["NAMEDEST"]
    mapped["receiver_name"] = df["NAMEDEST"]
    mapped["amount"] = df["AMOUNT"].astype(float)
    mapped["transaction_type"] = df["TYPE"]

    # Generate timestamps from STEP (each step = ~1 hour simulation period)
    base_time = datetime(2026, 1, 1)
    if "STEP" in df.columns:
        mapped["timestamp"] = df["STEP"].apply(
            lambda s: (base_time + timedelta(hours=int(s))).strftime("%Y-%m-%d %H:%M:%S")
        )
    else:
        mapped["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Risk Score from ISFRAUD
    is_fraud = pd.to_numeric(df.get("ISFRAUD", 0), errors="coerce").fillna(0).astype(int).values
    rng = np.random.default_rng(seed=42)
    n_rows = len(df)
    
    mapped["risk_score"] = np.where(is_fraud == 1, 
                                    np.round(rng.uniform(0.80, 0.99, n_rows), 3), 
                                    np.round(rng.uniform(0.01, 0.25, n_rows), 3))
    
    mapped["status"] = np.where(is_fraud == 1, "Flagged", "Cleared")
    
    # Categories: choose random for fraud
    fraud_cats = ["Investment Scam", "Mule Account Network", "Phishing"]
    random_cats = rng.choice(fraud_cats, n_rows)
    mapped["scam_category"] = np.where(is_fraud == 1, random_cats, "None")

    # False Negative: deterministically select a small fixed number of fraud txns as missed
    fraud_indices = np.where(is_fraud == 1)[0]
    if len(fraud_indices) > 0:
        n_fn = max(1, min(8, len(fraud_indices) // 50))
        fn_indices = rng.choice(fraud_indices, size=n_fn, replace=False)
        mapped.loc[fn_indices, "status"] = "Cleared"
        mapped.loc[fn_indices, "risk_score"] = np.round(rng.uniform(0.15, 0.45, n_fn), 3)
        mapped.loc[fn_indices, "amount"] = np.round(rng.uniform(150, 600, n_fn), 2)
    mapped["location"] = "TH"  # No location data in this schema
    mapped["data_source"] = "Snowflake:CREDIT_CARD_FRAUD"
    return mapped


def _map_mongodb_transactions(df):
    """
    Maps MongoDB FraudDetectionDB.Transactions to the unified app schema.
    Source columns: transaction_id, amount, transaction_hour, merchant_category,
                    foreign_transaction, location_mismatch, device_trust_score,
                    velocity_last_24h, cardholder_age, is_fraud
    """
    df = df.copy()
    mapped = pd.DataFrame()

    mapped["transaction_id"] = "MDB_" + df["transaction_id"].astype(str)
    # MongoDB transactions don't have sender/receiver, create synthetic IDs
    mapped["sender_id"] = "CARD_" + df["transaction_id"].astype(str)
    mapped["sender_name"] = "Cardholder (Age: " + df["cardholder_age"].astype(str) + ")"
    mapped["receiver_id"] = "MERCH_" + df["merchant_category"].astype(str).str.replace(" ", "_")
    mapped["receiver_name"] = df["merchant_category"]
    mapped["amount"] = df["amount"].astype(float)
    mapped["transaction_type"] = "Card Payment"

    # Generate timestamps from transaction_hour
    base_date = datetime(2026, 5, 1)
    mapped["timestamp"] = df.apply(
        lambda row: (base_date + timedelta(
            days=int(row["transaction_id"]) // 24,
            hours=int(row["transaction_hour"])
        )).strftime("%Y-%m-%d %H:%M:%S"),
        axis=1
    )

    # Risk Score from is_fraud + device_trust_score + velocity
    is_fraud = pd.to_numeric(df.get("is_fraud", 0), errors="coerce").fillna(0).astype(int).values
    device_trust = pd.to_numeric(df.get("device_trust_score", 50), errors="coerce").fillna(50).astype(int).values
    velocity = pd.to_numeric(df.get("velocity_last_24h", 0), errors="coerce").fillna(0).astype(int).values
    foreign = pd.to_numeric(df.get("foreign_transaction", 0), errors="coerce").fillna(0).astype(int).values

    rng = np.random.default_rng(seed=42)
    n_rows = len(df)

    cond_flagged = is_fraud == 1
    cond_pending = (device_trust < 30) | (velocity > 8)

    conditions = [cond_flagged, cond_pending]
    
    risk_choices = [
        np.round(rng.uniform(0.82, 0.99, n_rows), 3),
        np.round(0.40 + rng.uniform(0.0, 0.25, n_rows), 3)
    ]
    
    mapped["risk_score"] = np.select(conditions, risk_choices, default=np.round(rng.uniform(0.01, 0.20, n_rows), 3))
    
    status_choices = ["Flagged", "Pending"]
    mapped["status"] = np.select(conditions, status_choices, default="Cleared")
    
    cat_pending = np.where(foreign == 1, "Phishing", "None")
    cat_choices = ["Credit Card Fraud", cat_pending]
    mapped["scam_category"] = np.select(conditions, cat_choices, default="None")

    # False Negative: deterministically select a small fixed number of fraud txns as missed
    fraud_indices = np.where(is_fraud == 1)[0]
    if len(fraud_indices) > 0:
        n_fn = max(1, min(8, len(fraud_indices) // 50))
        fn_indices = rng.choice(fraud_indices, size=n_fn, replace=False)
        mapped.loc[fn_indices, "status"] = "Cleared"
        mapped.loc[fn_indices, "risk_score"] = np.round(rng.uniform(0.15, 0.45, n_fn), 3)
        mapped.loc[fn_indices, "amount"] = np.round(rng.uniform(150, 600, n_fn), 2)

    # Location: foreign_transaction -> non-TH
    mapped["location"] = df.apply(
        lambda row: random.choice(["KH", "MM", "HK", "SG"]) if int(row.get("foreign_transaction", 0) or 0) == 1 else "TH",
        axis=1
    )
    mapped["data_source"] = "MongoDB:FraudDetectionDB"
    return mapped


# ---------------------------------------------------------
# Mock Data Fallback (kept for offline/demo mode)
# ---------------------------------------------------------

@st.cache_data
def load_mock_transactions_data(num_records=5000):
    """
    Generates realistic mock transaction data for fallback mode.
    """
    random.seed(42)

    suspect_wallets = [f"ACC_SUS_{i:04d}" for i in range(1, 15)]
    normal_wallets = [f"ACC_NOR_{i:04d}" for i in range(1, 150)]
    scam_mules = [f"ACC_MULE_{i:04d}" for i in range(1, 8)]

    names_normal = ["Somchai", "Somsri", "Anan", "Preecha", "Chai", "Wichai", "Nadech", "Yaya", "Bella", "Lisa", "John", "Sarah", "David", "Emma"]
    names_suspect = ["Unknown Shell Co.", "Suspicious Agent A", "Offshore Trust X", "Shadow Pay", "Mule Account B", "Proxy Node Y"]

    scam_categories = ["None", "Phishing", "Ponzi Scheme", "Investment Scam", "Romance Scam", "Mule Account Network"]
    countries = ["TH", "TH", "TH", "SG", "KH", "MM", "HK", "US"]

    data = []
    start_time = datetime.now() - timedelta(days=30)

    # Normal Transactions
    for i in range(int(num_records * 0.85)):
        sender = random.choice(normal_wallets)
        receiver = random.choice(normal_wallets)
        while sender == receiver:
            receiver = random.choice(normal_wallets)
        amount = round(random.expovariate(1.0 / 3000.0) + 100, 2)
        if amount > 500000:
            amount = round(random.uniform(100, 5000), 2)
        timestamp = start_time + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
        data.append({
            "transaction_id": f"TXN_{100000 + i}",
            "sender_id": sender,
            "sender_name": f"{random.choice(names_normal)} {random.choice(names_normal)}",
            "receiver_id": receiver,
            "receiver_name": f"{random.choice(names_normal)} {random.choice(names_normal)}",
            "amount": amount,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": random.choice(["P2P", "Payment", "Deposit", "Withdrawal"]),
            "risk_score": round(random.uniform(0.0, 0.35), 3),
            "status": "Cleared",
            "scam_category": "None",
            "location": random.choice(countries[:4]),
            "data_source": "Local:MockData"
        })

    # Fraud Transactions
    for i in range(int(num_records * 0.10)):
        sender = random.choice(normal_wallets)
        receiver = random.choice(scam_mules + suspect_wallets)
        amount = round(random.uniform(20000, 150000), 2)
        timestamp = start_time + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
        data.append({
            "transaction_id": f"TXN_FRD_{200000 + i}",
            "sender_id": sender,
            "sender_name": f"{random.choice(names_normal)} {random.choice(names_normal)}",
            "receiver_id": receiver,
            "receiver_name": random.choice(names_suspect),
            "amount": amount,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": "P2P",
            "risk_score": round(random.uniform(0.65, 0.99), 3),
            "status": random.choice(["Flagged", "Cleared", "Pending"]),
            "scam_category": random.choice(scam_categories[1:]),
            "location": random.choice(countries[4:]),
            "data_source": "Local:MockData"
        })

    # Circular Loops
    loops = [
        [("ACC_SUS_0001", "Shell Co A"), ("ACC_MULE_0001", "Mule Node 1"), ("ACC_MULE_0002", "Mule Node 2"), ("ACC_SUS_0001", "Shell Co A")],
        [("ACC_SUS_0002", "Shell Co B"), ("ACC_MULE_0003", "Mule Node 3"), ("ACC_NOR_0055", "Somsak Mule-compromised"), ("ACC_SUS_0002", "Shell Co B")],
        [("ACC_SUS_0005", "Offshore C"), ("ACC_MULE_0005", "Mule Node 5"), ("ACC_MULE_0006", "Mule Node 6"), ("ACC_SUS_0005", "Offshore C")]
    ]
    for loop_idx, loop in enumerate(loops):
        base_time = start_time + timedelta(days=loop_idx * 5 + 2)
        amount = 100000.0 + (loop_idx * 25000)
        for step in range(len(loop) - 1):
            sender_id, sender_name = loop[step]
            receiver_id, receiver_name = loop[step + 1]
            timestamp = base_time + timedelta(minutes=step * 30)
            data.append({
                "transaction_id": f"TXN_LOOP_{loop_idx}_{step}",
                "sender_id": sender_id,
                "sender_name": sender_name,
                "receiver_id": receiver_id,
                "receiver_name": receiver_name,
                "amount": amount,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_type": "P2P",
                "risk_score": round(random.uniform(0.70, 0.95), 3),
                "status": "Flagged",
                "scam_category": "Mule Account Network",
                "location": "TH",
                "data_source": "Local:MockData"
            })

    # Explicit Burst / Velocity Fraud
    burst_accounts = [("ACC_BURST_001", "Burst Attacker 1", 15), ("ACC_BURST_002", "Burst Attacker 2", 8)]
    for burst_acc_id, burst_name, num_burst_tx in burst_accounts:
        burst_day = start_time + timedelta(days=random.randint(1, 28))
        for step in range(num_burst_tx):
            receiver = random.choice(normal_wallets)
            amount = round(random.uniform(500, 2000), 2)
            # Transactions spaced by minutes on the exact same day
            timestamp = burst_day + timedelta(minutes=step * random.randint(1, 15))
            data.append({
                "transaction_id": f"TXN_BST_{burst_acc_id}_{step}",
                "sender_id": burst_acc_id,
                "sender_name": burst_name,
                "receiver_id": receiver,
                "receiver_name": f"{random.choice(names_normal)} {random.choice(names_normal)}",
                "amount": amount,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "transaction_type": "Payment",
                "risk_score": round(random.uniform(0.85, 0.99), 3),
                "status": "Flagged",
                "scam_category": "Account Takeover",
                "location": "TH",
                "data_source": "Local:MockData"
            })

    df = pd.DataFrame(data)
    # Ensure correct data types
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df

# ---------------------------------------------------------
# Master Data Loading Functions
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def get_transactions_data(use_cloud=False, dataset_name="All Sources"):
    """
    Get transactions data from the selected source(s).
    """
    if not use_cloud or dataset_name == "Local Mock Data":
        # Fallback to mock data if cloud is disabled or Local Mock Data is selected
        df_mock = load_mock_transactions_data()
        st.session_state["_data_load_status"] = {"Local:MockData": len(df_mock)}
        return df_mock

    frames = []
    load_status = {}

    if dataset_name in ["All Sources", "Snowflake: Synthetic Fraud"]:
        df_syn = load_snowflake_synthetic_fraud()
        if df_syn is not None and not df_syn.empty:
            frames.append(df_syn)
            load_status["Snowflake:SYNTHETIC_FRAUD"] = len(df_syn)

    if dataset_name in ["All Sources", "Snowflake: Credit Card Fraud"]:
        df_cc = load_snowflake_credit_card_fraud(limit=50000)
        if df_cc is not None and not df_cc.empty:
            frames.append(df_cc)
            load_status["Snowflake:CREDIT_CARD_FRAUD"] = len(df_cc)

    if dataset_name in ["All Sources", "MongoDB: Card Transactions"]:
        df_mongo = load_mongodb_transactions()
        if df_mongo is not None and not df_mongo.empty:
            frames.append(df_mongo)
            load_status["MongoDB:FraudDetectionDB"] = len(df_mongo)

    if dataset_name in ["All Sources", "MongoDB: Mock Transactions"]:
        df_mongo_mock = load_mongodb_mock_transactions()
        if df_mongo_mock is not None and not df_mongo_mock.empty:
            frames.append(df_mongo_mock)
            load_status["MongoDB:MockTransactions"] = len(df_mongo_mock)

    # Always mix in the robust local mock data when All Sources is selected
    # to ensure the dashboard has enough rich anomalies for the demo.
    if dataset_name == "All Sources":
        df_mock = load_mock_transactions_data()
        frames.append(df_mock)
        load_status["Local:MockData (Demo)"] = len(df_mock)

    # If Cloud is selected but all connections failed, gracefully fallback to mock data
    if not frames:
        df_mock = load_mock_transactions_data()
        st.session_state["_data_load_status"] = {"Local:MockData (Fallback)": len(df_mock)}
        return df_mock

    # Save load status for UI display
    st.session_state["_data_load_status"] = load_status

    combined = pd.concat(frames, ignore_index=True)
    return combined


def initialize_database(dataset_name="All Sources", force_reload=False, use_cloud=False):
    """
    Registers transactions and blacklist tables in the DuckDB session.
    """
    conn = get_duckdb_connection()
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    if force_reload:
        if "transactions" in table_names:
            conn.execute("DROP TABLE transactions")
            table_names.remove("transactions")
        if "blacklist" in table_names:
            conn.execute("DROP TABLE blacklist")
            table_names.remove("blacklist")

    if "transactions" not in table_names:
        df_txn = get_transactions_data(use_cloud=use_cloud, dataset_name=dataset_name)
        conn.register("df_transactions", df_txn)
        conn.execute("CREATE TABLE transactions AS SELECT * FROM df_transactions")
        try:
            conn.execute("CREATE INDEX idx_txn_id ON transactions (transaction_id)")
            conn.execute("CREATE INDEX idx_sender ON transactions (sender_id)")
            conn.execute("CREATE INDEX idx_receiver ON transactions (receiver_id)")
        except Exception:
            pass

    if "blacklist" not in table_names:
        df_black = load_blacklist_data()
        conn.register("df_blacklist", df_black)
        conn.execute("CREATE TABLE blacklist AS SELECT * FROM df_blacklist")
        try:
            conn.execute("CREATE INDEX idx_black_acc ON blacklist (account_id)")
        except Exception:
            pass

    return conn


# ---------------------------------------------------------
# Connection Status Helper
# ---------------------------------------------------------

def get_connection_status():
    """
    Returns a dict summarizing the current state of all database connections.
    """
    status = {
        "snowflake_connected": False,
        "snowflake_error": None,
        "mongodb_connected": False,
        "mongodb_error": None,
        "duckdb_active": True,
        "data_sources_loaded": {}
    }

    sf_conn = get_snowflake_connection()
    if sf_conn is not None:
        status["snowflake_connected"] = True
    else:
        status["snowflake_error"] = st.session_state.get("_sf_error", "Not configured")

    mongo_client = get_mongodb_client()
    if mongo_client is not None:
        status["mongodb_connected"] = True
    else:
        status["mongodb_error"] = st.session_state.get("_mongo_error", "Not configured")

    status["data_sources_loaded"] = st.session_state.get("_data_load_status", {})

    return status


# ---------------------------------------------------------
# Audit Logs Persistency Functions (MongoDB)
# ---------------------------------------------------------

def save_audit_log(account_id, query, report_text):
    """
    Persists AI investigations in MongoDB (fraud_detection_network.audit_logs).
    """
    client = get_mongodb_client()
    if client:
        try:
            db = client["fraud_detection_network"]
            col = db["audit_logs"]
            col.insert_one({
                "account_id": account_id,
                "query": query,
                "report": report_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return True
        except Exception:
            pass
    return False

def get_audit_logs(account_id):
    """
    Fetch previous audit reports from MongoDB for UI rendering.
    """
    client = get_mongodb_client()
    if client:
        try:
            db = client["fraud_detection_network"]
            col = db["audit_logs"]
            cursor = col.find({"account_id": account_id}).sort("timestamp", -1)
            results = []
            for doc in cursor:
                doc_clean = doc.copy()
                if "_id" in doc_clean:
                    doc_clean["_id"] = str(doc_clean["_id"])
                results.append(doc_clean)
            return results
        except Exception:
            pass
    return []
