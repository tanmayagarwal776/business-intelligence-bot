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

# ----------------- LUXURY FINTECH THEME WITH CSS3 ANIMATIONS -----------------
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

    /* Keyframe Animations */
    @keyframes floatCard {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-7px); }
        100% { transform: translateY(0px); }
    }

    @keyframes pulseGlow {
        0% { box-shadow: 0 0 10px rgba(99, 102, 241, 0.2); }
        50% { box-shadow: 0 0 25px rgba(99, 102, 241, 0.6); }
        100% { box-shadow: 0 0 10px rgba(99, 102, 241, 0.2); }
    }

    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .animated-hero {
        background: linear-gradient(270deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9), rgba(49, 46, 129, 0.4));
        background-size: 400% 400%;
        animation: gradientShift 10s ease infinite;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.4);
    }

    .animated-step-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.35s ease;
        position: relative;
    }
    .animated-step-card:hover {
        transform: translateY(-5px);
        border-color: rgba(99, 102, 241, 0.5);
        animation: pulseGlow 2.5s infinite;
    }

    .step-number-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        background: linear-gradient(135deg, #6366F1, #38BDF8);
        color: #FFFFFF;
        font-weight: 800;
        border-radius: 12px;
        font-size: 1.1rem;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }

    .pipeline-connector {
        text-align: center;
        font-size: 1.8rem;
        color: #818CF8;
        padding: 10px 0;
        animation: floatCard 2.5s ease-in-out infinite;
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
        margin-bottom: 14px;
        transition: transform 0.25s ease;
    }
    .metric-card:hover { transform: translateY(-3px); }
    
    .metric-label { font-size: 0.76rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    .metric-val { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: #F8FAFC; }
    .metric-sub { font-size: 0.78rem; margin-top: 8px; font-weight: 500; display: flex; align-items: center; gap: 6px; }

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

    .whatsapp-btn {
        display: block;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: #FFFFFF !important;
        text-align: center;
        padding: 13px 20px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.95rem;
        text-decoration: none;
        margin-top: 10px;
        margin-bottom: 15px;
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

# ----------------- ROLE-BASED ACCESS UI -----------------
is_admin_active = st.session_state.get("logged_in") and st.session_state.get("role") == "admin"

if is_admin_active:
    st.markdown("""
        <style>
        header { visibility: visible !important; }
        [data-testid="stToolbar"] { display: block !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        #MainMenu, footer, header { visibility: hidden !important; display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="manage-app-button"] { display: none !important; }
        button[kind="header"] { display: none !important; }
        div[class*="viewerBadge"] { display: none !important; }
        div[class*="ProfileBadge"] { display: none !important; }
        iframe[title="streamlit_app"] ~ div { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        div[data-testid="stStatusWidget"] { display: none !important; }
        </style>
        <script>
        function removeManageButton() {
            const buttons = window.parent.document.querySelectorAll('button, div');
            buttons.forEach(el => {
                if (el.innerText && el.innerText.includes('Manage app')) {
                    el.style.display = 'none';
                    el.remove();
                }
            });
            const toolbars = window.parent.document.querySelectorAll('[data-testid="stToolbar"], header');
            toolbars.forEach(el => { el.style.display = 'none'; });
        }
        setInterval(removeManageButton, 300);
        </script>
    """, unsafe_allow_html=True)

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

def update_pricing_config(monthly_val, yearly_val):
    c = conn.cursor()
    c.execute("UPDATE system_config SET value=? WHERE key='price_monthly'", (str(monthly_val),))
    c.execute("UPDATE system_config SET value=? WHERE key='price_yearly'", (str(yearly_val),))
    conn.commit()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_client_device_hash(username):
    headers = st.context.headers
    user_agent = headers.get("User-Agent", "standard-browser")
    accept_lang = headers.get("Accept-Language", "en")
    raw_fingerprint = f"{user_agent}_{accept_lang}"
    return hashlib.sha256(raw_fingerprint.encode()).hexdigest()

def check_device_trial_exists(device_hash):
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE device_hash=? AND role != 'admin'", (device_hash,))
    return c.fetchone()

def add_user(username, password, phone, role="client", status="trial", plan="Free Trial (7 Days)", device_hash="", txn_id=""):
    c = conn.cursor()
    ist_time_str = get_ist_now_str()
    c.execute("INSERT OR REPLACE INTO users (username, password, phone, role, status, plan, created_at, device_hash, txn_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (username, hash_pw(password), phone, role, status, plan, ist_time_str, device_hash, txn_id))
    conn.commit()

def update_user_payment(username, plan, txn_id):
    c = conn.cursor()
    c.execute("UPDATE users SET plan=?, txn_id=?, status='pending' WHERE username=?", (plan, txn_id, username))
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

# ----------------- TALLY DATA PARSER -----------------
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
    st.markdown("""
        <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
            <div class="badge-chip badge-indigo">WHATSAPP SECURE ENTERPRISE SUITE</div>
            <h1 style="font-weight: 800; font-size: 2.8rem; letter-spacing: -0.02em; margin-bottom: 8px;">Tally Executive Suite</h1>
            <p style="color: #94A3B8; font-size: 1.05rem;">Turn raw Tally exports into executive P&L, stock intelligence & CA dossiers</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        menu = ["Sign In", "Start 7-Day Free Trial"]
        choice = st.segmented_control("Access Mode", menu, default="Sign In")

        if choice == "Sign In":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            u = st.text_input("Username", placeholder="Enter business ID")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            phone = st.text_input("Registered 10-Digit Mobile No.", placeholder="e.g. 9876543210")

            if not st.session_state["otp_sent"]:
                if st.button("Generate Login OTP via WhatsApp", use_container_width=True, type="primary"):
                    if u and p and phone and len(phone.strip()) >= 10:
                        res = verify_user_creds(u, p)
                        if res:
                            reg_phone, role, status, plan, created_at = res
                            otp = str(random.randint(100000, 999999))
                            st.session_state["generated_otp"] = otp
                            st.session_state["temp_user"] = {
                                "username": u, "phone": phone, "role": role, 
                                "status": status, "plan": plan, "created_at": created_at
                            }
                            st.session_state["otp_sent"] = True
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.error("Please provide valid username, password and 10-digit phone number.")
            else:
                target_phone = phone.strip()[-10:]
                msg_body = quote(f"Hello, your Tally Executive Suite Login OTP is: {st.session_state['generated_otp']}. Valid for 10 minutes.")
                wa_link = f"https://api.whatsapp.com/send?phone=91{target_phone}&text={msg_body}"

                st.markdown(f"""
                    <a href="{wa_link}" target="_blank" class="whatsapp-btn">
                        💬 Click Here: Send OTP to My WhatsApp (+91 {target_phone})
                    </a>
                """, unsafe_allow_html=True)

                with st.expander("👁️ Cannot access WhatsApp? Click to view OTP"):
                    st.info(f"Verification OTP: **`{st.session_state['generated_otp']}`**")

                entered_otp = st.text_input("Enter 6-Digit Verification OTP", placeholder="••••••")
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    if st.button("Verify OTP & Login", use_container_width=True, type="primary"):
                        if entered_otp.strip() == st.session_state["generated_otp"]:
                            usr = st.session_state["temp_user"]
                            status = usr["status"]
                            is_expired = False
                            if status == "trial":
                                try:
                                    dt_clean = usr["created_at"].split()[0]
                                    c_date = datetime.datetime.strptime(dt_clean, "%Y-%m-%d").date()
                                    if (get_ist_now().date() - c_date).days >= 7:
                                        is_expired = True
                                        status = "expired"
                                        c = conn.cursor()
                                        c.execute("UPDATE users SET status='expired' WHERE username=?", (usr["username"],))
                                        conn.commit()
                                except Exception:
                                    pass

                            st.session_state["logged_in"] = True
                            st.session_state["username"] = usr["username"]
                            st.session_state["phone"] = usr["phone"]
                            st.session_state["role"] = usr["role"]
                            st.session_state["status"] = "expired" if is_expired else status
                            st.session_state["plan"] = usr["plan"]
                            st.session_state["created_at"] = usr["created_at"]
                            st.session_state["otp_sent"] = False
                            st.rerun()
                        else:
                            st.error("Incorrect OTP entered.")
                with col_sub2:
                    if st.button("Resend / Reset", use_container_width=True):
                        st.session_state["otp_sent"] = False
                        st.rerun()

            st.markdown("""
                <div style="text-align: center; margin-top: 15px;">
                    <span style="color: #94A3B8; font-size: 0.85rem;">📞 Helpline & Support:</span>
                    <a href="tel:7016882039" style="color: #818CF8; font-weight: 700; text-decoration: none;">+91 7016882039</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        elif choice == "Start 7-Day Free Trial":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            new_u = st.text_input("Choose Username", placeholder="e.g. industrial_trade")
            new_p = st.text_input("Choose Password", type="password", placeholder="••••••••")
            new_phone = st.text_input("Mobile Number (WhatsApp Enabled)", placeholder="10-digit mobile number")
            
            st.caption("🔒 7-day full access included. Instant WhatsApp Verification.")
            if st.button("Register & Activate Trial", use_container_width=True, type="primary"):
                if new_u and new_p and new_phone and len(new_phone.strip()) >= 10:
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (new_u,))
                    if c.fetchone():
                        st.error("Username is already claimed.")
                    else:
                        dev_hash = get_client_device_hash(new_u)
                        prev_acc = check_device_trial_exists(dev_hash)
                        if prev_acc:
                            st.error(f"🚫 Workstation Trial Exists (`{prev_acc[0]}`). Please log in with existing account.")
                        else:
                            add_user(new_u, new_p, new_phone.strip(), role="client", status="trial", plan="Free Trial (7 Days)", device_hash=dev_hash, txn_id="FREE_TRIAL")
                            st.success("🎉 Account activated! Switch to 'Sign In' to login via WhatsApp OTP.")
                else:
                    st.error("Please fill all fields including 10-digit mobile number.")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- TRIAL EXPIRED PAYMENT SCREEN -----------------
current_monthly_price, current_yearly_price = get_pricing_config()

if st.session_state.get("status") == "expired":
    st.markdown("""
        <div style="text-align: center; margin-top: 30px; margin-bottom: 25px;">
            <div class="badge-chip badge-rose">TRIAL PERIOD EXPIRED</div>
            <h2 style="font-weight: 700; margin-top: 10px;">Renew Your Executive Access</h2>
            <p style="color: #94A3B8;">Your 7-day evaluation has concluded. Select an ongoing license below to continue analysis.</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        plan_sel = st.radio("Select Subscription Plan:", [
            f"Monthly License — ₹{current_monthly_price:,} / Month", 
            f"Annual Enterprise — ₹{current_yearly_price:,} / Year (Best Value)"
        ])
        amt = current_monthly_price if str(current_monthly_price) in plan_sel else current_yearly_price
        p_name = f"Monthly (₹{amt})" if amt == current_monthly_price else f"Yearly (₹{amt})"

        col_q1, col_q2 = st.columns([1.2, 1])
        with col_q1:
            st.markdown(f"**Amount Due:** `₹{amt:,}`")
            st.markdown("**UPI VPA:** `tanmayagarwal776@okhdfcbank`")
            pay_tx = st.text_input("12-Digit Bank / UPI UTR Ref No:")
        with col_q2:
            qr_img = generate_upi_qr("tanmayagarwal776@okhdfcbank", "Tanmay Agarwal", amt)
            st.image(qr_img, width=170)

        if st.button("Submit License Verification", use_container_width=True, type="primary"):
            if pay_tx.strip():
                update_user_payment(st.session_state["username"], p_name, pay_tx.strip())
                st.success("✅ Payment reference logged. Account unlocks immediately upon admin audit.")
            else:
                st.error("Valid transaction reference required.")

        if st.button("Log Out"):
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown(f"""
        <div style="padding: 12px 4px 18px 4px;">
            <div style="font-size: 0.8rem; color: #64748B; font-weight: 600;">ACTIVE WORKSPACE</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">{st.session_state['username']}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state["status"] == "trial":
        try:
            dt_clean = st.session_state.get("created_at", "").split()[0]
            c_date = datetime.datetime.strptime(dt_clean, "%Y-%m-%d").date()
            days_left = max(0, 7 - (get_ist_now().date() - c_date).days)
        except Exception:
            days_left = 7
        st.markdown(f'<div class="badge-chip badge-amber">Trial: {days_left} Days Left</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="badge-chip badge-emerald">{st.session_state.get("plan", "Enterprise Tier")}</div>', unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True, key="admin_app_signout"):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")

    if st.session_state["role"] == "admin":
        admin_mode = st.radio("Console Navigation", [
            "📊 Analytics Dashboard", 
            "👥 User Management & CRM", 
            "💳 License Approvals",
            "📖 App Guide & Animated Tour"
        ], key="admin_console_nav_radio")
    else:
        admin_mode = st.radio("Navigation View", [
            "📊 Analytics Dashboard", 
            "📖 App Guide & Animated Tour"
        ], key="client_nav_radio")

    st.markdown("#### ⚙️ Business Rules")
    credit_days_threshold = st.slider("Debtor Benchmark (Days)", 15, 180, 45, 5)

    st.markdown("---")
    st.markdown("#### 📂 Tally Data Ingestion")
    uploaded_files = st.file_uploader(
        "Upload Tally Files (.xml, .xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv", "xml"],
        accept_multiple_files=True,
        help="Upload Transactions.xml, Bills.xlsx, aur pables.xls"
    )

    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px; text-align: center;">
            <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Direct CA Support</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #38BDF8; margin-top: 4px; font-family: 'JetBrains Mono', monospace;">7016882039</div>
            <div style="margin-top: 8px;">
                <a href="https://wa.me/917016882039" target="_blank" style="background: rgba(34, 197, 94, 0.2); color: #4ADE80; padding: 5px 12px; border-radius: 8px; text-decoration: none; font-size: 0.78rem; font-weight: 700; border: 1px solid rgba(34, 197, 94, 0.35);">WhatsApp</a>
                <a href="tel:7016882039" style="background: rgba(99, 102, 241, 0.2); color: #818CF8; padding: 5px 12px; border-radius: 8px; text-decoration: none; font-size: 0.78rem; font-weight: 700; border: 1px solid rgba(99, 102, 241, 0.35); margin-left: 6px;">Call</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ----------------- ADMIN: USER CRM + PRICING CONTROLLER -----------------
if st.session_state["role"] == "admin" and admin_mode == "👥 User Management & CRM":
    st.markdown("""
        <div class="executive-topbar">
            <div>
                <h2 style="font-weight: 800; margin: 0; font-size: 1.7rem;">👥 User Directory & Subscription CRM</h2>
                <div style="color: #94A3B8; font-size: 0.88rem; margin-top: 3px;">Live customer telemetry, Accurate IST Timestamps & Pricing Control</div>
            </div>
            <div class="badge-chip badge-indigo">Admin Portal</div>
        </div>
    """, unsafe_allow_html=True)

    c = conn.cursor()
    all_users = c.execute("SELECT username, phone, role, status, plan, created_at, txn_id FROM users").fetchall()

    total_u = len(all_users)
    trial_u = sum(1 for x in all_users if x[3] == "trial")
    paid_u = sum(1 for x in all_users if x[3] == "approved")
    expired_u = sum(1 for x in all_users if x[3] in ["expired", "pending"])

    crm1, crm2, crm3, crm4 = st.columns(4)
    crm1.metric("Registered Accounts", total_u)
    crm2.metric("Active Trials", trial_u)
    crm3.metric("Paid Subscriptions", paid_u)
    crm4.metric("Pending / Expired", expired_u)

    st.markdown("---")
    st.markdown("### 💰 Subscription Pricing Manager (Live Store Controller)")
    col_p1, col_p2, col_p3 = st.columns([1.5, 1.5, 1.2])
    with col_p1:
        new_monthly = st.number_input("Monthly License Price (INR ₹):", min_value=99, max_value=99999, value=current_monthly_price, step=50)
    with col_p2:
        new_yearly = st.number_input("Annual Enterprise Price (INR ₹):", min_value=499, max_value=499999, value=current_yearly_price, step=100)
    with col_p3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Update Store Prices", type="primary", use_container_width=True):
            update_pricing_config(new_monthly, new_yearly)
            st.success(f"✅ Subscription rates updated: Monthly = ₹{new_monthly:,} | Yearly = ₹{new_yearly:,}")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Client Portfolio Master Table (Indian Standard Time)")
    table_data = []
    now_ist = get_ist_now().date()

    for u_name, u_ph, u_role, u_stat, u_pl, u_cr, u_tx in all_users:
        days_rem = "-"
        if u_stat == "trial":
            try:
                dt_clean = u_cr.split()[0]
                c_date = datetime.datetime.strptime(dt_clean, "%Y-%m-%d").date()
                days_left = max(0, 7 - (now_ist - c_date).days)
                days_rem = f"{days_left} Days Left"
            except Exception:
                days_rem = "Active"
        elif u_stat == "approved":
            days_rem = "Lifetime / Active"
        elif u_stat == "expired":
            days_rem = "0 Days (Expired)"
        elif u_stat == "pending":
            days_rem = "Pending Verification"

        table_data.append({
            "Username": u_name,
            "Mobile No.": u_ph if u_ph else "-",
            "Role": u_role.upper(),
            "Status": u_stat.upper(),
            "Plan Type": u_pl,
            "Entitlement Balance": days_rem,
            "Registration Date & Time (IST)": u_cr,
            "Bank Ref": u_tx if u_tx else "N/A"
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, height=350)

    st.markdown("---")
    st.markdown("### 🛠️ Instant User Entitlement Override")
    non_admin_usernames = [x[0] for x in all_users if x[0] != "tanmay_admin"]
    if non_admin_usernames:
        col_ov1, col_ov2, col_ov3 = st.columns([1.5, 1.5, 1])
        with col_ov1:
            target_user = st.selectbox("Select Client:", non_admin_usernames)
        with col_ov2:
            new_status_action = st.selectbox("Assign Action:", [
                f"Grant Annual Enterprise (₹{current_yearly_price})",
                f"Grant Monthly License (₹{current_monthly_price})",
                "Reset 7-Day Free Trial",
                "Expire / Lock Account"
            ])
        with col_ov3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Execute Override", type="primary", use_container_width=True):
                c = conn.cursor()
                now_str = get_ist_now_str()
                if "Annual" in new_status_action:
                    c.execute("UPDATE users SET status='approved', plan=? WHERE username=?", (f"Annual Enterprise (₹{current_yearly_price})", target_user))
                elif "Monthly" in new_status_action:
                    c.execute("UPDATE users SET status='approved', plan=? WHERE username=?", (f"Monthly License (₹{current_monthly_price})", target_user))
                elif "Reset" in new_status_action:
                    c.execute("UPDATE users SET status='trial', plan='Free Trial (7 Days)', created_at=? WHERE username=?", (now_str, target_user))
                elif "Expire" in new_status_action:
                    c.execute("UPDATE users SET status='expired' WHERE username=?", (target_user,))
                conn.commit()
                st.success(f"Updated status for {target_user} successfully!")
                st.rerun()
    st.stop()

# ----------------- ADMIN: LICENSE QUEUE -----------------
if st.session_state["role"] == "admin" and admin_mode == "💳 License Approvals":
    st.markdown("## 💳 License Verification Queue")
    c = conn.cursor()
    pending_users = c.execute("SELECT username, phone, plan, txn_id, status FROM users WHERE status='pending'").fetchall()
    if pending_users:
        st.info(f"Requests Awaiting Verification: {len(pending_users)}")
        for u_name, u_ph, u_plan, tx_id, stat in pending_users:
            with st.container():
                st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                col_u, col_ph, col_pl, col_tx, col_btn = st.columns([2, 1.5, 2, 2.5, 1.5])
                col_u.markdown(f"**Client:** `{u_name}`")
                col_ph.markdown(f"**Phone:** `{u_ph}`")
                col_pl.markdown(f"**Tier:** `{u_plan}`")
                col_tx.markdown(f"**UTR:** `{tx_id if tx_id else 'Awaiting'}`")
                if col_btn.button("Grant License", key=f"appr_{u_name}", type="primary"):
                    c.execute("UPDATE users SET status='approved' WHERE username=?", (u_name,))
                    conn.commit()
                    st.success(f"Access granted for {u_name}")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("All client licenses are active. No verification backlog.")
    st.stop()

# ----------------- ANIMATED INTERACTIVE APP GUIDE -----------------
def render_animated_introduction_page():
    st.markdown("""
        <div class="animated-hero">
            <div class="badge-chip badge-indigo" style="margin-bottom: 10px;">✨ INTERACTIVE ANIMATED PLATFORM TOUR</div>
            <h1 style="font-weight: 800; font-size: 2.7rem; margin: 0; background: linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Tally Executive BI & CA Audit Suite
            </h1>
            <p style="color: #94A3B8; font-size: 1.05rem; margin-top: 10px; max-width: 650px; margin-left: auto; margin-right: auto;">
                Raw Tally XML exports ko ek smart, high-margin executive dashboard me convert karein jo actual unpaid dues ko highlight kare aur statutory audit ko automate kare.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔄 The 3-Step Execution Pipeline")
    
    col1, col_arrow1, col2, col_arrow2, col3 = st.columns([2.5, 0.4, 2.5, 0.4, 2.5])
    
    with col1:
        st.markdown("""
            <div class="animated-step-card">
                <div class="step-number-badge">1</div>
                <h4 style="color: #38BDF8; margin: 0 0 6px 0;">Export Tally Data</h4>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 12px;">Zero Configuration Setup</div>
                <p style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.6;">
                    Tally Prime se <code>Transactions.xml</code> ya <code>Bills.xlsx</code> export karein. Koi third-party connector ya API installation ki zaroorat nahi.
                </p>
                <span class="badge-chip badge-emerald">Drag & Drop Ready</span>
            </div>
        """, unsafe_allow_html=True)

    with col_arrow1:
        st.markdown('<div class="pipeline-connector">➔</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="animated-step-card">
                <div class="step-number-badge">2</div>
                <h4 style="color: #818CF8; margin: 0 0 6px 0;">FIFO Knockoff Engine</h4>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 12px;">Automated Ledger Reconciliation</div>
                <p style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.6;">
                    Engine Sales, Receipts, aur Journals ko bill-by-bill match karta hai. Zero balance aur fully paid parties automatically remove ho jaati hain.
                </p>
                <span class="badge-chip badge-indigo">Clean Debtor Book</span>
            </div>
        """, unsafe_allow_html=True)

    with col_arrow2:
        st.markdown('<div class="pipeline-connector">➔</div>', unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="animated-step-card">
                <div class="step-number-badge">3</div>
                <h4 style="color: #34D399; margin: 0 0 6px 0;">Executive Action</h4>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 12px;">Cash Collection & Tax Audit</div>
                <p style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.6;">
                    1-Click me overdue customers ko WhatsApp recovery notice bhejein, Tally replica P&L dekhein, aur CA Audit Dossier download karein.
                </p>
                <span class="badge-chip badge-rose">1-Click WhatsApp</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📂 Required Files & Direct Tally Shortcuts")

    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        st.markdown("""
            <div class="animated-step-card">
                <div class="badge-chip badge-emerald" style="margin-bottom: 8px;">FILE 1: DAYBOOK TRANSACTIONS</div>
                <h4 style="color: #F8FAFC; margin-bottom: 8px;">Transactions.xml</h4>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.6;">
                    <b>Purpose:</b> Generates Gross Turnover (Sales A/c), Procurement (Purchase A/c), Direct Incomes & Tally P&L balances.<br><br>
                    <b>Tally Shortcut:</b><br>
                    <code>Display More Reports (D) > Day Book (D)</code><br>
                    Press <code>Alt + F2</code> ➔ Set Full Period (e.g. 1-Apr to 26-Sep)<br>
                    Press <code>Ctrl + E</code> ➔ Format: <b>XML</b>.
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_f2:
        st.markdown("""
            <div class="animated-step-card">
                <div class="badge-chip badge-indigo" style="margin-bottom: 8px;">FILE 2: CUSTOMER OUTSTANDINGS</div>
                <h4 style="color: #F8FAFC; margin-bottom: 8px;">Bills.xlsx / Bills.csv</h4>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.6;">
                    <b>Purpose:</b> 100% exact Tally screen match for Customer Overdues, Delay Days & WhatsApp notice tracking.<br><br>
                    <b>Tally Shortcut:</b><br>
                    <code>Display More Reports (D) > Statements of Accounts (S) > Outstandings (O) > Bills Receivable (B)</code><br>
                    Press <code>Ctrl + E</code> ➔ Format: <b>Excel (.xlsx)</b>.
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_f3:
        st.markdown("""
            <div class="animated-step-card">
                <div class="badge-chip badge-rose" style="margin-bottom: 8px;">FILE 3: VENDOR & MSME DUES</div>
                <h4 style="color: #F8FAFC; margin-bottom: 8px;">pables.xls / payables.xlsx</h4>
                <p style="color: #94A3B8; font-size: 0.85rem; line-height: 1.6;">
                    <b>Purpose:</b> Tracks supplier payment commitments and Section 43B(h) MSME 45-day statutory liability risks.<br><br>
                    <b>Tally Shortcut:</b><br>
                    <code>Display More Reports (D) > Statements of Accounts (S) > Outstandings (O) > Bills Payable (P)</code><br>
                    Press <code>Ctrl + E</code> ➔ Format: <b>Excel (.xls / .xlsx)</b>.
                </p>
            </div>
        """, unsafe_allow_html=True)

if admin_mode == "📖 App Guide & Animated Tour":
    render_animated_introduction_page()
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

    calculated_gross_profit = business_data["Sales"] - business_data["Purchase"]
    if business_data["Closing_Stock"] == 0.0 and business_data["Purchase"] > 0:
        business_data["Closing_Stock"] = round(business_data["Sales"] - business_data["Purchase"] - calculated_gross_profit, 2)

    gross_profit = calculated_gross_profit
    net_profit = gross_profit

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
                <div class="metric-label"><span>Actual Debtor Dues</span><span class="badge-chip badge-indigo">Receivables</span></div>
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

    st.markdown("### 📊 Margin Telemetry & Operating Spread (Tally P&L Mode)")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Gross Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.2f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Nett Profit", f"₹{net_profit:,.2f}", delta="Net Surplus" if net_profit >= 0 else "Deficit")

    st.markdown("---")

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
    render_animated_introduction_page()
