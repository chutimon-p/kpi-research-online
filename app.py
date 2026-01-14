import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

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
            df.columns = df.columns.str.strip()
            # ทำความสะอาดข้อมูลตัวเลข
            if 'ปี' in df.columns: df['ปี'] = pd.to_numeric(df['ปี'], errors='coerce').fillna(0).astype(int)
            if 'คะแนน' in df.columns: df['คะแนน'] = pd.to_numeric(df['คะแนน'], errors='coerce').fillna(0.0)
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
# 2. Page Configuration & Header
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1E3A8A; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f8fafc; border-radius: 5px; padding: 10px 15px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

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

# Load Data
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Accessing Google Sheets...")
    st.stop()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
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
            else: st.error("Invalid Credentials")
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
    st.markdown(f"### 📈 Performance Overview: {year_option}")
    
    # --- เตรียมข้อมูลพื้นฐาน (Unique Titles) ---
    df_u = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).copy()
    if year_option != "All Years":
        df_u = df_u[df_u["ปี"] == int(year_option)]
    
    # สถิติเบื้องต้น
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Publications", f"{len(df_u)} Titles")
    m2.metric("Active Researchers", f"{df_research[df_research['ชื่อเรื่อง'].isin(df_u['ชื่อเรื่อง'])]['ผู้เขียน'].nunique()} Persons")
    m3.metric("Total Weighted Score", f"{df_u['คะแนน'].sum():.2f}")

    t1, t2, t3, t4, t5 = st.tabs(["🏛 Institutional Overview", "🎓 Program KPI", "👤 Researcher Profile", "🏛 Faculty Performance", "📋 Master Database"])

    # --- TAB 1: Institutional Overview (NEW) ---
    with t1:
        st.markdown("#### 🌍 University Research Trend")
        inst_sum = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(
            Titles=("ชื่อเรื่อง", "count"),
            Weight=("คะแนน", "sum")
        ).reset_index().sort_values("ปี")
        
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_sum["ปี"], y=inst_sum["Titles"], name="Total Titles", marker_color='#1E3A8A'))
        fig_inst.add_trace(go.Scatter(x=inst_sum["ปี"], y=inst_sum["Weight"], name="Weight Score Sum", yaxis="y2", line=dict(color='#ef4444', width=3)))
        fig_inst.update_layout(
            yaxis=dict(title="Number of Titles"),
            yaxis2=dict(title="Weight Score Sum", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1), template="plotly_white"
        )
        st.plotly_chart(fig_inst, use_container_width=True)

    # --- TAB 2: Program KPI (REVISED) ---
    with t2:
        st.markdown("#### 🎓 KPI Achievement by Program (21 Programs)")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
        staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        # นับเฉพาะงานที่ไม่ซ้ำรายหลักสูตร
        df_prog_map = df_u.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        prog_agg = df_prog_map.groupby("หลักสูตร").agg(
            Titles=("ชื่อเรื่อง", "count"),
            Weight=("คะแนน", "sum")
        ).reset_index()
        
        prog_final = all_progs.merge(prog_agg, on="หลักสูตร", how="left").fillna(0)

        def get_kpi(row):
            n = staff_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            target = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Weight"] / n) * 100) / target) * 5, 5.0), 2)

        prog_final["KPI Score"] = prog_final.apply(get_kpi, axis=1)

        # กราฟเปรียบเทียบ 21 หลักสูตร
        fig_p = px.bar(prog_final, x="หลักสูตร", y=["KPI Score", "Weight", "Titles"], 
                       barmode="group", title="Program Metrics Comparison")
        fig_p.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="KPI Target")
        st.plotly_chart(fig_p, use_container_width=True)
        
        st.dataframe(prog_final.rename(columns={"Titles": "Total Titles", "Weight": "Weighted Score Sum"}), use_container_width=True, hide_index=True)

    # --- TAB 4: Faculty Performance (REVISED) ---
    with t4:
        st.markdown("#### 🏛 Faculty Performance Summary")
        df_fac_map = df_u.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        fac_sum = df_fac_map.groupby(["ปี", "คณะ"]).agg(
            Titles=("ชื่อเรื่อง", "count"),
            Weight=("คะแนน", "sum")
        ).reset_index().sort_values(["ปี", "Weight"], ascending=[False, False])
        
        st.plotly_chart(px.bar(fac_sum, x="ปี", y="Weight", color="คณะ", barmode="group", text_auto='.2f'), use_container_width=True)
        st.dataframe(fac_sum.rename(columns={"ปี": "Academic Year", "Titles": "Unique Research Count", "Weight": "Total Weight Score"}), use_container_width=True, hide_index=True)

    with t5:
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin Sections (With Duplicate Check)
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register New Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Publication Title (Check for duplicates before submitting)").strip()
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("Year (B.E.)", 2560, 2600, 2567)
        with c2: j_in = st.selectbox("Database / Journal", list(SCORE_MAP.keys()))
        a_in = st.multiselect("Select Author(s)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("💾 Save Record to Cloud"):
            # --- ตรวจสอบชื่อซ้ำ ---
            existing_titles = [str(t).lower() for t in df_research["ชื่อเรื่อง"].unique()]
            
            if not t_in or not a_in:
                st.error("Please fill in Title and at least one Author.")
            elif t_in.lower() in existing_titles:
                st.warning(f"⚠️ Warning: The title '{t_in}' already exists in the system!")
            else:
                for author in a_in:
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                st.success("✅ Recorded Successfully!")
                st.cache_data.clear()
                st.rerun()

elif menu == "⚙️ Manage Database":
    st.subheader("⚙️ Database Maintenance")
    if not df_research.empty:
        to_del = st.selectbox("Select title to remove:", sorted(df_research["ชื่อเรื่อง"].unique()))
        if st.button("🗑 Confirm Delete"):
            client = conn_sheets()
            ws = client.open("Research_Database").worksheet("research")
            try:
                # ลบทุกแถวที่ชื่อเรื่องนี้ปรากฏ (กรณีมีหลายผู้เขียน)
                cells = ws.findall(to_del)
                rows_to_del = sorted([c.row for c in cells], reverse=True)
                for r in rows_to_del:
                    ws.delete_rows(r)
                st.success(f"Removed all entries for: {to_del}")
                st.cache_data.clear()
                st.rerun()
            except: st.error("Error during deletion.")
