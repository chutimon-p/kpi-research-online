import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database Connection (โครงเดิม)
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
# 2. FIXED VALUES (ตัวหารตามไฟล์ Excel)
# ==========================================
FIXED_PROG_MEMBERS = {
    "BE": 5, "CA": 5, "B.Ed-Math": 5, "B.Ed-Sci": 5, "B.Ed-Eng": 5, "B.Ed-EC": 5,
    "G-Dip TH": 5, "G-Dip Inter": 5, "M.Ed-Admin": 3, "M.Ed-LMS": 3, "Ph.D-Admin": 3,
    "BBA": 9, "ACC": 5, "AB": 5, "ATC": 5, "AR": 5, "MBA": 3,
    "PH": 5, "OHS": 5, "MPH": 3, "NS": 5
}

# ==========================================
# 3. Page Configuration & Setup
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# Load Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังเชื่อมต่อข้อมูลจาก Google Sheets...")
    st.stop()

# --- [หัวใจสำคัญ] บังคับให้ข้อมูลสะอาดก่อนแสดงผล ---
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# Sidebar
all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
year_option = st.sidebar.selectbox("📅 เลือกปี พ.ศ.:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard Logic
# ==========================================
df_filtered = df_research.copy()
if year_option != "All Years":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# เชื่อมข้อมูลสังกัด
df_full = df_filtered.merge(
    df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
    left_on="ผู้เขียน", 
    right_on="Name-surname", 
    how="left"
)

t1, t2, t3 = st.tabs(["📊 KPI Dashboard", "👤 Individual", "🔍 Debug Data"])

with t1:
    st.markdown("#### 🏆 Program KPI")
    # 1 ชื่อเรื่อง นับ 1 ครั้งต่อหลักสูตร
    prog_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
    prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
    
    # รวมกับรายชื่อหลักสูตรทั้งหมด
    report = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
    report = report.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

    def calc_kpi(row):
        n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
        # กำหนดกลุ่มเป้าหมาย (x)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
        x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
        return round((((row["Total_Score"] / n) * 100) / x) * 5, 2)

    report["KPI Score"] = report.apply(calc_kpi, axis=1)
    
    st.plotly_chart(px.bar(report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score"), use_container_width=True)
    st.dataframe(report.sort_values("KPI Score", ascending=False), use_container_width=True)

with t3:
    st.subheader("🛠 ทำไมข้อมูลถึงไม่ขึ้น?")
    # เช็คว่ามีงานวิจัยกี่รายการที่หาหลักสูตรไม่เจอ
    mismatch = df_full[df_full['หลักสูตร'].isna()]
    if not mismatch.empty:
        st.error(f"พบงานวิจัย {len(mismatch)} รายการที่ 'ไม่รู้สังกัด' (ชื่ออาจารย์ไม่ตรงกับ Master)")
        st.write("รายชื่ออาจารย์ที่ต้องแก้ไขใน Google Sheets (สะกดไม่ตรง):")
        st.write(mismatch['ผู้เขียน'].unique())
    else:
        st.success("✅ ข้อมูลเชื่อมโยงถูกต้องทั้งหมดแล้ว")
