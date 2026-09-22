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
    page_title="Tally Executive Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- DATABASE INITIALIZATION & MIGRATION -----------------
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
    # Device fingerprinting fallback combination
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

# Default Admin Setup
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", role="admin", status="approved", plan="Lifetime", device_hash="ADMIN_DEV", txn_id="ADMIN")

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
    target_keywords = ['date', 'particulars', 'party', 'pending', 'amount', 'vch', 'due', 'debit', 'credit']
    
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
            
    # Standardize column naming
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
        elif "vch no" in c_low:
            col_rename[col] = "Vch No."
            
    df = df.rename(columns=col_rename)
    
    # Solve PyArrow Duplicate Column Names Crash
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f"{dup}_{i}" for i in range(sum(cols == dup))]
    df.columns = cols
    
    # Summary / Total rows filter karein taaki amount double count na ho
    for check_col in ["Party Name", "Date", "Vch Type"]:
        if check_col in df.columns:
            df = df[~df[check_col].astype(str).str.lower().str.contains('total|grand total|closing balance', na=False)]

    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'purchase', 'nan', 'none', ''])]
    
    # Numerical data conversion
    amt_cols = [c for c in df.columns if str(c).startswith("Amount")]
    for ac in amt_cols:
        df[ac] = pd.to_numeric(df[ac].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)

    # Agar Amount 0 ho aur Amount_1 me data ho toh swap/merge karein
    if "Amount_1" in df.columns:
        if "Amount" not in df.columns or df["Amount"].sum() == 0:
            df["Amount"] = df["Amount_1"]
        elif df["Amount_1"].sum() > 0 and df["Amount"].sum() > 0:
            df["Amount"] = df[["Amount", "Amount_1"]].max(axis=1)

    if "Days_Overdue" in df.columns:
        df["Days_Overdue"] = pd.to_numeric(df["Days_Overdue"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
        
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

# ----------------- AUTHENTICATION & TRIAL LOCK -----------------
if not st.session_state["logged_in"]:
    st.title("🔐 Tally Business Intelligence Portal")
    menu = ["Login", "Register (7 Days Free Trial)"]
    choice = st.selectbox("Action", menu)

    if choice == "Login":
        st.subheader("Account Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True):
            res = verify_user(u, p)
            if res:
                role, status, plan, created_at = res
                
                # Check Trial Expiry
                is_expired = False
                if status == "trial":
                    c_date = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    days_passed = (datetime.datetime.now() - c_date).days
                    if days_passed >= 7:
                        is_expired = True
                        status = "expired"
                        c = conn.cursor()
                        c.execute("UPDATE users SET status='expired' WHERE username=?", (u,))
                        conn.commit()

                if is_expired or status == "expired":
                    st.error("⛔ Aapka 7-Day Free Trial poora ho chuka hai. Kripya niche diye plan se renew karein.")
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.session_state["role"] = role
                    st.session_state["status"] = "expired"
                    st.session_state["plan"] = plan
                    st.rerun()
                elif status == "pending":
                    st.warning("⚠️ Aapka payment verification pending hai. Admin approval ke baad dashboard chalu hoga.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.session_state["role"] = role
                    st.session_state["status"] = status
                    st.session_state["plan"] = plan
                    st.session_state["created_at"] = created_at
                    st.rerun()
            else:
                st.error("Galat Username ya Password.")

    elif choice == "Register (7 Days Free Trial)":
        st.subheader("Start 7 Days Free Trial (No Card Required)")
        new_u = st.text_input("Choose Username")
        new_p = st.text_input("Choose Password", type="password")
        
        st.info("💡 7 din ke trial ke baad Monthly (₹499) ya Yearly (₹2,999) plan chun sakte hain.")

        if st.button("Activate Free Trial", use_container_width=True):
            if new_u and new_p:
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=?", (new_u,))
                if c.fetchone():
                    st.error("Yeh Username pehle se maujood hai. Dusra username chunein.")
                else:
                    # Security Check: Device Abuse Prevention
                    dev_hash = get_client_device_hash(new_u)
                    prev_acc = check_device_trial_exists(dev_hash)
                    
                    if prev_acc:
                        st.error(f"🚫 Anti-Abuse Alert: Is device/browser par pehle hi account `{prev_acc[0]}` ke liye Free Trial liya ja chuka hai. Nayi ID se dobara trial nahi liya ja sakta. Kripya subscribe karein.")
                    else:
                        add_user(new_u, new_p, role="client", status="trial", plan="Free Trial (7 Days)", device_hash=dev_hash, txn_id="FREE_TRIAL")
                        st.success("🎉 7 Days Free Trial Activate ho gaya hai! Kripya 'Login' par jaakar sign in karein.")
            else:
                st.error("Kripya Username aur Password dono fill karein.")
    st.stop()

# ----------------- TRIAL EXPIRED PAYMENT SCREEN -----------------
if st.session_state.get("status") == "expired":
    st.error("🚨 AAPKA 7 DAYS TRIAL KHATAM HO GAYA HAI")
    st.subheader("Dashboard ko dubara unlock karne ke liye subscription chunein:")

    plan_sel = st.radio(
        "Choose Plan:",
        ["Monthly Plan — ₹499 / Month", "Yearly Plan — ₹2,999 / Year (Best Value)"]
    )
    amt = 499 if "499" in plan_sel else 2999
    p_name = "Monthly (₹499)" if amt == 499 else "Yearly (₹2999)"
    
    st.write(f"Payment Amount: **₹{amt}**")
    st.write("UPI ID: `tanmayagarwal776@okhdfcbank`")
    
    qr_img = generate_upi_qr("tanmayagarwal776@okhdfcbank", "Tanmay Agarwal", amt)
    st.image(qr_img, caption=f"Scan to Pay ₹{amt}")
    
    pay_tx = st.text_input("Payment karne ke baad 12-digit UPI / UTR Transaction ID daalein:")
    if st.button("Submit Payment for Reactivation", use_container_width=True):
        if pay_tx.strip():
            update_user_payment(st.session_state["username"], p_name, pay_tx.strip())
            st.success("✅ Payment ID submit ho gayi hai! Admin verification ke baad aapka account wapas chalu ho jayega.")
        else:
            st.error("Kripya valid UTR / Transaction number dalein.")
            
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# ----------------- LOGGED IN INTERFACE & TRIAL STATUS -----------------
st.sidebar.markdown(f"👤 **User:** `{st.session_state['username']}`")
if st.session_state["status"] == "trial":
    c_date = datetime.datetime.strptime(st.session_state.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S")
    days_left = max(0, 7 - (datetime.datetime.now() - c_date).days)
    st.sidebar.warning(f"⏳ Free Trial: **{days_left} Days Remaining**")
else:
    st.sidebar.success(f"⭐ Plan: **{st.session_state.get('plan', 'Active')}**")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ----------------- ADMIN PORTAL -----------------
if st.session_state["role"] == "admin":
    st.sidebar.markdown("---")
    admin_mode = st.sidebar.radio("Admin Console", ["Use Bot & Dashboard", "Manage Subscriptions"])
    
    if admin_mode == "Manage Subscriptions":
        st.title("💳 Subscription & Payment Verification Panel")
        c = conn.cursor()
        pending_users = c.execute("SELECT username, plan, txn_id, status FROM users WHERE status='pending'").fetchall()
        
        if pending_users:
            st.info(f"Total Pending Requests: {len(pending_users)}")
            for u_name, u_plan, tx_id, stat in pending_users:
                col_u, col_pl, col_tx, col_btn = st.columns([2, 2, 3, 2])
                col_u.write(f"**User:** {u_name}")
                col_pl.write(f"**Plan:** {u_plan}")
                col_tx.write(f"**Txn Ref:** `{tx_id if tx_id else 'Awaiting'}`")
                if col_btn.button(f"Approve {u_name}", key=f"appr_{u_name}"):
                    c.execute("UPDATE users SET status='approved' WHERE username=?", (u_name,))
                    conn.commit()
                    st.success(f"{u_name} ka account approve kar diya gaya!")
                    st.rerun()
        else:
            st.success("Sabhi subscriptions verified hain. Koi pending request nahi hai.")
        st.stop()

# ----------------- EXECUTIVE DASHBOARD & PARSING -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("Upload Business Reports")
uploaded_files = st.sidebar.file_uploader(
    "Upload Tally Files (Sales, Bills Receivable, DayBook, Purchase)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

if uploaded_files:
    business_data = {
        "Sales": 0.0,
        "Purchase": 0.0,
        "Outstanding": 0.0,
        "Overdue": 0.0,
        "Top_Customer": "N/A",
        "Critical_60_Count": 0,
        "Receivables_DF": None,
        "Sales_DF": None,
        "Purchase_DF": None
    }

    for f in uploaded_files:
        fdf = load_tally_file(f)
        if fdf.empty:
            continue

        fname = f.name.lower()
        vch_types = []
        if "Vch Type" in fdf.columns:
            vch_types = [str(x).lower() for x in fdf["Vch Type"].dropna().unique()]

        # 1. PURCHASE FILE CHECK
        if "purch" in fname or any("purch" in v for v in vch_types):
            business_data["Purchase_DF"] = fdf
            if "Amount" in fdf.columns:
                val = fdf["Amount"].sum()
                if val == 0 and "Amount_1" in fdf.columns:
                    val = fdf["Amount_1"].sum()
                business_data["Purchase"] += val

        # 2. SALES FILE CHECK
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

        # 3. RECEIVABLES / OUTSTANDING FILE CHECK
        elif "receivable" in fname or "bill" in fname or "outstand" in fname or "Days_Overdue" in fdf.columns:
            business_data["Receivables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Outstanding"] += fdf["Amount"].sum()
            if "Days_Overdue" in fdf.columns:
                overdue_rows = fdf[fdf["Days_Overdue"] > 0]
                if "Amount" in overdue_rows.columns:
                    business_data["Overdue"] += overdue_rows["Amount"].sum()
                business_data["Critical_60_Count"] += len(fdf[fdf["Days_Overdue"] >= 60])

    # KPI Summary Cards
    st.markdown("### 🚀 Executive Business KPI")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly Sales", f"₹{business_data['Sales']:,.2f}")
    c2.metric("Total Outstanding", f"₹{business_data['Outstanding']:,.2f}")
    c3.metric("Overdue Dues", f"₹{business_data['Overdue']:,.2f}")
    c4.metric("Top Customer", str(business_data['Top_Customer'])[:20])

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        gross_diff = business_data["Sales"] - business_data["Purchase"]
        st.info(f"**Total Purchases:** ₹{business_data['Purchase']:,.2f} | **Gross Margin:** ₹{gross_diff:,.2f}")
    with col_b:
        st.error(f"**Critical Overdue (60+ Days Risk):** {business_data['Critical_60_Count']} Parties Pending")

    st.markdown("### 📑 Detailed Registers & Breakdown")
    tab1, tab2, tab3 = st.tabs(["Sales Register", "Purchase Register", "Receivables & Outstandings"])
    
    with tab1:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True)
        else:
            st.info("Sales Register file upload hone par yahan display hogi.")

    with tab2:
        if business_data["Purchase_DF"] is not None:
            st.dataframe(business_data["Purchase_DF"], use_container_width=True)
        else:
            st.info("Purchase Register file upload hone par yahan display hogi.")
            
    with tab3:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True)
        else:
            st.info("Bills Receivable upload hone par overdue analysis yahan aayega.")
else:
    st.info("ℹ️ Kripya Tally ki reports (Sales, Purchase, Receivables) sidebar se upload karein.")
