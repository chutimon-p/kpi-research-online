import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time
import os

# ==========================================
# 1. Database Connection
# ==========================================
@st.cache_resource
def conn_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(list(new_row_dict.values()))
        except Exception as e:
            st.error(f"❌ Save Failed: {e}")

# ==========================================
# 2. Page Configuration & Professional Header
# ==========================================
st.set_page_config(page_title="Research Management System - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1E3A8A; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER WITH LOGO ---
h_col1, h_col2 = st.columns([1, 5])
with h_col1:
    # ตรวจสอบไฟล์ logo.jpg แบบปลอดภัย
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=120)
    else:
        st.markdown("### 🏫 STIU")

with h_col2:
    st.markdown("""
        <div style="padding-top: 5px;">
            <h1 style="margin-bottom: 0px;">St Teresa International University</h1>
            <p style="font-size: 1.1rem; color: #64748b; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Load Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

if df_master.empty:
    st.warning("⚠️ Accessing Google Sheets... Please ensure 'Research_Database' is shared with Service Account.")
    st.stop()

# Data Cleaning
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
else:
    df_research = pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar (English Menu)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
    menu_options = ["📊 Performance Dashboard", "✍️ Submit Publication", "⚙️ Manage Database"]
    menu = st.radio("Go to:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        st.markdown("#### Admin Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Password")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.divider()
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_filter = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Content Pages
# ==========================================

# --- PAGE 1: DASHBOARD ---
if menu == "📊 Performance Dashboard":
    st.subheader(f"📈 Dashboard Overview: {year_filter}")
    
    df_filtered = df_research.copy()
    if year_filter != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_filter)]
    
    if df_filtered.empty:
        st.info("No data available for the selected year.")
    else:
        m1, m2, m3 = st.columns(3)
        unique_titles = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
        m1.metric("Total Publications", f"{len(unique_titles)} Titles")
        m2.metric("Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
        m3.metric("Total Scores", f"{unique_titles['คะแนน'].sum():.2f}")

        # กราฟ
        fig = px.bar(unique_titles.groupby("ฐานวารสาร").size().reset_index(name='Count'), 
                     x='ฐานวารสาร', y='Count', color='ฐานวารสาร', text_auto=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# --- PAGE 2: SUBMIT ---
elif menu == "✍️ Submit Publication":
    if not st.session_state.logged_in:
        st.warning("🔒 Admin access required to submit data.")
    else:
        st.subheader("✍️ Register New Publication")
        with st.form("form_submit", clear_on_submit=True):
            t_in = st.text_input("Publication Title")
            c1, c2 = st.columns(2)
            y_in = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
            db_in = c2.selectbox("Journal Database", list(SCORE_MAP.keys()))
            authors = st.multiselect("Author Names", df_master["Name-surname"].unique().tolist())
            
            if st.form_submit_button("Save Record"):
                if t_in and authors:
                    for a in authors:
                        save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": db_in, "คะแนน": SCORE_MAP[db_in], "ผู้เขียน": a})
                    st.success("Record Saved!"); st.cache_data.clear(); time.sleep(1); st.rerun()

# --- PAGE 3: MANAGE ---
elif menu == "⚙️ Manage Database":
    if not st.session_state.logged_in:
        st.warning("🔒 Admin access required to manage database.")
    else:
        st.subheader("⚙️ Data Management")
        if not df_research.empty:
            df_m = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
            opts = ["-- Select Entry --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_m.iterrows()]
            sel = st.selectbox("Select entry to delete:", opts)
            
            if sel != "-- Select Entry --":
                target = sel.split(" | ")[1].strip()
                if st.button("🚨 Confirm Delete"):
                    with st.spinner("Deleting..."):
                        client = conn_sheets()
                        ws = client.open("Research_Database").worksheet("research")
                        recs = ws.get_all_records()
                        rows = [i + 2 for i, r in enumerate(recs) if str(r.get('ชื่อเรื่อง')).strip() == target]
                        for r in sorted(rows, reverse=True):
                            ws.delete_rows(r)
                            time.sleep(0.3)
                        st.success("Deleted!"); st.cache_data.clear(); time.sleep(1); st.rerun()
