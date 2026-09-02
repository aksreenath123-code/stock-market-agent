import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
import random
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

# ==================== 3. ADVANCED ANTI-BOT FETCHING & BATCHING ====================
def clean_url(url_str):
    cleaned = re.sub(r'^\[.*?\]\((.*?)\)$', r'\1', str(url_str).strip())
    cleaned = cleaned.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    cleaned = cleaned.replace("'", "").replace('"', '').strip()
    return cleaned

def fetch_with_retry(url, retries=5):
    """5 തവണ റീട്രൈ ചെയ്യുകയും ബോട്ട് ബ്ലോക്കിംഗ് ഒഴിവാക്കാൻ റാൻഡം ഗ്യാപ്പ് നൽകുകയും ചെയ്യുന്നു"""
    clean_u = clean_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    for attempt in range(retries):
        try:
            # മനുഷ്യനെപ്പോലെ തോന്നിക്കാൻ റിക്വസ്റ്റിന് മുൻപ് ഒരു ചെറിയ ഗ്യാപ്പ്
            time.sleep(random.uniform(2, 5)) 
            res = requests.get(clean_u, headers=headers, timeout=25)
            
            if res.status_code == 200:
                return res.text
            else:
                print(f"⚠️ HTTP {res.status_code} received from {clean_u}")
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed for {clean_u}: {e}")
            
        if attempt < retries - 1:
            wait_time = random.uniform(10, 20) # 10 മുതൽ 20 സെക്കൻഡ് വരെ റാൻഡം വെയിറ്റിംഗ്
            print(f"⏳ {wait_time:.1f} സെക്കൻഡ് കാത്തിരിക്കുന്നു (Anti-bot delay)...")
            time.sleep(wait_time)
            
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
    print("⚙️ ക്രോസ്-വാലിഡേഷനായി ഡാറ്റ എടുക്കുന്നു (With Anti-bot delays)...")
    watch_data = fetch_ipo_watch_data()
    
    # രണ്ട് സൈറ്റുകൾക്കിടയിൽ സസ്പീഷ്യസ് ആവാതിരിക്കാൻ ഗ്യാപ്പ്
    time.sleep(random.uniform(5, 10)) 
    gain_data = fetch_investorgain_data()
    
    combined_data = watch_data + gain_data
    
    if len(combined_data.strip()) > 150:
        print("✅ ഡാറ്റ വിജയകരമായി ലഭിച്ചു.")
        return combined_data
    return ""

# ==================== 4. AI CROSS-VALIDATION ENGINE ====================
def analyze_ipo_data(raw_data):
    print("🧠 AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു (Source Tracking & Batching)...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് ക്വാണ്ടിറ്റേറ്റീവ് IPO അനലിസ്റ്റാണ്. 
    ഇന്നത്തെ തീയതി: {current_date}
    
    താഴെ നൽകിയിരിക്കുന്നത് വിവിധ വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഐപിഒ ഡാറ്റയാണ്:
    
    🚨 നിങ്ങളുടെ ടാസ്ക്:
    1. **Batch Limits:** ഡാറ്റയിൽ ഒരുപാട് പഴയ ഐപിഒകൾ ഉണ്ടെങ്കിൽ അവ ഒഴിവാക്കുക. നിലവിൽ ഓപ്പൺ ആയിട്ടുള്ളതും, വരാനിരിക്കുന്നതും, അടുത്തിടെ ക്ലോസ് ആയതുമായ ഏറ്റവും പുതിയ 15-20 ഐപിഒകൾ മാത്രം വിശകലനം ചെയ്യുക.
    2. **Source Tracking & Validation (Tolerance 10%):** 
       - രണ്ട് സോഴ്സുകളിൽ (IPO Watch & InvestorGain) ഡാറ്റ ലഭ്യമാണെങ്കിൽ അവയിലെ GMP താരതമ്യം ചെയ്യുക. 
         - വ്യത്യാസം +/- 10% ആണെങ്കിൽ: '✅ Validated (IPO Watch & InvestorGain)' എന്ന് രേഖപ്പെടുത്തുക.
         - വ്യത്യാസം വലുതാണെങ്കിൽ: '⚠️ Mismatch (Watch: ₹X | Gain: ₹Y)' എന്ന് രേഖപ്പെടുത്തുക.
       - ഒരു സോഴ്സിൽ മാത്രം (Single Source) ഡാറ്റ ലഭ്യമാണെങ്കിൽ: 'ℹ️ Single Source (ഉദാ: IPO Watch)' എന്ന് കൃത്യമായി വെബ്സൈറ്റിന്റെ പേര് സഹിതം രേഖപ്പെടുത്തുക.
    3. ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക.

    📋 OUTPUT FORMAT:
    ഒരു മനോഹരമായ HTML ടേബിൾ മാത്രം നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    | IPO Name & Status | Dates | Validation Status & Source | Verified GMP (₹) & Listing Gain (%) | Subscription | AI Verdict & Trend |
    
    കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക.
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🎯 IPO Analysis Report (Source Tracked & Validated)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    print("📧 റിപ്പോർട്ട് ഇമെയിൽ അയക്കുന്നു...")
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
      .mismatch {{ color: #c0392b; font-weight: bold; background-color: #fde8e8; padding: 4px; border-radius: 4px; }}
      .validated {{ color: #27ae60; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50; margin-bottom: 5px; border-bottom: 2px solid #f1c40f; padding-bottom: 5px; display: inline-block;'>🎯 IPO Analysis Report</h2>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 10px;'>* GMP is dynamically validated across multiple sources with Source Tracking.</p>
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
                print("✅ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
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
        send_failure_email("Scraping failed: Websites might be blocking the request. Anti-bot protection active.")
        sys.exit(1)
