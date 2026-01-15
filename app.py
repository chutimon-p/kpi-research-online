import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. การเชื่อมต่อข้อมูล
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
# 2. กำหนดค่าตัวหารคงที่ (Fixed Dividers)
# ==========================================
FIXED_PROG_MEMBERS = {
    "BE": 5, "CA": 5, "B.Ed-Math": 5, "B.Ed-Sci": 5, "B.Ed-Eng": 5, "B.Ed-EC": 5,
    "G-Dip TH": 5, "G-Dip Inter": 5, "M.Ed-Admin": 3, "M.Ed-LMS": 3, "Ph.D-Admin": 3,
    "BBA": 9, "ACC": 5, "AB": 5, "ATC": 5, "AR": 5, "MBA": 3,
    "PH": 5, "OHS": 5, "MPH": 3, "NS": 5
}

FIXED_FAC_MEMBERS = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15,
    "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40,
    "คณะสาธารณสุข": 18,
    "คณะพยาบาลศาสตร์": 15
}

# ==========================================
# 3. เริ่มต้นแอปและเตรียมข้อมูล
# ==========================================
st.set_page_config(page_title="Research KPI Dashboard", layout="wide")

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ ไม่พบข้อมูลใน Google Sheets")
    st.stop()

# --- ป้องกัน Error: บังคับคอลัมน์ที่ใช้ Merge ให้เป็น String ทั้งหมด ---
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()

# Cleaning อื่นๆ
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. ฟิลเตอร์และการจัดการข้อมูล
# ==========================================
st.sidebar.header("📌 Filter")
all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
year_option = st.sidebar.selectbox("เลือกปี (พ.ศ.):", ["ทั้งหมด"] + [str(y) for y in all_years])

df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# Merge ข้อมูล (เพิ่มตรรกะจัดการ Error)
try:
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมโยงข้อมูล: {e}")
    st.stop()

# ==========================================
# 5. การคำนวณและแสดงผล
# ==========================================
t1, t2 = st.tabs(["🎓 KPI รายหลักสูตร", "🏢 KPI รายคณะ"])

with t1:
    st.subheader(f"📊 ผลคะแนนรายหลักสูตร ({year_option})")
    
    # กรองเรื่องซ้ำ: 1 เรื่อง 1 หลักสูตร
    prog_dedup = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
    prog_summary = prog_dedup.groupby("หลักสูตร").agg(
        Total_Score=("คะแนน", "sum"),
        Total_Titles=("ชื่อเรื่อง", "count")
    ).reset_index()

    # นำมาแมพกับตัวหารค่าคงที่
    prog_report = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
    prog_report = prog_report.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

    def calc_prog_kpi(row):
        n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
        x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
        # สูตร: ((Score/n)*100)/x * 5
        score = (((row["Total_Score"] / n) * 100) / x) * 5
        return round(score, 2)

    prog_report["คะแนน KPI"] = prog_report.apply(calc_prog_kpi, axis=1)
    
    # กราฟ
    fig = px.bar(prog_report.sort_values("คะแนน KPI"), x="คะแนน KPI", y="หลักสูตร", 
                 orientation='h', text="คะแนน KPI", color="คะแนน KPI",
                 color_continuous_scale="Viridis")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(prog_report.sort_values("คะแนน KPI", ascending=False), use_container_width=True)

with t2:
    st.subheader(f"🏢 ผลคะแนนรายคณะ ({year_option})")
    
    # กรองเรื่องซ้ำ: 1 เรื่อง 1 คณะ
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

    fac_report["คะแนน KPI คณะ"] = fac_report.apply(calc_fac_kpi, axis=1)
    
    st.plotly_chart(px.bar(fac_report, x="คะแนน KPI คณะ", y="คณะ", orientation='h', text="คะแนน KPI คณะ"), use_container_width=True)
    st.dataframe(fac_report, use_container_width=True)
