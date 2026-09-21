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

# ----------------- DATABASE INITIALIZATION -----------------
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            status TEXT,
            plan TEXT,
            txn_id TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, role="client", status="pending", plan="Monthly (₹499)", txn_id=""):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)", 
              (username, hash_pw(password), role, status, plan, txn_id))
    conn.commit()

def update_user_payment(username, txn_id):
    c = conn.cursor()
    c.execute("UPDATE users SET txn_id=? WHERE username=?", (txn_id, username))
    conn.commit()

def verify_user(username, password):
    c = conn.cursor()
    c.execute("SELECT role, status, plan FROM users WHERE username=? AND password=?", 
              (username, hash_pw(password)))
    return c.fetchone()

# Default Admin Setup
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", role="admin", status="approved", plan="Lifetime", txn_id="ADMIN")

# ----------------- TALLY DATA PARSER ENGINE -----------------
def load_tally_file(uploaded_file):
    try:
        uploaded_file.seek(0)
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file, header=None)
        else:
            raw_df = pd.read_excel(uploaded_file, header=None)
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
            
    df = df.rename(columns=col_rename)
    
    # Solve Duplicate Column Names Crash
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f"{dup}_{i}" for i in range(sum(cols == dup))]
    df.columns = cols
    
    # Strip Tally To/By Prefixes & filter out system rows
    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'nan', 'none', ''])]
    
    # Convert numerical values safely
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
        
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

