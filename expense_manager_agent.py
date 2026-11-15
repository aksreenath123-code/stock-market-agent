import os
import smtplib
from datetime import datetime
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai
import warnings

# Ignore pandas warnings for cleaner logs
warnings.filterwarnings('ignore')

# Secrets
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVERS = os.environ.get("GMAIL_RECEIVERS", "").split(',')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EXPENSE_SHEET_ID = os.environ.get("EXPENSE_SHEET_ID")

def get_sheet_data(sheet_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(url)
        
        # ഹെഡിംഗുകളിലെ സ്പേസുകൾ ഒഴിവാക്കാൻ (Fix for KeyError)
        df.columns = df.columns.str.strip() 
        
        # ശൂന്യമായ (NaN) ഡാറ്റ സുരക്ഷിതമായി ഫിൽ ചെയ്യാൻ
        df = df.astype(object).fillna('') 
        return df
    except Exception as e:
        print(f"Error fetching sheet data: {e}")
        return pd.DataFrame()

def analyze_expenses_with_ai(expense_df):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    if not expense_df.empty:
        # Amount കോളം കൃത്യമായി നമ്പറിലേക്ക് മാറ്റുന്നു
        amount_col = 'Amount' if 'Amount' in expense_df.columns else expense_df.columns[1]
        expense_df['Amount_Num'] = pd.to_numeric(expense_df[amount_col], errors='coerce').fillna(0)
        total_expense = expense_df['Amount_Num'].sum()
        
        # കോളം പേരുകൾ കൃത്യമായി എടുക്കാൻ (KeyError ഒഴിവാക്കാൻ)
        cols_to_extract = [col for col in ['Task', 'Amount', 'Spend By'] if col in expense_df.columns]
        
        top_expenses = expense_df.nlargest(5, 'Amount_Num')[cols_to_extract].to_dict(orient='records')
        all_expenses = expense_df.to_dict(orient='records')
    else:
        total_expense = 0
        top_expenses, all_expenses = [], []

    prompt = f"""
    You are an elite Financial Director/CFO overseeing the capital expenditure for a new Medical Clinic launch. 
    Analyze this week's expense data:
    Total Spent So Far: ₹{total_expense}
    Top Expenses: {top_expenses}
    All Expenses: {all_expenses}
    
    Provide a deeply analytical, strategic financial summary strictly in **MALAYALAM LANGUAGE** (do NOT use markdown blocks like ```html) containing:
    - സാമ്പത്തിക അവലോകനം (Financial Overview): Brief summary of the overall spending health and total capital deployed.
    - പ്രധാന ചിലവുകൾ (Major Expense Analysis): Identify where the bulk of the money is going. Are these expenses justified for the current stage of the clinic?
    - ചിലവ് ചുരുക്കാനുള്ള നിർദ്ദേശങ്ങൾ (Cost Optimization/Strategic Advice): Point out any potential overspending areas, anomalies, and provide 2-3 strategic tips to optimize budget allocation for upcoming stages (Marketing, Hiring, etc.).
    Keep the tone professional, executive, and financially astute.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        ai_summary = response.text.strip()
    except Exception as e:
        print(f"AI Error: {e}")
        ai_summary = "<p>AI അനാലിസിസ് നിലവിൽ ലഭ്യമല്ല. ദയവായി താഴെയുള്ള ചിലവുകൾ പരിശോധിക്കുക.</p>"
        
    return ai_summary, total_expense, expense_df

def send_weekly_expense_report(ai_summary, total_expense, expense_df):
    now = datetime.now().strftime("%Y-%m-%d")
    subject = f"💰 Clinic Expense & Financial Report - {now}"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 13px; }}
            th {{ background-color: #27ae60; color: white; text-transform: uppercase; font-size: 12px; }}
            h2, h3 {{ color: #27ae60; border-bottom: 2px solid #2ecc71; padding-bottom: 5px; }}
            .ai-box {{ background: #f8f9fa; padding: 20px; border-left: 5px solid #27ae60; margin-bottom: 25px; line-height: 1.6; font-size: 14px; }}
            .total-box {{ font-size: 18px; font-weight: bold; background: #e8f8f5; padding: 15px; border-radius: 5px; color: #16a085; display: inline-block; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>ക്ലിനിക്ക് സാമ്പത്തിക അവലോകന റിപ്പോർട്ട്</h2>
        <div class="total-box">
            ആകെ ചിലവായ തുക (Total Spent): ₹{total_expense:,.2f}
        </div>
        
        <div class="ai-box">
            {ai_summary}
        </div>
        
        <h3>📋 ചിലവുകളുടെ പൂർണ്ണവിവരം (Expense List)</h3>
        <table>
            <tr>
                <th>ടാസ്ക് (Task)</th>
                <th>തുക (Amount)</th>
                <th>അഭിപ്രായങ്ങൾ (Comments)</th>
                <th>ചുമതല (Spend By)</th>
                <th>മാസം (Month)</th>
            </tr>
    """
    
    if not expense_df.empty:
        for _, row in expense_df.iterrows():
            amount_str = f"₹{row.iloc[1]}" if len(row) > 1 else "₹0"
            html_content += f"""
                <tr>
                    <td><b>{row.get('Task', row.iloc[0] if len(row) > 0 else '')}</b></td>
                    <td style="color:#c0392b; font-weight:bold;">{amount_str}</td>
                    <td>{row.get('Comments', row.iloc[2] if len(row) > 2 else '')}</td>
                    <td>{row.get('Spend By', row.iloc[3] if len(row) > 3 else '')}</td>
                    <td>{row.get('Month', row.iloc[4] if len(row) > 4 else '')}</td>
                </tr>
            """
    else:
        html_content += "<tr><td colspan='5'>ഷീറ്റിൽ ഡാറ്റ ലഭ്യമല്ല.</td></tr>"
         
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
        print("Weekly Expense Email Sent Successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    print("Fetching data from Expense Sheet...")
    expense_df = get_sheet_data(EXPENSE_SHEET_ID)
    
    if not expense_df.empty:
        ai_summary, total_expense, expense_df = analyze_expenses_with_ai(expense_df)
        send_weekly_expense_report(ai_summary, total_expense, expense_df)
    else:
        print("No expense data found or sheet is empty.")
