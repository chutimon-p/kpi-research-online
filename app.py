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
# 2. Modern & Clean UI CSS (ปรับปรุงใหม่ให้สบายตา)
# ==========================================
st.set_page_config(page_title="Research Management - STIU", layout="wide")

st.markdown("""
    <style>
    /* ปรับพื้นหลังหลักให้เป็นโทนสบายตา */
    .stApp {
        background-color: #0F172A;
    }

    /* ปรับแต่งตัวเลข Metric ให้ดูแพง */
    [data-testid="stMetricValue"] { 
        font-size: 2.8rem; 
        color: #38BDF8; 
        font-weight: 800;
        letter-spacing: -1px;
    }
    .stMetric {
        background-color: rgba(30, 41, 59, 0.7); 
        padding: 25px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* แท็บขนาดใหญ่และชัดเจนเป็นพิเศษ (Hero Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
        padding: 10px 0px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 70px; 
        min-width: 180px;
        background-color: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        padding: 0px 30px; 
        color: #94A3B8;
        font-size: 1.4rem !important; /* ใหญ่ขึ้นมาก */
        font-weight: 700 !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(56, 189, 248, 0.1);
        color: #38BDF8;
        border-color: #38BDF8;
    }

    /* สไตล์แท็บที่ถูกเลือก */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        color: white !important;
        font-size: 1.5rem !important;
        box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
        transform: translateY(-5px);
        border: none !important;
    }
    
    /* การ์ดอันดับ Ranking */
    .ranking-card {
        background-color: rgba(30, 41, 59, 0.8);
        padding: 30px; 
        border-radius: 20px; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .ranking-card:hover {
        transform: scale(1.02);
        border-color: #38BDF8;
    }

    h1, h2, h3, h4 { 
        font-family: 'Sarabun', sans-serif;
        color: #F8FAFC !important; 
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* ปรับแต่ง Scrollbar ให้ดูดี */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0F172A; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
    
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. Header & Data Loading
# ==========================================
header_col1, header_col2 = st.columns([1, 5])
with header_col1:
    try: st.image("logo.jpg", width=140)
    except: st.info("🏫 STIU LOGO")

with header_col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="margin-bottom: 0px; font-size: 2.8rem; background: linear-gradient(to right, #38BDF8, #818CF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                St Teresa International University
            </h1>
            <p style="color: #94A3B8; font-size: 1.2rem; font-weight: 500;">Research Excellence & KPI Tracking Dashboard</p>
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
# 4. Sidebar & Logic
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
with st.sidebar:
    st.markdown("### 🧭 MENU")
    menu_options = ["📊 DASHBOARD"]
    if st.session_state.logged_in:
        menu_options.insert(0, "✍️ SUBMIT")
        menu_options.append("⚙️ MANAGE")
    menu = st.radio("เลือกหน้า:", menu_options)
    st.divider()
    if not st.session_state.logged_in:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD: st.session_state.logged_in = True; st.rerun()
    else:
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
    
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_option = st.selectbox("📅 กรองปี (พ.ศ.):", ["ทั้งหมด"] + [str(y) for y in all_years])

# ==========================================
# 5. Dashboard Implementation
# ==========================================
if menu == "📊 DASHBOARD":
    df_filtered = df_research.copy()
    if year_option != "ทั้งหมด": df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]
    
    df_full_info = df_filtered.merge(df_master[['Name-surname', 'คณะ', 'หลักสูตร']], left_on="ผู้เขียน", right_on="Name-surname", how="left")
    df_unique_total = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
    df_unique_agency = df_full_info.drop_duplicates(subset=['ชื่อเรื่อง', 'หลักสูตร'])

    # Big Tabs with High Readability
    t0, t1, t2, t3, t4, t6 = st.tabs([
        "🏛 ภาพรวม", "🎓 หลักสูตร", "👤 ผู้วิจัย", 
        "🏢 คณะ", "📋 รายชื่อ", "🚀 แผนพัฒนา KPI"
    ])

    with t0:
        st.markdown("### 📈 แนวโน้มการเติบโตของงานวิจัย")
        inst_summary = df_unique_total.groupby("ปี").agg(Titles=("ชื่อเรื่อง", "count"), Total_Weight=("คะแนน", "sum")).reset_index()
        inst_summary = inst_summary[inst_summary['ปี'] > 0].sort_values("ปี")
        fig_inst = go.Figure()
        fig_inst.add_trace(go.Bar(x=inst_summary["ปี"], y=inst_summary["Titles"], name="จำนวนเรื่อง", marker_color='#3B82F6', marker_line_width=0))
        fig_inst.add_trace(go.Scatter(x=inst_summary["ปี"], y=inst_summary["Total_Weight"], name="คะแนนรวม", yaxis="y2", line=dict(color='#F43F5E', width=4, shape='spline')))
        fig_inst.update_layout(yaxis2=dict(overlaying="y", side="right"), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_inst, use_container_width=True)

    with t1:
        st.markdown("### 🎓 การบรรลุเป้าหมายรายหลักสูตร")
        prog_member_counts = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_summary = df_unique_agency.groupby("หลักสูตร").agg(Total_Score=("คะแนน", "sum")).reset_index()
        def calc_kpi(row):
            n = prog_member_counts.get(row["หลักสูตร"], 1)
            group_40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in group_40 else 20)
            return round(min((((row["Total_Score"] / n) * 100) / x) * 5, 5.0), 2)
        prog_summary["KPI Score"] = prog_summary.apply(calc_kpi, axis=1)
        st.plotly_chart(px.bar(prog_summary.sort_values("KPI Score"), x="KPI Score", y="หลักสูตร", orientation='h', range_x=[0, 5.5], text="KPI Score", template="plotly_dark", color_continuous_scale="Blues").add_vline(x=5.0, line_dash="dash", line_color="#EF4444"), use_container_width=True)

    with t2:
        st.markdown("### 🏆 นักวิจัยดีเด่น (Top 3 Ranking)")
        author_rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        r_cols = st.columns(3)
        medals = ["🥇 อันดับที่ 1", "🥈 อันดับที่ 2", "🥉 อันดับที่ 3"]
        m_colors = ["#F59E0B", "#94A3B8", "#B45309"]
        for i, (col, medal) in enumerate(zip(r_cols, medals)):
            if i < len(author_rank):
                row = author_rank.iloc[i]
                col.markdown(f'''
                    <div class="ranking-card">
                        <p style="font-size: 1.2rem; color: {m_colors[i]}; font-weight: bold;">{medal}</p>
                        <h2 style="margin: 10px 0;">{row["ผู้เขียน"]}</h2>
                        <p style="font-size: 1rem; color: #94A3B8;">คะแนนรวมสะสม</p>
                        <h1 style="color: #38BDF8 !important;">{row["คะแนน"]:.2f}</h1>
                    </div>
                ''', unsafe_allow_html=True)

    with t6:
        st.markdown("### 🚀 วิเคราะห์ส่วนต่างเพื่อบรรลุ KPI 5.0")
        p_mode = st.radio("ระดับการวางแผน:", ["รายหลักสูตร", "รายคณะ"], horizontal=True)
        
        def run_plan(name, current_sum, n, x_y):
            required_sum = (x_y * n) / 100
            gap = max(required_sum - current_sum, 0.0)
            current_kpi = min((((current_sum / n) * 100) / x_y) * 5, 5.0)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("KPI ปัจจุบัน", f"{current_kpi:.2f}")
            c2.metric("คะแนนที่ขาด", f"{gap:.2f}")
            c3.metric("จำนวนบุคลากร", n)
            
            if gap > 0:
                st.markdown("#### 📝 แนะนำประเภทงานวิจัยที่ต้องทำเพิ่ม (เลือกอย่างใดอย่างหนึ่ง)")
                sc, t1, t2 = st.columns(3)
                sc.info(f"**Scopus / Q1-4**\n\n {math.ceil(gap/1.0)} เรื่อง")
                t1.info(f"**TCI 1**\n\n {math.ceil(gap/0.8)} เรื่อง")
                t2.info(f"**TCI 2**\n\n {math.ceil(gap/0.6)} เรื่อง")
            else: st.balloons(); st.success("✅ บรรลุเป้าหมาย 5.0 เรียบร้อยแล้ว!")

        if p_mode == "รายหลักสูตร":
            sel = st.selectbox("เลือกหลักสูตร:", sorted(df_master["หลักสูตร"].unique().tolist()))
            if sel:
                curr = df_unique_agency[df_unique_agency["หลักสูตร"] == sel]["คะแนน"].sum()
                n = df_master[df_master["หลักสูตร"] == sel]["Name-surname"].nunique()
                g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
                x = 60 if sel == "Ph.D-Admin" else (40 if sel in g40 else 20)
                run_plan(sel, curr, n, x)
        else:
            sel = st.selectbox("เลือกคณะ:", sorted(df_master["คณะ"].unique().tolist()))
            if sel:
                curr = df_full_info[df_full_info["คณะ"] == sel].drop_duplicates(subset=['ชื่อเรื่อง', 'คณะ'])["คะแนน"].sum()
                n = df_master[df_master["คณะ"] == sel]["Name-surname"].nunique()
                y = 30 if sel in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
                run_plan(sel, curr, n, y)

elif menu == "✍️ SUBMIT":
    st.markdown("### ✍️ ลงทะเบียนผลงานวิจัย")
    with st.form("entry_form"):
        t_in = st.text_input("ชื่อเรื่อง (Title)")
        c1, c2 = st.columns(2)
        with c1: y_in = st.number_input("ปี พ.ศ.", 2560, 2600, 2568)
        with c2: j_in = st.selectbox("ฐานข้อมูลวารสาร", list(SCORE_MAP.keys()))
        a_in = st.multiselect("ชื่อผู้วิจัย", df_master["Name-surname"].unique().tolist())
        if st.form_submit_button("บันทึกข้อมูล"):
            if t_in and a_in:
                for a in a_in: save_to_sheet("research", {"ชื่อเรื่อง": t_in, "ปี": y_in, "ฐานวารสาร": j_in, "คะแนน": SCORE_MAP[j_in], "ผู้เขียน": a})
                st.success("บันทึกสำเร็จ!"); st.cache_data.clear(); st.rerun()

elif menu == "⚙️ MANAGE":
    st.markdown("### ⚙️ จัดการฐานข้อมูล")
    df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี', 'ฐานวารสาร'])
    sel = st.selectbox("ลบข้อมูลเรื่อง:", ["-- เลือก --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()])
    if sel != "-- เลือก --" and st.button("ยืนยันการลบ"):
        target = sel.split(" | ")[1].strip()
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [i + 2 for i, row in enumerate(ws.get_all_records()) if str(row.get('ชื่อเรื่อง')).strip() == target]
        for r in sorted(rows, reverse=True): ws.delete_rows(r)
        st.success("ลบข้อมูลแล้ว!"); st.cache_data.clear(); st.rerun()
