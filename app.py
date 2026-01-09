import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าเว็บและฟอนต์ ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# เกณฑ์คะแนน
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # พยายามดึงข้อมูลจาก Tab ชื่อ masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error("❌ หาแผ่นงาน (Tab) ไม่พบ")
        st.info("คำแนะนำ: รบกวนตรวจสอบใน Google Sheets ว่าตั้งชื่อ Tab ด้านล่างว่า 'masters' และ 'research' หรือยังคะ?")
        st.stop()

df_master, df_research = load_data()

# ตรวจสอบคอลัมน์สำคัญจากไฟล์จริง
if 'Name-surname' not in df_master.columns:
    st.error(f"❌ หาหัวตาราง 'Name-surname' ไม่พบ ในหน้า masters")
    st.write("หัวตารางที่คุณมีตอนนี้คือ:", list(df_master.columns))
    st.stop()

# =========================
# SIDEBAR: เมนูและตัวกรอง
# =========================
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงานและ KPI", "✍️ บันทึกผลงาน"])
    
    st.divider()
    st.header("🔍 ตัวกรองปี พ.ศ.")
    all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปีที่ต้องการดู", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูลวิจัยตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้าที่ 1: รายงานผล (Logic ตามต้นฉบับของคุณ)
# =========================
if menu == "📊 รายงานและ KPI":
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")

    # เตรียมรายชื่อหลักสูตรทั้งหมดจากหน้า masters
    all_programs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_programs, columns=["หลักสูตร"])
    
    # แมปคณะ
    prog_to_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    df_all_progs["คณะ"] = df_all_progs["หลักสูตร"].map(prog_to_fac)

    # ประมวลผลคะแนน
    if df_filtered.empty:
        prog_report = df_all_progs.copy()
        prog_report["คะแนนสะสม"] = 0.0
    else:
        df_full_res = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                        left_on="ผู้เขียน", right_on="Name-surname", how="left")
        res_sum = df_full_res.groupby("หลักสูตร").agg(คะแนนสะสม=("คะแนน", "sum")).reset_index()
        prog_report = df_all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)

    # สูตรคำนวณ KPI
    faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    def get_x_value(prog):
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        if prog in group_40: return 40
        if prog == "Ph.D-Admin": return 60
        return 20

    def calculate_kpi(row):
        prog = row["หลักสูตร"]
        n_fac = faculty_counts.get(prog, 1)
        x_val = get_x_value(prog)
        kpi = (((row["คะแนนสะสม"] / n_fac) * 100) / x_val) * 5
        return round(min(kpi, 5.0), 2)

    prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calculate_kpi, axis=1)
    prog_report["สถานะ"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: "ผ่านเกณฑ์ ✅" if x >= 5 else "กำลังดำเนินการ")
    prog_report = prog_report.sort_values(by=["คณะ", "หลักสูตร"])

    # แสดงกราฟ
    fig_prog = px.bar(
        prog_report, x="คะแนนปัจจุบัน", y="หลักสูตร", orientation='h', color="คณะ",
        color_discrete_sequence=px.colors.qualitative.Pastel, height=800
    )
    fig_prog.add_vline(x=5, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig_prog, use_container_width=True)

    # แสดงตาราง
    st.dataframe(prog_report[["คณะ", "หลักสูตร", "คะแนนสะสม", "คะแนนปัจจุบัน", "สถานะ"]], use_container_width=True)

# =========================
# หน้าที่ 2: บันทึกผลงาน (บันทึกลง Sheet)
# =========================
else:
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        authors = st.multiselect("เลือกผู้เขียน (อาจารย์)", df_master["Name-surname"].dropna().unique())

        if st.form_submit_button("💾 บันทึกข้อมูลลงระบบ"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                             "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                
                # อัปเดตไปยัง Google Sheets
                conn.update(worksheet="research", data=df_updated)
                
                st.success("บันทึกข้อมูลสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("⚠️ กรุณาระบุชื่อเรื่องและเลือกผู้เขียน")
