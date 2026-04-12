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
        st.secrets["cookie"]["expiry_days"],
        check_hash=False
    )
else:
    st.error("Missing secrets! Please configure Streamlit Secrets.")
    st.stop()

# Render Login Widget
authenticator.login()
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

# --- 3. DATA CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Read data starting from row 6
    df = conn.read(spreadsheet=SHEET_URL, header=5)
    
    # Drop completely empty columns
    df = df.dropna(how='all', axis=1)
    
    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    
    # --- FIX: Handle all merged/empty cells (Forward Fill) ---
    # This fills None values with the last valid entry for the specified columns
    columns_to_fill = ['Tester', 'Model', 'Activity Group'] # Add more columns here if needed
    for col in columns_to_fill:
        if col in df.columns:
            df[col] = df[col].ffill()
            
    return df

# Helper to extract numbers from frequency text
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
            # Column 6 is 'Next Date'
            next_date = pd.to_datetime(row.iloc[6], errors='coerce')
            
            if pd.notnull(next_date) and next_date <= today:
                # Set old 'Next' date as the new 'Last Date Done' (Column 5)
                df.iat[idx, 5] = row.iloc[6]
                
                # Calculate new 'Next' date
                months = extract_months(row.iloc[4]) # Column 4 is Frequency
                new_next = next_date + pd.DateOffset(months=months)
                df.iat[idx, 6] = new_next.strftime('%Y-%m-%d')
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

if auth_status:
    st.sidebar.success(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        if st.button("🔄 Sync & Auto-Update"):
            df = process_updates(df)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Database Editor")
        st.info("Edit cells, add rows, or delete rows. Click Save to sync with Google Sheets.")
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.button("💾 Save Changes to Google Sheets"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Google Sheets synchronized!")

elif auth_status is False:
    st.error("Username/password is incorrect")
    st.title("ICPE Lab PM Schedule")
    df = load_data()
    st.dataframe(df, use_container_width=True, hide_index=True)

else:
    st.title("ICPE Lab PM Schedule")
    st.info("Please login via the sidebar to update or edit dates.")
    try:
        df = load_data()
        st.dataframe(df, use_container_width=True, hide_index=True)
    except:
        st.warning("Could not connect to Google Sheets. Verify permissions and URL.")
