import json
import requests
import base64
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import date, timedelta, datetime

# --- הגדרות מה-Secrets של GitHub ---
SENDER_EMAIL = os.environ.get('EMAIL_SENDER')
SENDER_PASSWORD = os.environ.get('EMAIL_PASSWORD')
RECEIVER_EMAIL = os.environ.get('EMAIL_RECEIVER')
GH_TOKEN = os.environ.get('GH_TOKEN')
REPO = os.environ.get('GITHUB_REPOSITORY')
FILE_PATH = "pm_data.json"

def get_data_from_gh():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        raw_content = res.json()['content']
        content = base64.b64decode(raw_content).decode('utf-8')
        return json.loads(content), content
    return [], None

def create_html_table(data):
    if not data:
        return "<h3>No data available.</h3>"
    
    # מיון לפי תאריך ה-PM הבא
    data.sort(key=lambda x: datetime.strptime(x['Next Date'], "%d/%m/%Y") if x.get('Next Date') else datetime.max)
    
    # חילוץ כל שמות העמודות (Keys) הקיימים במידע
    headers = list(data[0].keys())
    
    today = date.today()
    next_week = today + timedelta(days=7)

    # יצירת שורת הכותרות
    header_html = "".join([f"<th style='border:1px solid #ddd; padding:8px; background-color:#f2f2f2;'>{h}</th>" for h in headers])
    
    # יצירת שורות הנתונים
    rows_html = ""
    for item in data:
        row_cells = ""
        nxt_date_str = item.get('Next Date', '')
        
        # חישוב צבע שורה לפי דחיפות ה-Next Date
        bg_color = "#ffffff" # לבן ברירת מחדל
        try:
            nxt_dt = datetime.strptime(nxt_date_str, "%d/%m/%Y").date()
            if nxt_dt < today:
                bg_color = "#ffcccc" # אדום בהיר לעבר
            elif today <= nxt_dt <= next_week:
                bg_color = "#fff9c4" # צהוב בהיר לקרוב
        except:
            pass

        for header in headers:
            val = item.get(header, "")
            # הדגשת תאריך ה-Next Date בתוך השורה
            cell_style = "border:1px solid #ddd; padding:8px;"
            if header == 'Next Date' and bg_color != "#ffffff":
                 cell_style += f" font-weight:bold;"
            
            row_cells += f"<td style='{cell_style}'>{val}</td>"
        
        rows_html += f"<tr style='background-color:{bg_color};'>{row_cells}</tr>"
    
    return f"""
    <html>
    <head>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h2>ICPE Lab - Full PM Status Report</h2>
        <p>Generated on: {today.strftime('%d/%m/%Y')}</p>
        <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <p><small>* Red background = Overdue | Yellow background = Due this week</small></p>
    </body>
    </html>
    """

def send_email():
    data, raw_json = get_data_from_gh()
    if not data:
        print("No data found to send.")
        return
    
    html_content = create_html_table(data)
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"📊 Full Lab Report: {date.today().strftime('%d/%m/%Y')}"
    
    msg.attach(MIMEText(html_content, 'html'))
    
    # צירוף קובץ ה-JSON
    attachment = MIMEApplication(raw_json, _subtype="json")
    attachment.add_header('Content-Disposition', 'attachment', filename=FILE_PATH)
    msg.attach(attachment)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Full report email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_email()
