import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from datetime import datetime

# ==============================================================================
# APP CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Sri Modern Rice Mill - Dynamic Billing & Accounting",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for clean modern mill accounting UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #78350f, #b45309, #d97706);
        color: white;
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(180, 83, 9, 0.15);
    }
    .main-header h1 {
        color: white !important;
        font-size: 26px !important;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .main-header p {
        color: #fef3c7 !important;
        font-size: 13px !important;
        margin-bottom: 0;
    }
    .metric-box {
        background: white;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {
        font-family: monospace;
        font-size: 22px;
        font-weight: 800;
    }
    .metric-label {
        font-size: 11px;
        text-transform: uppercase;
        color: #64748b;
        font-weight: 600;
    }
    .settlement-card-green {
        background: #ecfdf5;
        border: 2px solid #10b981;
        padding: 20px;
        border-radius: 12px;
        margin-top: 15px;
    }
    .settlement-card-red {
        background: #fff1f2;
        border: 2px solid #f43f5e;
        padding: 20px;
        border-radius: 12px;
        margin-top: 15px;
    }
    @media print {
        header, footer, [data-testid="stSidebar"], .stButton {
            display: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATABASE PERSISTENCE (SQLite)
# ==============================================================================
DB_FILE = "ricemill.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS ricemill_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no TEXT UNIQUE,
        bill_date TEXT,
        party_name TEXT,
        lorry_no TEXT,
        batch_no TEXT,
        lot_no TEXT,
        billing_mode TEXT,
        data_json TEXT,
        total_paddy_weight REAL DEFAULT 0,
        total_paddy_bags REAL DEFAULT 0,
        total_charges REAL DEFAULT 0,
        total_recoveries REAL DEFAULT 0,
        net_payable REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# HELPER FUNCTIONS & CURRENCY FORMATTERS
# ==============================================================================
def format_inr(val):
    if val is None or pd.isna(val):
        return "₹0.00"
    is_neg = val < 0
    abs_v = abs(val)
    parts = f"{abs_v:,.2f}".split(".")
    integer_part = parts[0].replace(",", "")
    decimals = parts[1]
    
    # Indian numbering format
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        other = integer_part[:-3]
        res = ""
        while len(other) > 2:
            res = "," + other[-2:] + res
            other = other[:-2]
        formatted = other + res + "," + last3
    else:
        formatted = integer_part
        
    return f"{'-' if is_neg else ''}₹{formatted}.{decimals}"

def number_to_words(num):
    if num is None or pd.isna(num):
        return "Rupees Zero Only"
    is_neg = num < 0
    abs_num = abs(num)
    rupees = int(abs_num)
    paise = int(round((abs_num - rupees) * 100))
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def two_digits(n):
        if n == 0: return ""
        if n < 20: return ones[n]
        rem = n % 10
        t = tens[n // 10]
        return f"{t} {ones[rem]}".strip()
        
    def convert_below_thousand(n):
        res = ""
        h = n // 100
        rem = n % 100
        if h > 0: res += f"{ones[h]} Hundred "
        if rem > 0: res += two_digits(rem)
        return res.strip()

    parts = []
    crores = rupees // 10000000
    rupees %= 10000000
    if crores > 0: parts.append(f"{convert_below_thousand(crores)} Crore")
    
    lakhs = rupees // 100000
    rupees %= 100000
    if lakhs > 0: parts.append(f"{two_digits(lakhs)} Lakh")
    
    thousands = rupees // 1000
    rupees %= 1000
    if thousands > 0: parts.append(f"{two_digits(thousands)} Thousand")
    
    if rupees > 0: parts.append(convert_below_thousand(rupees))
    
    rupees_str = " ".join(parts).strip() or "Zero"
    res = f"Rupees {rupees_str}"
    if paise > 0: res += f" and {two_digits(paise)} Paise"
    res += " Only"
    return ("Minus " + res) if is_neg else res

# ==============================================================================
# SAMPLE DATA PRESETS FROM YOUR SPREADSHEET
# ==============================================================================
DEFAULT_SINGLE_LABOR = [
    {"Particulars": "Paddy 70KG", "Bags": 393.3714, "Rate": 100.0, "Amount": 39337.14},
    {"Particulars": "Unloading", "Bags": 0.0, "Rate": 4.0, "Amount": 0.0},
    {"Particulars": "Gage Cutting & Dumping", "Bags": 380.0, "Rate": 6.0, "Amount": 2280.0},
    {"Particulars": "Rice Pack & Load 26kg", "Bags": 475.0, "Rate": 4.0, "Amount": 1900.0},
    {"Particulars": "Bkn Pack & Load 26kg", "Bags": 0.0, "Rate": 4.0, "Amount": 0.0},
    {"Particulars": "Bkn Pack & Load 50kg", "Bags": 54.0, "Rate": 8.0, "Amount": 432.0},
    {"Particulars": "Bran pack&load 50 kg", "Bags": 35.3, "Rate": 8.0, "Amount": 282.4},
    {"Particulars": "blower pack & load50kg", "Bags": 20.4, "Rate": 8.0, "Amount": 163.2},
    {"Particulars": "Outton", "Bags": 12.0, "Rate": 8.0, "Amount": 96.0},
    {"Particulars": "Rej Bkn pack & load 50KG", "Bags": 2.0, "Rate": 8.0, "Amount": 16.0},
    {"Particulars": "Empty Bags Rice", "Bags": 0.0, "Rate": 11.5, "Amount": 0.0},
    {"Particulars": "Empty Bags Broken", "Bags": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Shifting & Cutting Paddy", "Bags": 30.0, "Rate": 6.0, "Amount": 180.0},
    {"Particulars": "Empty gunny 50kg", "Bags": 0.0, "Rate": 9.0, "Amount": 0.0},
    {"Particulars": "Stiching Thread", "Bags": 1.0, "Rate": 200.0, "Amount": 200.0},
    {"Particulars": "Outton", "Bags": 1.0, "Rate": 500.0, "Amount": 500.0}
]

DEFAULT_SINGLE_BYPRODUCTS = [
    {"Particulars": "rice 26kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Broken 26kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Broken 50kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Bran 50kg", "Bags": 35.3, "Weight (KG)": 1775.0, "Rate": 28.96, "Amount": 51404.0},
    {"Particulars": "Blower 50kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Rejection Rice 26 KG", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Rejection Broken 26kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Gunny", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 0.0, "Amount": 0.0}
]

DEFAULT_MULTI_LOADS = [
    {"Load #": 1, "Lorry No": "TN29BF8709", "Bags": 350, "Paddy Weight (KG)": 27500.0},
    {"Load #": 2, "Lorry No": "TN28AE4120", "Bags": 450, "Paddy Weight (KG)": 34596.0},
    {"Load #": 3, "Lorry No": "KA01MF9832", "Bags": 650, "Paddy Weight (KG)": 25745.0},
    {"Load #": 4, "Lorry No": "TN30CK1124", "Bags": 152, "Paddy Weight (KG)": 47825.0}
]

DEFAULT_PADDY_LABOR = [
    {"Particulars": "Paddy", "Lot No": "500/256bg", "Bags": 500, "Rate": 6.0, "Amount": 3000.0},
    {"Particulars": "Unloading", "Lot No": "", "Bags": 100, "Rate": 5.0, "Amount": 500.0},
    {"Particulars": "shifting&cutting", "Lot No": "", "Bags": 20, "Rate": 5.5, "Amount": 110.0}
]

DEFAULT_RICE_LABOR = [
    {"Particulars": "Rice 26kgs", "Lot No": "", "Bags": 200, "Rate": 3.0, "Amount": 600.0},
    {"Particulars": "Bkn 50kgs", "Lot No": "", "Bags": 50, "Rate": 6.0, "Amount": 300.0},
    {"Particulars": "Bkn 26kgs", "Lot No": "", "Bags": 10, "Rate": 3.0, "Amount": 30.0},
    {"Particulars": "Bran 50kgs", "Lot No": "", "Bags": 10, "Rate": 6.0, "Amount": 60.0},
    {"Particulars": "BB 50kgs", "Lot No": "", "Bags": 11, "Rate": 6.0, "Amount": 66.0},
    {"Particulars": "2nd Bkn 50kgs", "Lot No": "", "Bags": 12, "Rate": 6.0, "Amount": 72.0},
    {"Particulars": "Rej Rice 50kgs", "Lot No": "", "Bags": 13, "Rate": 6.0, "Amount": 78.0},
    {"Particulars": "Rej bkn 50kgs", "Lot No": "", "Bags": 14, "Rate": 6.0, "Amount": 84.0},
    {"Particulars": "Rice Gunny", "Lot No": "", "Bags": 15, "Rate": 0.0, "Amount": 0.0},
    {"Particulars": "Gunny", "Lot No": "", "Bags": 15, "Rate": 15.0, "Amount": 225.0},
    {"Particulars": "Outan", "Lot No": "", "Bags": 1, "Rate": 500.0, "Amount": 500.0},
    {"Particulars": "Thread", "Lot No": "", "Bags": 2, "Rate": 200.0, "Amount": 400.0}
]

# Initialize Session State
if "single_labor_df" not in st.session_state:
    st.session_state.single_labor_df = pd.DataFrame(DEFAULT_SINGLE_LABOR)

if "single_byproducts_df" not in st.session_state:
    st.session_state.single_byproducts_df = pd.DataFrame(DEFAULT_SINGLE_BYPRODUCTS)

if "multi_loads_df" not in st.session_state:
    st.session_state.multi_loads_df = pd.DataFrame(DEFAULT_MULTI_LOADS)

if "multi_paddy_labor_df" not in st.session_state:
    st.session_state.multi_paddy_labor_df = pd.DataFrame(DEFAULT_PADDY_LABOR)

if "multi_rice_labor_df" not in st.session_state:
    st.session_state.multi_rice_labor_df = pd.DataFrame(DEFAULT_RICE_LABOR)

# ==============================================================================
# SIDEBAR: MILL SETTINGS & CONTROLS
# ==============================================================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&auto=format&fit=crop&q=60", caption="Modern Rice Mill Software")
    st.title("🌾 Mill Settings")
    mill_name = st.text_input("Mill Name", value="SRI MODERN RICE MILL")
    mill_tagline = st.text_input("Tagline", value="Paddy Processing & Rice Milling Ledger")
    mill_contact = st.text_input("Phone / Contact", value="+91 98765 43210")
    mill_gst = st.text_input("GSTIN", value="33AABCS1429B1Z8")
    
    st.divider()
    st.subheader("⚡ Quick Actions")
    if st.button("🔄 Reload Sample Data (TN29BF8709)", use_container_width=True):
        st.session_state.single_labor_df = pd.DataFrame(DEFAULT_SINGLE_LABOR)
        st.session_state.single_byproducts_df = pd.DataFrame(DEFAULT_SINGLE_BYPRODUCTS)
        st.session_state.multi_loads_df = pd.DataFrame(DEFAULT_MULTI_LOADS)
        st.session_state.multi_paddy_labor_df = pd.DataFrame(DEFAULT_PADDY_LABOR)
        st.session_state.multi_rice_labor_df = pd.DataFrame(DEFAULT_RICE_LABOR)
        st.success("Sample data restored!")
        st.rerun()

    if st.button("➕ Clear / Blank Slate", use_container_width=True):
        st.session_state.single_labor_df = pd.DataFrame([{"Particulars": "Unloading", "Bags": 0.0, "Rate": 4.0, "Amount": 0.0}])
        st.session_state.single_byproducts_df = pd.DataFrame([{"Particulars": "Bran 50kg", "Bags": 0.0, "Weight (KG)": 0.0, "Rate": 28.96, "Amount": 0.0}])
        st.session_state.multi_loads_df = pd.DataFrame([{"Load #": 1, "Lorry No": "", "Bags": 0, "Paddy Weight (KG)": 0.0}])
        st.info("Blank slate ready for dynamic entry!")
        st.rerun()

# ==============================================================================
# HEADER BANNER
# ==============================================================================
st.markdown(f"""
<div class="main-header">
    <h1>{mill_name}</h1>
    <p>{mill_tagline} • Ph: {mill_contact} • GSTIN: {mill_gst}</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📑 Single Batch (Vehicle Bill)",
    "🚛 Multi-Load (Lot Settlement)",
    "📊 Dual Side-by-Side View",
    "📁 Saved Bills Ledger"
])

# ==============================================================================
# TAB 1: SINGLE BATCH VEHICLE BILL
# ==============================================================================
with tab1:
    st.subheader("Single Batch Vehicle Billing & Labor Settlement")
    st.caption("Dynamic calculation for single lorry arrivals (Left Side of your sheet).")

    # Metadata Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        s_party = st.text_input("Party Name", value="M/S Sri Venkateswara Traders", key="s_party")
    with col2:
        s_lorry = st.text_input("Lorry / Vehicle No", value="TN29BF8709", key="s_lorry")
    with col3:
        s_date = st.date_input("Date", value=datetime.today(), key="s_date")
    with col4:
        s_batch = st.text_input("Batch No", value="1", key="s_batch")
    with col5:
        s_bill_no = st.text_input("Bill No", value="RM-2026-B001", key="s_bill_no")

    # Inward Paddy Weighment
    st.markdown("#### ⚖️ Inward Paddy Weighment & 70KG Conversion")
    p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
    with p_col1:
        paddy_weight = st.number_input("Paddy Total Weight (KG)", value=27536.0, step=10.0, format="%.2f", key="s_paddy_wt")
    with p_col2:
        paddy_bags_inward = st.number_input("Reported Inward Bags", value=380, step=1, key="s_inward_bags")
    with p_col3:
        bag_size = st.number_input("Bag Size Standard (KG)", value=70.0, step=1.0, key="s_bag_size")
    with p_col4:
        paddy_rate = st.number_input("Paddy Milling Rate (₹/70kg)", value=100.0, step=1.0, key="s_milling_rate")
    
    # Live conversion
    paddy_70kg_bags = paddy_weight / bag_size if bag_size > 0 else 0.0
    paddy_milling_amount = paddy_70kg_bags * paddy_rate
    
    with p_col5:
        st.metric(
            label=f"Converted {int(bag_size)}KG Bags",
            value=f"{paddy_70kg_bags:.4f} Bags",
            delta=f"₹{paddy_milling_amount:,.2f}"
        )

    st.divider()

    # Tables in two columns
    tbl_col1, tbl_col2 = st.columns(2)

    with tbl_col1:
        st.markdown("##### 1. Milling, Labor & Handling Expenses")
        st.caption("Edit bags or rates dynamically. Rows auto-multiply:")
        
        # Ensure Paddy 70KG row stays in sync
        current_labor = st.session_state.single_labor_df.copy()
        for idx, row in current_labor.iterrows():
            if "Paddy 70" in str(row["Particulars"]):
                current_labor.at[idx, "Bags"] = paddy_70kg_bags
                current_labor.at[idx, "Rate"] = paddy_rate
                current_labor.at[idx, "Amount"] = paddy_milling_amount
            else:
                # Recalculate amount if bags & rate are provided
                if row["Rate"] > 0:
                    current_labor.at[idx, "Amount"] = round(row["Bags"] * row["Rate"], 2)

        edited_labor = st.data_editor(
            current_labor,
            num_rows="dynamic",
            use_container_width=True,
            key="labor_editor"
        )
        st.session_state.single_labor_df = edited_labor

        # Compute dynamic sum
        total_labor_charges = edited_labor["Amount"].sum()
        st.markdown(f"**Total Labor & Milling Charges:** `{format_inr(total_labor_charges)}`")

    with tbl_col2:
        st.markdown("##### 2. By-Products Realization (Recoveries / Credit)")
        st.caption("Bran, broken rice, blower & gunny recoveries:")
        
        current_byproducts = st.session_state.single_byproducts_df.copy()
        for idx, row in current_byproducts.iterrows():
            if row.get("Weight (KG)", 0) > 0 and row.get("Rate", 0) > 0:
                current_byproducts.at[idx, "Amount"] = round(row["Weight (KG)"] * row["Rate"], 2)
            elif row.get("Bags", 0) > 0 and row.get("Rate", 0) > 0:
                current_byproducts.at[idx, "Amount"] = round(row["Bags"] * row["Rate"], 2)

        edited_byproducts = st.data_editor(
            current_byproducts,
            num_rows="dynamic",
            use_container_width=True,
            key="byproduct_editor"
        )
        st.session_state.single_byproducts_df = edited_byproducts

        total_recoveries = edited_byproducts["Amount"].sum()
        st.markdown(f"**Total Realization (Recoveries):** `{format_inr(total_recoveries)}`")

    # Settlement Card
    net_payable = total_recoveries - total_labor_charges
    is_mill_pays = net_payable >= 0

    st.markdown("---")
    st.subheader("💰 Net Settlement Breakdown")
    
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Total Labor & Milling (Expenses)", format_inr(total_labor_charges))
    with m_col2:
        st.metric("Total Realization (Recoveries)", format_inr(total_recoveries))
    with m_col3:
        st.metric("Net Balance", format_inr(abs(net_payable)), delta="Refund to Party" if is_mill_pays else "Due from Party")

    card_class = "settlement-card-green" if is_mill_pays else "settlement-card-red"
    direction_text = "MILL PAYS TO PARTY (Net Refund / Credit)" if is_mill_pays else "PARTY PAYS TO MILL (Net Debit / Due)"
    
    st.markdown(f"""
    <div class="{card_class}">
        <h3 style="margin-top:0;">{direction_text}: {format_inr(abs(net_payable))}</h3>
        <p><strong>Amount in Words:</strong> {number_to_words(net_payable)}</p>
    </div>
    """, unsafe_allow_html=True)

    # Save to SQLite Ledger
    st.write("")
    if st.button("💾 Save Bill to Ledger", key="save_single_btn"):
        bill_data = {
            "paddy_weight": paddy_weight,
            "paddy_bags": paddy_bags_inward,
            "labor_items": edited_labor.to_dict(orient="records"),
            "byproducts": edited_byproducts.to_dict(orient="records")
        }
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO ricemill_bills (
                bill_no, bill_date, party_name, lorry_no, batch_no, lot_no,
                billing_mode, data_json, total_paddy_weight, total_paddy_bags,
                total_charges, total_recoveries, net_payable, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s_bill_no, str(s_date), s_party, s_lorry, s_batch, "",
            "single_batch", json.dumps(bill_data), paddy_weight, paddy_bags_inward,
            total_labor_charges, total_recoveries, net_payable,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        st.success(f"Bill #{s_bill_no} successfully saved into database!")

# ==============================================================================
# TAB 2: MULTI-LOAD CONSOLIDATED SETTLEMENT
# ==============================================================================
with tab2:
    st.subheader("Multi-Load Consolidated Lot Settlement")
    st.caption("Consolidate multiple lorry loads, separate Paddy & Rice labor lines, and apply Bran credit (Right Side of your sheet).")

    m_row1, m_row2, m_row3, m_row4 = st.columns(4)
    with m_row1:
        ml_party = st.text_input("Party Name", value="M/S Sri Venkateswara Traders", key="ml_party")
    with m_row2:
        ml_batch = st.text_input("Batch No", value="1", key="ml_batch")
    with m_row3:
        ml_lot = st.text_input("Lot No / Marks", value="500/256bg", key="ml_lot")
    with m_row4:
        ml_bill_no = st.text_input("Lot Bill No", value="RM-2026-ML001", key="ml_bill_no")

    st.markdown("#### 🚛 Inward Paddy Loads (Multiple Lorries)")
    st.caption("Add or modify any number of lorry loads dynamically:")

    edited_loads = st.data_editor(
        st.session_state.multi_loads_df,
        num_rows="dynamic",
        use_container_width=True,
        key="loads_editor"
    )
    st.session_state.multi_loads_df = edited_loads

    # Totals of loads
    total_ml_weight = edited_loads["Paddy Weight (KG)"].sum()
    total_ml_bags = edited_loads["Bags"].sum()
    
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        ml_rate_70 = st.number_input("Paddy 70KG Rate (₹)", value=110.0, step=1.0, key="ml_rate_70")
    with col_r2:
        ml_70_bags = total_ml_weight / 70.0
        st.metric("Total 70KG Equivalent Bags", f"{ml_70_bags:.4f} Bags", delta=f"{total_ml_weight:,.2f} KG")
    with col_r3:
        ml_paddy_milling_amt = ml_70_bags * ml_rate_70
        st.metric("Paddy Milling Charge (@ ₹110)", format_inr(ml_paddy_milling_amt))

    st.divider()

    # Two labor tables
    lab_col1, lab_col2 = st.columns(2)
    with lab_col1:
        st.markdown("##### Paddy Labor Charges")
        current_pl = st.session_state.multi_paddy_labor_df.copy()
        for idx, row in current_pl.iterrows():
            if row["Rate"] > 0:
                current_pl.at[idx, "Amount"] = round(row["Bags"] * row["Rate"], 2)
        edited_pl = st.data_editor(current_pl, num_rows="dynamic", use_container_width=True, key="pl_editor")
        st.session_state.multi_paddy_labor_df = edited_pl
        total_paddy_labor = edited_pl["Amount"].sum()
        st.markdown(f"**Paddy Labor Subtotal:** `{format_inr(total_paddy_labor)}`")

    with lab_col2:
        st.markdown("##### Rice, By-Product & Gunny Labor Charges")
        current_rl = st.session_state.multi_rice_labor_df.copy()
        for idx, row in current_rl.iterrows():
            if row["Rate"] > 0:
                current_rl.at[idx, "Amount"] = round(row["Bags"] * row["Rate"], 2)
        edited_rl = st.data_editor(current_rl, num_rows="dynamic", use_container_width=True, key="rl_editor")
        st.session_state.multi_rice_labor_df = edited_rl
        
        computed_rl_sum = edited_rl["Amount"].sum()
        use_override = st.checkbox("Apply Sheet Override (₹2,049)", value=True, help="Your sheet recorded ₹2,049 instead of the line sum of ₹2,415")
        total_rice_labor = 2049.0 if use_override else computed_rl_sum
        st.markdown(f"**Rice Labor Active Total:** `{format_inr(total_rice_labor)}` *(Line sum: {format_inr(computed_rl_sum)})*")

    st.divider()

    # Bran Realization & Settlement
    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        st.markdown("##### 🌾 Bran Realization (Credit Deduction)")
        bran_weight = st.number_input("Bran Total Weight (KG)", value=5500.0, step=50.0, key="ml_bran_wt")
        bran_rate = st.number_input("Bran Selling Rate (₹/KG)", value=25.80, step=0.10, key="ml_bran_rate")
        total_bran_credit = bran_weight * bran_rate
        st.metric("Total Bran Realization Credit", format_inr(total_bran_credit))

    with b_col2:
        st.markdown("##### 💰 Consolidated Lot Settlement")
        gross_expenses = ml_paddy_milling_amt + total_paddy_labor + total_rice_labor
        ml_net_payable = total_bran_credit - gross_expenses
        ml_is_mill_pays = ml_net_payable >= 0

        st.write(f"• **Paddy Milling (70kg):** {format_inr(ml_paddy_milling_amt)}")
        st.write(f"• **Paddy Labor:** {format_inr(total_paddy_labor)} | • **Rice Labor:** {format_inr(total_rice_labor)}")
        st.write(f"• **Gross Mill Charges:** `{format_inr(gross_expenses)}`")
        st.write(f"• **Bran Credit Deducted:** `{format_inr(total_bran_credit)}`")
        
        ml_card_class = "settlement-card-green" if ml_is_mill_pays else "settlement-card-red"
        ml_direction_text = "MILL PAYS PARTY" if ml_is_mill_pays else "PARTY TO PAY MILL (Due to Mill)"
        
        st.markdown(f"""
        <div class="{ml_card_class}">
            <h3 style="margin-top:0;">{ml_direction_text}: {format_inr(abs(ml_net_payable))}</h3>
            <p><strong>In Words:</strong> {number_to_words(ml_net_payable)}</p>
        </div>
        """, unsafe_allow_html=True)

    # Save Multi Lot Bill
    if st.button("💾 Save Lot Settlement to Ledger", key="save_multi_btn"):
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO ricemill_bills (
                bill_no, bill_date, party_name, lorry_no, batch_no, lot_no,
                billing_mode, data_json, total_paddy_weight, total_paddy_bags,
                total_charges, total_recoveries, net_payable, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ml_bill_no, datetime.today().strftime("%Y-%m-%d"), ml_party, "Multiple Lorries", ml_batch, ml_lot,
            "multi_lot", json.dumps({"loads": edited_loads.to_dict(orient="records")}), total_ml_weight, total_ml_bags,
            gross_expenses, total_bran_credit, ml_net_payable,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        st.success(f"Lot Bill #{ml_bill_no} successfully saved into database!")

# ==============================================================================
# TAB 3: DUAL SIDE-BY-SIDE VIEW
# ==============================================================================
with tab3:
    st.subheader("Dual Side-by-Side Reconciliation Statement")
    st.caption("Reconcile both sides of your spreadsheet in one unified view:")
    
    dual_col1, dual_col2 = st.columns(2)
    with dual_col1:
        st.markdown("### 📑 Sheet A: Single Batch Vehicle Bill")
        st.info(f"**Vehicle:** {s_lorry} | **Batch:** #{s_batch} | **Inward:** {paddy_weight:,.2f} KG")
        st.write(f"• **Converted 70kg Bags:** {paddy_70kg_bags:.4f} @ ₹{paddy_rate}")
        st.write(f"• **Paddy Milling Charge:** {format_inr(paddy_milling_amount)}")
        st.write(f"• **Total Labor & Handling:** {format_inr(total_labor_charges)}")
        st.write(f"• **Total Realization (Bran/By-products):** {format_inr(total_recoveries)}")
        st.success(f"**Net Payable:** {format_inr(abs(net_payable))} (Mill Pays Party)")

    with dual_col2:
        st.markdown("### 🚛 Sheet B: Multi-Load Lot Statement")
        st.info(f"**Party:** {ml_party} | **Lot:** {ml_lot} | **Consolidated:** {total_ml_weight:,.2f} KG")
        st.write(f"• **Converted 70kg Bags:** {ml_70_bags:.4f} @ ₹{ml_rate_70}")
        st.write(f"• **Paddy Milling Charge:** {format_inr(ml_paddy_milling_amt)}")
        st.write(f"• **Paddy & Rice Labor Total:** {format_inr(total_paddy_labor + total_rice_labor)}")
        st.write(f"• **Bran Credit Deducted:** {format_inr(total_bran_credit)}")
        st.error(f"**Net Settlement:** {format_inr(abs(ml_net_payable))} (Party Owes Mill)")

# ==============================================================================
# TAB 4: SAVED BILLS DATABASE
# ==============================================================================
with tab4:
    st.subheader("Saved Bills & Settlement History")
    conn = get_db()
    bills_df = pd.read_sql_query("SELECT id, bill_no, bill_date, party_name, lorry_no, batch_no, billing_mode, total_paddy_weight, total_charges, total_recoveries, net_payable, created_at FROM ricemill_bills ORDER BY id DESC", conn)
    conn.close()

    if not bills_df.empty:
        # Format currency columns for display
        display_df = bills_df.copy()
        display_df["total_charges"] = display_df["total_charges"].apply(format_inr)
        display_df["total_recoveries"] = display_df["total_recoveries"].apply(format_inr)
        display_df["net_payable"] = display_df["net_payable"].apply(format_inr)
        
        st.dataframe(display_df, use_container_width=True)

        # Download CSV
        csv_data = bills_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Complete Ledger CSV",
            data=csv_data,
            file_name="ricemill_ledger.csv",
            mime="text/csv"
        )
    else:
        st.info("No bills saved in the ledger yet. Click 'Save Bill' in either tab to store records.")

# Footer
st.markdown("---")
st.caption(f"{mill_name} • Dynamic Rice Mill Billing & Accounting Software")
