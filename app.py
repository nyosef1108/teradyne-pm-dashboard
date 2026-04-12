import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Dashboard", layout="wide")

# --- 2. DATA CONNECTION ---
# SHEET_URL is the link to your Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """
    Fetches data from Google Sheets.
    ttl=0 ensures we bypass any cache and get the 'Live' version of your manual edits.
    """
    # Read the sheet starting from row 6 (header=5)
    df = conn.read(spreadsheet=SHEET_URL, header=5, ttl=0)
    
    # Clean up empty columns and whitespace
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Handle merged cells (ffill) so the app looks organized even if cells are merged in Excel
    df = df.ffill()
    
    # Ensure 'Next Date' column is treated as a string for the coloring logic
    if len(df.columns) > 6:
        next_date_col = df.columns[6]
        df[next_date_col] = df[next_date_col].astype(str)
        
    return df

# --- 3. STYLING LOGIC ---
def color_next_date(val):
    """
    Traffic light logic:
    Red: Overdue | Yellow: Due within 7 days | Green: Future
    """
    try:
        # Convert string to date object
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # Red
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # Yellow
        else:
            return 'background-color: #90ee90; color: black;'  # Green
    except:
        return '' # No color if date is invalid

# --- 4. MAIN UI ---
st.title("🛡️ ICPE Lab PM Live Dashboard")

# Display a live clock to show when the data was last refreshed
st.caption(f"Last updated from Google Sheets: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

try:
    # Load the fresh data
    df = load_data()
    
    # Apply the styling to the 'Next Date' column (index 6)
    target_col = df.columns[6]
    styled_df = df.style.map(color_next_date, subset=[target_col])
    
    # Display the table - Read Only mode
    st.dataframe(
        styled_df, 
        use_container_width=True, 
        hide_index=True
    )
    
    st.success("✅ Dashboard is live and syncing. Any manual edits in the Google Sheet will appear here on refresh.")

except Exception as e:
    st.error(f"Could not connect to Google Sheets: {e}")
    st.info("Please verify the spreadsheet URL and sharing permissions.")

# --- 5. AUTOMATIC REFRESH (Optional Tip) ---
# If you want the app to refresh itself every X minutes without clicking F5, 
# you can add: st_autorefresh(interval=60000) from the streamlit_autorefresh package.
