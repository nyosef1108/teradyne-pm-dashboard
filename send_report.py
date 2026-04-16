import json
import requests
import base64
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta, datetime

# --- הגדרות מה-Secrets של GitHub ---
SENDER_EMAIL = os.environ.get('EMAIL_SENDER')
SENDER_PASSWORD = os.environ.get('EMAIL_PASSWORD')
RECEIVER_EMAIL = os.environ.get('EMAIL_RECEIVER')
GH_TOKEN = os.environ.get('GH_TOKEN')
# הגרסה האוטומטית - מושכת את שם הריפו מהסביבה של גיטהאב
REPO = os.environ.get('GITHUB_REPOSITORY')
FILE_PATH = "pm_data.json"

def get_data_from_gh():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GH_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()['content']).decode('utf-8')
        return json.loads(content)
    return []

def create_html_table(data):
    # מיון הנתונים לפי תאריך
    data.sort(key=lambda x: datetime.strptime(x['Next Date'], "%d/%m/%Y") if x.get('Next Date') else datetime.max)
    
    rows = ""
    today = date.today()
    next_week = today + timedelta(days=7)

    for item in data:
        nxt_date_str = item.get('Next Date', '')
        color = "#90ee90"  # ירוק ברירת מחדל
        
        try:
            nxt_dt = datetime.strptime(nxt_date_str, "%d/%m/%Y").date()
            if nxt_dt < today: color = "#ff4b4b"      # אדום (עבר הזמן)
            elif today <= nxt_dt <= next_week: color = "#fffd8d" # צהוב (קרוב)
        except: pass

        rows += f"""
        <tr>
            <td style="border:1px solid #ddd; padding:8px;">{item.get('Tester Name','')}</td>
            <td style="border:1px solid #ddd; padding:8px;">{item.get('Model','')}</td>
            <td style="border:1px solid #ddd; padding:8px;">{item.get('Activity','')}</td>
            <td style="border:1px solid #ddd; padding:8px; background-color:{color};">{nxt_date_str}</td>
        </tr>
        """
    
    return f"""
    <html>
    <body>
        <h2>ICPE Lab - Weekly PM Report</h2>
        <p>Status as of: {today.strftime('%d/%m/%Y')}</p>
        <table style="border-collapse: collapse; width: 100%; font-family: Arial;">
            <tr style="background-color: #f2f2f2;">
                <th style="border:1px solid #ddd; padding:8px;">Tester</th>
                <th style="border:1px solid #ddd; padding:8px;">Model</th>
                <th style="border:1px solid #ddd; padding:8px;">Activity</th>
                <th style="border:1px solid #ddd; padding:8px;">Next Date</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """

def send_email():
    data = get_data_from_gh()
    if not data: return
    
    html_content = create_html_table(data)
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🛡️ ICPE Lab Weekly Report - {date.today().strftime('%d/%m/%Y')}"
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    send_email()
