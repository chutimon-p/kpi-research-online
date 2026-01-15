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
# 2. White Clean UI CSS (เน้น Tab ใหญ่และชัด)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    /* ปรับพื้นหลังหลักเป็นสีขาวสะอาด */
    .stApp {
        background-color: #FFFFFF;
    }

    /* ปรับแต่ง Metric ให้ดูเด่นบนพื้นขาว */
    [data-testid="stMetricValue"] { 
        font-size: 2.5rem; 
        color: #1E3A8A; 
        font-weight: 800;
    }
    .stMetric {
        background-color: #F8FAFC; 
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* การปรับแต่ง Tab ให้ใหญ่และเด่นชัดที่สุด */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: #F1F5F9;
        padding: 10px;
        border-radius: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 70px; 
        min-width: 200px;
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 0px 25px; 
        color: #64748B;
        font-size: 1.4rem !important; /* ขนาดตัวหนังสือใหญ่ชัดเจน */
        font-weight: 800 !important;   /* ตัวหนาพิเศษ */
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }

    /* Hover Effect */
    .stTabs [data-baseweb="tab"]:hover {
        color: #1E3A8A;
        border-color: #1E3A8A;
        background-color: #F8FAFC;
    }

    /* เมื่อเลือก Tab (Active State) */
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important; /* สีน้ำเงินเข้ม STIU */
        color: #FFFFFF !important;            /* ตัวหนังสือขาว */
        font-size: 1.5rem !important;
        border: none !important;
        box-shadow: 0 8px 15px rgba(30, 58, 138, 0.2);
        transform: translateY(-3px);
    }
    
    /* Ranking Card แบบสะอาดตา */
    .ranking-card {
        background-color: #FFFFFF;
        padding: 30px; 
        border-radius: 20px; 
        border: 2px solid #F1F5F9;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    h1, h2, h3, h4 { 
        font-family: 'Sarabun', sans-serif;
        color: #1E3A8A !important; 
        font-weight: 800;
    }
    
    /* ปรับตัวหนังสือทั่วไปให้อ่านง่าย */
    .stMarkdown p {
        font-size: 1.1rem;
        color: #334155;
    }

    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. Header
