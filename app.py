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

@st.cache_data(ttl=600) # เพิ่ม Cache 10 นาทีเพื่อความลื่นไหล
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
# 2. Page Configuration
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# CSS Styling
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

# Header
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

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังเชื่อมต่อข้อมูลจาก Google Sheets... หากรอนานเกินไปโปรดรีเฟรชหน้าจอ")
    st.stop()

# Data Cleaning
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# คะแนนถ่วงน้ำหนักตามฐานข้อมูล
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar & Navigation
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 เมนูหลัก")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("เลือกหน้า:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่านผู้ดูแลระบบ", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 กรองตามปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 สรุปผลการดำเนินงาน ปี {year_option}")
    
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # รวมข้อมูลสังกัด
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )
    
    # คลีนข้อมูลหลักสูตรและคณะสำหรับตัวหาร n
    df_master_clean = df_master[(df_master['หลักสูตร'].notna()) & (df_master['หลักสูตร'] != "-") & (df_master['หลักสูตร'] != "")].copy()
    prog_member_counts = df_master_clean.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    df_faculty_clean = df_master[(df_master['คณะ'].notna()) & (df_master['คณะ'] != "-") & (df_master['คณะ'] != "")].copy()
    fac_member_counts = df_faculty_clean.groupby("คณะ")["Name-surname"].nunique().to_dict()

    # สรุปภาพรวมด้านบน
    unique_titles_summary = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    m1, m2, m3 = st.columns(3)
    m1.metric("จำนวนงานวิจัยรวม", f"{len(unique_titles_summary)} เรื่อง")
    m2.metric("จำนวนนักวิจัย", f"{df_filtered['ผู้เขียน'].nunique()} คน")
    m3.metric("คะแนนถ่วงน้ำหนักรวม", f"{unique_titles_summary['คะแนน'].sum():.2f}")

    t0, t1, t2, t3, t4 = st.tabs(["🏛 ภาพรวมมหาวิทยาลัย", "🎓 KPI รายหลักสูตร", "👤 ข้อมูลนักวิจัย", "🏢 KPI รายคณะ", "📋 ฐานข้อมูลอาจารย์"])

    with t0:
        st.markdown("#### 🌍 การเติบโตของงานวิจัยระดับสถาบัน")
        inst_summary = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(
            Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")
        ).reset_index().sort_values("ปี")
        inst_summary = inst_summary[inst_summary['ปี'] > 0]
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Titles"], name="จำนวนเรื่อง", marker_color='#1E3A8A'))
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="คะแนนถ่วงน้ำหนัก", yaxis="y2", line=dict(color='#ef4444', width=3)))
        fig_inst.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig_inst, use_container_width=True)

    with t1:
        st.markdown("#### 🏆 คะแนน KPI รายหลักสูตร")
        all_progs = df_master_clean[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        
        # 1 เรื่อง นับ 1 ครั้งต่อหลักสูตร (กรณีผู้เขียนอยู่หลักสูตรเดียวกัน)
        prog_unique_res = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_summary = prog_unique_res.groupby("หลักสูตร").agg(
            Sum_Weight=("คะแนน", "sum"), 
            Count_Titles=("ชื่อเรื่อง", "count")
        ).reset_index()
        
        prog_report = all_progs.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 0)
            if n == 0: return 0.0
            
            # กำหนดค่า x (ร้อยละ) ตามไฟล์ Excel
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            if row["หลักสูตร"] == "Ph.D-Admin": x = 60
            elif row["หลักสูตร"] in group_40: x = 40
            else: x = 20 # สำหรับกลุ่ม ป.ตรี ทั่วไป
            
            # สูตร: ((คะแนนรวม / n) * 100) / x * 5
            raw_score = (((row["Sum_Weight"] / n) * 100) / x) * 5
            return round(raw_score, 2)

        prog_report["n (อาจารย์)"] = prog_report["หลักสูตร"].map(prog_member_counts)
        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        # สร้างคอลัมน์ KPI ที่ตัดเกรดไม่เกิน 5 เพื่อใช้โชว์ในกราฟประกันคุณภาพ
        prog_report["KPI (Max 5)"] = prog_report["KPI Score"].apply(lambda x: min(x, 5.0))
        
        st.plotly_chart(px.bar(prog_report.sort_values("KPI (Max 5)"), x="KPI (Max 5)", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="KPI Score", height=600, template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="red"), use_container_width=True)
        
        st.write("🔍 **ตารางตรวจสอบรายละเอียดรายหลักสูตร (Audit Table)**")
        st.dataframe(prog_report[['หลักสูตร', 'n (อาจารย์)', 'Count_Titles', 'Sum_Weight', 'KPI Score']].sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 👤 ข้อมูลผลงานรายบุคคล")
        search_author = st.selectbox("🔍 เลือกรายชื่อนักวิจัย:", ["-- เลือก --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- เลือก --":
            author_works = df_filtered[df_filtered["ผู้เขียน"] == search_author].copy().sort_values("ปี", ascending=False)
            if not author_works.empty:
                c1, c2 = st.columns([1, 3])
                c1.metric("จำนวนงานวิจัย", len(author_works))
                c1.metric("คะแนนสะสม", f"{author_works['คะแนน'].sum():.2f}")
                c2.dataframe(author_works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)
            else:
                st.info("ไม่พบข้อมูลผลงานในปีที่เลือก")

    with t3:
        st.markdown("#### 🏢 คะแนน KPI รายคณะ")
        if not df_full_info.empty:
            res_fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
            fac_sum = res_fac_unique.groupby("คณะ").agg(
                Sum_Weight=("คะแนน", "sum"), 
                Count_Titles=("ชื่อเรื่อง", "count")
            ).reset_index()

            def calc_fac_kpi(row):
                f_name = row["คณะ"]
                n = fac_member_counts.get(f_name, 0)
                if n == 0: return 0.0
                y = 30 if f_name in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                raw_score = (((row["Sum_Weight"] / n) * 100) / y) * 5
                return round(raw_score, 2)

            fac_sum["n (อาจารย์)"] = fac_sum["คณะ"].map(fac_member_counts)
            fac_sum["Faculty KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
            fac_sum["KPI (Max 5)"] = fac_sum["Faculty KPI Score"].apply(lambda x: min(x, 5.0))
            
            st.plotly_chart(px.bar(fac_sum.sort_values("KPI (Max 5)"), x="KPI (Max 5)", y="คณะ", orientation='h', range_x=[0, 5.5], text="Faculty KPI Score", color="คณะ", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="red"), use_container_width=True)
            st.dataframe(fac_sum[['คณะ', 'n (อาจารย์)', 'Count_Titles', 'Sum_Weight', 'Faculty KPI Score']].sort_values("Faculty KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t4:
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin Sections
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ ลงทะเบียนผลงานวิจัย")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("ชื่อเรื่อง (Title)").strip()
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        with c2: j_in = st.selectbox("ฐานข้อมูลวารสาร", list(SCORE_MAP.keys()))
        a_in = st.multiselect("ผู้เขียน (เลือกได้มากกว่า 1 คน)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("บันทึกข้อมูล"):
            if t_in and a_in:
                # บันทึกแยกรายคนเพื่อให้คำนวณ KPI รายคน/หลักสูตรได้ถูกต้อง
                for a in a_in:
                    save_to_sheet("research", {
                        "ชื่อเรื่อง": t_in, 
                        "ปี": y_in, 
                        "ฐานวารสาร": j_in, 
                        "คะแนน": SCORE_MAP[j_in], 
                        "ผู้เขียน": a
                    })
                st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("กรุณากรอกชื่อเรื่องและเลือกผู้เขียน")

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล (ลบข้อมูล)")
    if not df_research.empty:
        df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']).sort_values(by=['ปี', 'ชื่อเรื่อง'], ascending=[False, True])
        
        opts = ["-- เลือกรายการที่ต้องการลบ --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']} | {r['ฐานวารสาร']}" for _, r in df_manage.iterrows()]
        sel = st.selectbox("เลือกรายการผลงาน:", opts)
        
        if sel != "-- เลือกรายการที่ต้องการลบ --":
            target_title = sel.split(" | ")[1].strip()
            st.warning(f"คุณกำลังจะลบข้อมูลเรื่อง: {target_title}")
            if st.button("ยืนยันการลบข้อมูล"):
                with st.spinner("กำลังดำเนินการ..."):
                    ws = conn_sheets().open("Research_Database").worksheet("research")
                    all_data = ws.get_all_records()
                    # ค้นหาทุกบรรทัดที่มีชื่อเรื่องนี้ (เพราะ 1 เรื่องอาจมีหลายผู้เขียน)
                    rows_to_delete = [i + 2 for i, row in enumerate(all_data) if str(row.get('ชื่อเรื่อง')).strip() == target_title]
                    
                    for r in sorted(rows_to_delete, reverse=True):
                        ws.delete_rows(r)
                        
                    st.success(f"ลบข้อมูลสำเร็จ (จำนวน {len(rows_to_delete)} แถว)")
                    st.cache_data.clear()
                    st.rerun()
