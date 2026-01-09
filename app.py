import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าเว็บและฟอนต์ Sarabun ---
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
        h1, h2, h3 { color: #2c3e50; }
        .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# เกณฑ์คะแนน (ตามต้นฉบับของคุณ)
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจาก Tab masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์เพื่อป้องกัน Error
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Google Sheets ได้: {e}")
        st.info("กรุณาตรวจสอบ: 1.ชื่อ Tab (masters/research) 2.การแชร์ไฟล์ (Anyone with link) 3.URL ใน Secrets")
        st.stop()

df_master, df_research = load_data()

# ตรวจสอบหัวตารางพื้นฐาน
if 'Name-surname' not in df_master.columns or 'หลักสูตร' not in df_master.columns:
    st.error("❌ หัวตารางในหน้า 'masters' ไม่ถูกต้อง (ต้องมี Name-surname, หลักสูตร, คณะ)")
    st.write("หัวตารางที่พบตอนนี้:", list(df_master.columns))
    st.stop()

# =========================
# SIDEBAR: เมนูและตัวกรอง
# =========================
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["✍️ บันทึกผลงาน", "📊 รายงานและ KPI"])
    
    st.divider()
    st.header("🔍 ตัวกรองปี พ.ศ.")
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปีที่ต้องการดู", ["แสดงทั้งหมด"] + [str(y) for y in all_years])
    
    st.divider()
    st.info("💡 สูตร KPI ปรับปรุง: (((คะแนนรวม/อาจารย์)*100)/X)*5")

# กรองข้อมูลวิจัยตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้าที่ 1: บันทึกผลงาน
# =========================
if menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        
        journal = st.selectbox("ฐานวารสาร (Journal Database)", list(SCORE_MAP.keys()))
        authors = st.multiselect("เลือกผู้เขียน (เลือกได้หลายท่าน)", df_master["Name-surname"].dropna().unique())

        if st.form_submit_button("💾 บันทึกข้อมูลลงระบบ"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, 
                             "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                
                # บันทึกกลับไปยัง Google Sheets
                conn.update(worksheet="research", data=df_updated)
                
                st.success("บันทึกข้อมูลสำเร็จแล้ว!")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("⚠️ กรุณาระบุชื่อเรื่องและเลือกผู้เขียนอย่างน้อย 1 ท่าน")

# =========================
# หน้าที่ 2: รายงานผล (Logic ต้นฉบับ)
# =========================
else:
    st.title(f"📊 ผลลัพธ์การดำเนินงาน ({year_option})")

    # เตรียมโครงสร้างหลักสูตร
    all_programs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    df_all_progs = pd.DataFrame(all_programs, columns=["หลักสูตร"])
    prog_to_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    df_all_progs["คณะ"] = df_all_progs["หลักสูตร"].map(prog_to_fac)

    # ประมวลผลคะแนน
    if df_filtered.empty:
        prog_report = df_all_progs.copy()
        prog_report["คะแนนสะสม"] = 0.0
    else:
        df_full_res = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                        left_on="ผู้เขียน", right_on="Name-surname", how="left")
        res_sum = df_full_res.groupby("หลักสูตร").agg(คะแนนสะสม=("คะแนน", "sum")).reset_index()
        prog_report = df_all_progs.merge(res_sum, on="หลักสูตร", how="left")
        prog_report["คะแนนสะสม"] = prog_report["คะแนนสะสม"].fillna(0)

    faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    def get_x_value(prog):
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        if prog in group_40: return 40
        if prog == "Ph.D-Admin": return 60
        return 20

    def calculate_kpi(row):
        prog = row["หลักสูตร"]
        n_fac = faculty_counts.get(prog, 1)
        x_val = get_x_value(prog)
        kpi = (((row["คะแนนสะสม"] / n_fac) * 100) / x_val) * 5
        return round(kpi, 4)

    prog_report["คะแนนปัจจุบัน"] = prog_report.apply(calculate_kpi, axis=1)
    prog_report["ส่วนที่ขาด"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: max(0, 5 - x))
    prog_report["สถานะ"] = prog_report["คะแนนปัจจุบัน"].apply(lambda x: "ผ่านเกณฑ์ ✅" if x >= 5 else "กำลังดำเนินการ")
    prog_report = prog_report.sort_values(by=["คณะ", "หลักสูตร"])

    tab_prog, tab_person, tab_fac = st.tabs(["🎓 รายหลักสูตร (KPI)", "👤 รายบุคคล", "🏛 รายคณะ"])

    with tab_prog:
        st.subheader(f"สรุปความก้าวหน้า KPI รายหลักสูตร (ทั้งหมด {len(prog_report)} หลักสูตร)")
        fig_prog = px.bar(
            prog_report.melt(id_vars=["หลักสูตร", "คณะ"], value_vars=["คะแนนปัจจุบัน", "ส่วนที่ขาด"]),
            x="value", y="หลักสูตร", color="variable", orientation='h',
            color_discrete_map={"คะแนนปัจจุบัน": "#2ecc71", "ส่วนที่ขาด": "#f4f6f7"},
            labels={'value': 'คะแนน KPI', 'variable': 'สถานะคะแนน'}, height=800 
        )
        fig_prog.add_vline(x=5, line_dash="dash", line_color="#e74c3c", annotation_text="เป้าหมาย 5.0")
        st.plotly_chart(fig_prog, use_container_width=True)

        st.dataframe(
            prog_report[["คณะ", "หลักสูตร", "คะแนนสะสม", "คะแนนปัจจุบัน", "สถานะ"]]
            .style.apply(lambda x: ['background-color: #d4efdf' if x.สถานะ == "ผ่านเกณฑ์ ✅" else '' for _ in x], axis=1)
            .format({"คะแนนสะสม": "{:.2f}", "คะแนนปัจจุบัน": "{:.2f}"}),
            use_container_width=True, height=770
        )

    with tab_person:
        if not df_filtered.empty:
            df_p = df_filtered.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
            p_report = df_p.groupby(["คณะ", "ผู้เขียน"]).agg(จำนวนเรื่อง=("ชื่อเรื่อง", "nunique"), คะแนนรวม=("คะแนน", "sum")).reset_index()
            st.dataframe(p_report.sort_values(by=["คณะ", "คะแนนรวม"], ascending=[True, False]), use_container_width=True)
        else: st.info("ยังไม่มีข้อมูลผลงานในปีที่เลือก")

    with tab_fac:
        if not df_filtered.empty:
            df_f = df_filtered.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
            df_f['ปี_str'] = df_f['ปี'].astype(str)
            fig_f = px.bar(df_f.groupby(['ปี_str', 'คณะ'])['คะแนน'].sum().reset_index(), 
                           x="ปี_str", y="คะแนน", color="คณะ", barmode="group", title="คะแนนรายคณะแยกตามปี")
            st.plotly_chart(fig_f, use_container_width=True)
