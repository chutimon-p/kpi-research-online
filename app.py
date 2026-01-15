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
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
        return None

@st.cache_data(ttl=60) # ลดเวลา Cache เพื่อให้เห็นผลการแก้ทันที
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            
            if not data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            
            # แก้ไขจุดที่ทำให้เกิด Error: ล้างช่องว่างหัวตารางแบบปลอดภัย
            df.columns = [str(col).strip() for col in df.columns]
            
            # ล้างช่องว่างในข้อมูลที่เป็น String เท่านั้น
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
            
            return df
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดขณะโหลดแผ่นงาน '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ==========================================
# 2. เริ่มต้นแอปและการจัดการข้อมูล
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# โหลดข้อมูล
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

# ตรวจสอบว่าโหลดข้อมูลสำเร็จหรือไม่
if df_master.empty:
    st.error("❌ ไม่พบข้อมูลในแผ่นงาน 'masters' กรุณาตรวจสอบชื่อแผ่นงานหรือข้อมูลใน Google Sheets")
    st.stop()
if df_research.empty:
    st.info("ℹ️ แผ่นงาน 'research' ยังไม่มีข้อมูล หรือกำลังรอการบันทึกข้อมูลใหม่")
    # ไม่หยุดการทำงานเพื่อให้ Admin สามารถเข้าหน้า Submit ข้อมูลได้
    df_research = pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

# ทำความสะอาดข้อมูลตัวเลข (เฉพาะเมื่อมีข้อมูล)
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar & Logic (เหมือนเดิมแต่ยืดหยุ่นขึ้น)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 เมนูหลัก")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("เลือกหน้า:", menu_options)
    
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    # กรองปี (รองรับกรณีไม่มีข้อมูล)
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("📅 เลือกปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. ส่วน Dashboard และการจัดการ (คงเดิม)
# ==========================================
if menu == "📊 Dashboard & Reports":
    if df_research.empty:
        st.warning("ยังไม่มีข้อมูลงานวิจัยในระบบ กรุณาเข้าสู่ระบบเพื่อเพิ่มข้อมูล")
    else:
        st.success(f"โหลดข้อมูลสำเร็จ! พร้อมแสดงรายงานปี {year_option}")
        # ใส่ Logic Dashboard เดิมของคุณที่นี่...

elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ ลงทะเบียนผลงานใหม่")
    # ใส่ Logic Form เดิมของคุณที่นี่...

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    # ใส่ Logic Delete เดิมของคุณที่นี่...
