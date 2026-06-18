import streamlit as st

translations = {
    # Sidebar
    "config_panel": {"TH": "🛠️ แผงควบคุมการตั้งค่า", "EN": "🛠️ Configuration Panel"},
    "select_dataset": {"TH": "📊 เลือกชุดข้อมูล", "EN": "📊 Select Dataset"},
    "reload_cache": {"TH": "🔄 โหลดข้อมูลใหม่ / ล้างแคช", "EN": "🔄 Reload Data / Clear Cache"},
    "cache_cleared": {"TH": "ล้างแคชแล้ว! โหลดข้อมูลใหม่สำเร็จ", "EN": "Cache cleared! New data loaded."},
    "connection_status": {"TH": "🔗 สถานะการเชื่อมต่อ", "EN": "🔗 Connection Status"},
    "data_loaded": {"TH": "📦 โหลดข้อมูลแล้ว:", "EN": "📦 Data Loaded:"},
    "google_creds": {"TH": "🔑 คีย์สำหรับ Google AI", "EN": "🔑 Google AI Credentials"},
    "google_api_key_label": {"TH": "google-generativeai API Key", "EN": "google-generativeai API Key"},
    "google_api_key_help": {"TH": "ใส่ API Key ของ Google AI เพื่อเปิดใช้งานการตอบกลับของ Gemma", "EN": "Enter your Google AI API key to enable live Gemma responses."},
    "api_key_updated": {"TH": "อัปเดต API Key ในเซสชันแล้ว!", "EN": "API Key updated in session!"},
    "gemma_model_select": {"TH": "เลือกโมเดล Gemma", "EN": "Gemma Model Selection"},
    "current_case": {"TH": "📂 เคสปัจจุบัน:", "EN": "📂 Current Case:"},
    "snowflake_connected": {"TH": "✅ Snowflake: เชื่อมต่อแล้ว", "EN": "✅ Snowflake: Connected"},
    "snowflake_disconnected": {"TH": "❌ Snowflake: ไม่ได้เชื่อมต่อ", "EN": "❌ Snowflake: Disconnected"},
    "mongodb_connected": {"TH": "✅ MongoDB: เชื่อมต่อแล้ว", "EN": "✅ MongoDB: Connected"},
    "mongodb_disconnected": {"TH": "❌ MongoDB: ไม่ได้เชื่อมต่อ", "EN": "❌ MongoDB: Disconnected"},

    # Home Page
    "home_title": {"TH": "🛡️ เครือข่ายตรวจจับการฉ้อโกงและการหลอกลวงทางการเงิน", "EN": "🛡️ Financial Fraud & Scam Detection Network"},
    "home_subtitle": {
        "TH": "การวิเคราะห์กราฟแบบเรียลไทม์ · การประมวลผลบนหน่วยความจำประสิทธิภาพสูง · การตรวจสอบคดีด้วย AI",
        "EN": "Real-time graph analytics · High-performance in-memory processing · AI-driven forensic investigations"
    },
    "quick_nav": {"TH": "🚀 เมนูการนำทางอย่างรวดเร็ว", "EN": "🚀 Quick Navigation"},
    "nav_dashboard_title": {"TH": "แดชบอร์ดผู้บริหาร", "EN": "Executive Dashboard"},
    "nav_dashboard_desc": {
        "TH": "การ์ด KPI, แนวโน้มรายวัน, แผนภูมิตำแหน่งทางภูมิศาสตร์, หมวดหมู่การฉ้อโกง และข้อมูลความเสี่ยงแบบเรียลไทม์",
        "EN": "KPI cards, daily trend, geographic bubble map, scam typologies & real-time high-risk feed"
    },
    "nav_analytics_title": {"TH": "โหมดการวิเคราะห์เชิงลึก", "EN": "Analytics Mode"},
    "nav_analytics_desc": {
        "TH": "การกรองข้อมูลขั้นสูง, การตรวจจับธุรกรรมแบบวนรอบ, แผนภูมิความร้อนความเร็วคดี, เครือข่ายร้านค้าความเสี่ยงสูง และ Box Plot ตรวจจับสิ่งผิดปกติ",
        "EN": "Deep filtering, circular loop detection, velocity heatmap, Shared Merchant network & anomaly box plot"
    },
    "nav_copilot_title": {"TH": "ระบบผู้ช่วย AI Copilot", "EN": "AI Copilot"},
    "nav_copilot_desc": {
        "TH": "ส่งบัญชีต้องสงสัยเพื่อสร้างรายงานวิเคราะห์กิจกรรม (SAR) ด้วย Gemma, แผนภูมิกระแสเงินไหล Sankey และแชทบอทถามตอบข้อมูล",
        "EN": "Escalate suspicious accounts for Gemma-powered SAR generation, Sankey money-flow, and chatbot Q&A"
    },
    "pipeline_title": {"TH": "ท่อส่งข้อมูลอัจฉริยะด้านการฉ้อโกงระดับองค์กร", "EN": "Enterprise Fraud Intelligence Pipeline"},
    "pipeline_sources": {"TH": "แหล่งข้อมูล (Data Sources)", "EN": "Data Sources"},
    "pipeline_compute": {"TH": "การประมวลผลและคำนวณ (Compute & Processing)", "EN": "Compute & Processing"},
    "pipeline_intelligence": {"TH": "ปัญญาประดิษฐ์และการใช้งาน (Intelligence & Consumption)", "EN": "Intelligence & Consumption"},
    "pipeline_ingests": {"TH": "นำเข้าข้อมูล", "EN": "Ingests"},
    "pipeline_serves": {"TH": "ให้บริการ", "EN": "Serves"},
    "issues_motivation_title": {"TH": "🚨 ปัญหาและแรงจูงใจ", "EN": "🚨 Issues & Motivation"},
    "issues_motivation_desc": {
        "TH": "ในเศรษฐกิจดิจิทัลปัจจุบัน อาชญากรรมทางการเงินได้พัฒนาไปสู่รูปแบบเครือข่ายที่ซับซ้อนและข้ามพรมแดน ระบบตรวจจับแบบดั้งเดิมมักวิเคราะห์ธุรกรรมแยกกัน ทำให้ไม่สามารถมองเห็นภาพรวมได้<br><br><b>ความท้าทายหลัก:</b><ul><li><b>เครือข่ายบัญชีม้า:</b> มิจฉาชีพใช้เครือข่ายบัญชีม้าในการโอนเงินหลบเลี่ยงแบบวนรอบ ทำให้ยากต่อการระบุแหล่งที่มา</li><li><b>การเตือนผิดพลาด (False Positives):</b> ระบบดั้งเดิมสร้างการแจ้งเตือนผิดพลาดมากเกินไป ทำให้ผู้ตรวจสอบทำงานได้ช้าลง</li><li><b>ขาดคำอธิบาย:</b> แม้โมเดลจะตรวจจับได้ แต่ผู้ตรวจสอบไม่เข้าใจว่า<i>ทำไม</i>บัญชีนั้นจึงถูกบล็อก</li></ul>ความมุ่งมั่นของเราคือการเชื่อมประสานระหว่างวิทยาศาสตร์ข้อมูลขั้นสูงและการสืบสวนคดีอัจฉริยะ เพื่อสร้างระบบที่ไม่ได้ทำเพียงแค่บล็อกธุรกรรม แต่ยังจำลองแผนผังขบวนการอาชญากรรมทั้งหมด",
        "EN": "In today's highly digitized economy, financial crimes have evolved into complex, cross-border operations. Traditional rule-based detection systems are failing to keep up because they analyze transactions in isolation.<br><br><b>Key Challenges:</b><ul><li><b>Mule Account Networks:</b> Scammers use deep networks of compromised accounts to layer and launder money through circular fund flows, making the source untraceable.</li><li><b>False Positives:</b> Traditional systems generate too many false alarms, overwhelming investigators and delaying critical action.</li><li><b>Lack of Explainability:</b> Even when ML models detect fraud, analysts struggle to understand <i>why</i> a transaction was flagged, leading to slower response times.</li></ul>Our motivation is to bridge the gap between advanced data engineering and investigative intelligence by building a system that doesn't just block transactions, but maps out entire criminal syndicates."
    },
    "objective_title": {"TH": "🎯 วัตถุประสงค์", "EN": "🎯 Objective"},
    "objective_desc": {
        "TH": "วัตถุประสงค์หลักคือเพื่อพัฒนา<b>ระบบวิเคราะห์กราฟและผู้ช่วยสืบสวนคดี AI Copilot แบบเรียลไทม์</b> สำหรับหน่วยข่าวกรองทางการเงิน (FIU) และทีมรักษาความปลอดภัยไซเบอร์<br><br><b>เป้าหมายของเรา:</b><ol><li><b>การจำลองเครือข่าย (Graph Analytics):</b> เชื่อมโยงบัญชีและอุปกรณ์ที่น่าสงสัยเพื่อตรวจพบเครือข่ายการฟอกเงิน รวมถึงการตรวจจับธุรกรรมแบบวนรอบ (A→B→C→A)</li><li><b>การประมวลผลประสิทธิภาพสูง:</b> ใช้ประโยชน์จาก Snowflake, MongoDB และ DuckDB บนหน่วยความจำเพื่อวิเคราะห์รายการโอนเงินนับล้านในเวลารวดเร็ว</li><li><b>คำอธิบายการฉ้อโกงด้วย AI:</b> ใช้ AI Copilot (Gemma) ตรวจสอบความผิดปกติและเขียนรายงานกิจกรรมที่น่าสงสัย (SAR) เป็นภาษาไทยในทันที</li></ol>",
        "EN": "The core objective is to develop a <b>Real-time Graph-based Analytics and AI Copilot</b> tailored for Financial Intelligence Units (FIUs) and Cybersecurity teams.<br><br><b>Our Goals:</b><ol><li><b>Network Mapping (Graph Analytics):</b> Connect the dots between seemingly unrelated accounts, IP addresses, and devices to uncover hidden money laundering rings — including <span class=\"highlight\">Circular Loop Detection</span> (A→B→C→A).</li><li><b>High-Performance Data Processing:</b> Leverage Snowflake, MongoDB, and in-memory DuckDB to process millions of transactions with minimal latency using parameterized queries and TTL caching.</li><li><b>Explainable AI (GenAI Integration):</b> Deploy an AI Copilot (Gemma/Gemini) that automatically audits flagged transactions and generates plain-language <span class=\"highlight\">Suspicious Activity Reports (SAR)</span> to assist human investigators.</li></ol>"
    },
    "tech_stack_title": {"TH": "🛠️ เครื่องมือและเทคโนโลยี", "EN": "🛠️ Tech Stack"},

    # Executive Dashboard
    "exec_dashboard_title": {"TH": "📊 แดชบอร์ดผู้บริหาร", "EN": "📊 Executive Dashboard"},
    "kpi_total_txns": {"TH": "รายการธุรกรรมทั้งหมด", "EN": "Total Transactions"},
    "kpi_processed": {"TH": "จำนวนรายการที่ผ่านการประมวลผล", "EN": "Transactions Processed"},
    "kpi_total_volume": {"TH": "ยอดการโอนเงินรวม", "EN": "Total Volume"},
    "kpi_value_transacted": {"TH": "มูลค่าการโอนเงินในระบบ", "EN": "Total Transacted Value"},
    "kpi_avg_risk": {"TH": "ดัชนีความเสี่ยงเฉลี่ย", "EN": "Average Risk Index"},
    "kpi_system_wide_risk": {"TH": "ความเสี่ยงรวมของระบบ", "EN": "System-wide Risk"},
    "kpi_high_risk_alerts": {"TH": "การแจ้งเตือนความเสี่ยงสูง", "EN": "High Risk Alerts"},
    "kpi_threshold_alerts": {"TH": "ความเสี่ยง >= 70%", "EN": ">=70% Risk Score"},
    "business_impact": {"TH": "🛡️ ผลกระทบทางธุรกิจ (ROI)", "EN": "🛡️ Business Impact (ROI)"},
    "value_saved": {"TH": "มูลค่าที่ช่วยไว้ได้ (ตรวจพบ)", "EN": "Value Saved (Flagged)"},
    "actual_loss": {"TH": "มูลค่าที่เกิดความเสียหาย (เล็ดลอด)", "EN": "Actual Loss (Missed)"},
    "system_risk_level": {"TH": "ระดับความเสี่ยงของระบบ", "EN": "System Risk Level"},
    "fraud_funnel_title": {"TH": "🔽 ช่องทางการตรวจจับการฉ้อโกง (Funnel)", "EN": "🔽 Fraud Detection Funnel"},
    "daily_trend_title": {"TH": "📅 แนวโน้มธุรกรรมรายวัน", "EN": "📅 Daily Transaction Trend"},
    "tx_volume_risk_type": {"TH": "📊 ปริมาณธุรกรรมและความเสี่ยงแยกตามประเภท", "EN": "📊 Transaction Volume & Risk by Type"},
    "realtime_feed": {"TH": "⚡ ข้อมูลความเสี่ยงสูงแบบเรียลไทม์ (Top 5)", "EN": "⚡ Real-time High Risk Feed (Top 5)"},
    "scam_typologies": {"TH": "📊 รูปแบบและประเภทของการหลอกลวง", "EN": "📊 Scam Typologies & Volumes"},
    "geographic_risk": {"TH": "🗺️ ความเสี่ยงทางภูมิศาสตร์", "EN": "🗺️ Geographic Risk"},
    "risk_profiling_title": {"TH": "🕵️‍♂️ การวิเคราะห์โปรไฟล์ความเสี่ยง & บัญชีต้องสงสัย", "EN": "🕵️‍♂️ Risk Profiling & Top Suspicious Accounts"},
    "tx_val_vs_risk": {"TH": "มูลค่าการโอนเงินเทียบกับโปรไฟล์ความเสี่ยง", "EN": "Transaction Value vs Risk Profile"},
    "top_suspicious_merchants": {"TH": "ร้านค้า/ผู้รับโอนที่มีความเสี่ยงสูง (Top 8)", "EN": "Top High-Risk Merchants/Receivers"},

    # Analytics Mode
    "analytics_title": {"TH": "📈 การวิเคราะห์เชิงลึก & เครือข่ายสแกมเมอร์", "EN": "📈 Deep Analytics & Scam Networks"},
    "analytics_desc": {
        "TH": "การกรองข้อมูลขั้นสูง ค้นหารูปแบบธุรกรรม ตรวจจับการโอนเงินแบบวนรอบ วิเคราะห์ความเร็ว และจำลองความเสี่ยงผ่าน DuckDB",
        "EN": "Advanced filtering, query transaction patterns, circular loop detection, velocity analysis, and fraud visualizations powered by DuckDB."
    },
    "search_filters": {"TH": "🔍 ตัวกรองการค้นหา", "EN": "🔍 Search Filters"},
    "filter_amount": {"TH": "มูลค่าธุรกรรม ($)", "EN": "Transaction Amount ($)"},
    "filter_min_risk": {"TH": "คะแนนความเสี่ยงขั้นต่ำ", "EN": "Min Risk Score"},
    "filter_scam_typology": {"TH": "ประเภทการหลอกลวง (Scam)", "EN": "Scam Typology"},
    "filter_destinations": {"TH": "ประเทศปลายทาง", "EN": "Destinations"},
    "filter_status": {"TH": "สถานะธุรกรรม", "EN": "Transaction Status"},
    "view_tx_data": {"TH": "📊 ดูข้อมูลธุรกรรมทั้งหมด", "EN": "📊 View Transactions Data"},
    "found_matching_tx": {"TH": "พบ {count:,} รายการธุรกรรมที่สอดคล้อง", "EN": "Found {count:,} Matching Transactions"},
    "search_placeholder": {"TH": "🔍 ค้นหาด้วยชื่อผู้ส่ง/ผู้รับ หรือ ID", "EN": "🔍 Filter by Sender/Receiver ID or Name"},
    "filtered_records": {"TH": "กรองข้อมูลเหลือ {count} รายการ", "EN": "Filtered to {count} records"},
    "send_to_copilot_title": {"TH": "🤖 ส่งข้อมูลให้ AI Copilot ตรวจสอบ", "EN": "🤖 Send Data to AI Copilot"},
    "send_to_copilot_desc": {"TH": "เลือก Account ID จากตารางเพื่อนำไปวิเคราะห์ต่อในหน้าถัดไป", "EN": "Select Account ID from the table above to send for further analysis"},
    "account_id_input_placeholder": {"TH": "พิมพ์ Account ID (เช่น CARD_9998)", "EN": "Type Account ID (e.g. CARD_9998)"},
    "btn_send_copilot": {"TH": "ส่งเข้า AI Copilot", "EN": "Send to AI Copilot"},
    "msg_send_success": {"TH": "✅ เลือกบัญชี {account} สำเร็จ! กรุณาไปที่หน้า AI Copilot เพื่อดำเนินการต่อ", "EN": "✅ Selected account {account} successfully! Please proceed to AI Copilot page"},
    "msg_send_error": {"TH": "ไม่พบบัญชีนี้ กรุณาตรวจสอบ ID อีกครั้ง", "EN": "Account not found, please check the ID again"},
    "msg_send_warning": {"TH": "กรุณาพิมพ์ Account ID ก่อนกดส่ง", "EN": "Please type an Account ID first"},
    
    # Analytics Tabs
    "tab_network_risk": {"TH": "🔗 เครือข่ายการฉ้อโกง & รูปแบบความเสี่ยง", "EN": "🔗 Fraud Network & Risk Patterns"},
    "tab_loop_detection": {"TH": "🔄 การตรวจจับการโอนเงินวนรอบ", "EN": "🔄 Circular Loop Detection"},
    "tab_velocity_analysis": {"TH": "⚡ การวิเคราะห์ความถี่ธุรกรรม", "EN": "⚡ Velocity / Burst Analysis"},
    "tab_anomaly_detection": {"TH": "🚨 ตรวจจับสิ่งผิดปกติบัตรเครดิต", "EN": "🚨 Credit Card Anomaly Detection"},
    
    # Tab content
    "high_risk_merchant_concentration": {"TH": "🏪 ความหนาแน่นของร้านค้ากลุ่มเสี่ยงสูง", "EN": "🏪 High-Risk Merchant Concentration"},
    "risky_merchants": {"TH": "ร้านค้าที่มีความเสี่ยง", "EN": "Risky Merchants"},
    "flagged_connections": {"TH": "การเชื่อมโยงที่น่าสงสัย", "EN": "Flagged Connections"},
    "fraud_volume": {"TH": "ปริมาณเงินฉ้อโกง", "EN": "Fraud Volume"},
    "risk_pattern_analysis": {"TH": "📊 การวิเคราะห์รูปแบบความเสี่ยง (Risk Status)", "EN": "📊 Risk Pattern Analysis"},
    "flagged_txns_label": {"TH": "ธุรกรรมที่ถูกระงับ (Flagged)", "EN": "Flagged Transactions"},
    "avg_flagged_amount": {"TH": "มูลค่าเฉลี่ยที่ถูกระงับ", "EN": "Avg Flagged Amount"},
    "fraud_clean_ratio": {"TH": "อัตราเปรียบเทียบสแกม/คลีน", "EN": "Fraud/Clean Ratio"},
    "tx_volume_by_status": {"TH": "ปริมาณธุรกรรมแยกตามสถานะ", "EN": "Transaction Volume by Status"},
    "avg_tx_amount_by_status": {"TH": "มูลค่าธุรกรรมเฉลี่ยแยกตามสถานะ", "EN": "Avg Transaction Amount by Status"},
    "fraud_volume_by_category": {"TH": "🗂️ ยอดรวมความเสียหายแยกตามประเภทคดีสแกม", "EN": "🗂️ Fraud Volume by Scam Category"},

    "circular_fund_flow_title": {"TH": "🔄 การตรวจจับกระแสเงินไหลเวียนแบบวนรอบ (Circular Loops)", "EN": "🔄 Circular Fund Flow Detection"},
    "circular_fund_flow_desc": {
        "TH": "ตรวจจับการโอนเงินวนกลับมาที่เดิมเพื่อฟอกเงินผ่านบัญชีม้า — ทั้งแบบทางตรง 2-Hop (A → B → A) และแบบขยายขอบเขต 3-Hop (A → B → C → A)",
        "EN": "Detect potential circular money laundering loops — including 2-hop direct loops (A → B → A) and 3-hop layering loops (A → B → C → A)"
    },
    "direct_loops": {"TH": "ธุรกรรมวนรอบทางตรง (A→B→A)", "EN": "Direct Loops (A→B→A)"},
    "three_hop_loops": {"TH": "ธุรกรรมวนรอบ 3 ขั้น (A→B→C→A)", "EN": "3-Hop Loops (A→B→C→A)"},
    "total_loop_volume": {"TH": "มูลค่าเงินโอนวนรอบสะสม", "EN": "Total Loop Volume"},
    "circular_loop_network_graph": {"TH": "🕸️ แผนผังเครือข่ายธุรกรรมแบบวนรอบ (Circular Loop Network)", "EN": "🕸️ Circular Loop Network Graph"},
    "circular_graph_caption": {"TH": "🔴 = บัญชีที่โอนเงินวนรอบ | ➡️ = ทิศทางการโอน | ความหนาเส้น = ขนาดของมูลค่าเงินโอน", "EN": "🔴 = Loop participant nodes | ➡️ = direction of fund transfer | Edge width = transaction amount"},
    "loop_participants_summary": {"TH": "📋 สรุปข้อมูลผู้มีส่วนร่วมในการโอนเงินวนรอบ", "EN": "📋 Loop Participants Summary"},
    "detected_loop_edges": {"TH": "🔗 ความสัมพันธ์ของคู่บัญชีที่อยู่ในวงรอบการโอนเงิน", "EN": "🔗 Detected Loop Edges"},

    "velocity_burst_title": {"TH": "⚡ การวิเคราะห์ความถี่และพฤติกรรมธุรกรรมที่พุ่งสูงรวดเร็ว (Velocity & Burst)", "EN": "⚡ Velocity & Burst Transaction Analysis"},
    "velocity_burst_desc": {
        "TH": "ตรวจสอบบัญชีที่มีรายการโอนเงินบ่อยครั้งผิดปกติในวันเดียว (เช่น Card Testing, โจมตีบัญชีแบบอัตโนมัติ) และแผนภูมิความร้อนแสดงช่วงเวลาเสี่ยง",
        "EN": "Detect accounts with abnormally high transaction rates in a short timeframe (Card Testing / Account Takeover / Burst Fraud) and display temporal trends"
    },
    "min_tx_day_threshold": {"TH": "จำนวนธุรกรรมขั้นต่ำต่อวัน (Burst Threshold)", "EN": "Min Txns/Day (Burst threshold)"},
    "velocity_info_msg": {"TH": "บัญชีที่ทำธุรกรรมเกินจำนวนครั้งที่กำหนดต่อวันนี้ จะถูกตรวจสอบพฤติกรรมเสี่ยงทันที", "EN": "Accounts exceeding this transaction threshold per day will be flagged for velocity fraud"},
    "top_burst_accounts": {"TH": "🏃 รายชื่อบัญชีที่มีความถี่ธุรกรรมสูงสุดต่อวัน (Top Burst)", "EN": "🏃 Top Burst Accounts by Daily Transaction Count"},
    "burst_account_details": {"TH": "📋 รายละเอียดรายการธุรกรรมของบัญชีต้องสงสัย", "EN": "📋 Burst Account Details"},
    "fraud_temporal_analysis": {"TH": "📊 แผนภาพความถี่ตามช่วงเวลา (วัน × ชั่วโมงในหนึ่งสัปดาห์)", "EN": "📊 Fraud Temporal Analysis"},
    "fraud_temporal_caption": {"TH": "ขนาดวงกลม = ปริมาณธุรกรรม · สีเข้ม/แดง = ปริมาณสูงหรือมีความเสี่ยง", "EN": "Circle size = transaction volume · Darker colors = higher risk/volume"},
    "hourly_trend_caption": {"TH": "📈 ยอดธุรกรรมสะสมรายชั่วโมง (สะสมในทุกวัน)", "EN": "📈 Hourly Total (all days cumulative)"},

    "tx_amount_anomaly_title": {"TH": "💳 การตรวจหาธุรกรรมที่มูลค่าสูงผิดปกติ (Amount Anomaly)", "EN": "💳 Transaction Amount Anomaly Detection"},
    "tx_amount_anomaly_desc": {
        "TH": "แผนภูมิ Box/Violin แสดงการกระจายตัวของมูลค่าธุรกรรม จุดที่อยู่ห่างนอกกรอบคือจุดผิดปกติทางสถิติ (Outliers) ที่ต้องตรวจสอบเชิงลึก",
        "EN": "The Box/Violin plot shows transaction amount distribution. Points outside the normal range are statistical outliers that require attention."
    },
    "chart_type_label": {"TH": "ประเภทแผนภูมิ:", "EN": "Chart Type:"},
    "plot_box": {"TH": "📦 แผนภูมิกล่อง (เน้นค่าผิดปกติ Outliers)", "EN": "📦 Box Plot (Outliers)"},
    "plot_violin": {"TH": "🎻 แผนภูมิไวโอลิน (เน้นการกระจายตัว)", "EN": "🎻 Violin Plot (Distribution)"},
    "box_caption": {"TH": "📦 **Box Plot** — กล่อง = ช่วงข้อมูลปกติ (25th–75th percentile), เส้นกลาง = ค่ากลาง, จุดด้านนอก = ข้อมูลที่สูงผิดปกติทางสถิติ", "EN": "📦 **Box Plot** — Box = IQR (25th–75th percentile), center line = median, outer points = statistical outliers"},
    "violin_caption": {"TH": "🎻 **Violin Plot** แสดงความหนาแน่นของข้อมูล — ยิ่งแถบกว้าง = มีความถี่ธุรกรรมในช่วงราคานั้นสูง ซึ่งธุรกรรมต้องสงสัยมักกระจุกตัวที่ยอดราคาสูง", "EN": "🎻 **Violin Plot** shows Kernel Density Estimation (KDE) — wider parts = more transactions at that price point. Flagged txns tend to cluster at higher amounts."},

    # AI Copilot
    "ai_copilot_title": {"TH": "🤖 ระบบผู้ช่วยสืบสวนและวิเคราะห์คดีอัจฉริยะ (AI Copilot)", "EN": "🤖 AI Copilot (Powered by Gemma & MongoDB)"},
    "ai_copilot_desc": {"TH": "สร้างเอกสารรายงานกิจกรรมที่น่าสงสัย (SAR) อัตโนมัติ ตรวจสอบทิศทางเงินหมุนเวียนด้วยแผนภาพอุดตัน และแชทบอทสอบถามคดี", "EN": "Conduct automated intelligence reports, trace fund layering networks, and query crime database records."},
    "warn_no_case_selected": {"TH": "⚠️ โปรดกลับไปเลือกบัญชีที่ต้องการตรวจสอบจากตารางในหน้า 'โหมดการวิเคราะห์' (Analytics Mode) ก่อนใช้งานหน้านี้", "EN": "⚠️ Please select a suspicious account from the transactions table on the 'Analytics Mode' page first."},
    "investigating_file": {"TH": "📁 แฟ้มข้อมูลสอบสวนบัญชี: `{account}`", "EN": "📁 Investigating Account File: `{account}`"},
    "counterparty_network": {"TH": "🪢 แผนผังเครือข่ายคู่บัญชีสัมพันธ์ (Counter-party Network)", "EN": "🪢 Counter-party Network"},
    "money_flow_sankey": {"TH": "💸 กระแสเงินหมุนเวียน (Sankey Flow Diagram)", "EN": "💸 Money Flow (Sankey)"},
    "sankey_caption": {"TH": "🔴 = กระแสเงินความเสี่ยงสูง | 🟡 = ความเสี่ยงปานกลาง | 🔵 = ความเสี่ยงต่ำ | ความกว้างของสายสัมพันธ์แปรผันตามยอดโอน", "EN": "🔴 = High-risk flow | 🟡 = Medium risk | 🔵 = Low risk | Width = proportional to transaction amount"},
    "transaction_log_top5": {"TH": "📑 ประวัติรายการโอนเงิน 5 รายการล่าสุด", "EN": "📑 Transaction Log (Top 5)"},
    "explainable_ai_audit": {"TH": "🤖 รายงานการตรวจสอบคดีโดยปัญญาประดิษฐ์ (Gemma AI)", "EN": "🤖 Explainable AI Audit (Gemma Model)"},
    "btn_run_ai_analysis": {"TH": "🤖 เริ่มการวิเคราะห์ด้วย AI และสร้างรายงานวิเคราะห์กิจกรรม (SAR)", "EN": "🤖 Run AI Analysis & Generate SAR Report"},
    "btn_save_mongodb": {"TH": "💾 บันทึกรายงานวิเคราะห์นี้เก็บในฐานข้อมูล MongoDB", "EN": "💾 Save this Report to MongoDB (audit_logs)"},
    "msg_save_success": {"TH": "บันทึกข้อมูลเรียบร้อยแล้วในคอลเลกชัน MongoDB: audit_logs", "EN": "Saved successfully to MongoDB collection: audit_logs"},
    "msg_save_error": {"TH": "บันทึกไม่สำเร็จ กรุณาตรวจสอบการตั้งค่า MongoDB URI ใน secrets.toml", "EN": "Failed to save. Please verify your MongoDB connection string in secrets.toml"},
    "past_investigations": {"TH": "📚 ประวัติการตรวจสอบย้อนหลังที่เคยบันทึกในระบบ ({count} รายงาน)", "EN": "📚 Past Investigations ({count} reports in MongoDB)"},
    "chat_placeholder": {"TH": "ถามข้อมูลบัญชีนี้ (เช่น ใครเป็นผู้โอนเงินเข้ามามากที่สุด?)", "EN": "Ask about this account (e.g., Who sent the highest volume?)"},
    "btn_save_chat": {"TH": "💾 บันทึกประวัติการแชทลงฐานข้อมูล MongoDB", "EN": "💾 Save Chat History to MongoDB"},
    "msg_save_chat_success": {"TH": "บันทึกประวัติการสนทนาเรียบร้อย!", "EN": "Chat transcript saved successfully!"},
    "demo_mode_warning": {"TH": "⚠️ **[Demo Mode]** ระบบจำเป็นต้องใช้ Google Gemini API Key กรุณากรอกคีย์ที่แถบด้านข้าง (Sidebar) เพื่อเริ่มใช้งาน", "EN": "⚠️ **[Demo Mode]** Google Gemini API Key required. Please configure it in the sidebar to enable chat functionality."},
    "blacklist_status": {"TH": "⚠️ สถานะบัญชีดำ: {status}", "EN": "⚠️ Blacklist Status: {status}"},
    "account_label": {"TH": "บัญชี: {account_id}", "EN": "Account: {account_id}"},
    "reason_label": {"TH": "เหตุผล:", "EN": "Reason:"},
    "reported_label": {"TH": "วันที่รายงาน:", "EN": "Reported:"},
    "network_credentials_title": {"TH": "🛡️ ข้อมูลประจำตัวอาชญากรรมเครือข่าย (MongoDB)", "EN": "🛡️ Network Crime Credentials (MongoDB)"},
    "device_id_label": {"TH": "รหัสอุปกรณ์ (Device ID):", "EN": "Device ID:"},
    "ip_address_label": {"TH": "ที่อยู่ IP (IP Address):", "EN": "IP Address:"},
    "fetched_realtime_mongodb": {"TH": "*ดึงข้อมูลแบบเรียลไทม์จากคลัสเตอร์ MongoDB", "EN": "*Fetched in real-time from MongoDB cluster."},
    "hover_account": {"TH": "บัญชี", "EN": "Account"},
    "no_connections": {"TH": "ไม่มีข้อมูลการเชื่อมต่อเพื่อแสดงแผนผัง", "EN": "No connections to draw."},
    "no_network_data": {"TH": "ไม่มีข้อมูลเครือข่ายเชื่อมต่อ", "EN": "No connected network data."},
    "no_sankey_data": {"TH": "มีข้อมูลกระแสเงินไม่เพียงพอสำหรับสร้างแผนผัง Sankey", "EN": "Not enough flow data to build Sankey diagram."},
    "no_records": {"TH": "ไม่มีข้อมูลให้แสดง", "EN": "No records to display."},
    "tab_sar": {"TH": "📄 เครื่องมือสร้างรายงาน SAR", "EN": "📄 SAR Generator"},
    "tab_chat": {"TH": "💬 แชทบอทวิเคราะห์ข้อมูล", "EN": "💬 Data-Centric Chatbot"},
    "spinner_ai_analysis": {"TH": "กำลังเชื่อมต่อกับ Gemma AI และวิเคราะห์ธุรกรรม...", "EN": "Connecting to Gemma AI and analyzing transactions..."},
    "generated_sar_title": {"TH": "📄 รายงานกิจกรรมที่น่าสงสัย (SAR) ที่สร้างขึ้น", "EN": "Generated Suspicious Activity Report (SAR)"},
    "generated_sar_demo_title": {"TH": "📄 รายงาน SAR ที่สร้างขึ้น (โหมดสาธิต)", "EN": "Generated SAR (Demo Mode)"},
    "btn_save_report_mongodb": {"TH": "💾 บันทึกรายงานนี้ลง MongoDB", "EN": "Save this Report to MongoDB"},
    "msg_save_report_success": {"TH": "บันทึกเรียบร้อย (MongoDB: audit_logs)", "EN": "Saved successfully (MongoDB: audit_logs)"},
    "msg_save_report_error": {"TH": "บันทึกไม่สำเร็จ ตรวจสอบ MongoDB URI ใน secrets.toml", "EN": "Save failed, verify MongoDB URI in secrets.toml"},
    "no_prior_investigations": {"TH": "ไม่มีข้อมูลการสืบสวนก่อนหน้าสำหรับบัญชีนี้", "EN": "No prior investigations logged for this account."},
    "ai_database_agent": {"TH": "💬 เอเย่นต์ฐานข้อมูล AI", "EN": "AI Database Agent"},
    "chat_description": {"TH": "สนทนากับ AI โดยใช้บริบทธุรกรรมของบัญชีที่เลือก", "EN": "Chat with the AI using the context of the selected account's transactions."},
    "chatbot_demo_msg": {"TH": "⚠️ **[Demo Mode]** ระบบ Chatbot แบบโต้ตอบจำเป็นต้องใช้ Google Gemini API Key กรุณาใส่ API Key ที่แถบด้านข้าง (Sidebar) เพื่อเริ่มสนทนาครับ", "EN": "⚠️ **[Demo Mode]** Interactive Chatbot requires Google Gemini API Key. Please configure it in the sidebar to begin chatting."},
    "spinner_analyzing": {"TH": "กำลังวิเคราะห์...", "EN": "Analyzing..."},
    "invalid_api_key_err": {"TH": "❌ ข้อผิดพลาด: API key หรือโมเดลไม่ถูกต้อง กรุณาตรวจสอบข้อมูลการรับรองของคุณ", "EN": "❌ Error: Invalid API key or model. Please check your credentials"},
    "msg_save_chat_error": {"TH": "บันทึกประวัติการสนทนาไม่สำเร็จ กรุณาตรวจสอบการตั้งค่า MongoDB URI", "EN": "Failed to save chat history. Please verify your MongoDB connection string"}
}

def t(key):
    """
    Translates a key according to the active language in Streamlit session state.
    Defaults to TH if not configured.
    """
    lang = st.session_state.get("language", "TH")
    item = translations.get(key)
    if not item:
        return key
    return item.get(lang, item.get("EN", key))
