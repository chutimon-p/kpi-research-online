import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. การเชื่อมต่อฐานข้อมูล (Google Sheets)
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
        st.error(f"❌ การเชื่อมต่อล้มเหลว: {e}")
        return None

@st.cache_data(ttl=300) # รีเฟรชข้อมูลทุก 5 นาที
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
            st.error(f"❌ ไม่สามารถโหลดข้อมูล '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. การตั้งค่าหน้าจอและ UI
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #1E3A8A;
    }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try: st.image("logo.jpg", width=140)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="color: #1E3A8A; margin-bottom: 0px;">St Teresa International University</h1>
            <p style="color: #64748b; font-size: 1.1rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# โหลดข้อมูล
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังโหลดข้อมูล... โปรดรอสักครู่")
    st.stop()

# ทำความสะอาดข้อมูล
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. ส่วนควบคุมเมนู (Sidebar)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 เมนูหลัก")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("ไปยังหน้า:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 ตัวกรองปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้า Dashboard
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # ดึงข้อมูลชื่อ-คณะ-หลักสูตรมาเชื่อมกับงานวิจัย
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )
    
    # ตัวหาร n (จำนวนอาจารย์)
    df_master_clean = df_master[(df_master['หลักสูตร'].notna()) & (df_master['หลักสูตร'] != "-")].copy()
    prog_member_counts = df_master_clean.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    fac_member_counts = df_master_clean.groupby("คณะ")["Name-surname"].nunique().to_dict()

    m1, m2, m3 = st.columns(3)
    unique_titles = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    m1.metric("จำนวนผลงานทั้งหมด", f"{len(unique_titles)} เรื่อง")
    m2.metric("จำนวนนักวิจัยที่มีผลงาน", f"{df_filtered['ผู้เขียน'].nunique()} คน")
    m3.metric("คะแนนถ่วงน้ำหนักรวม", f"{unique_titles['คะแนน'].sum():.2f}")

    t1, t2, t3, t4 = st.tabs(["🎓 KPI รายหลักสูตร", "🏢 KPI รายคณะ", "👤 ข้อมูลนักวิจัย", "📋 ฐานข้อมูลอาจารย์"])

    with t1:
        st.markdown("#### 🏆 คะแนน KPI รายหลักสูตร (เทียบไฟล์ Excel)")
        prog_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_unique.groupby("หลักสูตร").agg(Sum_Weight=("คะแนน", "sum"), Count=("ชื่อเรื่อง", "count")).reset_index()
        
        # ผูกข้อมูลหลักสูตรที่มีทั้งหมด
        prog_report = df_master_clean[['หลักสูตร', 'คณะ']].drop_duplicates().merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 0)
            if n == 0: return 0.0
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Sum_Weight"] / n) * 100) / x) * 5
            return round(score, 2)

        prog_report["n"] = prog_report["หลักสูตร"].map(prog_member_counts)
        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        
        st.plotly_chart(px.bar(prog_report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', text="KPI Score", template="plotly_white"), use_container_width=True)
        st.write("**ตารางตรวจสอบ (Audit Table)**")
        st.dataframe(prog_report[['หลักสูตร', 'n', 'Count', 'Sum_Weight', 'KPI Score']], use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 🏢 คะแนน KPI รายคณะ")
        fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_unique.groupby("คณะ").agg(Sum_Weight=("คะแนน", "sum"), Count=("ชื่อเรื่อง", "count")).reset_index()
        
        def calc_fac_kpi(row):
            n = fac_member_counts.get(row["คณะ"], 0)
            if n == 0: return 0.0
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            score = (((row["Sum_Weight"] / n) * 100) / y) * 5
            return round(score, 2)

        fac_sum["n"] = fac_sum["คณะ"].map(fac_member_counts)
        fac_sum["KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_sum.sort_values("KPI Score"), x="KPI Score", y="คณะ", orientation='h', text="KPI Score", template="plotly_white"), use_container_width=True)
        st.dataframe(fac_sum, use_container_width=True, hide_index=True)

    with t3:
        author = st.selectbox("เลือกนักวิจัย:", ["-- เลือก --"] + sorted(df_master["Name-surname"].unique()))
        if author != "-- เลือก --":
            works = df_filtered[df_filtered["ผู้เขียน"] == author]
            st.metric("คะแนนสะสมบุคคล", f"{works['คะแนน'].sum():.2f}")
            st.dataframe(works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True)

    with t4:
        st.dataframe(df_master, use_container_width=True)

# ==========================================
# 5. หน้าจัดการข้อมูล (Manage Database)
# ==========================================
elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    
    # 1. ลบรายเรื่อง
    st.markdown("#### 🗑 ลบเฉพาะบางรายการ")
    if not df_research.empty:
        df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
        opts = ["-- เลือกเรื่องที่ต้องการลบ --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
        sel = st.selectbox("เลือกผลงาน:", opts)
        if sel != "-- เลือกเรื่องที่ต้องการลบ --":
            target = sel.split(" | ")[1].strip()
            if st.button("ยืนยันลบรายการนี้"):
                ws = conn_sheets().open("Research_Database").worksheet("research")
                rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
                for r in sorted(rows, reverse=True): ws.delete_rows(r)
                st.success("ลบสำเร็จ!"); st.cache_data.clear(); st.rerun()

    st.divider()

    # 2. ลบทั้งหมดตามปี
    st.markdown("#### ⚠️ ลบข้อมูลทั้งหมด")
    if year_option == "ทั้งหมด":
        st.info("กรุณาเลือก 'ปี พ.ศ.' ที่ต้องการลบในแถบเมนูด้านซ้ายก่อน")
    else:
        st.error(f"คำเตือน: คุณกำลังจะลบข้อมูลงานวิจัย 'ทั้งหมด' ของปี {year_option}")
        confirm = st.text_input(f"พิมพ์คำว่า 'DELETE {year_option}' เพื่อยืนยัน")
        if st.button(f"ยืนยันการล้างข้อมูลปี {year_option}"):
            if confirm == f"DELETE {year_option}":
                ws = conn_sheets().open("Research_Database").worksheet("research")
                all_rec = ws.get_all_records()
                rows = [i + 2 for i, row in enumerate(all_rec) if str(row.get('ปี')) == year_option]
                if rows:
                    for r in sorted(rows, reverse=True): ws.delete_rows(r)
                    st.success(f"ล้างข้อมูลปี {year_option} เรียบร้อยแล้ว!"); st.cache_data.clear(); st.rerun()
                else: st.info("ไม่พบข้อมูลในปีนี้")
            else: st.warning("คำยืนยันไม่ถูกต้อง")

# ==========================================
# 6. หน้าส่งข้อมูล (Submit Research)
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ ลงทะเบียนผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่อง")
        c1, c2 = st.columns(2)
        year = c1.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        db = c2.selectbox("ฐานข้อมูล", list(SCORE_MAP.keys()))
        authors = st.multiselect("รายชื่อผู้เขียน", df_master["Name-surname"].unique())
        if st.form_submit_button("บันทึกข้อมูล"):
            if title and authors:
                for a in authors:
                    save_to_sheet("research", {"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": a})
                st.success("บันทึกสำเร็จ!"); st.cache_data.clear(); st.rerun()
