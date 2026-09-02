import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
from datetime import datetime, timedelta

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

# ==================== 3. MULTI-SOURCE SMART SCRAPER & RETRY ====================
def clean_url(url_str):
    cleaned = re.sub(r'^\[.*?\]\((.*?)\)$', r'\1', str(url_str).strip())
    cleaned = cleaned.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    cleaned = cleaned.replace("'", "").replace('"', '').strip()
    return cleaned

def fetch_with_retry(url, retries=3):
    clean_u = clean_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

def fetch_ipo_watch_data():
    print("🔍 സ്റ്റെപ്പ് 1: IPO Watch (ipowatch.in) സൈറ്റിൽ നിന്നും ഡാറ്റ പരിശോധിക്കുന്നു...")
    url = "https://ipowatch.in/ipo-gmp-today-live-ipo-grey-market-premium/"
    html_content = fetch_with_retry(url)
    
    if not html_content: return None
        
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all('table')
        if not tables: return None
            
        data = "--- Source: IPO Watch (ipowatch.in) ---\n"
        for table in tables[:2]:
            for row in table.find_all('tr'):
                cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                if cols: data += " | ".join(cols) + "\n"
                    
        if len(data) < 100: return None
        return data
    except Exception as e:
        print(f"⚠️ IPO Watch parsing error: {e}")
        return None

