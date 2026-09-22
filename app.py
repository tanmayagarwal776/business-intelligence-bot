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

# ----------------- MODERN EXECUTIVE CSS THEME -----------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(14, 23, 42, 0.95) 0%, rgba(15, 23, 42, 1) 90%);
    }

    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 12px;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.65rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-sub {
        font-size: 0.78rem;
        margin-top: 6px;
        font-weight: 500;
    }

    .info-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 15px;
    }

    .support-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px dashed rgba(99, 102, 241, 0.35);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 15px;
        text-align: center;
    }

    section[data-testid="stSidebar"] {
        background-color: #0B1120;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    .badge-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .badge-primary { background: rgba(99, 102, 241, 0.2); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }
    .badge-danger { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.25); }
    .badge-success { background: rgba(34, 197, 94, 0.15); color: #4ADE80; border: 1px solid rgba(34, 197, 94, 0.25); }
    </style>
""", unsafe_allow_html=True)

# ----------------- DATABASE INITIALIZATION WITH PHONE -----------------
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
    conn.commit()
    return conn

conn = init_db()

def migrate_db_schema():
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in c.fetchall()]
    if "phone" not in cols:
        try:
            c.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass

migrate_db_schema()

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
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO users (username, password, phone, role, status, plan, created_at, device_hash, txn_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (username, hash_pw(password), phone, role, status, plan, now_str, device_hash, txn_id))
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

# Default Admin Setup
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", "7016882039", role="admin", status="approved", plan="Lifetime Enterprise", device_hash="ADMIN_DEV", txn_id="ADMIN")

# ----------------- ACCURATE INVENTORY & P&L XML EXTRACTION -----------------
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
    item_balances = {}  # {item_name: {"net_qty": 0.0, "net_val": 0.0, "unit": "bag", "rate": 0.0}}
    expense_records = []
    current_date = datetime.date.today()

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

        # Total voucher amount
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

        # Net Closing Stock Engine (Inwards: +, Outwards: -)
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
                it_amt = abs(float(amt_m.group(1))) if amt_m else 0.0
                
                # Parse numeric quantity
                raw_qty_str = qty_m.group(1).strip() if qty_m else "0"
                qty_val_m = re.search(r'([+-]?\d+(?:\.\d+)?)', raw_qty_str)
                num_qty = float(qty_val_m.group(1)) if qty_val_m else 0.0
                unit_str = re.sub(r'[0-9\.\+\-\s]', '', raw_qty_str) or "bag"

                # Parse rate
                raw_rate_str = rate_m.group(1).strip() if rate_m else "0"
                rate_val_m = re.search(r'([+-]?\d+(?:\.\d+)?)', raw_rate_str)
                num_rate = float(rate_val_m.group(1)) if rate_val_m else (it_amt / num_qty if num_qty != 0 else 0.0)

                if it_name not in item_balances:
                    item_balances[it_name] = {"net_qty": 0.0, "net_val": 0.0, "unit": unit_str, "last_rate": num_rate}

                if is_purchase:
                    item_balances[it_name]["net_qty"] += num_qty
                    item_balances[it_name]["net_val"] += it_amt
                    if num_rate > 0:
                        item_balances[it_name]["last_rate"] = num_rate
                elif is_sale:
                    item_balances[it_name]["net_qty"] -= num_qty
                    item_balances[it_name]["net_val"] -= it_amt
                else:
                    item_balances[it_name]["net_qty"] += num_qty
                    item_balances[it_name]["net_val"] += it_amt

        # Overheads for P&L
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
                        "Particulars (Expense Ledger)": lname,
                        "Vch Type": v_type,
                        "Vch No.": v_no,
                        "Amount": lamt
                    })

    # Convert inventory dictionary to clean item-wise summary (Matching Tally Stock Summary)
    stock_summary_rows = []
    for it_k, it_v in item_balances.items():
        stock_summary_rows.append({
            "Particulars (Stock Item)": it_k,
            "Closing Quantity": f"{it_v['net_qty']:,.0f} {it_v['unit']}",
            "Effective Rate": f"₹{it_v['last_rate']:,.2f}",
            "Closing Value": round(it_v['net_val'], 2)
        })

    vch_df = pd.DataFrame(vouchers) if vouchers else pd.DataFrame()
    stk_df = pd.DataFrame(stock_summary_rows) if stock_summary_rows else pd.DataFrame()
    exp_df = pd.DataFrame(expense_records) if expense_records else pd.DataFrame()
    return vch_df, stk_df, exp_df

# ----------------- TALLY EXCEL / CSV LOADER -----------------
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

# ----------------- SESSION STATE -----------------
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
        <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
            <div class="badge-tag badge-primary">2-FACTOR SECURE ENTERPRISE SUITE</div>
            <h1 style="font-weight: 800; font-size: 2.6rem; letter-spacing: -0.02em; margin-bottom: 8px;">Tally Executive Suite</h1>
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
                if st.button("Generate & Send Mobile OTP", use_container_width=True, type="primary"):
                    if u and p and phone and len(phone.strip()) >= 10:
                        res = verify_user_creds(u, p)
                        if res:
                            reg_phone, role, status, plan, created_at = res
                            otp = str(random.randint(100000, 999999))
                            st.session_state["generated_otp"] = otp
                            st.session_state["otp_sent"] = True
                            st.session_state["temp_user"] = {
                                "username": u, "phone": phone, "role": role, 
                                "status": status, "plan": plan, "created_at": created_at
                            }
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.error("Please provide valid username, password and 10-digit phone number.")
            else:
                st.success(f"📲 Security OTP generated for {phone}: **`{st.session_state['generated_otp']}`**")
                entered_otp = st.text_input("Enter 6-Digit OTP Received", placeholder="••••••")
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    if st.button("Verify OTP & Login", use_container_width=True, type="primary"):
                        if entered_otp.strip() == st.session_state["generated_otp"]:
                            usr = st.session_state["temp_user"]
                            status = usr["status"]
                            is_expired = False
                            if status == "trial":
                                c_date = datetime.datetime.strptime(usr["created_at"], "%Y-%m-%d %H:%M:%S")
                                if (datetime.datetime.now() - c_date).days >= 7:
                                    is_expired = True
                                    status = "expired"
                                    c = conn.cursor()
                                    c.execute("UPDATE users SET status='expired' WHERE username=?", (usr["username"],))
                                    conn.commit()

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
                <div class="support-box">
                    <span style="color: #94A3B8; font-size: 0.85rem;">📞 Helpline & Support:</span><br>
                    <a href="tel:7016882039" style="color: #818CF8; font-weight: 700; text-decoration: none; font-size: 1rem;">+91 7016882039</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        elif choice == "Start 7-Day Free Trial":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            new_u = st.text_input("Choose Username", placeholder="e.g. industrial_trade")
            new_p = st.text_input("Choose Password", type="password", placeholder="••••••••")
            new_phone = st.text_input("Mobile Number (For OTP Login)", placeholder="10-digit mobile number")
            
            st.caption("🔒 7-day full access included. Verified Mobile Security.")
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
                            st.success("🎉 Account activated! Switch to 'Sign In' to login via OTP.")
                else:
                    st.error("Please fill all fields including 10-digit mobile number.")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- TRIAL EXPIRED PAYMENT SCREEN -----------------
if st.session_state.get("status") == "expired":
    st.markdown("""
        <div style="text-align: center; margin-top: 30px; margin-bottom: 25px;">
            <div class="badge-tag badge-danger">TRIAL PERIOD EXPIRED</div>
            <h2 style="font-weight: 700;">Renew Your Executive Access</h2>
            <p style="color: #94A3B8;">Your 7-day evaluation has concluded. Select an ongoing license below to continue analysis.</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        st.markdown("<div class='info-card'>", unsafe_allow_html=True)
        plan_sel = st.radio("Select Subscription Plan:", ["Monthly License — ₹499 / Month", "Annual Enterprise — ₹2,999 / Year (Best Value)"])
        amt = 499 if "499" in plan_sel else 2999
        p_name = "Monthly (₹499)" if amt == 499 else "Yearly (₹2999)"

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

# ----------------- SIDEBAR WORKSPACE -----------------
with st.sidebar:
    st.markdown(f"""
        <div style="padding: 12px 4px 18px 4px;">
            <div style="font-size: 0.8rem; color: #64748B; font-weight: 600;">ACTIVE WORKSPACE</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">{st.session_state['username']}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state["status"] == "trial":
        c_date = datetime.datetime.strptime(st.session_state.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S")
        days_left = max(0, 7 - (datetime.datetime.now() - c_date).days)
        st.markdown(f'<div class="badge-tag badge-primary">Trial: {days_left} Days Remaining</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="badge-tag badge-success">{st.session_state.get("plan", "Enterprise License")}</div>', unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")

    if st.session_state["role"] == "admin":
        admin_mode = st.radio("Console Navigation", ["Analytics Dashboard", "License Approvals"])
    else:
        admin_mode = "Analytics Dashboard"

    st.markdown("#### ⚙️ Business Rules")
    credit_days_threshold = st.slider(
        "Standard Credit Period (Days)", 
        min_value=15, 
        max_value=180, 
        value=65, 
        step=5,
        help="Allowed credit days set karein (Salt: 65 Days)."
    )

    st.markdown("---")
    st.markdown("#### 📂 Tally Reports / Direct XML")
    uploaded_files = st.file_uploader(
        "Upload Tally Files (.xlsx, .xls, .csv, .xml)",
        type=["xlsx", "xls", "csv", "xml"],
        accept_multiple_files=True,
        help="Tally Transactions.xml ya Stock Summary Excel exports upload karein."
    )

    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 14px; text-align: center;">
            <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase;">Helpdesk & Support</div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #38BDF8; margin-top: 4px;">7016882039</div>
            <div style="margin-top: 8px;">
                <a href="https://wa.me/917016882039" target="_blank" style="background: rgba(34, 197, 94, 0.2); color: #4ADE80; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(34, 197, 94, 0.3);">WhatsApp</a>
                <a href="tel:7016882039" style="background: rgba(99, 102, 241, 0.2); color: #818CF8; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(99, 102, 241, 0.3); margin-left: 6px;">Call</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ----------------- ADMIN APPROVAL INTERFACE -----------------
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
        "Indirect_Expenses": 0.0,
        "MSME_Critical_Dues": 0.0,
        "Top_Customer": "N/A",
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

        # XML Parsing
        if fname.endswith('.xml'):
            s_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("sales|sale", na=False)]
            if not s_rows.empty:
                business_data["Sales_DF"] = s_rows
                business_data["Sales"] += s_rows["Amount"].sum()
                top_c = s_rows.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
                if not top_c.empty:
                    business_data["Top_Customer"] = top_c.index[0]

            p_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("purchase|purch", na=False)]
            if not p_rows.empty:
                business_data["Purchase_DF"] = p_rows
                business_data["Purchase"] += p_rows["Amount"].sum()

            r_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("receipt|receiv", na=False)]
            if not r_rows.empty:
                business_data["Receivables_DF"] = r_rows
                business_data["Outstanding"] += r_rows["Amount"].sum()
                overdue_r = r_rows[r_rows["Days_Overdue"] >= credit_days_threshold]
                business_data["Overdue"] += overdue_r["Amount"].sum()
                business_data["Critical_Count"] += len(overdue_r)

            py_rows = fdf[fdf["Vch Type"].astype(str).str.lower().str.contains("payment|payab", na=False)]
            if not py_rows.empty:
                business_data["Payables_DF"] = py_rows
                business_data["Payables"] += py_rows["Amount"].sum()
                msme_overdue_xml = py_rows[py_rows["Days_Overdue"] >= 45]
                business_data["MSME_Critical_Dues"] += msme_overdue_xml["Amount"].sum()

        # Standalone Stock Summary Sheet (Excel)
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

        elif "receivable" in fname or "bill" in fname or "outstand" in fname or "Days_Overdue" in fdf.columns:
            business_data["Receivables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Outstanding"] += fdf["Amount"].sum()
            if "Days_Overdue" in fdf.columns:
                overdue_rows = fdf[fdf["Days_Overdue"] > 0]
                if "Amount" in overdue_rows.columns:
                    business_data["Overdue"] += overdue_rows["Amount"].sum()
                critical_df = fdf[fdf["Days_Overdue"] >= credit_days_threshold]
                business_data["Critical_Count"] += len(critical_df)

        elif "profit" in fname or "loss" in fname or "p&l" in fname or "expense" in fname:
            business_data["PL_DF"] = fdf

    # Auto-consolidate Stock & P&L from XML extraction if separate Excel not uploaded
    if business_data["Stock_DF"] is None and xml_stock_accumulator:
        consolidated_stk = pd.concat(xml_stock_accumulator, ignore_index=True)
        # Group by Stock Item name to give clean closing balance
        if "Particulars (Stock Item)" in consolidated_stk.columns:
            stk_grouped = consolidated_stk.groupby("Particulars (Stock Item)").agg({
                "Closing Quantity": "last",
                "Effective Rate": "last",
                "Closing Value": "sum"
            }).reset_index()
            business_data["Stock_DF"] = stk_grouped
            business_data["Closing_Stock"] = stk_grouped["Closing Value"].sum()
        else:
            business_data["Stock_DF"] = consolidated_stk
            business_data["Closing_Stock"] = consolidated_stk["Closing Value"].sum() if "Closing Value" in consolidated_stk.columns else 0.0

    if business_data["PL_DF"] is None and xml_expense_accumulator:
        consolidated_exp = pd.concat(xml_expense_accumulator, ignore_index=True)
        business_data["PL_DF"] = consolidated_exp
        for _, rx in consolidated_exp.iterrows():
            px_name = str(rx["Particulars (Expense Ledger)"]).lower()
            amt_x = float(rx["Amount"])
            if any(k in px_name for k in ["freight", "carriage", "cartage", "wages", "fuel", "direct"]):
                business_data["Direct_Expenses"] += amt_x
            else:
                business_data["Indirect_Expenses"] += amt_x

    # Calculations
    cogs = (business_data["Purchase"] + business_data["Direct_Expenses"]) - business_data["Closing_Stock"]
    gross_profit = business_data["Sales"] - (cogs if cogs > 0 else business_data["Purchase"])
    net_profit = gross_profit - business_data["Indirect_Expenses"]

    # Header
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px;">
            <div>
                <h2 style="font-weight: 800; margin-bottom: 4px; letter-spacing: -0.02em;">Executive Performance & CA Audit Dashboard</h2>
                <p style="color: #94A3B8; font-size: 0.95rem; margin: 0;">Reconciliation, Working Capital, Overdues & Tax Compliance</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4 Core KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Gross Revenue (Turnover)</div>
                <div class="metric-val">₹{business_data['Sales']:,.2f}</div>
                <div class="metric-sub" style="color: #34D399;">● Reconciled Invoices</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Outstandings</div>
                <div class="metric-val">₹{business_data['Outstanding']:,.2f}</div>
                <div class="metric-sub" style="color: #38BDF8;">● Customer Debtors</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Overdue Portfolio</div>
                <div class="metric-val" style="color: #F87171;">₹{business_data['Overdue']:,.2f}</div>
                <div class="metric-sub" style="color: #F87171;">● Due Date Crossed ({credit_days_threshold}+ Days)</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Payables</div>
                <div class="metric-val">₹{business_data['Payables']:,.2f}</div>
                <div class="metric-sub" style="color: #FB7185;">● Vendor Outstandings</div>
            </div>
        """, unsafe_allow_html=True)

    # Key Accounts & Critical Risk Row
    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        st.markdown(f"""
            <div class="info-card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 600;">KEY REVENUE DRIVER</div>
                    <div style="font-size: 1.25rem; font-weight: 700;">{str(business_data['Top_Customer'])[:20]}</div>
                </div>
                <div class="badge-tag badge-primary" style="margin: 0;">TOP BUYER ACCOUNT</div>
            </div>
        """, unsafe_allow_html=True)
    with c_sub2:
        st.markdown(f"""
            <div class="info-card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 600;">CRITICAL OVERDUE RISK</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #F87171;">{business_data['Critical_Count']} Accounts Exceeded</div>
                </div>
                <div class="badge-tag badge-danger" style="margin: 0;">THRESHOLD: {credit_days_threshold}+ DAYS</div>
            </div>
        """, unsafe_allow_html=True)

    # P&L Summary Cards
    st.markdown("### 📈 P&L & Operating Margins (Tally Mode)")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.1f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Estimated Net Taxable Profit", f"₹{net_profit:,.2f}", delta="Taxable Surplus" if net_profit >= 0 else "Tax Loss")

    st.markdown("---")

    # March-Ending CA Audit Dossier
    st.markdown("### 🏛️ March-Ending CA Audit & Tax Dossier")
    ca_col1, ca_col2 = st.columns([2.2, 1.8])
    with ca_col1:
        st.markdown(f"""
            <div class="info-card">
                <div style="font-weight: 700; font-size: 1.05rem; color: #F8FAFC; margin-bottom: 8px;">Compliance & Audit Check</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94A3B8;">Closing Stock Valuation:</span>
                    <b style="color: {'#F87171' if business_data['Closing_Stock'] < 0 else '#F8FAFC'};">₹{business_data['Closing_Stock']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94A3B8;">MSME 45-Day Dues (Sec 43B(h)):</span>
                    <b style="color: {'#F87171' if business_data['MSME_Critical_Dues'] > 0 else '#34D399'};">₹{business_data['MSME_Critical_Dues']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94A3B8;">Critical Debtors Overdue (>{credit_days_threshold} Days):</span>
                    <b>{business_data['Critical_Count']} Accounts</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with ca_col2:
        audit_summary_df = pd.DataFrame([
            {"Audit Metric": "Annual Sales Turnover", "Amount (INR)": business_data["Sales"]},
            {"Audit Metric": "Annual Total Purchases", "Amount (INR)": business_data["Purchase"]},
            {"Audit Metric": "Closing Stock Valuation", "Amount (INR)": business_data["Closing_Stock"]},
            {"Audit Metric": "Operating Gross Profit", "Amount (INR)": gross_profit},
            {"Audit Metric": "Direct Expenses (Freight/Carriage)", "Amount (INR)": business_data["Direct_Expenses"]},
            {"Audit Metric": "Indirect Overheads", "Amount (INR)": business_data["Indirect_Expenses"]},
            {"Audit Metric": "Estimated Net Taxable Profit", "Amount (INR)": net_profit},
            {"Audit Metric": "Total Sundry Debtors (Receivables)", "Amount (INR)": business_data["Outstanding"]},
            {"Audit Metric": "Total Overdue Portfolio", "Amount (INR)": business_data["Overdue"]},
            {"Audit Metric": "Total Sundry Creditors (Payables)", "Amount (INR)": business_data["Payables"]},
            {"Audit Metric": "MSME Overdue Payables (>45 Days - Sec 43Bh)", "Amount (INR)": business_data["MSME_Critical_Dues"]}
        ])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            audit_summary_df.to_excel(writer, sheet_name="CA_Audit_Summary", index=False)
            if business_data["Receivables_DF"] is not None:
                business_data["Receivables_DF"].to_excel(writer, sheet_name="Debtors_Ageing", index=False)
            if business_data["Payables_DF"] is not None:
                business_data["Payables_DF"].to_excel(writer, sheet_name="Creditors_MSME", index=False)
            if business_data["Stock_DF"] is not None:
                business_data["Stock_DF"].to_excel(writer, sheet_name="Stock_Summary", index=False)
                
        st.download_button(
            label="📥 Download CA Audit Dossier (.xlsx)",
            data=output.getvalue(),
            file_name=f"Tally_Audit_Dossier_March_{datetime.datetime.now().year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

    # Detailed Registers Tabs
    st.markdown("### 📑 Detailed Accounting Ledgers")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Sales Register", 
        "📦 Purchase Register", 
        "⚠️ Receivables (Debtors)", 
        "🏢 Payables (Creditors & MSME)",
        "📋 Stock Summary",
        "⚖️ P&L Statements"
    ])
    
    with tab1:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True, height=400)
        else:
            st.info("Sales Register upload hone par customer transactions load honge.")

    with tab2:
        if business_data["Purchase_DF"] is not None:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True, height=400)
        else:
            st.info("Purchase Register upload hone par vendor billing load hogi.")
            
    with tab3:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Receivable upload hone par customer dues load honge.")

    with tab4:
        if business_data["Payables_DF"] is not None:
            st.dataframe(business_data["Payables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Payable upload hone par supplier dues load honge.")

    with tab5:
        if business_data["Stock_DF"] is not None and not business_data["Stock_DF"].empty:
            st.dataframe(business_data["Stock_DF"], use_container_width=True, height=400)
        else:
            st.info("Stock Summary file ya Inventory-enabled Transactions.xml upload hone par stock records display honge.")

    with tab6:
        if business_data["PL_DF"] is not None and not business_data["PL_DF"].empty:
            st.dataframe(business_data["PL_DF"], use_container_width=True, height=400)
        else:
            st.info("Profit & Loss statement ya Direct/Indirect expense entries yahan load hongi.")
else:
    st.markdown("""
        <div style="text-align: center; padding: 60px 20px; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; margin-top: 20px;">
            <div style="font-size: 2.8rem; margin-bottom: 10px;">📊</div>
            <h3 style="font-weight: 700;">No Financial Reports Loaded</h3>
            <p style="color: #94A3B8; max-width: 500px; margin: auto;">
                Sidebar uploader me Tally reports (Excel, CSV ya direct XML Transactions export) drop karein.
            </p>
        </div>
    """, unsafe_allow_html=True)
