import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. הגדרות דף ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
JSON_FILE = "pm_data.json"

# --- 2. ניהול נתונים ---
def load_data():
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def save_data(df):
    # הסרת עמודות ממשק (UI) בלבד לפני שמירה לקובץ
    cols_to_drop = ["Update Status", "Undo"]
    save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    data = save_df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים חכמה ---
def adjust_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. פונקציית צביעה ---
def apply_color(row):
    val = row["Next Date"]
    colors = [''] * len(row)
    try:
        idx = row.index.get_loc("Next Date")
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today: 
            colors[idx] = 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: 
            colors[idx] = 'background-color: #fffd8d; color: black;'
        else: 
            colors[idx] = 'background-color: #90ee90; color: black;'
    except: 
        pass
    return colors

# --- 5. מנגנון כניסה (Login) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 כניסה למערכת ICPE Lab")
    with st.form("login_gate"):
        u_input = st.text_input("שם משתמש")
        p_input = st.text_input("סיסמה", type="password")
        if st.form_submit_button("התחבר"):
            try:
                creds = st.secrets["credentials"]
                if u_input == creds["admin_name"] and p_input == creds["admin_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")
            except Exception:
                st.error("שגיאה בתצורת ה-Secrets בשרת")
    st.stop()

# --- 6. תפריט ניווט (מוצג רק לאחר התחברות) ---
st.sidebar.title(f"שלום, {st.secrets['credentials']['admin_name']}")
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "ניהול נתונים (Admin)"])

if st.sidebar.button("התנתק"):
    st.session_state.authenticated = False
    st.rerun()

# --- דף 1: לוח בקרה PM ---
if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Management System")
    
    if 'main_df' not in st.session_state:
        st.session_state.main_df = load_data()

    if st.session_state.main_df.empty:
        st.warning("בסיס הנתונים ריק. נא לעבור לדף הניהול להוספת נתונים.")
        st.stop()

    display_df = st.session_state.main_df.copy()
    display_df.insert(0, "Update Status", False)
    display_df.insert(1, "Undo", False)
    
    styled_df = display_df.style.apply(apply_color, axis=1)

    all_cols = display_df.columns.tolist()
    last_two_cols = all_cols[-2:] 
    
    col_config = {
        "Update Status": st.column_config.CheckboxColumn("Confirm PM"),
        "Undo": st.column_config.CheckboxColumn("Undo"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    }
    
    for col in last_two_cols:
        if col not in ["Update Status", "Undo", "Next Date", "Last Date Done"]:
            col_config[col] = None 

    edited_df = st.data_editor(
        styled_df, 
        column_config=col_config, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic", 
        key="pm_dashboard_editor"
    )

    if st.button("💾 שמור שינויים ידניים"):
        save_data(edited_df)
        st.session_state.main_df = load_data()
        st.success("השינויים נשמרו!")
        st.rerun()

    if st.session_state.pm_dashboard_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_dashboard_editor["edited_rows"].items():
            row_idx = int(row_idx_str)
            months = extract_months_count(edited_df.at[row_idx, "Frequency"])
            
            if changes.get("Update Status") is True:
                curr = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                edited_df.at[row_idx, "Last Date Done"] = str(curr)
                edited_df.at[row_idx, "Next Date"] = str(adjust_months(curr, months))
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.rerun()
                
            if changes.get("Undo") is True:
                curr_l = pd.to_datetime(edited_df.at[row_idx, "Last Date Done"]).date()
                edited_df.at[row_idx, "Next Date"] = str(curr_l)
                edited_df.at[row_idx, "Last Date Done"] = str(adjust_months(curr_l, -months))
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.rerun()

# --- דף 2: ניהול נתונים (Admin) ---
elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ הגדרות בסיס נתונים")
    st.info("כאן ניתן להוסיף שורות חדשות, למחוק שורות קיימות ולערוך את כל השדות ללא הגבלה.")
    
    admin_df = load_data()
    edited_admin = st.data_editor(
        admin_df, 
        use_container_width=True, 
        num_rows="dynamic", 
        key="admin_raw_editor"
    )
    
    if st.button("💾 שמור בסיס נתונים סופי"):
        save_data(edited_admin)
        st.session_state.main_df = load_data()
        st.success("בסיס הנתונים עודכן בהצלחה!")
        st.rerun()
