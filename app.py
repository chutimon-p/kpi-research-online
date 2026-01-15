import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. การเชื่อมต่อ Google Sheets (Core)
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

def save_to_sheet(sheet_name, new_row_list):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(new_row_list)
            return True
        except: return False
    return False

# ==========================================
# 2. ค่าคงที่ (อ้างอิงจาก Excel และภาพ Masters)
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

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. เริ่มต้นระบบและโหลดข้อมูล
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังโหลดข้อมูล...")
    st.stop()

# Clean Data ทันทีที่โหลด (แก้ปัญหา 87 รายการ)
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. Sidebar เมนู (โครงสร้างเดิม)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("📌 Menu")
    menu_list = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_list.insert(0, "✍️ Submit Research")
        menu_list.append("⚙️ Manage Database")
    
    menu = st.radio("Go to Page:", menu_list)
    
    st.divider()
    # Login Section
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == st.secrets.get("ADMIN_PASSWORD"):
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

# ==========================================
# 5. ฟังก์ชันแสดงผลหน้า Dashboard
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.header("📊 Research Dashboard")
    
    # ตัวกรองปี
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_choice = st.selectbox("เลือกปี พ.ศ.:", ["All Years"] + [str(y) for y in all_years])
    
    df_filtered = df_research.copy()
    if year_choice != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_choice)]
    
    # Merge หาหลักสูตร/คณะ
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    
    # แจ้งเตือน Mismatch (87 รายการ)
    mismatch = df_full[df_full['หลักสูตร'].isna()]
    if not mismatch.empty:
        st.error(f"⚠️ พบงานวิจัย {len(mismatch)} รายการที่ชื่ออาจารย์ไม่ตรงกับฐานข้อมูล Master")
        with st.expander("คลิกเพื่อดูรายชื่อที่ต้องแก้ไขใน Google Sheets"):
            st.table(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates().head(20))

    tab1, tab2, tab3 = st.tabs(["🎓 Program KPI", "🏢 Faculty KPI", "📋 Data Table"])

    with tab1:
        prog_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        report_p = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
        report_p = report_p.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_p(row):
            n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round((((row["Total_Score"] / n) * 100) / x) * 5, 2)

        report_p["KPI Score"] = report_p.apply(calc_p, axis=1)
        st.plotly_chart(px.bar(report_p.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score", height=600))

    with tab2:
        fac_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_f(row):
            n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            return round((((row["Total_Score"] / n) * 100) / y) * 5, 2)

        report_f["Faculty Score"] = report_f.apply(calc_f, axis=1)
        st.plotly_chart(px.bar(report_f, x="Faculty Score", y="คณะ", orientation='h', text="Faculty Score"))

    with tab3:
        st.dataframe(df_full, use_container_width=True)

# ==========================================
# 6. ฟังก์ชันหน้า Submit Research
# ==========================================
elif menu == "✍️ Submit Research":
    st.header("✍️ Submit New Research")
    with st.form("research_form"):
        title = st.text_input("ชื่อเรื่อง (Research Title)")
        year = st.number_input("ปี (พ.ศ.)", min_value=2560, max_value=2570, value=2567)
        source = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        author = st.selectbox("ชื่อผู้เขียน (อ้างอิงจาก Master)", sorted(df_master['Name-surname'].tolist()))
        
        if st.form_submit_button("Submit"):
            score = SCORE_MAP[source]
            new_data = [title, year, source, score, author]
            if save_to_sheet("research", new_data):
                st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว!")
                st.rerun()
            else:
                st.error("❌ เกิดข้อผิดพลาดในการบันทึก")

# ==========================================
# 7. ฟังก์ชันหน้า Manage Database
# ==========================================
elif menu == "⚙️ Manage Database":
    st.header("⚙️ Manage Research Records")
    st.write("รายการงานวิจัยทั้งหมด (เลือกเพื่อลบข้อมูล)")
    
    # เพิ่ม Index เพื่อใช้อ้างอิงการลบ
    df_manage = df_research.copy()
    df_manage['ID'] = range(2, len(df_manage) + 2) # เริ่มต้นที่แถว 2 ใน Google Sheets
    
    st.dataframe(df_manage, use_container_width=True)
    
    row_to_delete = st.number_input("ใส่หมายเลขลำดับที่ต้องการลบ (จากตารางด้านบน)", min_value=2, step=1)
    if st.button("🗑 ลบข้อมูลแถวนี้"):
        client = conn_sheets()
        if client:
            sh = client.open("Research_Database")
            ws = sh.worksheet("research")
            ws.delete_rows(int(row_to_delete))
            st.success(f"ลบข้อมูลแถวที่ {row_to_delete} สำเร็จ!")
            st.rerun()
