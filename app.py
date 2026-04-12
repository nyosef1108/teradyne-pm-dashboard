import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
JSON_FILE = "pm_data.json"

# --- 2. DATA PERSISTENCE ---
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    else:
        # יצירת מבנה העמודות המדויק שלך אם הקובץ לא קיים
        columns = [
            "Tester Name", "Model", "Activity", "Location", 
            "Frequency", "Last Date Done", "Next Date", "Comments"
        ]
        # שורת דוגמה ראשונה
        initial_data = [
            ["UF 1", "UltraFlex", "Monthly PM", "Lab A", "1 month", "2024-03-01", "2024-04-01", ""]
        ]
        df = pd.DataFrame(initial_data, columns=columns)
        save_data(df)
        return df

def save_data(df):
    # הסרת עמודת העדכון הזמנית לפני השמירה
    cols_to_save = [c for c in df.columns if c != "Update Status"]
    data_to_save = df[cols_to_save].to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)

# --- 3. DATE LOGIC ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. STYLING ---
def color_next_date(val):
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today: return 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: return 'background-color: #fffd8d; color: black;'
        else: return 'background-color: #90ee90; color: black;'
    except: return ''

# --- 5. MAIN UI ---
st.title("🛡️ ICPE Lab PM Manager (JSON Mode)")
st.info(f"📅 **Today's Date:** {datetime.now().strftime('%d/%m/%Y')} | הנתונים נשמרים בתוך המערכת")

# טעינה ראשונית של הנתונים ל-Session State
if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

# יצירת עמודת כפתור זמנית לתצוגה
display_df = st.session_state.main_df.copy()
display_df["Update Status"] = False

# הגדרת עיצוב לעמודת התאריך הבא (עמודה מספר 6)
styled_df = display_df.style.map(color_next_date, subset=["Next Date"])

# הטבלה המרכזית - עריכה חופשית של כל תא
edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM",
            help="סימון התיבה יעדכן את התאריכים אוטומטית",
            default=False,
        )
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor"
)

# כפתורים ופעולות
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("💾 Save Changes"):
        save_data(edited_df)
        st.session_state.main_df = load_data()
        st.success("Saved!")
        st.rerun()

# בדיקה אם בוצע עדכון דרך הצ'קבוקס
if st.session_state.pm_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            
            try:
                # לוגיקת עדכון תאריכים
                current_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
                months = extract_months_count(edited_df.at[row_idx, "Frequency"])
                
                edited_df.at[row_idx, "Last Date Done"] = str(current_next)
                edited_df.at[row_idx, "Next Date"] = str(add_months(current_next, months))
                
                # שמירה ורענון
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"Updated row {row_idx + 1}!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error calculating dates: {e}")

st.divider()
st.caption("הוראות: ניתן לערוך כל תא בטבלה. לשינוי שמות או ערכים ידניים יש ללחוץ על Save Changes. לעדכון PM שבוצע, פשוט סמן V בתיבה.")
