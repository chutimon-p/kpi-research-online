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
# 2. FIXED STRUCTURE (จัดกลุ่มคณะ-หลักสูตร และค่า n)
# ==========================================
PROGRAM_DATA = [
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

df_structure = pd.DataFrame(PROGRAM_DATA)
FIXED_FAC_MEMBERS = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15, "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40, "คณะสาธารณสุขศาสตร์": 18, "คณะพยาบาลศาสตร์": 15
}
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Page Configuration & Header (โครงสร้างเดิม)
# ==========================================
st.set_page_config(page_title="STIU Research Management", layout="wide")

# CSS Styling
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets...")
    st.stop()

# Clean Data
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. Sidebar & Logic (โครงสร้างเดิม)
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
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Dashboard Page
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # Merge ข้อมูลเพื่อหาคณะ/หลักสูตร
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Publications", f"{df_filtered['ชื่อเรื่อง'].nunique()} Titles")
    m2.metric("Weighted Score Sum", f"{df_filtered['คะแนน'].sum():.2f}")
    m3.metric("Mismatch Records", f"{df_full['หลักสูตร'].isna().sum()}")

    t1, t2, t3, t4 = st.tabs(["🎓 Program KPI", "🏢 Faculty KPI", "👤 Researcher Profile", "📋 Raw Data"])

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement (Grouped by Faculty)")
        # คำนวณรายหลักสูตร
        prog_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        # เชื่อมกับโครงสร้าง 21 หลักสูตรที่เรียงลำดับไว้แล้ว
        report_p = df_structure.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi_p(row):
            n = row["n"]
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(score, 2)

        report_p["KPI Score"] = report_p.apply(calc_kpi_p, axis=1)

        # กราฟแท่งจัดกลุ่มตามคณะ
        fig_p = px.bar(report_p, x="KPI Score", y="หลักสูตร", color="คณะ", 
                     orientation='h', text="KPI Score", height=700,
                     category_orders={"หลักสูตร": df_structure["หลักสูตร"].tolist()},
                     template="plotly_white")
        st.plotly_chart(fig_p, use_container_width=True)
        st.dataframe(report_p, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 🏢 Faculty KPI Performance")
        fac_unique = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_kpi_f(row):
            n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์", "คณะสาธารณสุข"] else 20
            score = (((row["Total_Score"] / n) * 100) / y) * 5
            return round(score, 2)

        report_f["Faculty Score"] = report_f.apply(calc_kpi_f, axis=1)
        st.plotly_chart(px.bar(report_f, x="Faculty Score", y="คณะ", orientation='h', text="Faculty Score", color="คณะ"))

    with t3:
        search_author = st.selectbox("🔍 Researcher Portfolio:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- Select --":
            author_works = df_filtered[df_filtered["ผู้เขียน"] == search_author]
            st.metric("Total Score", f"{author_works['คะแนน'].sum():.2f}")
            st.dataframe(author_works, use_container_width=True, hide_index=True)

    with t4:
        # ส่วนตรวจสอบ Mismatch (87 รายการ)
        mismatch = df_full[df_full['หลักสูตร'].isna()]
        if not mismatch.empty:
            st.error(f"⚠️ Found {len(mismatch)} records with mismatched names.")
            st.write("Please fix these names in Google Sheets (Sheet: research) to match Master records.")
            st.dataframe(mismatch[['ผู้เขียน', 'ชื่อเรื่อง']].drop_duplicates(), use_container_width=True)
        st.dataframe(df_full, use_container_width=True)

# ==========================================
# 6. Admin Sections (โครงสร้างเดิม)
# ==========================================
elif menu == "✍️ Submit Research":
    st.header("✍️ Submit Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Title")
        y_in = st.number_input("Year (B.E.)", 2560, 2570, 2568)
        j_in = st.selectbox("Journal Database", list(SCORE_MAP.keys()))
        a_in = st.selectbox("Author", sorted(df_master["Name-surname"].unique().tolist()))
        if st.form_submit_button("Save Record"):
            if save_to_sheet("research", [t_in, y_in, j_in, SCORE_MAP[j_in], a_in]):
                st.success("Record Saved!"); st.rerun()

elif menu == "⚙️ Manage Database":
    st.header("⚙️ Database Management")
    df_manage = load_sheet_data("research")
    st.dataframe(df_manage, use_container_width=True)
    row_idx = st.number_input("Row index to delete (starting from 2)", min_value=2, step=1)
    if st.button("🗑 Delete Row"):
        client = conn_sheets()
        ws = client.open("Research_Database").worksheet("research")
        ws.delete_rows(int(row_idx))
        st.success(f"Row {row_idx} deleted!"); st.rerun()
