import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. PAGE CONFIGURATION ---
# Sets the browser tab title and expands the layout to use the full screen width
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. AUTHENTICATION SETUP ---
# Validates that credentials exist in the app secrets before initializing the authenticator
if "credentials" in st.secrets:
    authenticator = stauth.Authenticate(
        st.secrets["credentials"].to_dict(),
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
        check_hash=False  # Set to False to allow plain-text passwords in Secrets
    )
else:
    st.error("Missing secrets! Please configure Streamlit Secrets.")
    st.stop()

# Render the login widget in the sidebar or main page
authenticator.login()
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

# --- 3. DATA CONNECTION SETUP ---
# Link to the specific Google Sheet used as the database
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """
    Fetches data from Google Sheets, cleans it, and handles merged cells.
    """
    # Read the sheet starting from the 6th row (header=5)
    df = conn.read(spreadsheet=SHEET_URL, header=5)
    
    # Remove columns that are completely empty
    df = df.dropna(how='all', axis=1)
    
    # Strip whitespace from column headers for consistent referencing
    df.columns = [str(c).strip() for c in df.columns]
    
    # Handle merged cells by filling empty values with the value from the row above
    df = df.ffill()
    return df

# --- 4. TABLE STYLING LOGIC ---
def color_next_date(val):
    """
    Returns CSS styling for the 'Next Date' cells based on the due date status.
    Red: Overdue | Yellow: Due within 7 days | Green: Future task
    """
    try:
        date_val = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_val < today:
            return 'background-color: #ff4b4b; color: white;' # Red (Overdue)
        elif today <= date_val <= next_week:
            return 'background-color: #fffd8d; color: black;' # Yellow (Warning)
        else:
            return 'background-color: #90ee90; color: black;' # Green (OK)
    except:
        return '' # Default styling if date conversion fails

# --- 5. AUTOMATED UPDATE LOGIC ---
def extract_months(freq_str):
    """
    Extracts the numerical month value from a frequency string (e.g., '3 month' -> 3).
    """
    try:
        nums = re.findall(r'\d+', str(freq_str))
        return int(nums[0]) if nums else 1
    except:
        return 1

def process_updates(df):
    """
    Identifies overdue tasks, updates 'Last Date Done', and calculates the next 'Next Date'.
    """
    today = pd.Timestamp.now().normalize()
    updated = False
    
    for idx, row in df.iterrows():
        try:
            # Column index 6 is assumed to be 'Next Date'
            next_date = pd.to_datetime(row.iloc[6], errors='coerce')
            
            if pd.notnull(next_date) and next_date <= today:
                # Update: Move old 'Next Date' to 'Last Date Done' (index 5)
                df.iat[idx, 5] = row.iloc[6]
                
                # Calculate the future date based on frequency (index 4)
                months = extract_months(row.iloc[4])
                new_next = next_date + pd.DateOffset(months=months)
                df.iat[idx, 6] = new_next.strftime('%Y-%m-%d')
                updated = True
        except:
            continue
            
    if updated:
        conn.update(spreadsheet=SHEET_URL, data=df)
        st.success("Schedules updated and synced with Google Sheets!")
    else:
        st.info("No pending updates found for today.")
    return df

# --- 6. MAIN USER INTERFACE ---

if auth_status:
    # Authenticated view for admins
    st.sidebar.success(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        # Action button to trigger the automatic date rollover logic
        if st.button("🔄 Sync & Auto-Update Overdue Tasks"):
            df = process_updates(df)
        
        # Apply the color formatting to the 'Next Date' column
        next_date_col_name = df.columns[6]
        styled_df = df.style.applymap(color_next_date, subset=[next_date_col_name])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
    with tab2:
        # Database editor for manual changes, adding or deleting rows
        st.subheader("Database Editor")
        st.info("Edit cells directly. Click the 'Save' button below to sync changes.")
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.button("💾 Save Manual Changes to Google Sheets"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Google Sheets synchronized successfully!")

elif auth_status is False:
    # Error message for failed login attempts
    st.error("Username/password is incorrect")
    st.dataframe(load_data(), use_container_width=True, hide_index=True)

else:
    # Default view for non-logged in users (Read-only)
    st.title("ICPE Lab PM Schedule")
    st.info("Login via the sidebar to update schedules or edit the database.")
    try:
        df = load_data()
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning("Could not connect to Google Sheets. Verify permissions.")
