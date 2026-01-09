import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

# เพิ่มฟอนต์ Sarabun และปรับแต่ง CSS
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลแยกตามชื่อ Worksheet (ต้องตั้งชื่อใน Google Sheets ว่า masters และ research)
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
            
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        st.info("คำแนะนำ: ตรวจสอบว่าใน Google Sheets มีแผ่นงาน (Tab) ชื่อ 'masters' และ 'research' หรือไม่ และตั้งค่า Secrets ถูกต้องหรือไม่")
        st.stop()

df_master, df_research = load_data()

# ตรวจสอบหัวตารางพื้นฐาน
if 'Name-surname' not in df_master.columns:
    st.error(f"ไม่พบหัวตาราง 'Name-surname' ในหน้า masters")
    st.stop()

# --- 3. ส่วนเมนู Sidebar ---
with st.sidebar:
    st.title("📌 เมนูระบบ")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    st.divider()
    
    # ดึงปีจากข้อมูลจริงในหน้า research
    if not df_research.empty and 'ปี' in df_research.columns:
        all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist())
        year_option = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])
    else:
        year_option = "ทั้งหมด"

# --- 4. หน้าที่ 1: รายงาน KPI ---
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงานวิจัย ปี {year_option}")
    
    # กรองตามปี
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

    # ประมวลผลหลักสูตร
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_df = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_df["คณะ"] = prog_df["หลักสูตร"].map(fac_map)
    
    # รวมคะแนน
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_agg = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    prog_df = prog_df.merge(res_agg, on="หลักสูตร", how="left").fillna(0)
    
    # สูตร KPI (นับจำนวนอาจารย์รายหลักสูตรจากหน้า masters)
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = staff_counts.get(p, 1)
        # ค่า X ตามเกณฑ์กลุ่มหลักสูตร
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    prog_df["คะแนน KPI"] = prog_df.apply(calc_kpi, axis=1)
    prog_df = prog_df.sort_values("คะแนน KPI", ascending=False)
    
    # แสดงกราฟ
    fig = px.bar(prog_df, x="คะแนน KPI", y="หลักสูตร", color="คณะ", 
                 orientation='h', height=800, text="คะแนน KPI")
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)
    
    # แสดงตารางข้อมูล
    st.dataframe(prog_df, use_container_width=True)

# --- 5. หน้าที่ 2: บันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานใหม่")
    st.info("ระบบจะบันทึกข้อมูลไปยังแผ่นงาน 'research' ใน Google Sheets โดยตรง")
    
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2:
            new_year = st.number_input("ปี พ.ศ. (ที่ตีพิมพ์)", 2560, 2600, 2568)
            
        col3, col4 = st.columns(2)
        with col3:
            # รายชื่อฐานวารสารตามเกณฑ์คะแนน
            score_map = {
                "TCI 1": 0.8, "TCI 2": 0.6, 
                "Scopus Q1": 1.0, "Scopus Q2": 1.0, 
                "Scopus Q3": 1.0, "Scopus Q4": 1.0
            }
            new_journal = st.selectbox("ฐานวารสาร / ระดับ", list(score_map.keys()))
        with col4:
            # ดึงรายชื่ออาจารย์จาก masters มาให้เลือก
            author_list = sorted(df_master["Name-surname"].dropna().unique().tolist())
            selected_authors = st.multiselect("เลือกผู้เขียน (อาจารย์)", author_list)
            
        new_external = st.text_input("ผู้เขียนภายนอก (ถ้ามี)")

        if st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets"):
            if new_title and selected_authors:
                # เตรียมข้อมูลสำหรับเพิ่มเข้าไป
                new_entries = []
                for author in selected_authors:
                    new_entries.append({
                        "ชื่อเรื่อง": new_title,
                        "ปี": new_year,
                        "ฐานวารสาร": new_journal,
                        "คะแนน": score_map[new_journal],
                        "ผู้เขียน": author,
                        "ผู้เขียนภายนอก": new_external
                    })
                
                # รวมข้อมูลเก่าและใหม่
                new_data_df = pd.DataFrame(new_entries)
                updated_research = pd.concat([df_research, new_data_df], ignore_index=True)
                
                # ส่งข้อมูลกลับไปที่ Google Sheets
                conn.update(worksheet="research", data=updated_research)
                
                st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว!")
                st.balloons()
                # ล้างแคชเพื่อให้เห็นข้อมูลใหม่ทันที
                st.cache_data.clear()
            else:
                st.error("⚠️ กรุณากรอกชื่อเรื่องและเลือกผู้เขียนอย่างน้อย 1 ท่าน")
