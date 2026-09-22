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
    page_title="Tally Executive Financial Intelligence",
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

# ----------------- TALLY MULTI-REPORT PARSER -----------------
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
    target_keywords = ['date', 'particulars', 'party', 'pending', 'amount', 'vch', 'due', 'debit', 'credit', 'expense', 'income']
    
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
        if "party" in c_low or "particular" in c_low or "customer" in c_low:
            col_rename[col] = "Party Name"
        elif "pending" in c_low or "amount" in c_low or "balance" in c_low or "debit" in c_low or "credit" in c_low:
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
    
    # Handle Duplicate Column Headers
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f"{dup}_{i}" for i in range(sum(cols == dup))]
    df.columns = cols
    
    # Numeric conversions
    amt_cols = [c for c in df.columns if str(c).startswith("Amount")]
    for ac in amt_cols:
        df[ac] = pd.to_numeric(df[ac].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    if "Amount_1" in df.columns:
        if "Amount" not in df.columns or df["Amount"].sum() == 0:
            df["Amount"] = df["Amount_1"]
        elif df["Amount_1"].sum() > 0 and df["Amount"].sum() > 0:
            df["Amount"] = df[["Amount", "Amount_1"]].max(axis=1)

    if "Days_Overdue" in df.columns:
        df["Days_Overdue"] = pd.to_numeric(df["Days_Overdue"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    # Summary Row Strip
    for check_col in ["Party Name", "Date", "Vch Type", "Vch No."]:
        if check_col in df.columns:
            df = df[~df[check_col].astype(str).str.lower().str.contains('total|grand total|closing balance', na=False)]

    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].replace(['None', 'nan', '', None], pd.NA).ffill()
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'purchase', 'nan', 'none', ''])]

    if "Vch No." in df.columns and "Date" in df.columns:
        df = df[~(df["Vch No."].isna() & df["Date"].isna())]
    elif "Date" in df.columns:
        df = df[df["Date"].notna() & (~df["Date"].astype(str).str.lower().isin(['none', 'nan', '']))]

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
        <div style="text-align: center; margin-top: 40px; margin-bottom: 30px;">
            <div class="badge-tag badge-primary">ENTERPRISE INTELLIGENCE</div>
            <h1 style="font-weight: 800; font-size: 2.6rem; letter-spacing: -0.02em; margin-bottom: 8px;">Tally Executive Suite</h1>
            <p style="color: #94A3B8; font-size: 1.05rem;">Turn raw accounting registers into executive P&L, working capital & risk insights</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        menu = ["Sign In", "Start 7-Day Free Trial"]
        choice = st.segmented_control("Access Mode", menu, default="Sign In")

        if choice == "Sign In":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            u = st.text_input("Username", placeholder="Enter your business ID")
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
            st.markdown("</div>", unsafe_allow_html=True)

        elif choice == "Start 7-Day Free Trial":
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            new_u = st.text_input("Choose Username", placeholder="e.g. accounts_head")
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
        if admin_mode == "License Approvals":
            st.markdown("---")
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
        help="Drop Sales, Purchase, Receivables, Payables, or P&L statement files."
    )

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
        "Direct_Expenses": 0.0,
        "Indirect_Expenses": 0.0,
        "Top_Customer": "N/A",
        "Critical_Count": 0,
        "Receivables_DF": None,
        "Payables_DF": None,
        "Sales_DF": None,
        "Purchase_DF": None,
        "PL_DF": None
    }

    for f in uploaded_files:
        fdf = load_tally_file(f)
        if fdf.empty:
            continue

        fname = f.name.lower()
        cols_text = " ".join([str(c).lower() for c in fdf.columns])
        vch_types = []
        if "Vch Type" in fdf.columns:
            vch_types = [str(x).lower() for x in fdf["Vch Type"].dropna().unique()]

        # 1. BILLS PAYABLE (VENDOR OUTSTANDINGS)
        if "payable" in fname or "vendor_outstand" in fname:
            business_data["Payables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Payables"] += fdf["Amount"].sum()

        # 2. PURCHASE REGISTER
        elif "purch" in fname or any("purch" in v for v in vch_types):
            business_data["Purchase_DF"] = fdf
            if "Amount" in fdf.columns:
                val = fdf["Amount"].sum()
                if val == 0 and "Amount_1" in fdf.columns:
                    val = fdf["Amount_1"].sum()
                business_data["Purchase"] += val

        # 3. SALES REGISTER / DAYBOOK
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

        # 4. BILLS RECEIVABLE (CUSTOMER OUTSTANDINGS)
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

        # 5. PROFIT & LOSS / EXPENSE STATEMENTS
        elif "profit" in fname or "loss" in fname or "p&l" in fname or "expense" in fname:
            business_data["PL_DF"] = fdf
            if "Amount" in fdf.columns and "Party Name" in fdf.columns:
                # Classify direct vs indirect expenses
                for _, r in fdf.iterrows():
                    p_name = str(r["Party Name"]).lower()
                    amt = float(r["Amount"])
                    if any(x in p_name for x in ["freight", "wages", "carriage", "factory", "fuel"]):
                        business_data["Direct_Expenses"] += amt
                    else:
                        business_data["Indirect_Expenses"] += amt

    # Core Calculations
    gross_profit = business_data["Sales"] - (business_data["Purchase"] + business_data["Direct_Expenses"])
    net_profit = gross_profit - business_data["Indirect_Expenses"]
    net_liquidity = business_data["Outstanding"] - business_data["Payables"]

    # Header
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px;">
            <div>
                <h2 style="font-weight: 800; margin-bottom: 4px; letter-spacing: -0.02em;">Executive Financial Performance</h2>
                <p style="color: #94A3B8; font-size: 0.95rem; margin: 0;">Comprehensive P&L, Working Capital & Exposure Analysis</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 4 Executive KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Revenue / Gross Sales</div>
                <div class="metric-val">₹{business_data['Sales']:,.2f}</div>
                <div class="metric-sub" style="color: #34D399;">● Reconciled Invoices</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Receivables (Aana Hai)</div>
                <div class="metric-val">₹{business_data['Outstanding']:,.2f}</div>
                <div class="metric-sub" style="color: #38BDF8;">● Market Dues</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Payables (Dena Hai)</div>
                <div class="metric-val">₹{business_data['Payables']:,.2f}</div>
                <div class="metric-sub" style="color: #FB7185;">● Vendor Outstandings</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Net Working Liquidity</div>
                <div class="metric-val" style="color: {'#34D399' if net_liquidity >= 0 else '#F87171'};">
                    ₹{net_liquidity:,.2f}
                </div>
                <div class="metric-sub" style="color: #94A3B8;">● (Receivables - Payables)</div>
            </div>
        """, unsafe_allow_html=True)

    # Profit & Loss Statement Summary Card
    st.markdown("### 📈 Profit & Loss Summary (Tally Mode)")
    pl_c1, pl_c2, pl_c3, pl_c4 = st.columns(4)
    pl_c1.metric("Gross Turnover", f"₹{business_data['Sales']:,.2f}")
    pl_c2.metric("Total Procurement (COGS)", f"₹{business_data['Purchase']:,.2f}")
    pl_c3.metric("Operating Gross Profit", f"₹{gross_profit:,.2f}", delta=f"{(gross_profit / business_data['Sales'] * 100):.1f}% Margin" if business_data['Sales'] > 0 else "0%")
    pl_c4.metric("Estimated Net Profit", f"₹{net_profit:,.2f}", delta="Net Return" if net_profit >= 0 else "Operating Deficit")

    st.markdown("---")

    # Risk & Procurement Row
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

    # Detailed Ledgers & Analysis Tabs
    st.markdown("### 📑 Detailed Accounting Registers")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Sales Register", 
        "📦 Purchase Register", 
        "⚠️ Receivables (Customers)", 
        "🏢 Payables (Vendors)",
        "📋 P&L Statements"
    ])
    
    with tab1:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True, height=400)
        else:
            st.info("Sales Register upload hone par customer transactions yahan display honge.")

    with tab2:
        if business_data["Purchase_DF"] is not None:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True, height=400)
        else:
            st.info("Purchase Register upload hone par vendor billing details yahan display hogi.")
            
    with tab3:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Receivable upload hone par aged customer dues yahan aayenge.")

    with tab4:
        if business_data["Payables_DF"] is not None:
            st.dataframe(business_data["Payables_DF"], use_container_width=True, height=400)
        else:
            st.info("Bills Payable upload hone par supplier dues yahan display honge.")

    with tab5:
        if business_data["PL_DF"] is not None:
            st.dataframe(business_data["PL_DF"], use_container_width=True, height=400)
        else:
            st.info("Profit & Loss / Expense report upload hone par itemized overheads yahan load honge.")
else:
    st.markdown("""
        <div style="text-align: center; padding: 60px 20px; border: 1px dashed rgba(255,255,255,0.15); border-radius: 18px; margin-top: 20px;">
            <div style="font-size: 2.8rem; margin-bottom: 10px;">📊</div>
            <h3 style="font-weight: 700;">No Financial Reports Loaded</h3>
            <p style="color: #94A3B8; max-width: 500px; margin: auto;">
                Sidebar uploader me apne Tally export reports (Sales Register, Purchase Register, Receivables, Payables, ya Profit & Loss statement) drop karein.
            </p>
        </div>
    """, unsafe_allow_html=True)
