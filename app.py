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
        return df
    return pd.DataFrame()

def save_data(df):
    # הסרת עמודות ממשק לפני שמירה
    cols_to_drop = ["Update Status", "Undo"]
    save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    data = save_df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים חכמה (קדימה ואחורה) ---
def adjust_months(sourcedate, months):
    """
    פונקציה אחת שמוסיפה או מחסירה חודשים.
    עבור Undo נשלח מספר חודשים שלילי.
    """
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

# --- 5. ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")

if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

# הכנת גרסת תצוגה עם כפתורי פעולה
display_df = st.session_state.main_df.copy()
display_df.insert(0, "Update Status", False)
display_df.insert(1, "Undo", False)

styled_df = display_df.style.apply(apply_color, axis=1)

edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn("Confirm PM", help="Move forward by frequency"),
        "Undo": st.column_config.CheckboxColumn("Undo", help="Move backward by frequency"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor_v6"
)

# כפתור שמירה לשינויים ידניים בטקסט
if st.button("💾 Save Manual Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.rerun()

# לוגיקת כפתורים חכמה
if st.session_state.pm_editor_v6["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_v6["edited_rows"].items():
        row_idx = int(row_idx_str)
        months = extract_months_count(edited_df.at[row_idx, "Frequency"])
        
        # --- אפשרות 1: אישור PM (קדימה) ---
        if changes.get("Update Status") is True:
            try:
                current_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                new_next = adjust_months(current_next, months)
                
                edited_df.at[row_idx, "Last Date Done"] = str(current_next)
                edited_df.at[row_idx, "Next Date"] = str(new_next)
                
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Updated {edited_df.at[row_idx, 'Tester Name']} (+{months}m)", icon="✅")
                st.rerun()
            except: st.error("Date format error")

        # --- אפשרות 2: Undo חכם (אחורה) ---
        if changes.get("Undo") is True:
            try:
                # מחשבים אחורה מהתאריך הנוכחי שרשום ב-Last Date Done
                current_last = pd.to_datetime(edited_df.at[row_idx, "Last Date Done"]).date()
                new_last_done = adjust_months(current_last, -months) # חיסור חודשים
                
                # התאריך הבא יהיה מה שהיה ה-Last Done
                edited_df.at[row_idx, "Next Date"] = str(current_last)
                edited_df.at[row_idx, "Last Date Done"] = str(new_last_done)
                
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Undo: Rolled back {edited_df.at[row_idx, 'Tester Name']} (-{months}m)", icon="🔙")
                st.rerun()
            except: st.error("Could not undo - check date format")

st.divider()
st.caption("Instructions: 'Confirm PM' moves dates forward. 'Undo' calculates backward based on the Frequency column.")
