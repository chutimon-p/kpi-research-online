import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database Connection & Data Engine
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

def load_data():
    client = conn_sheets()
    if not client: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("Research_Database")
        # Load Masters
        df_m = pd.DataFrame(sh.worksheet("masters").get_all_records())
        # Load Research & Data Cleaning (ป้องกันข้อมูลขยะ)
        df_r = pd.DataFrame(sh.worksheet("research").get_all_records())
        
        if not df_r.empty:
            df_r.columns = df_r.columns.str.strip()
            df_r['ปี'] = pd.to_numeric(df_r['ปี'], errors='coerce').fillna(0).astype(int)
            df_r['คะแนน'] = pd.to_numeric(df_r['คะแนน'], errors='coerce').fillna(0.0)
            df_r['ชื่อเรื่อง'] = df_r['ชื่อเรื่อง'].astype(str).str.strip()
            
        return df_m, df_r
    except Exception as e:
        st.error(f"❌ Error Loading Data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_to_sheet(new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        sh.worksheet("research").append_row(list(new_row_dict.values()))

# ==========================================
# 2. Page Configuration & Custom CSS
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1E3A8A; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f8fafc; border-radius: 8px; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Header Section
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try: st.image("logo.jpg", width=150)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="color: #1E3A8A; margin-bottom: 0px;">St Teresa International University</h1>
            <p style="color: #64748b; font-size: 1.2rem; margin-top: 0px;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Initial Data Load
df_master, df_research = load_data()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

if df_master.empty or df_research.empty:
    st.warning("⚠️ Connecting to database or No data found...")
    st.stop()

# ==========================================
# 3. Sidebar & Auth
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("Select Page", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        st.markdown("#### 🔐 Admin Access")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Invalid Password")
    else:
        st.success("🔓 Authenticated")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.divider()
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 Academic Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.subheader(f"📈 Performance Analysis: {year_option}")
    
    # 🔍 จัดเตรียมข้อมูล Unique Titles สำหรับระดับภาพรวม
    df_unique_all = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).copy()
    
    # กรองตามปี
    df_u_filtered = df_unique_all.copy()
    if year_option != "All Years":
        df_u_filtered = df_u_filtered[df_u_filtered["ปี"] == int(year_option)]
    
    # Summary Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Research Titles", f"{len(df_u_filtered)} Titles")
    c2.metric("Total Weighted Score", f"{df_u_filtered['คะแนน'].sum():.2f}")
    c3.metric("Active Researchers", f"{df_research[df_research['ชื่อเรื่อง'].isin(df_u_filtered['ชื่อเรื่อง'])]['ผู้เขียน'].nunique()} Persons")

    t1, t2, t3, t4 = st.tabs(["🏛 Institutional Overview", "🎓 Program KPI", "🏢 Faculty Performance", "📋 Master Database"])

    # --- TAB 1: Institutional Overview ---
    with t1:
        st.markdown("#### 🌍 University-Wide Research Growth")
        # สรุปข้อมูลรายปี (นับเฉพาะ Unique)
        inst_summary = df_unique_all[df_unique_all['ปี'] > 0].groupby("ปี").agg(
            Title_Count=("ชื่อเรื่อง", "count"),
            Total_Weight=("คะแนน", "sum")
        ).reset_index().sort_values("ปี")
        
        fig_inst = go.Figure()
        # กราฟแท่งจำนวนเรื่อง
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Title_Count"], name="Titles", marker_color='#1E3A8A', text=inst_summary["Title_Count"], textposition='auto'))
        # กราฟเส้นคะแนนสะสม
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="Weight Score Sum", yaxis="y2", line=dict(color='#ef4444', width=4), mode='lines+markers'))
        
        fig_inst.update_layout(
            title="Institutional Trend: Titles vs. Weighted Score",
            yaxis=dict(title="Number of Titles"),
            yaxis2=dict(title="Weight Score Sum", overlaying="y", side="right", showgrid=False),
            template="plotly_white", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_inst, use_container_width=True)
        
        st.markdown("##### 📋 Institutional Yearly Summary Table")
        st.dataframe(inst_summary.rename(columns={"ปี": "Year", "Title_Count": "Total Titles", "Total_Weight": "Total Weight Score"}).sort_values("Year", ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 2: Program KPI ---
    with t2:
        st.markdown("#### 🎓 KPI Achievement by Program")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[all_progs["หลักสูตร"].str.len() > 1]
        
        # เชื่อมข้อมูล Unique กับ Master เพื่อหาหลักสูตร
        df_prog_mapped = df_u_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        
        staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_agg = df_prog_mapped.groupby("หลักสูตร").agg(Title_Count=("ชื่อเรื่อง", "count"), Weight=("คะแนน", "sum")).reset_index()
        prog_report = all_progs.merge(prog_agg, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = staff_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            target = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Weight"] / n) * 100) / target) * 5, 5.0), 2)

        prog_report["KPI_Score"] = prog_report.apply(calc_kpi, axis=1)

        fig_p = px.bar(prog_report, x="หลักสูตร", y=["KPI_Score", "Weight", "Title_Count"], 
                       barmode="group", title="Program Performance Comparison",
                       color_discrete_sequence=['#1E3A8A', '#3b82f6', '#94a3b8'], height=500)
        fig_p.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Target 5.0")
        st.plotly_chart(fig_p, use_container_width=True)
        
        st.dataframe(prog_report[['หลักสูตร', 'Title_Count', 'Weight', 'KPI_Score']].rename(columns={'Title_Count':'Titles', 'Weight':'Weighted Score', 'KPI_Score':'KPI'}), use_container_width=True, hide_index=True)

    # --- TAB 3: Faculty Performance ---
    with t3:
        st.markdown("#### 🏢 Faculty Summary")
        df_fac_mapped = df_u_filtered.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        fac_agg = df_fac_mapped.groupby(["ปี", "คณะ"]).agg(Title_Count=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")).reset_index()
        
        st.plotly_chart(px.bar(fac_agg, x="คณะ", y="Title_Count", color="คณะ", title="Research Titles by Faculty"), use_container_width=True)
        st.dataframe(fac_agg.rename(columns={'ปี':'Year', 'คณะ':'Faculty', 'Title_Count':'Number of Research', 'Total_Weight':'Weighted Score'}), use_container_width=True, hide_index=True)

    with t4:
        st.markdown("#### 📋 Master Academic Database")
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin: Submit Research (With Validation)
# ==========================================
elif menu == "✍️ Submit Research":
    st.subheader("✍️ Add New Research Entry")
    with st.form("add_form", clear_on_submit=True):
        title_in = st.text_input("Research Title").strip()
        col1, col2 = st.columns(2)
        year_in = col1.number_input("Year (B.E.)", 2560, 2600, 2567)
        db_in = col2.selectbox("Journal Database", list(SCORE_MAP.keys()))
        authors_in = st.multiselect("Select Author(s)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("Submit Data"):
            # 🔍 ตรวจสอบชื่อเรื่องซ้ำ
            existing_titles = df_research["ชื่อเรื่อง"].str.lower().tolist()
            if not title_in or not authors_in:
                st.error("❌ Title and Authors are required.")
            elif title_in.lower() in existing_titles:
                st.warning(f"⚠️ Duplicate Detected: '{title_in}' is already in the system.")
            else:
                for author in authors_in:
                    save_to_sheet({"ชื่อเรื่อง": title_in, "ปี": year_in, "ฐานวารสาร": db_in, "คะแนน": SCORE_MAP[db_in], "ผู้เขียน": author})
                st.success("✅ Recorded Successfully!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ Manage Database":
    st.subheader("⚙️ Database Maintenance")
    if not df_research.empty:
        to_del = st.selectbox("Select title to remove:", sorted(df_research["ชื่อเรื่อง"].unique()))
        if st.button("🗑 Confirm Permanent Delete"):
            client = conn_sheets()
            ws = client.open("Research_Database").worksheet("research")
            cells = ws.findall(to_del)
            rows = sorted([c.row for c in cells], reverse=True)
            for r in rows: ws.delete_rows(r)
            st.success("Entry Deleted.")
            st.cache_data.clear()
            st.rerun()
