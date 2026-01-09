import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ==========================================
# 1. การตั้งค่าหน้าเว็บและสไตล์
# ==========================================
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# กำหนดรหัสผ่าน Admin
ADMIN_PASSWORD = "admin1234"
MASTER_FILE = "masters.csv"
RESEARCH_FILE = "research.csv"

# เกณฑ์คะแนน KPI
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# ==========================================
# 2. ฟังก์ชันจัดการระบบ Login & Data
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

@st.cache_data(ttl=60)
def load_data(file_path, default_cols):
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=default_cols)
    for enc in ["utf-8-sig", "cp874", "tis-620", "utf-8"]:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            df.columns = df.columns.str.strip() 
            return df
        except:
            continue
    return pd.DataFrame(columns=default_cols)

df_master = load_data(MASTER_FILE, ["Name-surname", "หลักสูตร", "คณะ"])
df_research = load_data(RESEARCH_FILE, ["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

# ==========================================
# 3. Sidebar และการเข้าสู่ระบบ
# ==========================================
with st.sidebar:
    st.title("📌 ระบบวิจัย")
    menu_options = ["📊 รายงานและ KPI"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ บันทึกผลงาน")
        menu_options.append("⚙️ จัดการข้อมูล")
    
    menu = st.radio("เลือกหน้าจอ", menu_options)
    
    # Login Section
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านผิด")
    else:
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    if not df_research.empty:
        all_years = sorted(df_research["ปี"].unique().tolist())
        year_option = st.selectbox("🔍 ปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])
    else: year_option = "ทั้งหมด"

df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# ==========================================
# 4. หน้าจอ: รายงานและ KPI
# ==========================================
if menu == "📊 รายงานและ KPI":
    st.title(f"📊 ผลการดำเนินงาน ({year_option})")
    
    if df_master.empty:
        st.error("ไม่พบข้อมูลอาจารย์ในระบบ")
    else:
        # เตรียมข้อมูลสำหรับประมวลผล
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        res_with_prog = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร', 'คณะ']], 
                                         left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        t1, t2, t3 = st.tabs(["🎓 รายหลักสูตร", "👤 รายบุคคล (เจาะลึก)", "🏛 รายคณะ"])
        
        with t1:
            res_sum = res_with_prog.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
            prog_report = all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)
            
            def calculate_kpi(row):
                prog = row["หลักสูตร"]
                score = row["คะแนน"]
                n_fac = faculty_counts.get(prog, 1)
                group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in group_40 else 20)
                return round(min((((score / n_fac) * 100) / x_val) * 5, 5.0), 2)

            prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calculate_kpi, axis=1)
            fig = px.bar(prog_report.sort_values("คะแนนปัจจุบัน"), x="คะแนนปัจจุบัน", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="คะแนนปัจจุบัน")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(prog_report, use_container_width=True)

        with t2:
            st.subheader("📋 สรุปผลงานรายบุคคล")
            if not df_filtered.empty:
                # 1. สร้างตารางสรุป
                p_report = df_filtered.groupby("ผู้เขียน").agg(
                    จำนวนเรื่อง=("ชื่อเรื่อง", "count"),
                    คะแนนสะสม=("คะแนน", "sum")
                ).reset_index().sort_values("คะแนนสะสม", ascending=False)
                
                st.write("💡 *คลิกเลือกชื่ออาจารย์ด้านล่างเพื่อดูรายละเอียดชื่อเรื่อง*")
                # 2. แสดงตารางสรุปหลัก
                st.dataframe(p_report, use_container_width=True, hide_index=True)
                
                # 3. ส่วน Drill-down (รายละเอียดรายบุคคล)
                st.divider()
                selected_author = st.selectbox("เลือกชื่ออาจารย์เพื่อดูชื่อเรื่องและวารสาร:", ["-- เลือกรายชื่อ --"] + p_report["ผู้เขียน"].tolist())
                
                if selected_author != "-- เลือกรายชื่อ --":
                    st.success(f"📌 ผลงานของ: {selected_author}")
                    detail_df = df_filtered[df_filtered["ผู้เขียน"] == selected_author][["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน"]]
                    st.table(detail_df) # ใช้ st.table เพื่อความสวยงามในหน้ารายละเอียด
            else:
                st.info("ยังไม่มีข้อมูลผลงานในปีนี้")

        with t3:
            if "คณะ" in res_with_prog.columns:
                fac_sum = res_with_prog.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby("คณะ")["คะแนน"].sum().reset_index()
                st.plotly_chart(px.pie(fac_sum, values='คะแนน', names='คณะ'), use_container_width=True)

# ==========================================
# 5. หน้าจอ Protected (ต้อง Login)
# ==========================================
elif menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์", 2560, 2600, 2568)
        col3, col4 = st.columns(2)
        with col3: journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        with col4: authors = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("💾 บันทึก"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                df_updated.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
                st.success("บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ จัดการข้อมูล":
    st.title("⚙️ จัดการข้อมูล")
    to_delete = st.selectbox("เลือกเรื่องที่จะลบ", df_research["ชื่อเรื่อง"].unique())
    if st.button("🗑 ยืนยันการลบ"):
        df_new = df_research[df_research["ชื่อเรื่อง"] != to_delete]
        df_new.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
        st.success("ลบสำเร็จ")
        st.cache_data.clear()
        st.rerun()
