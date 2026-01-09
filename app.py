import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

# ตั้งค่าฟอนต์ภาษาไทย
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูล (ปรับปรุงเพื่อรองรับภาษาไทย) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจากแผ่นงานโดยตรง
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างชื่อคอลัมน์และจัดการช่องว่าง
        df_m.columns = [str(c).strip() for c in df_m.columns]
        df_r.columns = [str(c).strip() for c in df_r.columns]
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        st.stop()

df_master, df_research = load_data()

# --- 3. ส่วนการแสดงผล ---
st.success("✅ เชื่อมต่อข้อมูลสำเร็จแล้วค่ะ")

with st.sidebar:
    st.title("📌 เมนูหลัก")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])

if menu == "📊 รายงาน KPI":
    st.title("📊 สรุปผลการดำเนินงานวิจัย")
    
    # คำนวณรายหลักสูตร
    progs = df_master["หลักสูตร"].unique()
    report = pd.DataFrame(progs, columns=["หลักสูตร"])
    
    # รวมคะแนน
    merged = df_research.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    score_sum = merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    report = report.merge(score_sum, on="หลักสูตร", how="left").fillna(0)
    
    # แสดงกราฟ
    fig = px.bar(report, x="คะแนน", y="หลักสูตร", orientation='h', title="คะแนนรวมรายหลักสูตร")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(report, use_container_width=True)

else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("add_form"):
        title = st.text_input("ชื่อเรื่อง (ภาษาไทย/อังกฤษ)")
        author = st.selectbox("เลือกผู้เขียน", df_master["Name-surname"].unique())
        if st.form_submit_button("💾 บันทึก"):
            st.info("กำลังพัฒนาระบบการเขียนกลับ ข้อมูลเบื้องต้นถูกเตรียมไว้แล้วค่ะ")
