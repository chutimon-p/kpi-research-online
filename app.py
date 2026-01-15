import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database Connection (โครงสร้างเดิมของคุณ)
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
# 2. FIXED VALUES & STRUCTURE (ส่วนที่เพิ่มตาม Excel)
# ==========================================
# รายการ 21 หลักสูตร เรียงลำดับตามคณะ พร้อมจำนวนอาจารย์ (n)
PROGRAM_STRUCTURE = [
    {"คณะ": "มนุษย์ศาสตร์และสังคมศาสตร์", "หลักสูตร": "BE", "n": 5},
    {"คณะ": "มนุษย์ศาสตร์และสังคมศาสตร์", "หลักสูตร": "CA", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "B.Ed-Math", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "B.Ed-Sci", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "B.Ed-Eng", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "B.Ed-EC", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "G-Dip TH", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "G-Dip Inter", "n": 5},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "M.Ed-Admin", "n": 3},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "M.Ed-LMS", "n": 3},
    {"คณะ": "คณะศึกษาศาสตร์", "หลักสูตร": "Ph.D-Admin", "n": 3},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "BBA", "n": 9},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "ACC", "n": 5},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "AB", "n": 5},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "ATC", "n": 5},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "AR", "n": 5},
    {"คณะ": "คณะบริหารธุรกิจบัณฑิต", "หลักสูตร": "MBA", "n": 3},
    {"คณะ": "คณะสาธารณสุขศาสตร์", "หลักสูตร": "PH", "n": 5},
    {"คณะ": "คณะสาธารณสุขศาสตร์", "หลักสูตร": "OHS", "n": 5},
    {"คณะ": "คณะสาธารณสุขศาสตร์", "หลักสูตร": "MPH", "n": 3},
    {"คณะ": "คณะพยาบาลศาสตร์", "หลักสูตร": "NS", "n": 5}
]
df_prog_base = pd.DataFrame(PROGRAM_STRUCTURE)

# จำนวนอาจารย์รายคณะ (n_fac)
FACULTY_N = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15, "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40, "คณะสาธารณสุขศาสตร์": 18, "คณะพยาบาลศาสตร์": 15
}

# ==========================================
# 3. Page Configuration (โครงสร้างเดิมของคุณ)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #1E3A8A; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; font-weight: bold; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ... (ส่วน Header Logo และ Title คงเดิมตามไฟล์ของคุณ) ...

# Load Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

# Data Cleaning
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 4. Sidebar & Logic (โครงสร้างเดิมของคุณ)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
# ... (ส่วน Login/Logout และ Sidebar คงเดิมตามไฟล์ของคุณ) ...

# ==========================================
# 5. Dashboard & Reports (จุดที่มีการแก้ไขการจัดกลุ่ม)
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # 🔗 เชื่อมข้อมูลงานวิจัยกับ Master Data
    df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

    t0, t1, t2, t3, t4 = st.tabs(["🏛 Overview", "🎓 Program KPI", "🏢 Faculty KPI", "👤 Researcher Profile", "📋 Mismatch Check"])

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement (Grouped by Faculty)")
        
        # ตัดเรื่องซ้ำระดับหลักสูตร
        df_unique_agency = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_summary = df_unique_agency.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        # รวมเข้ากับโครงสร้าง 21 หลักสูตรที่กำหนดไว้ (เพื่อให้เรียงลำดับตามคณะและแสดงครบทุกหลักสูตร)
        prog_report = df_prog_base.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = row["n"] # ใช้ n จากโครงสร้างที่กำหนดไว้
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(score, 2)

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        
        # แสดงกราฟ - บังคับลำดับแกน Y ตาม df_prog_base
        fig_p = px.bar(prog_report, 
                       x="KPI Score", 
                       y="หลักสูตร", 
                       color="คณะ", 
                       orientation='h', 
                       text="KPI Score",
                       height=700,
                       category_orders={"หลักสูตร": df_prog_base["หลักสูตร"].tolist()}, # จัดลำดับที่นี่
                       template="plotly_white")
        
        st.plotly_chart(fig_p, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 🏢 Faculty KPI Performance")
        # ตัดเรื่องซ้ำระดับคณะ
        res_fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = res_fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()

        # สร้างตารางคณะตามเป้าหมาย n ใน FACULTY_N
        report_f = pd.DataFrame(list(FACULTY_N.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_fac_kpi(row):
            f_name = row["คณะ"]
            n = FACULTY_N.get(f_name, 1)
            y = 30 if f_name in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            score = (((row["Total_Score"] / n) * 100) / y) * 5
            return round(score, 2)

        report_f["Faculty Score"] = report_f.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(report_f.sort_values("Faculty Score"), x="Faculty Score", y="คณะ", orientation='h', text="Faculty Score", color="คณะ", template="plotly_white"), use_container_width=True)

    with t4:
        # ส่วนตรวจสอบชื่อสะกดผิด (Mismatch)
        mismatch = df_full_info[df_full_info['หลักสูตร'].isna()]
        if not mismatch.empty:
            st.error(f"⚠️ พบข้อมูล {len(mismatch)} รายการที่ระบุชื่อผู้เขียนไม่ตรงกับตาราง Master")
            st.dataframe(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates(), use_container_width=True)
        else:
            st.success("✅ ข้อมูลทั้งหมดถูกต้อง")

# ==========================================
# 6. Admin Sections
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Title").strip()
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        with c2: j_in = st.selectbox("Journal Database", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("Save Record"):
            if t_in and a_in:
                existing_titles = [t.lower() for t in df_research["ชื่อเรื่อง"].unique()]
                if t_in.lower() in existing_titles:
                    st.warning(f"⚠️ Title '{t_in}' already exists.")
                else:
                    for a in a_in: 
                        save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                    st.success("✅ Recorded Successfully!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    if not df_research.empty:
        df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']).sort_values(by=['ปี', 'ชื่อเรื่อง'], ascending=[False, True])
        st.dataframe(df_manage[['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']], use_container_width=True, hide_index=True)
        opts = ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']} | {r['ฐานวารสาร']}" for _, r in df_manage.iterrows()]
        sel = st.selectbox("Delete Entry:", opts)
        if sel != "-- Select --":
            target = sel.split(" | ")[1].strip()
            if st.button("Confirm Delete"):
                with st.spinner("Deleting..."):
                    ws = conn_sheets().open("Research_Database").worksheet("research")
                    rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
                    for r in sorted(rows, reverse=True): ws.delete_rows(r)
                    st.success("Deleted!"); st.cache_data.clear(); st.rerun()

