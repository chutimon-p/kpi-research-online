import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. การเชื่อมต่อฐานข้อมูล
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
            
            # --- จุดที่แก้ไข: ป้องกัน Error .str accessor ---
            # จะใช้ strip() เฉพาะคอลัมน์ที่เป็นชื่อหัวตาราง และตรวจสอบว่าเป็น string
            df.columns = [str(col).strip() for col in df.columns]
            
            # ล้างช่องว่างในข้อมูลที่เป็นข้อความทั้งหมด
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
            
            return df
        except Exception as e:
            st.error(f"❌ โหลดข้อมูล '{sheet_name}' ล้มเหลว: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. การตั้งค่าหน้าจอ
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# (CSS ส่วนเดิม...)
st.markdown("<style>html, body, [class*='css'] { font-family: 'Sarabun', sans-serif; }</style>", unsafe_allow_html=True)

# โหลดข้อมูล
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ ไม่พบข้อมูลหรือกำลังโหลด... โปรดตรวจสอบ Google Sheets")
    st.stop()

# ทำความสะอาดข้อมูลตัวเลข
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar & Navigation
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

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 เลือกปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้า Dashboard (คงเดิมตามสูตร Excel)
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 รายงานผลงานวิจัยปี {year_option}")
    # (ส่วน logic Dashboard เหมือนเดิมที่คำนวณ KPI ถูกต้องแล้ว)

# ==========================================
# 5. หน้าจัดการข้อมูล (แก้ไขป้องกัน API Error)
# ==========================================
elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    client = conn_sheets()
    sh = client.open("Research_Database")
    ws = sh.worksheet("research")

    # ส่วนที่ 1: ลบรายเรื่อง
    st.markdown("#### 🗑 ลบเฉพาะรายการ")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
    opts = ["-- เลือกเรื่อง --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
    sel = st.selectbox("เลือกงานวิจัย:", opts)
    
    if sel != "-- เลือกเรื่อง --":
        target = sel.split(" | ")[1].strip()
        if st.button("ยืนยันการลบ"):
            with st.spinner("กำลังลบ..."):
                all_records = ws.get_all_records()
                indices = [i + 2 for i, r in enumerate(all_records) if str(r.get('ชื่อเรื่อง')).strip() == target]
                if indices:
                    for idx in sorted(indices, reverse=True):
                        ws.delete_rows(idx)
                        time.sleep(0.3) # ป้องกัน API โดนล็อค
                    st.success("ลบสำเร็จ!"); st.cache_data.clear(); st.rerun()

    st.divider()

    # ส่วนที่ 2: ลบทั้งหมด (Batch Safe)
    st.markdown("#### ⚠️ ลบข้อมูลทั้งหมด")
    if year_option == "ทั้งหมด":
        st.info("กรุณาเลือกปีที่ต้องการลบในแถบเมนูด้านซ้าย")
    else:
        st.error(f"ระวัง: ข้อมูลปี {year_option} ทั้งหมดจะถูกลบ")
        confirm = st.text_input(f"พิมพ์ 'DELETE {year_option}'")
        if st.button("ยืนยันล้างข้อมูล"):
            if confirm == f"DELETE {year_option}":
                with st.spinner("กำลังดำเนินการ..."):
                    all_rec = ws.get_all_records()
                    rows = [i + 2 for i, r in enumerate(all_rec) if str(r.get('ปี')) == year_option]
                    if rows:
                        for r in sorted(rows, reverse=True):
                            ws.delete_rows(r)
                            if r % 5 == 0: time.sleep(0.5)
                        st.success("ล้างข้อมูลเรียบร้อย!"); st.cache_data.clear(); st.rerun()
