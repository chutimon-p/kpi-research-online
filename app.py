import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ==========================================
# 1. การตั้งค่าหน้าเว็บและสไตล์
# ==========================================
st.set_page_config(page_title="ระบบบริหารจัดการผลงานวิจัย", layout="wide")

st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# กำหนดรหัสผ่าน Admin
ADMIN_PASSWORD = "admin1234"
MASTER_FILE = "masters.csv"
RESEARCH_FILE = "research.csv"

# เกณฑ์คะแนน
SCORE_MAP = {
    "TCI1": 0.8, "TCI2": 0.6,
    "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0,
}

# ==========================================
# 2. ฟังก์ชันจัดการระบบ Login & Data
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

@st.cache_data(ttl=60)
def load_data(file_path, default_cols):
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=default_cols)
    for enc in ["utf-8-sig", "cp874", "tis-620", "utf-8"]:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            df.columns = df.columns.str.strip() 
            return df
        except:
            continue
    return pd.DataFrame(columns=default_cols)

df_master = load_data(MASTER_FILE, ["Name-surname", "หลักสูตร", "คณะ"])
df_research = load_data(RESEARCH_FILE, ["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

# ==========================================
# 3. Sidebar และการเข้าสู่ระบบ
# ==========================================
with st.sidebar:
    st.title("📌 ระบบวิจัย")
    menu_options = ["📊 รายงานและ KPI"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ บันทึกผลงาน")
        menu_options.append("⚙️ จัดการข้อมูล")
    
    menu = st.radio("เลือกหน้าจอ", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("รหัสผ่าน Admin", type="password")
        if st.button("เข้าสู่ระบบ"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("รหัสผ่านผิด")
    else:
        if st.button("ออกจากระบบ"):
            st.session_state.logged_in = False
            st.rerun()

    # ตัวกรองปี (ใช้สำหรับกรองตารางสรุป แต่กราฟคณะจะใช้ข้อมูลทั้งหมดเพื่อเปรียบเทียบปี)
    if not df_research.empty:
        all_years = sorted(df_research["ปี"].unique().tolist())
        year_option = st.selectbox("🔍 กรองข้อมูลปี พ.ศ. (สำหรับตาราง)", ["ทั้งหมด"] + [str(y) for y in all_years])
    else: year_option = "ทั้งหมด"

df_filtered = df_research.copy()
if year_option != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

# ==========================================
# 4. หน้าจอ: รายงานและ KPI
# ==========================================
if menu == "📊 รายงานและ KPI":
    st.title(f"📊 สรุปผลการดำเนินงาน")
    
    if df_master.empty:
        st.error("ไม่พบข้อมูลอาจารย์ในระบบ")
    else:
        # เชื่อมข้อมูลวิจัยกับข้อมูล Master (คณะ)
        res_with_prog = df_research.merge(df_master[['Name-surname', 'คณะ']], 
                                         left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        t1, t2 = st.tabs(["👤 รายบุคคล (เจาะลึก)", "🏛 รายคณะ (เปรียบเทียบปี)"])
        
        with t1:
            st.subheader(f"📋 สรุปผลงานรายบุคคล ({year_option})")
            if not df_filtered.empty:
                p_report = df_filtered.groupby("ผู้เขียน").agg(
                    จำนวนเรื่อง=("ชื่อเรื่อง", "count"),
                    คะแนนสะสม=("คะแนน", "sum")
                ).reset_index().sort_values("คะแนนสะสม", ascending=False)
                
                st.dataframe(p_report, use_container_width=True, hide_index=True)
                
                st.divider()
                selected_author = st.selectbox("เลือกชื่ออาจารย์เพื่อดูรายละเอียด:", ["-- เลือกรายชื่อ --"] + p_report["ผู้เขียน"].tolist())
                if selected_author != "-- เลือกรายชื่อ --":
                    st.success(f"📌 รายละเอียดผลงานของ: {selected_author}")
                    detail_df = df_filtered[df_filtered["ผู้เขียน"] == selected_author][["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน"]]
                    st.table(detail_df)
            else:
                st.info("ไม่มีข้อมูลผลงาน")

        with t2:
            st.subheader("🏛 คะแนนสะสมถ่วงน้ำหนักแยกตามคณะและปี พ.ศ.")
            if "คณะ" in res_with_prog.columns and not df_research.empty:
                # จัดกลุ่มข้อมูลตาม ปี และ คณะ เพื่อทำกราฟแท่ง
                # ใช้ drop_duplicates เพื่อไม่ให้นับคะแนนซ้ำหากหนึ่งเรื่องมีผู้เขียนหลายคนในคณะเดียวกัน
                fac_year_data = res_with_prog.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]).groupby(["ปี", "คณะ"])["คะแนน"].sum().reset_index()
                
                # ตรวจสอบว่า "ปี" เป็นตัวเลขเพื่อให้แกน X เรียงลำดับถูกต้อง
                fac_year_data["ปี"] = fac_year_data["ปี"].astype(str)
                
                # สร้างกราฟแท่งเปรียบเทียบ
                fig_fac = px.bar(
                    fac_year_data, 
                    x="ปี", 
                    y="คะแนน", 
                    color="คณะ",
                    barmode="group",
                    labels={"คะแนน": "ค่าถ่วงน้ำหนักสะสม", "ปี": "ปี พ.ศ."},
                    title="เปรียบเทียบคะแนนสะสมรายคณะแยกตามปี พ.ศ.",
                    text_auto='.2f'
                )
                
                fig_fac.update_layout(xaxis_title="ปี พ.ศ.", yaxis_title="คะแนนสะสมถ่วงน้ำหนัก")
                st.plotly_chart(fig_fac, use_container_width=True)
                
                # แสดงตารางข้อมูลประกอบกราฟ
                st.write("📋 **ตารางสรุปคะแนนรายคณะ**")
                st.dataframe(fac_year_data.pivot(index='คณะ', columns='ปี', values='คะแนน').fillna(0), use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลเพียงพอสำหรับแสดงกราฟรายคณะ")

# ==========================================
# 5. หน้าจอ Protected (ต้อง Login)
# ==========================================
elif menu == "✍️ บันทึกผลงาน":
    st.title("✍️ บันทึกผลงานใหม่")
    with st.form("research_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1: title = st.text_input("ชื่อเรื่องงานวิจัย")
        with col2: year = st.number_input("ปีที่ตีพิมพ์ (พ.ศ.)", 2560, 2600, 2568)
        col3, col4 = st.columns(2)
        with col3: journal = st.selectbox("ฐานวารสาร", list(SCORE_MAP.keys()))
        with col4: authors = st.multiselect("เลือกผู้เขียน", df_master["Name-surname"].unique().tolist() if not df_master.empty else [])
        if st.form_submit_button("💾 บันทึก"):
            if title and authors:
                new_rows = [{"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": journal, "คะแนน": SCORE_MAP[journal], "ผู้เขียน": a} for a in authors]
                df_updated = pd.concat([df_research, pd.DataFrame(new_rows)], ignore_index=True)
                df_updated.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
                st.success("บันทึกสำเร็จ!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ จัดการข้อมูล":
    st.title("⚙️ จัดการข้อมูล")
    if not df_research.empty:
        to_delete = st.selectbox("เลือกเรื่องที่จะลบ", df_research["ชื่อเรื่อง"].unique())
        if st.button("🗑 ยืนยันการลบ"):
            df_new = df_research[df_research["ชื่อเรื่อง"] != to_delete]
            df_new.to_csv(RESEARCH_FILE, index=False, encoding="utf-8-sig")
            st.success("ลบสำเร็จ")
            st.cache_data.clear()
            st.rerun()
