import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import time

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

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e:
            st.error(f"❌ Cannot load '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_sheet(sheet_name, new_row_dict):
    client = conn_sheets()
    if client:
        try:
            sh = client.open("Research_Database")
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(list(new_row_dict.values()))
        except Exception as e:
            st.error(f"❌ Save Failed: {e}")

# ==========================================
# 2. Page Configuration & Header with Logo
# ==========================================
st.set_page_config(page_title="Research Management System - STIU", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1E3A8A; }
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION WITH LOGO ---
col1, col2 = st.columns([1, 5])
with col1:
    try:
        # พยายามโหลดไฟล์ logo.jpg
        st.image("logo.jpg", width=120)
    except:
        st.info("🏫 STIU LOGO")

with col2:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style="margin-bottom: 0px;">St Teresa International University</h1>
            <p style="font-size: 1.2rem; color: #64748b;">Research Management & KPI Tracking System</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Load Data
df_master = load_sheet_data("masters")
df_research = load_sheet_data("research")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD")

if df_master.empty:
    st.error("⚠️ Master Data Not Found. Please check Google Sheets.")
    st.stop()

# Data Cleaning
if not df_research.empty:
    df_research['คะแนน'] = pd.to_numeric(df_research['คะแนน'], errors='coerce').fillna(0.0)
    df_research['ปี'] = pd.to_numeric(df_research['ปี'], errors='coerce').fillna(0).astype(int)
else:
    df_research = pd.DataFrame(columns=["ชื่อเรื่อง", "ปี", "ฐานวารสาร", "คะแนน", "ผู้เขียน"])

SCORE_MAP = {"TCI1": 0.8, "TCI2": 0.6, "Scopus Q1": 1.0, "Scopus Q2": 1.0, "Scopus Q3": 1.0, "Scopus Q4": 1.0}

# ==========================================
# 3. Sidebar (English Menus)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

with st.sidebar:
    st.image("logo.jpg", width=100) if 'logo.jpg' else st.write("### STIU")
    st.markdown("### 🧭 Main Navigation")
    
    # Menu names in English
    menu_options = ["📊 Performance Dashboard", "✍️ Submit Publication", "⚙️ Manage Database"]
    menu = st.radio("Select Page:", menu_options)
    
    st.divider()
    if not st.session_state.logged_in:
        st.markdown("#### Admin Access")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect Password")
    else:
        st.success("Welcome, Admin")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.divider()
    all_years = sorted(df_research[df_research["ปี"] > 0]["ปี"].unique().tolist())
    year_filter = st.selectbox("📅 Year Filter (B.E.):", ["All Years"] + [str(y) for y in all_years])

# ==========================================
# 4. Performance Dashboard
# ==========================================
if menu == "📊 Performance Dashboard":
    st.subheader(f"📈 Research Performance: {year_filter}")
    
    df_filtered = df_research.copy()
    if year_filter != "All Years":
        df_filtered = df_filtered[df_filtered["ปี"] == int(year_filter)]
    
    if df_filtered.empty:
        st.info("No research records found for the selected period.")
    else:
        # Key Metrics
        m1, m2, m3 = st.columns(3)
        unique_titles = df_filtered.drop_duplicates(subset=['ชื่อเรื่อง'])
        m1.metric("Total Publications", f"{len(unique_titles)} Titles")
        m2.metric("Active Researchers", f"{df_filtered['ผู้เขียน'].nunique()} Persons")
        m3.metric("Weighted Score Sum", f"{unique_titles['คะแนน'].sum():.2f}")

        # Chart
        st.markdown("#### 📊 Publications by Database")
        db_summary = unique_titles.groupby("ฐานวารสาร").size().reset_index(name='Count')
        fig = px.bar(db_summary, x='ฐานวารสาร', y='Count', color='ฐานวารสาร', text_auto=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 Publication Details")
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# ==========================================
# 5. Submit Publication
# ==========================================
elif menu == "✍️ Submit Publication":
    if not st.session_state.logged_in:
        st.warning("🔒 Please login as Admin to submit new records.")
    else:
        st.subheader("✍️ Register New Publication")
        with st.form("entry_form", clear_on_submit=True):
            title = st.text_input("Research Title")
            c1, c2 = st.columns(2)
            y_in = c1.number_input("Year (B.E.)", 2560, 2600, 2568)
            db_in = c2.selectbox("Journal Database", list(SCORE_MAP.keys()))
            authors = st.multiselect("Select Authors (from Master List)", df_master["Name-surname"].unique().tolist())
            
            if st.form_submit_button("Save to Database"):
                if title and authors:
                    for a in authors:
                        save_to_sheet("research", {
                            "ชื่อเรื่อง": title, "ปี": y_in, 
                            "ฐานวารสาร": db_in, "คะแนน": SCORE_MAP[db_in], 
                            "ผู้เขียน": a
                        })
                    st.success("✅ Record successfully saved!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Please provide both Title and Authors.")

# ==========================================
# 6. Manage Database
# ==========================================
elif menu == "⚙️ Manage Database":
    if not st.session_state.logged_in:
        st.warning("🔒 Please login as Admin to manage database.")
    else:
        st.subheader("⚙️ Database Management")
        if df_research.empty:
            st.info("The database is currently empty.")
        else:
            st.markdown("#### Delete Entry")
            # List unique titles for deletion
            df_manage = df_research.drop_duplicates(subset=['ชื่อเรื่อง', 'ปี']).sort_values('ปี', ascending=False)
            opts = ["-- Select Entry to Delete --"] + [f"{r['ปี']} | {r['ชื่อเรื่อง']}" for _, r in df_manage.iterrows()]
            sel = st.selectbox("Search and Select:", opts)
            
            if sel != "-- Select Entry to Delete --":
                target_title = sel.split(" | ")[1].strip()
                if st.button("🚨 Confirm Delete"):
                    with st.spinner("Deleting from Google Sheets..."):
                        client = conn_sheets()
                        ws = client.open("Research_Database").worksheet("research")
                        all_rec = ws.get_all_records()
                        rows_to_del = [i + 2 for i, r in enumerate(all_rec) if str(r.get('ชื่อเรื่อง')).strip() == target_title]
                        for r in sorted(rows_to_del, reverse=True):
                            ws.delete_rows(r)
                            time.sleep(0.3)
                        st.success("🗑️ Record deleted successfully!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
