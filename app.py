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

# ----------------- ACCURATE INDIAN STANDARD TIME (IST) HELPER -----------------
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
        -webkit-backdrop-filter: blur(16px);
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

    .whatsapp-btn {
        display: inline-block;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: #FFFFFF !important;
        text-align: center;
        padding: 13px 20px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.95rem;
        text-decoration: none;
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
    .whatsapp-chase-badge:hover {
        background: rgba(37, 211, 102, 0.25);
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
    add_user("tanmay_admin", "admin123", "7016882039", role="admin", status="approved", plan="Lifetime Enterprise", device_hash="ADMIN_DEV", txn_id="ADMIN")[cite: 14]

# ----------------- TRUE TALLY INVENTORY & RECONCILED LEDGER ENGINE -----------------
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
    item_stats = {}
    expense_records = []
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

        is_purchase = any(x in v_type.lower() for x in ["purchase", "receipt note"])
        is_sale = any(x in v_type.lower() for x in ["sale", "delivery note"])

        inv_blocks = re.findall(r'<ALLINVENTORYENTRIES\.LIST\b[^>]*>(.*?)</ALLINVENTORYENTRIES\.LIST>', block, re.DOTALL | re.IGNORECASE)
        for ib in inv_blocks:
            item_name_m = re.search(r'<STOCKITEMNAME[^>]*>(.*?)</', ib, re.IGNORECASE)
            rate_m = re.search(r'<RATE[^>]*>(.*?)</', ib, re.IGNORECASE)
            qty_m = re.search(r'<(?:BILLEDQTY|ACTUALQTY)[^>]*>(.*?)</', ib, re.IGNORECASE)
            amt_m = re.search(r'<AMOUNT[^>]*>\s*([+-]?\d+(?:\.\d+)?)\s*</', ib, re.IGNORECASE)
            
            if item_name_m:
                it_name = item_name_m.group(1).strip()
                it_name = re.sub(r'&amp;', '&', it_name)
                it_name = re.sub(r'&#[0-9xX]+;', '', it_name)
                it_amt = abs(float(amt_m.group(1))) if amt_m else 0.0
                
                raw_qty_str = qty_m.group(1).strip() if qty_m else "0"
                qty_val_m = re.search(r'([+-]?\d+(?:\.\d+)?)', raw_qty_str)
                num_qty = abs(float(qty_val_m.group(1))) if qty_val_m else 0.0
                unit_str = re.sub(r'[0-9\.\+\-\s]', '', raw_qty_str) or "bag"

                raw_rate_str = rate_m.group(1).strip() if rate_m else "0"
                rate_val_m = re.search(r'([+-]?\d+(?:\.\d+)?)', raw_rate_str)
                num_rate = float(rate_val_m.group(1)) if rate_val_m else (it_amt / num_qty if num_qty != 0 else 0.0)

                if it_name not in item_stats:
                    item_stats[it_name] = {
                        "purch_qty": 0.0,
                        "purch_val": 0.0,
                        "sales_qty": 0.0,
                        "unit": unit_str,
                        "fallback_rate": num_rate
                    }

                if is_purchase:
                    item_stats[it_name]["purch_qty"] += num_qty
                    item_stats[it_name]["purch_val"] += it_amt
                    if num_rate > 0:
                        item_stats[it_name]["fallback_rate"] = num_rate
                elif is_sale:
                    item_stats[it_name]["sales_qty"] += num_qty
                else:
                    item_stats[it_name]["purch_qty"] += num_qty
                    item_stats[it_name]["purch_val"] += it_amt

        led_blocks = re.findall(r'<ALLLEDGERENTRIES\.LIST\b[^>]*>(.*?)</ALLLEDGERENTRIES\.LIST>', block, re.DOTALL | re.IGNORECASE)
        for lb in led_blocks:
            led_name_m = re.search(r'<LEDGERNAME[^>]*>(.*?)</', lb, re.IGNORECASE)
            led_amt_m = re.search(r'<AMOUNT[^>]*>\s*([+-]?\d+(?:\.\d+)?)\s*</', lb, re.IGNORECASE)
            if led_name_m and led_amt_m:
                lname = led_name_m.group(1).strip()
                lamt = abs(float(led_amt_m.group(1)))
                l_low = lname.lower()
                if any(k in l_low for k in ["freight", "cartage", "carriage", "wages", "salary", "rent", "interest", "commission", "discount", "office", "expense", "audit", "electric", "telephone", "fuel"]):
                    expense_records.append({
                        "Date": v_date_clean,
                        "Particulars": lname,
                        "Vch Type": v_type,
                        "Vch No.": v_no,
                        "Amount": lamt
                    })

    stock_summary_rows = []
    for it_k, it_v in item_stats.items():
        net_qty = it_v["purch_qty"] - it_v["sales_qty"]
        if it_v["purch_qty"] > 0 and it_v["purch_val"] > 0:
            valuation_rate = it_v["purch_val"] / it_v["purch_qty"]
        else:
            valuation_rate = it_v["fallback_rate"]

        closing_val = round(net_qty * valuation_rate, 2)
        if abs(net_qty) > 0.001 or abs(closing_val) > 0.001:
            stock_summary_rows.append({
                "Particulars (Stock Item)": it_k,
                "Closing Quantity": f"{net_qty:,.0f} {it_v['unit']}",
                "Valuation Rate": f"₹{valuation_rate:,.2f}",
                "Closing Value": closing_val
            })

    vch_df = pd.DataFrame(vouchers) if vouchers else pd.DataFrame()
    stk_df = pd.DataFrame(stock_summary_rows) if stock_summary_rows else pd.DataFrame()
    exp_df = pd.DataFrame(expense_records) if expense_records else pd.DataFrame()
    return vch_df, stk_df, exp_df

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
    target_keywords = ['date', 'particulars', 'party', 'pending', 'amount', 'vch', 'due', 'debit', 'credit', 'month', 'july', 'stock', 'balance', 'closing', 'ref', 'value']
    
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
    if not df.empty:
        first_row_vals = [str(v).lower() for v in df.iloc[0].values]
        if any(v in ['amount', 'by days', 'dr', 'cr'] for v in first_row_vals):
            df = df.iloc[1:]
            
    col_rename = {}
    for col in df.columns:
        c_low = str(col).lower()
        if "party" in c_low or "particular" in c_low or "customer" in c_low or "ledger" in c_low or "item" in c_low:
            col_rename[col] = "Party Name"
        elif "pending" in c_low or "amount" in c_low or "balance" in c_low or "debit" in c_low or "credit" in c_low or "value" in c_low:
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
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f"{dup}_{i}" for i in range(sum(cols == dup))]
    df.columns = cols

    amt_cols = [c for c in df.columns if str(c).startswith("Amount")]
    for ac in amt_cols:
        df[ac] = pd.to_numeric(df[ac].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    if "Amount_1" in df.columns:
        if "Amount" not in df.columns or df["Amount"].sum() == 0:
            df["Amount"] = df["Amount_1"]
        elif df["Amount_1"].sum() > 0 and df["Amount"].sum() > 0:
            df["Amount"] = df.apply(lambda r: r["Amount_1"] if r["Amount"] == 0 else r["Amount"], axis=1)

    if "Days_Overdue" in df.columns:
        df["Days_Overdue"] = pd.to_numeric(df["Days_Overdue"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    is_summary_row = df.astype(str).apply(lambda row: row.str.lower().str.contains('grand total|total:|closing balance|average', na=False)).any(axis=1)
    df = df[~is_summary_row]

    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].replace(['None', 'nan', '', None], pd.NA).ffill()
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'purchase', 'nan', 'none', 'total'])]

    if "Vch No." in df.columns and "Date" in df.columns:
        valid_vch = df["Vch No."].notna() & (~df["Vch No."].astype(str).str.lower().isin(['none', 'nan', '', '0']))
        valid_date = df["Date"].notna() & (~df["Date"].astype(str).str.lower().isin(['none', 'nan', '', '0']))
        df = df[valid_vch | valid_date]
    elif "Date" in df.columns:
        df = df[df["Date"].notna() & (~df["Date"].astype(str).str.lower().isin(['none', 'nan', '']))]

    df = df.reset_index(drop=True)
    return df, pd.DataFrame(), pd.DataFrame()