# ==========================================
header_col1, header_col2 = st.columns([1, 5])
with header_col1:
    try: st.image("logo.jpg", width=140)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="margin-bottom: 0px; font-size: 2.5rem; color: #1E3A8A;">
                St Teresa International University
            </h1>
            <p style="color: #64748B; font-size: 1.2rem; font-weight: 600;">Research Management & KPI Tracking System</p>
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
# 4. Sidebar
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
    else:
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
    
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Filter Year (B.E.):", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 5. Dashboard Implementation
# ==========================================
if menu == "📊 DASHBOARD":
    df_filtered = df_research.copy()
    if year_option != "All Years": df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    df_unique_total = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    df_unique_agency = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])

    # Big English Tabs
    t0, t1, t2, t3, t4, t6 = st.tabs([
        "OVERVIEW", "PROGRAM KPI", "RESEARCHER PROFILE", 
        "FACULTY KPI", "MASTER DATABASE", "IMPROVEMENT PLAN"
    ])

    with t0:
        st.markdown("### 📈 Publication Growth")
        inst_summary = df_unique_total.groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")).reset_index()
        inst_summary = inst_summary[inst_summary['ปี'] > 0].sort_values("ปี")
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Titles"], name="Publications", marker_color='#1E3A8A'))
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="Weighted Score", yaxis="y2", line=dict(color='#F43F5E', width=4)))
        fig_inst.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig_inst, use_container_width=True)

    with t1:
        st.markdown("### 🎓 Program KPI Status")
        prog_member_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_summary = df_unique_agency.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Total_Score"] / n) * 100) / x) * 5, 5.0), 2)
        prog_summary["KPI Score"] = prog_summary.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_summary.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', range_x=[0, 5.5], text="KPI Score", template="plotly_white", color_discrete_sequence=['#1E3A8A']).add_vline(x=5.0, line_dash="dash", line_color="#EF4444"), use_container_width=True)

    with t2:
        st.markdown("### 🏆 Top Researchers")
        author_rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        r_cols = st.columns(3)
        medals = ["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]
        for i, (col, medal) in enumerate(zip(r_cols, medals)):
            if i < len(author_rank):
                row = author_rank.iloc[i]
                col.markdown(f'''
                    <div class="ranking-card">
                        <p style="font-size: 1.2rem; color: #1E3A8A; font-weight: bold;">{medal}</p>
                        <h2 style="margin: 10px 0;">{row["ผู้เขียน"]}</h2>
                        <p style="font-size: 1rem; color: #64748B;">Total Score</p>
                        <h1>{row["คะแนน"]:.2f}</h1>
                    </div>
                ''', unsafe_allow_html=True)

    with t6:
        st.markdown("### 🚀 KPI Improvement Plan (Road to 5.0)")
        p_mode = st.radio("Plan Level:", ["Program", "Faculty"], horizontal=True)
        
        def run_plan(name, current_sum, n, x_y):
            required_sum = (x_y * n) / 100
            gap = max(required_sum - current_sum, 0.0)
            current_kpi = min((((current_sum / n) * 100) / x_y) * 5, 5.0)
            
            st.subheader(f"Strategy for: {name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Current KPI", f"{current_kpi:.2f}")
            c2.metric("Weight Needed", f"{gap:.2f}")
            c3.metric("Staff (n)", n)
            
            if gap > 0:
                st.info(f"💡 To reach KPI 5.0, you need an additional weight of **{gap:.2f}**")
                sc, t1, t2 = st.columns(3)
                sc.warning(f"**Scopus (Q1-4)**\n\n {math.ceil(gap/1.0)} papers")
                t1.warning(f"**TCI Group 1**\n\n {math.ceil(gap/0.8)} papers")
                t2.warning(f"**TCI Group 2**\n\n {math.ceil(gap/0.6)} papers")
            else: st.balloons(); st.success("✅ Target 5.0 Achieved!")

        if p_mode == "Program":
            sel = st.selectbox("Select Program:", sorted(df_master["หลักสูตร"].unique().tolist()))
            if sel:
                curr = df_unique_agency[df_unique_agency["หลักสูตร"] == sel]["คะแนน"].sum()
                n = df_master[df_master["หลักสูตร"] == sel]["Name-surname"].nunique()
                g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x = 60 if sel == "Ph.D-Admin" else (40 if sel in g40 else 20)
                run_plan(sel, curr, n, x)
        else:
            sel = st.selectbox("Select Faculty:", sorted(df_master["คณะ"].unique().tolist()))
            if sel:
                curr = df_full_info[df_full_info["คณะ"] == sel].drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])["คะแนน"].sum()
                n = df_master[df_master["คณะ"] == sel]["Name-surname"].nunique()
                y = 30 if sel in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                run_plan(sel, curr, n, y)

# ส่วนการ SUBMIT และ MANAGE จะทำงานเหมือนเดิมบนหน้าสีขาวที่สะอาดตาขึ้น
elif menu == "✍️ SUBMIT":
    st.markdown("### ✍️ Register New Publication")
    with st.form("entry_form"):
        t_in = st.text_input("Title")
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        with c2: j_in = st.selectbox("Database", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("Save"):
            if t_in and a_in:
                for a in a_in: save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("Saved!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ MANAGE":
    st.markdown("### ⚙️ Database Management")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร'])
    sel = st.selectbox("Delete Entry:", ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()])
    if sel != "-- Select --" and st.button("Confirm Delete"):
        target = sel.split(" | ")[1].strip()
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
        for r in sorted(rows, reverse=True): ws.delete_rows(r)
        st.success("Deleted!"); st.cache_data.clear(); st.rerun()
