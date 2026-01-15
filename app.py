import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import math

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

@st.cache_data(ttl=600) 
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database") 
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip() 
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
# 2. UI Configuration (TH Sarabun & Times New Roman)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

# นำเข้าฟอนต์ TH Sarabun New จาก CDN
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700;800&display=swap" rel="stylesheet">
    <style>
    /* ตั้งค่าฟอนต์หลัก: ภาษาอังกฤษใช้ Times New Roman, ภาษาไทยใช้ Sarabun */
    html, body, [class*="css"], .stMarkdown, p, div {
        font-family: 'Times New Roman', 'Sarabun', serif !important;
        color: #1E293B;
    }

    /* พื้นหลังสีขาวสะอาด */
    .stApp { background-color: #FFFFFF; }

    /* ปรับแต่ง Tab ให้เด่นชัดและใช้ Times New Roman */
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
        font-size: 1.4rem !important; /* ใหญ่ชัดเจน */
        font-weight: 700 !important;
        font-family: 'Times New Roman', serif !important; /* บังคับใช้ Times New Roman สำหรับชื่อ Tab */
        border: 1px solid #CBD5E1;
        transition: all 0.2s ease;
    }

    /* สไตล์ Tab เมื่อถูกเลือก */
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

    /* ปรับแต่งตาราง */
    .styled-table { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# Header Section
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

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.stop()

df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar (Filters)
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
with st.sidebar:
    st.markdown("### 🧭 NAVIGATION")
    menu_options = ["📊 DASHBOARD"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ SUBMIT")
        menu_options.append("⚙️ MANAGE")
    menu = st.radio("Select Menu:", menu_options)
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
    else:
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
    
    years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_opt = st.selectbox("📅 Filter Year:", ["All Years"] + [str(y) for y in years])

# ==========================================
# 4. Dashboard & Tables
# ==========================================
if menu == "📊 DASHBOARD":
    df_filtered = df_research.copy()
    if year_opt != "All Years": df_filtered = df_filtered[df_filtered["ปี"] == int(year_opt)]
    
    df_full = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    df_u_total = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    df_u_agency = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])

    # Big Tabs
    t0, t1, t2, t3, t4 = st.tabs([
        "OVERVIEW", "PROGRAM KPI", "RESEARCHER", "FACULTY KPI", "IMPROVEMENT PLAN"
    ])

    with t0:
        st.markdown("### 📈 University Growth")
        summary = df_u_total.groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Score=("คะแนน", "sum")).reset_index()
        summary = summary[summary['ปี'] > 0].sort_values("ปี")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary["ปี"], y=summary["Titles"], name="Publications", marker_color='#1E3A8A'))
        fig.add_trace(go.Scatter(x=summary["ปี"], y=summary["Score"], name="Weighted Score", yaxis="y2", line=dict(color='#F43F5E', width=4)))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with t1:
        st.markdown("### 🎓 Program KPI Achievement")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[all_progs["หลักสูตร"] != ""]
        prog_n = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_sum = df_u_agency.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        prog_rep = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)
        
        def calc_kpi(row):
            n = prog_n.get(row["หลักสูตร"], 1)
            g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in g40 else 20)
            return round(min((((row["Total_Score"] / n) * 100) / x) * 5, 5.0), 2)
        
        prog_rep["KPI Score"] = prog_rep.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_rep.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📋 Detailed Program Summary")
        st.dataframe(prog_rep.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("### 🏆 Top Researchers")
        rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        cols = st.columns(3)
        medals = ["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]
        for i, (col, medal) in enumerate(zip(cols, medals)):
            if i < len(rank):
                row = rank.iloc[i]
                col.metric(medal, row["ผู้เขียน"], f"Total: {row['คะแนน']:.2f}")
        st.divider()
        st.markdown("#### 🔍 Full Publication Database")
        st.dataframe(df_u_total[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)

    with t3:
        st.markdown("### 🏢 Faculty KPI Performance")
        fac_n = df_master.groupby("คณะ")["Name-surname"].nunique().to_dict()
        fac_sum = df_full.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ']).groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        def calc_fac_kpi(row):
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            n = fac_n.get(row["คณะ"], 1)
            return round(min((((row["Total_Score"] / n) * 100) / y) * 5, 5.0), 2)
        
        fac_sum["Faculty KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_sum.sort_values("Faculty KPI Score"), x="Faculty KPI Score", y="คณะ", orientation='h', range_x=[0, 5.5], text="Faculty KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📋 Detailed Faculty Summary")
        st.dataframe(fac_sum.sort_values("Faculty KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t4:
        st.markdown("### 🚀 KPI Improvement Plan")
        plan_m = st.radio("Target:", ["By Program", "By Faculty"], horizontal=True)
        def run_p(name, curr_s, n, x_y):
            req = (x_y * n) / 100
            gap = max(req - curr_s, 0.0)
            kpi = min((((curr_s / n) * 100) / x_y) * 5, 5.0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Current KPI", f"{kpi:.2f}")
            c2.metric("Needed Score", f"{gap:.2f}")
            c3.metric("Staff (n)", n)
            if gap > 0:
                st.warning(f"💡 Additional Research Needed for KPI 5.0:")
                sc, tc = st.columns(2)
                sc.info(f"**Scopus (1.0)**: {math.ceil(gap/1.0)} papers")
                tc.info(f"**TCI 1 (0.8)**: {math.ceil(gap/0.8)} papers")
            else: st.success("✅ Goal Achieved!")

        if plan_m == "By Program":
            sel = st.selectbox("Select Program:", sorted(df_master["หลักสูตร"].unique().tolist()))
            if sel:
                curr = df_u_agency[df_u_agency["หลักสูตร"] == sel]["คะแนน"].sum()
                n = df_master[df_master["หลักสูตร"] == sel]["Name-surname"].nunique()
                g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x = 60 if sel == "Ph.D-Admin" else (40 if sel in g40 else 20)
                run_p(sel, curr, n, x)
        else:
            sel = st.selectbox("Select Faculty:", sorted(df_master["คณะ"].unique().tolist()))
            if sel:
                curr = df_full[df_full["คณะ"] == sel].drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])["คะแนน"].sum()
                n = df_master[df_master["คณะ"] == sel]["Name-surname"].nunique()
                y = 30 if sel in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                run_p(sel, curr, n, y)

# ==========================================
# 5. Admin (Submit & Manage)
# ==========================================
elif menu == "✍️ SUBMIT":
    st.markdown("### ✍️ Register New Publication")
    with st.form("f1", clear_on_submit=True):
        t = st.text_input("Publication Title")
        c1, c2 = st.columns(2)
        y = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
        db = c2.selectbox("Database", list(SCORE_MAP.keys()))
        auths = st.multiselect("Select Authors", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("Save"):
            if t and auths:
                for a in auths: save_to_sheet("research", {"ชื่อเรื่อง": t, "ปี": y, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": a})
                st.success("Saved!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ MANAGE":
    st.markdown("### ⚙️ Delete Records")
    df_m = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี'])
    sel = st.selectbox("Choose to Delete:", ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_m.iterrows()])
    if sel != "-- Select --" and st.button("Delete Permanent"):
        target = sel.split(" | ")[1].strip()
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [i + 2 for i, r in enumerate(ws.get_all_records()) if str(r.get('ชื่อเรื่อง')).strip() == target]
        for r in sorted(rows, reverse=True): ws.delete_rows(r)
        st.success("Deleted!"); st.cache_data.clear(); st.rerun()
