import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

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
# 2. FIXED VALUES (จำนวนอาจารย์คงที่ตามไฟล์ Excel)
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
    "คณะสาธารณสุขศาสตร์": 18,
    "คณะพยาบาลศาสตร์": 15
}

# ==========================================
# 3. Main Logic & Data Cleaning
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if not df_master.empty and not df_research.empty:
    # ล้างข้อมูลชื่อ: ตัดช่องว่าง และทำให้เป็นตัวพิมพ์ใหญ่-เล็กตามจริง (อ้างอิงจากภาพ Google Sheets)
    df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
    df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
    
    # แปลงคะแนนและปี
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. Dashboard Processing
# ==========================================
st.markdown("### 📊 Research Dashboard & KPI Tracking")

# เลือกปี
all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
year_option = st.sidebar.selectbox("📅 เลือกปี พ.ศ.:", ["All Years"] + [str(y) for y in all_years])

df_filtered = df_research.copy()
if year_option != "All Years":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# เชื่อมข้อมูล (Merge) เพื่อหาหลักสูตร/คณะ
df_full_info = df_filtered.merge(
    df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
    left_on="ผู้เขียน", 
    right_on="Name-surname", 
    how="left"
)

# --- ส่วนแจ้งเตือนชื่อที่สะกดไม่ตรง (87 รายการของคุณจะแสดงที่นี่) ---
mismatch = df_full_info[df_full_info['หลักสูตร'].isna()]
if not mismatch.empty:
    st.warning(f"⚠️ พบข้อมูล {len(mismatch)} รายการที่ชื่อผู้เขียนไม่ตรงกับฐานข้อมูล Master")
    with st.expander("🔍 ดูรายชื่อที่ต้องแก้ไขใน Google Sheets"):
        st.dataframe(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates(), use_container_width=True)

# ==========================================
# 5. Display Tabs
# ==========================================
t1, t2, t3 = st.tabs(["🎓 Program KPI", "🏢 Faculty KPI", "📋 Raw Data"])

with t1:
    st.markdown("#### 🏆 Program KPI Score")
    # 1 เรื่อง นับ 1 ครั้งต่อหลักสูตร
    prog_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
    prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
    
    # รวมกับรายชื่อหลักสูตรทั้งหมด
    report_p = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
    report_p = report_p.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

    def calc_kpi_p(row):
        n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
        # กำหนดกลุ่มเป้าหมาย x
        group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
        x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
        return round((((row["Total_Score"] / n) * 100) / x) * 5, 2)

    report_p["KPI Score"] = report_p.apply(calc_kpi_p, axis=1)
    st.plotly_chart(px.bar(report_p.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score", height=600), use_container_width=True)

with t2:
    st.markdown("#### 🏢 Faculty KPI Score")
    fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
    fac_sum = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
    
    report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
    report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

    def calc_kpi_f(row):
        n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
        y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
        return round((((row["Total_Score"] / n) * 100) / y) * 5, 2)

    report_f["KPI Score"] = report_f.apply(calc_kpi_f, axis=1)
    st.plotly_chart(px.bar(report_f, x="KPI Score", y="คณะ", orientation='h', text="KPI Score"), use_container_width=True)

with t3:
    st.dataframe(df_full_info, use_container_width=True)
