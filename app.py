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
                        df = pd.DataFrame(data)
                        # וידוא עמודות נכונות
                        cols = ["Model", "Activity", "Group", "Frequency", "Last Date Done", "Next Date"]
                        for c in cols:
                            if c not in df.columns: df[c] = ""
                        return df[cols]
            except:
                continue
    return pd.DataFrame(columns=["Model", "Activity", "Group", "Frequency", "Last Date Done", "Next Date"])

def save_data(df):
    try:
        cols_to_drop = ["Update Status", "Undo"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        data = save_df.to_dict(orient="records")
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        shutil.copy2(JSON_FILE, BACKUP_FILE)
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
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

# --- 4. פונקציית צביעה משופרת (מבוססת שם עמודה) ---
def apply_color(row):
    # יצירת רשימת עיצוב ריקה באורך השורה
    formats = [''] * len(row)
    try:
        # איתור המיקום של עמודת Next Date
        target_col = "Next Date"
        if target_col in row.index:
            idx = row.index.get_loc(target_col)
            val = row[target_col]
            
            # המרה לתאריך ובדיקת סטטוס
            date_obj = pd.to_datetime(val).date()
            today = datetime.now().date()
            warning_zone = today + timedelta(days=7)
            
            if date_obj < today:
                formats[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;' # אדום - עבר זמן
            elif today <= date_obj <= warning_zone:
                formats[idx] = 'background-color: #fffd8d; color: black;' # צהוב - שבוע קרוב
            else:
                formats[idx] = 'background-color: #90ee90; color: black;' # ירוק - תקין
    except:
        pass # אם התאריך ריק או לא תקין, לא נצבע
    return formats

# --- 5. אבטחה ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 ICPE Lab Login")
    with st.form("login"):
        u = st.text_input("User")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("התחבר"):
            try:
                creds = st.secrets["credentials"]
                if u == creds["admin_name"] and p == creds["admin_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("פרטים שגויים")
            except: st.error("שגיאה ב-Secrets")
    st.stop()

# --- 6. ממשק ---
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "ניהול נתונים (Admin)"])

if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Dashboard")
    df = load_data()
    
    if df.empty:
        st.info("אין נתונים. טען קובץ בדף ה-Admin.")
        st.stop()

    # יצירת תצוגה עם עמודות עזר
    display_df = df.copy()
    display_df.insert(0, "Update Status", False)
    
    # הפעלת העיצוב (הצבעים)
    styled_df = display_df.style.apply(apply_color, axis=1)

    edited_df = st.data_editor(
        styled_df,
        column_config={"Update Status": st.column_config.CheckboxColumn("V")},
        use_container_width=True,
        hide_index=True,
        key="pm_editor"
    )

    if st.button("💾 שמור שינויים"):
        save_data(edited_df)
        st.rerun()

    # לוגיקת עדכון מהיר
    if st.session_state.pm_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            idx = int(row_idx_str)
            if changes.get("Update Status") is True:
                months = extract_months_count(edited_df.at[idx, "Frequency"])
                if months:
                    curr_next = pd.to_datetime(edited_df.at[idx, "Next Date"]).date()
                    edited_df.at[idx, "Last Date Done"] = str(curr_next)
                    edited_df.at[idx, "Next Date"] = str(adjust_months(curr_next, months))
                    save_data(edited_df)
                    st.rerun()

elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ ניהול בסיס נתונים")
    
    # הורדת גיבוי
    current_df = load_data()
    json_str = current_df.to_json(orient="records", indent=4, force_ascii=False)
    st.download_button("📥 הורד קובץ JSON למחשב", data=json_str, file_name="pm_backup.json")

    st.divider()

    # טעינה ידנית (הכפתור שביקשת)
    uploaded_file = st.file_uploader("טען גרסה ידנית (קובץ JSON):", type="json")
    if uploaded_file:
        if st.button("🔄 עדכן מערכת מהקובץ"):
            new_df = pd.DataFrame(json.load(uploaded_file))
            save_data(new_df)
            st.success("המערכת עודכנה!")
            st.rerun()

    st.divider()

    # עריכה חופשית
    st.subheader("עריכה ידנית / הדבקה")
    edited_admin = st.data_editor(current_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 שמור עריכה"):
        save_data(edited_admin)
        st.success("נשמר!")
        st.rerun()
