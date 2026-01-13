import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. Database & Connection Engine
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
        return None

def load_data():
    client = conn_sheets()
    if not client: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("Research_Database")
        # Load Masters
        df_m = pd.DataFrame(sh.worksheet("masters").get_all_records())
        # Load Research & Clean Data
        df_r = pd.DataFrame(sh.worksheet("research").get_all_records())
        
        # คลีนข้อมูลให้เป็นตัวเลขที่ถูกต้องป้องกัน Error ในกราฟ
        if not df_r.empty:
            df_r['ปี'] = pd.to_numeric(df_r['ปี'], errors='coerce').fillna(0).astype(int)
            df_r['คะแนน'] = pd.to_numeric(df_r['คะแนน'], errors='coerce').fillna(0.0)
            df_r['ชื่อเรื่อง'] = df_r['ชื่อเรื่อง'].astype(str).str.strip()
            
        return df_m, df_r
    except:
        return pd.DataFrame(), pd.DataFrame()

def save_to_sheet(new_row_dict):
    client = conn_sheets()
    if client:
        sh = client.open("Research_Database")
        sh.worksheet("research").append_row(list(new_row_dict.values()))

# ==========================================
# 2. Page Setup & Styling
# ==========================================
st.set_page_config(page_title="STIU Research System", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #1E3A8A; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #1E3A8A; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Header
h_col1, h_col2 = st.columns([1, 5])
with h_col1:
    try: st.image("logo.jpg", width=140)
    except: st.title("🏫 STIU")
with h_col2:
    st.markdown("<h1 style='color: #1E3A8A; margin-bottom:0;'>St Teresa International University</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 1.2rem;'>Research Management & KPI Tracking Dashboard</p>", unsafe_allow_html=True)

st.divider()

# Load Data
df_master, df_research = load_data()
if df_master.empty or df_research.empty:
    st.error("⚠️ ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบการตั้งค่าไฟล์ Sheets หรือ Secrets")
    st.stop()

# Constants
SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}
ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "1234")

# ==========================================
# 3. Sidebar Navigation
# ==========================================
if 'auth' not in st.session_state: st.session_state.auth = False

with st.sidebar:
    st.markdown("### 🧭 Main Navigation")
    menu = ["📊 Dashboard & Reports"]
    if st.session_state.auth:
        menu = ["✍️ Submit Research", "📊 Dashboard & Reports", "⚙️ Manage Database"]
    
    choice = st.radio("Go to:", menu)
    
    st.divider()
    if not st.session_state.auth:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PWD:
                st.session_state.auth = True
                st.rerun()
            else: st.error("Wrong password")
    else:
        if st.button("Logout"):
            st.session_state.auth = False
            st.rerun()

    st.divider()
    years = sorted(df_research["ปี"].unique().tolist())
    year_filter = st.selectbox("📅 Filter by Academic Year:", ["All Years"] + [str(y) for y in years if y > 0])

