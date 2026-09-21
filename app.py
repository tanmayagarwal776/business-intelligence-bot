
import streamlit as st
import pandas as pd
import datetime
import sqlite3
import hashlib
import qrcode
from io import BytesIO
from urllib.parse import quote

def load_tally_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        raw_df = pd.read_csv(uploaded_file, header=None)
    else:
        raw_df = pd.read_excel(uploaded_file, header=None)
    
    header_idx = None
    target_keywords = ['date', 'particulars', 'party', 'vch no', 'voucher', 'debit', 'credit', 'amount']
    
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
    df = df.reset_index(drop=True)
    return df
st.set_page_config(page_title="Business Intelligence Bot", page_icon="💼", layout="wide")

# ==========================================
# ⚙️ CONFIGURATION (Apni Details Dalein)
# ==========================================
MY_UPI_ID = "tanmayagarwal776@okhdfcbank"       # <-- Yahan apni real UPI ID likhein
BUSINESS_NAME = "Business Intelligence Bot"
ADMIN_USERNAME = "tanmay_admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()  # Admin login password

MONTHLY_PRICE = 499
YEARLY_PRICE = 3999

# ==========================================
# 🗄️ DATABASE INITIALIZATION
# ==========================================
conn = sqlite3.connect('business_saas.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        is_paid INTEGER,
        plan_expiry DATE
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        plan TEXT,
        amount INTEGER,
        utr_number TEXT,
        date_submitted TEXT,
        status TEXT
    )
