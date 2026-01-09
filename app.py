import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าเว็บและฟอนต์ Sarabun ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
        h1, h2, h3 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# --- 2. เชื่อมต่อ Google Sheets ---
# หมายเหตุ: URL ของ Google Sheets จะถูกตั้งค่าใน Streamlit Secrets ตอนขึ้นออนไลน์
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ดึงข้อมูลจาก Google Sheets แถบ masters และ research
    # ttl=0 สำหรับ research เพื่อให้เห็นข้อมูลใหม่ทันทีที่บันทึก
    df_m = conn.read(worksheet="masters", ttl="10m") 
    df_r = conn.read(worksheet="research", ttl=0)
    return df_m, df_r

try:
    df_master, df_research = load_data()
except Exception as e:
    st.error("❌ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้ กรุณาตรวจสอบการตั้งค่า URL ใน Secrets")
    st.stop()

# --- 3. ระบบ Login สำหรับแอดมิน ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ดึง Username/Password จาก Secrets (ถ้าไม่มีจะใช้ค่า Default)
ADMIN_USER = st.secrets.get("admin_user", "admin")
ADMIN_PWD = st.secrets.get("admin_pwd", "password123")

def login_form():
    with st.sidebar:
        st.subheader("🔑 แอดมินล็อกอิน")
        user = st.text_input("Username", key="input_user")
        pwd = st.text_input("Password", type="password", key="input_pwd")
        if st.button("Login"):
            if user == ADMIN_USER and pwd == ADMIN_PWD:
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("Username หรือ Password ไม่ถูกต้อง")

# --- 4. เมนูและ Sidebar ---
if not st.session_state['logged_in']:
    login_form()
    menu_options = ["📊 รายงานและ KPI"]
else:
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    menu_options = ["📊 รายงานและ KPI", "✍️ บันทึกผลงาน"]

menu = st.sidebar.radio("เมนูหลัก", menu_options)

with st.sidebar:
    st.divider()
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปี พ.ศ.", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# กรองข้อมูลตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้า: บันทึกผลงาน (บันทึกลง Google Sheets)
# =========================
if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัย (สิทธิ์แอดมิน)")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        authors = st.multiselect("เลือกผู้เขียน (ในระบบ)", df_master["Name-surname"].dropna().unique())
        external_authors = st.text_input("ชื่อผู้เขียนภายนอก (ถ้ามี - คั่นด้วยจุลภาค ,)")

        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and (authors or external_authors):
                new_data_list = []
                for a in authors:
                    new_data_list.append({
                        "ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                        "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a, "ผู้เขียนภายนอก": external_authors
                    })
                
                # กรณีมีเฉพาะผู้เขียนภายนอก
                if not authors and external_authors:
                    new_data_list.append({
                        "ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                        "คะแนน": 0, "ผู้เขียน": "บุคคลภายนอก", "ผู้เขียนภายนอก": external_authors
                    })

                # อัปเดตข้อมูลไปยัง Google Sheets
                updated_df = pd.concat([df_research, pd.DataFrame(new_data_list)], ignore_index=True)
                conn.update(worksheet="research", data=updated_df)
                
                st.success("✅ บันทึกข้อมูลลง Google Sheets เรียบร้อยแล้ว!")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("⚠️ กรุณาระบุชื่อเรื่องและผู้เขียน")

