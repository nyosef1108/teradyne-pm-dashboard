import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. DATA CONNECTION ---
# SHEET_URL is the link to your specific Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetches data from Google Sheets with no cache (ttl=0)."""
    # Read raw data
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    # Cleanup empty columns and strip headers
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Create display version with ffill for merged cells
    df_display = df.ffill()
    # Ensure Next Date is a string for styling/display purposes
    if len(df_display.columns) > 6:
        df_display[df_display.columns[6]] = df_display[df_display.columns[6]].astype(str)
        
    # Add the interactive checkbox column
    df_display["Update Status"] = False
    return df_display

# --- 3. SMART DATE LOGIC ---
def add_months(sourcedate, months):
    """Calculates next date, handling end-of-month correctly (e.g., Jan 31 -> Feb 28)."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    """Extracts the number of months from frequency text (e.g., '6 month' -> 6)."""
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. SAFE UPDATE FUNCTION ---
def perform_safe_update(row_idx, df):
    """Updates specific cells in GSheets without destroying formatting."""
    try:
        # Get data for calculation
        current_next_str = df.iat[row_idx, 6]
        freq_str = df.iat[row_idx, 4]
        
        last_done = pd.to_datetime(current_next_str).date()
        months = extract_months_count(freq_str)
        new_next = add_months(last_done, months)
        
        # Calculate Excel/Sheet row: Header(5) + 1 (Header row) + 1 (1-based index) = +7
        sheet_row = row_idx + 7
        
        # Get the underlying gspread client from the connection
        # This bypasses the 'range' keyword error in some library versions
        client = conn._instance.client
        spreadsheet = client.open_by_url(SHEET_URL)
        worksheet = spreadsheet.get_worksheet(0) # First tab
        
        # Update cells: Column F (6) for Last Done, Column G (7) for Next Date
        worksheet.update_cell(sheet_row, 6, str(last_done))
        worksheet.update_cell(sheet_row, 7, str(new_next))
        
        st.toast(f"Row {sheet_row} updated successfully!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Update failed: {e}")
        st.info("Ensure the Google Sheet is shared with 'Editor' permissions to your Service Account email.")

# --- 5. STYLING LOGIC ---
def color_next_date(val):
    """Returns CSS for cell background based on dates."""
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # Overdue
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # Within 7 days
        else:
            return 'background-color: #90ee90; color: black;'  # OK
    except:
        return ''

# --- 6. MAIN USER INTERFACE ---
st.title("🛡️ ICPE Lab PM Live Manager")
st.info(f"📅 **Server Date:** {datetime.now().strftime('%A, %d/%m/%Y')} | Direct Sync Active")

# Load fresh data
df = load_data()

# Style the dataframe
target_col = df.columns[6]
styled_df = df.style.map(color_next_date, subset=[target_col])

# Display interactive data editor
# Users can only check/uncheck the "Update Status" column
pm_editor = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM Done",
            help="Check to update Last Done to current 'Next Date' and calculate future 'Next Date'",
            default=False,
        )
    },
    disabled=[c for c in df.columns if c != "Update Status"],
    use_container_width=True,
    hide_index=True,
    key="pm_table_editor"
)

# Monitor for edits (Checkbox clicks)
if st.session_state.pm_table_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_table_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            perform_safe_update(int(row_idx_str), df)

st.divider()
st.caption("Instructions: Edit the original Google Sheet for structural changes. Use the checkboxes above to record completed maintenance.")
