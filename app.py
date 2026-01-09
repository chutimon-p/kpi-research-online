import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ==========================================
# 1. การตั้งค่าหน้าเว็บและสไตล์ (Font Sarabun)
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
        .stDataFrame { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

MASTER_FILE = "masters.csv"
RESEARCH_FILE = "research.csv"

# เกณฑ์คะแนน KPI
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# ==========================================
# 2. ฟังก์ชันโหลดข้อมูล (พร้อมระบบแก้ Encoding)
# ==========================================
@st.cache_data(ttl=60)
def load_data(file_path, default_cols):
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=default_cols)
    
    # ลองเปิดด้วยหลาย Encoding เพื่อแก้ปัญหา UnicodeDecodeError
    for enc in ["utf-8-sig", "cp874", "tis-620", "utf-8"]:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            df.columns = df.columns.str.strip() # ลบเว้นวรรคส่วนเกินที่หัวตาราง
            return df
        except (UnicodeDecodeError, Exception):
            continue
    
    st.error(f"❌ ไม่สามารถอ่านไฟล์ {file_path} ได้ กรุณาตรวจสอบการบันทึกไฟล์ CSV")
    return pd.DataFrame(columns=default_cols)

# โหลดข้อมูล
df_master = load_data(MASTER_FILE, ["Name-surname", "หลักสูตร", "คณะ"])
df_research = load_data(RESEARCH_FILE, ["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

# ตรวจสอบว่ามีข้อมูล Master หรือไม่
if df_master.empty and not os.path.exists(MASTER_FILE):
    st.warning(f"⚠️ ไม่พบไฟล์ {MASTER_FILE} ในระบบ กรุณาอัปโหลดไฟล์ขึ้น GitHub")

# ==========================================
# 3. ส่วนเมนู (Sidebar)
# ==========================================
with st.sidebar:
    st.title("📌 เมนูหลัก")
    menu = st.radio("เลือกหน้าจอ", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI", "⚙️ จัดการข้อมูล"])
    
    st.divider()
    # ตัวกรองปี
    if not df_research.empty:
        all_years = sorted(df_research["ปี"].unique().tolist())
        year_option = st.selectbox("🔍 กรองตามปี พ.ศ.", ["แสดงทั้งหมด"] + [str(y) for y in all_years])
    else:
        year_option = "แสดงทั้งหมด"

# กรองข้อมูลตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# ==========================================
# 4. หน้าจอ: บันทึกผลงาน
# ==========================================
if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        col3, col4 = st.columns(2)
        with col3: journal = st.selectbox("ฐานวารสาร (Journal Database)", list(SCORE_MAP.keys()))
        with col4: 
            # ดึงรายชื่อจาก Master
            author_list = df_master["Name-surname"].dropna().unique().tolist()
            authors = st.multiselect("เลือกผู้เขียน (จากฐานข้อมูลอาจารย์)", author_list)

        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                             "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                df_updated.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("⚠️ กรุณากรอกชื่อเรื่องและเลือกผู้เขียน")

# ==========================================
# 5. หน้าจอ: รายงานและ KPI
# ==========================================
elif menu == "📊 รายงานและ KPI":
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")
    
    if df_master.empty:
        st.error("ไม่พบข้อมูลอาจารย์ในระบบ (Master Data)")
    else:
        # เตรียมโครงสร้างหลักสูตร 21 หลักสูตร
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[all_progs["หลักสูตร"] != "-"]
        
        # คำนวณจำนวนอาจารย์รายหลักสูตร
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        # เชื่อมข้อมูลวิจัยกับหลักสูตร
        res_with_prog = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                         left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        res_sum = res_with_prog.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_report = all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)

        # ฟังก์ชันคำนวณ KPI
        def calculate_kpi(row):
            prog = row["หลักสูตร"]
            score = row["คะแนน"]
            n_fac = faculty_counts.get(prog, 1)
            # กำหนดค่า X ตามกลุ่มหลักสูตร
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in group_40 else 20)
            
            kpi = (((score / n_fac) * 100) / x_val) * 5
            return round(min(kpi, 5.0), 2) # สูงสุดไม่เกิน 5.0

        prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calculate_kpi, axis=1)

        # แสดงผล Tabs
        t1, t2, t3 = st.tabs(["🎓 รายหลักสูตร", "👤 รายบุคคล", "🏛 รายคณะ"])
        
        with t1:
            fig = px.bar(prog_report.sort_values("คะแนนปัจจุบัน"), x="คะแนนปัจจุบัน", y="หลักสูตร", 
                         color="คณะ", orientation='h', range_x=[0, 5.5], text="คะแนนปัจจุบัน",
                         title="ความก้าวหน้า KPI (เป้าหมาย 5.0)")
            fig.add_vline(x=5, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(prog_report, use_container_width=True)

        with t2:
            if not df_filtered.empty:
                p_report = df_filtered.groupby("ผู้เขียน").agg({"ชื่อเรื่อง": "count", "คะแนน": "sum"}).reset_index()
                st.dataframe(p_report.sort_values("คะแนน", ascending=False), use_container_width=True)
            else:
                st.info("ไม่มีข้อมูล")

        with t3:
            # รายคณะแบบไม่นับงานซ้ำ
            fac_data = res_with_prog.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"])
            fac_sum = fac_data.groupby("คณะ")["คะแนน"].sum().reset_index()
            st.plotly_chart(px.pie(fac_sum, values='คะแนน', names='คณะ', title="สัดส่วนผลงานแยกตามคณะ"), use_container_width=True)

# ==========================================
# 6. หน้าจอ: จัดการข้อมูล
# ==========================================
else:
    st.title("⚙️ จัดการข้อมูล")
    
    st.subheader("🗑 ลบข้อมูลงานวิจัย")
    if not df_research.empty:
        to_delete = st.selectbox("เลือกงานวิจัยที่ต้องการลบ", df_research["ชื่อเรื่อง"].unique())
        if st.button("ยืนยันการลบข้อมูล"):
            df_new = df_research[df_research["ชื่อเรื่อง"] != to_delete]
            df_new.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
            st.success(f"ลบเรื่อง '{to_delete}' เรียบร้อยแล้ว")
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลงานวิจัยในระบบ")
    
    st.divider()
    st.subheader("📥 ดาวน์โหลดข้อมูล (Backup)")
    if not df_research.empty:
        csv = df_research.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("Download Research CSV", csv, "research_backup.csv", "text/csv")
