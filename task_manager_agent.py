import os
import smtplib
from datetime import datetime
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# Secrets (ഇതിൽ JSON ആവശ്യമില്ല)
#GMAIL_SENDER = os.environ.get("SENDER_EMAIL")
#GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
#GMAIL_RECEIVERS = os.environ.get("GMAIL_RECEIVERS").split(',')
#GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
#TASK_SHEET_ID = os.environ.get("TRIDENT_TASK_SHEET_ID")


# Secrets (Corrected to match YAML left-side variables)
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVERS = os.environ.get("GMAIL_RECEIVERS", "").split(',')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TASK_SHEET_ID = os.environ.get("TASK_SHEET_ID")
def get_sheet_data(sheet_id):
    try:
        # JSON ഇല്ലാതെ പബ്ലിക് ആക്സസ് വഴി നേരിട്ട് ഡാറ്റ എടുക്കുന്നു
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(url)
        df = df.fillna('') # ശൂന്യമായ കോളങ്ങൾ ശരിയാക്കാൻ
        return df
    except Exception as e:
        print(f"Error fetching sheet data: {e}")
        return pd.DataFrame()

def analyze_tasks_with_ai(tasks_df):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    today = datetime.now()
    pending_tasks = pd.DataFrame()
    delayed_tasks = []
    closed_tasks = []
    
    if not tasks_df.empty:
        tasks_df['ETA_Date'] = pd.to_datetime(tasks_df.get('ETA', ''), errors='coerce')
        status_col = tasks_df.get('Status', '').astype(str).str.strip().str.lower()
        
        pending_tasks = tasks_df[~status_col.isin(['closed', 'done'])].copy()
        pending_tasks['Is_Delayed'] = pending_tasks['ETA_Date'] < today
        
        delayed_tasks = pending_tasks[pending_tasks['Is_Delayed']].to_dict(orient='records')
        closed_tasks = tasks_df[status_col.isin(['closed', 'done'])].to_dict(orient='records')

    prompt = f"""
    You are an AI Project Manager. Analyze this weekly task data:
    1. Delayed Tasks (Missed ETA): {delayed_tasks}
    2. Closed Tasks this week: {closed_tasks}
    
    Provide a concise, professional HTML summary containing:
    - An encouraging opening note for the weekend.
    - Actionable feedback or priority suggestions for the delayed tasks.
    - Appreciation for closed tasks.
    Format the output directly as clean HTML (without markdown blocks like ```html).
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        ai_summary = response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        ai_summary = "<p>AI Analysis currently unavailable. Please review the pending tasks below.</p>"
        
    return ai_summary, pending_tasks

def send_weekly_task_report(ai_summary, pending_tasks):
    now = datetime.now().strftime("%Y-%m-%d")
    subject = f"📊 Weekly Task Master Report - {now}"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
            .red-alert {{ color: #c0392b; font-weight: bold; background-color: #fdebd0; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 13px; }}
            th {{ background-color: #2c3e50; color: white; text-transform: uppercase; font-size: 12px; }}
            h2, h3 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
        </style>
    </head>
    <body>
        <h2>Weekly Master Task Report</h2>
        <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin-bottom: 20px;">
            {ai_summary}
        </div>
        
        <h3>📝 Pending & Delayed Tasks Overview</h3>
        <table>
            <tr>
                <th>Task Name</th>
                <th>Category</th>
                <th>ETA</th>
                <th>Status</th>
                <th>Owner</th>
                <th>Comments/Gating</th>
            </tr>
    """
    
    if not pending_tasks.empty:
        for _, row in pending_tasks.iterrows():
            eta_str = row['ETA_Date'].strftime('%Y-%m-%d') if pd.notnull(row.get('ETA_Date')) else str(row.get('ETA', 'N/A'))
            row_class = "red-alert" if row.get('Is_Delayed', False) else ""
            
            html_content += f"""
                <tr class="{row_class}">
                    <td><b>{row.get('Task list', '')}</b></td>
                    <td>{row.get('Category', '')}</td>
                    <td>{eta_str}</td>
                    <td>{row.get('Status', 'Open')}</td>
                    <td>{row.get('Owner', '')}</td>
                    <td>{row.get('Comments/Gating', '')}</td>
                </tr>
            """
    else:
         html_content += "<tr><td colspan='6'>No pending tasks! 🎉</td></tr>"
         
    html_content += "</table></body></html>"
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_SENDER
    msg['To'] = ", ".join(GMAIL_RECEIVERS) 
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, GMAIL_RECEIVERS, msg.as_string())
        server.quit()
        print("Weekly Task Master Email Sent Successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    print("Fetching data from Task Sheet (Public Link)...")
    tasks_df = get_sheet_data(TASK_SHEET_ID)
    
    if not tasks_df.empty:
        ai_summary, pending_tasks = analyze_tasks_with_ai(tasks_df)
        send_weekly_task_report(ai_summary, pending_tasks)
    else:
        print("No task data found or sheet is empty.")
