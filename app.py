import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
import pandas as pd
import re

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. AUTHENTICATION SETUP ---
if "credentials" in st.secrets:
    authenticator = stauth.Authenticate(
        st.secrets["credentials"].to_dict(),
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"]
    )
else:
    st.error("Missing secrets! Please configure Streamlit Secrets.")
    st.stop()

# Render Login Widget (Updated for the latest streamlit-authenticator version)
authenticator.login()

# Retrieve authentication status from session state
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

# --- 3. DATA CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit?gid=330466147#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Read the sheet starting from row 5 (header=4)
    df = conn.read(spreadsheet=SHEET_URL, header=4)
    # Clean empty columns
    df = df.dropna(how='all', axis=1)
    # Fill merged cells for the first two columns (Tester and Model)
    if not df.empty:
        df.iloc[:, 0] = df.iloc[:, 0].ffill()
        df.iloc[:, 1] = df.iloc[:, 1].ffill()
    return df

# Helper to extract months from frequency string
def extract_months(freq_str):
    try:
        nums = re.findall(r'\d+', str(freq_str))
        return int(nums[0]) if nums else 1
    except:
        return 1

# --- 4. AUTO-UPDATE LOGIC ---
def process_updates(df):
    today = pd.Timestamp.now().normalize()
    updated = False
    
    for idx, row in df.iterrows():
        try:
            # Column indices based on your structure: 4=Freq, 5=Last, 6=Next
            next_date = pd.to_datetime(row.iloc[6], errors='coerce')
            
            if pd.notnull(next_date) and next_date <= today:
                # Set old 'Next' as the new 'Last Done'
                df.iat[idx, 5] = row.iloc[6]
                
                # Calculate new 'Next Date'
                months = extract_months(row.iloc[4])
                new_next = next_date + pd.DateOffset(months=months)
                df.iat[idx, 6] = new_next.strftime('%m/%d/%Y')
                updated = True
        except:
            continue
            
    if updated:
        conn.update(spreadsheet=SHEET_URL, data=df)
        st.success("Schedules updated successfully!")
    else:
        st.info("No pending updates found for today.")
    return df

# --- 5. MAIN UI ---

# CASE 1: Admin is logged in
if auth_status:
    st.sidebar.success(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        if st.button("🔄 Sync & Auto-Update Dates"):
            df = process_updates(df)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Database Editor")
        st.info("You can edit cells directly, add rows at the bottom, or delete rows.")
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.button("💾 Save Changes to Google Sheets"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Google Sheets updated!")

# CASE 2: Login failed
elif auth_status is False:
    st.error("Username/password is incorrect")
    # Show public view even if login failed
    st.title("ICPE Lab PM Schedule (Public View)")
    df = load_data()
    st.dataframe(df, use_container_width=True, hide_index=True)

# CASE 3: Not logged in (Initial State)
else:
    st.title("ICPE Lab PM Schedule")
    st.info("Login via the sidebar to edit or update dates.")
    df = load_data()
    st.dataframe(df, use_container_width=True, hide_index=True)
