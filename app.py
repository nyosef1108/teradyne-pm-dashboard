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
    st.error("Missing secrets! Please configure Streamlit Secrets.")
    st.stop()

authenticator.login()
auth_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

# --- 3. DATA CONNECTION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/17jIiOurOabjkobbID_ZkNj_u5nMhiCTrNfLIkYaS6Vg/edit#gid=330466147"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Fetches and cleans data from the sheet."""
    df = conn.read(spreadsheet=SHEET_URL, header=5)
    df = df.dropna(how='all', axis=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.ffill()
    return df

# --- 4. STYLING LOGIC (With forced date conversion) ---
def color_next_date(val):
    """Applies Red/Yellow/Green background based on due date."""
    try:
        # Force conversion to date object for comparison
        date_val = pd.to_datetime(val).date()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        
        if date_val < today:
            return 'background-color: #ff4b4b; color: white;'  # Overdue
        elif today <= date_val <= next_week:
            return 'background-color: #fffd8d; color: black;'  # Due soon
        else:
            return 'background-color: #90ee90; color: black;'  # Future
    except:
        return ''

# --- 5. UPDATE LOGIC ---
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
        st.success("Schedules updated successfully!")
    return df

# --- 6. MAIN UI ---
if auth_status:
    st.sidebar.success(f"Welcome {name}")
    authenticator.logout('Logout', 'sidebar')
    
    df = load_data()
    tab1, tab2 = st.tabs(["📊 Schedule View", "🛠️ Admin Control"])
    
    with tab1:
        # Display server date for verification
        st.info(f"📅 **Today is:** {datetime.now().strftime('%A, %d %B %Y')}")
        
        if st.button("🔄 Sync & Auto-Update Overdue Tasks"):
            df = process_updates(df)
        
        # Identify 'Next Date' column (index 6)
        next_date_col = df.columns[6]
        
        # Apply the styling and display
        styled_df = df.style.applymap(color_next_date, subset=[next_date_col])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Database Editor")
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("💾 Save Changes to Google Sheets"):
            conn.update(spreadsheet=SHEET_URL, data=edited_df)
            st.success("Google Sheets synchronized!")

elif auth_status is False:
    st.error("Login failed.")
    st.dataframe(load_data(), use_container_width=True, hide_index=True)

else:
    st.title("ICPE Lab PM Schedule")
    st.info("Please login to update or edit dates.")
    st.dataframe(load_data(), use_container_width=True, hide_index=True)
