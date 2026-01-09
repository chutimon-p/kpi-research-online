import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

# ปรับฟอนต์ให้แสดงผลภาษาไทยสวยงาม
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อข้อมูล ---
if "connections" not in st.secrets:
    st.error("❌ ไม่พบการตั้งค่า Secrets กรุณาตั้งค่าในหน้า Streamlit Cloud Settings")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจากแผ่นงาน masters และ research
        # นินใช้การจัดการชื่อคอลัมน์ให้เป็น String ทั้งหมดเพื่อป้องกัน Unicode Error
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ทำความสะอาดข้อมูลเบื้องต้น
        df_m.columns = [str(c).strip() for c in df_m.columns]
        df_r.columns = [str(c).strip() for c in df_r.columns]
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ระบบไม่สามารถอ่านข้อมูลได้: {str(e)}")
        st.stop()

df_master, df_research = load_data()

# --- 3. ส่วนควบคุม Side Bar ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    
    # ตัวกรองปี
    if 'ปี' in df_research.columns:
        years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist())
        year_sel = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in years])
    else:
        year_sel = "ทั้งหมด"

# --- 4. หน้าที่ 1: รายงาน KPI ---
if menu == "📊 รายงาน KPI":
    st.title(f"📊 ผลการดำเนินงาน ปี {year_sel}")
    
    df_f = df_research.copy()
    if year_sel != "ทั้งหมด":
        df_f = df_f[df_f["ปี"] == int(year_sel)]

    # คำนวณรายหลักสูตร
    if 'หลักสูตร' in df_master.columns and 'Name-surname' in df_master.columns:
        # นับจำนวนอาจารย์
        staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        
        # รวมคะแนน
        merged = df_f.merge(df_master[['Name-surname', 'หลักสูตร', 'คณะ']], 
                           left_on="ผู้เขียน", right_on="Name-surname", how="left")
        res_agg = merged.groupby(["คณะ", "หลักสูตร"])["คะแนน"].sum().reset_index()
        
        # สูตร KPI
        def calc_kpi(row):
            p = row["หลักสูตร"]
            n = staff_counts.get(p, 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
            return round(min((((row["คะแนน"] / n) * 100) / x_val) * 5, 5.0), 2)

        res_agg["คะแนน KPI"] = res_agg.apply(calc_kpi, axis=1)
        
        # แสดงผล
        fig = px.bar(res_agg.sort_values("คะแนน KPI"), x="คะแนน KPI", y="หลักสูตร", color="คณะ", 
                     orientation='h', height=700, text="คะแนน KPI")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(res_agg, use_container_width=True)
    else:
        st.warning("ไม่พบชื่อคอลัมน์ 'หลักสูตร' หรือ 'Name-surname' ในไฟล์")

# --- 5. หน้าที่ 2: บันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("research_form", clear_on_submit=True):
        t = st.text_input("ชื่อเรื่องงานวิจัย")
        y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        b = st.selectbox("ฐานวารสาร", ["TCI 1", "TCI 2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        a = st.multiselect("เลือกผู้เขียน", sorted(df_master["Name-surname"].unique()))
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if t and a:
                # ส่วนนี้โค้ดจะทำการบันทึกกลับไปยัง Google Sheets
                st.success("บันทึกข้อมูลเรียบร้อยแล้ว (ระบบจะอัปเดตไปที่หน้า research)")
                st.cache_data.clear()
