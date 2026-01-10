import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ==========================================
# 1. การเชื่อมต่อ Google Sheets
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
        st.error(f"❌ ระบบไม่สามารถเชื่อมต่อ Google Cloud ได้: {e}")
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
            st.error(f"❌ โหลดข้อมูลจาก Sheet '{sheet_name}' ไม่สำเร็จ: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. การตั้งค่าหน้าเว็บและดีไซน์ (Header & Branding)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# ส่วนหัวเว็บไซต์ (Header) ปรับปรุงใหม่ให้รูปขึ้นแน่นอน
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try:
        # สั่งให้อ่านไฟล์ชื่อ logo.png ที่อยู่ในโฟลเดอร์เดียวกับ app.py
        st.image("logo.png", width=120)
    except:
        # กรณีที่ยังไม่ได้อัปโหลดไฟล์ หรือชื่อไฟล์ไม่ตรง จะแสดงข้อความแทนเพื่อไม่ให้หน้าเว็บพัง
        st.markdown("### 🏫 STIU")

with header_col2:
    st.markdown("""
        <div style="padding-top: 5px;">
            <h1 style="color: #1E3A8A; margin-bottom: 0px; font-family: 'Sarabun', sans-serif;">St Teresa International University</h1>
            <p style="color: #4B5563; font-size: 1.2rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# โหลดข้อมูล
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ ไม่พบข้อมูลใน Google Sheets หรือการเชื่อมต่อมีปัญหา กรุณาตรวจสอบสิทธิ์การแชร์ไฟล์")
    st.stop()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar
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
    
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # แสดง Metrics สีสันสวยงาม
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"📚 **Total Titles**\n\n### {len(df_filtered.drop_duplicates(subset=['ชื่อเรื่อง']))}")
    with c2:
        st.success(f"👥 **Researchers**\n\n### {df_filtered['ผู้เขียน'].nunique()}")
    with c3:
        st.warning(f"🏆 **Total Score**\n\n### {df_filtered['คะแนน'].sum():.2f}")

    t1, t2, t3, t4 = st.tabs(["🎓 Program KPI", "👤 Researcher", "🏛 Faculty", "📋 Master Data"])

    with t1:
        st.markdown("### 🏆 ความก้าวหน้า KPI รายหลักสูตร")
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
            score = round(min((((row["คะแนน"] / n) * 100) / x) * 5, 5.0), 2)
            return score

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        prog_report = prog_report.sort_values(by=["คณะ", "KPI Score"])

        fig = px.bar(prog_report, x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', 
                     range_x=[0, 5.5], text="KPI Score", height=700,
                     color_discrete_sequence=px.colors.qualitative.Bold)
        fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="Target 5.0")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("### 👤 ผลงานแยกตามรายบุคคล")
        if not df_filtered.empty:
            p_report = df_filtered.groupby("ผู้เขียน").agg(จำนวนเรื่อง=("ชื่อเรื่อง", "count"), คะแนนสะสม=("คะแนน", "sum")).reset_index()
            st.dataframe(p_report.sort_values("คะแนนสะสม", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("ไม่มีข้อมูล")

    with t3:
        st.markdown("### 🏛 ผลงานแยกตามรายคณะ")
        res_with_prog = df_research.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        if not res_with_prog.empty:
            fac_sum = res_with_prog.groupby(["ปี", "คณะ"])["คะแนน"].sum().reset_index()
            st.plotly_chart(px.bar(fac_sum, x="ปี", y="คะแนน", color="คณะ", barmode="group"), use_container_width=True)

    with t4:
        st.subheader("📋 ข้อมูลดิบ (Master Data)")
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. หน้า Admin
# ==========================================
elif menu == "✍️ Submit Research":
    st.subheader("✍️ บันทึกผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        t_in = st.text_input("ชื่อเรื่องงานวิจัย")
        y_in = st.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        j_in = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        a_in = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("บันทึกข้อมูล"):
            if t_in and a_in:
                for author in a_in:
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ Manage Database":
    st.subheader("⚙️ ลบข้อมูลออกจากฐานข้อมูล")
    if not df_research.empty:
        to_del = st.selectbox("เลือกเรื่องที่จะลบ", df_research["ชื่อเรื่อง"].unique())
        if st.button("🗑 ยืนยันการลบ"):
            client = conn_sheets()
            sh = client.open("Research_Database")
            ws = sh.worksheet("research")
            cell = ws.find(to_del)
            ws.delete_rows(cell.row)
            st.success("ลบสำเร็จ")
            st.cache_data.clear()
            st.rerun()

