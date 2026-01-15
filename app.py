import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. การเชื่อมต่อ Google Sheets
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

def load_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            ws = sh.worksheet(sheet_name)
            df = pd.DataFrame(ws.get_all_records())
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"❌ โหลดข้อมูล {sheet_name} ไม่สำเร็จ: {e}")
    return pd.DataFrame()

def save_data(sheet_name, row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        ws = sh.worksheet(sheet_name)
        ws.append_row(list(row_dict.values()))

# ==========================================
# 2. กำหนดค่าตัวหารคงที่ (Fixed Dividers ตามไฟล์ Excel)
# ==========================================
FIXED_PROG_MEMBERS = {
    "BE": 5, "CA": 5, "B.Ed-Math": 5, "B.Ed-Sci": 5, "B.Ed-Eng": 5, "B.Ed-EC": 5,
    "G-Dip TH": 5, "G-Dip Inter": 5, "M.Ed-Admin": 3, "M.Ed-LMS": 3, "Ph.D-Admin": 3,
    "BBA": 9, "ACC": 5, "AB": 5, "ATC": 5, "AR": 5, "MBA": 3,
    "PH": 5, "OHS": 5, "MPH": 3, "NS": 5
}

FIXED_FAC_MEMBERS = {
    "มนุษย์ศาสตร์และสังคมศาสตร์": 15,
    "คณะศึกษาศาสตร์": 42,
    "คณะบริหารธุรกิจบัณฑิต": 40,
    "คณะสาธารณสุขศาสตร์": 18,
    "คณะพยาบาลศาสตร์": 15
}

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. เริ่มต้นแอปและเตรียมข้อมูล
# ==========================================
st.set_page_config(page_title="STIU Research Management", layout="wide")

# โหลดข้อมูล
df_master = load_data("masters")
df_research = load_data("research")

if df_master.empty or df_research.empty:
    st.info("🔄 กำลังโหลดข้อมูล...")
    st.stop()

# --- ป้องกัน Error: แปลงข้อมูลเป็น String และลบช่องว่างก่อน Merge ---
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)

# ==========================================
# 4. เมนูและการนำทาง (Navigation)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.title("🏫 STIU Research")
    menu = st.radio("เมนูหลัก:", ["📊 Dashboard & KPI", "✍️ บันทึกงานวิจัย", "⚙️ จัดการฐานข้อมูล"])
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == st.secrets.get("ADMIN_PASSWORD"): 
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        if st.button("ออกจากระบบ"): 
            st.session_state.logged_in = False
            st.rerun()

