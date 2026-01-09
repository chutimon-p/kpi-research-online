import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

# ปรับปรุงฟอนต์ Sarabun เพื่อความสวยงาม
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Google Sheets ---
# ระบบจะดึง URL จาก Secrets [connections.gsheets] spreadsheet
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0) # ttl=0 เพื่อให้ดึงข้อมูลใหม่เสมอเมื่อกด Refresh
def load_all_data():
    try:
        # ดึงข้อมูลจาก 2 แผ่นงานหลัก
        m_df = conn.read(worksheet="masters")
        r_df = conn.read(worksheet="research")
        return m_df, r_df
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
        st.info("คำแนะนำ: ตรวจสอบชื่อ Tab ใน Google Sheets ว่าเป็น 'masters' และ 'research' หรือยัง?")
        st.stop()

df_master, df_research = load_all_data()

# --- 3. ระบบ Login สำหรับแอดมิน ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ดึงรหัสผ่านจาก Secrets (ถ้าไม่มีจะใช้ admin/password123 เป็นค่าตั้งต้น)
ADMIN_USER = st.secrets.get("admin_user", "admin")
ADMIN_PWD = st.secrets.get("admin_pwd", "password123")

def login_section():
    with st.sidebar:
        st.subheader("🔐 ส่วนเจ้าหน้าที่")
        if not st.session_state['logged_in']:
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.button("เข้าสู่ระบบ"):
                if user == ADMIN_USER and pwd == ADMIN_PWD:
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("รหัสผ่านไม่ถูกต้อง")
        else:
            st.success(f"สวัสดีคุณ {ADMIN_USER}")
            if st.button("ออกจากระบบ"):
                st.session_state['logged_in'] = False
                st.rerun()

login_section()

# --- 4. เมนูหลัก ---
menu = st.sidebar.selectbox("เมนูหลัก", ["📊 รายงานสรุป KPI", "✍️ บันทึกผลงาน"])

# ค่าคะแนนของแต่ละฐานวารสาร
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# =========================
# หน้า: รายงานสรุป KPI
# =========================
if menu == "📊 รายงานสรุป KPI":
    st.title("📊 สรุปผลงานวิจัยตามตัวบ่งชี้ (KPI)")
    
    # ตัวกรองปี พ.ศ.
    years = sorted(df_research["ปี"].unique()) if not df_research.empty else [2567, 2568]
    selected_year = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in years])
    
    df_filtered = df_research.copy()
    if selected_year != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(selected_year)]

    # คำนวณรายหลักสูตร (21 หลักสูตร)
    progs = df_master["หลักสูตร"].unique()
    prog_data = []

    for p in progs:
        # จำนวนอาจารย์ในหลักสูตร
        n_staff = len(df_master[df_master["หลักสูตร"] == p])
        # คะแนนสะสมของหลักสูตร
        total_score = df_filtered[df_filtered["ผู้เขียน"].isin(df_master[df_master["หลักสูตร"] == p]["Name-surname"])]["คะแนน"].sum()
        
        # สูตรคำนวณ KPI (X)
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"] else 20)
        
        # คำนวณคะแนนปัจจุบัน (เต็ม 5)
        kpi_score = (((total_score / n_staff) * 100) / x_val) * 5
        kpi_score = min(kpi_score, 5.0) # ไม่ให้เกิน 5

        prog_data.append({
            "หลักสูตร": p,
            "คะแนนปัจจุบัน": round(kpi_score, 2),
            "คะแนนสะสม": total_score,
            "ส่วนที่ขาด": round(max(0, 5 - kpi_score), 2)
        })

    df_kpi = pd.DataFrame(prog_data)

    # กราฟแท่งพร้อมเส้นผ่านเกณฑ์ 5.0
    st.subheader("กราฟแสดงความก้าวหน้า (เป้าหมาย 5.0 คะแนน)")
    fig = px.bar(df_kpi, x="คะแนนปัจจุบัน", y="หลักสูตร", orientation='h',
                 color_discrete_sequence=['#2ecc71'], height=700)
    
    # เพิ่มเส้นไฮไลต์สีแดงตรง 5 คะแนน
    fig.add_vline(x=5.0, line_dash="dash", line_color="#e74c3c", 
                 annotation_text=" เกณฑ์ผ่าน (5.0)", annotation_position="top right")
    
    st.plotly_chart(fig, use_container_width=True)

    # ตารางสรุป
    st.write("### รายละเอียดรายหลักสูตร")
    st.dataframe(df_kpi.style.applymap(lambda x: 'background-color: #d4efdf' if x == 5 else '', subset=['คะแนนปัจจุบัน']), use_container_width=True)

# =========================
# หน้า: บันทึกผลงาน (เฉพาะ Admin)
# =========================
elif menu == "✍️ บันทึกผลงาน":
    if not st.session_state['logged_in']:
        st.warning("🔒 กรุณาเข้าสู่ระบบที่แถบด้านข้างเพื่อบันทึกข้อมูล")
    else:
        st.title("✍️ บันทึกข้อมูลงานวิจัยใหม่")
        with st.form("add_form", clear_on_submit=True):
            t_col1, t_col2 = st.columns([3, 1])
            with t_col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
            with t_col2: year = st.number_input("ปี พ.ศ.", 2560, 2600, 2567)
            
            base = st.selectbox("ฐานข้อมูลวารสาร", list(SCORE_MAP.keys()))
            authors = st.multiselect("เลือกผู้เขียน (อาจารย์ในระบบ)", df_master["Name-surname"].unique())
            ext_author = st.text_input("ชื่อผู้เขียนภายนอก (ถ้ามี)")
            
            if st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets"):
                if title and (authors or ext_author):
                    new_rows = []
                    for a in authors:
                        new_rows.append({
                            "ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": base, 
                            "คะแนน": SCORE_MAP[base], "ผู้เขียน": a, "ผู้เขียนภายนอก": ext_author
                        })
                    
                    new_df = pd.DataFrame(new_rows)
                    updated_research = pd.concat([df_research, new_df], ignore_index=True)
                    
                    # อัปเดตกลับไปที่ Google Sheets
                    conn.update(worksheet="research", data=updated_research)
                    st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว กราฟจะอัปเดตอัตโนมัติ!")
                    st.balloons()
                else:
                    st.error("กรุณากรอกชื่อเรื่องและเลือกผู้เขียน")
