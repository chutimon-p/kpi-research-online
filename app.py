import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบ KPI งานวิจัย", layout="wide")

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ดึงข้อมูล และตัดช่องว่างในชื่อคอลัมน์ออกโดยอัตโนมัติ
        m_df = conn.read(worksheet="masters", ttl=0)
        r_df = conn.read(worksheet="research", ttl=0)
        
        # ล้างช่องว่างในชื่อคอลัมน์เพื่อกัน Error
        m_df.columns = m_df.columns.str.strip()
        r_df.columns = r_df.columns.str.strip()
        
        return m_df, r_df
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
        st.info("กรุณาตรวจสอบ: 1.ชื่อ Tab (masters/research) 2.สถานะการแชร์ (Anyone with link) 3.URL ใน Secrets")
        st.stop()

df_master, df_research = load_data()

# --- 3. ตรวจสอบชื่อคอลัมน์ (เพื่อป้องกันแอปพัง) ---
required_m = ['Name-surname', 'คณะ', 'หลักสูตร']
required_r = ['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร', 'คะแนน', 'ผู้เขียน']

missing_m = [c for c in required_m if c not in df_master.columns]
missing_r = [c for c in required_r if c not in df_research.columns]

if missing_m or missing_r:
    st.error(f"❌ หัวตารางใน Google Sheets ไม่ถูกต้อง")
    if missing_m: st.write(f"หน้า masters ขาดคอลัมน์: {missing_m}")
    if missing_r: st.write(f"หน้า research ขาดคอลัมน์: {missing_r}")
    st.stop()

# --- 4. Logic การคำนวณและแสดงผล ---
st.title("📊 ระบบสรุปผลงานวิจัยออนไลน์")

# เมนู Sidebar
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
with st.sidebar:
    st.header("🔑 ส่วนแอดมิน")
    if not st.session_state['logged_in']:
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if user == st.secrets.get("admin_user", "admin") and pwd == st.secrets.get("admin_pwd", "password123"):
                st.session_state['logged_in'] = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

menu = st.sidebar.radio("เลือกหน้า", ["ดูรายงาน KPI", "เพิ่มข้อมูลวิจัย"])

if menu == "ดูรายงาน KPI":
    # ส่วนสรุป KPI (ดึง Logic เดิมที่คุณต้องการ)
    st.subheader("เป้าหมาย KPI รายหลักสูตร (เส้นแดงคือเกณฑ์ 5.0)")
    
    # คำนวณคะแนน (ตัวอย่างแบบย่อ)
    res_agg = df_research.groupby("ผู้เขียน")["คะแนน"].sum().reset_index()
    summary = df_master.merge(res_agg, left_on="Name-surname", right_on="ผู้เขียน", how="left").fillna(0)
    
    prog_report = summary.groupby("หลักสูตร")["คะแนน"].mean().reset_index() # คำนวณค่าเฉลี่ยเบื้องต้น
    prog_report.columns = ["หลักสูตร", "คะแนนเฉลี่ย"]
    
    fig = px.bar(prog_report, x="คะแนนเฉลี่ย", y="หลักสูตร", orientation='h', color_discrete_sequence=['#2ecc71'])
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เกณฑ์ผ่าน (5.0)")
    st.plotly_chart(fig, use_container_width=True)
    st.table(prog_report)

elif menu == "เพิ่มข้อมูลวิจัย":
    if not st.session_state['logged_in']:
        st.warning("กรุณาล็อกอินเพื่อบันทึกข้อมูล")
    else:
        with st.form("add_form", clear_on_submit=True):
            st.subheader("บันทึกผลงานใหม่")
            f_title = st.text_input("ชื่อเรื่อง")
            f_year = st.number_input("ปี พ.ศ.", 2567, 2570, 2567)
            f_base = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus"])
            f_author = st.selectbox("ผู้เขียน", df_master["Name-surname"].unique())
            
            if st.form_submit_button("💾 บันทึกลง Google Sheets"):
                score_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus": 1.0}
                new_data = pd.DataFrame([{
                    "ชื่อเรื่อง": f_title, "ปี": f_year, "ฐานวารสาร": f_base,
                    "คะแนน": score_map[f_base], "ผู้เขียน": f_author, "ผู้เขียนภายนอก": ""
                }])
                updated_df = pd.concat([df_research, new_data], ignore_index=True)
                conn.update(worksheet="research", data=updated_df)
                st.success("บันทึกสำเร็จ! กราฟจะอัปเดตทันที")
                st.balloons()
