import streamlit as st
import pandas as pd
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. הגדרות דף ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
JSON_FILE = "pm_data.json"
BACKUP_FILE = "pm_data_backup.json"

# --- 2. ניהול נתונים ---
def load_data():
    for file_path in [JSON_FILE, BACKUP_FILE]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return pd.DataFrame(data)
            except Exception:
                continue
    # אם הקובץ ריק, מייצרים את המבנה המקורי שלך בדיוק
    return pd.DataFrame(columns=["Model", "Activity", "Group", "Frequency", "Last Date Done", "Next Date"])

def save_data(df):
    try:
        # ניקוי עמודות ממשק לפני שמירה
        cols_to_drop = ["Update Status", "Undo"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        # שמירת הנתונים כפי שהם
        data = save_df.to_dict(orient="records")
        temp_file = "temp_data.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        shutil.copy2(temp_file, JSON_FILE)
        shutil.move(temp_file, BACKUP_FILE)
        return True
    except Exception as e:
        st.error(f"שגיאת שמירה: {e}")
        return False

# --- 3. לוגיקת תאריכים ---
def adjust_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    if pd.isna(freq_str): return None
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

# --- 4. פונקציית צביעה ---
def apply_color(row):
    val = row.get("Next Date", "")
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

# --- 5. מנגנון כניסה ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 כניסה למערכת ICPE Lab")
    with st.form("login"):
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type="password")
        if st.form_submit_button("התחבר"):
            creds = st.secrets["credentials"]
            if u == creds["admin_name"] and p == creds["admin_password"]:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("פרטים שגויים")
    st.stop()

# --- 6. ניווט ---
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "ניהול נתונים (Admin)"])

# --- דף 1: לוח בקרה PM ---
if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Management System")
    df = load_data()
    if df.empty:
        st.info("בסיס הנתונים ריק. הוסף נתונים בדף הניהול.")
        st.stop()

    display_df = df.copy()
    display_df.insert(0, "Update Status", False)
    display_df.insert(1, "Undo", False)
    
    col_config = {
        "Update Status": st.column_config.CheckboxColumn("V"),
        "Undo": st.column_config.CheckboxColumn("Undo"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    }

    # תצוגת הטבלה
    edited_df = st.data_editor(display_df.style.apply(apply_color, axis=1), 
                               column_config=col_config, use_container_width=True, hide_index=True, key="pm_editor")

    if st.button("💾 שמור שינויים"):
        save_data(edited_df)
        st.success("נשמר!")
        st.rerun()

    # עדכון אוטומטי בלחיצה על V
    if st.session_state.pm_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            idx = int(row_idx_str)
            months = extract_months_count(edited_df.at[idx, "Frequency"])
            if not months: continue
            
            if changes.get("Update Status") is True:
                curr = pd.to_datetime(edited_df.at[idx, "Next Date"]).date()
                edited_df.at[idx, "Last Date Done"] = str(curr)
                edited_df.at[idx, "Next Date"] = str(adjust_months(curr, months))
                save_data(edited_df); st.rerun()
            
            if changes.get("Undo") is True:
                curr_l = pd.to_datetime(edited_df.at[idx, "Last Date Done"]).date()
                edited_df.at[idx, "Next Date"] = str(curr_l)
                edited_df.at[idx, "Last Date Done"] = str(adjust_months(curr_l, -months))
                save_data(edited_df); st.rerun()

# --- דף 2: ניהול נתונים (Admin) ---
elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ ניהול נתונים")
    admin_df = load_data()
    
    if not admin_df.empty:
        st.download_button("📥 הורד גיבוי JSON", admin_df.to_json(orient="records"), "pm_backup.json")

    st.subheader("עריכת טבלה")
    # עורך נתונים חופשי לגמרי - ללא עמודות כפויות
    edited_admin = st.data_editor(admin_df, use_container_width=True, num_rows="dynamic", key="admin_editor")
    
    if st.button("💾 שמור בסיס נתונים"):
        if save_data(edited_admin):
            st.success("בסיס הנתונים נשמר בהצלחה!")
            st.rerun()
