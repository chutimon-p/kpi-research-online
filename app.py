import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import math

# ==========================================
# 1. Database Connection & Error Handling
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
        st.error(f"❌ Connection Failed: Please check secrets/credentials. Error: {e}")
        return None

@st.cache_data(ttl=300) 
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database") 
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip() # ล้างช่องว่างที่หัวคอลัมน์
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(list(new_row_dict.values()))
            return True
        except Exception as e:
            st.error(f"❌ Save Failed: {e}")
            return False
    return False

# ==========================================
# 2. UI Configuration (Times New Roman & TH Sarabun)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
    /* ฟอนต์หลัก: อังกฤษใช้ Times New Roman, ไทยใช้ Sarabun */
    html, body, [class*="css"], .stMarkdown, p, div {
        font-family: 'Times New Roman', 'Sarabun', serif !important;
        color: #1E293B;
    }

    .stApp { background-color: #FFFFFF; }

    /* ปรับแต่ง Tab ให้เด่นชัดและใหญ่ตามที่คุณต้องการ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #F8FAFC;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 65px; 
        min-width: 170px;
        background-color: #FFFFFF;
        border-radius: 8px;
        color: #475569;
        font-size: 1.4rem !important; 
        font-weight: 700 !important;
        font-family: 'Times New Roman', serif !important;
        border: 1px solid #CBD5E1;
        transition: all 0.2s ease;
    }

    /* Tab เมื่อถูกเลือก */
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important; 
        color: #FFFFFF !important;
        font-size: 1.5rem !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(30, 58, 138, 0.2);
    }

    /* ปรับแต่ง Metric */
    [data-testid="stMetricValue"] { 
        font-size: 2.5rem; 
        color: #1E3A8A; 
        font-weight: 800;
        font-family: 'Times New Roman', sans-serif;
    }
    
    .stMetric {
        background-color: #F1F5F9; 
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #E2E8F0;
    }

    h1, h2, h3, h4 { 
        color: #1E3A8A !important; 
        font-weight: 800;
        font-family: 'Times New Roman', 'Sarabun', serif !important;
    }

    /* ปรับขนาดตัวหนังสือในตารางให้ชัดเจน */
    [data-testid="stTable"], .stDataFrame {
        font-size: 1.1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Header Setup
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try: st.image("logo.jpg", width=130)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="margin-bottom: 0px; font-size: 2.8rem;">St Teresa International University</h1>
            <p style="color: #64748B; font-size: 1.3rem; font-weight: 600;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 3. Data Processing
# ==========================================
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("🔄 Connecting to Google Sheets... Please ensure the file is shared with the Service Account.")
    st.stop()

# ทำความสะอาดข้อมูลเพื่อป้องกัน Error การคำนวณ
df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 4. Sidebar & Navigation
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
with st.sidebar:
    st.markdown("### 🧭 NAVIGATION")
    menu_options = ["📊 DASHBOARD"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ SUBMIT")
        menu_options.append("⚙️ MANAGE")
    menu = st.radio("Select Page:", menu_options)
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
            else: st.error("❌ Wrong Password")
    else:
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
    
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Filter Year (B.E.):", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Page Content: DASHBOARD
# ==========================================
if menu == "📊 DASHBOARD":
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # รวมข้อมูล Master กับ Research
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    df_u_total = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    df_u_agency = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])

    # แถบเมนูภาษาอังกฤษ ตัวหนา ชัดเจน
    tabs = st.tabs(["OVERVIEW", "PROGRAM KPI", "RESEARCHER PROFILE", "FACULTY KPI", "IMPROVEMENT PLAN"])

    with tabs[0]:
        st.markdown("### 📈 Publication Growth")
        summary = df_u_total.groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Score=("คะแนน", "sum")).reset_index()
        summary = summary[summary['ปี'] > 0].sort_values("ปี")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary["ปี"], y=summary["Titles"], name="Publications", marker_color='#1E3A8A'))
        fig.add_trace(go.Scatter(x=summary["ปี"], y=summary["Score"], name="Weighted Score", yaxis="y2", line=dict(color='#F43F5E', width=4)))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.markdown("### 🎓 Program KPI Achievement")
        # เตรียมข้อมูล KPI รายหลักสูตร
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[all_progs["หลักสูตร"] != ""]
        prog_n = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_sum = df_u_agency.groupby("หลักสูตร").agg(Total_Weight=("คะแนน", "sum")).reset_index()
        prog_rep = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)
        
        def calc_kpi(row):
            n = prog_n.get(row["หลักสูตร"], 1)
            g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in g40 else 20)
            return round(min((((row["Total_Weight"] / n) * 100) / x) * 5, 5.0), 2)
        
        prog_rep["KPI Score"] = prog_rep.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_rep.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📄 Detailed Program KPI Summary Table")
        st.dataframe(prog_rep.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown("### 🏆 Top Researchers")
        rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        cols = st.columns(3)
        for i, medal in enumerate(["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]):
            if i < len(rank):
                row = rank.iloc[i]
                cols[i].metric(medal, row["ผู้เขียน"], f"Score: {row['คะแนน']:.2f}")
        st.divider()
        st.markdown("#### 🔍 Researcher Database Lookup")
        st.dataframe(df_u_total[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("### 🏢 Faculty KPI Performance")
        fac_n = df_master.groupby("คณะ")["Name-surname"].nunique().to_dict()
        fac_sum = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ']).groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        def calc_fac_kpi(row):
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            n = fac_n.get(row["คณะ"], 1)
            return round(min((((row["Total_Score"] / n) * 100) / y) * 5, 5.0), 2)
        
        fac_sum["Faculty KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_sum.sort_values("Faculty KPI Score"), x="Faculty KPI Score", y="คณะ", orientation='h', range_x=[0, 5.5], text="Faculty KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📄 Detailed Faculty KPI Summary Table")
        st.dataframe(fac_sum.sort_values("Faculty KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with tabs[4]:
        st.markdown("### 🚀 KPI Improvement Plan (Road to 5.0)")
        p_mode = st.radio("Target Level:", ["By Program", "By Faculty"], horizontal=True)
        
        def run_plan(name, curr_s, n, x_y):
            req_s = (x_y * n) / 100
            gap = max(req_s - curr_s, 0.0)
            st.subheader(f"Target: {name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Points Needed", f"{gap:.2f}")
            c2.metric("Staff Count (n)", n)
            c3.metric("Goal Weight", f"{req_s:.2f}")
            if gap > 0:
                st.info(f"💡 Need **{gap:.2f}** more weight points to reach KPI 5.0")
                st.markdown(f"* **Scopus (1.0):** {math.ceil(gap/1.0)} papers")
                st.markdown(f"* **TCI 1 (0.8):** {math.ceil(gap/0.8)} papers")
                st.markdown(f"* **TCI 2 (0.6):** {math.ceil(gap/0.6)} papers")
            else: st.success("✅ KPI 5.0 Goal Already Achieved!")

        if p_mode == "By Program":
            sel = st.selectbox("Choose Program:", sorted(df_master["หลักสูตร"].unique().tolist()))
            if sel:
                curr = df_u_agency[df_u_agency["หลักสูตร"] == sel]["คะแนน"].sum()
                n = df_master[df_master["หลักสูตร"] == sel]["Name-surname"].nunique()
                g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x = 60 if sel == "Ph.D-Admin" else (40 if sel in g40 else 20)
                run_plan(sel, curr, n, x)
        else:
            sel = st.selectbox("Choose Faculty:", sorted(df_master["คณะ"].unique().tolist()))
            if sel:
                curr = df_full[df_full["คณะ"] == sel].drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])["คะแนน"].sum()
                n = df_master[df_master["คณะ"] == sel]["Name-surname"].nunique()
                y = 30 if sel in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                run_plan(sel, curr, n, y)

# ==========================================
# 6. Admin: SUBMIT & MANAGE
# ==========================================
elif menu == "✍️ SUBMIT":
    st.markdown("### ✍️ Register New Research Publication")
    with st.form("form_submit", clear_on_submit=True):
        title = st.text_input("Research Title")
        c1, c2 = st.columns(2)
        year = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
        db = c2.selectbox("Journal Database", list(SCORE_MAP.keys()))
        authors = st.multiselect("Select Authors", sorted(df_master["Name-surname"].unique().tolist()))
        if st.form_submit_button("Save Record"):
            if title and authors:
                for a in authors:
                    save_to_sheet("research", {"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": a})
                st.success("✅ Success! Record saved to database."); st.cache_data.clear(); st.rerun()
            else: st.error("⚠️ Please fill in all fields.")

elif menu == "⚙️ MANAGE":
    st.markdown("### ⚙️ Database Management (Delete Record)")
    df_m = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี'])
    sel = st.selectbox("Select Record to Delete:", ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_m.iterrows()])
    if sel != "-- Select --" and st.button("Confirm Delete"):
        target_title = sel.split(" | ")[1].strip()
        ws = conn_sheets().open("Research_Database").worksheet("research")
        all_recs = ws.get_all_records()
        rows_to_del = [i + 2 for i, r in enumerate(all_recs) if str(r.get('ชื่อเรื่อง')).strip() == target_title]
        for r in sorted(rows_to_del, reverse=True):
            ws.delete_rows(r)
        st.success("🗑️ Record deleted successfully!"); st.cache_data.clear(); st.rerun()
