import pymongo
import random
import pandas as pd
from datetime import datetime, timedelta

def generate_mock_data(num_records=5000):
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
            "data_source": "MongoDB:MockTransactions"
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
            "data_source": "MongoDB:MockTransactions"
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
                "data_source": "MongoDB:MockTransactions"
            })

    # Explicit Burst / Velocity Fraud
    burst_accounts = [("ACC_BURST_001", "Burst Attacker 1", 15), ("ACC_BURST_002", "Burst Attacker 2", 8)]
    for burst_acc_id, burst_name, num_burst_tx in burst_accounts:
        burst_day = start_time + timedelta(days=random.randint(1, 28))
        for step in range(num_burst_tx):
            receiver = random.choice(normal_wallets)
            amount = round(random.uniform(500, 2000), 2)
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
                "data_source": "MongoDB:MockTransactions"
            })

    return data

def seed_mongodb():
    print("Generating mock data...")
    records = generate_mock_data()
    print(f"Generated {len(records)} records.")
    
    print("Connecting to MongoDB...")
    uri = "mongodb+srv://tirawat_thiti:NUfClwHBLcEUfJQM@cluster0.zsinxxe.mongodb.net/?appName=Cluster0"
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client["FraudDetectionDB"]
    col = db["MockTransactions"]
    
    print("Dropping old MockTransactions collection if it exists...")
    col.drop()
    
    print("Inserting data into MongoDB...")
    col.insert_many(records)
    print(f"✅ Successfully inserted {len(records)} records into FraudDetectionDB.MockTransactions!")

if __name__ == "__main__":
    seed_mongodb()
