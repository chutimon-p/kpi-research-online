import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

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

# Custom CSS for Modern Dashboard Look
st.markdown("""
    <style>
    /* Metric Card Styling */
    [data-testid="stMetricValue"] { font-size: 2rem; color: #1E3A8A; }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #1E3A8A;
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
        font-weight: bold;
    }
    /* Global Font */
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    try:
        # ใช้ชื่อไฟล์ logo.jpg ตามที่คุณตั้งไว้
        st.image("logo.jpg", width=150)
    except:
        st.info("🏫 STIU LOGO")

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
    st.warning("⚠️ Accessing Google Sheets... Please wait or check your connection.")
    st.stop()

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar & Navigation
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.image("logo.jpg", width=80) if st.session_state.logged_in else None
    st.markdown("### 🧭 Main Navigation")
    menu_options = ["📊 Dashboard & Reports"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ Submit Research")
        menu_options.append("⚙️ Manage Database")
    
    menu = st.radio("Go to Page:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        st.markdown("#### 🔐 Administrator Login")
        pwd = st.text_input("Password", type="password")
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
    all_years = sorted(df_research["ปี"].unique().tolist()) if not df_research.empty else []
    year_option = st.selectbox("📅 Academic Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Dashboard & Reports
# ==========================================
if menu == "📊 Dashboard & Reports":
    st.markdown(f"### 📈 Performance Overview: {year_option}")
    
    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    # Key Performance Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Publications", f"{len(df_filtered.drop_duplicates(subset=['ชื่อเรื่อง']))} Titles")
    m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
    m3.metric("Weighted Score", f"{df_filtered['คะแนน'].sum():.2f}")

    t1, t2, t3, t4 = st.tabs(["🎓 Program KPI", "👤 Researcher Profile", "🏛 Faculty Performance", "📋 Master Database"])

    with t1:
        st.markdown("#### 🏆 KPI Achievement by Program")
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        all_progs = all_progs[(all_progs["หลักสูตร"] != "-") & (all_progs["หลักสูตร"] != "")]
        faculty_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()

        prog_sum = df_filtered.merge(df_master[['Name-surname', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        prog_sum = prog_sum.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        prog_report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_kpi(row):
            n = faculty_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["คะแนน"] / n) * 100) / x) * 5, 5.0), 2)

        prog_report["KPI Score"] = prog_report.apply(calc_kpi, axis=1)
        prog_report = prog_report.sort_values(by=["คณะ", "KPI Score"])

        fig = px.bar(prog_report, x="KPI Score", y="หลักสูตร", color="คณะ", orientation='h', 
                     range_x=[0, 5.5], text="KPI Score", height=600, template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.add_vline(x=5.0, line_dash="dash", line_color="#ef4444", annotation_text="Target")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(prog_report, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 👤 Researcher Rankings")
        if not df_filtered.empty:
            p_report = df_filtered.groupby("ผู้เขียน").agg(
                Titles=("ชื่อเรื่อง", "nunique"), 
                Total_Score=("คะแนน", "sum")
            ).reset_index()
            st.dataframe(p_report.sort_values("Total_Score", ascending=False), use_container_width=True, hide_index=True)
        else: st.info("No research records found.")

    with t3:
        st.markdown("#### 🏛 Faculty Performance Analysis")
        res_with_prog = df_research.merge(df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
        if not res_with_prog.empty:
            fac_sum = res_with_prog.groupby(["ปี", "คณะ"]).agg(
                Total_Score=("คะแนน", "sum"),
                Unique_Publications=("ชื่อเรื่อง", "nunique")
            ).reset_index().rename(columns={"ปี": "Year", "คณะ": "Faculty"})
            
            # Interactive Chart
            st.plotly_chart(px.bar(fac_sum, x="Year", y="Total_Score", color="Faculty", barmode="group", text_auto='.2f'), use_container_width=True)
            
            # --- ปรับปรุงส่วนตารางสรุปรายคณะ ---
            st.markdown("#### 📋 Faculty Summary Data Table")
            st.dataframe(
                fac_sum.sort_values(by=["Year", "Total_Score"], ascending=[False, False]),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Insufficient data for faculty analysis.")

    with t4:
        st.markdown("#### 📋 Master Academic Database")
        st.dataframe(df_master, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin Sections
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register New Publication")
    with st.form("entry_form", clear_on_submit=True):
        t_in = st.text_input("Publication Title")
        c1, c2 = st.columns(2)
        with c1:
            y_in = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        with c2:
            j_in = st.selectbox("Database / Journal", list(SCORE_MAP.keys()))
        
        a_in = st.multiselect("Select Author(s)", df_master["Name-surname"].unique().tolist())
        
        if st.form_submit_button("💾 Save Record to Cloud"):
            if t_in and a_in:
                for author in a_in:
                    save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": author})
                st.success("✅ Success: Data pushed to Google Sheets!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    st.warning("Action: Data deletion is permanent.")
    if not df_research.empty:
        to_del = st.selectbox("Select title to remove:", df_research["ชื่อเรื่อง"].unique())
        if st.button("🗑 Delete Selected Entry"):
            client = conn_sheets()
            sh = client.open("Research_Database")
            ws = sh.worksheet("research")
            try:
                cell = ws.find(to_del)
                ws.delete_rows(cell.row)
                st.success(f"Removed: {to_del}")
                st.cache_data.clear()
                st.rerun()
            except:
                st.error("Could not locate entry in Sheet.")
