import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import time
import os

# ==========================================
# 1. Database Connection (Secure & Clean)
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

@st.cache_data(ttl=60)
def load_data():
    client = conn_sheets()
    if not client: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("Research_Database")
        # Load Masters (Lecturers info)
        df_m = pd.DataFrame(sh.worksheet("masters").get_all_records())
        # Load Research Data
        df_r = pd.DataFrame(sh.worksheet("research").get_all_records())
        
        # Clean columns
        df_m.columns = [str(c).strip() for c in df_m.columns]
        df_r.columns = [str(c).strip() for c in df_r.columns]
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# ==========================================
# 2. Page Setup & Logo
# ==========================================
st.set_page_config(page_title="STIU Research KPI", layout="wide")

# Header with Logo
h_col1, h_col2 = st.columns([1, 6])
with h_col1:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=100)
    else:
        st.markdown("### 🏫 STIU")
with h_col2:
    st.markdown("<h1 style='margin:0;'>St Teresa International University</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:grey;'>Research KPI & Quality Assurance Tracking System</p>", unsafe_allow_html=True)

st.divider()

# Load Data
df_master, df_research = load_data()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

if df_master.empty:
    st.warning("⚠️ Ready to connect! Please check your Google Sheets 'masters' and 'research' tabs.")
    st.stop()

# Prepare Data
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 3. Sidebar Navigation (English)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Menu")
    menu = st.radio("Select Navigation:", ["📊 KPI Dashboard", "✍️ Submit Data", "⚙️ Manage Database"])
    
    st.divider()
    year_list = sorted(df_research['ปี'].unique().tolist()) if not df_research.empty else []
    sel_year = st.selectbox("📅 Filter Year (B.E.):", ["All"] + [str(y) for y in year_list if y > 0])
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

# ==========================================
# 4. Logic: Dashboard & KPI Calculation
# ==========================================
if menu == "📊 KPI Dashboard":
    st.subheader(f"Performance Analysis - Year: {sel_year}")
    
    # Filter Data
    df_r_filtered = df_research.copy()
    if sel_year != "All":
        df_r_filtered = df_r_filtered[df_r_filtered['ปี'] == int(sel_year)]
    
    # Merge Research with Master to get Faculty/Program
    df_merged = df_r_filtered.merge(df_master, left_on="ผู้เขียน", right_on="Name-surname", how="left")

    tab1, tab2, tab3 = st.tabs(["Individual Report", "Program KPI", "Faculty KPI"])

    with tab1:
        st.markdown("#### 👤 Individual Research Output")
        st.dataframe(df_merged[["ผู้เขียน", "ชื่อเรื่อง", "ฐานวารสาร", "คะแนน", "คณะ", "หลักสูตร"]], use_container_width=True)

    with tab2:
        st.markdown("#### 📚 Program KPI Calculation")
        # Logic: Sum Score / Number of Lecturers in Program
        prog_research = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_master = df_master.groupby("หลักสูตร").size().reset_index(name="Total_Lecturers")
        
        df_prog_kpi = prog_master.merge(prog_research, on="หลักสูตร", how="left").fillna(0)
        df_prog_kpi["KPI_Score"] = (df_prog_kpi["คะแนน"] / df_prog_kpi["Total_Lecturers"]) * 5
        
        st.dataframe(df_prog_kpi.style.format({"KPI_Score": "{:.2f}"}), use_container_width=True)

    with tab3:
        st.markdown("#### 🏢 Faculty KPI Calculation")
        # Logic: Sum Score / Number of Lecturers in Faculty
        fac_research = df_merged.groupby("คณะ")["คะแนน"].sum().reset_index()
        fac_master = df_master.groupby("คณะ").size().reset_index(name="Total_Lecturers")
        
        df_fac_kpi = fac_master.merge(fac_research, on="คณะ", how="left").fillna(0)
        df_fac_kpi["KPI_Score"] = (df_fac_kpi["คะแนน"] / df_fac_kpi["Total_Lecturers"]) * 5
        
        st.dataframe(df_fac_kpi.style.format({"KPI_Score": "{:.2f}"}), use_container_width=True)

# ==========================================
# 5. Submit Data
# ==========================================
elif menu == "✍️ Submit Data":
    if not st.session_state.logged_in:
        st.warning("Please login to submit data.")
    else:
        st.subheader("Add New Research Entry")
        with st.form("input_form", clear_on_submit=True):
            title = st.text_input("Research Title")
            c1, c2 = st.columns(2)
            year = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
            db = c2.selectbox("Database", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
            authors = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
            
            score_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
            
            if st.form_submit_button("Submit"):
                if title and authors:
                    client = conn_sheets()
                    ws = client.open("Research_Database").worksheet("research")
                    for a in authors:
                        ws.append_row([title, year, db, score_map[db], a])
                    st.success("Successfully Saved!"); st.cache_data.clear(); time.sleep(1); st.rerun()

# ==========================================
# 6. Manage Database
# ==========================================
elif menu == "⚙️ Manage Database":
    if not st.session_state.logged_in:
        st.warning("Please login to manage data.")
    else:
        st.subheader("Delete Research Records")
        if not df_research.empty:
            # Create list of unique titles to delete
            unique_list = df_research.drop_duplicates(subset=['ชื่อเรื่อง'])
            sel_del = st.selectbox("Select Research Title to Delete:", ["-- Select --"] + unique_list['ชื่อเรื่อง'].tolist())
            
            if sel_del != "-- Select --":
                if st.button("🚨 Confirm Delete Record"):
                    client = conn_sheets()
                    ws = client.open("Research_Database").worksheet("research")
                    records = ws.get_all_records()
                    # Find and delete rows from bottom up
                    for i, row in enumerate(reversed(records)):
                        if row.get('ชื่อเรื่อง') == sel_del:
                            ws.delete_rows(len(records) - i + 1)
                            time.sleep(0.2)
                    st.success("Deleted!"); st.cache_data.clear(); time.sleep(1); st.rerun()
