import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Research Management System", layout="wide")

st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .main { background-color: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

MASTER_FILE = "masters.csv"
RESEARCH_FILE = "research.csv"

# เกณฑ์คะแนน (ปรับแต่งได้ที่นี่)
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# ==========================================
# 2. DATA ENGINE (Load/Save)
# ==========================================
@st.cache_data(ttl=60)
def load_master_data():
    if not os.path.exists(MASTER_FILE):
        # สร้าง Mockup Data หากไม่พบไฟล์ (เพื่อป้องกันโปรแกรมพัง)
        df = pd.DataFrame(columns=["Name-surname", "หลักสูตร", "คณะ"])
        st.error(f"⚠️ ไม่พบไฟล์ {MASTER_FILE} กรุณาตรวจสอบ")
        return df
    return pd.read_csv(MASTER_FILE, encoding="utf-8-sig")

def load_research_data():
    if os.path.exists(RESEARCH_FILE):
        return pd.read_csv(RESEARCH_FILE, encoding="utf-8-sig")
    return pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

df_master = load_master_data()
df_research = load_research_data()

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942780.png", width=100)
    st.title("ระบบบริหารงานวิจัย")
    menu = st.radio("เมนูหลัก", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI", "⚙️ จัดการข้อมูล"])
    
    st.divider()
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else [2568]
    year_filter = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูล
df_filtered = df_research.copy()
if year_filter != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_filter)]

# ==========================================
# 4. MAIN LOGIC: บันทึกผลงาน
# ==========================================
if menu == "✍️ บันทึกผลงาน":
    st.header("✍️ บันทึกผลงานวิจัยใหม่")
    
    with st.container(border=True):
        with st.form("research_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1: title = st.text_input("ชื่อเรื่องงานวิจัย (Title)")
            with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
            
            col3, col4 = st.columns(2)
            with col3: journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
            with col4: authors = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].unique())

            if st.form_submit_button("💾 บันทึกข้อมูลลงระบบ"):
                if title and authors:
                    new_entries = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                                   "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                    df_updated = pd.concat([df_research, pd.DataFrame(new_entries)], ignore_index=True)
                    df_updated.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
                    st.success("✅ บันทึกข้อมูลสำเร็จ!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

# ==========================================
# 5. MAIN LOGIC: รายงานและ KPI
# ==========================================
elif menu == "📊 รายงานและ KPI":
    st.header(f"📊 สรุปผลการดำเนินงาน ปี {year_filter}")

    # Logic การคำนวณ KPI
    all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
    fac_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    def calc_kpi_score(row):
        prog = row["หลักสูตร"]
        score = row["คะแนนสะสม"]
        n_fac = fac_counts.get(prog, 1)
        
        # กำหนดค่า X
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in group_40 else 20)
        
        kpi = (((score / n_fac) * 100) / x_val) * 5
        return min(round(kpi, 2), 5.0) # Max 5.0

    # ประมวลผลคะแนนรายหลักสูตร
    res_agg = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_sum = res_agg.groupby("หลักสูตร")["คะแนน"].sum().reset_index().rename(columns={"คะแนน": "คะแนนสะสม"})
    
    prog_report = all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)
    prog_report["KPI Score"] = prog_report.apply(calc_kpi_score, axis=1)

    # แสดง Dashboard
    t1, t2 = st.tabs(["🎓 KPI รายหลักสูตร", "🏛 สรุปรายคณะ"])
    
    with t1:
        fig = px.bar(prog_report, x="KPI Score", y="หลักสูตร", color="คณะ", 
                     orientation='h', range_x=[0, 5], text="KPI Score",
                     title="คะแนน KPI รายหลักสูตร (เป้าหมาย 5.0)")
        fig.add_vline(x=5, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True)

    with t2:
        # สรุปรายคณะแบบไม่นับซ้ำ
        fac_sum = res_agg.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby("คณะ")["คะแนน"].sum().reset_index()
        st.plotly_chart(px.pie(fac_sum, values='คะแนน', names='คณะ', title="สัดส่วนคะแนนสะสมรายคณะ"), use_container_width=True)

# ==========================================
# 6. MAIN LOGIC: จัดการข้อมูล (Delete/Edit)
# ==========================================
else:
    st.header("⚙️ จัดการข้อมูลงานวิจัย")
    if not df_research.empty:
        st.write("ตารางข้อมูลทั้งหมด (สามารถลบรายการได้)")
        df_display = df_research.copy()
        selected_row = st.selectbox("เลือกรายการที่ต้องการลบ (ตามชื่อเรื่อง)", df_display["ชื่อเรื่อง"].unique())
        
        if st.button("🗑 ลบรายการที่เลือก"):
            df_new = df_research[df_research["ชื่อเรื่อง"] != selected_row]
            df_new.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
            st.success("ลบข้อมูลสำเร็จ!")
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        st.dataframe(df_research, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลให้แสดง")
