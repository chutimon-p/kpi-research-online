import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ==========================================
# 1. การเชื่อมต่อ Google Sheets
# ==========================================
def conn_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลจาก Secrets ได้ (gcp_service_account)")
        st.stop()
    return gspread.authorize(creds)

def load_sheet_data(sheet_name):
    client = conn_sheets()
    # *** ตรวจสอบชื่อไฟล์ Google Sheets ของคุณให้ถูกต้อง ***
    sh = client.open("Research_Database") 
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip() 
    return df

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    sh = client.open("Research_Database")
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. การตั้งค่าหน้าเว็บและดีไซน์ (Header & Branding)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# Custom CSS เพื่อความสวยงาม
st.markdown("""
    <style>
    /* ปรับแต่ง Font และสีพื้นหลัง */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Sarabun', sans-serif;
    }
    .main {
        background-color: #f8f9fa;
    }
    /* ปรับแต่งปุ่ม */
    .stButton>button {
        border-radius: 8px;
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #3b82f6;
        border-color: #3b82f6;
    }
    /* ปรับแต่ง Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #e5e7eb;
        border-radius: 5px 5px 0px 0px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ส่วนหัวเว็บไซต์ (Header)
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    # โลโก้มหาวิทยาลัย
    st.image("https://www.stic.ac.th/wp-content/uploads/2021/03/logo-stic.png", width=100)
with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="color: #1E3A8A; margin-bottom: 0px;">St Teresa International University</h1>
            <p style="color: #4B5563; font-size: 1.2rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# โหลดข้อมูล
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
try:
    df_master = load_sheet_data("masters")
    df_research = load_sheet_data("research")
except Exception as e:
    st.error(f"⚠️ การเชื่อมต่อฐานข้อมูลขัดข้อง: {e}")
    st.stop()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar (เมนูข้างขวา)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("Go to", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        st.markdown("#### 🔐 Admin Access")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Incorrect Password")
    else:
        st.success("🔓 Logged in as Admin")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.divider()
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("📅 Academic Year", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้าจอแสดงผล (Reports)
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.subheader(f"📈 Research Performance Report ({year_option})")
    
    # สถิติสรุปเบื้องต้น (Metrics)
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Research", f"{len(df_filtered.drop_duplicates(subset=['ชื่อเรื่อง']))} Titles")
    m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
    m3.metric("Total Weighted Score", f"{df_filtered['คะแนน'].sum():.2f}")

    # Tabs สำหรับรายงานแต่ละประเภท
    t1, t2, t3, t4 = st.tabs(["🎓 Program KPI", "👤 Researcher", "🏛 Faculty", "📋 Master Data"])

    with t1:
        st.markdown("#### 🏆 ความก้าวหน้า KPI รายหลักสูตร")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        prog_sum = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        prog_sum = prog_sum.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = faculty_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["คะแนน"] / n) * 100) / x) * 5, 5.0), 2)

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        prog_report = prog_report.sort_values(by=["คณะ", "KPI Score"])

        fig = px.bar(prog_report, x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', 
                     range_x=[0, 5.5], text="KPI Score", height=600,
                     color_discrete_sequence=px.colors.qualitative.Prism)
        fig.add_vline(x=5.0, line_dash="dash", line_color="#ef4444", annotation_text="Target (5.0)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 👤 ผลงานแยกตามรายบุคคล")
        if not df_filtered.empty:
            p_report = df_filtered.groupby("ผู้เขียน").agg(Total_Titles=("ชื่อเรื่อง", "count"), Total_Score=("คะแนน", "sum")).reset_index()
            st.dataframe(p_report.sort_values("Total_Score", ascending=False), use_container_width=True)
            sel = st.selectbox("Select researcher to see details:", ["-- Select --"] + p_report["ผู้เขียน"].tolist())
            if sel != "-- Select --":
                st.table(df_filtered[df_filtered["ผู้เขียน"] == sel][["ชื่อเรื่อง", "ฐานวารสาร", "ปี", "คะแนน"]])
        else: st.info("No research data found for this year.")

    with t3:
        st.markdown("#### 🏛 คะแนนสะสมถ่วงน้ำหนักแยกตามคณะ")
        res_with_prog = df_research.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        if not res_with_prog.empty and "คณะ" in res_with_prog.columns:
            fac_data = res_with_prog.dropna(subset=["คณะ"])
            fac_sum = fac_data.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby(["ปี", "คณะ"])["คะแนน"].sum().reset_index()
            fac_sum["ปี"] = fac_sum["ปี"].astype(str)
            st.plotly_chart(px.bar(fac_sum, x="ปี", y="คะแนน", color="คณะ", barmode="group", text_auto='.2f'), use_container_width=True)

    with t4:
        st.markdown("#### 📋 ข้อมูลอาจารย์และหลักสูตรทั้งหมด")
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. หน้าบันทึกข้อมูล (Admin)
# ==========================================
elif menu == "✍️ Submit Research":
    st.subheader("✍️ Add New Research Publication")
    with st.form("add_form", clear_on_submit=True):
        t_in = st.text_input("Research Title (ชื่อเรื่อง)")
        c1, c2 = st.columns(2)
        with c1:
            y_in = st.number_input("Year (พ.ศ.)", 2560, 2600, 2568)
        with c2:
            j_in = st.selectbox("Journal Database (ฐานข้อมูล)", list(SCORE_MAP.keys()))
        
        a_in = st.multiselect("Authors (เลือกอาจารย์ผู้เขียน)", df_master["Name-surname"].unique().tolist())
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Save to Cloud"):
            if t_in and a_in:
                for author in a_in:
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                st.success("✅ Successfully saved to Google Sheets!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Please fill in all required fields.")

elif menu == "⚙️ Manage Database":
    st.subheader("⚙️ Database Management")
    st.info("Caution: Deleting a record here will permanently remove it from Google Sheets.")
    if not df_research.empty:
        # ลบโดยอ้างอิงชื่อเรื่อง
        unique_titles = df_research["ชื่อเรื่อง"].unique()
        to_del = st.selectbox("Select title to delete:", unique_titles)
        if st.button("🗑 Confirm Delete"):
            client = conn_sheets()
            sh = client.open("Research_Database")
            ws = sh.worksheet("research")
            try:
                cell = ws.find(to_del)
                ws.delete_rows(cell.row)
                st.success(f"Deleted: {to_del}")
                st.cache_data.clear()
                st.rerun()
            except:
                st.error("Could not find the record.")
