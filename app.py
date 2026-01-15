import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. Database Connection (Original Function)
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

def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database") 
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            # ล้างช่องว่างที่หัวตารางและจัดการตัวอักษรพิเศษ
            df.columns = [str(c).strip().replace('\xa0', ' ') for c in df.columns]
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ==========================================
# 2. Page Setup & Logic
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# โหลดข้อมูล
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังเชื่อมต่อข้อมูลจาก Google Sheets...")
    st.stop()

# ทำความสะอาดข้อมูลเหมือนโค้ดดั้งเดิม
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
# จัดการช่องว่างในชื่อเพื่อการ Merge ที่ถูกต้อง
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()

# ==========================================
# 3. Sidebar & Navigation
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("📌 Menu")
    menu = st.radio("Go to:", ["📊 Dashboard", "✍️ Submit Data"])
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

# ==========================================
# 4. Dashboard (อ้างอิงโค้ดแรกสุดที่ทำงานได้ดี)
# ==========================================
if menu == "📊 Dashboard":
    st.header("Research Performance Dashboard")
    
    # รวมข้อมูล (Merge)
    df_full = df_research.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )

    # Tabs การแสดงผล
    tab1, tab2, tab3 = st.tabs(["Individual", "Program KPI", "Faculty KPI"])

    with tab1:
        st.subheader("Individual Performance")
        st.dataframe(df_full[["ผู้เขียน", "ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "คณะ", "หลักสูตร"]], use_container_width=True)

    with tab2:
        st.subheader("Program KPI (IQA Standard)")
        # นับจำนวนอาจารย์ n ต่อหลักสูตร (ตามจำนวนใน Master)
        prog_n = df_master.groupby("หลักสูตร")["Name-surname"].nunique().reset_index(name="n")
        # รวมคะแนนต่อหลักสูตร
        prog_score = df_full.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        
        prog_report = prog_n.merge(prog_score, on="หลักสูตร", how="left").fillna(0)
        
        # สูตรการคำนวณ KPI (Score / n) * 5
        prog_report["KPI"] = (prog_report["คะแนน"] / prog_report["n"]) * 5
        
        st.dataframe(prog_report.style.format({"KPI": "{:.2f}"}), use_container_width=True)
        
        # กราฟ KPI รายหลักสูตร
        fig_prog = px.bar(prog_report, x="หลักสูตร", y="KPI", title="KPI Score by Program", color="หลักสูตร")
        st.plotly_chart(fig_prog, use_container_width=True)

    with tab3:
        st.subheader("Faculty KPI")
        # นับจำนวนอาจารย์ n ต่อคณะ
        fac_n = df_master.groupby("คณะ")["Name-surname"].nunique().reset_index(name="n")
        # รวมคะแนนต่อคณะ
        fac_score = df_full.groupby("คณะ")["คะแนน"].sum().reset_index()
        
        fac_report = fac_n.merge(fac_score, on="คณะ", how="left").fillna(0)
        fac_report["KPI"] = (fac_report["คะแนน"] / fac_report["n"]) * 5
        
        st.dataframe(fac_report.style.format({"KPI": "{:.2f}"}), use_container_width=True)
        
        # กราฟ KPI รายคณะ
        fig_fac = px.pie(fac_report, values="คะแนน", names="คณะ", title="Score Distribution by Faculty")
        st.plotly_chart(fig_fac, use_container_width=True)

# ==========================================
# 5. Submit Data
# ==========================================
elif menu == "✍️ Submit Data":
    if not st.session_state.logged_in:
        st.warning("Please login to submit data.")
    else:
        st.header("Submit New Publication")
        with st.form("add_form"):
            title = st.text_input("Research Title")
            year = st.number_input("Year (B.E.)", 2560, 2600, 2568)
            db = st.selectbox("Database", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
            # ให้เลือกผู้เขียนจาก Master
            author = st.selectbox("Author Name", df_master["Name-surname"].unique())
            
            score_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
            
            if st.form_submit_button("Submit"):
                if title:
                    client = conn_sheets()
                    sh = client.open("Research_Database")
                    ws = sh.worksheet("research")
                    ws.append_row([title, year, db, score_map[db], author])
                    st.success("Data Saved!")
                    time.sleep(1)
                    st.rerun()
