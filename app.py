import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. การเชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงข้อมูลจาก Tab ชื่อ 'masters' และ 'research'
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างช่องว่างในชื่อคอลัมน์
        df_m.columns = df_m.columns.str.strip()
        df_r.columns = df_r.columns.str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ระบบหาข้อมูลไม่พบ หรือชื่อ Tab ไม่ถูกต้อง")
        st.info("คำแนะนำ: ตรวจสอบว่าใน Google Sheets ตั้งชื่อแผ่นงานว่า 'masters' และ 'research' หรือยัง?")
        st.stop()

df_master, df_research = load_data()

# ตรวจสอบชื่อคอลัมน์ตามไฟล์จริงที่คุณส่งมา
if 'Name-surname' not in df_master.columns:
    st.error(f"❌ หาคอลัมน์ 'Name-surname' ไม่เจอ (ตรวจพบ: {list(df_master.columns)})")
    st.stop()

# --- 3. ส่วนควบคุม Side Bar ---
with st.sidebar:
    st.title("📌 เมนูระบบ")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    
    st.divider()
    all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist()) if not df_research.empty else []
    year_option = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])

# กรองข้อมูล
df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# --- 4. หน้าแสดงผล KPI (21 หลักสูตร) ---
if menu == "📊 รายงาน KPI":
    st.title(f"📊 สรุปผลการดำเนินงาน ปี {year_option}")
    
    # ดึงรายชื่อหลักสูตรทั้งหมดจากหน้า masters
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_df = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    # แมป คณะ
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_df["คณะ"] = prog_df["หลักสูตร"].map(fac_map)
    
    # คำนวณคะแนน
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_sum = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    prog_df = prog_df.merge(res_sum, on="หลักสูตร", how="left").fillna(0)
    
    # สูตร KPI
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = staff_counts.get(p, 1)
        x = 60 if p == "Ph.D-Admin" else (40 if p in ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"] else 20)
        score = (((row["คะแนน"] / n) * 100) / x) * 5
        return round(min(score, 5.0), 2)

    prog_df["คะแนน KPI"] = prog_df.apply(calc_kpi, axis=1)
    
    # กราฟ
    fig = px.bar(prog_df, x="คะแนน KPI", y="หลักสูตร", orientation='h', color="คณะ", height=800)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(prog_df, use_container_width=True)

# --- 5. หน้าบันทึกผลงาน ---
else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("ชื่อเรื่อง")
        y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        b = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        a = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].dropna().unique())
        
        if st.form_submit_button("💾 บันทึก"):
            if t and a:
                scores = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
                new_data = pd.DataFrame([{"ชื่อเรื่อง": t, "ปี": y, "ฐานวารสาร": b, "คะแนน": scores[b], "ผู้เขียน": i} for i in a])
                conn.update(worksheet="research", data=pd.concat([df_research, new_data], ignore_index=True))
                st.success("บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
