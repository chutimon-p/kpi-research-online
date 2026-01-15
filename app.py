import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. Database Connection
# ==========================================
@st.cache_resource
def conn_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database") 
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            # ล้างช่องว่างที่หัวตารางและจัดการอักขระพิเศษ
            df.columns = [str(c).strip().replace('\xa0', ' ') for c in df.columns]
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. Page Configuration & Style
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try: st.image("logo.jpg", width=140)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="color: #1E3A8A; margin-bottom: 0px;">St Teresa International University</h1>
            <p style="color: #64748b; font-size: 1.1rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

# Data Cleaning
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
df_research['ผู้เขียน'] = df_research['ผู้เขียน'].astype(str).str.strip()
df_master['Name-surname'] = df_master['Name-surname'].astype(str).str.strip()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("Go to Page:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Wrong Password")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 Performance Overview: {year_option}")
    
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # ดึงข้อมูลสังกัดมาไว้ในตารางงานวิจัย
    df_full_info = df_filtered.merge(
        df_master[['Name-surname', 'คณะ', 'หลักสูตร']], 
        left_on="ผู้เขียน", 
        right_on="Name-surname", 
        how="left"
    )
    
    # นับจำนวนอาจารย์ n จาก Master (นับทุกคนตามที่ระบุ)
    prog_member_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    fac_member_counts = df_master.groupby("คณะ")["Name-surname"].nunique().to_dict()

    m1, m2, m3 = st.columns(3)
    unique_titles_summary = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    m1.metric("Total Publications", f"{len(unique_titles_summary)} Titles")
    m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
    m3.metric("Weighted Score Sum", f"{unique_titles_summary['คะแนน'].sum():.2f}")

    t0, t1, t2, t3, t4 = st.tabs(["🏛 Overview", "🎓 Program KPI", "👤 Researcher Profile", "🏢 Faculty KPI", "📋 Master Database"])

    with t0:
        st.markdown("#### 🌍 University Growth")
        inst_summary = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(
            Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")
        ).reset_index().sort_values("ปี")
        inst_summary = inst_summary[inst_summary['ปี'] > 0]
        
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Titles"], name="Titles", marker_color='#1E3A8A'))
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="Weight", yaxis="y2", line=dict(color='#ef4444', width=3)))
        fig_inst.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig_inst, use_container_width=True)

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement")
        # เตรียมรายชื่อหลักสูตรทั้งหมด
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        
        prog_unique_res = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_summary = prog_unique_res.groupby("หลักสูตร").agg(
            Total_Score=("คะแนน", "sum"), 
            Total_Titles=("ชื่อเรื่อง", "count")
        ).reset_index()
        
        prog_report = all_progs.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(min(score, 5.0), 2)

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        
        fig_prog = px.bar(prog_report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="KPI Score", height=600, template="plotly_white")
        fig_prog.add_vline(x=5.0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_prog, use_container_width=True)
        st.dataframe(prog_report.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 👤 Researcher Portfolio")
        search_author = st.selectbox("🔍 Select Researcher:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- Select --":
            author_works = df_filtered[df_filtered["ผู้เขียน"] == search_author].copy().sort_values("ปี", ascending=False)
            if not author_works.empty:
                c1, c2 = st.columns([1, 3])
                c1.metric("Works", len(author_works))
                c1.metric("Score", f"{author_works['คะแนน'].sum():.2f}")
                c2.dataframe(author_works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)
            else:
                st.info("No records found for this researcher in the selected year.")

    with t3:
        st.markdown("#### 🏢 Faculty KPI Performance")
        if not df_full_info.empty:
            res_fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
            fac_sum = res_fac_unique.groupby("คณะ").agg(
                Total_Score=("คะแนน", "sum"), 
                Total_Titles=("ชื่อเรื่อง", "count")
            ).reset_index()

            def calc_fac_kpi(row):
                f_name = row["คณะ"]
                n = fac_member_counts.get(f_name, 1)
                y = 30 if f_name in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                score = (((row["Total_Score"] / n) * 100) / y) * 5
                return round(min(score, 5.0), 2)

            fac_sum["Faculty KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
            
            fig_fac = px.bar(fac_sum.sort_values("Faculty KPI Score"), x="Faculty KPI Score", y="คณะ", orientation='h', range_x=[0, 5.5], text="Faculty KPI Score", color="คณะ", template="plotly_white")
            fig_fac.add_vline(x=5.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_fac, use_container_width=True)
            st.dataframe(fac_sum.sort_values("Faculty KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t4:
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin Sections
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Title").strip()
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        with c2: j_in = st.selectbox("Journal Database", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("Save Record"):
            if t_in and a_in:
                for a in a_in: 
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("Saved!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    if not df_research.empty:
        df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']).sort_values(by=['ปี', 'ชื่อเรื่อง'], ascending=[False, True])
        st.dataframe(df_manage[['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร']], use_container_width=True, hide_index=True)
        opts = ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']} | {r['ฐานวารสาร']}" for _, r in df_manage.iterrows()]
        sel = st.selectbox("Delete Entry:", opts)
        if sel != "-- Select --":
            target = sel.split(" | ")[1].strip()
            if st.button("Confirm Delete"):
                with st.spinner("Deleting..."):
                    ws = conn_sheets().open("Research_Database").worksheet("research")
                    rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
                    for r in sorted(rows, reverse=True): ws.delete_rows(r)
                    st.success("Deleted!"); st.cache_data.clear(); time.sleep(1); st.rerun()
