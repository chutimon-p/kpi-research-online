import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าจอและฟอนต์ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #ffffff; border: 1px solid #ddd; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # อ่านข้อมูลจาก Tab ชื่อ masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างที่อาจติดมากับหัวตาราง
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อข้อมูลได้: {e}")
        st.stop()

df_master, df_research = load_data()

# --- 3. ส่วนควบคุม (Sidebar) ---
with st.sidebar:
    st.title("📌 เมนูระบบ")
    menu = st.radio("ไปที่หน้า:", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    
    st.divider()
    # ดึงปี พ.ศ. จากข้อมูลจริง
    available_years = sorted(df_research["ปี"].dropna().unique().astype(int)) if not df_research.empty else [2567, 2568]
    selected_year = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in available_years])
    
    st.info("💡 ระบบคำนวณ KPI อิงตามหลักสูตร 21 สาขา")

# กรองข้อมูลตามปีที่เลือก
df_filtered = df_research.copy()
if selected_year != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(selected_year)]

# =========================
# หน้าที่ 1: รายงาน KPI (อิงจาก 21 หลักสูตรและไฟล์จริง)
# =========================
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงาน ปี {selected_year}")
    
    # 1. รวบรวมหลักสูตรทั้งหมดจากไฟล์ masters
    all_programs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_report = pd.DataFrame(all_programs, columns=["หลักสูตร"])
    
    # 2. แมปชื่อคณะให้แต่ละหลักสูตร
    map_fac = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_report["คณะ"] = prog_report["หลักสูตร"].map(map_fac)
    
    # 3. คำนวณคะแนนรวมรายหลักสูตร
    # เชื่อมข้อมูลวิจัยกับอาจารย์เพื่อดูว่าใครอยู่หลักสูตรไหน
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    score_sum = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    
    prog_report = prog_report.merge(score_sum, on="หลักสูตร", how="left").fillna(0)
    
    # 4. สูตรคำนวณ KPI (Logic ที่คุณต้องการ)
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    
    def calculate_kpi_score(row):
        prog = row["หลักสูตร"]
        n_staff = staff_counts.get(prog, 1)
        # กำหนดค่า X ตามกลุ่มหลักสูตร
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if prog == "Ph.D-Admin" else (40 if prog in group_40 else 20)
        
        # (((คะแนนรวม/จำนวนอาจารย์)*100)/X)*5
        raw_kpi = (((row["คะแนน"] / n_staff) * 100) / x_val) * 5
        return round(min(raw_kpi, 5.0), 2)

    prog_report["คะแนน KPI"] = prog_report.apply(calculate_kpi_score, axis=1)
    prog_report = prog_report.sort_values(["คณะ", "หลักสูตร"])

    # แสดงกราฟ
    fig = px.bar(prog_report, x="คะแนน KPI", y="หลักสูตร", orientation='h',
                 color="คณะ", title="ความก้าวหน้า KPI รายหลักสูตร",
                 height=800, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)

    # แสดงตาราง
    st.write("### 📋 ตารางสรุปข้อมูลรายหลักสูตร")
    st.dataframe(prog_report.style.highlight_max(axis=0, subset=["คะแนน KPI"], color='#d4efdf'), use_container_width=True)

# =========================
# หน้าที่ 2: บันทึกผลงาน
# =========================
else:
    st.title("✍️ บันทึกผลงานวิจัยใหม่ลงระบบ")
    with st.form("input_form", clear_on_submit=True):
        f_title = st.text_input("ชื่อเรื่องงานวิจัย")
        f_year = st.number_input("ปี พ.ศ. (ที่ตีพิมพ์)", 2560, 2600, 2568)
        f_base = st.selectbox("ฐานข้อมูลวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        f_authors = st.multiselect("เลือกผู้เขียน (อาจารย์ในสังกัด)", df_master["Name-surname"].dropna().unique())
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if f_title and f_authors:
                score_dict = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
                new_entries = []
                for author in f_authors:
                    new_entries.append({
                        "ชื่อเรื่อง": f_title, "ปี": f_year, "ฐานวารสาร": f_base,
                        "คะแนน": score_dict[f_base], "ผู้เขียน": author, "ผู้เขียนภายนอก": ""
                    })
                
                # อัปเดตกลับไปที่ Google Sheets
                updated_df = pd.concat([df_research, pd.DataFrame(new_entries)], ignore_index=True)
                conn.update(worksheet="research", data=updated_df)
                st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว!")
                st.balloons()
                st.cache_data.clear()
            else:
                st.error("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
