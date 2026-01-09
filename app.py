import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ตรวจสอบการตั้งค่า Secrets ---
if "connections" not in st.secrets or "gsheets" not in st.secrets.connections:
    st.error("❌ ไม่พบการตั้งค่า Spreadsheet ใน Secrets")
    st.info("""
    **วิธีแก้ไข:**
    1. ไปที่หน้า **Streamlit Cloud Settings > Secrets**
    2. วางค่าคอนฟิกดังนี้:
       ```toml
       [connections.gsheets]
       spreadsheet = "URL_ของ_GOOGLE_SHEETS_คุณ"
       ```
    """)
    st.stop()

# --- 3. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจากแผ่นงาน masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อหัวตาราง
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        st.info("ตรวจสอบว่าชื่อ Tab คือ 'masters' และ 'research' (ตัวพิมพ์เล็ก) และเปิดแชร์ไฟล์เป็น 'Anyone with the link' หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# --- 4. ส่วนควบคุม (Sidebar) ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกเมนู", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    st.divider()
    
    # ดึงปี พ.ศ. จากข้อมูล
    if not df_research.empty and 'ปี' in df_research.columns:
        all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist())
        year_option = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])
    else:
        year_option = "ทั้งหมด"

# --- 5. หน้าที่ 1: รายงาน KPI ---
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงานวิจัย ปี {year_option}")
    
    df_f = df_research.copy()
    if year_option != "ทั้งหมด":
        df_f = df_f[df_f["ปี"] == int(year_option)]

    # ประมวลผลหลักสูตรจากหน้า masters
    progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    report = pd.DataFrame(progs, columns=["หลักสูตร"])
    
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    staff_cnt = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    
    # รวมคะแนน
    merged = df_f.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    score_sum = merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    
    report = report.merge(score_sum, on="หลักสูตร", how="left").fillna(0)
    report["คณะ"] = report["หลักสูตร"].map(fac_map)

    # คำนวณ KPI Score
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = staff_cnt.get(p, 1)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    report["คะแนน KPI"] = report.apply(calc_kpi, axis=1)
    report = report.sort_values("คะแนน KPI", ascending=False)

    # แสดงกราฟ
    fig = px.bar(report, x="คะแนน KPI", y="หลักสูตร", color="คณะ", orientation='h', height=800,
                 text="คะแนน KPI", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(report, use_container_width=True)

# --- 6. หน้าที่ 2: บันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("research_form", clear_on_submit=True):
        t = st.text_input("ชื่อเรื่องงานวิจัย")
        y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        s_map = {"TCI 1": 0.8, "TCI 2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
        base = st.selectbox("ฐานวารสาร", list(s_map.keys()))
        authors = st.multiselect("เลือกอาจารย์ผู้เขียน", sorted(df_master["Name-surname"].unique()))
        
        if st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets"):
            if t and authors:
                new_data = [{"ชื่อเรื่อง": t, "ปี": y, "ฐานวารสาร": base, "คะแนน": s_map[base], "ผู้เขียน": a} for a in authors]
                updated_df = pd.concat([df_research, pd.DataFrame(new_data)], ignore_index=True)
                conn.update(worksheet="research", data=updated_df)
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
