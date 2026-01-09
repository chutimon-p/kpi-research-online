import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบสารสนเทศงานวิจัย", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูลแบบแยกแผ่น (แก้ปัญหา Series Error) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # ดึงแยกทีละแผ่นงานเพื่อให้ได้ DataFrame ที่ถูกต้อง
        df_m = conn.read(worksheet="masters")
        df_r = conn.read(worksheet="research")
        
        # ล้างหัวตาราง (กำจัดเว้นวรรค)
        if hasattr(df_m, 'columns'):
            df_m.columns = df_m.columns.str.strip()
        if hasattr(df_r, 'columns'):
            df_r.columns = df_r.columns.str.strip()
            
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
        st.info("กรุณาตรวจสอบว่าใน Google Sheets มีแผ่นงานชื่อ 'masters' และ 'research' (ตัวพิมพ์เล็ก) หรือไม่")
        st.stop()

df_master, df_research = load_data()

# --- 3. ส่วนควบคุม (Sidebar) ---
with st.sidebar:
    st.title("📌 ระบบบริหารงานวิจัย")
    menu = st.radio("เลือกหน้าจอ", ["📊 รายงาน KPI", "✍️ บันทึกผลงาน"])
    st.divider()
    
    # กรองปี พ.ศ.
    if not df_research.empty and 'ปี' in df_research.columns:
        all_years = sorted(df_research["ปี"].dropna().unique().astype(int).tolist())
        year_option = st.selectbox("เลือกปี พ.ศ.", ["ทั้งหมด"] + [str(y) for y in all_years])
    else:
        year_option = "ทั้งหมด"

# กรองข้อมูลวิจัย
df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# =========================
# หน้าที่ 1: รายงาน KPI (อิงตามไฟล์จริงของคุณ)
# =========================
if menu == "📊 รายงาน KPI":
    st.title(f"📊 รายงานสรุปผลงานวิจัย ปี {year_option}")

    # ดึงรายชื่อหลักสูตรทั้งหมด
    all_progs = df_master[df_master["หลักสูตร"].notna() & (df_master["หลักสูตร"] != "-")]["หลักสูตร"].unique()
    prog_df = pd.DataFrame(all_progs, columns=["หลักสูตร"])
    
    # แมปคณะ
    fac_map = df_master.drop_duplicates("หลักสูตร").set_index("หลักสูตร")["คณะ"].to_dict()
    prog_df["คณะ"] = prog_df["หลักสูตร"].map(fac_map)
    
    # รวมคะแนน
    df_merged = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    res_agg = df_merged.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
    prog_df = prog_df.merge(res_agg, on="หลักสูตร", how="left").fillna(0)
    
    # สูตร KPI
    staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    def calc_kpi(row):
        p = row["หลักสูตร"]
        n = staff_counts.get(p, 1)
        group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
        x_val = 60 if p == "Ph.D-Admin" else (40 if p in group_40 else 20)
        score = (((row["คะแนน"] / n) * 100) / x_val) * 5
        return round(min(score, 5.0), 2)

    prog_df["คะแนน KPI"] = prog_df.apply(calc_kpi, axis=1)
    
    # กราฟ
    fig = px.bar(prog_df, x="คะแนน KPI", y="หลักสูตร", color="คณะ", orientation='h', height=800)
    fig.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="เป้าหมาย 5.0")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(prog_df.sort_values("คะแนน KPI", ascending=False), use_container_width=True)

# =========================
# หน้าที่ 2: บันทึกผลงาน
# =========================
else:
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("ชื่อเรื่องงานวิจัย")
        y = st.number_input("ปี พ.ศ.", 2567, 2600, 2568)
        b = st.selectbox("ฐานวารสาร", ["TCI1", "TCI2", "Scopus Q1", "Scopus Q2", "Scopus Q3", "Scopus Q4"])
        a = st.multiselect("เลือกผู้เขียน (อาจารย์)", df_master["Name-surname"].dropna().unique())
        
        if st.form_submit_button("💾 บันทึก"):
            if t and a:
                scores_map = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
                new_data = pd.DataFrame([{"ชื่อเรื่อง": t, "ปี": y, "ฐานวารสาร": b, "คะแนน": scores_map[b], "ผู้เขียน": i} for i in a])
                conn.update(worksheet="research", data=pd.concat([df_research, new_data], ignore_index=True))
                st.success("บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()
