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

ADMIN_PASSWORD = "admin1234"
MASTER_FILE = "masters.csv"
RESEARCH_FILE = "research.csv"

SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# ==========================================
# 2. ฟังก์ชันโหลดข้อมูล (Smart Encoding)
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
# 3. Sidebar และระบบ Login
# ==========================================
with st.sidebar:
    st.title("📌 ระบบวิจัย")
    menu_options = ["📊 รายงานและ KPI"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ บันทึกผลงาน")
        menu_options.append("⚙️ จัดการข้อมูล")
    
    menu = st.radio("เลือกหน้าจอ", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("🔐 รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        st.success("🔓 สถานะ: เจ้าหน้าที่")
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    if not df_research.empty:
        all_years = sorted(df_research["ปี"].unique().tolist())
        year_option = st.selectbox("🔍 เลือกปี พ.ศ. (สำหรับรายงาน)", ["ทั้งหมด"] + [str(y) for y in all_years])
    else: year_option = "ทั้งหมด"

df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# ==========================================
# 4. หน้าจอ: รายงานและ KPI (Public Access)
# ==========================================
if menu == "📊 รายงานและ KPI":
    st.title(f"📊 สรุปผลการดำเนินงาน")
    
    if df_master.empty:
        st.error("ไม่พบข้อมูลพื้นฐานในไฟล์ masters.csv")
    else:
        # เตรียมรายชื่อหลักสูตรทั้งหมด (ยกเว้น "-")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
        
        # นับจำนวนอาจารย์ต่อหลักสูตร
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        # เชื่อมข้อมูลวิจัยกับข้อมูลอาจารย์
        res_full_filtered = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร', 'คณะ']], 
                                             left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        t1, t2, t3 = st.tabs(["🎓 รายหลักสูตร (KPI)", "👤 รายบุคคล (เจาะลึก)", "🏛 รายคณะ (เปรียบเทียบปี)"])
        
        with t1:
            st.subheader(f"🎓 ความก้าวหน้า KPI รายหลักสูตร ({year_option})")
            
            # รวมข้อมูลวิจัยเข้ากับหลักสูตรทั้งหมด (Left Join เพื่อให้แสดงแม้ไม่มีข้อมูล)
            prog_sum = res_full_filtered.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
            prog_report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

            def calculate_kpi(row):
                prog = row["หลักสูตร"]
                score = row["คะแนน"]
                n_fac = faculty_counts.get(prog, 1)
                group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in group_40 else 20)
                return round(min((((score / n_fac) * 100) / x_val) * 5, 5.0), 2)

            prog_report["คะแนน KPI"] = prog_report.apply(calculate_kpi, axis=1)
            prog_report = prog_report.sort_values("คะแนน KPI", ascending=True)

            # กราฟแท่งแสดงผล 21 หลักสูตร
            fig_prog = px.bar(prog_report, x="คะแนน KPI", y="หลักสูตร", color="คณะ", 
                             orientation='h', range_x=[0, 5.5], text="คะแนน KPI", height=700)
            
            # เพิ่มเส้นไฮไลท์เกณฑ์ผ่าน 5.0
            fig_prog.add_vline(x=5.0, line_dash="dash", line_color="red", 
                              annotation_text=" เกณฑ์ผ่าน (5.0) ", annotation_position="top right")
            
            st.plotly_chart(fig_prog, use_container_width=True)
            st.dataframe(prog_report, use_container_width=True, hide_index=True)

        with t2:
            st.subheader(f"📋 สรุปผลงานรายบุคคล ({year_option})")
            if not df_filtered.empty:
                p_report = df_filtered.groupby("ผู้เขียน").agg(
                    จำนวนเรื่อง=("ชื่อเรื่อง", "count"),
                    คะแนนสะสม=("คะแนน", "sum")
                ).reset_index().sort_values("คะแนนสะสม", ascending=False)
                st.dataframe(p_report, use_container_width=True, hide_index=True)
                
                selected_author = st.selectbox("เลือกชื่ออาจารย์เพื่อดูรายละเอียดผลงาน:", ["-- เลือกรายชื่อ --"] + p_report["ผู้เขียน"].tolist())
                if selected_author != "-- เลือกรายชื่อ --":
                    st.success(f"📌 ผลงานของ: {selected_author}")
                    st.table(df_filtered[df_filtered["ผู้เขียน"] == selected_author][["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน"]])
            else: st.info("ยังไม่มีข้อมูลงานวิจัยในปีที่เลือก")

        with t3:
            st.subheader("🏛 คะแนนสะสมถ่วงน้ำหนักรายคณะ (เปรียบเทียบปี)")
            # ดึงข้อมูลทั้งหมดเพื่อดูแนวโน้มรายปี
            res_all_time = df_research.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
            if not res_all_time.empty:
                fac_year = res_all_time.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby(["ปี", "คณะ"])["คะแนน"].sum().reset_index()
                fac_year["ปี"] = fac_year["ปี"].astype(str)
                fig_fac = px.bar(fac_year, x="ปี", y="คะแนน", color="คณะ", barmode="group", 
                                labels={"คะแนน":"ค่าถ่วงน้ำหนักสะสม", "ปี":"ปี พ.ศ."}, text_auto='.2f')
                st.plotly_chart(fig_fac, use_container_width=True)
                st.write("💡 *กราฟรายคณะแสดงข้อมูลทุกปีที่มีในระบบเพื่อเปรียบเทียบความก้าวหน้า*")

# ==========================================
# 5. หน้าจอ Protected (ต้อง Login)
# ==========================================
elif menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        col3, col4 = st.columns(2)
        with col3: journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        with col4: authors = st.multiselect("เลือกผู้เขียน (ดึงข้อมูลจาก Master)", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and authors:
                new_data = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_data)], ignore_index=True)
                df_updated.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ จัดการข้อมูล":
    st.title("⚙️ จัดการข้อมูล")
    if not df_research.empty:
        to_del = st.selectbox("เลือกเรื่องที่ต้องการลบ", df_research["ชื่อเรื่อง"].unique())
        if st.button("🗑 ยืนยันการลบข้อมูล"):
            df_research = df_research[df_research["ชื่อเรื่อง"] != to_del]
            df_research.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
            st.success("ลบข้อมูลเรียบร้อยแล้ว")
            st.cache_data.clear()
            st.rerun()