# ==========================================
# 5. หน้า Dashboard & KPI
# ==========================================
if menu == "📊 Dashboard & KPI":
    st.header("📈 ผลการประเมินงานวิจัยและ KPI")
    
    year_list = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    sel_year = st.selectbox("📅 เลือกปี พ.ศ.:", ["ทั้งหมด"] + [str(y) for y in year_list])

    df_filtered = df_research.copy()
    if sel_year != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(sel_year)]

    # เชื่อมข้อมูลสังกัด (Merge)
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

    t1, t2, t3 = st.tabs(["🎓 KPI รายหลักสูตร", "🏢 KPI รายคณะ", "👤 ค้นหารายบุคคล"])

    with t1:
        # ตรรกะ: 1 ชื่อเรื่อง นับ 1 ครั้งต่อหลักสูตร (ถ้าอยู่ BE ทั้งคู่ นับแค่ 1)
        prog_dedup = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_dedup.groupby("หลักสูตร").agg(Score=('คะแนน', 'sum'), Titles=('ชื่อเรื่อง', 'count')).reset_index()
        
        # นำมาแมพกับตัวหารค่าคงที่
        report_p = pd.DataFrame(list(FIXED_PROG_MEMBERS.keys()), columns=["หลักสูตร"])
        report_p = report_p.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_p(row):
            n = FIXED_PROG_MEMBERS.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            # สูตร: ((คะแนน / จำนวนอาจารย์) * 100) / เกณฑ์กลุ่ม * 5
            return round((((row["Score"] / n) * 100) / x) * 5, 2)

        report_p["คะแนน KPI"] = report_p.apply(calc_p, axis=1)
        
        st.plotly_chart(px.bar(report_p.sort_values("คะแนน KPI"), x="คะแนน KPI", y="หลักสูตร", text="คะแนน KPI", orientation='h', height=600), use_container_width=True)
        st.dataframe(report_p.sort_values("คะแนน KPI", ascending=False), use_container_width=True, hide_index=True)

    with t2:
        # ตรรกะ: 1 ชื่อเรื่อง นับ 1 ครั้งต่อคณะ
        fac_dedup = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_dedup.groupby("คณะ").agg(Score=('คะแนน', 'sum'), Titles=('ชื่อเรื่อง', 'count')).reset_index()
        
        report_f = pd.DataFrame(list(FIXED_FAC_MEMBERS.keys()), columns=["คณะ"])
        report_f = report_f.merge(fac_sum, on="คณะ", how="left").fillna(0)

        def calc_f(row):
            n = FIXED_FAC_MEMBERS.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            return round((((row["Score"] / n) * 100) / y) * 5, 2)

        report_f["คะแนน KPI คณะ"] = fac_report_f = report_f.apply(calc_f, axis=1)
        st.plotly_chart(px.bar(report_f, x="คะแนน KPI คณะ", y="คณะ", text="คะแนน KPI คณะ", orientation='h'), use_container_width=True)
        st.dataframe(report_f, use_container_width=True, hide_index=True)

    with t3:
        search_name = st.selectbox("🔎 ค้นหานักวิจัย:", ["-- เลือกชื่อ --"] + sorted(df_master["Name-surname"].tolist()))
        if search_name != "-- เลือกชื่อ --":
            person_work = df_filtered[df_filtered["ผู้เขียน"] == search_name]
            st.metric("จำนวนงานวิจัยสะสม", len(person_work))
            st.table(person_work[["ปี", "ชื่อเรื่อง", "ฐานวารสาร", "คะแนน"]])

# ==========================================
# 6. หน้าบันทึกงานวิจัย (สำหรับ Admin)
# ==========================================
elif menu == "✍️ บันทึกงานวิจัย":
    if not st.session_state.logged_in: st.warning("🔒 เฉพาะผู้ดูแลระบบเท่านั้น"); st.stop()
    
    st.header("📝 บันทึกผลงานวิจัยใหม่")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่องงานวิจัย")
        c1, c2 = st.columns(2)
        year = c1.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        db = c2.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        authors = st.multiselect("ผู้เขียน (เลือกได้หลายคน)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("💾 บันทึก"):
            if title and authors:
                for author in authors:
                    save_data("research", {"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": author})
                st.success("บันทึกข้อมูลเรียบร้อย!"); st.cache_data.clear()
            else: st.error("กรุณากรอกข้อมูลให้ครบถ้วน")

# ==========================================
# 7. หน้าจัดการข้อมูล (สำหรับ Admin)
# ==========================================
elif menu == "⚙️ จัดการฐานข้อมูล":
    if not st.session_state.logged_in: st.warning("🔒 เฉพาะผู้ดูแลระบบเท่านั้น"); st.stop()
    
    st.header("⚙️ ตรวจสอบและลบข้อมูล")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values("ปี", ascending=False)
    st.dataframe(df_manage[["ปี", "ชื่อเรื่อง", "ฐานวารสาร"]], use_container_width=True)
    
    del_title = st.selectbox("เลือกเรื่องที่ต้องการลบ:", ["-- เลือก --"] + df_manage["ชื่อเรื่อง"].tolist())
    if del_title != "-- เลือก --":
        if st.button("🗑️ ยืนยันการลบ"):
            client = conn_sheets().open("Research_Database").worksheet("research")
            records = client.get_all_records()
            # ค้นหาทุกแถวที่มีชื่อเรื่องตรงกันเพื่อลบออกทั้งหมด
            rows_to_del = [i+2 for i, r in enumerate(records) if r["ชื่อเรื่อง"] == del_title]
            for r in reversed(rows_to_del): client.delete_rows(r)
            st.success("ลบข้อมูลสำเร็จ!"); st.cache_data.clear(); st.rerun()
