import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. DATA CONNECTION ---
# Using ttl=0 to ensure we always see the most manual edits from the sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    # ffill is only for the visual representation in the app
    df_visual = df.ffill()
    return df, df_visual

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

# --- 4. SAFE UPDATE FUNCTION ---
def update_pm_date(row_index, current_next_date, freq_str):
    """
    Updates only the specific cells in Google Sheets to preserve formatting.
    Note: row_index in pandas + 7 (5 rows header + 2 for 1-based index) = Sheet Row
    """
    try:
        # 1. Calculate new dates
        last_done = pd.to_datetime(current_next_date).date()
        months = extract_months_count(freq_str)
        new_next = add_months(last_done, months)
        
        # 2. Prepare the update
        # We target columns F (Last Done) and G (Next Date)
        # In Google Sheets, header=5 means our first data row is row 7
        sheet_row = row_index + 7 
        
        # Update Last Done (Column F)
        conn.update(spreadsheet=SHEET_URL, range=f"F{sheet_row}", data=[[str(last_done)]])
        # Update Next Date (Column G)
        conn.update(spreadsheet=SHEET_URL, range=f"G{sheet_row}", data=[[str(new_next)]])
        
        st.success(f"Updated row {sheet_row} successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to update: {e}")

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
st.title("🛡️ ICPE Lab PM Live Manager")
st.info(f"📅 **Today's Date:** {datetime.now().strftime('%d/%m/%Y')}")

# Load data
raw_df, visual_df = load_data()

# Create a styled version of the table for display
target_col = visual_df.columns[6]
styled_df = visual_df.style.map(color_next_date, subset=[target_col])

# Display the table
st.dataframe(styled_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Manual Update Actions")

# Create a clean interface with buttons for each row
# We use a loop to create "Update" buttons for tasks that are due
for idx, row in visual_df.iterrows():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    next_date_val = row.iloc[6]
    tester_name = row.iloc[0]
    activity = row.iloc[2]
    
    # Check if the task is overdue or due within 7 days
    try:
        is_due = pd.to_datetime(next_date_val).date() <= (datetime.now().date() + timedelta(days=7))
    except:
        is_due = False

    if is_due:
        with col1:
            st.write(f"**{tester_name}**")
        with col2:
            st.write(f"*{activity}*")
        with col3:
            st.write(f"Next: {next_date_val}")
        with col4:
            if st.button(f"Confirm PM Done", key=f"btn_{idx}"):
                update_pm_date(idx, next_date_val, row.iloc[4])

st.success("Edit the Google Sheet directly for name changes or structural edits.")
