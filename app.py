import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. DATA CONNECTION ---
# Using ttl=0 ensures we see the latest manual edits from Google Sheets on every refresh
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetches data from Google Sheets and prepares it for display."""
    # Read raw data starting from row 6
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    
    # Cleanup: remove empty columns and strip whitespace from headers
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Fill merged cells (ffill) for the visual display only
    df_display = df.ffill()
    
    # Ensure Next Date is a string so styling works reliably
    if len(df_display.columns) > 6:
        df_display[df_display.columns[6]] = df_display[df_display.columns[6]].astype(str)
        
    # Add the virtual checkbox column for user interaction
    df_display["Update Status"] = False
    return df_display

# --- 3. SMART DATE LOGIC ---
def add_months(sourcedate, months):
    """Calculates future date while handling end-of-month correctly (e.g., Feb 29)."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    """Extracts the digit from strings like '6 months'."""
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else 1

# --- 4. SAFE CELL-LEVEL UPDATE ---
def perform_safe_update(row_idx, df):
    """Updates only two specific cells in the sheet to keep formatting intact."""
    try:
        # Calculate new dates
        current_next_str = df.iat[row_idx, 6]
        freq_str = df.iat[row_idx, 4]
        
        last_done = pd.to_datetime(current_next_str).date()
        months = extract_months_count(freq_str)
        new_next = add_months(last_done, months)
        
        # Calculate Sheet Row: Header(5) + 1 (Titles) + 1 (1-based index) = Row Index + 7
        sheet_row = row_idx + 7
        
        # Get gspread client directly from the connection object
        client = conn.client
        spreadsheet = client.open_by_url(SHEET_URL)
        worksheet = spreadsheet.get_worksheet(0) # Assumes first tab
        
        # Update Column F (6) and Column G (7)
        worksheet.update_cell(sheet_row, 6, str(last_done))
        worksheet.update_cell(sheet_row, 7, str(new_next))
        
        st.toast(f"Row {sheet_row} updated successfully!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Update failed: {e}")
        st.info("Check if your Service Account has 'Editor' access in Google Sheets.")

# --- 5. VISUAL STYLING ---
def color_next_date(val):
    """Standard traffic light logic for dates."""
    try:
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # Overdue
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # Due within a week
        else:
            return 'background-color: #90ee90; color: black;'  # OK
    except:
        return ''

# --- 6. MAIN UI ---
st.title("🛡️ ICPE Lab PM Live Manager")
st.write(f"📅 **System Date:** {datetime.now().strftime('%d/%m/%Y')}")

# Load and style
df = load_data()
target_col = df.columns[6]
styled_df = df.style.map(color_next_date, subset=[target_col])

# Display the interactive table
pm_table = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM Done",
            help="Check this box to archive the current date and set the next one.",
            default=False,
        )
    },
    disabled=[c for c in df.columns if c != "Update Status"],
    use_container_width=True,
    hide_index=True,
    key="main_pm_editor"
)

# Listen for the checkbox click
if st.session_state.main_pm_editor["edited_rows"]:
    for row_idx_str, changes in st.session_state.main_pm_editor["edited_rows"].items():
        if changes.get("Update Status") is True:
            perform_safe_update(int(row_idx_str), df)

st.divider()
st.caption("Note: Formatting and merged cells in Google Sheets are preserved during updates.")
