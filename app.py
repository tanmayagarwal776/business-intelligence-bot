import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import qrcode
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

# ----------------- DATABASE INITIALIZATION -----------------
def init_db():
    conn = sqlite3.connect("tally_users_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
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

def add_user(username, password, role="client", status="trial", plan="Free Trial (7 Days)", device_hash="", txn_id=""):
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
              (username, hash_pw(password), role, status, plan, now_str, device_hash, txn_id))
    conn.commit()

def update_user_payment(username, plan, txn_id):
    c = conn.cursor()
    c.execute("UPDATE users SET plan=?, txn_id=?, status='pending' WHERE username=?", (plan, txn_id, username))
    conn.commit()

def verify_user(username, password):
    c = conn.cursor()
    c.execute("SELECT role, status, plan, created_at FROM users WHERE username=? AND password=?", 
              (username, hash_pw(password)))
    return c.fetchone()

# Admin Account Default
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", role="admin", status="approved", plan="Lifetime Enterprise", device_hash="ADMIN_DEV", txn_id="ADMIN")

# ----------------- TALLY DATA PARSER ENGINE -----------------
def load_tally_file(uploaded_file):
    try:
        uploaded_file.seek(0)
        fname = uploaded_file.name.lower()
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
        return pd.DataFrame()

    header_idx = None
    target_keywords = ['date', 'particulars', 'party', 'pending', 'amount', 'vch', 'due', 'debit', 'credit', 'month', 'july', 'august', 'stock', 'balance', 'closing']
    
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

    # Exclude Summary & Total Rows
    is_summary_row = df.astype(str).apply(lambda row: row.str.lower().str.contains('grand total|total:|closing balance|average', na=False)).any(axis=1)
    df = df[~is_summary_row]

    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].replace(['None', 'nan', '', None], pd.NA).ffill()
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'purchase', 'nan', 'none', 'total'])]

    df = df.reset_index(drop=True)
    return df

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["status"] = ""
    st.session_state["plan"] = ""
    st.session_state["created_at"] = ""

def generate_upi_qr(vpa, name, amount):
    upi_url = f"upi://pay?pa={vpa}&pn={quote(name)}&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

