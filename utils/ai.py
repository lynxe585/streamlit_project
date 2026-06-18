from google.ai import generativelanguage
import streamlit as st
import os
import pandas as pd
import json

# Try to import google.generativeai, handle import error gracefully
HAS_GENAI = False
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    pass

def get_api_key():
    """
    Retrieves the Google API Key from secrets, environment variables, or session state.
    """
    # 1. Check session state (user-entered in UI)
    try:
        if "google_api_key" in st.session_state and st.session_state["google_api_key"]:
            return st.session_state["google_api_key"]
    except Exception:
        pass
    
    # 2. Check streamlit secrets
    try:
        if "google" in st.secrets and "api_key" in st.secrets["google"]:
            return st.secrets["google"]["api_key"]
    except Exception:
        pass

    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
        
    # 3. Check environment variables
    return os.environ.get("GOOGLE_API_KEY", "")


def is_ai_configured():
    """
    Checks if the Google GenAI SDK is installed and an API key is available.
    """
    return HAS_GENAI and bool(get_api_key())

def get_gemma_model_list(api_key=None):
    """
    Lists available Gemma models if the API key is configured.
    Falls back to standard lists.
    """
    if not api_key:
        api_key = get_api_key()
        
    if HAS_GENAI and api_key:
        try:
            genai.configure(api_key=api_key)
            models = genai.list_models()
            available_models = [m.name.split('/')[-1] for m in models if "gemma" in m.name.lower()]
            if available_models:
                return available_models
        except Exception as e:
            pass
    # Standard Gemma models list
    return ["gemma-2-27b-it", "gemma-2-9b-it", "gemma-1.1-7b-it", "gemma-7b-it"]

def query_gemma_model(prompt, system_instruction=None, model_name="gemma2-9b-it"):
    """
    Queries the specified Gemma model using the google-generativeai SDK.
    Falls back to demo response if no API key is set.
    """
    api_key = get_api_key()
    
    if not HAS_GENAI:
        return _generate_demo_response(prompt, "Google Generative AI library not installed.")
        
    if not api_key:
        return _generate_demo_response(prompt, "API Key is missing. Configure it in the Sidebar or secrets.toml")

    try:
        genai.configure(api_key=api_key)
        
        # Configure generation parameters
        generation_config = {
            "temperature": 0.4,
            "top_p": 0.95,
            "max_output_tokens": 4096,
        }
        
        # In the new google-generativeai API:
        # If system_instruction is supported (Gemini/Gemma models), use GenerativeModel constructor
        # gemma2-9b-it and gemini models accept system_instruction in GenerativeModel
        model = genai.GenerativeModel(
            model_name=f"models/{model_name}" if not model_name.startswith("models/") else model_name,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # If gemma2-9b-it fails or isn't available under this API key, try falling back to gemini-1.5-flash
        if "gemma" in model_name:
            try:
                fallback_model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config=generation_config,
                    system_instruction=system_instruction
                )
                response = fallback_model.generate_content(prompt + "\n\n*(Note: Ran using Gemini fallback as Gemma model request failed)*")
                return response.text
            except Exception as ex:
                return f"Error running GenAI models: {str(e)} -> Fallback error: {str(ex)}"
        return f"Error querying Generative AI model: {str(e)}"

def run_ai_investigation(account_id, transactions_df, user_question):
    """
    Prepares data and system prompts to investigate a suspicious wallet address / account.
    """
    # Format transactions for LLM context
    tx_records = transactions_df.to_dict(orient="records")
    tx_context = ""
    for r in tx_records[:30]: # Limit to top 30 transactions for token conservation
        tx_context += (
            f"- TxID: {r['transaction_id']} | Date: {r['timestamp']} | "
            f"Sender: {r['sender_id']} ({r['sender_name']}) -> "
            f"Receiver: {r['receiver_id']} ({r['receiver_name']}) | "
            f"Amount: ${r['amount']:,} | Risk Score: {r['risk_score']} | "
            f"Status: {r['status']} | Category: {r['scam_category']} | Location: {r['location']}\n"
        )
        
    system_instruction = (
        "You are an expert Financial Intelligence Unit (FIU) Lead Investigator and Forensic Auditor. "
        "Your role is to analyze transaction logs to detect scams, money laundering, mule account networks, "
        "and coordinate threat mitigation. You use clear, structured language, point out specific red flags, "
        "explain money-routing networks (e.g., shell accounts, layered payouts), and recommend actions (freeze accounts, KYC audit). "
        "Keep your output professional, objective, and action-oriented."
    )
    
    prompt = f"""
Analyze the transactions associated with the account: **{account_id}**.
Below are the transaction logs related to this account:

{tx_context}

User's Investigation Query: "{user_question}"

Please provide your forensic analysis covering:
1. **Account Risk Profile**: Is this account a victim, a mule account, an organizer/shell company, or a normal actor? Explain why based on the transfer patterns (e.g. speed, amounts, directions).
2. **Key Anomaly Findings**: Highlight any specific red flags (e.g., cross-border transfers to high-risk zones like MM/KH, high volume speed, circular/loop trails, or rapid drain of deposits).
3. **Network Connection Map (Brief Text Explanation)**: Explain how they link to other nodes in the logs.
4. **Actionable Recommendations**: Give 3 step-by-step mitigation options (e.g., suspend withdrawals, request enhanced diligence, notify police/fiu).
5. **Direct Answer**: Provide a concise answer to the User's Query.
"""
    # Get the selected model from session state, defaulting to gemma2-9b-it
    selected_model = st.session_state.get("selected_model", "gemma2-9b-it")
    return query_gemma_model(prompt, system_instruction, selected_model)

