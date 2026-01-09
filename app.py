import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d8e0; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Google Sheets ---
if "connections" not in st.secrets or "gsheets" not in st.secrets.connections:
    st.error("❌ ไม่พบการตั้งค่า Secrets")
    st.info("กรุณาตรวจสอบว่าในหน้า Settings > Secrets ได้วางโค้ด [connections.gsheets] พร้อม URL ของไฟล์แล้ว")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจาก Tab: masters และ research
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        if "400" in str(e):
            st.warning("💡 คำแนะนำ: ตรวจสอบว่าแชร์ไฟล์ Google Sheets เป็น 'Anyone with the link' หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# --- 3. ส่วนควบคุม Side Bar ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    st.divider()
    
    # ดึงปี พ.ศ. จากข้อมูลวิจัย
    if not df_research.empty and 'ปี' in df_research.columns:
        all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist())
        year_option = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])
    else:
        year_option = "ทั้งหมด"

# --- 4. หน้าที่ 1: รายงาน KPI (คำนวณจากอาจารย์ 162 ท่าน) ---
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงานวิจัย ปี {year_option}")
    
    # กรองข้อมูลตามปี
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

    # ประมวลผลหลักสูตรและคะแนน
    # ดึงรายชื่อหลักสูตรทั้งหมดที่มีในระบบ
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_df = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    # แมปคณะให้แต่ละหลักสูตร
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_df["คณะ"] = prog_df["หลักสูตร"].map(fac_map)
    
    # รวมคะแนนจากหน้า Research โดยเชื่อมผ่านชื่ออาจารย์
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_agg = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    
    prog_df = prog_df.merge(res_agg, on="หลักสูตร", how="left").fillna(0)
    
    # นับจำนวนอาจารย์รายหลักสูตร
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = staff_counts.get(p, 1) # จำนวนอาจารย์
        # ค่า X ตามกลุ่มหลักสูตร (Logic: PhD=60, Master/Dip=40, Other=20)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        
        # สูตร: (((คะแนนรวม/จำนวนอาจารย์)*100)/X)*5
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    prog_df["คะแนน KPI"] = prog_df.apply(calc_kpi, axis=1)
    prog_df = prog_df.sort_values("คะแนน KPI", ascending=False)
    
    # กราฟแท่ง
    fig = px.bar(prog_df, x="คะแนน KPI", y="หลักสูตร", color="คณะ", 
                 orientation='h', height=800, text="คะแนน KPI",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)
    
    st.write("### 📋 ตารางสรุปผลงานรายหลักสูตร")
    st.dataframe(prog_df, use_container_width=True)

# --- 5. หน้าที่ 2: บันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานวิจัยใหม่")
    st.info("กรอกข้อมูลด้านล่างเพื่อบันทึกข้อมูลลงในหน้า 'research' ของ Google Sheets")
    
    with st.form("research_form", clear_on_submit=True):
        title = st.text_input("ชื่อเรื่องงานวิจัย")
        
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        with col2:
            score_dict = {"TCI 1": 0.8, "TCI 2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
            journal = st.selectbox("ฐานวารสาร", list(score_dict.keys()))
            
        # เลือกอาจารย์จากรายชื่อที่มีในหน้า masters
        all_authors = sorted(df_master["Name-surname"].dropna().unique().tolist())
        selected_authors = st.multiselect("เลือกผู้เขียน (อาจารย์)", all_authors)
        
        external = st.text_input("ผู้เขียนภายนอก (ถ้ามี)")

        if st.form_submit_button("💾 บันทึกข้อมูล"):
            if title and selected_authors:
                # สร้างข้อมูลใหม่เพื่อ append
                new_data = []
                for auth in selected_authors:
                    new_data.append({
                        "ชื่อเรื่อง": title,
                        "ปี": year,
                        "ฐานวารสาร": journal,
                        "คะแนน": score_dict[journal],
                        "ผู้เขียน": auth,
                        "ผู้เขียนภายนอก": external
                    })
                
                # รวมข้อมูลและอัปเดต
                new_df = pd.DataFrame(new_data)
                updated_df = pd.concat([df_research, new_df], ignore_index=True)
                
                conn.update(worksheet="research", data=updated_df)
                
                st.success("✅ บันทึกสำเร็จ!")
                st.cache_data.clear() # ล้างแคชเพื่อให้กราฟอัปเดตทันที
                st.rerun()
            else:
                st.error("⚠️ กรุณากรอกชื่อเรื่องและเลือกผู้เขียน")
