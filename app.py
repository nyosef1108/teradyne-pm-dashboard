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
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    return pd.DataFrame()

def save_data(df):
    cols_to_drop = ["Update Status", "Undo"]
    save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    data = save_df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים ---
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
        if date_obj < today: colors[idx] = 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: colors[idx] = 'background-color: #fffd8d; color: black;'
        else: colors[idx] = 'background-color: #90ee90; color: black;'
    except: pass
    return colors

# --- 5. ניהול התחברות ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

st.sidebar.title("תפריט")
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "Admin Settings"])

# --- דף PM Dashboard ---
if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Management System")
    if 'main_df' not in st.session_state:
        st.session_state.main_df = load_data()

    if st.session_state.main_df.empty:
        st.warning("בסיס הנתונים ריק. נא לפנות למנהל.")
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

    edited_df = st.data_editor(styled_df, column_config=col_config, use_container_width=True, hide_index=True, num_rows="dynamic", key="pm_editor_v9")

    if st.button("💾 שמור שינויים"):
        save_data(edited_df)
        st.session_state.main_df = load_data()
        st.success("נשמר!")
        st.rerun()

    # לוגיקת כפתורים (Update/Undo)
    if st.session_state.pm_editor_v9["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor_v9["edited_rows"].items():
            row_idx = int(row_idx_str)
            months = extract_months_count(edited_df.at[row_idx, "Frequency"])
            if changes.get("Update Status") is True:
                curr = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                edited_df.at[row_idx, "Last Date Done"], edited_df.at[row_idx, "Next Date"] = str(curr), str(adjust_months(curr, months))
                save_data(edited_df); st.session_state.main_df = load_data(); st.rerun()
            if changes.get("Undo") is True:
                curr_l = pd.to_datetime(edited_df.at[row_idx, "Last Date Done"]).date()
                edited_df.at[row_idx, "Next Date"], edited_df.at[row_idx, "Last Date Done"] = str(curr_l), str(adjust_months(curr_l, -months))
                save_data(edited_df); st.session_state.main_df = load_data(); st.rerun()

# --- דף Admin (חיבור מאובטח מהסיקרטס) ---
elif page == "Admin Settings":
    st.title("⚙️ ניהול מערכת")

    if not st.session_state.authenticated:
        with st.form("login_form"):
            u_input = st.text_input("שם משתמש")
            p_input = st.text_input("סיסמה", type="password")
            submit = st.form_submit_button("התחבר")
            
            if submit:
                # בדיקה מול st.secrets
                if u_input == st.secrets["admin_user"] and p_input == st.secrets["admin_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים")
    else:
        st.success(f"מחובר כ: {st.secrets['admin_user']}")
        if st.button("התנתק"):
            st.session_state.authenticated = False
            st.rerun()
        
        st.divider()
        st.subheader("עריכת בסיס הנתונים")
        admin_df = load_data()
        edited_admin = st.data_editor(admin_df, use_container_width=True, num_rows="dynamic", key="admin_edit")
        if st.button("💾 שמור הכל (Admin)"):
            save_data(edited_admin)
            st.session_state.main_df = load_data()
            st.success("עודכן!")
            st.rerun()def extract_months_count(freq_str):
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
        if date_obj < today: colors[idx] = 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: colors[idx] = 'background-color: #fffd8d; color: black;'
        else: colors[idx] = 'background-color: #90ee90; color: black;'
    except: pass
    return colors

# --- 5. ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")

if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

# הכנת גרסת תצוגה
display_df = st.session_state.main_df.copy()
display_df.insert(0, "Update Status", False)
display_df.insert(1, "Undo", False)

styled_df = display_df.style.apply(apply_color, axis=1)

# זיהוי שמות העמודות האחרונות כדי להסתיר אותן
all_cols = display_df.columns.tolist()
last_two_cols = all_cols[-2:] # שתי העמודות האחרונות ב-DataFrame

# יצירת מילון הגדרות עמודות דינמי
col_config = {
    "Update Status": st.column_config.CheckboxColumn("Confirm PM"),
    "Undo": st.column_config.CheckboxColumn("Undo"),
    "Next Date": st.column_config.Column(disabled=True),
    "Last Date Done": st.column_config.Column(disabled=True),
}

# הסתרה אוטומטית של שתי העמודות האחרונות
for col in last_two_cols:
    if col not in ["Update Status", "Undo", "Next Date", "Last Date Done"]:
        col_config[col] = None 

edited_df = st.data_editor(
    styled_df,
    column_config=col_config,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor_v7"
)

# כפתור שמירה
if st.button("💾 Save Manual Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.rerun()

# לוגיקת כפתורים
if st.session_state.pm_editor_v7["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_v7["edited_rows"].items():
        row_idx = int(row_idx_str)
        months = extract_months_count(edited_df.at[row_idx, "Frequency"])
        
        if changes.get("Update Status") is True:
            current_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
            new_next = adjust_months(current_next, months)
            edited_df.at[row_idx, "Last Date Done"] = str(current_next)
            edited_df.at[row_idx, "Next Date"] = str(new_next)
            save_data(edited_df)
            st.session_state.main_df = load_data()
            st.rerun()

        if changes.get("Undo") is True:
            current_last = pd.to_datetime(edited_df.at[row_idx, "Last Date Done"]).date()
            new_last_done = adjust_months(current_last, -months)
            edited_df.at[row_idx, "Next Date"] = str(current_last)
            edited_df.at[row_idx, "Last Date Done"] = str(new_last_done)
            save_data(edited_df)
            st.session_state.main_df = load_data()
            st.rerun()
