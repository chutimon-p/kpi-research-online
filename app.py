import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

# --- เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data_robust():
    try:
        # ดึงข้อมูลแผ่นงานทั้งหมด
        all_sheets = conn.read()
        
        # 1. พยายามหาตามชื่อก่อน
        df_m = all_sheets.get("masters")
        df_r = all_sheets.get("research")
        
        # 2. ถ้าหาตามชื่อไม่เจอ ให้ดึงตามลำดับ (แผ่นที่ 1 คือ masters, แผ่นที่ 2 คือ research)
        sheet_names = list(all_sheets.keys())
        if df_m is None:
            df_m = all_sheets[sheet_names[0]]
        if df_r is None:
            df_r = all_sheets[sheet_names[1]]
            
        # ล้างชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
        st.stop()

df_master, df_research = load_data_robust()

# --- เมนู Sidebar ---
with st.sidebar:
    st.title("📌 ระบบงานวิจัย")
    menu = st.radio("เลือกเมนู", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])

# --- หน้าที่ 1: รายงาน KPI (อิงตามไฟล์จริงที่คุณส่งมา) ---
if menu == "📊 รายงาน KPI":
    st.title("📊 สรุปความก้าวหน้า KPI รายหลักสูตร")
    
    # ดึงรายชื่อหลักสูตรและจำนวนอาจารย์ (จากคอลัมน์ 'หลักสูตร' และ 'Name-surname')
    prog_info = df_master.groupby("หลักสูตร").agg(
        จำนวนอาจารย์=("Name-surname", "nunique"),
        คณะ=("คณะ", "first")
    ).reset_index()
    
    # รวมคะแนนจากหน้า research
    res_score = df_research.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                   left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_sum = res_score.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    
    # รวมข้อมูลเพื่อคำนวณ
    report = prog_info.merge(res_sum, on="หลักสูตร", how="left").fillna(0)
    
    # ฟังก์ชันคำนวณ KPI ตามเกณฑ์ของคุณ
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = row["จำนวนอาจารย์"]
        # ค่า X ตามกลุ่มหลักสูตร
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    report["คะแนน KPI"] = report.apply(calc_kpi, axis=1)
    
    # กราฟแท่ง
    fig = px.bar(report.sort_values("คะแนน KPI"), x="คะแนน KPI", y="หลักสูตร", color="คณะ",
                 orientation='h', height=700)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(report[["คณะ", "หลักสูตร", "จำนวนอาจารย์", "คะแนน", "คะแนน KPI"]], use_container_width=True)

# --- หน้าที่ 2: บันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("input_form"):
        t = st.text_input("ชื่อเรื่อง")
        a = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].unique())
        j = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        
        if st.form_submit_button("💾 บันทึก"):
            if t and a:
                # Logic บันทึกข้อมูลกลับ (เหมือนเดิม)
                st.success("บันทึกข้อมูลเรียบร้อย (ตัวอย่าง)")
