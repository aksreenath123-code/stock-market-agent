import os
import smtplib
from datetime import datetime
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# Secrets (Corrected to match YAML left-side variables)
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVERS = os.environ.get("GMAIL_RECEIVERS", "").split(',')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TASK_SHEET_ID = os.environ.get("TASK_SHEET_ID")

def get_sheet_data(sheet_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(url)
        df = df.fillna('') 
        return df
    except Exception as e:
        print(f"Error fetching sheet data: {e}")
        return pd.DataFrame()

def analyze_tasks_with_ai(tasks_df):
    client = genai.Client(api_key=GEMINI_API_KEY)
    today = datetime.now()
    
    if not tasks_df.empty:
        tasks_df['ETA_Date'] = pd.to_datetime(tasks_df.get('ETA', ''), errors='coerce')
        tasks_df['Status_Clean'] = tasks_df.get('Status', '').astype(str).str.strip().str.lower()
        
        # Identify delayed tasks (ETA crossed and not closed)
        tasks_df['Is_Delayed'] = (tasks_df['ETA_Date'] < today) & (~tasks_df['Status_Clean'].isin(['closed', 'done']))
        
        delayed_tasks = tasks_df[tasks_df['Is_Delayed']].to_dict(orient='records')
        closed_tasks = tasks_df[tasks_df['Status_Clean'].isin(['closed', 'done'])].to_dict(orient='records')
        open_tasks = tasks_df[(~tasks_df['Is_Delayed']) & (~tasks_df['Status_Clean'].isin(['closed', 'done']))].to_dict(orient='records')
    else:
        delayed_tasks, closed_tasks, open_tasks = [], [], []

    # Highly intelligent prompt tailored for a Medical Clinic Launch with Malayalam output
    prompt = f"""
    You are an elite Strategic Launch Director and AI Project Manager overseeing the setup of a new Medical Clinic. 
    The project encompasses critical sequential stages: Initial Setup, Banking & Finance Setup, Marketing, and Operations/Hiring.
    
    Analyze this week's task data:
    1. Delayed Tasks (Violated ETA): {delayed_tasks}
    2. Active/Open Tasks: {open_tasks}
    3. Closed Tasks: {closed_tasks}
    
    Provide a deeply analytical, strategic HTML summary strictly in **MALAYALAM LANGUAGE** (do NOT use markdown blocks like ```html) containing:
    - Executive Trajectory (പ്രവർത്തന പുരോഗതി): A brief encouraging overview of the current clinic launch progress.
    - Cascading Impact Analysis (കാലതാമസത്തിന്റെ പ്രത്യാഘാതങ്ങൾ): Critically analyze the delayed tasks. Explain exactly how a delay in these specific tasks will create a bottleneck for subsequent clinic stages (e.g., how banking delays block equipment procurement, or how setup delays impact hiring timelines).
    - Strategic Priorities (മുൻഗണന നൽകേണ്ട കാര്യങ്ങൾ): Give the top 2 to 3 absolute focus areas for the upcoming week to mitigate risks and keep the clinic launch on schedule.
    Keep the tone professional, executive, proactive, and highly insightful, ensuring the entire output is in fluent Malayalam.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        ai_summary = response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        ai_summary = "<p>AI അനാലിസിസ് നിലവിൽ ലഭ്യമല്ല. ദയവായി താഴെയുള്ള ടാസ്ക്കുകൾ പരിശോധിക്കുക.</p>"
        
    return ai_summary, tasks_df

def send_weekly_task_report(ai_summary, tasks_df):
    now = datetime.now().strftime("%Y-%m-%d")
    subject = f"🏥 ക്ലിനിക്ക് ലോഞ്ച് സ്ട്രാറ്റജി റിപ്പോർട്ട് - {now}"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
            .tr-red {{ background-color: #ffe6e6; }} /* Light Red for Delayed */
            .tr-green {{ background-color: #e6ffe6; }} /* Light Green for Closed */
            .tr-yellow {{ background-color: #fff9db; }} /* Light Yellow for Open */
            .tr-purple {{ background-color: #f3e6ff; }} /* Light Purple for New */
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 13px; }}
            th {{ background-color: #2c3e50; color: white; text-transform: uppercase; font-size: 12px; }}
            h2, h3 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
            .ai-box {{ background: #f8f9fa; padding: 20px; border-left: 5px solid #2980b9; margin-bottom: 25px; line-height: 1.6; font-size: 14px; }}
            .color-legend {{ font-size: 12px; margin-bottom: 10px; padding: 10px; background: #eee; border-radius: 5px; display: inline-block; }}
        </style>
    </head>
    <body>
        <h2>ക്ലിനിക്ക് ലോഞ്ച് സ്ട്രാറ്റജി & ടാസ്ക് റിപ്പോർട്ട്</h2>
        <div class="ai-box">
            {ai_summary}
        </div>
        
        <h3>📋 ടാസ്ക് വിവരങ്ങൾ (Master Task Overview)</h3>
        <div class="color-legend">
            <b>സൂചന (Legend):</b> 
            <span style="background:#e6ffe6; padding:2px 5px;">🟩 പൂർത്തിയായവ (Closed)</span> | 
            <span style="background:#fff9db; padding:2px 5px;">🟨 പുരോഗമിക്കുന്നവ (Open)</span> | 
            <span style="background:#f3e6ff; padding:2px 5px;">🟪 പുതിയവ (New)</span> | 
            <span style="background:#ffe6e6; padding:2px 5px; font-weight:bold;">🟥 വൈകിയവ (Delayed/ETA Violated)</span>
        </div>
        
        <table>
            <tr>
                <th>ടാസ്ക് (Task Name)</th>
                <th>വിഭാഗം (Category)</th>
                <th>തിയ്യതി (ETA)</th>
                <th>സ്റ്റാറ്റസ് (Status)</th>
                <th>ചുമതല (Owner)</th>
                <th>അഭിപ്രായങ്ങൾ (Comments)</th>
            </tr>
    """
    
    if not tasks_df.empty:
        for _, row in tasks_df.iterrows():
            status = str(row.get('Status', '')).strip().lower()
            is_delayed = row.get('Is_Delayed', False)
            
            # Color coding logic
            if is_delayed:
                row_class = "tr-red"
            elif status in ['closed', 'done']:
                row_class = "tr-green"
            elif status == 'new':
                row_class = "tr-purple"
            else:
                row_class = "tr-yellow"
                
            eta_str = row['ETA_Date'].strftime('%Y-%m-%d') if pd.notnull(row.get('ETA_Date')) else str(row.get('ETA', 'N/A'))
            
            html_content += f"""
                <tr class="{row_class}">
                    <td><b>{row.get('Task list', row.iloc[0] if len(row) > 0 else '')}</b></td>
                    <td>{row.get('Category', '')}</td>
                    <td>{eta_str}</td>
                    <td>{row.get('Status', 'Open')}</td>
                    <td>{row.get('Owner', row.iloc[5] if len(row) > 5 else '')}</td>
                    <td>{row.get('Comments/Gating', row.iloc[6] if len(row) > 6 else '')}</td>
                </tr>
            """
    else:
        html_content += "<tr><td colspan='6'>ഷീറ്റിൽ ടാസ്ക്കുകൾ ലഭ്യമല്ല.</td></tr>"
         
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
    print("Fetching data from Task Sheet...")
    tasks_df = get_sheet_data(TASK_SHEET_ID)
    
    if not tasks_df.empty:
        ai_summary, tasks_df = analyze_tasks_with_ai(tasks_df)
        send_weekly_task_report(ai_summary, tasks_df)
    else:
        print("No task data found or sheet is empty.")
