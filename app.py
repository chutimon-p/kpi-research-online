import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

# ปรับฟอนต์ Sarabun เพื่อความสวยงาม
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # อ่านข้อมูลจาก Tab ชื่อ masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างที่อาจติดมาในหัวตาราง และตัดคอลัมน์ที่ไม่มีชื่อออก
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        df_m = df_m.loc[:, ~df_m.columns.str.contains('^Unnamed')]
        df_r = df_r.loc[:, ~df_r.columns.str.contains('^Unnamed')]
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ระบบหาแผ่นงาน 'masters' หรือ 'research' ไม่พบ")
        st.info("กรุณาเปลี่ยนชื่อ Tab ใน Google Sheets ให้เป็นภาษาอังกฤษตามที่นินแนะนำนะคะ")
        st.stop()

df_master, df_research = load_data()

# ตรวจสอบคอลัมน์สำคัญ (Name-surname คือคอลัมน์ที่ 3 ในไฟล์จริงของคุณ)
if 'Name-surname' not in df_master.columns:
    st.error("❌ หาหัวตาราง 'Name-surname' ไม่เจอ")
    st.stop()

# --- 3. ส่วนควบคุม (Sidebar) ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    
    st.divider()
    # ดึงปีจากคอลัมน์ 'ปี' ในไฟล์ research
    all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist()) if not df_research.empty else [2567, 2568]
    year_option = st.selectbox("เลือกปี พ.ศ.", ["แสดงทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูลวิจัยตามปี
df_filtered = df_research.copy()
if year_option != "แสดงทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้าที่ 1: รายงาน KPI (อิงตามไฟล์จริง)
# =========================
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงานวิจัย ปี {year_option}")

    # 1. เตรียมรายชื่อหลักสูตรทั้งหมด 21 หลักสูตรจากหน้า masters
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_df = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    # 2. แมปคณะ
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_df["คณะ"] = prog_df["หลักสูตร"].map(fac_map)
    
    # 3. คำนวณคะแนนรวม
    # เชื่อมผลงานวิจัยกับข้อมูลหลักสูตรอาจารย์
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], 
                                    left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_agg = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    
    prog_df = prog_df.merge(res_agg, on="หลักสูตร", how="left").fillna(0)
    
    # 4. สูตรคำนวณ KPI (Logic ตามที่คุณต้องการ)
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

    def calculate_kpi(row):
        p = row["หลักสูตร"]
        n = staff_counts.get(p, 1) # จำนวนอาจารย์ในหลักสูตร
        # ค่า X ตามประเภทหลักสูตร
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        
        # สูตร: (((คะแนนรวม/จำนวนอาจารย์)*100)/X)*5
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    prog_df["คะแนน KPI"] = prog_df.apply(calculate_kpi, axis=1)
    prog_df = prog_df.sort_values(["คณะ", "หลักสูตร"])

    # แสดงกราฟ
    fig = px.bar(prog_df, x="คะแนน KPI", y="หลักสูตร", color="คณะ", 
                 orientation='h', height=800, title="ความก้าวหน้า KPI รายหลักสูตร")
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)

    # แสดงตาราง
    st.write("### 📋 ข้อมูลรายละเอียดรายหลักสูตร")
    st.dataframe(prog_df[["คณะ", "หลักสูตร", "คะแนน", "คะแนน KPI"]].rename(columns={"คะแนน": "คะแนนสะสม"}), use_container_width=True)

# =========================
# หน้าที่ 2: บันทึกผลงาน
# =========================
else:
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: t = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        
        b = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        a = st.multiselect("เลือกผู้เขียน (อาจารย์)", df_master["Name-surname"].dropna().unique())
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if t and a:
                scores = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
                new_data = pd.DataFrame([{"ชื่อเรื่อง": t, "ปี": y, "ฐานวารสาร": b, "คะแนน": scores[b], "ผู้เขียน": i} for i in a])
                
                # อัปเดตกลับไปยัง Google Sheets
                df_updated = pd.concat([df_research, new_data], ignore_index=True)
                conn.update(worksheet="research", data=df_updated)
                
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("⚠️ กรุณาระบุชื่อเรื่องและเลือกผู้เขียน")
