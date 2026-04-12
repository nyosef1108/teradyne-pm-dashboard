import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- הגדרות דף ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
JSON_FILE = "pm_data.json"

# --- פונקציות ניהול נתונים ---
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    return pd.DataFrame()

def save_data(df):
    # מסננים את עמודת ה-Checkbox לפני השמירה
    cols = [c for c in df.columns if c != "Update Status"]
    data = df[cols].to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- לוגיקת תאריכים ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- עיצוב טבלה ---
def color_next_date(val):
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # אדום - עבר זמנו
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # צהוב - השבוע
        else:
            return 'background-color: #90ee90; color: black;'  # ירוק - תקין
    except:
        return ''

# --- ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")
st.write(f"📅 **Today:** {datetime.now().strftime('%d/%m/%Y')}")

# טעינת נתונים ל-Session State כדי שיהיה מהיר
if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

if st.session_state.main_df.empty:
    st.error("Missing pm_data.json file!")
    st.stop()

# הכנת הטבלה לתצוגה
display_df = st.session_state.main_df.copy()
display_df["Update Status"] = False

# החלת עיצוב צבעים
styled_df = display_df.style.map(color_next_date, subset=["Next Date"])

# הצגת עורך הנתונים
edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM Done",
            help="Check to update dates automatically",
            default=False,
        ),
        "Next Date": st.column_config.Column(disabled=True), # מונע שינוי ידני של התאריך הבא בטעות
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor"
)

# כפתור שמירה ידנית לשינויי טקסט
if st.button("💾 Save Text/Manual Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.success("Database Updated!")
    st.rerun()

# בדיקה אם לחצו על ה-V (עדכון אוטומטי)
if st.session_state.pm_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            try:
                # לוגיקת גלגול תאריך
                current_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                months = extract_months_count(edited_df.at[row_idx, "Frequency"])
                
                edited_df.at[row_idx, "Last Date Done"] = str(current_next)
                edited_df.at[row_idx, "Next Date"] = str(add_months(current_next, months))
                
                # שמירה ורענון מיידי
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Updated {edited_df.at[row_idx, 'Tester Name']}!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating dates: {e}")

st.divider()
st.caption("Instructions: To update a PM, check the box. To change names/models, edit the cell and click 'Save Changes'.")