def generate_upi_qr(vpa, name, amount):
    upi_url = f"upi://pay?pa={vpa}&pn={quote(name)}&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

# ----------------- AUTHENTICATION -----------------
if not st.session_state["logged_in"]:
    st.markdown("""
        <div style="text-align: center; margin-top: 50px; margin-bottom: 35px;">
            <div class="badge-chip badge-indigo" style="margin-bottom: 12px;">Next-Gen Financial Intelligence</div>
            <h1 style="font-weight: 800; font-size: 3.1rem; letter-spacing: -0.04em; margin-bottom: 8px; background: linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Tally Executive BI Suite
            </h1>
            <p style="color: #94A3B8; font-size: 1.05rem; font-weight: 400; max-width: 580px; margin: auto;">
                Transform raw Tally ERP transactions into auditable working capital insights, live P&L statements & CA dossiers.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.7, 1])
    with col2:
        menu = ["Sign In", "Start 7-Day Free Trial"]
        choice = st.segmented_control("Access Mode", menu, default="Sign In")

        if choice == "Sign In":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            u = st.text_input("Business Username", placeholder="e.g. industrial_trade")
            p = st.text_input("Security Password", type="password", placeholder="••••••••")
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
                            st.error("Invalid credentials provided.")
                    else:
                        st.error("Please provide valid username, password and 10-digit mobile number.")
            else:
                target_phone = phone.strip()[-10:]
                msg_body = quote(f"Hello, your Tally Executive Suite Login OTP is: {st.session_state['generated_otp']}. Valid for 10 minutes.")
                wa_link = f"https://api.whatsapp.com/send?phone=91{target_phone}&text={msg_body}"

                st.markdown(f"""
                    <div style="text-align: center; margin: 15px 0;">
                        <a href="{wa_link}" target="_blank" class="whatsapp-btn">
                            💬 Send Instant OTP to WhatsApp (+91 {target_phone})
                        </a>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander("👁️ Backup: Display OTP on screen"):
                    st.info(f"Verification Code: **`{st.session_state['generated_otp']}`**")

                entered_otp = st.text_input("Enter 6-Digit OTP", placeholder="••••••")
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    if st.button("Verify OTP & Authorize", use_container_width=True, type="primary"):
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
                            st.error("Incorrect verification token entered.")
                with col_sub2:
                    if st.button("Reset Session", use_container_width=True):
                        st.session_state["otp_sent"] = False
                        st.rerun()

            st.markdown("""
                <div class="support-box">
                    <span style="color: #94A3B8; font-size: 0.82rem;">Direct Executive Concierge</span><br>
                    <a href="tel:7016882039" style="color: #818CF8; font-weight: 700; text-decoration: none; font-size: 0.95rem;">+91 7016882039</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        elif choice == "Start 7-Day Free Trial":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            new_u = st.text_input("Desired Username", placeholder="e.g. shree_balaji")
            new_p = st.text_input("Set Password", type="password", placeholder="••••••••")
            new_phone = st.text_input("Mobile Number (WhatsApp Active)", placeholder="10-digit mobile number")
            
            st.caption("🔒 Includes 7-day unlimited access to all auditing modules & P&L intelligence.")
            if st.button("Activate Free Enterprise Evaluation", use_container_width=True, type="primary"):
                if new_u and new_p and new_phone and len(new_phone.strip()) >= 10:
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (new_u,))
                    if c.fetchone():
                        st.error("Username is already allocated.")
                    else:
                        dev_hash = get_client_device_hash(new_u)
                        prev_acc = check_device_trial_exists(dev_hash)
                        if prev_acc:
                            st.error(f"🚫 Workstation trial already claimed by `{prev_acc[0]}`. Please sign in.")
                        else:
                            add_user(new_u, new_p, new_phone.strip(), role="client", status="trial", plan="Free Trial (7 Days)", device_hash=dev_hash, txn_id="FREE_TRIAL")
                            st.success("🎉 Enterprise trial unlocked! Switch to 'Sign In' to authorize.")
                else:
                    st.error("Please complete all fields with a valid 10-digit mobile number.")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- TRIAL EXPIRED SCREEN -----------------
current_monthly_price, current_yearly_price = get_pricing_config()

if st.session_state.get("status") == "expired":
    st.markdown("""
        <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
            <div class="badge-chip badge-rose" style="margin-bottom: 10px;">Evaluation Period Concluded</div>
            <h2 style="font-weight: 800; font-size: 2.3rem;">Renew Executive Access</h2>
            <p style="color: #94A3B8;">Unlock ongoing Tally compliance, automated debtor tracking & March CA audit exports.</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        plan_options = [
            f"Monthly License — ₹{current_monthly_price:,} / Month", 
            f"Annual Enterprise — ₹{current_yearly_price:,} / Year (Best Value)"
        ]
        plan_sel = st.radio("Subscription Tier:", plan_options)
        
        amt = current_monthly_price if str(current_monthly_price) in plan_sel else current_yearly_price
        p_name = f"Monthly (₹{amt})" if amt == current_monthly_price else f"Yearly (₹{amt})"

        col_q1, col_q2 = st.columns([1.2, 1])
        with col_q1:
            st.markdown(f"**Amount Payable:** `₹{amt:,}`")
            st.markdown("**UPI VPA:** `tanmayagarwal776@okhdfcbank`")
            pay_tx = st.text_input("12-Digit Bank UTR / Ref Number:")
        with col_q2:
            qr_img = generate_upi_qr("tanmayagarwal776@okhdfcbank", "Tanmay Agarwal", amt)
            st.image(qr_img, width=170)

        if st.button("Submit License Verification", use_container_width=True, type="primary"):
            if pay_tx.strip():
                update_user_payment(st.session_state["username"], p_name, pay_tx.strip())
                st.success("✅ Payment reference logged. Audit suite activates upon clearance.")
            else:
                st.error("Valid transaction reference required.")

        st.markdown("""
            <div class="support-box">
                <span style="color: #94A3B8; font-size: 0.85rem;">💬 Payment Query?</span><br>
                <b>Customer Care:</b> <a href="https://wa.me/917016882039" style="color: #34D399; font-weight: 700; text-decoration: none;">+91 7016882039</a>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Log Out"):
            st.session_state.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown(f"""
        <div style="padding: 14px 4px 18px 4px;">
            <div style="font-size: 0.75rem; color: #64748B; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">Workspace</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #F8FAFC; margin-top: 2px;">{st.session_state['username']}</div>
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
        admin_mode = st.radio("Console View", ["Analytics Dashboard", "User Management & CRM", "License Approvals"], key="admin_console_nav_radio")
    else:
        admin_mode = "Analytics Dashboard"

    st.markdown("#### ⚙️ Business Rules")
    credit_days_threshold = st.slider(
        "Debtor Credit Limit (Days)", 
        min_value=15, 
        max_value=180, 
        value=65, 
        step=5,
        help="Standard credit days setting (Salt Industry benchmark: 65 Days)."
    )

    st.markdown("---")
    st.markdown("#### 📂 Tally Data Ingestion")
    uploaded_files = st.file_uploader(
        "Upload Tally Files (.xml, .xlsx, .csv)",
        type=["xlsx", "xls", "csv", "xml"],
        accept_multiple_files=True,
        help="Drop your direct Tally Transactions.xml or stock ledger exports."
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
if st.session_state["role"] == "admin" and admin_mode == "User Management & CRM":
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

    st.markdown("### 💰 Subscription Pricing Manager")
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
    else:
        st.info("No client accounts registered yet.")

    st.stop()

# ----------------- ADMIN: LICENSE QUEUE -----------------
if st.session_state["role"] == "admin" and admin_mode == "License Approvals":
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

# ----------------- MAIN EXECUTIVE DASHBOARD -----------------
if uploaded_files:
    business_data = {
        "Sales": 0.0,
        "Purchase": 0.0,
        "Outstanding": 0.0,
        "Payables": 0.0,
        "Overdue": 0.0,
        "Closing_Stock": 0.0,
        "Direct_Expenses": 0.0,
        "Direct_Incomes": 0.0,
        "Indirect_Expenses": 0.0,
        "Indirect_Incomes": 0.0,
        "MSME_Critical_Dues": 0.0,
        "Top_Customer": "N/A",
        "Top_Customer_Amt": 0.0,
        "Critical_Count": 0,
        "Receivables_DF": None,
        "Payables_DF": None,
        "Sales_DF": None,
        "Purchase_DF": None,
        "Stock_DF": None,
        "PL_DF": None
    }

    xml_stock_accumulator = []
    xml_expense_accumulator = []

    for f in uploaded_files:
        fdf, s_df, e_df = load_tally_file(f)
        if fdf.empty and s_df.empty:
            continue

        fname = f.name.lower()
        if not s_df.empty:
            xml_stock_accumulator.append(s_df)
        if not e_df.empty:
            xml_expense_accumulator.append(e_df)

        vch_types = []
        if "Vch Type" in fdf.columns:
            vch_types = [str(x).lower() for x in fdf["Vch Type"].dropna().unique()]

        if fname.endswith('.xml'):
            # Sales Vouchers (Debit)
            s_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("sales|sale", na=False)]
            if not s_rows.empty:
                business_data["Sales_DF"] = s_rows
                business_data["Sales"] += s_rows["Amount"].sum()
                top_c = s_rows.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
                if not top_c.empty:
                    business_data["Top_Customer"] = top_c.index[0]
                    business_data["Top_Customer_Amt"] = top_c.iloc[0]

            # Purchase Vouchers (Credit)
            p_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("purchase|purch", na=False)]
            if not p_rows.empty:
                business_data["Purchase_DF"] = p_rows
                business_data["Purchase"] += p_rows["Amount"].sum()

            # Payments Made to Vendors
            py_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("payment|payab", na=False)]
            if not py_rows.empty:
                business_data["Payables_DF"] = py_rows
                business_data["Payables"] += py_rows["Amount"].sum()
                msme_overdue_xml = py_rows[py_rows["Days_Overdue"] >= 45]
                business_data["MSME_Critical_Dues"] += msme_overdue_xml["Amount"].sum()

            # ----------------- TRUE DEBTOR RECONCILIATION ENGINE -----------------
            # Party Balance = (Total Sales Billed) MINUS (Total Receipts Received)
            rcpt_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("receipt", na=False)]
            
            sales_by_party = s_rows.groupby("Party Name")["Amount"].sum() if not s_rows.empty else pd.Series(dtype=float)
            rcpt_by_party = rcpt_rows.groupby("Party Name")["Amount"].sum() if not rcpt_rows.empty else pd.Series(dtype=float)

            reconciled_debtors = []
            all_parties = set(sales_by_party.index).union(set(rcpt_by_party.index))

            for party in all_parties:
                # Bank / Internal transfers ko party se filter karein
                if any(k in party.lower() for k in ["bank", "cash", "gst", "tds", "round", "interest", "sales", "purchase"]):
                    continue
                    
                total_billed = float(sales_by_party.get(party, 0.0))
                total_paid = float(rcpt_by_party.get(party, 0.0))
                net_due = total_billed - total_paid

                # Agar payment completely settled hai (Balance <= 10 INR difference) to overdue se hatayein!
                if net_due > 10.0:
                    party_sales_vchs = s_rows[s_rows["Party Name"] == party]
                    max_days = party_sales_vchs["Days_Overdue"].max() if not party_sales_vchs.empty else 0
                    last_vch = party_sales_vchs["Vch No."].iloc[-1] if not party_sales_vchs.empty else "BILL"
                    last_date = party_sales_vchs["Date"].iloc[-1] if not party_sales_vchs.empty else str(get_ist_now().date())

                    reconciled_debtors.append({
                        "Party Name": party,
                        "Net Outstanding Due (₹)": net_due,
                        "Total Billed (₹)": total_billed,
                        "Total Paid (₹)": total_paid,
                        "Last Bill Date": last_date,
                        "Ref Invoice": last_vch,
                        "Days Overdue": max_days
                    })

            if reconciled_debtors:
                rec_df = pd.DataFrame(reconciled_debtors)
                business_data["Receivables_DF"] = rec_df
                business_data["Outstanding"] = rec_df["Net Outstanding Due (₹)"].sum()
                
                overdue_rec = rec_df[rec_df["Days Overdue"] >= credit_days_threshold]
                business_data["Overdue"] = overdue_rec["Net Outstanding Due (₹)"].sum()
                business_data["Critical_Count"] = len(overdue_rec)
            else:
                business_data["Receivables_DF"] = pd.DataFrame()
                business_data["Outstanding"] = 0.0
                business_data["Overdue"] = 0.0
                business_data["Critical_Count"] = 0

        elif "stock" in fname or "inventory" in fname:
            business_data["Stock_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Closing_Stock"] = fdf["Amount"].sum()

        elif "payable" in fname or "creditor" in fname:
            business_data["Payables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Payables"] += fdf["Amount"].sum()
            if "Days_Overdue" in fdf.columns:
                msme_overdue = fdf[fdf["Days_Overdue"] >= 45]
                if "Amount" in msme_overdue.columns:
                    business_data["MSME_Critical_Dues"] += msme_overdue["Amount"].sum()

        elif "purch" in fname or any("purch" in v for v in vch_types):
            business_data["Purchase_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Purchase"] += fdf["Amount"].sum()

        elif "sale" in fname or any("sale" in v for v in vch_types) or "daybook" in fname:
            business_data["Sales_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Sales"] += fdf["Amount"].sum()
            if "Party Name" in fdf.columns and not fdf.empty:
                valid_parties = fdf[~fdf["Party Name"].str.lower().isin(['total', '', 'nan', 'none'])]
                if not valid_parties.empty and "Amount" in valid_parties.columns:
                    top_c = valid_parties.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
                    if not top_c.empty:
                        business_data["Top_Customer"] = top_c.index[0]
                        business_data["Top_Customer_Amt"] = top_c.iloc[0]

        elif "profit" in fname or "loss" in fname or "p&l" in fname or "expense" in fname:
            business_data["PL_DF"] = fdf

    if business_data["Stock_DF"] is None and xml_stock_accumulator:
        consolidated_stk = pd.concat(xml_stock_accumulator, ignore_index=True)
        business_data["Stock_DF"] = consolidated_stk
        if "Closing Value" in consolidated_stk.columns:
            business_data["Closing_Stock"] = round(consolidated_stk["Closing Value"].sum(), 2)

    if xml_expense_accumulator:
        consolidated_exp = pd.concat(xml_expense_accumulator, ignore_index=True)
        for _, rx in consolidated_exp.iterrows():
            px_name = str(rx.get("Particulars", "")).lower()
            amt_x = float(rx.get("Amount", 0.0))
            if any(k in px_name for k in ["freight", "carriage", "cartage", "wages", "fuel", "direct"]):
                business_data["Direct_Expenses"] += amt_x
            else:
                business_data["Indirect_Expenses"] += amt_x

    gross_profit = (business_data["Sales"] + business_data["Direct_Incomes"] + business_data["Closing_Stock"]) - (business_data["Purchase"] + business_data["Direct_Expenses"])
    net_profit = (gross_profit + business_data["Indirect_Incomes"]) - business_data["Indirect_Expenses"]

    # ----------------- ADVANCED AI HEALTH SCORE & RISK CALCULATOR -----------------
    health_score = 100
    risk_warnings = []
    
    if business_data["Outstanding"] > 0:
        overdue_ratio = (business_data["Overdue"] / business_data["Outstanding"]) * 100
        if overdue_ratio > 40:
            health_score -= 25
            risk_warnings.append(f"⚠️ **Debtor Illiquidity Alert**: {overdue_ratio:.1f}% of total net receivables are past due limits! Immediate cash flow impact predicted.")
        elif overdue_ratio > 20:
            health_score -= 10
            risk_warnings.append(f"⚡ **Debtor Delay Warning**: {overdue_ratio:.1f}% receivables overdue.")

    if business_data["Sales"] > 0 and business_data["Top_Customer_Amt"] > 0:
        cust_conc = (business_data["Top_Customer_Amt"] / business_data["Sales"]) * 100
        if cust_conc > 35:
            health_score -= 20
            risk_warnings.append(f"🚨 **High Concentration Risk**: `{business_data['Top_Customer']}` drives {cust_conc:.1f}% of entire business revenue!")
        elif cust_conc > 25:
            health_score -= 10

    if business_data["Payables"] > business_data["Outstanding"] and business_data["Outstanding"] > 0:
        health_score -= 15
        diff = business_data["Payables"] - business_data["Outstanding"]
        risk_warnings.append(f"🛑 **Working Capital Deficit**: Supplier payables exceed customer debtor receivables by ₹{diff:,.2f}.")

    if business_data["MSME_Critical_Dues"] > 0:
        health_score -= 15
        risk_warnings.append(f"⚖️ **MSME Section 43B(h) Risk**: Overdue vendor dues of ₹{business_data['MSME_Critical_Dues']:,.2f} exceeding 45 days face disallowance & tax interest.")

    health_score = max(10, min(100, health_score))
    
    if health_score >= 80:
        health_status = "PRIME STABILITY (LOW RISK)"
        health_badge = "badge-emerald"
        health_color = "#34D399"
    elif health_score >= 55:
        health_status = "MODERATE VULNERABILITY"
        health_badge = "badge-amber"
        health_color = "#FBBF24"
    else:
        health_status = "CRITICAL WORKING CAPITAL STRESS"
        health_badge = "badge-rose"
        health_color = "#FB7185"

    # Luxury Top Financial Banner
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

    # AI RADAR
    st.markdown(f"""
        <div class="ai-radar-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="font-size: 1.4rem;">🛡️</div>
                    <div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #F8FAFC;">AI Liquidity Radar & Financial Health Meter</div>
                        <div style="font-size: 0.8rem; color: #94A3B8;">Real-time balance sheet audit, debtor concentration & working capital stress tests</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div class="badge-chip {health_badge}" style="font-size: 0.8rem;">{health_status}</div>
                </div>
            </div>
            <div style="display: flex; align-items: baseline; gap: 12px; margin-top: 8px;">
                <div style="font-size: 2.6rem; font-weight: 800; color: {health_color}; font-family: 'JetBrains Mono', monospace;">
                    {health_score}<span style="font-size: 1.2rem; color: #64748B;"> / 100</span>
                </div>
                <div style="color: #94A3B8; font-size: 0.9rem;">
                    Health Composite: Based on cash lockup, MSME compliance, turnover spread & payable liabilities.
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if risk_warnings:
        with st.expander("⚡ View AI Risk & Working Capital Action Items", expanded=True):
            for w in risk_warnings:
                st.markdown(f"- {w}")

    # 4 Core KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">
                    <span>Revenue (Turnover)</span>
                    <span class="badge-chip badge-emerald">Sales A/c</span>
                </div>
                <div class="metric-val">₹{business_data['Sales']:,.2f}</div>
                <div class="metric-sub" style="color: #34D399;">● Reconciled Trading Ledger</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">
                    <span>Actual Debtor Book</span>
                    <span class="badge-chip badge-indigo">Net Dues</span>
                </div>
                <div class="metric-val">₹{business_data['Outstanding']:,.2f}</div>
                <div class="metric-sub" style="color: #818CF8;">● Reconciled Outstanding (Debit - Credit)</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">
                    <span>Actual Overdue Risk</span>
                    <span class="badge-chip badge-rose">{credit_days_threshold}+ Days</span>
                </div>
                <div class="metric-val" style="color: #FB7185;">₹{business_data['Overdue']:,.2f}</div>
                <div class="metric-sub" style="color: #FB7185;">● Real Unpaid Cash Lockup</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">
                    <span>Vendor Exposure</span>
                    <span class="badge-chip badge-amber">Payables</span>
                </div>
                <div class="metric-val">₹{business_data['Payables']:,.2f}</div>
                <div class="metric-sub" style="color: #FBBF24;">● Supplier Liabilities</div>
            </div>
        """, unsafe_allow_html=True)

    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        st.markdown(f"""
            <div class="info-card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.76rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Primary Revenue Contributor</div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #F8FAFC; margin-top: 3px;">{str(business_data['Top_Customer'])[:22]}</div>
                </div>
                <div class="badge-chip badge-indigo">Anchor Buyer</div>
            </div>
        """, unsafe_allow_html=True)
    with c_sub2:
        st.markdown(f"""
            <div class="info-card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.76rem; color: #94A3B8; font-weight: 700; text-transform: uppercase;">Real Debtor Risk ({credit_days_threshold}+ Days)</div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #FB7185; margin-top: 3px;">{business_data['Critical_Count']} Overdue Accounts</div>
                </div>
                <div class="badge-chip badge-rose">Net Pending Only</div>
            </div>
        """, unsafe_allow_html=True)

    # Executive P&L Snapshot
    st.markdown("### 📊 Margin Telemetry & Operating Spread")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Gross Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.2f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Nett Profit", f"₹{net_profit:,.2f}", delta="Net Surplus" if net_profit >= 0 else "Deficit")

    st.markdown("---")

    # CA Audit Dossier
    st.markdown("### 🏛️ March-Ending CA Audit & Tax Dossier")
    ca_col1, ca_col2 = st.columns([2.2, 1.8])
    with ca_col1:
        st.markdown(f"""
            <div class="info-card">
                <div style="font-weight: 700; font-size: 1.1rem; color: #F8FAFC; margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span>Audit & Statutory Checks</span>
                    <span class="badge-chip badge-indigo">Statutory</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #94A3B8;">Inventory Closing Valuation:</span>
                    <b style="color: {'#FB7185' if business_data['Closing_Stock'] < 0 else '#34D399'}; font-family: 'JetBrains Mono', monospace;">₹{business_data['Closing_Stock']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #94A3B8;">MSME 45-Day Dues (Sec 43B(h)):</span>
                    <b style="color: {'#FB7185' if business_data['MSME_Critical_Dues'] > 0 else '#34D399'}; font-family: 'JetBrains Mono', monospace;">₹{business_data['MSME_Critical_Dues']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94A3B8;">Debtors Exceeding Benchmark ({credit_days_threshold} Days):</span>
                    <b style="color: #F8FAFC; font-family: 'JetBrains Mono', monospace;">{business_data['Critical_Count']} Accounts</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with ca_col2:
        audit_summary_df = pd.DataFrame([
            {"Audit Metric": "Annual Sales Turnover (Sales A/c)", "Amount (INR)": business_data["Sales"]},
            {"Audit Metric": "Annual Total Purchases (Purchase A/c)", "Amount (INR)": business_data["Purchase"]},
            {"Audit Metric": "Closing Stock Valuation", "Amount (INR)": business_data["Closing_Stock"]},
            {"Audit Metric": "Gross Profit c/o", "Amount (INR)": gross_profit},
            {"Audit Metric": "Direct Expenses", "Amount (INR)": business_data["Direct_Expenses"]},
            {"Audit Metric": "Indirect Expenses", "Amount (INR)": business_data["Indirect_Expenses"]},
            {"Audit Metric": "Nett Profit", "Amount (INR)": net_profit},
            {"Audit Metric": "Actual Sundry Debtors (Reconciled Net Dues)", "Amount (INR)": business_data["Outstanding"]},
            {"Audit Metric": "Actual Overdue Risk Portfolio", "Amount (INR)": business_data["Overdue"]},
            {"Audit Metric": "Total Sundry Creditors (Payables)", "Amount (INR)": business_data["Payables"]},
            {"Audit Metric": "MSME Overdue Payables (>45 Days - Sec 43Bh)", "Amount (INR)": business_data["MSME_Critical_Dues"]}
        ])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            audit_summary_df.to_excel(writer, sheet_name="CA_Audit_Summary", index=False)
            if business_data["Receivables_DF"] is not None and not business_data["Receivables_DF"].empty:
                business_data["Receivables_DF"].to_excel(writer, sheet_name="Debtors_Ageing", index=False)
            if business_data["Payables_DF"] is not None:
                business_data["Payables_DF"].to_excel(writer, sheet_name="Creditors_MSME", index=False)
            if business_data["Stock_DF"] is not None:
                business_data["Stock_DF"].to_excel(writer, sheet_name="Stock_Summary", index=False)
                
        st.download_button(
            label="📥 Download Certified CA Audit Dossier (.xlsx)",
            data=output.getvalue(),
            file_name=f"Tally_Audit_Dossier_March_{get_ist_now().year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

    # Detailed Sub-Ledgers
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Sales Register", 
        "📦 Purchase Register", 
        "⚠️ Reconciled Receivables & WhatsApp Recovery", 
        "🏢 Payables (Creditors & MSME)",
        "📋 Stock Summary",
        "⚖️ Profit & Loss A/c"
    ])
    
    with tab1:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True, height=400)
        else:
            st.info("Sales transactions will populate once data is uploaded.")

    with tab2:
        if business_data["Purchase_DF"] is not None:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True, height=400)
        else:
            st.info("Purchase billing records will populate once data is uploaded.")
            
    with tab3:
        # ----------------- TRUE RECONCILED DEBTORS TABLE -----------------
        if business_data["Receivables_DF"] is not None and not business_data["Receivables_DF"].empty:
            r_df = business_data["Receivables_DF"].copy()

            # Overdue Dues Center (Only positive pending balances)
            overdue_only = r_df[r_df["Days Overdue"] >= credit_days_threshold]
            if not overdue_only.empty:
                st.markdown(f"""
                    <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.25); border-radius: 12px; padding: 14px 18px; margin-bottom: 15px;">
                        <b style="color: #FB7185;">Critical Overdue Action Center:</b> {len(overdue_only)} debtors have genuine unpaid dues exceeding {credit_days_threshold} days. (Settled parties like JAY SALT auto-removed).
                    </div>
                """, unsafe_allow_html=True)

                col_wa1, col_wa2, col_wa3 = st.columns([1.8, 1.2, 1.2])
                with col_wa1:
                    selected_party = st.selectbox("Select Overdue Debtor to Dispatch Notice:", overdue_only["Party Name"].unique(), key="chase_party_sel")
                
                party_row = overdue_only[overdue_only["Party Name"] == selected_party].iloc[0]
                total_party_due = party_row["Net Outstanding Due (₹)"]
                max_days = party_row["Days Overdue"]
                first_vch = party_row["Ref Invoice"]

                with col_wa2:
                    st.metric("Net Pending Balance", f"₹{total_party_due:,.2f}", f"{max_days} Days Delay")

                with col_wa3:
                    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
                    chase_msg = quote(
                        f"Dear {selected_party},\n\n"
                        f"This is a formal payment update regarding your net outstanding balance of *₹{total_party_due:,.2f}* (Ref: {first_vch}), "
                        f"which is overdue by *{max_days} days* against our agreed credit terms of {credit_days_threshold} days.\n\n"
                        f"Kindly confirm the transfer of funds today or provide the RTGS/NEFT transaction UTR to avoid hold on future dispatches.\n\n"
                        f"Regards,\nAccounts & Finance Department"
                    )
                    wa_chase_url = f"https://api.whatsapp.com/send?text={chase_msg}"
                    st.markdown(f"""
                        <a href="{wa_chase_url}" target="_blank" class="whatsapp-chase-badge" style="padding: 10px 16px; font-size: 0.9rem;">
                            💬 Send Legal Notice via WhatsApp
                        </a>
                    """, unsafe_allow_html=True)

            st.dataframe(r_df, use_container_width=True, height=350)
        else:
            st.success("🎉 All customer ledger balances are fully reconciled & paid! No outstanding receivables found.")

    with tab4:
        if business_data["Payables_DF"] is not None:
            st.dataframe(business_data["Payables_DF"], use_container_width=True, height=400)
        else:
            st.info("Creditor & MSME outstandings will populate once data is uploaded.")

    with tab5:
        if business_data["Stock_DF"] is not None and not business_data["Stock_DF"].empty:
            st.dataframe(business_data["Stock_DF"], use_container_width=True, height=400)
        else:
            st.info("Stock records will display once inventory data is uploaded.")

    with tab6:
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
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">{business_data['Direct_Incomes']:,.2f}</td>
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
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">{business_data['Indirect_Expenses']:,.2f}</td>
                            <td>Gross Profit b/f</td>
                            <td style="text-align: right; font-weight: 700; color: #34D399; font-family: 'JetBrains Mono', monospace;">{gross_profit:,.2f}</td>
                        </tr>
                        <tr>
                            <td>Nett Profit</td>
                            <td style="text-align: right; font-weight: 700; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">{net_profit:,.2f}</td>
                            <td>Indirect Incomes</td>
                            <td style="text-align: right; font-family: 'JetBrains Mono', monospace;">{business_data['Indirect_Incomes']:,.2f}</td>
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
    st.markdown("""
        <div style="text-align: center; padding: 70px 20px; border: 1px dashed rgba(255,255,255,0.12); border-radius: 22px; margin-top: 25px; background: rgba(15, 23, 42, 0.35);">
            <div style="font-size: 3rem; margin-bottom: 12px;">⚡</div>
            <h3 style="font-weight: 800; font-size: 1.45rem; color: #F8FAFC;">Executive Intelligence Awaiting Data</h3>
            <p style="color: #94A3B8; max-width: 520px; margin: auto; font-size: 0.95rem; line-height: 1.6;">
                Drop your Tally <code>Transactions.xml</code> or audited Excel balance sheets into the sidebar to generate instant audit dossiers, inventory valuations & working capital telemetry.
            </p>
        </div>
    """, unsafe_allow_html=True)
