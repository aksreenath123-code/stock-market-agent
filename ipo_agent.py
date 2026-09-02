import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
from datetime import datetime

# ==================== 1. ലൈബ്രറി ഇൻസ്റ്റാളേഷൻ ====================
REQUIRED_PACKAGES = ["requests", "google-genai", "beautifulsoup4"]

def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            pkg_name = "google.genai" if package == "google-genai" else ("bs4" if package == "beautifulsoup4" else package)
            __import__(pkg_name)
        except ImportError:
            print(f"📦 ഇൻസ്റ്റാൾ ചെയ്യുന്നു: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_missing_packages()

import requests
from bs4 import BeautifulSoup
from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. MULTI-SOURCE FETCHING ====================
def clean_url(url_str):
    cleaned = re.sub(r'^\[.*?\]\((.*?)\)$', r'\1', str(url_str).strip())
    cleaned = cleaned.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    cleaned = cleaned.replace("'", "").replace('"', '').strip()
    return cleaned

def fetch_with_retry(url, retries=3):
    clean_u = clean_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for attempt in range(retries):
        try:
            res = requests.get(clean_u, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.text
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed for {clean_u}: {e}")
            time.sleep(2)
    return None

def parse_html_table(html_content, source_name, max_tables=2):
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all('table')
    if not tables: return None

    data = f"--- Source: {source_name} ---\n"
    valid_data_found = False

    for table in tables[:max_tables]:
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if headers:
            data += " | ".join(headers) + "\n"
            data += "-" * 60 + "\n"

        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if cols:
                row_data = [col.get_text(strip=True) for col in cols]
                data += " | ".join(row_data) + "\n"
                valid_data_found = True
        data += "\n\n"

    if not valid_data_found or len(data) < 100:
        return None
    return data

def fetch_ipo_watch_data():
    print("🔍 IPO Watch (ipowatch.in) സൈറ്റിൽ നിന്നും ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://ipowatch.in/ipo-gmp-today-live-ipo-grey-market-premium/"
    html_content = fetch_with_retry(url)
    if not html_content: return ""
    return parse_html_table(html_content, "IPO Watch", max_tables=2) or ""

def fetch_investorgain_data():
    print("🔍 InvestorGain (investorgain.com) സൈറ്റിൽ നിന്നും ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    html_content = fetch_with_retry(url)
    if not html_content: return ""
    return parse_html_table(html_content, "InvestorGain", max_tables=1) or ""

def get_comprehensive_ipo_data():
    print("⚙️ ക്രോസ്-വാലിഡേഷനായി രണ്ട് സോഴ്സുകളിൽ നിന്നും ഡാറ്റ എടുക്കുന്നു...")
    watch_data = fetch_ipo_watch_data()
    gain_data = fetch_investorgain_data()
    
    combined_data = watch_data + gain_data
    
    if len(combined_data.strip()) > 150:
        print("✅ രണ്ട് സൈറ്റുകളിൽ നിന്നുമുള്ള ഡാറ്റ വിജയകരമായി ലഭിച്ചു.")
        return combined_data
    return ""

# ==================== 4. AI CROSS-VALIDATION ENGINE ====================
def analyze_ipo_data(raw_data):
    print("🧠 AI ഡാറ്റ ക്രോസ്-വാലിഡേഷൻ നടത്തുന്നു (Checking +/- 10% GMP Difference)...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് ക്വാണ്ടിറ്റേറ്റീവ് IPO അനലിസ്റ്റാണ്. 
    ഇന്നത്തെ തീയതി: {current_date}
    
    താഴെ നൽകിയിരിക്കുന്നത് 'IPO Watch', 'InvestorGain' എന്നീ രണ്ട് വ്യത്യസ്ത വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഐപിഒ ഡാറ്റയാണ്:
    
    🚨 നിങ്ങളുടെ ടാസ്ക് (STRICT CROSS-VALIDATION LOGIC):
    1. രണ്ട് സോഴ്സുകളിലെയും ഒരേ ഐപിഒയുടെ GMP (Grey Market Premium) വാല്യൂകൾ തമ്മിൽ താരതമ്യം ചെയ്യുക. 
    2. **Validation Rule (Tolerance 10%):** 
       - രണ്ട് വെബ്സൈറ്റിലെയും GMP തമ്മിലുള്ള വ്യത്യാസം +/- 10% അല്ലെങ്കിൽ അതിൽ താഴെയാണെങ്കിൽ, അത് കറക്റ്റ് ആണെന്ന് കണക്കാക്കി '✅ Validated' എന്ന് രേഖപ്പെടുത്തുക (IPO Watch-ലെ വാല്യൂ മെയിൻ ആയി കാണിക്കുക).
       - വ്യത്യാസം 10%-ൽ കൂടുതൽ ആണെങ്കിൽ (ഉദാഹരണത്തിന് ഒന്നിൽ ₹50, മറ്റൊന്നിൽ ₹2), അത് '⚠️ Mismatch' എന്ന് രേഖപ്പെടുത്തുക.
    3. **Mismatch Formatting:** Mismatch ആണെങ്കിൽ 'Verified GMP' കോളത്തിൽ രണ്ട് ഡാറ്റയും വ്യക്തമായി എഴുതുക (ഉദാഹരണത്തിന്: "IPO Watch: ₹50 | InvestorGain: ₹2").
    4. ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക.

    📋 OUTPUT FORMAT:
    ഒരു മനോഹരമായ HTML ടേബിൾ മാത്രം നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    | IPO Name & Status | Dates | Validation Status (✅ Validated / ⚠️ Mismatch) | Verified GMP (₹) & Listing Gain (%) | Subscription | AI Verdict & Trend |
    
    കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക. Mismatch ഉള്ള വരികൾക്ക് പ്രത്യേക ശ്രദ്ധ കിട്ടുന്ന രീതിയിൽ ഡിസൈൻ ചെയ്യുക.
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🎯 IPO Analysis Report (Strict Cross-Validated)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    print("📧 വാലിഡേറ്റ് ചെയ്ത റിപ്പോർട്ട് ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    wrapped_html = f"""
    <html>
    <head>
    <style>
      table {{ border-collapse: collapse; width: 100%; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; font-size: 14px; margin-top: 15px; }}
      th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; vertical-align: top; line-height: 1.5; }}
      th {{ background-color: #2c3e50; color: #f1c40f; font-weight: bold; text-transform: uppercase; font-size: 13px; }}
      tr:nth-child(even) {{ background-color: #f8f9fa; color: #333; }}
      tr:nth-child(odd) {{ background-color: #ffffff; color: #333; }}
      /* മിസ്മാച്ച് ഹൈലൈറ്റ് ചെയ്യാൻ */
      .mismatch {{ color: #c0392b; font-weight: bold; background-color: #fde8e8; padding: 4px; border-radius: 4px; }}
      .validated {{ color: #27ae60; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50; margin-bottom: 5px; border-bottom: 2px solid #f1c40f; padding-bottom: 5px; display: inline-block;'>🎯 IPO Cross-Validated Report</h2>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 10px;'>* GMP is strictly cross-verified between IPO Watch and InvestorGain.</p>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 20px;'>* Tolerance: +/- 10% difference is auto-resolved. High variations are flagged as <b>⚠️ Mismatch</b>.</p>
    {html_content}
    </body>
    </html>
    """
    msg.attach(MIMEText(wrapped_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

def send_failure_email(error_message):
    print("🚨 ഫെയിലിയർ അലേർട്ട് മെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "❌ ALERT: IPO Agent Failed!"
    html_content = f"<html><body><h3>⚠️ IPO Agent Failed</h3><pre>{error_message}</pre></body></html>"
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ==================== 6. MAIN EXECUTION ====================
if __name__ == "__main__":
    extracted_data = get_comprehensive_ipo_data()
    
    if extracted_data.strip():
        max_retries = 3
        success = False
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                subject, content = analyze_ipo_data(extracted_data)
                send_email(subject, content)
                print("✅ വാലിഡേറ്റ് ചെയ്ത ഐപിഒ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
                success = True
                break 
            
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Attempt {attempt + 1} പരാജയപ്പെട്ടു: {e}")
                time.sleep(60)
        
        if not success:
            send_failure_email(last_error)
            sys.exit(1)
    else:
        print("ഡാറ്റയൊന്നും ലഭിച്ചില്ല. ഫെയിലിയർ മെയിൽ അയക്കുന്നു...")
        send_failure_email("Cross-validation failed: Missing data from scraping sources.")
        sys.exit(1)
