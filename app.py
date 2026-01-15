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

# ==========================================
# 2. FIXED VALUES (ค่า n และ x ตามไฟล์ Excel)
# ==========================================
# จำนวนอาจารย์รายหลักสูตร (n)
FIXED_PROG_MEMBERS = {
    "BE": 5, "CA": 5, "B.Ed-Math": 5, "B.Ed-Sci": 5, "B.Ed-Eng": 5, "B.Ed-EC": 5,
    "G-Dip TH": 5, "G-Dip Inter": 5, "M.Ed-Admin": 3, "M.Ed-LMS": 3, "Ph.D-Admin": 3,
    "BBA": 9, "ACC": 5, "AB": 5, "ATC": 5, "AR": 5, "MBA": 3,
    "PH": 5, "OHS": 5, "MPH": 3, "NS": 5
}

# จำนวนอาจารย์รายคณะ (n_fac)
FIXED_FAC_MEMBERS = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15,
    "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40,
    "คณะสาธารณสุขศาสตร์": 18,
    "คณะพยาบาลศาสตร์": 15
}

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Page Setup & Data Loading
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

# ทำความสะอาดข้อมูลเบื้องต้น
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. Sidebar Menu
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

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Page: Dashboard
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # เชื่อมข้อมูลหา คณะ/หลักสูตร
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

    st.markdown(f"## 📈 Performance Overview: {year_option}")
    
    t1, t2, t3, t4 = st.tabs(["🎓 Program KPI", "🏢 Faculty KPI", "👤 Researcher Profile", "🔍 Check Mismatch"])

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement (Manual Calc Logic)")
        # 1 เรื่อง นับ 1 ครั้งต่อหลักสูตร
        prog_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        report_p = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
        report_p = report_p.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi_p(row):
            n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(score, 2)

        report_p["KPI Score"] = report_p.apply(calc_kpi_p, axis=1)
        st.plotly_chart(px.bar(report_p.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', text="KPI Score", height=600, color_discrete_sequence=['#1E3A8A']))
        st.dataframe(report_p.sort_values("KPI Score", ascending=False), use_container_width=True)

    with t2:
        st.markdown("#### 🏢 Faculty KPI Performance")
        fac_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_kpi_f(row):
            n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            score = (((row["Total_Score"] / n) * 100) / y) * 5
            return round(score, 2)

        report_f["Faculty Score"] = report_f.apply(calc_kpi_f, axis=1)
        st.plotly_chart(px.bar(report_f.sort_values("Faculty Score"), x="Faculty Score", y="คณะ", orientation='h', text="Faculty Score", color_discrete_sequence=['#3B82F6']))

    with t3:
        search_author = st.selectbox("🔍 Researcher Search:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- Select --":
            works = df_filtered[df_filtered["ผู้เขียน"] == search_author]
            st.metric("Total Score", f"{works['คะแนน'].sum():.2f}")
            st.dataframe(works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], hide_index=True)

    with t4:
        mismatch = df_full[df_full['หลักสูตร'].isna()]
        if not mismatch.empty:
            st.error(f"⚠️ Found {len(mismatch)} records with mismatched names.")
            st.dataframe(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates(), use_container_width=True)
        else:
            st.success("✅ All data is correctly mapped to Master records.")

# ==========================================
# 6. Page: Submit Research
# ==========================================
elif menu == "✍️ Submit Research":
    st.header("✍️ Register New Publication")
    with st.form("research_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่อง (Title)")
        year = st.number_input("ปี (พ.ศ.)", 2560, 2570, 2567)
        source = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        author = st.selectbox("ชื่อผู้เขียน (Master List)", sorted(df_master["Name-surname"].unique().tolist()))
        
        if st.form_submit_button("Save Record"):
            if title and author:
                client = conn_sheets()
                ws = client.open("Research_Database").worksheet("research")
                ws.append_row([title, year, source, SCORE_MAP[source], author])
                st.success("บันทึกสำเร็จ!")
                st.rerun()

# ==========================================
# 7. Page: Manage Database
# ==========================================
elif menu == "⚙️ Manage Database":
    st.header("⚙️ Database Management")
    st.write("รายการทั้งหมด (เลือกเพื่อลบ)")
    
    # ดึงข้อมูลใหม่เพื่อความสดใหม่
    df_manage = load_sheet_data("research")
    st.dataframe(df_manage, use_container_width=True)
    
    row_idx = st.number_input("ใส่หมายเลขแถวที่ต้องการลบ (นับจากแถว 2)", min_value=2, step=1)
    if st.button("🗑 ลบแถวที่เลือก"):
        client = conn_sheets()
        ws = client.open("Research_Database").worksheet("research")
        ws.delete_rows(int(row_idx))
        st.success(f"ลบแถวที่ {row_idx} สำเร็จ!")
        st.rerun()