# =========================
# หน้า: รายงานผล (แสดงครบ 21 หลักสูตร)
# =========================
else:
    st.title(f"📊 รายงานสรุปผลงาน ({year_option})")

    # 1. เตรียมรายชื่อหลักสูตรทั้งหมด 21 หลักสูตร
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    prog_to_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    df_all_progs["คณะ"] = df_all_progs["หลักสูตร"].map(prog_to_fac)

    # 2. คำนวณ KPI (เฉพาะคนในระบบ)
    df_internal = df_filtered[df_filtered["ผู้เขียน"] != "บุคคลภายนอก"]
    res_sum = df_internal.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left") \
                .groupby("หลักสูตร").agg(คะแนนสะสม=("คะแนน", "sum")).reset_index()
    
    prog_report = df_all_progs.merge(res_sum, on="หลักสูตร", how="left").fillna(0)
    faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    def calc_kpi(row):
        prog = row["หลักสูตร"]
        x = 60 if prog == "Ph.D-Admin" else (40 if prog in ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"] else 20)
        n_fac = faculty_counts.get(prog, 1)
        score = (((row["คะแนนสะสม"] / n_fac) * 100) / x) * 5
        return round(score, 4)

    prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calc_kpi, axis=1)
    prog_report["ส่วนที่ขาด"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: max(0, 5 - x))
    prog_report["สถานะ"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: "ผ่านเกณฑ์ ✅" if x >= 5 else "กำลังดำเนินการ")
    prog_report = prog_report.sort_values(by=["คณะ", "หลักสูตร"])

    tab_prog, tab_person, tab_fac = st.tabs(["🎓 รายหลักสูตร", "👤 รายบุคคล (เจาะลึก)", "🏛 รายคณะ"])

    with tab_prog:
        st.subheader("เป้าหมาย KPI ทุกหลักสูตร (เส้นแดงคือเกณฑ์ผ่าน 5.0)")
        fig_prog = px.bar(prog_report.melt(id_vars=["หลักสูตร", "คณะ"], value_vars=["คะแนนปัจจุบัน", "ส่วนที่ขาด"]),
                          x="value", y="หลักสูตร", color="variable", orientation='h', height=800,
                          color_discrete_map={"คะแนนปัจจุบัน": "#2ecc71", "ส่วนที่ขาด": "#f4f6f7"},
                          labels={'value': 'คะแนน', 'variable': 'ประเภท'})
        fig_prog.add_vline(x=5.0, line_dash="dash", line_color="#e74c3c", annotation_text="เกณฑ์ผ่าน (5.0)")
        st.plotly_chart(fig_prog, use_container_width=True)

        st.dataframe(
            prog_report[["คณะ", "หลักสูตร", "คะแนนสะสม", "คะแนนปัจจุบัน", "สถานะ"]]
            .style.apply(lambda x: ['background-color: #d4efdf' if x.สถานะ == "ผ่านเกณฑ์ ✅" else '' for _ in x], axis=1)
            .format({"คะแนนสะสม": "{:.2f}", "คะแนนปัจจุบัน": "{:.2f}"}),
            use_container_width=True, height=770
        )

    with tab_person:
        st.subheader("สรุปผลงานรายบุคคล")
        if not df_filtered.empty:
            df_p = df_internal.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
            p_summary = df_p.groupby(["คณะ", "ผู้เขียน"]).agg(จำนวนเรื่อง=("ชื่อเรื่อง", "nunique"), คะแนนรวม=("คะแนน", "sum")).reset_index()
            st.dataframe(p_summary.sort_values(["คณะ", "คะแนนรวม"], ascending=[True, False]), use_container_width=True)
            
            st.divider()
            target_user = st.selectbox("เลือกชื่ออาจารย์เพื่อดูชื่อเรื่องงานวิจัย:", sorted(df_p["ผู้เขียน"].unique()))
            user_works = df_p[df_p["ผู้เขียน"] == target_user][["ปี", "ชื่อเรื่อง", "ฐานวารสาร", "ผู้เขียนภายนอก"]]
            st.info(f"📚 รายการงานวิจัยของอาจารย์ {target_user}")
            st.table(user_works)
        else: st.info("ยังไม่มีข้อมูลผลงานในปีที่เลือก")

    with tab_fac:
        st.subheader("เปรียบเทียบคะแนนรายคณะ")
        if not df_filtered.empty:
            df_f = df_internal.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
            df_f['ปี_str'] = df_f['ปี'].astype(str)
            fig_f = px.bar(df_f.groupby(['ปี_str', 'คณะ'])['คะแนน'].sum().reset_index(), 
                           x="ปี_str", y="คะแนน", color="คณะ", barmode="group")
            st.plotly_chart(fig_f, use_container_width=True)
            
            f_sum = df_f.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby("คณะ")["คะแนน"].sum().reset_index()
            st.dataframe(f_sum.sort_values("คะแนน", ascending=False), use_container_width=True)