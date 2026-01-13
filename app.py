import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ==========================================
# 1. การเชื่อมต่อ Google Sheets
# ==========================================
def conn_sheets():
    # กำหนดขอบเขตการเข้าถึง
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # ดึงข้อมูล JSON จาก Secrets ของ Streamlit Cloud
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception as e:
        st.error("❌ ไม่สามารถดึงข้อมูลจาก Secrets ได้ กรุณาตรวจสอบการตั้งค่าใน Streamlit Cloud")
        st.stop()
        
    client = gspread.authorize(creds)
    return client

def load_sheet_data(sheet_name):
    client = conn_sheets()
    # *** เปลี่ยนชื่อตรงนี้ให้ตรงกับชื่อไฟล์ Google Sheets ของคุณ ***
    sh = client.open("Research_Database_System") 
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip() # ลบเว้นวรรคที่หัวตาราง
    return df

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    # *** เปลี่ยนชื่อตรงนี้ให้ตรงกับชื่อไฟล์ Google Sheets ของคุณ ***
    sh = client.open("Research_Database_System")
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. เริ่มต้นแอปและการโหลดข้อมูล
# ==========================================
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

# แสดง CSS เพื่อความสวยงาม
st.markdown("""
    <style>
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        font-family: 'Sarabun', sans-serif;
    </style>
""", unsafe_allow_html=True)

# โหลดข้อมูล (มีระบบดักจับ Error กรณีหาไฟล์ไม่เจอ)
try:
    df_master = load_sheet_data("masters")
    df_research = load_sheet_data("research")
except Exception as e:
    st.error(f"⚠️ การเชื่อมต่อขัดข้อง: {e}")
    st.info("ตรวจสอบว่า: 1.ชื่อไฟล์ Sheets ในโค้ดตรงกับใน Drive 2.ชื่อ Tab คือ 'masters' และ 'research' 3.แชร์สิทธิ์ Editor ให้ Email ใน JSON แล้ว")
    st.stop()

ADMIN_PASSWORD = "admin1234"
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar และระบบ Login
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.title("📌 เมนูหลัก")
    menu_options = ["📊 รายงานและ KPI"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ บันทึกผลงาน")
        menu_options.append("⚙️ จัดการข้อมูล")
    
    menu = st.radio("เลือกหน้าจอ", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("🔐 รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านไม่ถูกต้อง")
    else:
        st.success("🔓 สถานะ: เจ้าหน้าที่")
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    # ตัวกรองปี
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("🔍 กรองตามปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 4. หน้าจอแสดงผลรายงาน
# ==========================================
if menu == "📊 รายงานและ KPI":
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")
    
    # กรองข้อมูลตามปี
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

    # กรองเอาหลักสูตรที่มีชื่อ (ยกเว้น "-")
    all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
    all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
    faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    t1, t2, t3 = st.tabs(["🎓 รายหลักสูตร", "👤 รายบุคคล", "🏛 รายคณะ"])

    with t1:
        st.subheader("🎓 ความก้าวหน้า KPI รายหลักสูตร")
        # รวมข้อมูล Master และงานวิจัย
        prog_data = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        prog_sum = prog_data.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = faculty_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["คะแนน"] / n) * 100) / x) * 5, 5.0), 2)

        prog_report["คะแนน KPI"] = prog_report.apply(calc_kpi, axis=1)
        prog_report = prog_report.sort_values(by=["คณะ", "คะแนน KPI"])

        fig = px.bar(prog_report, x="คะแนน KPI", y="หลักสูตร", color="คณะ", orientation='h', 
                     range_x=[0, 5.5], text="คะแนน KPI", height=700,
                     category_orders={"หลักสูตร": prog_report["หลักสูตร"].tolist()})
        fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เกณฑ์ผ่าน (5.0)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("👤 สรุปผลงานรายอาจารย์")
        if not df_filtered.empty:
            p_report = df_filtered.groupby("ผู้เขียน").agg(จำนวนเรื่อง=("ชื่อเรื่อง", "count"), คะแนนสะสม=("คะแนน", "sum")).reset_index()
            st.dataframe(p_report.sort_values("คะแนนสะสม", ascending=False), use_container_width=True, hide_index=True)
            
            sel = st.selectbox("เลือกชื่ออาจารย์เพื่อดูรายละเอียด:", ["-- เลือกรายชื่อ --"] + p_report["ผู้เขียน"].tolist())
            if sel != "-- เลือกรายชื่อ --":
                st.table(df_filtered[df_filtered["ผู้เขียน"] == sel][["ชื่อเรื่อง", "ฐานวารสาร", "ปี", "คะแนน"]])
        else: st.info("ยังไม่มีข้อมูลงานวิจัย")

    with t3:
        st.subheader("🏛 คะแนนสะสมถ่วงน้ำหนักรายคณะ (เปรียบเทียบปี)")
        res_with_prog = df_research.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        if not res_with_prog.empty and "คณะ" in res_with_prog.columns:
            fac_data = res_with_prog.dropna(subset=["คณะ"])
            fac_sum = fac_data.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby(["ปี", "คณะ"])["คะแนน"].sum().reset_index()
            fac_sum["ปี"] = fac_sum["ปี"].astype(str)
            st.plotly_chart(px.bar(fac_sum, x="ปี", y="คะแนน", color="คณะ", barmode="group", text_auto='.2f'), use_container_width=True)

# ==========================================
# 5. หน้าจอสำหรับ Admin (บันทึกข้อมูล)
# ==========================================
elif menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานลงระบบ Google Sheets")
    with st.form("add_form", clear_on_submit=True):
        t_in = st.text_input("ชื่อเรื่องงานวิจัย")
        y_in = st.number_input("ปี พ.ศ. ที่ตีพิมพ์", 2560, 2600, 2568)
        j_in = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        a_in = st.multiselect("เลือกอาจารย์ (ผู้เขียน)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if t_in and a_in:
                for author in a_in:
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                st.success("✅ บันทึกข้อมูลสำเร็จ! ข้อมูลถูกส่งไปยัง Google Sheets แล้ว")
                st.cache_data.clear()
                st.rerun()

# ==========================================
# 6. หน้าจอสำหรับ Admin (ลบข้อมูล)
# ==========================================
elif menu == "⚙️ จัดการข้อมูล":
    st.title("⚙️ ลบข้อมูลในระบบ")
    if not df_research.empty:
        to_del = st.selectbox("เลือกชื่อเรื่องที่จะลบ", df_research["ชื่อเรื่อง"].unique())
        if st.button("🗑 ยืนยันการลบ"):
            client = conn_sheets()
            sh = client.open("Research_Database_System")
            ws = sh.worksheet("research")
            try:
                cell = ws.find(to_del)
                ws.delete_rows(cell.row)
                st.success("✅ ลบข้อมูลออกจาก Google Sheets เรียบร้อยแล้ว")
                st.cache_data.clear()
                st.rerun()
            except:
                st.error("ไม่พบข้อมูลที่ต้องการลบในระบบ")
