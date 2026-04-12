import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. DATA CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Fetch data - ttl=0 ensures we see manual edits immediately after refresh
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    
    # We create a display version with filled merged cells
    df_display = df.ffill()
    
    # Add a "virtual" column for the button
    df_display["Update Status"] = False
    return df_display

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
def perform_safe_update(row_idx, df):
    try:
        # Get the 'Next Date' and 'Frequency' for calculation
        current_next_str = df.iat[row_idx, 6]
        freq_str = df.iat[row_idx, 4]
        
        last_done = pd.to_datetime(current_next_str).date()
        months = extract_months_count(freq_str)
        new_next = add_months(last_done, months)
        
        # Calculate the real row in Google Sheets (Header=5 + 2 for 1-based index)
        sheet_row = row_idx + 7
        
        # Update only specific cells to preserve formatting/merges
        conn.update(spreadsheet=SHEET_URL, range=f"F{sheet_row}", data=[[str(last_done)]])
        conn.update(spreadsheet=SHEET_URL, range=f"G{sheet_row}", data=[[str(new_next)]])
        
        st.toast(f"Row {sheet_row} updated successfully!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Update failed: {e}")

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
st.info(f"📅 **Server Date:** {datetime.now().strftime('%d/%m/%Y')} | Updates affect Google Sheets directly.")

# Load the data
df = load_data()

# Identify the 'Next Date' column for styling
target_col = df.columns[6]

# Apply styling
styled_df = df.style.map(color_next_date, subset=[target_col])

# Create the Interactive Data Editor with a button column
event = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM Done",
            help="Check this box to set Last Done to today and calculate the next date",
            default=False,
        )
    },
    disabled=[c for c in df.columns if c != "Update Status"], # Only allow checking the box
    use_container_width=True,
    hide_index=True,
    key="pm_editor"
)

# Logic: If someone checks the checkbox, trigger the update
# We check which row was edited
if st.session_state.pm_editor["edited_rows"]:
    for row_idx, changes in st.session_state.pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            perform_safe_update(int(row_idx), df)

st.divider()
st.caption("Instructions: To update a PM, check the box in the 'Confirm PM Done' column. The Google Sheet will update automatically.")