# ----------------- AUTHENTICATION VIEW -----------------
if not st.session_state["logged_in"]:
    st.markdown("""
        <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
            <div class="badge-tag badge-primary">ENTERPRISE AUDIT & TAX SUITE</div>
            <h1 style="font-weight: 800; font-size: 2.6rem; letter-spacing: -0.02em; margin-bottom: 8px;">Tally Executive Suite</h1>
            <p style="color: #94A3B8; font-size: 1.05rem;">Turn raw Tally exports into executive P&L, March-ending CA dossier & risk analytics</p>
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
            if st.button("Log In to Dashboard", use_container_width=True, type="primary"):
                res = verify_user(u, p)
                if res:
                    role, status, plan, created_at = res
                    is_expired = False
                    if status == "trial":
                        c_date = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        if (datetime.datetime.now() - c_date).days >= 7:
                            is_expired = True
                            status = "expired"
                            c = conn.cursor()
                            c.execute("UPDATE users SET status='expired' WHERE username=?", (u,))
                            conn.commit()

                    if is_expired or status == "expired":
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u
                        st.session_state["role"] = role
                        st.session_state["status"] = "expired"
                        st.session_state["plan"] = plan
                        st.rerun()
                    elif status == "pending":
                        st.warning("⚠️ Payment verification under review. Admin will approve shortly.")
                    else:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u
                        st.session_state["role"] = role
                        st.session_state["status"] = status
                        st.session_state["plan"] = plan
                        st.session_state["created_at"] = created_at
                        st.rerun()
                else:
                    st.error("Invalid username or password.")

            st.markdown("""
                <div class="support-box">
                    <span style="color: #94A3B8; font-size: 0.85rem;">📞 Need assistance? Customer Care:</span><br>
                    <a href="tel:7016882039" style="color: #818CF8; font-weight: 700; text-decoration: none; font-size: 1rem;">+91 7016882039</a>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        elif choice == "Start 7-Day Free Trial":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            new_u = st.text_input("Choose Username", placeholder="e.g. business_audit")
            new_p = st.text_input("Choose Password", type="password", placeholder="••••••••")
            
            st.caption("🔒 7-day full access included. No credit card required.")
            if st.button("Activate Free Trial", use_container_width=True, type="primary"):
                if new_u and new_p:
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (new_u,))
                    if c.fetchone():
                        st.error("Username is already claimed.")
                    else:
                        dev_hash = get_client_device_hash(new_u)
                        prev_acc = check_device_trial_exists(dev_hash)
                        if prev_acc:
                            st.error(f"🚫 Abuse Prevention: A trial is already active for this workstation (`{prev_acc[0]}`). Please purchase a subscription.")
                        else:
                            add_user(new_u, new_p, role="client", status="trial", plan="Free Trial (7 Days)", device_hash=dev_hash, txn_id="FREE_TRIAL")
                            st.success("🎉 Trial activated successfully! Switch to 'Sign In' to begin.")
                else:
                    st.error("Please fill in both fields.")
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
                <span style="color: #94A3B8; font-size: 0.85rem;">💬 Payment or Verification Query?</span><br>
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

    # Business Rules
    st.markdown("#### ⚙️ Business Rules")
    credit_days_threshold = st.slider(
        "Standard Credit Period (Days)", 
        min_value=15, 
        max_value=180, 
        value=65, 
        step=5,
        help="Salt, Manufacturing ya FMCG ke mutabiq allowed credit days set karein."
    )

    st.markdown("---")
    st.markdown("#### 📂 Tally Reports Import")
    uploaded_files = st.file_uploader(
        "Upload Tally Exports (.xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help="Drop Sales, Purchase, Receivables, Payables, Stock Summary, Trial Balance ya P&L files."
    )

    st.markdown("---")
    # Customer Care Widget
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
    pending_users = c.execute("SELECT username, plan, txn_id, status FROM users WHERE status='pending'").fetchall()
    
    if pending_users:
        st.info(f"Requests Awaiting Verification: {len(pending_users)}")
        for u_name, u_plan, tx_id, stat in pending_users:
            with st.container():
                st.markdown("<div class='info-card'>", unsafe_allow_html=True)
                col_u, col_pl, col_tx, col_btn = st.columns([2, 2, 3, 1.5])
                col_u.markdown(f"**Client:** `{u_name}`")
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

    for f in uploaded_files:
        fdf = load_tally_file(f)
        if fdf.empty:
            continue

        fname = f.name.lower()
        vch_types = []
        if "Vch Type" in fdf.columns:
            vch_types = [str(x).lower() for x in fdf["Vch Type"].dropna().unique()]

        # 1. STOCK SUMMARY (CLOSING INVENTORY)
        if "stock" in fname or "inventory" in fname:
            business_data["Stock_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Closing_Stock"] += fdf["Amount"].sum()

        # 2. BILLS PAYABLE (VENDOR OUTSTANDINGS / MSME SECTION 43B(H))
        elif "payable" in fname or "vendor_outstand" in fname:
            business_data["Payables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Payables"] += fdf["Amount"].sum()
            if "Days_Overdue" in fdf.columns:
                # MSME Section 43B(h) Mandate: 45 Days Exceeded Check
                msme_overdue = fdf[fdf["Days_Overdue"] >= 45]
                if "Amount" in msme_overdue.columns:
                    business_data["MSME_Critical_Dues"] += msme_overdue["Amount"].sum()

        # 3. PURCHASE REGISTER
        elif "purch" in fname or any("purch" in v for v in vch_types):
            business_data["Purchase_DF"] = fdf
            if "Amount" in fdf.columns:
                val = fdf["Amount"].sum()
                if val == 0 and "Amount_1" in fdf.columns:
                    val = fdf["Amount_1"].sum()
                business_data["Purchase"] += val

        # 4. SALES REGISTER / DAYBOOK
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

        # 5. BILLS RECEIVABLE (CUSTOMER OUTSTANDINGS)
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

        # 6. PROFIT & LOSS / EXPENSES
        elif "profit" in fname or "loss" in fname or "p&l" in fname or "expense" in fname:
            business_data["PL_DF"] = fdf
            if "Amount" in fdf.columns and "Party Name" in fdf.columns:
                for _, r in fdf.iterrows():
                    p_name = str(r["Party Name"]).lower()
                    amt = float(r["Amount"])
                    if any(x in p_name for x in ["freight", "wages", "carriage", "factory", "fuel", "direct"]):
                        business_data["Direct_Expenses"] += amt
                    else:
                        business_data["Indirect_Expenses"] += amt

    # Calculations
    cogs = (business_data["Purchase"] + business_data["Direct_Expenses"]) - business_data["Closing_Stock"]
    gross_profit = business_data["Sales"] - (cogs if cogs > 0 else business_data["Purchase"])
    net_profit = gross_profit - business_data["Indirect_Expenses"]
    net_liquidity = business_data["Outstanding"] - business_data["Payables"]

    # Header
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px;">
            <div>
                <h2 style="font-weight: 800; margin-bottom: 4px; letter-spacing: -0.02em;">Executive Performance & CA Audit Dashboard</h2>
                <p style="color: #94A3B8; font-size: 0.95rem; margin: 0;">March-Ending Reconciliation, P&L, Working Capital & Exposure Analysis</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4 Executive KPI Cards
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
                <div class="metric-label">Receivables (Sundry Debtors)</div>
                <div class="metric-val">₹{business_data['Outstanding']:,.2f}</div>
                <div class="metric-sub" style="color: #38BDF8;">● Market Dues</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Payables (Sundry Creditors)</div>
                <div class="metric-val">₹{business_data['Payables']:,.2f}</div>
                <div class="metric-sub" style="color: #FB7185;">● Supplier Liabilities</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Net Working Liquidity</div>
                <div class="metric-val" style="color: {'#34D399' if net_liquidity >= 0 else '#F87171'};">
                    ₹{net_liquidity:,.2f}
                </div>
                <div class="metric-sub" style="color: #94A3B8;">● (Debtors - Creditors)</div>
            </div>
        """, unsafe_allow_html=True)

    # P&L Summary Cards
    st.markdown("### 📈 P&L & Operating Margins (Tally Mode)")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.1f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Estimated Net Taxable Profit", f"₹{net_profit:,.2f}", delta="Taxable Surplus" if net_profit >= 0 else "Tax Loss Carry-Forward")

    st.markdown("---")

    # March-Ending CA Audit Dossier Banner
    st.markdown("### 🏛️ March-Ending CA Audit & Tax Dossier")
    ca_col1, ca_col2 = st.columns([2.2, 1.8])
    with ca_col1:
        st.markdown(f"""
            <div class="info-card">
                <div style="font-weight: 700; font-size: 1.1rem; color: #F8FAFC; margin-bottom: 8px;">Compliance & Filing Health Check</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94A3B8;">Closing Stock Valuation:</span>
                    <b>₹{business_data['Closing_Stock']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94A3B8;">MSME 45-Day Rule Liability (Sec 43B(h)):</span>
                    <b style="color: {'#F87171' if business_data['MSME_Critical_Dues'] > 0 else '#34D399'};">₹{business_data['MSME_Critical_Dues']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94A3B8;">Overdue Customer Receivables:</span>
                    <b>₹{business_data['Overdue']:,.2f}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94A3B8;">Critical Risk Accounts (>{credit_days_threshold} Days):</span>
                    <b>{business_data['Critical_Count']} Accounts</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with ca_col2:
        st.markdown("""
            <div class="info-card">
                <div style="font-weight: 700; font-size: 1.05rem; color: #F8FAFC; margin-bottom: 6px;">Direct Export for Chartered Accountant</div>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 12px;">
                    Apne CA ko bhejne ke liye consolidated Audit Sheet download karein. Isme Turnover, COGS, Net Profit, Debtors/Creditors Summary aur MSME compliance ek sath taiyar hai.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Generate CA Audit Dossier Excel
        audit_summary_df = pd.DataFrame([
            {"Audit Metric": "Annual Sales Turnover", "Amount (INR)": business_data["Sales"]},
            {"Audit Metric": "Annual Total Purchases", "Amount (INR)": business_data["Purchase"]},
            {"Audit Metric": "Closing Stock Valuation", "Amount (INR)": business_data["Closing_Stock"]},
            {"Audit Metric": "Gross Profit", "Amount (INR)": gross_profit},
            {"Audit Metric": "Direct Expenses (Freight/Carriage)", "Amount (INR)": business_data["Direct_Expenses"]},
            {"Audit Metric": "Indirect Overheads", "Amount (INR)": business_data["Indirect_Expenses"]},
            {"Audit Metric": "Estimated Net Taxable Profit", "Amount (INR)": net_profit},
            {"Audit Metric": "Total Sundry Debtors (Receivables)", "Amount (INR)": business_data["Outstanding"]},
            {"Audit Metric": "Total Sundry Creditors (Payables)", "Amount (INR)": business_data["Payables"]},
            {"Audit Metric": "MSME Overdue Payables (>45 Days - Sec 43Bh)", "Amount (INR)": business_data["MSME_Critical_Dues"]},
            {"Audit Metric": "Top Buyer Account", "Amount (INR)": business_data["Top_Customer"]}
        ])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            audit_summary_df.to_excel(writer, sheet_name="CA_Audit_Summary", index=False)
            if business_data["Receivables_DF"] is not None:
                business_data["Receivables_DF"].to_excel(writer, sheet_name="Debtors_Ageing", index=False)
            if business_data["Payables_DF"] is not None:
                business_data["Payables_DF"].to_excel(writer, sheet_name="Creditors_MSME", index=False)
                
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
            st.info("Sales Register upload hone par customer transactions display honge.")

    with tab2:
        if business_data["Purchase_DF"] is not None:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True, height=400)
        else:
            st.info("Purchase Register upload hone par vendor billing display hogi.")
            
    with tab3:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Receivable upload hone par aged customer dues load honge.")

    with tab4:
        if business_data["Payables_DF"] is not None:
            st.dataframe(business_data["Payables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Payable upload hone par supplier dues & MSME 45-day status load honge.")

    with tab5:
        if business_data["Stock_DF"] is not None:
            st.dataframe(business_data["Stock_DF"], use_container_width=True, height=400)
        else:
            st.info("Stock Summary file upload karein closing inventory valuation calculate karne ke liye.")

    with tab6:
        if business_data["PL_DF"] is not None:
            st.dataframe(business_data["PL_DF"], use_container_width=True, height=400)
        else:
            st.info("Profit & Loss / Expense statement upload hone par itemized overheads load honge.")
else:
    st.markdown("""
        <div style="text-align: center; padding: 60px 20px; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; margin-top: 20px;">
            <div style="font-size: 2.8rem; margin-bottom: 10px;">📊</div>
            <h3 style="font-weight: 700;">No Financial Reports Loaded</h3>
            <p style="color: #94A3B8; max-width: 500px; margin: auto;">
                Sidebar uploader me Tally reports (Sales, Purchase, Receivables, Payables, Stock Summary ya P&L) drop karein taaki CA-ready audit sheets generate ho sakein.
            </p>
        </div>
    """, unsafe_allow_html=True)
