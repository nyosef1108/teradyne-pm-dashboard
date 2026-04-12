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
        df = pd.DataFrame(data)
        # וידוא שכל העמודות קיימות
        for col in ["Last Date Done", "Next Date", "Frequency"]:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame()

def save_data(df):
    if "Update Status" in df.columns:
        df = df.drop(columns=["Update Status"])
    data = df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים חכמה ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. פונקציית הצביעה (Traffic Light) ---
def apply_color(row):
    val = row["Next Date"]
    colors = [''] * len(row)
    try:
        # איתור אינדקס העמודה של Next Date
        next_date_idx = row.index.get_loc("Next Date")
        
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            colors[next_date_idx] = 'background-color: #ff4b4b; color: white;' # אדום
        elif today <= date_obj <= next_week:
            colors[next_date_idx] = 'background-color: #fffd8d; color: black;' # צהוב
        else:
            colors[next_date_idx] = 'background-color: #90ee90; color: black;' # ירוק
    except:
        pass
    return colors

# --- 5. ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")

if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

if st.session_state.main_df.empty:
    st.error("Missing pm_data.json!")
    st.stop()

# יצירת גרסת תצוגה עם עמודת ה-Checkbox
display_df = st.session_state.main_df.copy()
display_df.insert(0, "Update Status", False)

# החלת הצבעים על ה-DataFrame
styled_df = display_df.style.apply(apply_color, axis=1)

st.subheader("PM Schedule Data Editor")
st.info("ניתן לערוך ידנית כל תא (כולל Next Date). לסיום עריכה ידנית לחץ על Save. לעדכון אוטומטי סמן V בתיבה.")

# עורך הנתונים
edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn("Confirm PM", default=False),
        "Next Date": st.column_config.TextColumn("Next Date (YYYY-MM-DD)"),
        "Frequency": st.column_config.TextColumn("Frequency"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor_v4"
)

# כפתור שמירה לשינויים ידניים
if st.button("💾 Save All Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.success("Changes saved!")
    st.rerun()

# לוגיקת ה-V (עדכון אוטומטי)
if st.session_state.pm_editor_v4["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_v4["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            try:
                # לוגיקה חכמה: תאריך היעד הישן הופך ל-"בוצע לאחרונה"
                old_next_str = edited_df.at[row_idx, "Next Date"]
                last_done = pd.to_datetime(old_next_str).date()
                
                # חישוב תאריך יעד חדש
                months = extract_months_count(edited_df.at[row_idx, "Frequency"])
                new_next = add_months(last_done, months)
                
                # עדכון הערכים ב-Dataframe
                edited_df.at[row_idx, "Last Date Done"] = str(last_done)
                edited_df.at[row_idx, "Next Date"] = str(new_next)
                
                # שמירה ורענון
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Updated row {row_idx+1} successfully!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}. Check if 'Next Date' format is YYYY-MM-DD")

st.divider()
st.caption("Tip: Use YYYY-MM-DD format for manual date entry.")