# ==========================================
# 4. Dashboard & Reports (Logic & View)
# ==========================================
if choice == "📊 Dashboard & Reports":
    # 🔍 Data Processing: กรองข้อมูลเฉพาะที่ Unique (ชื่อเรื่องเดียวเอาบรรทัดเดียว)
    df_u = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).copy()
    if year_filter != "All Years":
        df_u = df_u[df_u["ปี"] == int(year_filter)]
    
    # 1. Institutional Summary Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Unique Titles", f"{len(df_u)} Items")
    m2.metric("Total Weighted Score", f"{df_u['คะแนน'].sum():.2f}")
    m3.metric("Contributing Researchers", f"{df_research[df_research['ชื่อเรื่อง'].isin(df_u['ชื่อเรื่อง'])]['ผู้เขียน'].nunique()} Persons")

    tab1, tab2, tab3 = st.tabs(["🏛 Institutional Trends", "🎓 Program KPI", "🏢 Faculty Performance"])

    with tab1:
        st.markdown("#### 📈 University-Wide Research Growth")
        # สรุปข้อมูลรายปีแบบสะอาตตา
        yearly_stat = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).groupby("ปี").agg(
            Title_Count=("ชื่อเรื่อง", "count"),
            Total_Weight=("คะแนน", "sum")
        ).reset_index().sort_values("ปี")
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(x=yearly_stat["ปี"], y=yearly_stat["Title_Count"], name="Number of Titles", marker_color='#1E3A8A'))
        fig_trend.add_trace(go.Scatter(x=yearly_stat["ปี"], y=yearly_stat["Total_Weight"], name="Weight Score", yaxis="y2", line=dict(color='#ef4444', width=4)))
        
        fig_trend.update_layout(
            title="Trend: Research Volume vs Weighted Score",
            yaxis=dict(title="Number of Titles"),
            yaxis2=dict(title="Weight Score Sum", overlaying="y", side="right"),
            template="plotly_white", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.markdown("##### 📋 Yearly Data Summary")
        st.dataframe(yearly_stat.rename(columns={"ปี": "Year", "Title_Count": "Titles", "Total_Weight": "Weight Score"}), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### 🎓 KPI & Weight by Program (21 Programs)")
        # Mapping ข้อมูลคณะ/หลักสูตรให้งานวิจัย
        df_mapped = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).merge(
            df_master[['Name-surname', 'หลักสูตร', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left"
        )
        if year_filter != "All Years": df_mapped = df_mapped[df_mapped["ปี"] == int(year_filter)]

        # คำนวณ KPI รายหลักสูตร
        prog_list = df_master[["หลักสูตร", "คณะ"]].drop_duplicates().dropna()
        prog_list = prog_list[prog_list["หลักสูตร"].str.len() > 1]
        
        # นับจำนวนอาจารย์
        staff_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        
        prog_agg = df_mapped.groupby("หลักสูตร").agg(
            Titles=("ชื่อเรื่อง", "count"),
            Weight=("คะแนน", "sum")
        ).reset_index()
        
        prog_final = prog_list.merge(prog_agg, on="หลักสูตร", how="left").fillna(0)
        
        def get_kpi(row):
            n = staff_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            target = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Weight"] / n) * 100) / target) * 5, 5.0), 2)

        prog_final["KPI_Score"] = prog_final.apply(get_kpi, axis=1)

        # กราฟเปรียบเทียบ
        fig_p = px.bar(prog_final, x="หลักสูตร", y=["KPI_Score", "Weight", "Titles"], 
                       barmode="group", title="Program Performance Comparison",
                       color_discrete_sequence=['#1E3A8A', '#3b82f6', '#94a3b8'], height=500)
        fig_p.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Target 5.0")
        st.plotly_chart(fig_p, use_container_width=True)
        
        st.dataframe(prog_final[['หลักสูตร', 'Titles', 'Weight', 'KPI_Score']].sort_values("KPI_Score", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("#### 🏛 Faculty Performance")
        df_fac_mapped = df_research.drop_duplicates(subset=['ชื่อเรื่อง']).merge(
            df_master[['Name-surname', 'คณะ']], left_on="ผู้เขียน", right_on="Name-surname", how="left"
        )
        if year_filter != "All Years": df_fac_mapped = df_fac_mapped[df_fac_mapped["ปี"] == int(year_filter)]
        
        fac_agg = df_fac_mapped.groupby(["ปี", "คณะ"]).agg(
            Titles=("ชื่อเรื่อง", "count"),
            Weight=("คะแนน", "sum")
        ).reset_index().sort_values(["ปี", "Weight"], ascending=[False, False])
        
        st.plotly_chart(px.bar(fac_agg, x="ปี", y="Titles", color="คณะ", barmode="group"), use_container_width=True)
        st.markdown("##### 📋 Faculty Summary Table")
        st.dataframe(fac_agg, use_container_width=True, hide_index=True)

# ==========================================
# 5. Admin: Submit Research (With Validation)
# ==========================================
elif choice == "✍️ Submit Research":
    st.markdown("### ✍️ Add New Research Publication")
    with st.form("entry_form", clear_on_submit=True):
        title = st.text_input("Research Title (Required)").strip()
        col_y, col_j = st.columns(2)
        year = col_y.number_input("Academic Year (B.E.)", 2560, 2600, 2567)
        db = col_j.selectbox("Journal Database", list(SCORE_MAP.keys()))
        authors = st.multiselect("Select Author(s) - You can select multiple", df_master["Name-surname"].unique().tolist())
        
        submit = st.form_submit_button("Save to Cloud")
        
        if submit:
            # Check for Duplicates
            existing = df_research["ชื่อเรื่อง"].str.lower().tolist()
            if not title or not authors:
                st.error("❌ Please provide both Title and at least one Author.")
            elif title.lower() in existing:
                st.warning(f"⚠️ Duplicate Found: '{title}' is already in the system. Entry ignored.")
            else:
                for author in authors:
                    save_to_sheet({"ชื่อเรื่อง": title, "ปี": year, "ฐานวารสาร": db, "คะแนน": SCORE_MAP[db], "ผู้เขียน": author})
                st.success("✅ Successfully Recorded!")
                st.cache_data.clear()
                st.rerun()

# ==========================================
# 6. Admin: Manage Database
# ==========================================
elif choice == "⚙️ Manage Database":
    st.markdown("### ⚙️ Delete or Manage Records")
    if not df_research.empty:
        titles = sorted(df_research["ชื่อเรื่อง"].unique().tolist())
        to_del = st.selectbox("Select Research Title to Delete:", titles)
        if st.button("🗑 Permanently Delete This Entry"):
            client = conn_sheets()
            ws = client.open("Research_Database").worksheet("research")
            # ลบทุกแถวที่ชื่อเรื่องนี้ปรากฏ (เพราะหนึ่งเรื่องอาจมีหลายผู้เขียน)
            cells = ws.findall(to_del)
            rows_to_del = sorted([c.row for c in cells], reverse=True)
            for r in rows_to_del:
                ws.delete_rows(r)
            st.success(f"Deleted all records for: {to_del}")
            st.cache_data.clear()
            st.rerun()
