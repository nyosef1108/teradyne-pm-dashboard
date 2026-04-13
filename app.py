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

# --- 2. ניהול נתונים בטוח ---
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
    return pd.DataFrame()

def save_data(df):
    try:
        # ניקוי עמודות ממשק
        cols_to_drop = ["Update Status", "Undo"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        data = save_df.to_dict(orient="records")
        
        temp_file = "temp_data.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        shutil.copy2(temp_file, JSON_FILE)
        shutil.move(temp_file, BACKUP_FILE)
        return True
    except Exception as e:
        st.error(f"שגיאת שמירה קריטית: {e}")
        return False

# --- 3. לוגיקת תאריכים ---
def adjust_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

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

# --- 6. תפריט ניווט ---
st.sidebar.title(f"שלום, Admin")
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
        st.info("בסיס הנתונים ריק. הוסף רשומות בדף הניהול.")
        st.stop()

    display_df = st.session_state.main_df.copy()
    display_df.insert(0, "Update Status", False)
    display_df.insert(1, "Undo", False)
    styled_df = display_df.style.apply(apply_color, axis=1)

    col_config = {
        "Update Status": st.column_config.CheckboxColumn("Confirm PM"),
        "Undo": st.column_config.CheckboxColumn("Undo"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    }

    edited_df = st.data_editor(styled_df, column_config=col_config, use_container_width=True, hide_index=True, num_rows="dynamic", key="pm_editor")

    if st.button("💾 שמור שינויים ידניים"):
        save_data(edited_df)
        st.session_state.main_df = load_data()
        st.rerun()

    # לוגיקת כפתורים מהירה
    if st.session_state.pm_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            row_idx = int(row_idx_str)
            freq_val = edited_df.at[row_idx, "Frequency"]
            months = extract_months_count(freq_val)
            
            if months is None:
                st.error(f"לא ניתן לעדכן: שדה Frequency בשורה {row_idx+1} חייב להכיל מספר חודשים.")
                continue

            if changes.get("Update Status") is True:
                curr = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                edited_df.at[row_idx, "Last Date Done"] = str(curr)
                edited_df.at[row_idx, "Next Date"] = str(adjust_months(curr, months))
                save_data(edited_df); st.session_state.main_df = load_data(); st.rerun()
                
            if changes.get("Undo") is True:
                curr_l = pd.to_datetime(edited_df.at[row_idx, "Last Date Done"]).date()
                edited_df.at[row_idx, "Next Date"] = str(curr_l)
                edited_df.at[row_idx, "Last Date Done"] = str(adjust_months(curr_l, -months))
                save_data(edited_df); st.session_state.main_df = load_data(); st.rerun()

# --- דף 2: ניהול נתונים (Admin) ---
elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ הגדרות בסיס נתונים")
    admin_df = load_data()
    
    # הורדת גיבוי
    if not admin_df.empty:
        json_string = admin_df.to_json(orient="records", indent=4, force_ascii=False)
        st.download_button(label="📥 הורד גיבוי JSON למחשב", data=json_string, file_name=f"pm_backup_{datetime.now().strftime('%Y%m%d')}.json")

    st.divider()
    st.subheader("עריכת רשימת הציוד")
    st.caption("להוספת מכשיר: גלול לתחתית הטבלה ולחץ על ה-+. לשמירה: לחץ על הכפתור למטה.")
    
    edited_admin = st.data_editor(admin_df, use_container_width=True, num_rows="dynamic", key="admin_editor")
    
    if st.button("💾 שמור בסיס נתונים מעודכן"):
        # --- ולידציה לפני שמירה ---
        valid = True
        for i, row in edited_admin.iterrows():
            # בדיקת תיאור
            if pd.isna(row.get("Description")) or row.get("Description") == "":
                st.error(f"שגיאה בשורה {i+1}: חסר שם מכשיר (Description).")
                valid = False
            # בדיקת תדירות
            if extract_months_count(row.get("Frequency")) is None:
                st.error(f"שגיאה בשורה {i+1}: עמודת Frequency חייבת להכיל מספר (למשל '6 months').")
                valid = False
            # בדיקת תאריך
            try:
                pd.to_datetime(row.get("Next Date"))
            except:
                st.error(f"שגיאה בשורה {i+1}: פורמט תאריך לא תקין ב-Next Date (השתמש ב-YYYY-MM-DD).")
                valid = False
        
        if valid:
            if save_data(edited_admin):
                st.session_state.main_df = load_data()
                st.success("הנתונים אומתו ונשמרו בהצלחה!")
                st.rerun()
