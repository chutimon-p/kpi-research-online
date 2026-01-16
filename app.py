import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import math

# ==========================================
# 1. Database Connection (SAFE)
# ==========================================
@st.cache_resource
def conn_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
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
        sh = client.open("Research_Database")
        ws = sh.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        df.columns = df.columns.str.strip()
        return df
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if not client:
        return
    ws = client.open("Research_Database").worksheet(sheet_name)
    headers = ws.row_values(1)
    row = [new_row_dict.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

# ==========================================
# 2. Page Config & UI (IMPROVED)
# ==========================================
st.set_page_config(
    page_title="Research Management - STIU",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Sarabun', sans-serif;
    background-color: #F8FAFC;
}
h1, h2, h3, h4 {
    color: #1E3A8A !important;
    font-weight: 700;
}
.stMetric {
    background-color: #FFFFFF;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    border-left: 6px solid #1E40AF;
}
[data-testid="stMetricValue"] {
    font-size: 2.1rem;
    font-weight: 700;
    color: #1E40AF;
}
.ranking-card {
    background-color: #FFFFFF;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.1);
    text-align: center;
    margin-bottom: 15px;
    border-top: 6px solid #2563EB;
}
.stTabs [data-baseweb="tab"] {
    height: 46px;
    background-color: #E5E7EB;
    border-radius: 10px 10px 0 0;
    padding: 10px 16px;
    font-weight: 600;
    color: #475569;
}
.stTabs [aria-selected="true"] {
    background-color: #1E40AF !important;
    color: white !important;
}
thead tr th {
    background-color: #E5E7EB !important;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. Header
# ==========================================
h1, h2 = st.columns([1, 6])
with h1:
    try:
        st.image("logo.jpg", width=130)
    except:
        st.write("")
with h2:
    st.markdown("""
    <h1 style="margin-bottom:0;">St Teresa International University</h1>
    <p style="color:#475569;font-size:1.05rem;">
    Research Management & KPI Tracking System
    </p>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 4. Load Data
# ==========================================
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")

if df_master.empty or df_research.empty:
    st.warning("⚠️ Loading data from Google Sheets...")
    st.stop()

df_research["คะแนน"] = pd.to_numeric(df_research["คะแนน"], errors="coerce").fillna(0)
df_research["ปี"] = pd.to_numeric(df_research["ปี"], errors="coerce").fillna(0).astype(int)

SCORE_MAP = {
    "TCI1": 0.8,
    "TCI2": 0.6,
    "Scopus Q1": 1.0,
    "Scopus Q2": 1.0,
    "Scopus Q3": 1.0,
    "Scopus Q4": 1.0
}

# ==========================================
# 5. Sidebar (UNCHANGED LOGIC)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
                st.error("Wrong Password")
    else:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique())
    year_option = st.selectbox("📅 Year Filter:", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 6. Dashboard & Reports (LOGIC SAME)
# ==========================================
if menu == "📊 Dashboard & Reports":

    df_filtered = df_research.copy()
    if year_option != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_option)]

    df_full = df_filtered.merge(
        df_master[["Name-surname", "คณะ", "หลักสูตร"]],
        left_on="ผู้เขียน",
        right_on="Name-surname",
        how="left"
    )

    df_unique_total = df_filtered.drop_duplicates(subset=["ชื่อเรื่อง"])
    df_unique_agency = df_full.drop_duplicates(subset=["ชื่อเรื่อง", "หลักสูตร"])

    t0, t1, t2, t3, t4, t5, t6 = st.tabs([
        "🏛 Overview", "🎓 Program KPI", "👤 Researcher Profile",
        "🏢 Faculty KPI", "📋 Master Database", "🔍 Verification", "🚀 KPI Improvement Plan"
    ])

    # ---------- Overview ----------
    with t0:
        inst = df_unique_total.groupby("ปี").agg(
            Titles=("ชื่อเรื่อง", "count"),
            Total_Weight=("คะแนน", "sum")
        ).reset_index()

        fig = go.Figure()
        fig.add_bar(x=inst["ปี"], y=inst["Titles"], name="Titles")
        fig.add_scatter(
            x=inst["ปี"], y=inst["Total_Weight"],
            yaxis="y2", name="Score"
        )
        fig.update_layout(
            yaxis2=dict(overlaying="y", side="right"),
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------- Program KPI ----------
    with t1:
        all_progs = df_master[["หลักสูตร", "คณะ"]].drop_duplicates()
        members = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
        prog_sum = df_unique_agency.groupby("หลักสูตร")["คะแนน"].sum().reset_index()
        report = all_progs.merge(prog_sum, on="หลักสูตร", how="left").fillna(0)

        def calc_prog(row):
            n = members.get(row["หลักสูตร"], 1)
            g40 = ["G-Dip TH", "G-Dip Inter", "M. Ed-Admin", "M. Ed-LMS", "MBA", "MPH"]
            x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else (40 if row["หลักสูตร"] in g40 else 20)
            return round(min((((row["คะแนน"] / n) * 100) / x) * 5, 5), 2)

        report["KPI Score"] = report.apply(calc_prog, axis=1)

        st.plotly_chart(
            px.bar(
                report.sort_values("KPI Score"),
                x="KPI Score", y="หลักสูตร",
                orientation="h", color="คณะ",
                template="plotly_white",
                range_x=[0, 5.5], text="KPI Score"
            ).add_vline(x=5.0, line_dash="dash"),
            use_container_width=True
        )

    # ---------- Researcher ----------
    with t2:
        rank = df_filtered.groupby("ผู้เขียน")["คะแนน"].sum().reset_index().sort_values("คะแนน", ascending=False).head(3)
        cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        for i, col in enumerate(cols):
            if i < len(rank):
                r = rank.iloc[i]
                col.markdown(
                    f"<div class='ranking-card'><h3>{medals[i]}</h3><b>{r['ผู้เขียน']}</b><br>Score: {r['คะแนน']:.2f}</div>",
                    unsafe_allow_html=True
                )

    # ---------- Faculty ----------
    with t3:
        members = df_master.groupby("คณะ")["Name-surname"].nunique().to_dict()
        fac_unique = df_full.drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"])
        fac_sum = fac_unique.groupby("คณะ")["คะแนน"].sum().reset_index()

        def fac_kpi(row):
            y = 30 if row["คณะ"] in ["คณะสาธารณสุขศาสตร์", "คณะพยาบาลศาสตร์"] else 20
            n = members.get(row["คณะ"], 1)
            return round(min((((row["คะแนน"] / n) * 100) / y) * 5, 5), 2)

        fac_sum["KPI"] = fac_sum.apply(fac_kpi, axis=1)

        st.plotly_chart(
            px.bar(
                fac_sum.sort_values("KPI"),
                x="KPI", y="คณะ",
                orientation="h",
                template="plotly_white",
                range_x=[0, 5.5], text="KPI"
            ).add_vline(x=5.0, line_dash="dash"),
            use_container_width=True
        )

    # ---------- Master ----------
    with t4:
        st.dataframe(df_master, use_container_width=True, hide_index=True)

    # ---------- Verification ----------
    with t5:
        mode = st.radio("Mode:", ["Program", "Faculty"], horizontal=True)
        if mode == "Program":
            sel = st.selectbox("Select Program:", sorted(df_master["หลักสูตร"].unique()))
            st.dataframe(df_unique_agency[df_unique_agency["หลักสูตร"] == sel])
        else:
            sel = st.selectbox("Select Faculty:", sorted(df_master["คณะ"].unique()))
            st.dataframe(df_full[df_full["คณะ"] == sel].drop_duplicates(subset=["ชื่อเรื่อง", "คณะ"]))

    # ---------- Improvement Plan ----------
    with t6:
        st.info("🚀 KPI Improvement Plan (Road to 5.0)")

# ==========================================
# 7. Admin Sections (UNCHANGED)
# ==========================================
elif menu == "✍️ Submit Research":
    st.markdown("### ✍️ Register Publication")
    with st.form("entry_form", clear_on_submit=True):
        title = st.text_input("Title")
        year = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        journal = st.selectbox("Journal Database", list(SCORE_MAP.keys()))
        authors = st.multiselect("Authors", df_master["Name-surname"].unique())
        if st.form_submit_button("Save"):
            for a in authors:
                save_to_sheet("research", {
                    "ชื่อเรื่อง": title,
                    "ปี": year,
                    "ฐานวารสาร": journal,
                    "คะแนน": SCORE_MAP[journal],
                    "ผู้เขียน": a
                })
            st.success("Saved")
            st.cache_data.clear()
            st.rerun()

elif menu == "⚙️ Manage Database":
    st.markdown("### ⚙️ Database Management")
    df_m = df_research.drop_duplicates(subset=["ชื่อเรื่อง", "ปี", "ฐานวารสาร"])
    sel = st.selectbox(
        "Delete Entry:",
        ["--"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']} | {r['ฐานวารสาร']}" for _, r in df_m.iterrows()]
    )
    if sel != "--" and st.button("Confirm Delete"):
        year, title, journal = sel.split(" | ")
        ws = conn_sheets().open("Research_Database").worksheet("research")
        rows = [
            i + 2 for i, r in enumerate(ws.get_all_records())
            if str(r["ชื่อเรื่อง"]) == title and str(r["ปี"]) == year and str(r["ฐานวารสาร"]) == journal
        ]
        for r in sorted(rows, reverse=True):
            ws.delete_rows(r)
        st.success("Deleted")
        st.cache_data.clear()
        st.rerun()
