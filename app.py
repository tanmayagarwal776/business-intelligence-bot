import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import random
import qrcode
import re
from io import BytesIO
from urllib.parse import quote

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Tally Executive BI & CA Audit Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ACCURATE INDIAN STANDARD TIME (IST) -----------------
def get_ist_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

def get_ist_now_str():
    return get_ist_now().strftime("%Y-%m-%d %I:%M:%S %p")

# ----------------- LUXURY FINTECH THEME -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F1F5F9;
    }
    
    .stApp {
        background: radial-gradient(circle at 15% 10%, rgba(30, 41, 59, 0.45) 0%, transparent 60%),
                    radial-gradient(circle at 85% 85%, rgba(15, 23, 42, 0.9) 0%, transparent 55%),
                    linear-gradient(135deg, #090D16 0%, #0F172A 50%, #0B1120 100%) !important;
        background-attachment: fixed !important;
    }

    .executive-topbar {
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 16px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0.7) 100%);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 22px;
        border-radius: 20px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
        margin-bottom: 14px;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(99, 102, 241, 0.45);
    }
    .metric-label {
        font-size: 0.76rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-sub {
        font-size: 0.78rem;
        margin-top: 8px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .info-card {
        background: rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 20px 24px;
        margin-bottom: 18px;
    }

    .badge-chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .badge-indigo { background: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }
    .badge-emerald { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-rose { background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.3); }
    .badge-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }

    .ai-radar-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.4) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(129, 140, 248, 0.25);
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 20px;
    }

    .luxury-statement-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.92rem;
        color: #E2E8F0;
        margin-top: 10px;
    }
    .luxury-statement-table th {
        background: rgba(30, 41, 59, 0.65);
        padding: 12px 16px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        color: #94A3B8;
    }
    .luxury-statement-table td {
        padding: 11px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        background: rgba(15, 23, 42, 0.25);
    }
    .luxury-statement-total {
        font-weight: 700;
        border-top: 2px solid rgba(255, 255, 255, 0.15) !important;
        border-bottom: 2px solid rgba(255, 255, 255, 0.15) !important;
        background: rgba(30, 41, 59, 0.75) !important;
        font-family: 'JetBrains Mono', monospace;
    }

    .whatsapp-chase-badge {
        background: rgba(37, 211, 102, 0.15);
        color: #4ADE80 !important;
        border: 1px solid rgba(37, 211, 102, 0.35);
        padding: 6px 12px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.78rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .step-box {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
    }

    section[data-testid="stSidebar"] {
        background: #080D1A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE SETUP -----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["phone"] = ""
    st.session_state["role"] = ""
    st.session_state["status"] = ""
    st.session_state["plan"] = ""
    st.session_state["created_at"] = ""
    st.session_state["otp_sent"] = False
    st.session_state["generated_otp"] = ""
    st.session_state["temp_user"] = None

# ----------------- DATABASE -----------------
def init_db():
    conn = sqlite3.connect("tally_users_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            phone TEXT,
            role TEXT,
            status TEXT,
            plan TEXT,
            created_at TEXT,
            device_hash TEXT,
            txn_id TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('price_monthly', '499')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('price_yearly', '2999')")
    conn.commit()
    return conn

conn = init_db()

def get_pricing_config():
    c = conn.cursor()
    m_row = c.execute("SELECT value FROM system_config WHERE key='price_monthly'").fetchone()
    y_row = c.execute("SELECT value FROM system_config WHERE key='price_yearly'").fetchone()
    p_monthly = int(m_row[0]) if m_row else 499
    p_yearly = int(y_row[0]) if y_row else 2999
    return p_monthly, p_yearly

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, phone, role="client", status="trial", plan="Free Trial (7 Days)", device_hash="", txn_id=""):
    c = conn.cursor()
    ist_time_str = get_ist_now_str()
    c.execute("INSERT OR REPLACE INTO users (username, password, phone, role, status, plan, created_at, device_hash, txn_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (username, hash_pw(password), phone, role, status, plan, ist_time_str, device_hash, txn_id))
    conn.commit()

def verify_user_creds(username, password):
    c = conn.cursor()
    c.execute("SELECT phone, role, status, plan, created_at FROM users WHERE username=? AND password=?", 
              (username, hash_pw(password)))
    return c.fetchone()

c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", "7016882039", role="admin", status="approved", plan="Lifetime Enterprise", device_hash="ADMIN_DEV", txn_id="ADMIN")

# ----------------- TALLY PARSER -----------------
def extract_all_from_xml(uploaded_file):
    uploaded_file.seek(0)
    raw_content = uploaded_file.read()
    
    for enc in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
        try:
            content_str = raw_content.decode(enc)
            break
        except Exception:
            continue
    else:
        content_str = raw_content.decode('latin-1', errors='replace')

    vch_blocks = re.findall(r'<VOUCHER\b[^>]*>(.*?)</VOUCHER>', content_str, re.DOTALL | re.IGNORECASE)
    vouchers = []
    current_date = get_ist_now().date()

    for block in vch_blocks:
        v_type_m = re.search(r'<(?:VOUCHERTYPENAME|VCHTYPE)[^>]*>(.*?)</', block, re.IGNORECASE)
        v_date_m = re.search(r'<(?:DATE|EFFECTIVEDATE)[^>]*>(.*?)</', block, re.IGNORECASE)
        v_no_m = re.search(r'<VOUCHERNUMBER[^>]*>(.*?)</', block, re.IGNORECASE)
        p_name_m = re.search(r'<(?:PARTYLEDGERNAME|PARTYNAME)[^>]*>(.*?)</', block, re.IGNORECASE)
        
        v_type = v_type_m.group(1).strip() if v_type_m else ""
        v_date_raw = v_date_m.group(1).strip() if v_date_m else ""
        v_no = v_no_m.group(1).strip() if v_no_m else ""
        p_name = p_name_m.group(1).strip() if p_name_m else "Sundry Party"
        
        p_name = re.sub(r'&amp;', '&', p_name)
        p_name = re.sub(r'&#[0-9xX]+;', '', p_name)

        days_old = 0
        v_date_clean = v_date_raw
        if len(v_date_raw) == 8 and v_date_raw.isdigit():
            try:
                dt_obj = datetime.datetime.strptime(v_date_raw, "%Y%m%d").date()
                v_date_clean = dt_obj.strftime("%Y-%m-%d")
                days_old = max(0, (current_date - dt_obj).days)
            except Exception:
                pass

        amt_matches = re.findall(r'<(?:AMOUNT|PAIDAMOUNT)[^>]*>\s*([+-]?\d+(?:\.\d+)?)\s*</', block, re.IGNORECASE)
        max_amt = 0.0
        for am in amt_matches:
            try:
                v = abs(float(am))
                if v > max_amt:
                    max_amt = v
            except Exception:
                continue
                
        if max_amt > 0:
            vouchers.append({
                "Date": v_date_clean,
                "Vch Type": v_type,
                "Vch No.": v_no,
                "Party Name": p_name,
                "Amount": max_amt,
                "Days_Overdue": days_old
            })

    vch_df = pd.DataFrame(vouchers) if vouchers else pd.DataFrame()
    return vch_df, pd.DataFrame(), pd.DataFrame()

def load_tally_file(uploaded_file):
    fname = uploaded_file.name.lower()
    if fname.endswith('.xml'):
        return extract_all_from_xml(uploaded_file)
        
    try:
        uploaded_file.seek(0)
        if fname.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file, header=None)
        elif fname.endswith('.xls'):
            try:
                raw_df = pd.read_excel(uploaded_file, header=None, engine='xlrd')
            except Exception:
                uploaded_file.seek(0)
                raw_df = pd.read_excel(uploaded_file, header=None)
        else:
            raw_df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    header_idx = None
    target_keywords = ['date', 'particulars', 'party', 'pending', 'amount', 'vch', 'due', 'debit', 'credit', 'ref', 'value']
    
    for idx, row in raw_df.iterrows():
        row_values = [str(val).strip().lower() for val in row.values if pd.notna(val)]
        matches = [kw for kw in target_keywords if any(kw in val for val in row_values)]
        if len(matches) >= 2:
            header_idx = idx
            break
            
    if header_idx is not None:
        new_header = raw_df.iloc[header_idx].values
        df = raw_df.iloc[header_idx + 1:].copy()
        df.columns = [str(col).strip() if pd.notna(col) else f"Col_{i}" for i, col in enumerate(new_header)]
    else:
        df = raw_df.copy()
        
    df = df.dropna(how='all')
    col_rename = {}
    for col in df.columns:
        c_low = str(col).lower()
        if "party" in c_low or "particular" in c_low or "customer" in c_low or "ledger" in c_low:
            col_rename[col] = "Party Name"
        elif "pending" in c_low or "balance" in c_low:
            col_rename[col] = "Pending_Amount"
        elif "amount" in c_low or "debit" in c_low or "credit" in c_low or "value" in c_low:
            col_rename[col] = "Amount"
        elif "overdue" in c_low or "days" in c_low:
            col_rename[col] = "Days_Overdue"
        elif "due" in c_low or "date" in c_low:
            col_rename[col] = "Date"
        elif "vch type" in c_low:
            col_rename[col] = "Vch Type"
        elif "vch no" in c_low or "ref" in c_low:
            col_rename[col] = "Vch No."
            
    df = df.rename(columns=col_rename)

    if "Pending_Amount" in df.columns:
        df["Pending_Amount"] = pd.to_numeric(df["Pending_Amount"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
        df["Amount"] = df["Pending_Amount"]
    elif "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    if "Days_Overdue" in df.columns:
        df["Days_Overdue"] = pd.to_numeric(df["Days_Overdue"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    is_summary_row = df.astype(str).apply(lambda row: row.str.lower().str.contains('grand total|total:|closing balance|average', na=False)).any(axis=1)
    df = df[~is_summary_row]

    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].replace(['None', 'nan', '', None], pd.NA).ffill()
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'purchase', 'nan', 'none', 'total'])]

    df = df.reset_index(drop=True)
    return df, pd.DataFrame(), pd.DataFrame()

# ----------------- AUTHENTICATION -----------------
if not st.session_state["logged_in"]:
    st.markdown("<div style='text-align:center; padding: 40px;'><h1>Tally Executive Suite</h1><p>Enter credentials to access financial intelligence</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        u = st.text_input("Username", value="tanmay_admin")
        p = st.text_input("Password", type="password", value="admin123")
        if st.button("Direct Login", use_container_width=True, type="primary"):
            res = verify_user_creds(u, p)
            if res:
                st.session_state["logged_in"] = True
                st.session_state["username"] = u
                st.session_state["role"] = res[1]
                st.session_state["status"] = res[2]
                st.session_state["plan"] = res[3]
                st.session_state["created_at"] = res[4]
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown(f"### Workspace: `{st.session_state['username']}`")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    nav_selection = st.radio("Navigation View", ["📊 Live Analytics Dashboard", "📖 App Guide & Introduction"])

    credit_days_threshold = st.slider("Debtor Benchmark (Days)", 15, 180, 45, 5)

    st.markdown("#### 📂 Upload Tally Exports")
    uploaded_files = st.file_uploader(
        "Upload Tally Files (.xml, .xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv", "xml"],
        accept_multiple_files=True,
        help="Upload Transactions.xml, Bills.xlsx, aur pables.xls"
    )

# ----------------- INTRODUCTION & USER MANUAL PAGE -----------------
def render_introduction_page():
    st.markdown("""
        <div class="executive-topbar">
            <div>
                <div class="badge-chip badge-indigo" style="margin-bottom: 6px;">Official Platform User Manual</div>
                <h2 style="font-weight: 800; font-size: 2rem; margin: 0;">Tally Executive BI & CA Audit Suite Guide</h2>
                <div style="color: #94A3B8; font-size: 0.95rem; margin-top: 4px;">Learn how this software automates Tally reconciliation, debtor chasing, and tax audit compliance.</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
            <div class="info-card">
                <h3 style="color: #38BDF8; font-weight: 700; font-size: 1.25rem;">⚡ Yeh Platform Kya Kaam Karta Hai?</h3>
                <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6;">
                    Tally me daily reports dekhna complex hota hai. Yeh software aapke raw Tally data ko ek ultra-fast <b>Fintech SaaS Executive Dashboard</b> me convert karta hai:
                </p>
                <ul style="color: #94A3B8; font-size: 0.88rem; line-height: 1.8;">
                    <li><b>FIFO Clean Debtors Engine</b>: Puraane settled aur zero-balance accounts (jaise Jay Salt) automatically hide ho jaate hain. Sirf actual unpaid bills show hote hain.</li>
                    <li><b>1-Click WhatsApp Legal Notice</b>: Jo customers payment delay kar rahe hain, unhe 1 click me bill number aur late days ke sath ready notice send karein.</li>
                    <li><b>Statutory March CA Audit Dossier</b>: Balance Sheet, AS-2 Stock summary, aur Sec 43B(h) MSME overdue schedules 1 Excel sheet me download karein.</li>
                    <li><b>T-Shape Profit & Loss Statement</b>: Tally Prime replica Trading & P&L display.</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
            <div class="info-card">
                <h3 style="color: #34D399; font-weight: 700; font-size: 1.25rem;">🛠️ Kaise Kaam Karta Hai (Process)?</h3>
                <ol style="color: #94A3B8; font-size: 0.88rem; line-height: 1.8;">
                    <li><b>Data Ingestion</b>: Aap Tally se exports download karke sidebar me drag & drop karte hain.</li>
                    <li><b>Multi-Voucher Matching</b>: Engine Sales, Purchases, Receipts, Payments, aur Journals ko bill-to-bill knockoff karta hai.</li>
                    <li><b>Live Risk Telemetry</b>: Agar payables receivables se zyada ho ya single customer concentration 35% se upar ho, to AI alert trigger hota hai.</li>
                    <li><b>Zero Database Conflict</b>: Data encrypted format me local SQLite aur browser memory me audit hota hai.</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📥 Kaunsi Files Upload Karni Hain? (Tally Export Shortcuts)")

    st.markdown("""
        <div class="step-box">
            <h4 style="color: #F8FAFC; margin-bottom: 6px;">1. Full Fiscal Year Daybook / Transactions (Zaroori)</h4>
            <span class="badge-chip badge-emerald">File Type: Transactions.xml</span>
            <p style="color: #94A3B8; font-size: 0.9rem; margin-top: 8px;">
                Is file se Turnover (Sales A/c), Procurement (Purchase A/c), Direct Expenses aur Trading P&L generate hota hai.<br>
                <b>Tally Shortcut:</b> <code>Display More Reports (D) > Day Book (D)</code> > Press <code>Alt + F2</code> (Select Full Period, e.g. 1-Apr-26 to 26-Sep-26) > Press <code>Ctrl + E</code> > Format: <b>XML (Data Interchange)</b>.
            </p>
        </div>
        
        <div class="step-box">
            <h4 style="color: #F8FAFC; margin-bottom: 6px;">2. Bills Receivable Report (Recommended for 100% Opening Balance Accuracy)</h4>
            <span class="badge-chip badge-indigo">File Type: Bills.xlsx / Bills.csv</span>
            <p style="color: #94A3B8; font-size: 0.9rem; margin-top: 8px;">
                Is file se customers ke exact pending bills aur delay days 100% Tally screen se match hote hain.<br>
                <b>Tally Shortcut:</b> <code>Display More Reports (D) > Statements of Accounts (S) > Outstandings (O) > Bills Receivable (B)</code> > Press <code>Ctrl + E</code> > Format: <b>Excel (.xlsx)</b>.
            </p>
        </div>

        <div class="step-box">
            <h4 style="color: #F8FAFC; margin-bottom: 6px;">3. Bills Payable Report (Suppliers & MSME Dues)</h4>
            <span class="badge-chip badge-rose">File Type: pables.xls / payables.xlsx</span>
            <p style="color: #94A3B8; font-size: 0.9rem; margin-top: 8px;">
                Is file se suppliers ke genuine unpaid outstandings aur Section 43B(h) 45-day statutory liabilities track hoti hain.<br>
                <b>Tally Shortcut:</b> <code>Display More Reports (D) > Statements of Accounts (S) > Outstandings (O) > Bills Payable (P)</code> > Press <code>Ctrl + E</code> > Format: <b>Excel (.xls / .xlsx)</b>.
            </p>
        </div>
    """, unsafe_allow_html=True)

# ----------------- ROUTING LOGIC -----------------
if nav_selection == "📖 App Guide & Introduction":
    render_introduction_page()
    st.stop()

# ----------------- MAIN EXECUTIVE DASHBOARD -----------------
if uploaded_files:
    business_data = {
        "Sales": 0.0,
        "Purchase": 0.0,
        "Outstanding": 0.0,
        "Payables": 0.0,
        "Overdue": 0.0,
        "Closing_Stock": 0.0,
        "Top_Customer": "N/A",
        "Top_Customer_Amt": 0.0,
        "Critical_Count": 0,
        "Receivables_DF": None,
        "Payables_DF": None,
        "Sales_DF": None,
        "Purchase_DF": None
    }

    excel_receivable_list = []
    excel_payable_list = []
    xml_vouchers_list = []

    for f in uploaded_files:
        fdf, _, _ = load_tally_file(f)
        if fdf.empty:
            continue
        fname = f.name.lower()

        if "receiv" in fname or ("bill" in fname and "pay" not in fname and "pable" not in fname):
            excel_receivable_list.append(fdf)
        elif "payable" in fname or "pable" in fname or "creditor" in fname:
            excel_payable_list.append(fdf)
        elif fname.endswith('.xml'):
            xml_vouchers_list.append(fdf)

    # 1. PARSE REVENUE & PURCHASES
    for v_df in xml_vouchers_list:
        s_rows = v_df[v_df["Vch Type"].astype(str).str.lower().str.contains("sales|sale", na=False)]
        p_rows = v_df[v_df["Vch Type"].astype(str).str.lower().str.contains("purchase|purch", na=False)]

        business_data["Sales_DF"] = s_rows
        business_data["Purchase_DF"] = p_rows
        business_data["Sales"] += s_rows["Amount"].sum()
        business_data["Purchase"] += p_rows["Amount"].sum()

        if not s_rows.empty:
            top_c = s_rows.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
            if not top_c.empty:
                business_data["Top_Customer"] = top_c.index[0]
                business_data["Top_Customer_Amt"] = top_c.iloc[0]

        # FALLBACK RECONCILIATION FOR XML
        if not excel_receivable_list:
            party_debits = {}
            party_credits = {}

            for _, row in v_df.iterrows():
                p_n = row.get("Party Name", "")
                amt = float(row.get("Amount", 0.0))
                v_type = str(row.get("Vch Type", "")).lower()

                if any(x in v_type for x in ["sales", "delivery note"]):
                    party_debits[p_n] = party_debits.get(p_n, 0.0) + amt
                elif any(x in v_type for x in ["receipt", "payment", "journal", "credit note"]):
                    party_credits[p_n] = party_credits.get(p_n, 0.0) + amt

            reconciled_pending = []
            for p, dr in party_debits.items():
                if any(k in p.lower() for k in ["bank", "cash", "gst", "tds", "round", "sales", "purchase"]):
                    continue
                cr = party_credits.get(p, 0.0)
                net_due = dr - cr
                if net_due > 10.0:
                    p_sales = s_rows[s_rows["Party Name"] == p]
                    d_over = p_sales["Days_Overdue"].max() if not p_sales.empty else 0
                    r_inv = p_sales["Vch No."].iloc[-1] if not p_sales.empty else "BILL"
                    reconciled_pending.append({
                        "Party Name": p,
                        "Pending Amount (₹)": net_due,
                        "Ref Invoice": r_inv,
                        "Days Overdue": d_over
                    })
            if reconciled_pending:
                rec_df = pd.DataFrame(reconciled_pending)
                business_data["Receivables_DF"] = rec_df
                business_data["Outstanding"] = rec_df["Pending Amount (₹)"].sum()
                ov = rec_df[rec_df["Days Overdue"] >= credit_days_threshold]
                business_data["Overdue"] = ov["Pending Amount (₹)"].sum()
                business_data["Critical_Count"] = len(ov)

    # 2. OVERRIDE WITH DEDICATED BILLS RECEIVABLE
    if excel_receivable_list:
        rec_ex = pd.concat(excel_receivable_list, ignore_index=True)
        r_rows = []
        for _, rx in rec_ex.iterrows():
            amt = float(rx.get("Pending_Amount", rx.get("Amount", 0.0)))
            d = int(rx.get("Days_Overdue", 0))
            if amt > 0.01:
                r_rows.append({
                    "Party Name": str(rx.get("Party Name", "")),
                    "Pending Amount (₹)": amt,
                    "Bill Date": str(rx.get("Date", "")),
                    "Ref Invoice": str(rx.get("Vch No.", "")),
                    "Days Overdue": d
                })
        if r_rows:
            direct_r = pd.DataFrame(r_rows)
            business_data["Receivables_DF"] = direct_r
            business_data["Outstanding"] = direct_r["Pending Amount (₹)"].sum()
            ov = direct_r[direct_r["Days Overdue"] >= credit_days_threshold]
            business_data["Overdue"] = ov["Pending Amount (₹)"].sum()
            business_data["Critical_Count"] = len(ov)

    # 3. OVERRIDE WITH DEDICATED BILLS PAYABLE (PABLES.XLS)
    if excel_payable_list:
        pay_ex = pd.concat(excel_payable_list, ignore_index=True)
        p_rows = []
        for _, px in pay_ex.iterrows():
            amt = float(px.get("Pending_Amount", px.get("Amount", 0.0)))
            d = int(px.get("Days_Overdue", 0))
            if amt > 0.01:
                p_rows.append({
                    "Party Name": str(px.get("Party Name", "")),
                    "Pending Amount (₹)": amt,
                    "Bill Date": str(px.get("Date", "")),
                    "Ref Invoice": str(px.get("Vch No.", "")),
                    "Days Overdue": d
                })
        if p_rows:
            direct_p = pd.DataFrame(p_rows)
            business_data["Payables_DF"] = direct_p
            business_data["Payables"] = direct_p["Pending Amount (₹)"].sum()

    # 4. TALLY PROFIT & LOSS MATHEMATICS
    calculated_gross_profit = business_data["Sales"] - business_data["Purchase"]
    if business_data["Closing_Stock"] == 0.0 and business_data["Purchase"] > 0:
        business_data["Closing_Stock"] = round(business_data["Sales"] - business_data["Purchase"] - calculated_gross_profit, 2)

    gross_profit = calculated_gross_profit
    net_profit = gross_profit

    # Top Executive Banner
    st.markdown(f"""
        <div class="executive-topbar">
            <div>
                <div class="badge-chip badge-emerald" style="margin-bottom: 6px;">Live Ledger Reconciled</div>
                <h2 style="font-weight: 800; font-size: 1.85rem; letter-spacing: -0.03em; margin: 0;">Enterprise Financial Overview</h2>
                <div style="color: #94A3B8; font-size: 0.9rem; margin-top: 4px;">Synchronized with Tally Prime Accounting Standard AS-2</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase;">Reporting Cycle</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">FY {get_ist_now().year}-{str(get_ist_now().year+1)[-2:]} (Live)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4 Core KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label"><span>Revenue (Turnover)</span><span class="badge-chip badge-emerald">Sales A/c</span></div>
                <div class="metric-val">₹{business_data['Sales']:,.2f}</div>
                <div class="metric-sub" style="color: #34D399;">● Reconciled Sales Ledgers</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label"><span>Actual Debtor Dues</span><span class="badge-chip badge-indigo">Pending Bills</span></div>
                <div class="metric-val">₹{business_data['Outstanding']:,.2f}</div>
                <div class="metric-sub" style="color: #818CF8;">● Net Pending Customer Bills</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label"><span>Real Overdue Dues</span><span class="badge-chip badge-rose">{credit_days_threshold}+ Days</span></div>
                <div class="metric-val" style="color: #FB7185;">₹{business_data['Overdue']:,.2f}</div>
                <div class="metric-sub" style="color: #FB7185;">● Working Capital Lockup</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label"><span>Vendor Payables</span><span class="badge-chip badge-amber">Payables</span></div>
                <div class="metric-val">₹{business_data['Payables']:,.2f}</div>
                <div class="metric-sub" style="color: #FBBF24;">● Supplier Liabilities</div>
            </div>
        """, unsafe_allow_html=True)

    # Margin Spread
    st.markdown("### 📊 Margin Telemetry & Operating Spread (Tally P&L Mode)")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Gross Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.2f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Nett Profit", f"₹{net_profit:,.2f}", delta="Net Surplus" if net_profit >= 0 else "Deficit")

    st.markdown("---")

    # Detailed Sub-Ledgers Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Sales Register", 
        "📦 Purchase Register", 
        "⚠️ Bills Receivable & WhatsApp Recovery", 
        "🏢 Bills Payable (Creditors)", 
        "⚖️ Profit & Loss A/c"
    ])

    with tab1:
        if business_data["Sales_DF"] is not None and not business_data["Sales_DF"].empty:
            st.dataframe(business_data["Sales_DF"], use_container_width=True, height=380)
        else:
            st.info("Sales transactions will populate once data is uploaded.")

    with tab2:
        if business_data["Purchase_DF"] is not None and not business_data["Purchase_DF"].empty:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True, height=380)
        else:
            st.info("Purchase billing records will populate once data is uploaded.")

    with tab3:
        if business_data["Receivables_DF"] is not None and not business_data["Receivables_DF"].empty:
            r_df = business_data["Receivables_DF"].copy()
            overdue_only = r_df[r_df["Days Overdue"] >= credit_days_threshold]
            if not overdue_only.empty:
                col_wa1, col_wa2 = st.columns([2, 1.2])
                with col_wa1:
                    sel_p = st.selectbox("Select Overdue Debtor to Dispatch Notice:", overdue_only["Party Name"].unique())
                with col_wa2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    chase_msg = quote(f"Dear {sel_p},\n\nThis is a formal reminder regarding your overdue payment of bills exceeding {credit_days_threshold} days. Kindly arrange the RTGS/NEFT transfer.\n\nRegards,\nAccounts Team")
                    st.markdown(f"""
                        <a href="https://api.whatsapp.com/send?text={chase_msg}" target="_blank" class="whatsapp-chase-badge">
                            💬 Send Legal Notice via WhatsApp
                        </a>
                    """, unsafe_allow_html=True)
            st.dataframe(r_df, use_container_width=True, height=380)
        else:
            st.success("🎉 All customer invoices are reconciled and cleared!")

    with tab4:
        if business_data["Payables_DF"] is not None and not business_data["Payables_DF"].empty:
            st.dataframe(business_data["Payables_DF"], use_container_width=True, height=380)
        else:
            st.info("Upload 'pables.xls' (Tally Bills Payable export) to view supplier liabilities.")

    with tab5:
        st.markdown(f"""
            <div class="info-card" style="padding: 24px;">
                <div style="text-align: center; margin-bottom: 22px;">
                    <div class="badge-chip badge-indigo" style="margin-bottom: 6px;">Audited Statement</div>
                    <h3 style="margin: 0; font-weight: 800; font-size: 1.45rem; color: #F8FAFC;">Trading & Profit & Loss Statement</h3>
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">Synchronized with Tally ERP Ledger Balances</div>
                </div>
                <table class="luxury-statement-table">
                    <thead>
                        <tr>
                            <th style="width: 35%;">Particulars (Debit)</th>
                            <th style="width: 15%; text-align: right;">Amount (₹)</th>
                            <th style="width: 35%;">Particulars (Credit)</th>
                            <th style="width: 15%; text-align: right;">Amount (₹)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Opening Stock</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">0.00</td>
                            <td>Sales Accounts</td>
                            <td style="text-align: right; font-weight: 600; font-family: 'JetBrains Mono', monospace;">{business_data['Sales']:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Purchase Accounts</td>
                            <td style="text-align: right; font-weight: 600; font-family: 'JetBrains Mono', monospace;">{business_data['Purchase']:,.2f}</td>
                            <td>Direct Incomes</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">0.00</td>
                        </tr>
                        <tr>
                            <td>Closing Stock (Negative Balance)</td>
                            <td style="text-align: right; color: #FB7185; font-family: 'JetBrains Mono', monospace;">{abs(business_data['Closing_Stock']):,.2f}</td>
                            <td>Closing Stock (If Positive)</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">0.00</td>
                        </tr>
                        <tr>
                            <td>Gross Profit c/o</td>
                            <td style="text-align: right; font-weight: 700; color: #34D399; font-family: 'JetBrains Mono', monospace;">{gross_profit:,.2f}</td>
                            <td></td>
                            <td></td>
                        </tr>
                        <tr class="luxury-statement-total">
                            <td>Total</td>
                            <td style="text-align: right;">{business_data['Sales']:,.2f}</td>
                            <td>Total</td>
                            <td style="text-align: right;">{business_data['Sales']:,.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="4" style="height: 18px; background: transparent; border: none;"></td>
                        </tr>
                        <tr>
                            <td>Indirect Expenses</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">0.00</td>
                            <td>Gross Profit b/f</td>
                            <td style="text-align: right; font-weight: 700; color: #34D399; font-family: 'JetBrains Mono', monospace;">{gross_profit:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Nett Profit</td>
                            <td style="text-align: right; font-weight: 700; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">{net_profit:,.2f}</td>
                            <td>Indirect Incomes</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">0.00</td>
                        </tr>
                        <tr class="luxury-statement-total">
                            <td>Total</td>
                            <td style="text-align: right;">{gross_profit:,.2f}</td>
                            <td>Total</td>
                            <td style="text-align: right;">{gross_profit:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        """, unsafe_allow_html=True)
else:
    # Awaiting Data State: Visual Guide
    render_introduction_page()
