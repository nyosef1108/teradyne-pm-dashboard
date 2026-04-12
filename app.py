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
        for col in ["Last Date Done", "Next Date", "Frequency", "Tester Name"]:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame()

def save_data(df):
    # הסרת עמודת הסטטוס הזמנית לפני שמירה ל-JSON
    if "Update Status" in df.columns:
        df = df.drop(columns=["Update Status"])
    data = df.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. לוגיקת תאריכים חכמה ---
def add_months(sourcedate, months):
    """חישוב תאריך עתידי עם הגנה על חריגת ימים בחודש (למשל 31 לינואר -> 28 לפברואר)"""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    """חילוץ מספר החודשים מתוך טקסט חופשי"""
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. פונקציית צביעה יציבה (Traffic Light) ---
def apply_color(row):
    val = row["Next Date"]
    colors = [''] * len(row)
    try:
        next_date_idx = row.index.get_loc("Next Date")
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            colors[next_date_idx] = 'background-color: #ff4b4b; color: white;' # אדום - פג תוקף
        elif today <= date_obj <= next_week:
            colors[next_date_idx] = 'background-color: #fffd8d; color: black;' # צהוב - דחוף
        else:
            colors[next_date_idx] = 'background-color: #90ee90; color: black;' # ירוק - תקין
    except:
        pass
    return colors

# --- 5. ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")
st.info(f"📅 **Today:** {datetime.now().strftime('%d/%m/%Y')} | מודל מאובטח: חישוב תאריכים אוטומטי בלבד")

if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

if st.session_state.main_df.empty:
    st.error("Missing pm_data.json!")
    st.stop()

# הכנת גרסת תצוגה
display_df = st.session_state.main_df.copy()
display_df.insert(0, "Update Status", False)

# החלת עיצוב הצבעים
styled_df = display_df.style.apply(apply_color, axis=1)

# עורך הנתונים
edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn("Confirm PM", help="סמן V לעדכון תאריך אוטומטי", default=False),
        "Next Date": st.column_config.Column("Next Date", disabled=True), # חסום לעריכה ידנית!
        "Last Date Done": st.column_config.Column("Last Date Done", disabled=True), # חסום לעריכה ידנית!
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor_safe"
)

# כפתור שמירה לשינויי טקסט (שמות בודקים, דגמים וכו')
if st.button("💾 Save Manual Changes (Names/Models)"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.success("Changes saved!")
    st.rerun()

# לוגיקת ה-V (העדכון החכם והבטוח)
if st.session_state.pm_editor_safe["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_safe["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            try:
                # לוגיקה: התאריך שהיה ב-Next Date הופך ל-Last Done
                old_next_str = edited_df.at[row_idx, "Next Date"]
                last_done = pd.to_datetime(old_next_str).date()
                
                # חישוב התאריך הבא לפי התדירות (Frequency)
                months = extract_months_count(edited_df.at[row_idx, "Frequency"])
                new_next = add_months(last_done, months)
                
                # עדכון הערכים בטבלה
                edited_df.at[row_idx, "Last Date Done"] = str(last_done)
                edited_df.at[row_idx, "Next Date"] = str(new_next)
                
                # שמירה מיידית ורענון
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Updated {edited_df.at[row_idx, 'Tester Name']} successfully!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}. Check formatting of Frequency/Date columns.")

st.divider()
st.caption("Instructions: To update a PM, check the box. The system will archive the current date and calculate the next one based on the Frequency column.")