def _generate_demo_response(prompt, warning_msg):
    """
    High-fidelity simulation of Gemma AI response when API key is missing.
    Analyzes the prompt text to provide highly relevant mock analysis.
    """
    account_id = "Unknown"
    # Try to extract account ID from prompt
    for line in prompt.split("\n"):
        if "associated with the account:" in line or "Analyze the transactions" in line or "เกี่ยวกับบัญชี" in line:
            parts = line.split("**")
            if len(parts) >= 2:
                account_id = parts[1]
                break
                
    is_mule = "MULE" in account_id or "SUS" in account_id
    is_suspect = "SUS" in account_id
    
    if language == "TH":
        role = "บัญชีม้า / จุดพักเงิน (Layering Node)" if is_mule else ("บริษัทผีความเสี่ยงสูง (Shell Account)" if is_suspect else "บัญชีผู้ใช้ทั่วไป")
        risk_level = "สูงมาก (HIGH - 95%)" if (is_mule or is_suspect) else "ต่ำ (LOW - 12%)"
        
        demo_output = f"""
> ⚠️ **[DEMO MODE]** *{warning_msg} นี่คือการจำลองผลลัพธ์ของโมเดล Gemma-2b/9b*

### 🔍 รายงานการตรวจสอบทางนิติวิทยาศาสตร์: บัญชี {account_id}
**เวลาที่วิเคราะห์:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**ระดับความเสี่ยง:** `{risk_level}`  
**ประเมินประเภทบัญชี:** `{role}`

---

#### 1. บทสรุปผู้บริหารและวิเคราะห์พฤติกรรม
"""
        if is_mule or is_suspect:
            demo_output += f"""
- **ประเภทบัญชี:** มีส่วนร่วมในเครือข่ายบัญชีม้า (Mule Ring)
- **รูปแบบพฤติกรรม:** บัญชีนี้มีพฤติกรรม 'ทางผ่านเงิน' (Pass-through) อย่างชัดเจน พบว่ามีเงินฝากจำนวนมากเข้ามาจากบัญชีย่อย จากนั้นจะถูกโอนออกไปยังบัญชีต่างประเทศ (Offshore) ทันที เงินแทบจะไม่ถูกเก็บไว้ในบัญชีเกิน 24 ชั่วโมง ซึ่งบ่งชี้ถึงการฟอกเงินเพื่อปกปิดแหล่งที่มา
"""
        else:
            demo_output += f"""
- **ประเภทบัญชี:** บัญชีส่วนบุคคลหรือร้านค้าที่มีความเสี่ยงต่ำ
- **รูปแบบพฤติกรรม:** ปริมาณและระยะเวลาการทำธุรกรรมอยู่ในเกณฑ์ปกติ ไม่พบสัญญาณการโอนเงินแบบอัตโนมัติ การสูบเงินออกอย่างรวดเร็ว หรือพฤติกรรมที่น่าสงสัย
"""

        demo_output += """
#### 2. ข้อพิรุธหลักที่ตรวจพบ (Key Red Flags)
"""
        if is_mule or is_suspect:
            demo_output += f"""
- 🔴 **ความเร็วในการทำธุรกรรมสูง:** มีการโอนเงินเข้าและออกสลับกันอย่างรวดเร็วภายในไม่กี่นาทีหรือชั่วโมง
- 🔴 **เส้นทางข้ามพรมแดน:** มีการกระจุกตัวของการโอนเงินไปยังพื้นที่ชายแดนความเสี่ยงสูง (เช่น กัมพูชา - KH, เมียนมาร์ - MM)
- 🔴 **เครือข่ายวนลูป:** ธุรกรรมเชื่อมโยงกับบัญชีที่มีการโอนเงินกลับมายังต้นทางหรือบริษัทผีในเครือข่าย ซึ่งเป็นตัวบ่งชี้การฟอกเงินแบบวนลูป
"""
        else:
            demo_output += """
- 🟢 **พฤติกรรมปกติ:** ปลายทางทั้งหมดอยู่ในเขตความเสี่ยงต่ำ (TH/SG)
- 🟢 **ระยะเวลา:** มีการทิ้งช่วงเวลาที่เหมาะสมระหว่างการรับเงินและการจ่ายเงิน
"""

        demo_output += f"""
#### 3. สรุปเครือข่ายเชื่อมโยง (Network Map)
- **บัญชีต้นทาง (Source Nodes):** เงินไหลเข้ามาจากบัญชีรายย่อยหลายบัญชี
- **บัญชีพักเงิน (Intermediary Nodes):** เงินถูกรวบรวมไว้ที่ **{account_id}**
- **บัญชีปลายทาง (Exit Nodes):** ทุนถูกโอนออกไปยังบัญชีบริษัทผีในต่างประเทศ

#### 4. ข้อเสนอแนะสำหรับการดำเนินการ (Actionable Recommendations)
1. 🚫 **ระงับชั่วคราว:** อายัดการทำธุรกรรมฝั่งขาออก (Debit-freeze) ของบัญชี **{account_id}** ทันที เพื่อป้องกันเงินไหลออกนอกประเทศ
2. 📇 **ตรวจสอบเชิงลึก (EDD):** ร้องขอเอกสารยืนยันตัวตนของผู้รับผลประโยชน์ที่แท้จริง (UBO) และแหล่งที่มาของรายได้
3. 📞 **รายงาน ปปง. (FIU):** ยื่นรายงานธุรกรรมที่มีเหตุอันควรสงสัย (STR) ต่อสำนักงานป้องกันและปราบปรามการฟอกเงิน

#### 5. คำตอบโดยตรง
จากรูปแบบการทำธุรกรรม บัญชีนี้ทำงานในลักษณะ **{role}** ที่อำนวยความสะดวกในการย้ายเงินผิดกฎหมาย แนะนำให้ระงับการทำธุรกรรมและตรวจสอบตัวตนอย่างละเอียดทันที
"""
        return demo_output

    else:
        role = "Mule Account / Layering Node" if is_mule else ("High-Risk Shell Account" if is_suspect else "Standard Retail Account")
        risk_level = "HIGH (95%)" if (is_mule or is_suspect) else "LOW (12%)"
        
        demo_output = f"""
> ⚠️ **[DEMO MODE]** *{warning_msg} Showing simulated Gemma-2b/9b inference.*

### 🔍 Forensic Audit Report: Account {account_id}
**Analysis Timestamp:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Risk Level Score:** `{risk_level}`  
**Assessed Entity Persona:** `{role}`

---

#### 1. Account Risk Profile
"""
        if is_mule or is_suspect:
            demo_output += f"""
- **Entity Type:** Active participant in structured fund layering (Mule Ring).
- **Behavioral Pattern:** This account displays a classic 'pass-through' velocity signature. We observe substantial deposit sums arriving from retail accounts, followed immediately by high-value outward transfers to offshore entities. Very little capital is held in the account for more than 24 hours, indicating transactional layering designed to obfuscate the origin of illicit funds.
"""
        else:
            demo_output += f"""
- **Entity Type:** Low-risk personal account or merchant receiver.
- **Behavioral Pattern:** Regular transaction volumes with consistent peer frequencies. No signs of automated layering, rapid drainage, or suspicious multi-party consolidation.
"""

        demo_output += """
#### 2. Key Anomaly Findings
"""
        if is_mule or is_suspect:
            demo_output += f"""
- 🔴 **High Velocity Transfers:** Rapid inflow-outflow cycles occurring within minutes/hours of each other.
- 🔴 **Jurisdictional Routing:** High concentration of funds routed to high-risk border regions (e.g., Cambodia - KH, Myanmar - MM).
- 🔴 **Loop Networks:** Transactions involve accounts that ultimately cycle funds back to the source or affiliated shell companies, a strong indicator of circular money laundering.
"""
        else:
            demo_output += """
- 🟢 **Standard Behavior:** All locations reside in low-risk regions (TH/SG).
- 🟢 **Pacing:** Healthy time intervals between deposits and payments.
"""

        demo_output += f"""
#### 3. Network Connection Map (Text Explanation)
- **Source Nodes:** Inflows originating from various retail accounts.
- **Intermediary Nodes:** Funds are aggregated at **{account_id}**.
- **Exit Nodes:** Capital is funneled out to Offshore Shell accounts.

#### 4. Actionable Recommendations
1. 🚫 **Temporary Hold:** Place a temporary debit-freeze on account **{account_id}** immediately to prevent further offshore flight of funds.
2. 📇 **Enhanced Due Diligence (EDD):** Request verification of the beneficial owner (UBO) and source of wealth documents.
3. 📞 **FIU Escalation:** File a Suspicious Transaction Report (STR) with the Anti-Money Laundering Office (AMLO/FIU).

#### 5. Direct Answer
Based on the transaction pattern, this account is operating as a **{role}** facilitating illicit funds movement. It is highly recommended to suspend transaction capabilities and perform full identity verification.
"""
        return demo_output
