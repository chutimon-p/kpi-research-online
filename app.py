import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. การเชื่อมต่อฐานข้อมูล (Database Connection)
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
            # ล้างช่องว่างหัวตาราง (ป้องกัน Error .str accessor)
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
# 2. การตั้งค่าหน้าจอ (Page Configuration)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #1E3A8A;
    }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# โหลดข้อมูลเบื้องต้น
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty:
    st.warning("⚠️ Accessing Google Sheets... Please check 'masters' sheet.")
    st.stop()

# จัดการข้อมูลงานวิจัยเบื้องต้น
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
else:
    df_research = pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. เมนูด้านซ้าย (Sidebar)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("Go to Page:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Wrong Password")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้ารายงาน (Dashboard & Reports)
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 Performance Overview: {year_option}")
    
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # เชื่อมข้อมูลอาจารย์กับคณะ
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", right_on="Name-surname", how="left"
    )
    
    # ตรวจสอบว่ามีข้อมูลโชว์หรือไม่
    if df_filtered.empty:
        st.info("No
