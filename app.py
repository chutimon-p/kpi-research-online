import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

# --- เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # พยายามดึงข้อมูลจากชื่อ Tab ที่กำหนด
        df_m = conn.read(worksheet="masters", ttl="5m")
        df_r = conn.read(worksheet="research", ttl=0)
        return df_m, df_r
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลได้: ตรวจสอบว่าชื่อ Tab ใน Google Sheets คือ 'masters' และ 'research' หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# --- Logic การคำนวณเดิมของคุณ ---
# (ส่วนนี้คงไว้ตามโค้ดต้นฉบับที่คุณส่งมา เพื่อให้หน้าตาเหมือนเดิม)
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI"])
    
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปีที่ต้องการดู", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

# ... (ส่วนการแสดงผลและคำนวณ KPI ใช้ตามโค้ดเดิมของคุณได้เลยค่ะ) ...

if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        authors = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].dropna().unique())

        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                             "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                # บันทึกกลับไปยัง Google Sheets
                conn.update(worksheet="research", data=df_updated)
                st.success("บันทึกสำเร็จ!")
                st.rerun()
