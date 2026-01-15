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
def load_full_data():
    client = conn_sheets()
    if not client: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("Research_Database")
        
        # Load and Clean Masters
        df_m = pd.DataFrame(sh.worksheet("masters").get_all_records())
        df_m.columns = [str(c).strip() for c in df_m.columns]
        if "Name-surname" in df_m.columns:
            df_m["Name-surname"] = df_m["Name-surname"].astype(str).str.strip()
            
        # Load and Clean Research
        df_r = pd.DataFrame(sh.worksheet("research").get_all_records())
        df_r.columns = [str(c).strip() for c in df_r.columns]
        if "ผู้เขียน" in df_r.columns:
            df_r["ผู้เขียน"] = df_r["ผู้เขียน"].astype(str).str.strip()
            
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# ==========================================
# 2. Page Setup & Header
# ==========================================
st.set_page_config(page_title="STIU Research KPI System", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; }
    h1, h2, h3 { color: #1E3A8A; font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

h_col_l, h_col_r = st.columns([1, 6])
with h_col_l:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=100)
    else:
        st.markdown("### 🏫 STIU")
with h_col_r:
    st.markdown("<h1 style='margin:0;'>St Teresa International University</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:grey;'>Research KPI Management System (IQA Standard)</p>", unsafe_allow_html=True)

st.divider()

# Load Data
df_master, df_research = load_full_data()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

if df_master.empty:
    st.warning("⚠️ Ready to connect. Please check your Google Sheets configuration.")
    st.stop()

if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 3. Sidebar Navigation
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
    menu = st.radio("Go to:", ["📊 Performance Dashboard", "✍️ Submit Publication", "⚙️ Manage Database"])
    
    st.divider()
    years = sorted(df_research['ปี'].unique().tolist()) if not df_research.empty else []
    sel_year = st.selectbox("📅 Filter Year (B.E.):", ["All Years"] + [str(y) for y in years if y > 0])
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
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

# ==========================================
# 4. Content Pages
# ==========================================
if menu == "📊 Performance Dashboard":
    st.subheader(f"Performance Analysis: {sel_year}")
    
    df_r_active = df_research.copy()
    if sel_year != "All Years":
        df_r_active = df_r_active[df_r_active['ปี'] == int(sel_year)]
    
    if not df_r_active.empty:
        df_merged = df_r_active.merge(df_master, left_on="ผู้เขียน", right_on="Name-surname", how="left")
    else:
        df_merged = pd.DataFrame(columns=list(df_research.columns) + list(df_master.columns))

    t1, t2, t3 = st.tabs(["Individual Report", "Program KPI", "Faculty KPI"])

    with t1:
        st.markdown("#### 👤 Individual Research Records")
        st.dataframe(df_merged[["ผู้เขียน", "ชื่อเรื่อง", "ฐานวารสาร", "คะแนน", "คณะ", "หลักสูตร"]], use_container_width=True)

    with t2:
        st.markdown("#### 📚 Program-Level KPI (Score / Lecturers * 5)")
        prog_score = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_count = df_master.groupby("หลักสูตร").size().reset_index(name="Total_Lecturers")
        kpi_p = prog_count.merge(prog_score, on="หลักสูตร", how="left").fillna(0)
        kpi_p["KPI_Score"] = (kpi_p["คะแนน"] / kpi_p["Total_Lecturers"]) * 5
        st.dataframe(kpi_p.style.format({"KPI_Score": "{:.2f}", "คะแนน": "{:.2f}"}), use_container_width=True)

    with t3:
        st.markdown("#### 🏢 Faculty-Level KPI")
        fac_score = df_merged.groupby("คณะ")["คะแนน"].sum().reset_index()
        fac_count = df_master.groupby("คณะ").size().reset_index(name="Total_Lecturers")
        kpi_f = fac_count.merge(fac_score, on="คณะ", how="left").fillna(0)
        kpi_f["KPI_Score"] = (kpi_f["คะแนน"] / kpi_f["Total_Lecturers"]) * 5
        st.dataframe(kpi_f.style.format({"KPI_Score": "{:.2f}", "คะแนน": "{:.2f}"}), use_container_width=True)

elif menu == "✍️ Submit Publication":
    if not st.session_state.logged_in:
        st.warning("🔒 Please login as Admin to register new research.")
    else:
        st.subheader("Register New Publication")
        with st.form("input_form", clear_on_submit=True):
            title = st.text_input("Research Title")
            c1, c2 = st.columns(2)
            year = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
            db = c2.selectbox("Database", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
            authors = st.multiselect("Select Authors", df_master["Name-surname"].unique().tolist())
            s_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
            if st.form_submit_button("Submit"):
                if title and authors:
                    client = conn_sheets()
                    ws = client.open("Research_Database").worksheet("research")
                    for a in authors:
                        ws.append_row([title, year, db, s_map[db], a])
                    st.success("Successfully Saved!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "⚙️ Manage Database":
    if not st.session_state.logged_in:
        st.warning("🔒 Please login as Admin to manage database.")
    else:
        st.subheader("Manage Records")
        if not df_research.empty:
            unique_titles = df_research.drop_duplicates(subset=['ชื่อเรื่อง'])
            sel = st.selectbox("Select Title to Remove:", ["-- Select --"] + unique_titles['ชื่อเรื่อง'].tolist())
            if sel != "-- Select --":
                if st.button("🚨 Delete Record"):
                    client = conn_sheets()
                    ws = client.open("Research_Database").worksheet("research")
                    recs = ws.get_all_records()
                    for i, r in enumerate(reversed(recs)):
                        if r.get('ชื่อเรื่อง') == sel:
                            ws.delete_rows(len(recs) - i + 1)
                            time.sleep(0.2)
                    st.success("Deleted!"); st.cache_data.clear(); time.sleep(1); st.rerun()
