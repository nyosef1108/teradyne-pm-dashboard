import streamlit as st
import pandas as pd
import json
import requests
import base64
import re
from datetime import datetime, timedelta
from calendar import monthrange

# --- 1. הגדרות דף ופורמט ---
st.set_page_config(page_title="ICPE Lab PM Manager", layout="wide")
DATE_FORMAT = "%d/%m/%Y"

# --- 2. עזרי תאריכים לפורמט ישראלי ---
def parse_date(date_str):
    """הופך טקסט בפורמט dd/mm/yyyy לאובייקט תאריך בצורה בטוחה"""
    if pd.isna(date_str) or date_str == "": return None
    try:
        return datetime.strptime(str(date_str).strip(), DATE_FORMAT).date()
    except ValueError:
        # תמיכה בפורמט הישן למקרה של מעבר הדרגתי
        try:
            return pd.to_datetime(date_str).date()
        except:
            return None

def format_date(date_obj):
    """הופך אובייקט תאריך לטקסט בפורמט dd/mm/yyyy"""
    if date_obj is None or pd.isna(date_obj): return ""
    return date_obj.strftime(DATE_FORMAT)

# --- 3. ניהול נתונים מול GITHUB (שמירה תמידית) ---
def load_data():
    try:
        token = st.secrets["github_token"]
        repo = st.secrets["github_repo"]
        path = st.secrets["github_file_path"]
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        else:
            return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])
    except Exception as e:
        st.error(f"שגיאת טעינה מ-GitHub: {e}")
        return pd.DataFrame(columns=["Tester Name", "Model", "Activity", "Activity Group", "Frequency", "Last Date Done", "Next Date"])

def save_data(df):
    try:
        token = st.secrets["github_token"]
        repo = st.secrets["github_repo"]
        path = st.secrets["github_file_path"]
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}

        # קבלת ה-SHA של הקובץ הקיים לעדכון
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None

        # ניקוי עמודות ממשק
        cols_to_drop = ["Update Status", "Undo", "sort_priority"]
        save_df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        new_content = json.dumps(save_df.to_dict(orient="records"), indent=4, ensure_ascii=False)
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

        payload = {
            "message": f"Update PM Data {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "content": encoded_content,
            "sha": sha
        }
        
        put_res = requests.put(url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            return True
        else:
            st.error(f"שגיאת סנכרון לגיט: {put_res.text}")
            return False
    except Exception as e:
        st.error(f"שגיאה בתהליך השמירה: {e}")
        return False

# --- 4. לוגיקה, צביעה ומיון ---
def adjust_months(sourcedate, months):
    if not sourcedate: return None
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, monthrange(year, month)[1])
    return datetime(year, month, day).date()

def extract_months_count(freq_str):
    nums = re.findall(r'\d+', str(freq_str))
    return int(nums[0]) if nums else None

def get_sort_priority(date_str):
    dt = parse_date(date_str)
    if not dt: return 3
    today = datetime.now().date()
    if dt < today: return 0  # אדום (עבר זמנו)
    if today <= dt <= (today + timedelta(days=7)): return 1  # צהוב (קרוב)
    return 2  # ירוק (תקין)

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

# --- 5. אבטחת כניסה ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 כניסה למערכת ICPE Lab")
    with st.form("login"):
        u = st.text_input("שם משתמש")
        p = st.text_input("סיסמה", type="password")
        if st.form_submit_button("התחבר"):
            creds = st.secrets["credentials"]
            if u == creds["admin_name"] and p == creds["admin_password"]:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("פרטים שגויים")
    st.stop()

# --- 6. ממשק משתמש ---
page = st.sidebar.radio("ניווט:", ["לוח בקרה PM", "ניהול נתונים (Admin)"])

if page == "לוח בקרה PM":
    st.title("🛡️ ICPE Lab PM Dashboard")
    df = load_data()
    
    if df.empty:
        st.info("אין נתונים ב-GitHub. טען את הקובץ בדף ה-Admin.")
        st.stop()

    # 1. יצירת עמודת מיון (Sort Priority)
    display_df = df.copy()
    display_df['sort_priority'] = display_df['Next Date'].apply(get_sort_priority)
    
    # 2. מיון כברירת מחדל (אדום -> צהוב -> ירוק)
    display_df = display_df.sort_values(by=['sort_priority', 'Next Date'])
    display_df = display_df.drop(columns=['sort_priority'])
    
    display_df.insert(0, "Update Status", False)
    display_df.insert(1, "Undo", False)
    
    col_config = {
        "Update Status": st.column_config.CheckboxColumn("V"),
        "Undo": st.column_config.CheckboxColumn("Undo"),
        "Next Date": st.column_config.Column(disabled=True),
        "Last Date Done": st.column_config.Column(disabled=True),
    }

    edited_df = st.data_editor(display_df.style.apply(apply_color, axis=1), 
                               column_config=col_config, use_container_width=True, hide_index=True, key="pm_editor")

    if st.button("💾 שמור שינויים"):
        if save_data(edited_df):
            st.success("נשמר וסונכרן ל-GitHub!")
            st.rerun()

    # עדכון אוטומטי בלחיצה על הצ'קבוקס
    if st.session_state.pm_editor["edited_rows"]:
        for row_idx_str, changes in st.session_state.pm_editor["edited_rows"].items():
            idx = int(row_idx_str)
            months = extract_months_count(edited_df.at[idx, "Frequency"])
            if not months: continue
            
            if changes.get("Update Status") is True:
                curr = parse_date(edited_df.at[idx, "Next Date"])
                if curr:
                    edited_df.at[idx, "Last Date Done"] = format_date(curr)
                    edited_df.at[idx, "Next Date"] = format_date(adjust_months(curr, months))
                    save_data(edited_df); st.rerun()
            
            if changes.get("Undo") is True:
                last_done = parse_date(edited_df.at[idx, "Last Date Done"])
                if last_done:
                    edited_df.at[idx, "Next Date"] = format_date(last_done)
                    edited_df.at[idx, "Last Date Done"] = format_date(adjust_months(last_done, -months))
                    save_data(edited_df); st.rerun()

elif page == "ניהול נתונים (Admin)":
    st.title("⚙️ Admin - ניהול נתונים")
    admin_df = load_data()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("גיבוי")
        st.download_button("📥 הורד JSON (פורמט ישראלי)", admin_df.to_json(orient="records", indent=4), "pm_backup.json")
    
    with col2:
        st.subheader("טעינה ידנית")
        up = st.file_uploader("העלה קובץ גיבוי", type="json")
        if up and st.button("⬆️ טען ושמור ל-GitHub"):
            new_df = pd.DataFrame(json.load(up))
            if save_data(new_df):
                st.success("הקובץ נטען וסונכרן בהצלחה!")
                st.rerun()

    st.divider()
    st.subheader("עריכה ישירה של בסיס הנתונים")
    edited_admin = st.data_editor(admin_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 שמור הכל ל-GitHub"):
        if save_data(edited_admin):
            st.success("בסיס הנתונים עודכן ב-GitHub!")
            st.rerun()
