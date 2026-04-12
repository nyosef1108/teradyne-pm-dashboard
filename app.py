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
        # וידוא עמודות נחוצות ועמודות גיבוי ל-Undo
        required_cols = ["Tester Name", "Model", "Activity", "Frequency", "Last Date Done", "Next Date", "Prev Last Done", "Prev Next Date"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame()

def save_data(df):
    # הסרת עמודות כפתורים זמניות לפני שמירה
    cols_to_drop = ["Update Status", "Undo Update"]
    save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    data = save_df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים ---
def add_months(sourcedate, months):
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

# הכנת תצוגה
display_df = st.session_state.main_df.copy()
display_df.insert(0, "Update Status", False)
display_df.insert(1, "Undo Update", False)

# החלת עיצוב
styled_df = display_df.style.apply(apply_color, axis=1)

edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn("Confirm PM", help="Update to next period"),
        "Undo Update": st.column_config.CheckboxColumn("Undo", help="Restore previous dates"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
        # הסתרת עמודות הגיבוי מהמשתמש
        "Prev Last Done": None,
        "Prev Next Date": None,
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor_v5"
)

# כפתור שמירה כללי
if st.button("💾 Save Manual Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.rerun()

# לוגיקת כפתורים (V ו-Undo)
if st.session_state.pm_editor_v5["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_v5["edited_rows"].items():
        row_idx = int(row_idx_str)
        
        # --- פעולת UPDATE ---
        if changes.get("Update Status") is True:
            try:
                # גיבוי המצב הנוכחי לפני שינוי
                edited_df.at[row_idx, "Prev Last Done"] = edited_df.at[row_idx, "Last Date Done"]
                edited_df.at[row_idx, "Prev Next Date"] = edited_df.at[row_idx, "Next Date"]
                
                # חישוב חדש
                old_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                months = extract_months_count(edited_df.at[row_idx, "Frequency"])
                new_next = add_months(old_next, months)
                
                edited_df.at[row_idx, "Last Date Done"] = str(old_next)
                edited_df.at[row_idx, "Next Date"] = str(new_next)
                
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.rerun()
            except: pass

        # --- פעולת UNDO ---
        if changes.get("Undo Update") is True:
            prev_last = edited_df.at[row_idx, "Prev Last Done"]
            prev_next = edited_df.at[row_idx, "Prev Next Date"]
            
            if prev_next: # בודק שיש מה לשחזר
                edited_df.at[row_idx, "Last Date Done"] = prev_last
                edited_df.at[row_idx, "Next Date"] = prev_next
                # מנקה את הגיבוי כדי שלא יהיה ניתן לעשות אנדו כפול בטעות
                edited_df.at[row_idx, "Prev Last Done"] = ""
                edited_df.at[row_idx, "Prev Next Date"] = ""
                
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast("Restored previous dates", icon="🔙")
                st.rerun()
            else:
                st.warning("No previous history found for this row.")
