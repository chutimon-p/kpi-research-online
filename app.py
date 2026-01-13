import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database Connection & Helper Functions
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
# 2. Page Configuration & Setup
# ==========================================
st.set_page_config(page_title="STIU Research Management", layout="wide")

# Constants
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# Load Primary Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

# Header
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try: st.image("logo.jpg", width=150)
    except: st.info("🏫 STIU")

with header_col2:
    st.markdown("<h1 style='color: #1E3A8A;'>St Teresa International University</h1>", unsafe_allow_html=True)
    st.markdown("### Research Management & KPI Tracking System")

st.divider()

# ==========================================
# 3. Sidebar & Auth
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    menu_options = ["📊 Overall Dashboard", "🎓 Program & Faculty Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Data Entry")
        menu_options.append("⚙️ Manage Data")
    
    menu = st.radio("Select Page", menu_options)
    
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

    st.divider()
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("📅 Year Filter", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Logic: Data Processing (Unique Title Focused)
# ==========================================
# สำหรับรายงานส่วนใหญ่ เราจะนับ 1 เรื่องต่อ 1 ผลงาน (แม้จะมีผู้เขียนหลายคน)
df_unique_research = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']) if not df_research.empty else pd.DataFrame()

# ==========================================
# 5. Page: Overall Dashboard (ใหม่ตามข้อ 3)
# ==========================================
if menu == "📊 Overall Dashboard":
    st.header("🏛 Institutional Overview")
    if not df_unique_research.empty:
        # สรุปภาพรวมรายปี
        yearly_summary = df_unique_research.groupby("ปี").agg(
            Titles=("ชื่อเรื่อง", "nunique"),
            Total_Weight=("คะแนน", "sum")
        ).reset_index()

        c1, c2 = st.columns(2)
        with c1:
            fig_count = px.line(yearly_summary, x="ปี", y="Titles", title="Annual Research Volume", markers=True)
            st.plotly_chart(fig_count, use_container_width=True)
        with c2:
            fig_weight = px.bar(yearly_summary, x="ปี", y="Total_Weight", title="Annual Weighted Score Sum", color_discrete_sequence=['#FFB300'])
            st.plotly_chart(fig_weight, use_container_width=True)
        
        st.dataframe(yearly_summary.sort_values("ปี", ascending=False), use_container_width=True)

# ==========================================
# 6. Page: Program & Faculty Reports (ปรับตามข้อ 1 & 2)
# ==========================================
elif menu == "🎓 Program & Faculty Reports":
    st.header(f"📈 Detailed Performance ({year_option})")
    
    # Filter data by year
    df_f_unique = df_unique_research.copy()
    df_f_all = df_research.copy()
    if year_option != "All Years":
        df_f_unique = df_f_unique[df_f_unique["ปี"] == int(year_option)]
        df_f_all = df_f_all[df_f_all["ปี"] == int(year_option)]

    t1, t2 = st.tabs(["🎓 Program-wise Analysis (21 Programs)", "🏛 Faculty Performance"])

    with t1:
        # เตรียมข้อมูล 21 หลักสูตร
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[all_progs["หลักสูตร"].str.len() > 1] # ตัดค่าว่าง
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        # นับคะแนนและจำนวนเรื่อง (Unique Title per Program)
        # เชื่อมข้อมูลวิจัยกับหลักสูตรผ่านชื่อผู้เขียน
        merged_data = df_f_all.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        # จัดการนับ Unique: 1 เรื่อง 1 หลักสูตร (แม้จะมีอาจารย์ในหลักสูตรเดียวกันหลายคน)
        prog_stats = merged_data.groupby("หลักสูตร").agg(
            Count=("ชื่อเรื่อง", "nunique"),
            Weight_Sum=("คะแนน", "sum") # คะแนนถ่วงน้ำหนักสะสม
        ).reset_index()

        report_21 = all_progs.merge(prog_stats, on="หลักสูตร", how="left").fillna(0)

        # คำนวณ KPI
        def calc_kpi(row):
            n = faculty_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Weight_Sum"] / n) * 100) / x) * 5, 5.0), 2)

        report_21["KPI_Score"] = report_21.apply(calc_kpi, axis=1)

        # 1. กราฟ KPI
        fig_kpi = px.bar(report_21, x="หลักสูตร", y="KPI_Score", title="KPI Score by Program", color="คณะ")
        fig_kpi.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Target 5.0")
        st.plotly_chart(fig_kpi, use_container_width=True)

        # 2. กราฟจำนวนเรื่อง และ ค่าถ่วงน้ำหนัก
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(report_21, x="หลักสูตร", y="Count", title="Publication Count by Program"), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(report_21, x="หลักสูตร", y="Weight_Sum", title="Weighted Score Sum by Program"), use_container_width=True)

        # 3. ตารางสรุป
        st.markdown("#### 📋 Summary Table (21 Programs)")
        st.dataframe(report_21[["หลักสูตร", "Count", "Weight_Sum", "KPI_Score"]].rename(
            columns={"Count": "จำนวนเรื่อง", "Weight_Sum": "ค่าถ่วงน้ำหนักสะสม", "KPI_Score": "คะแนน KPI"}
        ), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("### 🏛 Faculty Comparison")
        merged_fac = df_f_all.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        fac_summary = merged_fac.groupby(["ปี", "คณะ"]).agg(
            Titles=("ชื่อเรื่อง", "nunique"),
            Weight=("คะแนน", "sum")
        ).reset_index()

        st.plotly_chart(px.bar(fac_summary, x="ปี", y="Weight", color="คณะ", barmode="group", title="Faculty Weighted Score Comparison"), use_container_width=True)
        
        st.markdown("#### 📋 Faculty Data Table")
        st.table(fac_summary.rename(columns={
            "ปี": "ปีการศึกษา", "คณะ": "ชื่อคณะ", "Titles": "จำนวนงานวิจัย", "Weight": "ค่าถ่วงน้ำหนักสะสม"
        }))

# ==========================================
# 7. Page: Data Entry (เพิ่มการเช็คชื่อซ้ำตามข้อ 4)
# ==========================================
elif menu == "✍️ Data Entry":
    st.header("✍️ Submit New Research")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Research Title (ชื่อเรื่อง)")
        y_in = st.number_input("Academic Year (พ.ศ.)", 2560, 2600, 2568)
        j_in = st.selectbox("Database", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("Submit"):
            if t_in and a_in:
                # *** ข้อ 4: Check Duplicates ***
                if not df_research.empty and t_in.strip().lower() in df_research["ชื่อเรื่อง"].str.strip().str.lower().values:
                    st.warning(f"⚠️ Warning: The title '{t_in}' is already in the system. Please check for duplicates.")
                else:
                    for author in a_in:
                        save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                    st.success("✅ Recorded successfully!")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.error("Please provide both Title and Authors.")

# (หน้า Manage Data เหมือนเดิม)