def fetch_fallback_investorgain_data():
    print("🔄 Fallback: InvestorGain (investorgain.com) സൈറ്റിൽ നിന്നും ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    html_content = fetch_with_retry(url)
    
    if not html_content: return None
        
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find('table')
        if not table: return None
            
        data = "--- Source: InvestorGain (investorgain.com) ---\n"
        for row in table.find_all('tr'):
            cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
            if cols: data += " | ".join(cols) + "\n"
        return data
    except Exception as e:
        print(f"⚠️ InvestorGain parsing error: {e}")
        return None

def fetch_fallback_chittorgarh_data():
    print("🔄 Fallback: Chittorgarh (chittorgarh.com) സൈറ്റിൽ നിന്നും ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://www.chittorgarh.com/"
    html_content = fetch_with_retry(url)
    
    if not html_content: return None
        
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all('table')
        if not tables: return None
            
        data = "--- Source: Chittorgarh (chittorgarh.com) ---\n"
        for table in tables[:3]:
            for row in table.find_all('tr'):
                cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                if cols: data += " | ".join(cols) + "\n"
        return data
    except Exception as e:
        print(f"⚠️ Chittorgarh parsing error: {e}")
        return None

def get_comprehensive_ipo_data():
    data = fetch_ipo_watch_data()
    if data and len(data.strip()) > 150:
        print("✅ IPO Watch-ൽ നിന്നും ഡാറ്റ വിജയകരമായി ലഭിച്ചു.")
        return data
        
    print("⚠️ IPO Watch ഡാറ്റ അപൂർണ്ണമാണ്. അടുത്ത സോഴ്സിലേക്ക് മാറുന്നു...")
    
    data = fetch_fallback_investorgain_data()
    if data and len(data.strip()) > 150:
        print("✅ InvestorGain-ൽ നിന്നും ഡാറ്റ വിജയകരമായി ലഭിച്ചു.")
        return data
        
    print("⚠️ InvestorGain ഡാറ്റയും ലഭ്യമായില്ല. ഫൈനൽ സോഴ്സിലേക്ക് മാറുന്നു...")
    
    data = fetch_fallback_chittorgarh_data()
    if data:
        print("✅ Chittorgarh-ൽ നിന്നും ബാക്കപ്പ് ഡാറ്റ ലഭിച്ചു.")
        return data
        
    return ""

# ==================== 4. AI അനാലിസിസ് ====================
def analyze_ipo_data(raw_data):
    print("🧠 സ്റ്റെപ്പ് 3: AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു (GMP & Source Verification)...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു വിദഗ്ദ്ധനായ ഇന്ത്യൻ സ്റ്റോക്ക് മാർക്കറ്റ് & IPO അനലിസ്റ്റാണ്. 
    താഴെ നൽകിയിരിക്കുന്നത് വിശ്വസനീയം ആയ വെബ്സൈറ്റുകളിൽ നിന്നും ശേഖരിച്ച ഐപിഒ ഡാറ്റയാണ്.
    ഇന്നത്തെ തീയതി: {current_date}
    
    🚨 നിങ്ങളുടെ കർശനമായ ടാസ്ക്കുകൾ:
    1. **ACCURATE GMP & SUBSCRIPTION:** ഡാറ്റയിലുള്ള ഓരോ ഐപിഒയുടെയും യഥാർത്ഥ ഗ്രേ മാർക്കറ്റ് പ്രീമിയം (GMP), ലിസ്റ്റിംഗ് ഗെയിൻ ശതമാനം, QIB, NII, Retail സബ്സ്ക്രിപ്ഷൻ വിവരങ്ങൾ എന്നിവ യാതൊരു തെറ്റും കൂടാതെ കൃത്യമായി വിശകലനം ചെയ്യുക.
    2. **DAILY GMP HISTORY & AI STRATEGY:** തിയ്യതി തിരിച്ചുള്ള GMP ട്രെൻഡ് പരിശോധിച്ച്, കഴിഞ്ഞ ദിവസങ്ങളിലെ ഡെയിലി GMP ഹിസ്റ്ററി 'AI Analysis & Recommendation' കോളത്തിൽ ലിസ്റ്റ് ആയി ചേർക്കുക. ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക.
    3. **DATA SOURCE IDENTIFICATION (NEW):** നൽകിയിട്ടുള്ള ഡാറ്റയുടെ മുകളിൽ ഏത് വെബ്സൈറ്റിൽ നിന്നാണ് ഡാറ്റ എടുത്തത് എന്ന് (ഉദാ: Source: IPO Watch അല്ലെങ്കിൽ InvestorGain) നൽകിയിട്ടുണ്ടാകും. അത് ഓരോ ഐപിഒയുടെയും കൂടെ 'Data Source' എന്ന പുതിയ കോളത്തിൽ കൃത്യമായി രേഖപ്പെടുത്തുക.
    
    📋 OUTPUT FORMAT (CRITICAL):
    ഒരു എക്സെൽ ഷീറ്റ് പോലെയുള്ള മനോഹരമായ **HTML ടേബിൾ** രൂപത്തിൽ മാത്രം ഔട്ട്പുട്ട് നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 7 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    
    | IPO Name & Status | Dates (Start - End) | GMP & Listing Gain (%) | Subscription (QIB/NII/Retail) | GMP Trend | AI Analysis & Daily GMP History | Data Source |
    
    - കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക.
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🎯 IPO Analysis Report (Multi-Source Verified)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ & ഫെയിലിയർ അലേർട്ട് ====================
def send_email(subject, html_content):
    print("📧 സ്റ്റെപ്പ് 4: ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    wrapped_html = f"""
    <html>
    <head>
    <style>
      table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 14px; }}
      th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; vertical-align: top; line-height: 1.5; }}
      th {{ background-color: #2c3e50; color: white; }}
      tr:nth-child(even) {{ background-color: #f2f2f2; color: #333; }}
      tr:nth-child(odd) {{ background-color: #ffffff; color: #333; }}
      ul {{ margin-top: 8px; margin-bottom: 0px; padding-left: 20px; color: #555; font-size: 13px; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50; margin-bottom: 5px;'>🎯 IPO Analysis Report (Source Verified)</h2>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 20px;'>* Includes specific data source for cross-checking GMP accuracy.</p>
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
    msg["Subject"] = "❌ ALERT: IPO Analysis Agent Failed!"
    html_content = f"""
    <html><body style="font-family: Arial, sans-serif;">
    <h3 style="color: #c0392b;">⚠️ IPO Analysis Agent Failed (After 3 Retries)</h3>
    <p><b>Error Details:</b></p>
    <pre style="background: #f8d7da; color: #721c24; padding: 12px; border-radius: 4px;">{error_message}</pre>
    </body></html>
    """
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
                print("✅ ഐപിഒ റിപ്പോർട്ട് വിജയകരമായി തയ്യാറാക്കി അയച്ചു!")
                success = True
                break 
            
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Attempt {attempt + 1} പരാജയപ്പെട്ടു (AI/Email Error): {e}")
                
                if attempt < max_retries - 1:
                    print("⏳ 1 മിനിറ്റിനുശേഷം വീണ്ടും ശ്രമിക്കുന്നു...")
                    time.sleep(60)
        
        if not success:
            send_failure_email(last_error)
            sys.exit(1)
    else:
        print("ഡാറ്റയൊന്നും ലഭിച്ചില്ല. ഫെയിലിയർ മെയിൽ അയക്കുന്നു...")
        send_failure_email("All scraping sources returned zero data.")
        sys.exit(1)
