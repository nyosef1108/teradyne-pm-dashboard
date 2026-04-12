import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
LOCAL_FILE = "pm_database.xlsx"

# --- 2. INITIAL DATA SETUP (מבנה העמודות המדויק שלך) ---
def create_initial_data():
    if not os.path.exists(LOCAL_FILE):
        # יצירת מבנה העמודות בדיוק כמו באקסל המקורי (כולל עמודות ריקות לרווח)
        columns = [
            "Tester Name", "Model", "Activity", "Location", 
            "Frequency", "Last Date Done", "Next Date", "Comments"
        ]
        # נתונים לדוגמה במבנה הנכון
        data = [
            ["UF 1", "UltraFlex", "Monthly PM", "Lab A", "1 month", "2024-03-01", "2024-04-01", ""],
            ["UF 2", "UltraFlex", "Quarterly PM", "Lab A", "3 month", "2024-01-01", "2024-04-01", ""]
        ]
        df = pd.DataFrame(data, columns=columns)
        df.to_excel(LOCAL_FILE, index=False)

create_initial_data()

# --- 3. LOAD & SAVE ---
def load_data():
    df = pd.read_excel(LOCAL_FILE)
    df = df.ffill() # תמיכה בתאים ממוזגים ויזואלית
    df["Update Status"] = False # עמודת הכפתור
    return df

def save_data(df):
    # הסרת עמודת העדכון לפני השמירה לאקסל
    if "Update Status" in df.columns:
        df = df.drop(columns=["Update Status"])
    df.to_excel(LOCAL_FILE, index=False)

# --- 4. DATE LOGIC ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 5. STYLING ---
def color_next_date(val):
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today: return 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: return 'background-color: #fffd8d; color: black;'
        else: return 'background-color: #90ee90; color: black;'
    except: return ''

# --- 6. MAIN UI ---
st.title("🛡️ ICPE Lab PM Manager (Internal)")
st.info(f"📅 **Today:** {datetime.now().strftime('%d/%m/%Y')} | המידע נשמר מקומית במערכת")

# טעינת נתונים
df = load_data()

# עיצוב
target_col = "Next Date"
styled_df = df.style.map(color_next_date, subset=[target_col])

# הצגת הטבלה המלאה בדיוק כמו במקור
st.subheader("PM Schedule Table")
edited_df = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM",
            help="Check to update dates automatically",
            default=False,
        )
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="pm_editor"
)

# כפתור שמירה כללי לשינויי טקסט
if st.button("💾 Save Manual Changes (Text/Names)"):
    save_data(edited_df)
    st.success("Changes Saved!")
    st.rerun()

# לוגיקת עדכון אוטומטי מהצ'קבוקס
if st.session_state.pm_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            row_idx = int(row_idx_str)
            
            # חישוב תאריכים
            current_next = pd.to_datetime(edited_df.at[row_idx, "Next Date"]).date()
            months = extract_months_count(edited_df.at[row_idx, "Frequency"])
            
            edited_df.at[row_idx, "Last Date Done"] = str(current_next)
            edited_df.at[row_idx, "Next Date"] = str(add_months(current_next, months))
            
            save_data(edited_df)
            st.success(f"Updated row {row_idx + 1}!")
            st.rerun()
