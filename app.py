# =========================================================
# Research Management & KPI Dashboard (Executive Version)
# St Teresa International University
# =========================================================

import streamlit as st
import pandas as pd
import gspread
import math
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# 1. DATABASE CONNECTION (SAFE & SCALABLE)
# =========================================================
@st.cache_resource
def conn_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def load_sheet(sheet_name):
    ws = conn_sheets().open("Research_Database").worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()
    return df

def safe_append_row(sheet_name, row_dict):
    ws = conn_sheets().open("Research_Database").worksheet(sheet_name)
    headers = ws.row_values(1)

    # ตรวจสอบ column
    missing = set(row_dict.keys()) - set(headers)
    if missing:
        st.error(f"❌ Column mismatch: {missing}")
        return

    row = [row_dict.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

# =========================================================
# 2. PAGE CONFIGURATION & EXECUTIVE UI
# =========================================================
st.set_page_config(
    page_title="STIU Research KPI System",
    layout="wide"
)

st.markdown("""
<style>
html, body {
    font-family: 'Sarabun', sans-serif;
    background-color: #F8FAFC;
}
h1, h2, h3 {
    color: #1E3A8A;
    font-weight: 700;
}
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    border-left: 6px solid #1E40AF;
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1E40AF;
}
.kpi-label {
    font-size: 0.95rem;
    color: #475569;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. LOAD DATA
# =========================================================
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

df_master = load_sheet("masters")
df_research = load_sheet("research")

df_research["คะแนน"] = pd.to_numeric(df_research["คะแนน"], errors="coerce").fillna(0)
df_research["ปี"] = pd.to_numeric(df_research["ปี"], errors="coerce").fillna(0).astype(int)

SCORE_MAP = {
    "Scopus Q1-4": 1.0,
    "TCI Group 1": 0.8,
    "TCI Group 2": 0.6
}

# =========================================================
# 4. SIDEBAR
# =========================================================
if "login" not in st.session_state:
    st.session_state.login = False

with st.sidebar:
    st.markdown("### Navigation")
    menu = st.radio(
        "Menu",
        ["Dashboard", "Submit Research", "Database Management"]
        if st.session_state.login else ["Dashboard"]
    )

    st.divider()

    if not st.session_state.login:
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login") and pwd == ADMIN_PASSWORD:
            st.session_state.login = True
            st.rerun()
    else:
        if st.button("Logout"):
            st.session_state.login = False
            st.rerun()

    years = sorted(df_research["ปี"].unique())
    year_filter = st.selectbox(
        "Year",
        ["All"] + [str(y) for y in years if y > 0]
    )

# =========================================================
# 5. DASHBOARD (EXECUTIVE VIEW)
# =========================================================
if menu == "Dashboard":
    df_f = df_research.copy()
    if year_filter != "All":
        df_f = df_f[df_f["ปี"] == int(year_filter)]

    df_full = df_f.merge(
        df_master[["Name-surname", "คณะ", "หลักสูตร"]],
        left_on="ผู้เขียน",
        right_on="Name-surname",
        how="left"
    )

    df_unique = df_f.drop_duplicates(subset=["ชื่อเรื่อง"])
    df_prog_unique = df_full.drop_duplicates(subset=["ชื่อเรื่อง", "หลักสูตร"])

    # ================= KPI SUMMARY =================
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Publications</div>
            <div class="kpi-value">{len(df_unique)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Research Score</div>
            <div class="kpi-value">{df_unique["คะแนน"].sum():.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        avg = df_unique["คะแนน"].sum() / max(df_master["Name-surname"].nunique(), 1)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Average Score per Staff</div>
            <div class="kpi-value">{avg:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ================= TREND =================
    yearly = df_unique.groupby("ปี")["คะแนน"].sum().reset_index()
    fig = go.Figure()
    fig.add_bar(x=yearly["ปี"], y=yearly["คะแนน"], name="Total Score")
    fig.update_layout(
        title="Research Output Trend",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ================= PROGRAM KPI =================
    st.markdown("## Program KPI Performance")
    member_prog = df_master.groupby("หลักสูตร")["Name-surname"].nunique().to_dict()
    prog_sum = df_prog_unique.groupby("หลักสูตร")["คะแนน"].sum().reset_index()

    def calc_prog_kpi(row):
        n = member_prog.get(row["หลักสูตร"], 1)
        x = 60 if row["หลักสูตร"] == "Ph.D-Admin" else 40
        return min((((row["คะแนน"] / n) * 100) / x) * 5, 5)

    prog_sum["KPI"] = prog_sum.apply(calc_prog_kpi, axis=1)

    st.dataframe(
        prog_sum.sort_values("KPI", ascending=False),
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# 6. SUBMIT RESEARCH (ADMIN)
# =========================================================
elif menu == "Submit Research":
    st.markdown("## Register Research Output")

    with st.form("submit_form", clear_on_submit=True):
        title = st.text_input("Title")
        year = st.number_input("Year (B.E.)", 2560, 2600, 2568)
        journal = st.selectbox("Journal Type", list(SCORE_MAP.keys()))
        authors = st.multiselect(
            "Authors",
            sorted(df_master["Name-surname"].unique())
        )

        if st.form_submit_button("Save"):
            for a in authors:
                safe_append_row("research", {
                    "ชื่อเรื่อง": title,
                    "ปี": year,
                    "ฐานวารสาร": journal,
                    "คะแนน": SCORE_MAP[journal],
                    "ผู้เขียน": a
                })
            st.success("Saved successfully")
            st.cache_data.clear()
            st.rerun()

# =========================================================
# 7. DATABASE MANAGEMENT (ADMIN)
# =========================================================
elif menu == "Database Management":
    st.markdown("## Database Management")

    unique_entries = df_research.drop_duplicates(
        subset=["ชื่อเรื่อง", "ปี", "ฐานวารสาร"]
    )

    sel = st.selectbox(
        "Select entry to delete",
        ["--"] + [
            f"{r['ปี']} | {r['ชื่อเรื่อง']} | {r['ฐานวารสาร']}"
            for _, r in unique_entries.iterrows()
        ]
    )

    if sel != "--" and st.button("Confirm Delete"):
        year, title, journal = sel.split(" | ")
        ws = conn_sheets().open("Research_Database").worksheet("research")

        rows = [
            i + 2 for i, r in enumerate(ws.get_all_records())
            if str(r["ชื่อเรื่อง"]) == title
            and str(r["ปี"]) == year
            and str(r["ฐานวารสาร"]) == journal
        ]

        for r in sorted(rows, reverse=True):
            ws.delete_rows(r)

        st.success("Deleted successfully")
        st.cache_data.clear()
        st.rerun()