''')
conn.commit()

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_upi_qr(amount, note):
    upi_url = f"upi://pay?pa={MY_UPI_ID}&pn={quote(BUSINESS_NAME)}&am={amount}&cu=INR&tn={quote(note)}"
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), upi_url

# ==========================================
# 🔐 SESSION STATES
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "is_paid" not in st.session_state:
    st.session_state.is_paid = False

# ==========================================
# 1. LOGIN & SIGNUP SCREEN
# ==========================================
if not st.session_state.authenticated:
    st.title("🔐 Business Intelligence Bot - Login")
    tab_login, tab_signup = st.tabs(["Client Login", "New Registration"])

    with tab_login:
        user_input = st.text_input("Username", key="login_u")
        pass_input = st.text_input("Password", type="password", key="login_p")
        if st.button("Log In", use_container_width=True):
            h_input = hash_pass(pass_input)
            if user_input == ADMIN_USERNAME and h_input == ADMIN_PASSWORD_HASH:
                st.session_state.authenticated = True
                st.session_state.username = user_input
                st.session_state.is_paid = True
                st.success("Admin login successful!")
                st.rerun()
            else:
                c.execute("SELECT is_paid, plan_expiry FROM users WHERE username = ? AND password = ?", (user_input, h_input))
                record = c.fetchone()
                if record:
                    st.session_state.authenticated = True
                    st.session_state.username = user_input
                    today_str = datetime.date.today().isoformat()
                    if record[0] == 1 and str(record[1]) >= today_str:
                        st.session_state.is_paid = True
                    else:
                        st.session_state.is_paid = False
                    st.rerun()
                else:
                    st.error("Invalid Username or Password.")

    with tab_signup:
        new_u = st.text_input("Choose Username", key="reg_u")
        new_p = st.text_input("Choose Password", type="password", key="reg_p")
        if st.button("Create Account", use_container_width=True):
            if new_u and new_p:
                try:
                    c.execute("INSERT INTO users VALUES (?, ?, 0, ?)", (new_u, hash_pass(new_p), datetime.date.today().isoformat()))
                    conn.commit()
                    st.success("Account created successfully! Please switch to Login tab.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists.")
            else:
                st.warning("Please fill all details.")

# ==========================================
# 2. LOGGED IN PORTAL
# ==========================================
else:
    col_u, col_out = st.sidebar.columns([3, 1])
    col_u.write(f"Logged in as: **{st.session_state.username}**")
    if col_out.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.is_paid = False
        st.rerun()

    is_admin = (st.session_state.username == ADMIN_USERNAME)

    # ADMIN APPROVAL PANEL
    if is_admin:
        st.sidebar.markdown("---")
        admin_tab = st.sidebar.radio("Admin Mode", ["Use Bot", "Approve Payments"])
        
        if admin_tab == "Approve Payments":
            st.title("💳 Pending GPay / PhonePe Approvals")
            pending_df = pd.read_sql_query("SELECT id, username, plan, amount, utr_number, date_submitted FROM payments WHERE status = 'PENDING'", conn)

            if pending_df.empty:
                st.success("No pending payment approvals.")
            else:
                for idx, row in pending_df.iterrows():
                    with st.expander(f"Payment: {row['username']} - ₹{row['amount']} ({row['plan']})", expanded=True):
                        st.write(f"**UTR No:** `{row['utr_number']}` | **Date:** {row['date_submitted']}")
                        btn1, btn2 = st.columns(2)
                        if btn1.button("✅ Approve Access", key=f"app_{row['id']}"):
                            days_to_add = 365 if row['plan'] == "Yearly" else 30
                            new_expiry = (datetime.date.today() + datetime.timedelta(days=days_to_add)).isoformat()
                            c.execute("UPDATE users SET is_paid = 1, plan_expiry = ? WHERE username = ?", (new_expiry, row['username']))
                            c.execute("UPDATE payments SET status = 'APPROVED' WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.success(f"Activated for {row['username']} until {new_expiry}!")
                            st.rerun()
                        if btn2.button("❌ Reject", key=f"rej_{row['id']}"):
                            c.execute("UPDATE payments SET status = 'REJECTED' WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.warning("Rejected.")
                            st.rerun()
            st.stop()

    # PAYWALL (Non-Admin & Unpaid Clients)
    if not st.session_state.is_paid and not is_admin:
        st.warning("🔒 Subscription Required")
        st.subheader("Choose a Plan to Access Business Intelligence Bot")
        
        plan_choice = st.radio("Plan:", [f"Monthly Plan - ₹{MONTHLY_PRICE}/month", f"Annual Plan - ₹{YEARLY_PRICE}/year"], horizontal=True)
        selected_amount = MONTHLY_PRICE if "Monthly" in plan_choice else YEARLY_PRICE
        selected_plan = "Monthly" if "Monthly" in plan_choice else "Yearly"

        col_qr, col_info = st.columns([1, 1])

        with col_qr:
            qr_bytes, upi_raw_link = generate_upi_qr(selected_amount, f"{selected_plan} - {st.session_state.username}")
            st.image(qr_bytes, caption=f"Scan via GPay / PhonePe (₹{selected_amount})", width=250)
            st.markdown(f'<a href="{upi_raw_link}" style="display:inline-block;padding:8px 16px;background:#28a745;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">📲 Pay via PhonePe / GPay</a>', unsafe_allow_html=True)

        with col_info:
            st.markdown(f"""
            **Amount:** ₹{selected_amount}  
            **UPI ID:** `{MY_UPI_ID}`
            
            Payment complete hone ke baad transaction ka **12-digit UTR No.** yahan submit karein:
            """)
            utr = st.text_input("12-Digit UTR Number:")
            if st.button("Submit For Verification"):
                if len(utr.strip()) >= 6:
                    c.execute("INSERT INTO payments (username, plan, amount, utr_number, date_submitted, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
                              (st.session_state.username, selected_plan, selected_amount, utr.strip(), datetime.date.today().isoformat()))
                    conn.commit()
                    st.success("✅ Submitted! Admin verification ke baad turant dashboard khul jayega.")
                else:
                    st.error("Enter valid UTR number.")
        st.stop()

    # 3. CORE BOT (Active Clients & Admin)
    st.title("🤖 Business Intelligence Bot")
    st.caption("Upload Excel/CSV sales & receivables data for instant analytics.")

    uploaded_file = st.sidebar.file_uploader("Upload Excel/CSV Report", type=["xlsx", "xls", "csv"])

    if uploaded_file is not None:
        try:
            df = load_tally_file(uploaded_file)
            df.columns = [col.strip() for col in df.columns]
            
            cols = {c.lower(): c for c in df.columns}
            cust_col = cols.get('customer') or cols.get('party name') or cols.get('party') or df.columns[0]
            sales_col = cols.get('sales_amount') or cols.get('sales') or cols.get('amount') or cols.get('invoice value')
            out_col = cols.get('outstanding_amount') or cols.get('outstanding') or cols.get('balance') or cols.get('due amount')
            due_date_col = cols.get('due_date') or cols.get('due on') or cols.get('date')

            if sales_col:
                df[sales_col] = pd.to_numeric(df[sales_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            if out_col:
                df[out_col] = pd.to_numeric(df[out_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)

            today = pd.to_datetime(datetime.date.today())
            if due_date_col:
                df[due_date_col] = pd.to_datetime(df[due_date_col], errors='coerce')
                df['Days_Overdue'] = (today - df[due_date_col]).dt.days.apply(lambda x: x if x > 0 else 0)
            else:
                df['Days_Overdue'] = 0

            total_sales = df[sales_col].sum() if sales_col else 0
            total_outstanding = df[out_col].sum() if out_col else 0
            overdue_df = df[(df['Days_Overdue'] > 0) & (df[out_col] > 0)] if out_col else pd.DataFrame()
            total_overdue = overdue_df[out_col].sum() if not overdue_df.empty else 0
            critical_df = df[(df['Days_Overdue'] > 60) & (df[out_col] > 0)] if out_col else pd.DataFrame()

            top_cust = df.groupby(cust_col)[sales_col].sum().sort_values(ascending=False).index[0] if (sales_col and cust_col) else "N/A"

            # KPI Dashboard
            st.subheader("📌 Executive Dashboard")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Monthly Sales", f"₹{total_sales:,.2f}")
            m2.metric("Outstanding", f"₹{total_outstanding:,.2f}")
            m3.metric("Overdue", f"₹{total_overdue:,.2f}", delta="-Pending" if total_overdue > 0 else None, delta_color="inverse")
            m4.metric("Top Customer", f"{top_cust}")

            st.markdown("---")
            st.subheader("⚠️ Collection & Overdue Breakdown")
            w1, w2 = st.columns(2)
            with w1:
                st.info(f"**Collection Due:** {len(overdue_df[cust_col].unique()) if not overdue_df.empty else 0} customers with overdue invoices.")
            with w2:
                critical_count = len(critical_df[cust_col].unique()) if not critical_df.empty else 0
                st.error(f"**Warning:** {critical_count} customers ki payment **60+ days pending** hai.")

            tab1, tab2 = st.tabs(["Critical 60+ Days", "Full Ledger Data"])
            with tab1:
                if not critical_df.empty:
                    st.dataframe(critical_df[[cust_col, out_col, due_date_col, 'Days_Overdue']], use_container_width=True)
                else:
                    st.success("No accounts currently pending past 60 days.")
            with tab2:
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Error parsing data: {e}")
    else:
        st.info("👈 Upload your Tally or Excel report from the sidebar.")
