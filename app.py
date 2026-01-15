import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. การเชื่อมต่อข้อมูล (Database Connection)
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
            df.columns = df.columns.str.strip() 
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ==========================================
# 2. กำหนดค่าคงที่ (อ้างอิงตามไฟล์ Excel ของคุณ)
# ==========================================

# จำนวนอาจารย์รายหลักสูตร (ตัวหาร n)
FIXED_PROG_MEMBERS = {
    "BE": 5, "CA": 5, "B.Ed-Math": 5, "B.Ed-Sci": 5, "B.Ed-Eng": 5, "B.Ed-EC": 5,
    "G-Dip TH": 5, "G-Dip Inter": 5, "M.Ed-Admin": 3, "M.Ed-LMS": 3, "Ph.D-Admin": 3,
    "BBA": 9, "ACC": 5, "AB": 5, "ATC": 5, "AR": 5, "MBA": 3,
    "PH": 5, "OHS": 5, "MPH": 3, "NS": 5
}

# จำนวนอาจารย์รายคณะ (ตัวหาร n)
FIXED_FAC_MEMBERS = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15,
    "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40,
    "คณะสาธารณสุข": 18,
    "คณะพยาบาลศาสตร์": 15
}

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. การตั้งค่าหน้าจอและสไตล์
# ==========================================
st.set_page_config(page_title="Research KPI Dashboard", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    [data-testid="stMetricValue"] { color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Research KPI Performance (Fixed Multiplier)")

# Load Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("กำลังโหลดข้อมูลจาก Google Sheets...")
    st.stop()

# Cleaning Data
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. ฟิลเตอร์กรองข้อมูล (Sidebar)
# ==========================================
all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
year_option = st.sidebar.selectbox("📅 เลือกปีการศึกษา (พ.ศ.):", ["ทั้งหมด"] + [str(y) for y in all_years])

df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# เชื่อมข้อมูลสังกัด
df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

# ==========================================
# 5. การแสดงผล Dashboard
# ==========================================
t1, t2, t3 = st.tabs(["🎓 KPI รายหลักสูตร", "🏢 KPI รายคณะ", "📋 ข้อมูลดิบ"])

with t1:
    st.markdown(f"### ผลการดำเนินงานระดับหลักสูตร ปี {year_option}")
    
    # --- ตรรกะ: 1 เรื่องนับ 1 ครั้งต่อหลักสูตร ---
    prog_dedup = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
    
    prog_summary = prog_dedup.groupby("หลักสูตร").agg(
        Total_Score=("คะแนน", "sum"), 
        Total_Titles=("ชื่อเรื่อง", "count")
    ).reset_index()
    
    # สร้างตารางตามรายชื่อหลักสูตรที่มีค่าคงที่
    prog_report = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
    prog_report = prog_report.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

    def calc_prog_kpi(row):
        n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
        # กำหนดค่า Target (x)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
        x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
        
        # สูตร: ((คะแนนสะสม / จำนวนอาจารย์) * 100) / x * 5
        score = (((row["Total_Score"] / n) * 100) / x) * 5
        return round(score, 2)

    prog_report["KPI_Score"] = prog_report.apply(calc_prog_kpi, axis=1)
    
    # แสดงกราฟ
    fig_prog = px.bar(prog_report.sort_values("KPI_Score"), 
                      x="KPI_Score", y="หลักสูตร", orientation='h', 
                      text="KPI_Score", title="คะแนน KPI เปรียบเทียบรายหลักสูตร",
                      color="KPI_Score", color_continuous_scale="RdYlGn")
    st.plotly_chart(fig_prog, use_container_width=True)
    
    st.dataframe(prog_report.sort_values("KPI_Score", ascending=False), use_container_width=True, hide_index=True)

with t2:
    st.markdown(f"### ผลการดำเนินงานระดับคณะ ปี {year_option}")
    
    # --- ตรรกะ: 1 เรื่องนับ 1 ครั้งต่อคณะ ---
    fac_dedup = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
    
    fac_summary = fac_dedup.groupby("คณะ").agg(
        Total_Score=("คะแนน", "sum"), 
        Total_Titles=("ชื่อเรื่อง", "count")
    ).reset_index()
    
    fac_report = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
    fac_report = fac_report.merge(fac_summary, on="คณะ", how="left").fillna(0)

    def calc_fac_kpi(row):
        n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
        y = 30 if row["คณะ"] in ["คณะสาธารณสุข", "คณะพยาบาลศาสตร์"] else 20
        score = (((row["Total_Score"] / n) * 100) / y) * 5
        return round(score, 2)

    fac_report["Faculty_KPI"] = fac_report.apply(calc_fac_kpi, axis=1)
    
    fig_fac = px.bar(fac_report.sort_values("Faculty_KPI"), 
                     x="Faculty_KPI", y="คณะ", orientation='h', 
                     text="Faculty_KPI", color="Faculty_KPI",
                     template="plotly_white")
    st.plotly_chart(fig_fac, use_container_width=True)
    st.dataframe(fac_report, use_container_width=True, hide_index=True)

with t3:
    st.markdown("### ข้อมูลมาสเตอร์ (อาจารย์และบุคลากร)")
    st.dataframe(df_master, use_container_width=True)
