import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

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
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"❌ โหลดข้อมูลล้มเหลว: {e}")
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. UI Configuration
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ กำลังโหลดข้อมูล...")
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
    
    menu = st.radio("ไปยังหน้า:", menu_options)
    
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 ตัวกรองปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้า Dashboard (คงเดิม)
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.info(f"กำลังแสดงข้อมูลปี: {year_option}")
    # ... (ส่วน Dashboard ของคุณคงเดิมจากเวอร์ชันก่อนหน้า) ...
    st.write("เลือกเมนูอื่นๆ จากแถบด้านซ้ายเพื่อจัดการข้อมูล")

# ==========================================
# 5. หน้าจัดการข้อมูล (แก้ไขเพื่อป้องกัน API Error)
# ==========================================
elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    client = conn_sheets()
    sh = client.open("Research_Database")
    ws = sh.worksheet("research")
    
    # --- ส่วนที่ 1: ลบรายรายการ ---
    st.markdown("#### 🗑 ลบเฉพาะบางรายการ")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
    opts = ["-- เลือกเรื่องที่ต้องการลบ --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
    sel = st.selectbox("เลือกผลงาน:", opts)
    
    if sel != "-- เลือกเรื่องที่ต้องการลบ --":
        target = sel.split(" | ")[1].strip()
        if st.button("ยืนยันลบรายการนี้"):
            with st.spinner("กำลังลบ..."):
                all_records = ws.get_all_records()
                # ค้นหา index แถวทั้งหมดที่ชื่อเรื่องตรงกัน (ใช้ 1-based index สำหรับ Google Sheets)
                indices = [i + 2 for i, r in enumerate(all_records) if str(r.get('ชื่อเรื่อง')).strip() == target]
                
                # ลบแบบ Batch เพื่อป้องกัน API Error
                if indices:
                    for idx in sorted(indices, reverse=True):
                        ws.delete_rows(idx)
                    st.success("ลบสำเร็จ!"); st.cache_data.clear(); st.rerun()

    st.divider()

    # --- ส่วนที่ 2: ลบทั้งหมด (Batch Delete) ---
    st.markdown("#### ⚠️ ลบข้อมูลทั้งหมดตามปี")
    if year_option == "ทั้งหมด":
        st.warning("กรุณาเลือก 'ปี พ.ศ.' ที่ต้องการลบใน Sidebar ด้านซ้ายก่อน")
    else:
        st.error(f"คุณกำลังจะลบข้อมูล 'ทั้งหมด' ของปี {year_option}")
        confirm = st.text_input(f"พิมพ์ 'DELETE {year_option}' เพื่อยืนยัน")
        
        if st.button(f"ยืนยันล้างข้อมูลปี {year_option}"):
            if confirm == f"DELETE {year_option}":
                with st.spinner("กำลังล้างข้อมูล..."):
                    all_records = ws.get_all_records()
                    # ค้นหาทุกแถวที่เป็นปีนั้น
                    rows_to_delete = [i + 2 for i, r in enumerate(all_records) if str(r.get('ปี')) == year_option]
                    
                    if rows_to_delete:
                        # วิธี Batch Delete: ลบทีละแถวจากล่างขึ้นบน 
                        # แต่ถ้าข้อมูลเยอะมาก (เช่น > 50 แถว) แนะนำให้ใช้คำสั่งลบช่วงหรือ Batch
                        for r in sorted(rows_to_delete, reverse=True):
                            ws.delete_rows(r)
                            
                        st.success(f"ล้างข้อมูลปี {year_option} สำเร็จ!"); st.cache_data.clear(); st.rerun()
                    else:
                        st.info("ไม่พบข้อมูลในปีนี้")

# ==========================================
# 6. Submit Research (คงเดิม)
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ ลงทะเบียนผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่อง")
        c1, c2 = st.columns(2)
        year = c1.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        db = c2.selectbox("ฐานข้อมูล", list(SCORE_MAP.keys()))
        authors = st.multiselect("รายชื่อผู้เขียน", df_master["Name-surname"].unique())
        if st.form_submit_button("บันทึกข้อมูล"):
            if title and authors:
                for a in authors:
                    save_to_sheet("research", {"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": a})
                st.success("บันทึกสำเร็จ!"); st.cache_data.clear(); st.rerun()
