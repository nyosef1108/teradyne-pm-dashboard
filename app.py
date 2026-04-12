import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. AUTHENTICATION SETUP ---
if "credentials" in st.secrets:
    authenticator = stauth.Authenticate(
        st.secrets["credentials"].to_dict(),
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
        check_hash=False
    )
else:
    st.error("Missing secrets!")
    st.stop()

authenticator.login()
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

# --- 3. DATA CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetches data and ensures 'Next Date' is treated as a date string."""
    df = conn.read(spreadsheet=SHEET_URL, header=5)
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.ffill()
    
    # Force the Next Date column to strings to ensure styling works consistently
    if len(df.columns) > 6:
        df[df.columns[6]] = df[df.columns[6]].astype(str)
        
    return df

# --- 4. STYLING LOGIC ---
def color_next_date(val):
    """Calculates color based on date string value."""
    try:
        # Clean the string and convert to date object
        date_obj = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_obj < today:
            return 'background-color: #ff4b4b; color: white;'  # Overdue - Red
        elif today <= date_obj <= next_week:
            return 'background-color: #fffd8d; color: black;'  # Due soon - Yellow
        else:
            return 'background-color: #90ee90; color: black;'  # OK - Green
    except:
        return '' # No color if not a valid date

# --- 5. HELPER FUNCTIONS ---
def extract_months(freq_str):
    try:
        nums = re.findall(r'\d+', str(freq_str))
        return int(nums[0]) if nums else 1
    except:
        return 1

def process_updates(df):
    today = pd.Timestamp.now().normalize()
    updated = False
    for idx, row in df.iterrows():
        try:
            next_date = pd.to_datetime(row.iloc[6], errors='coerce')
            if pd.notnull(next_date) and next_date <= today:
                df.iat[idx, 5] = row.iloc[6]
                months = extract_months(row.iloc[4])
                new_next = next_date + pd.DateOffset(months=months)
                df.iat[idx, 6] = new_next.strftime('%Y-%m-%d')
                updated = True
        except:
            continue
    if updated:
        conn.update(spreadsheet=SHEET_URL, data=df)
        st.success("Database updated!")
    return df

# --- 6. MAIN UI ---
if auth_status:
    st.sidebar.success(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        st.info(f"📅 **Server Date:** {datetime.now().strftime('%d/%m/%Y')}")
        
        if st.button("🔄 Sync & Auto-Update"):
            df = process_updates(df)
            st.rerun() # Refresh page to show new colors
            
        # Get the name of the 'Next Date' column
        target_col = df.columns[6]
        
        # Apply the styling (using map instead of applymap)
        styled_df = df.style.map(color_next_date, subset=[target_col])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Database Editor")
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 Save Changes"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Synced!")
            st.rerun()

elif auth_status is False:
    st.error("Login failed.")
    st.dataframe(load_data(), use_container_width=True, hide_index=True)

else:
    st.title("ICPE Lab PM Schedule")
    st.info("Please login to manage the database.")
    # Show read-only styled table even for non-logged in users
    raw_df = load_data()
    target_col = raw_df.columns[6]
    st.dataframe(raw_df.style.map(color_next_date, subset=[target_col]), use_container_width=True, hide_index=True)
