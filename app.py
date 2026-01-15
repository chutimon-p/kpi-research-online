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
# 2. Page Configuration & UI (White Theme + Large Tabs)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    /* พื้นหลังสีขาวสะอาดตา */
    .stApp { background-color: #FFFFFF; }

    /* ปรับแต่ง Metric */
    [data-testid="stMetricValue"] { font-size: 2.2rem; color: #1E3A8A; font-weight: 800; }
    .stMetric {
        background-color: #F8FAFC; 
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }
    
    /* ปรับแต่ง Tab ให้ใหญ่ เด่น และชัดเจน */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #F1F5F9;
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px; 
        min-width: 160px;
        background-color: #FFFFFF;
        border-radius: 8px;
        color: #64748B;
        font-size: 1.3rem !important; 
        font-weight: 700 !important;
        border: 1px solid #E2E8F0;
        transition: all 0.3s ease;
    }

    /* เมื่อเลือก Tab (Active) */
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important; 
        color: white !important;
        font-size: 1.4rem !important;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
    }
    
    h1, h2, h3, h4 { color: #1E3A8A !important; font-weight: 800; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
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
            <h1 style="margin-bottom: 0px;">St Teresa International University</h1>
            <p style="color: #64748B; font-size: 1.1rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Load & Clean Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
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
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
            else: st.error("Wrong Password")
    else:
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Filter Year:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    df_filtered = df_research.copy()
    if year_option != "All Years": df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    df_unique_total = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    df_unique_agency = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])

    t0, t1, t2, t3, t4, t5, t6 = st.tabs([
        "🏛 OVERVIEW", "🎓 PROGRAM KPI", "👤 RESEARCHER", 
        "🏢 FACULTY KPI", "📋 MASTER DB", "🔍 AUDIT", "🚀 IMPROVEMENT"
    ])

    with t0:
        st.markdown("#### 🌍 University Growth")
        inst_summary = df_unique_total.groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")).reset_index()
        inst_summary = inst_summary[inst_summary['ปี'] > 0].sort_values("ปี")
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Titles"], name="Titles", marker_color='#1E3A8A'))
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="Weight", yaxis="y2", line=dict(color='#F43F5E', width=3)))
        fig_inst.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig_inst, use_container_width=True)

    with t1:
        st.markdown("#### 🏆 Program KPI Achievement")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
        prog_member_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_summary = df_unique_agency.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        prog_report = all_progs.merge(prog_summary, on="หลักสูตร", how="left").fillna(0)
        
        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Total_Score"] / n) * 100) / x) * 5, 5.0), 2)
        
        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', range_x=[0, 5.5], text="KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📄 Program KPI Data Table")
        st.dataframe(prog_report.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 🏆 Top 3 Researchers")
        author_rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        r_cols = st.columns(3)
        medals = ["🥇 1st Place", "🥈 2nd Place", "🥉 3rd Place"]
        for i, (col, medal) in enumerate(zip(r_cols, medals)):
            if i < len(author_rank):
                row = author_rank.iloc[i]
                col.metric(medal, row["ผู้เขียน"], f"Score: {row['คะแนน']:.2f}")
        st.divider()
        search_author = st.selectbox("🔍 Search Portfolio:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if search_author != "-- Select --":
            author_works = df_filtered[df_filtered["ผู้เขียน"] == search_author].sort_values("ปี", ascending=False)
            st.dataframe(author_works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)

    with t3:
        st.markdown("#### 🏢 Faculty KPI Performance")
        fac_members = df_master.groupby("คณะ")["Name-surname"].nunique().to_dict()
        res_fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = res_fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()
        
        def calc_fac_kpi(row):
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            n = fac_members.get(row["คณะ"], 1)
            return round(min((((row["Total_Score"] / n) * 100) / y) * 5, 5.0), 2)
        
        fac_sum["Faculty KPI Score"] = fac_sum.apply(calc_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_sum.sort_values("Faculty KPI Score"), x="Faculty KPI Score", y="คณะ", orientation='h', range_x=[0, 5.5], text="Faculty KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="#F43F5E"), use_container_width=True)
        
        st.markdown("#### 📄 Faculty KPI Data Table")
        st.dataframe(fac_sum.sort_values("Faculty KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with t4: st.dataframe(df_master, use_container_width=True, hide_index=True)

    with t5:
        st.markdown("#### 🔍 Verification (Audit Trail)")
        audit_mode = st.radio("Mode:", ["Program", "Faculty"], horizontal=True)
        target = st.selectbox("Select Target:", sorted(df_master["หลักสูตร" if audit_mode == "Program" else "คณะ"].unique().tolist()))
        if target:
            audit_df = df_unique_agency if audit_mode == "Program" else df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
            st.dataframe(audit_df[audit_df["หลักสูตร" if audit_mode == "Program" else "คณะ"] == target], use_container_width=True)

    with t6:
        st.markdown("#### 🚀 KPI Improvement Plan")
        plan_mode = st.radio("Level:", ["By Program", "By Faculty"], horizontal=True)
        
        def show_plan(name, current_sum, n, x_y):
            required_sum = (x_y * n) / 100
            gap = max(required_sum - current_sum, 0.0)
            current_kpi = min((((current_sum / n) * 100) / x_y) * 5, 5.0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Current KPI", f"{current_kpi:.2f}")
            c2.metric("Weight Gap", f"{gap:.2f}")
            c3.metric("Staff Count (n)", n)
            if gap > 0:
                st.info(f"💡 Need {gap:.2f} more points to reach KPI 5.0")
                sc, t1, t2 = st.columns(3)
                sc.warning(f"**Scopus**\n\n{math.ceil(gap/1.0)} papers")
                t1.warning(f"**TCI 1**\n\n{math.ceil(gap/0.8)} papers")
                t2.warning(f"**TCI 2**\n\n{math.ceil(gap/0.6)} papers")
            else: st.balloons(); st.success("✅ KPI 5.0 Reached!")

        if plan_mode == "By Program":
            sel = st.selectbox("Select Program:", sorted(df_master["หลักสูตร"].unique().tolist()))
            if sel:
                curr = df_unique_agency[df_unique_agency["หลักสูตร"] == sel]["คะแนน"].sum()
                n = df_master[df_master["หลักสูตร"] == sel]["Name-surname"].nunique()
                g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x = 60 if sel == "Ph.D-Admin" else (40 if sel in g40 else 20)
                show_plan(sel, curr, n, x)
        else:
            sel = st.selectbox("Select Faculty:", sorted(df_master["คณะ"].unique().tolist()))
            if sel:
                curr = df_full_info[df_full_info["คณะ"] == sel].drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])["คะแนน"].sum()
                n = df_master[df_master["คณะ"] == sel]["Name-surname"].nunique()
                y = 30 if sel in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                show_plan(sel, curr, n, y)

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
        if st.form_submit_button("Save"):
            if t_in and a_in:
                for a in a_in: save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("✅ Recorded!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร'])
    sel = st.selectbox("Delete Entry:", ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()])
    if sel != "-- Select --" and st.button("Confirm Delete"):
        target = sel.split(" | ")[1].strip()
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
        for r in sorted(rows, reverse=True): ws.delete_rows(r)
        st.success("Deleted!"); st.cache_data.clear(); st.rerun()
