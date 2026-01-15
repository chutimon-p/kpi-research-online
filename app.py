import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. การเชื่อมต่อฐานข้อมูล (Connection)
# ==========================================
@st.cache_resource
def conn_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ การเชื่อมต่อล้มเหลว: {e}")
        return None

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            # ล้างช่องว่างหัวตาราง
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e:
            st.error(f"❌ โหลดแผ่นงาน '{sheet_name}' ไม่ได้: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(list(new_row_dict.values()))
        except Exception as e:
            st.error(f"❌ บันทึกไม่สำเร็จ: {e}")

# ==========================================
# 2. การตั้งค่าหน้ากระดาษ (Page Config)
# ==========================================
st.set_page_config(page_title="Research KPI Dashboard", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# โหลดข้อมูล
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

if df_master.empty:
    st.error("⚠️ ไม่พบข้อมูลอาจารย์ (Sheet: masters)")
    st.stop()

# ทำความสะอาดข้อมูล
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
else:
    df_research = pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. เมนูด้านข้าง (Navigation)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("📌 STIU Research")
    menu = st.radio("เลือกเมนู:", ["📊 รายงานผล Dashboard", "✍️ กรอกข้อมูลรายงาน", "⚙️ จัดการฐานข้อมูล"])
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_filter = st.selectbox("📅 ปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. ส่วนหน้าจอ Dashbord
# ==========================================
if menu == "📊 รายงานผล Dashboard":
    st.subheader(f"📈 ภาพรวมรายงานผลงานวิจัยปี: {year_filter}")
    
    df_filtered = df_research.copy()
    if year_filter != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_filter)]
    
    if df_filtered.empty:
        st.info("ยังไม่มีข้อมูลงานวิจัยในปีที่เลือก")
    else:
        # สรุปตัวเลข (Metrics)
        m1, m2, m3 = st.columns(3)
        unique_titles = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
        m1.metric("จำนวนงานวิจัยรวม", f"{len(unique_titles)} เรื่อง")
        m2.metric("จำนวนนักวิจัย", f"{df_filtered['ผู้เขียน'].nunique()} คน")
        m3.metric("คะแนนสะสมรวม", f"{unique_titles['คะแนน'].sum():.2f}")

        # กราฟแท่งสรุปตามฐานวารสาร
        st.markdown("#### 📊 จำนวนงานวิจัยแยกตามฐานข้อมูล")
        db_summary = unique_titles.groupby("ฐานวารสาร").size().reset_index(name='จำนวน')
        fig = px.bar(db_summary, x='ฐานวารสาร', y='จำนวน', color='ฐานวารสาร', text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 รายละเอียดข้อมูล")
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# ==========================================
# 5. ส่วนหน้าจอจัดการข้อมูล (Submit & Manage)
# ==========================================
elif menu == "✍️ กรอกข้อมูลรายงาน":
    if not st.session_state.logged_in:
        st.warning("🔒 กรุณาเข้าสู่ระบบด้วยรหัสผ่าน Admin เพื่อใช้งานหน้านี้")
    else:
        st.subheader("✍️ กรอกข้อมูลงานวิจัยใหม่")
        with st.form("research_form", clear_on_submit=True):
            title = st.text_input("ชื่อเรื่องงานวิจัย")
            c1, c2 = st.columns(2)
            y_in = c1.number_input("ปี พ.ศ. (เช่น 2568)", 2560, 2600, 2568)
            db
