import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าเว็บและฟอนต์ ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# เกณฑ์คะแนนตามฐานวารสาร
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # อ่านข้อมูลจาก Tab ชื่อ masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        # ตัดคอลัมน์ที่ไม่มีชื่อ (ถ้ามี)
        df_r = df_r.loc[:, ~df_r.columns.str.contains('^Unnamed')]
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
        st.info("กรุณาตรวจสอบว่าชื่อ Tab ใน Google Sheets คือ 'masters' และ 'research' หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# =========================
# SIDEBAR: เมนูและตัวกรอง
# =========================
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI"])
    
    st.divider()
    st.header("🔍 ตัวกรองปี พ.ศ.")
    # ดึงปีจากคอลัมน์ 'ปี'
    all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปีที่ต้องการดู", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูลตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้าที่ 1: บันทึกผลงาน
# =========================
if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        # ใช้คอลัมน์ 'Name-surname' ตามไฟล์จริงของคุณ
        authors = st.multiselect("เลือกผู้เขียน (อาจารย์)", df_master["Name-surname"].dropna().unique())
        ext_author = st.text_input("ชื่อผู้เขียนภายนอก (ถ้ามี)")

        if st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets"):
            if title and (authors or ext_author):
                new_rows = []
                for a in authors:
                    new_rows.append({
                        "ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                        "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a, "ผู้เขียนภายนอก": ext_author
                    })
                
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                conn.update(worksheet="research", data=df_updated)
                
                st.success("บันทึกข้อมูลสำเร็จแล้ว!")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("⚠️ กรุณาระบุชื่อเรื่องและเลือกผู้เขียน")

# =========================
# หน้าที่ 2: รายงานผล (Logic ตามไฟล์จริง)
# =========================
else:
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")

    # ดึงหลักสูตรจากคอลัมน์ 'หลักสูตร'
    all_programs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_programs, columns=["หลักสูตร"])
    
    # แมป คณะ กับ หลักสูตร
    prog_to_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    df_all_progs["คณะ"] = df_all_progs["หลักสูตร"].map(prog_to_fac)

    if df_filtered.empty:
        prog_report = df_all_progs.copy()
        prog_report["คะแนนสะสม"] = 0.0
    else:
        # เชื่อมข้อมูลวิจัยกับข้อมูลอาจารย์ผ่าน 'ผู้เขียน' และ 'Name-surname'
        df_full_res = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                        left_on="ผู้เขียน", right_on="Name-surname", how="left")
        res_sum = df_full_res.groupby("หลักสูตร").agg(คะแนนสะสม=("คะแนน", "sum")).reset_index()
        prog_report = df_all_progs.merge(res_sum, on="หลักสูตร", how="left")
        prog_report["คะแนนสะสม"] = prog_report["คะแนนสะสม"].fillna(0)

    # นับจำนวนอาจารย์รายหลักสูตร
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
        # สูตร KPI: (((คะแนนสะสม / จำนวนอาจารย์) * 100) / X) * 5
        kpi = (((row["คะแนนสะสม"] / n_fac) * 100) / x_val) * 5
        return round(min(kpi, 5.0), 2)

    prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calculate_kpi, axis=1)
    prog_report["ส่วนที่ขาด"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: round(max(0, 5 - x), 2))
    prog_report["สถานะ"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: "ผ่านเกณฑ์ ✅" if x >= 5 else "กำลังดำเนินการ")

    tab_prog, tab_person = st.tabs(["🎓 รายหลักสูตร (KPI)", "👤 รายบุคคล"])

    with tab_prog:
        st.subheader("กราฟแสดงความก้าวหน้า KPI (เส้นสีแดงคือเป้าหมาย 5.0)")
        fig_prog = px.bar(
            prog_report, x="คะแนนปัจจุบัน", y="หลักสูตร", orientation='h',
            color_discrete_sequence=["#2ecc71"], height=800 
        )
        fig_prog.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
        st.plotly_chart(fig_prog, use_container_width=True)
        st.dataframe(prog_report[["คณะ", "หลักสูตร", "คะแนนสะสม", "คะแนนปัจจุบัน", "สถานะ"]], use_container_width=True)

    with tab_person:
        if not df_filtered.empty:
            p_report = df_filtered.groupby("ผู้เขียน").agg(จำนวนเรื่อง=("ชื่อเรื่อง", "nunique"), คะแนนรวม=("คะแนน", "sum")).reset_index()
            st.dataframe(p_report.sort_values("คะแนนรวม", ascending=False), use_container_width=True)
