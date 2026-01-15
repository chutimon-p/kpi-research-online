import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time  # เพิ่มมาเพื่อช่วยคุมจังหวะ API

# ==========================================
# 1. Database Connection
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
        st.error(f"❌ Connection Failed: {e}")
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
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"❌ โหลดข้อมูล '{sheet_name}' ล้มเหลว: {e}")
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. Page Config & Data Processing
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# (CSS ส่วนเดิม...)
st.markdown("<style>html, body, [class*='css'] { font-family: 'Sarabun', sans-serif; }</style>", unsafe_allow_html=True)

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังเชื่อมต่อฐานข้อมูล...")
    st.stop()

df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 เมนูหลัก")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("ไปที่หน้า:", menu_options)
    
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 กรองข้อมูลปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้า Dashboard (ส่วนคำนวณ KPI ที่ปรับให้ตรงกับ Excel)
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 สรุปข้อมูลปี {year_option}")
    # (ส่วน Dashboard logic เหมือนโค้ดก่อนหน้า แต่เพิ่ม Audit Table เพื่อความโปร่งใส)
    st.info("กรุณาเลือกเมนู Manage Database หากต้องการลบข้อมูล")

# ==========================================
# 5. หน้าจัดการข้อมูล (แก้ไข API Error)
# ==========================================
elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    
    # ดึง Worksheet มาเตรียมไว้
    client = conn_sheets()
    sh = client.open("Research_Database")
    ws = sh.worksheet("research")
    
    # ส่วนที่ 1: ลบทีละรายการ
    st.markdown("#### 🗑 ลบเฉพาะรายการที่เลือก")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
    opts = ["-- เลือกเรื่อง --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
    sel = st.selectbox("เลือกงานวิจัยที่ต้องการลบ:", opts)
    
    if sel != "-- เลือกเรื่อง --":
        target_title = sel.split(" | ")[1].strip()
        if st.button("ยืนยันการลบรายการนี้"):
            with st.spinner("กำลังลบข้อมูล..."):
                all_records = ws.get_all_records()
                # หาเลขแถว (1-based index)
                rows_to_del = [i + 2 for i, r in enumerate(all_records) if str(r.get('ชื่อเรื่อง')).strip() == target_title]
                for r in sorted(rows_to_del, reverse=True):
                    ws.delete_rows(r)
                    time.sleep(0.2) # พักจังหวะ API
                st.success("ลบข้อมูลสำเร็จ!")
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # ส่วนที่ 2: ลบข้อมูลทั้งหมดตามปี (Batch Delete)
    st.markdown("#### ⚠️ ลบข้อมูลทั้งหมดตามปี")
    if year_option == "ทั้งหมด":
        st.warning("กรุณาเลือก 'ปี พ.ศ.' ที่ต้องการลบในแถบเมนูด้านซ้ายก่อน")
    else:
        st.error(f"คุณกำลังจะลบข้อมูลงานวิจัย 'ทั้งหมด' ของปี {year_option}")
        confirm = st.text_input(f"พิมพ์คำว่า 'DELETE {year_option}' เพื่อยืนยัน")
        
        if st.button(f"ยืนยันล้างข้อมูลปี {year_option}"):
            if confirm == f"DELETE {year_option}":
                with st.spinner("กำลังล้างข้อมูลขนาดใหญ่..."):
                    try:
                        all_records = ws.get_all_records()
                        rows_to_del = [i + 2 for i, r in enumerate(all_records) if str(r.get('ปี')) == year_option]
                        
                        if rows_to_del:
                            # ลบจากล่างขึ้นบนเพื่อรักษาตำแหน่งแถว
                            for r in sorted(rows_to_del, reverse=True):
                                ws.delete_rows(r)
                                # หากลบเยอะมาก ให้หยุดพักทุกๆ 5 แถว
                                if r % 5 == 0:
                                    time.sleep(0.5)
                            
                            st.success(f"ล้างข้อมูลปี {year_option} เรียบร้อย!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.info("ไม่พบข้อมูลในปีที่เลือก")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดขณะลบ: {e}. แนะนำให้รีเฟรชหน้าจอแล้วทำใหม่")
            else:
                st.warning("กรุณาพิมพ์ข้อความยืนยันให้ถูกต้อง")

# ==========================================
# 6. Submit Research
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ ลงทะเบียนผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่อง (Title)")
        c1, c2 = st.columns(2)
        y_in = c1.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        db_in = c2.selectbox("ฐานข้อมูล", list(SCORE_MAP.keys()))
        authors = st.multiselect("รายชื่ออาจารย์", df_master["Name-surname"].unique())
        
        if st.form_submit_button("บันทึก"):
            if title and authors:
                for a in authors:
                    save_to_sheet("research", {"ชื่อเรื่อง": title, "ปี": y_in, "ฐานวารสาร": db_in, "คะแนน": SCORE_MAP[db_in], "ผู้เขียน": a})
                st.success("บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
