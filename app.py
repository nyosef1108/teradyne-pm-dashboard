import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. הגדרות דף ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")

# --- 2. לוגיקת תאריכים וצבעים ---
def adjust_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

def apply_color(row):
    val = row.get("Next Date", "")
    colors = [''] * len(row)
    try:
        idx = row.index.get_loc("Next Date")
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        if date_obj < today: colors[idx] = 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= (today + timedelta(days=7)): colors[idx] = 'background-color: #fffd8d;'
        else: colors[idx] = 'background-color: #90ee90;'
    except: pass
    return colors

# --- 3. ניהול מצב הנתונים (Session State) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame(columns=["Model", "Activity", "Group", "Frequency", "Last Date Done", "Next Date"])

# --- 4. אבטחה וכניסה ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 ICPE Lab PM Login")
    with st.form("login"):
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.form_submit_button("Login"):
            # כאן נשאר רק ה-Credentials ב-Secrets
            try:
                creds = st.secrets["credentials"]
                if u == creds["admin_name"] and p == creds["admin_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Access Denied")
            except: st.error("Please set [credentials] in Streamlit Secrets")
    st.stop()

# --- 5. ממשק המערכת ---
page = st.sidebar.radio("ניווט", ["לוח בקרה PM", "ניהול וטעינת נתונים"])

# --- דף 1: לוח בקרה PM ---
if page == "לוח בקרה PM":
    st.title("🛡️ PM Dashboard")
    
    if st.session_state.main_df.empty:
        st.info("אין נתונים בזיכרון. עבור לדף הניהול כדי לטעון קובץ או להזין נתונים.")
        st.stop()

    display_df = st.session_state.main_df.copy()
    display_df.insert(0, "Update Status", False)
    
    edited_df = st.data_editor(
        display_df.style.apply(apply_color, axis=1),
        column_config={"Update Status": st.column_config.CheckboxColumn("V")},
        use_container_width=True, hide_index=True, key="pm_editor"
    )

    # לוגיקת עדכון מהיר בלחיצה על V
    if st.session_state.pm_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            idx = int(row_idx_str)
            if changes.get("Update Status") is True:
                months = extract_months_count(edited_df.at[idx, "Frequency"])
                if months:
                    curr = pd.to_datetime(edited_df.at[idx, "Next Date"]).date()
                    edited_df.at[idx, "Last Date Done"] = str(curr)
                    edited_df.at[idx, "Next Date"] = str(adjust_months(curr, months))
                    # עדכון הזיכרון
                    st.session_state.main_df = edited_df.drop(columns=["Update Status"])
                    st.rerun()

# --- דף 2: ניהול וטעינת נתונים ---
elif page == "ניהול וטעינת נתונים":
    st.title("⚙️ ניהול נתונים ידני")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. טעינת גרסה (Upload)")
        uploaded_file = st.file_uploader("גרור כאן את קובץ ה-JSON ששמרת", type="json")
        if uploaded_file is not None:
            data = json.load(uploaded_file)
            st.session_state.main_df = pd.DataFrame(data)
            st.success("הנתונים נטענו בהצלחה לזיכרון!")

    with col2:
        st.subheader("2. גיבוי נתונים (Download)")
        if not st.session_state.main_df.empty:
            json_data = st.session_state.main_df.to_json(orient="records", indent=4, force_ascii=False)
            st.download_button(
                label="📥 הורד גרסה נוכחית למחשב",
                data=json_data,
                file_name=f"pm_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )

    st.divider()
    st.subheader("3. עריכה ידנית / הדבקה מאקסל")
    edited_admin = st.data_editor(st.session_state.main_df, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 שמור שינויים לזיכרון האפליקציה"):
        st.session_state.main_df = edited_admin
        st.success("השינויים נשמרו בזיכרון האפליקציה (אל תשכח להוריד גיבוי למחשב!)")
