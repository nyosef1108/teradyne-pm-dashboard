import streamlit as st
import pandas as pd
import json
import requests
import base64
import re
from datetime import datetime, date
from calendar import monthrange

# --- 1. Page Config & Constants ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
DATE_FORMAT = "%d/%m/%Y"

# --- 2. Date Helpers ---
def parse_date(date_str):
    """Safely converts dd/mm/yyyy string to date object"""
    if pd.isna(date_str) or date_str == "" or date_str is None: return None
    try:
        return datetime.strptime(str(date_str).strip(), DATE_FORMAT).date()
    except ValueError:
        try:
            return pd.to_datetime(date_str).date()
        except:
            return None

def format_date(date_obj):
    """Converts date object to dd/mm/yyyy string"""
    if date_obj is None or pd.isna(date_obj): return ""
    if isinstance(date_obj, str): return date_obj
    return date_obj.strftime(DATE_FORMAT)

def calculate_next_date(current_date, months_to_add):
    """
    Calculates the next date by adding months. 
    Keeps the same day of the month unless it doesn't exist.
    """
    if not current_date: return None
    
    total_months = current_date.month + months_to_add
    year_increment = (total_months - 1) // 12
    target_month = (total_months - 1) % 12 + 1
    target_year = current_date.year + year_increment
    
    # Handle end-of-month logic (e.g., Jan 31 -> Feb 28)
    _, last_day_of_target_month = monthrange(target_year, target_month)
    target_day = min(current_date.day, last_day_of_target_month)
    
    return date(target_year, target_month, target_day)

# --- 3. GitHub Data Management ---
def load_data():
    if "github_token" not in st.secrets:
        st.error("⚠️ Error: github_token missing in Streamlit Secrets.")
        return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])
    
    try:
        token = st.secrets["github_token"]
        repo = st.secrets["github_repo"]
        path = st.secrets["github_file_path"]
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.get(url, headers=headers)
        
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        elif res.status_code == 404:
            return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])
        else:
            st.error(f"GitHub Error ({res.status_code}): {res.text}")
            return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])

def save_data(df):
    try:
        token = st.secrets["github_token"]
        repo = st.secrets["github_repo"]
        path = st.secrets["github_file_path"]
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}

        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None

        cols_to_drop = ["Update Status", "sort_priority"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        new_content = json.dumps(save_df.to_dict(orient="records"), indent=4, ensure_ascii=False)
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

        payload = {
            "message": f"Update PM Data {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "content": encoded_content,
            "sha": sha
        }
        
        put_res = requests.put(url, headers=headers, json=payload)
        return put_res.status_code in [200, 201]
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

# --- 4. UI Logic & Styling ---
def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

def get_sort_priority(date_str):
    dt = parse_date(date_str)
    if not dt: return 3
    today = datetime.now().date()
    if dt < today: return 0  # Red
    if today <= dt <= (today + timedelta(days=7)): return 1  # Yellow
    return 2  # Green

def apply_color(row):
    val = row.get("Next Date", "")
    colors = [''] * len(row)
    try:
        idx = row.index.get_loc("Next Date")
        date_obj = parse_date(val)
        if not date_obj: return colors
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        if date_obj < today: colors[idx] = 'background-color: #ff4b4b; color: white;'
        elif today <= date_obj <= next_week: colors[idx] = 'background-color: #fffd8d; color: black;'
        else: colors[idx] = 'background-color: #90ee90; color: black;'
    except: pass
    return colors

# --- 5. Security ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 ICPE Lab Login")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["credentials"]["admin_name"] and p == st.secrets["credentials"]["admin_password"]:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Invalid credentials")
    st.stop()

# --- 6. Navigation ---
page = st.sidebar.radio("Navigation:", ["PM Dashboard", "Admin - Data Management"])

if page == "PM Dashboard":
    st.title("🛡️ ICPE Lab PM Dashboard")
    df = load_data()
    
    if df.empty:
        st.info("Database is empty or GitHub file not found.")
        st.stop()

    # Prepare table with sorting
    display_df = df.copy()
    display_df['sort_priority'] = display_df['Next Date'].apply(get_sort_priority)
    display_df = display_df.sort_values(by=['sort_priority', 'Next Date'])
    display_df = display_df.drop(columns=['sort_priority'])
    
    display_df.insert(0, "Update Status", False)
    
    col_config = {
        "Update Status": st.column_config.CheckboxColumn("Done"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    }

    edited_df = st.data_editor(display_df.style.apply(apply_color, axis=1), 
                               column_config=col_config, use_container_width=True, hide_index=True, key="pm_editor")

    if st.button("💾 Save Changes"):
        if save_data(edited_df):
            st.success("Successfully synced with GitHub!")
            st.rerun()

    # Logic for checkbox update
    if st.session_state.pm_editor["edited_rows"]:
        needs_rerun = False
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            idx = int(row_idx_str)
            if changes.get("Update Status") is True:
                months = extract_months_count(edited_df.at[idx, "Frequency"])
                # We use "today" as the new completion date
                today_date = datetime.now().date()
                
                # Logic: Update Last Done to Today, Next Date = Today + Frequency
                edited_df.at[idx, "Last Date Done"] = format_date(today_date)
                
                if months:
                    next_dt = calculate_next_date(today_date, months)
                    edited_df.at[idx, "Next Date"] = format_date(next_dt)
                
                needs_rerun = True
        
        if needs_rerun:
            save_data(edited_df)
            st.rerun()

elif page == "Admin - Data Management":
    st.title("⚙️ Admin Settings")
    admin_df = load_data()
    
    st.subheader("Database Editor")
    edited_admin = st.data_editor(admin_df, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Push All to GitHub"):
        if save_data(edited_admin):
            st.success("GitHub Database updated successfully!")
            st.rerun()