if "reg_success_user" not in st.session_state:
    st.session_state["reg_success_user"] = None
    st.session_state["reg_plan_amt"] = 0
    st.session_state["reg_plan_name"] = ""

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
    st.title("🔐 Tally Business Intelligence Suite")
    menu = ["Login", "Register / Subscribe"]
    choice = st.selectbox("Select Action", menu)

    if choice == "Login":
        st.subheader("Sign In")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True):
            res = verify_user(u, p)
            if res:
                role, status, plan = res
                if status == "pending":
                    st.warning("⚠️ Aapka payment verification pending hai. Admin approval ke baad dashboard open hoga.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.session_state["role"] = role
                    st.session_state["status"] = status
                    st.session_state["plan"] = plan
                    st.rerun()
            else:
                st.error("Invalid Username ya Password.")

    elif choice == "Register / Subscribe":
        # Check agar user ne abhi register click kiya hai
        if st.session_state["reg_success_user"] is None:
            st.subheader("Step 1: Account & Plan Selection")
            new_u = st.text_input("Choose Username")
            new_p = st.text_input("Choose Password", type="password")
            plan_option = st.radio(
                "Choose Subscription Plan:",
                ["Monthly Plan — ₹499 / Month", "Yearly Plan — ₹2,999 / Year (Best Value)"]
            )
            
            if st.button("Proceed to Payment & QR", use_container_width=True):
                if new_u and new_p:
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username=?", (new_u,))
                    if c.fetchone():
                        st.error("Yeh Username pehle se maujood hai. Kripya doosra chunein.")
                    else:
                        amt = 499 if "499" in plan_option else 2999
                        p_name = "Monthly (₹499)" if amt == 499 else "Yearly (₹2999)"
                        add_user(new_u, new_p, role="client", status="pending", plan=p_name, txn_id="")
                        st.session_state["reg_success_user"] = new_u
                        st.session_state["reg_plan_amt"] = amt
                        st.session_state["reg_plan_name"] = p_name
                        st.rerun()
                else:
                    st.error("Kripya Username aur Password dono fill karein.")
        else:
            # Registration ke baad QR aur Payment submit ka screen
            st.success(f"✅ Account create ho gaya: **{st.session_state['reg_success_user']}**")
            st.subheader(f"Step 2: Pay for {st.session_state['reg_plan_name']}")
            st.write(f"Payment Amount: **₹{st.session_state['reg_plan_amt']}**")
            st.write("UPI ID: `tanmayagarwal776@okhdfcbank`")
            
            qr_bytes = generate_upi_qr(
                "tanmayagarwal776@okhdfcbank", 
                "Tanmay Agarwal", 
                st.session_state['reg_plan_amt']
            )
            st.image(qr_bytes, caption=f"Scan to Pay ₹{st.session_state['reg_plan_amt']}")
            
            txn_id = st.text_input("Payment ke baad 12-digit UPI / UTR Transaction Ref ID daalein:")
            if st.button("Submit Transaction ID", use_container_width=True):
                if txn_id.strip():
                    update_user_payment(st.session_state["reg_success_user"], txn_id.strip())
                    st.success("🎉 Payment details receive ho gayi hain! Admin approve karte hi aap Login kar sakenge.")
                    st.session_state["reg_success_user"] = None
                else:
                    st.error("Kripya valid UTR / Transaction number daalein.")
    st.stop()

# ----------------- MAIN PORTAL (LOGGED IN) -----------------
st.sidebar.markdown(f"👤 **Logged in as:** `{st.session_state['username']}`")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["status"] = ""
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
                    st.success(f"{u_name} ka subscription activate kar diya gaya!")
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
        "Sales_DF": None
    }

    for f in uploaded_files:
        fdf = load_tally_file(f)
        if fdf.empty:
            continue

        text_corpus = " ".join([str(col).lower() for col in fdf.columns])
        fname = f.name.lower()

        # Receivables / Outstanding Check
        if any("overdue" in c or "pending" in c for c in fdf.columns) or "Days_Overdue" in fdf.columns or "receivable" in fname or "bill" in fname:
            business_data["Receivables_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Outstanding"] += fdf["Amount"].sum()
            if "Days_Overdue" in fdf.columns:
                overdue_rows = fdf[fdf["Days_Overdue"] > 0]
                if "Amount" in overdue_rows.columns:
                    business_data["Overdue"] += overdue_rows["Amount"].sum()
                business_data["Critical_60_Count"] += len(fdf[fdf["Days_Overdue"] >= 60])

        # Sales Register / DayBook Check
        elif "sale" in fname or "sale" in text_corpus or "daybook" in fname:
            business_data["Sales_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Sales"] += fdf["Amount"].sum()
            if "Party Name" in fdf.columns and not fdf.empty:
                top_c = fdf.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
                if not top_c.empty:
                    business_data["Top_Customer"] = top_c.index[0]

        # Purchase Register Check
        elif "purchase" in fname or "purchase" in text_corpus:
            if "Amount" in fdf.columns:
                business_data["Purchase"] += fdf["Amount"].sum()

    # Metrics Summary Row
    st.markdown("### 🚀 Executive Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly Sales", f"₹{business_data['Sales']:,.2f}")
    c2.metric("Total Outstanding", f"₹{business_data['Outstanding']:,.2f}")
    c3.metric("Overdue Dues", f"₹{business_data['Overdue']:,.2f}")
    c4.metric("Top Customer", str(business_data['Top_Customer'])[:18])

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        gross_diff = business_data["Sales"] - business_data["Purchase"]
        st.info(f"**Total Purchases:** ₹{business_data['Purchase']:,.2f} | **Cashflow Margin:** ₹{gross_diff:,.2f}")
    with col_b:
        st.error(f"**Critical Overdue (60+ Days Risk):** {business_data['Critical_60_Count']} Parties Pending")

    st.markdown("### ⚠️ Collection & Ledger Breakdown")
    tab1, tab2 = st.tabs(["Receivables & Overdue Records", "Sales Register Records"])
    
    with tab1:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True)
        else:
            st.info("Bills Receivable upload karein taaki overdue aur risk analysis render ho sake.")
            
    with tab2:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True)
        else:
            st.info("Sales Register upload karein taaki transaction analysis render ho sake.")
else:
    st.info("ℹ️ Kripya Tally ki reports (Sales Register, Bills Receivable, DayBook) sidebar se upload karein.")
