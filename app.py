import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
import pandas as pd
import re

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Teradyne PM Manager", layout="wide")

# --- 2. AUTHENTICATION SETUP ---
# Load security credentials from Streamlit Secrets
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

# Render Login Widget in the sidebar
name, auth_status, username = authenticator.login('sidebar', 'Login')

# --- 3. DATA CONNECTION ---
# IMPORTANT: Replace the URL below with your actual Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-EqnZWSUuGBT4foAME6E8kiXstULnQxi/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Read the sheet starting from row 5 (header=4) due to spreadsheet titles
    df = conn.read(spreadsheet=SHEET_URL, header=4)
    # Remove empty columns if any exist
    df = df.dropna(how='all', axis=1)
    # Handle merged cells for Tester/Model columns (Forward Fill)
    df.iloc[:, 0] = df.iloc[:, 0].ffill()
    df.iloc[:, 1] = df.iloc[:, 1].ffill()
    return df

# Helper to extract digits from frequency strings (e.g., "6 month" -> 6)
def extract_months(freq_str):
    try:
        nums = re.findall(r'\d+', str(freq_str))
        return int(nums[0]) if nums else 1
    except:
        return 1

# --- 4. AUTO-UPDATE LOGIC (Section 2 of your requirements) ---
def process_updates(df):
    today = pd.Timestamp.now().normalize()
    updated = False
    
    # Logic: If Next Date <= Today, update Last Date and calculate new Next Date
    # Column Indices based on your image: G=4 (Freq), H=5 (Last), I=6 (Next)
    for idx, row in df.iterrows():
        try:
            next_date = pd.to_datetime(row.iloc[6], errors='coerce')
            
            if pd.notnull(next_date) and next_date <= today:
                # Set current 'Next Date' as the new 'Last Date'
                df.iat[idx, 5] = row.iloc[6]
                
                # Calculate new 'Next Date' based on frequency
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
if auth_status:
    # --- ADMIN VIEW ---
    st.sidebar.success(f"Hello {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        if st.button("🔄 Sync & Auto-Update Dates"):
            df = process_updates(df)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Database Editor")
        st.write("Edit cells, add rows (bottom row), or delete rows. Click Save when finished.")
        # Data editor allows adding/deleting rows (Section 3 of your requirements)
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.button("💾 Save Changes to Google Sheets"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Database synchronized!")

else:
    # --- PUBLIC VIEW (Read-Only) ---
    st.title("ICPE Lab PM Schedule")
    df = load_data()
    st.dataframe(df, use_container_width=True, hide_index=True)
