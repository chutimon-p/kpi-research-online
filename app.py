import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database Connection (โครงสร้างเดิม)
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

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. FIXED VALUES (ตัวหารตามไฟล์ Excel)
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

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Page Configuration & Header
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังดึงข้อมูลจาก Google Sheets...")
    st.stop()

# --- [หัวใจสำคัญ] การ Clean ข้อมูลเพื่อแก้ปัญหา 87 รายการที่ไม่ขึ้น ---
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. Sidebar & Logic การกรอง
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    menu = st.radio("Go to Page:", menu_options)
    
    st.divider()
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # การ Merge ข้อมูล
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )

    # --- ส่วนแจ้งเตือนและตรวจสอบชื่อ (ช่วยแก้ 87 รายการ) ---
    mismatch = df_full_info[df_full_info['หลักสูตร'].isna()]
    if not mismatch.empty:
        st.error(f"⚠️ พบงานวิจัย {len(mismatch)} แถว ที่ชื่อผู้เขียนไม่ตรงกับฐานข้อมูล Master (ข้อมูลจึงไม่แสดงบนกราฟ)")
        with st.expander("🔍 คลิกเพื่อดูรายชื่อที่ต้องแก้ไขใน Google Sheets"):
            st.dataframe(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates(), use_container_width=True)

    t1, t2, t3 = st.tabs(["🎓 KPI รายหลักสูตร", "🏢 KPI รายคณะ", "📋 ข้อมูลดิบ"])

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement")
        prog_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_summary = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        report_p = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
        report_p = report_p.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi_p(row):
            n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round((((row["Total_Score"] / n) * 100) / x) * 5, 2)

        report_p["KPI Score"] = report_p.apply(calc_kpi_p, axis=1)
        st.plotly_chart(px.bar(report_p.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score", height=600), use_container_width=True)
        st.dataframe(report_p.sort_values("KPI Score", ascending=False), use_container_width=True)

    with t2:
        st.markdown("#### 🏢 Faculty KPI Performance")
        fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_summary = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_summary, on="คณะ", how="left").fillna(0)

        def calc_kpi_f(row):
            n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์", "คณะสาธารณสุข"] else 20
            return round((((row["Total_Score"] / n) * 100) / y) * 5, 2)

        report_f["KPI Score"] = report_f.apply(calc_kpi_f, axis=1)
        st.plotly_chart(px.bar(report_f, x="KPI Score", y="คณะ", orientation='h', text="KPI Score"), use_container_width=True)

    with t3:
        st.dataframe(df_full_info, use_container_width=True)

# (ส่วนหน้าบันทึกและจัดการฐานข้อมูล คงไว้ตามโค้ดเดิมของคุณได้เลยครับ)
