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
    # מנסה לטעון מהקובץ הראשי, אם לא קיים מנסה מהגיבוי
    for file_path in [JSON_FILE, BACKUP_FILE]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return pd.DataFrame(data)
            except:
                continue
    # מבנה ברירת מחדל אם הכל ריק
    return pd.DataFrame(columns=["Model", "Activity", "Group", "Frequency", "Last Date Done", "Next Date"])

def save_data(df):
    try:
        # ניקוי עמודות עזר לפני שמירה
        cols_to_drop = ["Update Status", "Undo"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        data = save_df.to_dict(orient="records")
        
        # שמירה כפולה (מקור + מראה)
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
        elif today <= date_obj <= next_week: colors[idx] = 'background-color: #fffd8d;'
        else: colors[idx] = 'background-color: #90ee90;'
    except: pass
    return colors

# --- 5. מנגנון כניסה ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 כניסה למערכת ICPE Lab")
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
            except: st.error("שגיאה בהגדרות Secrets")
    st.stop()

# --- 6. ממשק משתמש ---
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "ניהול נתונים (Admin)"])

if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Dashboard")
    df = load_data()
    if df.empty:
        st.info("אין נתונים להצגה. עבור לדף הניהול לטעינת קובץ או הוספת שורות.")
        st.stop()

    display_df = df.copy()
    display_df.insert(0, "Update Status", False)
    display_df.insert(1, "Undo", False)
    
    edited_df = st.data_editor(display_df.style.apply(apply_color, axis=1), 
                               column_config={"Update Status": st.column_config.CheckboxColumn("V")},
                               use_container_width=True, hide_index=True, key="pm_editor")

    if st.button("💾 שמור שינויים"):
        if save_data(edited_df):
            st.success("הנתונים נשמרו בהצלחה!")
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

elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ ניהול בסיס נתונים")
    
    # --- אופציה 1: הורדת גיבוי ---
    st.subheader("1. גיבוי נתונים")
    current_df = load_data()
    if not current_df.empty:
        json_str = current_df.to_json(orient="records", indent=4, force_ascii=False)
        st.download_button("📥 הורד קובץ JSON למחשב", data=json_str, file_name=f"pm_backup_{datetime.now().strftime('%Y%m%d')}.json")

    st.divider()

    # --- אופציה 2: טעינת גרסה ידנית (מה שביקשת) ---
    st.subheader("2. טען גרסה ידנית (Upload)")
    uploaded_file = st.file_uploader("בחר קובץ JSON ששמרת בעבר:", type="json")
    if uploaded_file is not None:
        try:
            new_data = json.load(uploaded_file)
            new_df = pd.DataFrame(new_data)
            if st.button("🔄 עדכן את המערכת לפי הקובץ שהועלה"):
                if save_data(new_df):
                    st.success("המערכת עודכנה בהצלחה מהקובץ!")
                    st.rerun()
        except Exception as e:
            st.error(f"שגיאה בקריאת הקובץ: {e}")

    st.divider()

    # --- אופציה 3: עריכה ישירה ---
    st.subheader("3. עריכה ידנית או הדבקה מאקסל")
    edited_admin = st.data_editor(current_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 שמור עריכה ידנית"):
        if save_data(edited_admin):
            st.success("השינויים נשמרו!")
            st.rerun()
