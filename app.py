import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

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

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. FIXED VALUES (ค่าคงที่จากไฟล์ Excel ของคุณ)
# ==========================================
# แก้ไขตัวเลขจำนวนอาจารย์ที่นี่เพื่อให้ตรงกับไฟล์ Excel ปีล่าสุด
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
# 3. Page Configuration & Style
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

# Data Cleaning & Type Protection
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 4. Sidebar & Navigation
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
            else: st.error("Wrong Password")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Main Content: Dashboard
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # เชื่อมข้อมูลสังกัด
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )

    m1, m2, m3 = st.columns(3)
    unique_titles_summary = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    m1.metric("Total Publications", f"{len(unique_titles_summary)} Titles")
    m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
    m3.metric("Weighted Score Sum", f"{unique_titles_summary['คะแนน'].sum():.2f}")

    t0, t1, t2, t3, t4 = st.tabs(["🏛 Overview", "🎓 Program KPI", "👤 Researcher Profile", "🏢 Faculty KPI", "📋 Master Database"])

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement")
        # กรอง 1 เรื่องต่อ 1 หลักสูตร
        prog_unique_res = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_summary = prog_unique_res.groupby("หลักสูตร").agg(
            Total_Score=("คะแนน", "sum"), 
            Total_Titles=("ชื่อเรื่อง", "count")
        ).reset_index()
        
        # ใช้รายชื่อหลักสูตรจากตัวหารคงที่เพื่อให้ตารางแสดงผลครบทุกหลักสูตร
        prog_report = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
        prog_report = prog_report.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1) # ใช้ค่าคงที่แทนการนับเอง
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(score, 2) # เอา min(..., 5.0) ออกเพื่อให้ตรงตาม Excel ที่มีคะแนนเกิน 5

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score", height=600, template="plotly_white"), use_container_width=True)
        st.dataframe(prog_report.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.markdown("#### 🏢 Faculty KPI Performance")
        res_fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = res_fac_unique.groupby("คณะ").agg(
            Total_Score=("คะแนน", "sum"), 
            Total_Titles=("ชื่อเรื่อง", "count")
        ).reset_index()
        
        fac_report = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        fac_report = fac_report.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_fac_kpi(row):
            f_name = row["คณะ"]
            n = FIXED_FAC_MEMBERS.get(f_name, 1) # ใช้ค่าคงที่
            y = 30 if f_name in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            score = (((row["Total_Score"] / n) * 100) / y) * 5
            return round(score, 2)

        fac_report["Faculty KPI Score"] = fac_report.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_report.sort_values("Faculty KPI Score"), x="Faculty KPI Score", y="คณะ", orientation='h', text="Faculty KPI Score", template="plotly_white"), use_container_width=True)
        st.dataframe(fac_report, use_container_width=True, hide_index=True)

    # (ส่วน Overview, Researcher Profile, Master Database คงเดิมตามโค้ดที่คุณส่งมา...)
    with t0:
        inst_summary = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")).reset_index().sort_values("ปี")
        st.plotly_chart(px.line(inst_summary[inst_summary['ปี']>0], x="ปี", y="Total_Weight", title="University Weighted Growth"), use_container_width=True)
    with t2:
        search_author = st.selectbox("🔍 Select Researcher:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- Select --":
            author_works = df_filtered[df_filtered["ผู้เขียน"] == search_author]
            st.dataframe(author_works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True)
    with t4:
        st.dataframe(df_master, use_container_width=True)

# ส่วน Admin Submit และ Manage Database คงเดิมตามโค้ดที่คุณส่งมา...
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
                for a in a_in: save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("Saved!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร'])
    st.dataframe(df_manage[['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']], use_container_width=True)
    target = st.selectbox("Select Title to Delete:", ["-- Select --"] + df_manage["ชื่อเรื่อง"].tolist())
    if target != "-- Select --" and st.button("Confirm Delete"):
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
        for r in sorted(rows, reverse=True): ws.delete_rows(r)
        st.success("Deleted!"); st.cache_data.clear(); st.rerun()
