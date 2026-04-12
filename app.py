import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from calendar import monthrange
import re

# --- 1. PAGE CONFIG & FILE SETUP ---
st.set_page_config(page_title="PM Internal Manager", layout="wide")
DATA_FILE = "pm_data.csv"

# פונקציה ליצירת נתונים ראשוניים אם הקובץ לא קיים
def create_initial_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "Tester": ["UF 1", "UF 2", "J750-1", "J750-2"],
            "Model": ["UltraFlex", "UltraFlex", "J750", "J750"],
            "Activity": ["Monthly PM", "Quarterly PM", "Annual PM", "Monthly PM"],
            "Location": ["Lab A", "Lab A", "Lab B", "Lab B"],
            "Frequency": ["1 month", "3 months", "12 months", "1 month"],
            "Last Done": [str(datetime.now().date())] * 4,
            "Next Date": [str((datetime.now() + timedelta(days=30)).date())] * 4
        }
        pd.DataFrame(data).to_csv(DATA_FILE, index=False)

create_initial_data()

# --- 2. LOAD & SAVE LOGIC ---
def load_data():
    df = pd.read_csv(DATA_FILE)
    # וידוא שתאריכים הם מחרוזות לצורך עריכה נוחה
    df['Next Date'] = df['Next Date'].astype(str)
    df['Last Done'] = df['Last Done'].astype(str)
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 3. DATE CALCULATION LOGIC ---
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
st.title("🚀 Internal PM Management System")
st.write(f"📅 **Today:** {datetime.now().strftime('%d/%m/%Y')}")

# טעינת הנתונים
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# עיצוב הטבלה
styled_df = st.session_state.df.style.map(color_next_date, subset=['Next Date'])

st.subheader("Database Editor")
st.info("ניתן לערוך כל תא בטבלה באופן חופשי. לחיצה על הכפתור למטה תבצע עדכון תאריכים אוטומטי לשורות שנבחרו.")

# עורך הנתונים - מאפשר לערוך הכל!
edited_df = st.data_editor(
    styled_df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic", # מאפשר להוסיף ולמחוק שורות!
    key="data_editor"
)

# כפתור שמירה כללי (לשינויים ידניים בתאים)
if st.button("💾 Save All Changes"):
    save_data(edited_df)
    st.session_state.df = edited_df
    st.success("All changes saved locally!")
    st.rerun()

st.divider()
st.subheader("Quick Actions")

# עדכון תאריך PM בלחיצת כפתור לשורה ספציפית
col1, col2 = st.columns(2)
with col1:
    selected_row = st.selectbox("Select Item to confirm PM Done:", edited_df['Tester'] + " - " + edited_df['Activity'])
    if st.button("✅ Confirm PM & Calculate Next"):
        idx = edited_df[edited_df['Tester'] + " - " + edited_df['Activity'] == selected_row].index[0]
        
        # חישוב
        current_next = pd.to_datetime(edited_df.at[idx, 'Next Date']).date()
        months = extract_months_count(edited_df.at[idx, 'Frequency'])
        
        edited_df.at[idx, 'Last Done'] = str(current_next)
        edited_df.at[idx, 'Next Date'] = str(add_months(current_next, months))
        
        save_data(edited_df)
        st.session_state.df = edited_df
        st.success(f"Updated {selected_row}!")
        st.rerun()
