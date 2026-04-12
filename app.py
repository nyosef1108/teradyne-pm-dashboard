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
    """Fetches fresh data from the sheet."""
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    df_display = df.ffill()
    if len(df_display.columns) > 6:
        df_display[df_display.columns[6]] = df_display[df_display.columns[6]].astype(str)
    df_display["Update Status"] = False
    return df_display

# --- 3. DATE LOGIC ---
def add_months(sourcedate, months):
    """Handles month increments including end-of-month logic."""
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
    """Updates only the necessary cells using the official update method."""
    try:
        # Calculate values
        current_next_str = df.iat[row_idx, 6]
        freq_str = df.iat[row_idx, 4]
        last_done = pd.to_datetime(current_next_str).date()
        months = extract_months_count(freq_str)
        new_next = add_months(last_done, months)
        
        # Calculate Row: Header(5) + 1 (Titles) + 1 (1-based index) = +7
        sheet_row = row_idx + 7
        
        # Update Column F (Last Done)
        conn.update(
            spreadsheet=SHEET_URL,
            range=f"F{sheet_row}",
            data=pd.DataFrame([[str(last_done)]])
        )
        
        # Update Column G (Next Date)
        conn.update(
            spreadsheet=SHEET_URL,
            range=f"G{sheet_row}",
            data=pd.DataFrame([[str(new_next)]])
        )
        
        st.toast(f"Row {sheet_row} updated!", icon="✅")
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
st.write(f"📅 **System Date:** {datetime.now().strftime('%d/%m/%Y')}")

df = load_data()
target_col = df.columns[6]
styled_df = df.style.map(color_next_date, subset=[target_col])

pm_table = st.data_editor(
    styled_df,
    column_config={
        "Update Status": st.column_config.CheckboxColumn(
            "Confirm PM Done",
            help="Check to update dates in Google Sheets",
            default=False,
        )
    },
    disabled=[c for c in df.columns if c != "Update Status"],
    use_container_width=True,
    hide_index=True,
    key="pm_editor_final"
)

if st.session_state.pm_editor_final["edited_rows"]:
    for row_idx_str, changes in st.session_state.pm_editor_final["edited_rows"].items():
        if changes.get("Update Status") is True:
            perform_safe_update(int(row_idx_str), df)

st.divider()
st.caption("Manual edits in Google Sheets are reflected here on refresh.")
