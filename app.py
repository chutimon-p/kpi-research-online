import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจาก Google Sheets
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        # ล้างช่องว่างที่ชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
        st.stop()

df_master, df_research = load_data()

# เกณฑ์คะแนน
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# --- 3. Sidebar เมนูและตัวกรอง ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI"])
    
    all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปีที่ต้องการดู", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูล
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# --- 4. หน้าบันทึกผลงาน ---
if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        authors = st.multiselect("เลือกผู้เขียน (อาจารย์)", df_master["Name-surname"].dropna().unique())

        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and authors:
                new_data = pd.DataFrame([{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                                          "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors])
                df_updated = pd.concat([df_research, new_data], ignore_index=True)
                conn.update(worksheet="research", data=df_updated)
                st.success("บันทึกข้อมูลเรียบร้อย!")
                st.cache_data.clear()
                st.rerun()

# --- 5. หน้าแสดงผล KPI (Logic 21 หลักสูตรของคุณ) ---
else:
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")
    
    # ดึงหลักสูตรทั้งหมด
    all_programs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_programs, columns=["หลักสูตร"])
    prog_to_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    df_all_progs["คณะ"] = df_all_progs["หลักสูตร"].map(prog_to_fac)

    # คำนวณคะแนน
    if df_filtered.empty:
        prog_report = df_all_progs.copy()
        prog_report["คะแนนสะสม"] = 0.0
    else:
        df_full_res = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                        left_on="ผู้เขียน", right_on="Name-surname", how="left")
        res_sum = df_full_res.groupby("หลักสูตร").agg(คะแนนสะสม=("คะแนน", "sum")).reset_index()
        prog_report = df_all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)

    # สูตรคำนวณ KPI
    fac_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    def calc_kpi(row):
        prog = row["หลักสูตร"]
        x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"] else 20)
        n_staff = fac_counts.get(prog, 1)
        score = (((row["คะแนนสะสม"] / n_staff) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calc_kpi, axis=1)
    
    # กราฟ
    fig = px.bar(prog_report, x="คะแนนปัจจุบัน", y="หลักสูตร", orientation='h', 
                 color_discrete_sequence=["#2ecc71"], height=800)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(prog_report, use_container_width=True)
