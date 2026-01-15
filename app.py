import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time
import os

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

@st.cache_data(ttl=60)
def load_all_data():
    client = conn_sheets()
    if not client: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("Research_Database")
        # Load Masters
        df_m = pd.DataFrame(sh.worksheet("masters").get_all_records())
        df_m.columns = df_m.columns.str.strip()
        df_m["Name-surname"] = df_m["Name-surname"].astype(str).str.strip()
        
        # Load Research
        df_r = pd.DataFrame(sh.worksheet("research").get_all_records())
        df_r.columns = df_r.columns.str.strip()
        df_r["ผู้เขียน"] = df_r["ผู้เขียน"].astype(str).str.strip()
        
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(list(new_row_dict.values()))

# ==========================================
# 2. UI & Header
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 6])
with col1:
    if os.path.exists("logo.jpg"): st.image("logo.jpg", width=130)
    else: st.info("🏫 STIU")
with col2:
    st.markdown("<h1 style='color: #1E3A8A; margin-bottom:0;'>St Teresa International University</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 1.1rem;'>Research Management & KPI Tracking System</p>", unsafe_allow_html=True)

st.divider()

# Initial Data Load
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")
df_master, df_research = load_all_data()

if df_master.empty:
    st.warning("⚠️ Accessing Google Sheets... Please wait.")
    st.stop()

# Data Cleaning
if not df_research.empty:
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
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in years])

# ==========================================
# 4. Dashboard Logic
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 Performance Overview: {year_option}")
    
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # Merge for KPI Analysis
    df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")

    # Member Counts for Division (n)
    prog_member_counts = df_master[df_master['หลักสูตร'] != ""].groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    fac_member_counts = df_master[df_master['คณะ'] != ""].groupby("คณะ")["Name-surname"].nunique().to_dict()

    m1, m2, m3 = st.columns(3)
    unique_titles = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    m1.metric("Total Publications", f"{len(unique_titles)} Titles")
    m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
    m3.metric("Weighted Score Sum", f"{unique_titles['คะแนน'].sum():.2f}")

    tabs = st.tabs(["🏛 Overview", "🎓 Program KPI", "👤 Researcher Profile", "🏢 Faculty KPI", "📋 Master Database"])

    with tabs[0]: # Overview
        st.markdown("#### 🌍 University Growth")
        growth = df_research[df_research['ปี'] > 0].drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Score=("คะแนน", "sum")).reset_index()
        fig_g = go.Figure()
        fig_g.add_trace(go.Bar(x=growth["ปี"], y=growth["Titles"], name="Titles", marker_color='#1E3A8A'))
        fig_g.add_trace(go.Scatter(x=growth["ปี"], y=growth["Score"], name="Weight", yaxis="y2", line=dict(color='#ef4444', width=3)))
        fig_g.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_white")
        st.plotly_chart(fig_g, use_container_width=True)

    with tabs[1]: # Program KPI
        st.markdown("#### 🏆 Program KPI Achievement")
        prog_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])
        prog_sum = prog_unique.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum"), Total_Titles=("ชื่อเรื่อง", "count")).reset_index()
        
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        prog_report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def get_prog_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M.Ed-Admin", "M.Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            score = (((row["Total_Score"] / n) * 100) / x) * 5
            return round(min(score, 5.0), 2)

        prog_report["KPI Score"] = prog_report.apply(get_prog_kpi, axis=1)
        st.plotly_chart(px.bar(prog_report.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', text="KPI Score", template="plotly_white").add_vline(x=5.0, line_dash="dash", line_color="red"), use_container_width=True)
        st.dataframe(prog_report.sort_values("KPI Score", ascending=False), use_container_width=True, hide_index=True)

    with tabs[2]: # Researcher Profile
        st.markdown("#### 👤 Researcher Portfolio")
        sel_auth = st.selectbox("🔍 Search Name:", ["-- Select --"] + sorted(df_master["Name-surname"].unique().tolist()))
        if sel_auth != "-- Select --":
            works = df_filtered[df_filtered["ผู้เขียน"] == sel_auth].sort_values("ปี", ascending=False)
            c1, c2 = st.columns([1, 3])
            c1.metric("Works", len(works))
            c1.metric("Score", f"{works['คะแนน'].sum():.2f}")
            c2.dataframe(works[['ปี', 'ชื่อเรื่อง', 'ฐานวารสาร', 'คะแนน']], use_container_width=True, hide_index=True)

    with tabs[3]: # Faculty KPI
        st.markdown("#### 🏢 Faculty KPI Performance")
        fac_unique = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])
        fac_sum = fac_unique.groupby("คณะ").agg(Total_Score=("คะแนน", "sum")).reset_index()

        def get_fac_kpi(row):
            n = fac_member_counts.get(row["คณะ"], 1)
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            score = (((row["Total_Score"] / n) * 100) / y) * 5
            return round(min(score, 5.0), 2)

        fac_sum["Faculty KPI Score"] = fac_sum.apply(get_fac_kpi, axis=1)
        st.plotly_chart(px.bar(fac_sum, x="Faculty KPI Score", y="คณะ", orientation='h', text="Faculty KPI Score", color="คณะ", template="plotly_white"), use_container_width=True)

    with tabs[4]: # Master
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin Sections
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Title").strip()
        c1, c2 = st.columns(2)
        y_in = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
        j_in = c2.selectbox("Journal Database", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Authors", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("Save Record"):
            if t_in and a_in:
                for a in a_in: save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("Saved!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    if not df_research.empty:
        df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values(by='ปี', ascending=False)
        opts = ["-- Select --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
        sel = st.selectbox("Select Entry to Delete:", opts)
        if sel != "-- Select --":
            target = sel.split(" | ")[1].strip()
            if st.button("Confirm Delete"):
                ws = conn_sheets().open("Research_Database").worksheet("research")
                rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
                for r in sorted(rows, reverse=True): ws.delete_rows(r)
                st.success("Deleted!"); st.cache_data.clear(); time.sleep(1); st.rerun()
