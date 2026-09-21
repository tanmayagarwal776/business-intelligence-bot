import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import qrcode
from io import BytesIO
from urllib.parse import quote

# ----------------- CONFIG & DATABASE SETUP -----------------
st.set_page_config(page_title="Tally Executive Business Intelligence", layout="wide")

def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            status TEXT,
            txn_id TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password, role="client", status="pending", txn_id=""):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)", 
              (username, hash_pw(password), role, status, txn_id))
    conn.commit()

def verify_user(username, password):
    c = conn.cursor()
    c.execute("SELECT role, status FROM users WHERE username=? AND password=?", 
              (username, hash_pw(password)))
    return c.fetchone()

# Default Admin create karein agar exist na ho
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username='tanmay_admin'")
if not c.fetchone():
    add_user("tanmay_admin", "admin123", role="admin", status="approved")

# ----------------- TALLY DATA PARSER -----------------
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
    
    if "Party Name" in df.columns:
        df["Party Name"] = df["Party Name"].astype(str).str.replace(r'^(To\s+|By\s+)', '', case=False, regex=True).str.strip()
        df = df[~df["Party Name"].str.lower().isin(['to', 'by', 'sales', 'nan', 'none', ''])]
    
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
        
    if "Days_Overdue" in df.columns:
        df["Days_Overdue"] = pd.to_numeric(df["Days_Overdue"].astype(str).str.replace(',', '').str.replace(' ', ''), errors='coerce').fillna(0)
        
    df = df.reset_index(drop=True)
    return df

# ----------------- SESSION STATE & AUTH -----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["status"] = ""

def generate_upi_qr(vpa, name, amount):
    upi_url = f"upi://pay?pa={vpa}&pn={quote(name)}&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

# ----------------- LOGIN / SIGNUP / PAYMENT SCREEN -----------------
if not st.session_state["logged_in"]:
    st.title("🔐 Tally Business Intelligence Portal")
    menu = ["Login", "Register / Subscribe"]
    choice = st.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Account Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            res = verify_user(u, p)
            if res:
                role, status = res
                if status == "pending":
                    st.warning("⚠️ Aapka payment verification pending hai. Admin approval ke baad dashboard open hoga.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u
                    st.session_state["role"] = role
                    st.session_state["status"] = status
                    st.rerun()
            else:
                st.error("Invalid Username ya Password.")

    elif choice == "Register / Subscribe":
        st.subheader("New Business Subscription")
        new_u = st.text_input("Choose Username")
        new_p = st.text_input("Choose Password", type="password")
        st.markdown("#### Subscription Plan: ₹999 / Year")
        st.write("Neeche diye QR code par payment karke UTR/Transaction ID daalein:")
        
        # QR Code Generation (Replace with your actual UPI ID)
        qr_bytes = generate_upi_qr("your-upi-id@okaxis", "Business Intelligence", "999")
        st.image(qr_bytes, caption="Scan to Pay ₹999")
        
        txn_id = st.text_input("Enter UPI / UTR Transaction Reference ID")
        if st.button("Submit Payment for Verification"):
            if new_u and new_p and txn_id:
                add_user(new_u, new_p, role="client", status="pending", txn_id=txn_id)
                st.success("Registration aur Payment details receive ho gayi hain! Admin approval ke baad aap login kar sakenge.")
            else:
                st.error("Kripya sabhi fields fill karein.")
    st.stop()

# ----------------- LOGGED IN INTERFACE -----------------
st.sidebar.markdown(f"**Logged in as:** `{st.session_state['username']}`")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["status"] = ""
    st.rerun()

# ----------------- ADMIN PANEL -----------------
if st.session_state["role"] == "admin":
    st.sidebar.markdown("---")
    admin_mode = st.sidebar.radio("Admin Mode", ["Use Bot", "Approve Payments"])
    
    if admin_mode == "Approve Payments":
        st.title("💳 Subscription & Payment Approval Panel")
        c = conn.cursor()
        pending_users = c.execute("SELECT username, txn_id, status FROM users WHERE status='pending'").fetchall()
        
        if pending_users:
            for u_name, tx_id, stat in pending_users:
                col_u, col_tx, col_btn = st.columns([2, 3, 2])
                col_u.write(f"**User:** {u_name}")
                col_tx.write(f"**Txn ID:** `{tx_id}`")
                if col_btn.button(f"Approve {u_name}", key=f"appr_{u_name}"):
                    c.execute("UPDATE users SET status='approved' WHERE username=?", (u_name,))
                    conn.commit()
                    st.success(f"{u_name} ko approve kar diya gaya!")
                    st.rerun()
        else:
            st.info("Abhi koi pending subscription payment approval nahi hai.")
        st.stop()

# ----------------- EXECUTIVE DASHBOARD & BOT -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("Upload Business Reports")
uploaded_files = st.sidebar.file_uploader(
    "Upload Tally Files (Sales, Receivables, Purchase etc.)",
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

        # Sales Check / DayBook
        elif "sale" in fname or "sale" in text_corpus or "daybook" in fname:
            business_data["Sales_DF"] = fdf
            if "Amount" in fdf.columns:
                business_data["Sales"] += fdf["Amount"].sum()
            if "Party Name" in fdf.columns and not fdf.empty:
                top_c = fdf.groupby("Party Name")["Amount"].sum().sort_values(ascending=False)
                if not top_c.empty:
                    business_data["Top_Customer"] = top_c.index[0]

        # Purchase Check
        elif "purchase" in fname or "purchase" in text_corpus:
            if "Amount" in fdf.columns:
                business_data["Purchase"] += fdf["Amount"].sum()

    st.markdown("### 🚀 Executive Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly Sales", f"₹{business_data['Sales']:,.2f}")
    c2.metric("Outstanding", f"₹{business_data['Outstanding']:,.2f}")
    c3.metric("Overdue", f"₹{business_data['Overdue']:,.2f}")
    c4.metric("Top Customer", str(business_data['Top_Customer'])[:18])

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"**Total Purchases:** ₹{business_data['Purchase']:,.2f}")
    with col_b:
        st.warning(f"**Critical Overdue (60+ Days):** {business_data['Critical_60_Count']} Parties")

    st.markdown("### ⚠️ Collection & Overdue Breakdown")
    tab1, tab2 = st.tabs(["Receivables & Overdue Records", "Sales Register"])
    
    with tab1:
        if business_data["Receivables_DF"] is not None:
            st.dataframe(business_data["Receivables_DF"], use_container_width=True)
        else:
            st.info("Bills Receivable upload karein taaki overdue aur risk breakdown yahan load ho sake.")
            
    with tab2:
        if business_data["Sales_DF"] is not None:
            st.dataframe(business_data["Sales_DF"], use_container_width=True)
        else:
            st.info("Sales Register upload karein taaki transactions yahan load ho sakein.")
else:
    st.info("ℹ️ Tally ki reports (Sales Register, Receivables ya DayBook) sidebar se upload karein.")
