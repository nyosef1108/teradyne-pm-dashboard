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
    # מסננים את עמודת ה-Checkbox לפני השמירה לקובץ
    cols = [c for c in df.columns if c != "Update Status"]
    data = df[cols].to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- לוגיקת תאריכים חכמה ---
def add_months(sourcedate, months):
    """מוסיף חודשים ומטפל נכון בסוף חודש (למשל ינואר 31 -> פברואר 28)"""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    """מחלץ את מספר החודשים מהטקסט (תומך ב-'3 month', '6 months' וכו')"""
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- עיצוב טבלה ---
def color_next_date(val):
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # אדום - פג תוקף
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # צהוב - דחוף (7 ימים)
        else:
            return 'background-color: #90ee90; color: black;'  # ירוק - תקין
    except:
        return ''

# --- ממשק משתמש ---
st.title("🛡️ ICPE Lab PM Management System")
st.write(f"📅 **Today's Date:** {datetime.now().strftime('%d/%m/%Y')}")

# טעינת נתונים
if 'main_df' not in st.session_state:
    st.session_state.main_df = load_data()

if st.session_state.main_df.empty:
    st.error("קובץ pm_data.json חסר או ריק!")
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
            help="סימון התיבה יעדכן את התאריכים אוטומטית לפי התדירות",
            default=False,
        ),
        # עמודת התאריך הבא פתוחה כעת לעריכה ידנית
        "Next Date": st.column_config.TextColumn(
            "Next Date",
            help="ניתן לערוך ידנית בפורמט YYYY-MM-DD או לתת למערכת לחשב",
        ),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor"
)

# כפתור שמירה לשינויים ידניים (שמות, דגמים, או תאריכים ששינית בעצמך)
if st.button("💾 Save All Changes"):
    save_data(edited_df)
    st.session_state.main_df = load_data()
    st.success("הנתונים נשמרו בהצלחה!")
    st.rerun()

# בדיקה אם לחצו על ה-V (עדכון חכם אוטומטי)
if st.session_state.pm_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            try:
                # 1. לוקחים את תאריך היעד שהיה אמור להתבצע (הופך ל-Last Done)
                current_next_val = edited_df.at[row_idx, "Next Date"]
                last_done_date = pd.to_datetime(current_next_val).date()
                
                # 2. מחלצים תדירות (למשל 3 חודשים)
                freq_str = edited_df.at[row_idx, "Frequency"]
                months_to_add = extract_months_count(freq_str)
                
                # 3. מחשבים תאריך יעד חדש
                new_next_date = add_months(last_done_date, months_to_add)
                
                # 4. מעדכנים את הטבלה
                edited_df.at[row_idx, "Last Date Done"] = str(last_done_date)
                edited_df.at[row_idx, "Next Date"] = str(new_next_date)
                
                # 5. שמירה ורענון
                save_data(edited_df)
                st.session_state.main_df = load_data()
                st.toast(f"עודכן בהצלחה: {edited_df.at[row_idx, 'Tester Name']}", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"שגיאה בחישוב התאריך: {e}. וודא שהתאריך בפורמט YYYY-MM-DD")

st.divider()
st.info("💡 **טיפ:** ניתן לשנות כל תאריך בטבלה ידנית ואז ללחוץ על Save. לחיצה על התיבה בטור 'Confirm PM' תבצע חישוב אוטומטי של התאריך הבא בהתבסס על התדירות.")
