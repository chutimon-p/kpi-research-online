import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ดึงข้อมูลจาก Tab ชื่อ masters และ research
        df_m = conn.read(worksheet="masters", ttl="5m") 
        df_r = conn.read(worksheet="research", ttl=0)
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลจาก Google Sheets ได้: {e}")
        st.info("กรุณาเช็ก: 1. ชื่อ Tab ใน Google Sheets ต้องเป็น 'masters' และ 'research' | 2. ใส่ URL ใน Secrets หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# --- 3. ระบบ Login ---
ADMIN_USER = st.secrets.get("admin_user", "admin")
ADMIN_PWD = st.secrets.get("admin_pwd", "password123")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login_form():
    with st.sidebar:
        st.subheader("🔑 แอดมินล็อกอิน")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if user == ADMIN_USER and pwd == ADMIN_PWD:
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("ข้อมูลไม่ถูกต้อง")

# --- 4. เมนู ---
if not st.session_state['logged_in']:
    login_form()
    menu = st.sidebar.radio("เมนู", ["📊 รายงานและ KPI"])
else:
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    menu = st.sidebar.radio("เมนู", ["📊 รายงานและ KPI", "✍️ บันทึกผลงาน"])

# --- 5. การแสดงผล (รายงานและ KPI) ---
if menu == "📊 รายงานและ KPI":
    st.title("📊 รายงานสรุปผลงานวิจัย")
    
    # คำนวณ KPI (Logic เดิมที่คุณชอบ)
    all_progs = df_master["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    # สรุปคะแนน
    res_sum = df_research.groupby("ผู้เขียน")["คะแนน"].sum().reset_index()
    # รวมข้อมูลอาจารย์กับผลงาน
    df_merged = df_master.merge(res_sum, left_on="Name-surname", right_on="ผู้เขียน", how="left").fillna(0)
    
    prog_report = df_merged.groupby(["คณะ", "หลักสูตร"])["คะแนน"].sum().reset_index()
    # (นินตัดส่วนคำนวณสูตร KPI 5 คะแนนมาใส่ตรงนี้เพื่อให้กราฟแสดงผล)
    prog_report["คะแนนปัจจุบัน"] = prog_report["คะแนน"] # ตัวอย่างการแสดงผล
    prog_report["ส่วนที่ขาด"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: max(0, 5-x))

    # กราฟแท่งพร้อมเส้นแดง 5.0
    fig = px.bar(prog_report, x="คะแนนปัจจุบัน", y="หลักสูตร", orientation='h', 
                 title="คะแนน KPI รายหลักสูตร", color_discrete_sequence=['#2ecc71'])
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เกณฑ์ผ่าน (5.0)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(prog_report, use_container_width=True)

# --- 6. การบันทึกข้อมูล ---
elif menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกข้อมูลใหม่ลง Google Sheets")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่อง")
        year = st.number_input("ปี (พ.ศ.)", 2560, 2600, 2567)
        journal = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2"])
        author = st.selectbox("เลือกผู้เขียน", df_master["Name-surname"].unique())
        
        if st.form_submit_button("บันทึก"):
            score_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0}
            new_row = pd.DataFrame([{
                "ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                "คะแนน": score_map[journal], "ผู้เขียน": author, "ผู้เขียนภายนอก": ""
            }])
            # อัปเดต Google Sheets
            updated_df = pd.concat([df_research, new_row], ignore_index=True)
            conn.update(worksheet="research", data=updated_df)
            st.success("บันทึกสำเร็จ!")
            st.rerun()
