import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
from datetime import datetime

# ==================== 1. ഓട്ടോമാറ്റിക് പാക്കേജ് ഇൻസ്റ്റാളേഷൻ ====================
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

# ==================== 2. API & Credentials ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# കുക്കിയിലെ അനാവശ്യ സ്പേസുകളും പുതിയ ലൈനുകളും ഒഴിവാക്കുന്നു
raw_cookie = os.getenv("BANANA_COOKIE")
BANANA_COOKIE = str(raw_cookie).strip().replace('\n', '').replace('\r', '') if raw_cookie else None

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. COOKIE-BASED DATA EXTRACTION ====================
def fetch_banana_data():
    print("🌐 ബനാന പാറ്റേൺസിൽ നിന്നും ഡീറ്റെയിൽഡ് ഡാറ്റ ശേഖരിക്കുന്നു...")
    
    url = "https://bananapatterns.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": BANANA_COOKIE
    }
    
    scraped_data = ""
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            print("✅ ലോഗിൻ സക്സസ്ഫുൾ! പേജ് കണ്ടെന്റ് എക്സ്ട്രാക്ട് ചെയ്യുന്നു...")
            soup = BeautifulSoup(res.text, "html.parser")
            
            scraped_data += soup.get_text(separator=' \n ', strip=True)
            
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and any(k in script.string for k in ['Forming', 'Climbing', 'Fresh breakouts', 'breakout', 'support', 'resistance', 'pattern']):
                    scraped_data += "\n--- Technical Script & Chart Data ---\n" + script.string[:8000]
                    
            scraped_data = scraped_data[:35000]
        else:
            print(f"❌ ആക്സസ് ഫെയിൽഡ് (Status: {res.status_code}). കുക്കി പരിശോധിക്കുക.")
    except Exception as e:
        print(f"❌ സ്ക്രാപ്പിംഗ് എറർ: {e}")
        
    return scraped_data

# ==================== 4. HIGH CONVICTION AI QUANT ENGINE (>90% WIN-RATE) ====================
def analyze_data(raw_data):
    print("🧠 90%+ Win-Rate കൺവിക്ഷൻ അനാലിസിസും മാസ്റ്റർ ലിസ്റ്റും തയ്യാറാക്കുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് ലെവൽ ക്വാണ്ടിറ്റേറ്റീവ് & മാക്രോ-ടെക്നിക്കൽ സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. 
    ഇന്നത്തെ തീയതി: {current_date}.
    
    താഴെ നൽകിയിരിക്കുന്നത് 'Banana Patterns' വെബ്സൈറ്റിൽ നിന്നുള്ള 'Forming', 'Climbing', 'Fresh breakouts' ഡാറ്റയാണ്:
    -----------------------------------------
    {raw_data}
    -----------------------------------------

    🚨 നിങ്ങളുടെ അനാലിസിസ് ടാസ്ക്കുകൾ:
    നിങ്ങളുടെ HTML ഔട്ട്പുട്ടിൽ കൃത്യമായി 2 ഭാഗങ്ങൾ (Sections) ഉണ്ടായിരിക്കണം.

    **ഭാഗം 1: SECTION 1 - TOP 15 ELITE PICKS (>90% CONVICTION)**
    - "<h3>1. The Ultimate 15 Swing Setups</h3>" എന്ന് ഹെഡിങ് നൽകുക.
    - ഗ്ലോബൽ മാർക്കറ്റ് സെന്റിമെന്റ്, 20/50/200 EMAs, RSI, MACD, Volume എന്നിവ വെച്ച് അനലൈസ് ചെയ്ത് കൃത്യം 15 സ്റ്റോക്കുകൾ (Forming-ൽ നിന്ന് 5, Climbing-ൽ നിന്ന് 5, Fresh breakouts-ൽ നിന്ന് 5) തിരഞ്ഞെടുക്കുക.
    - ഇതിനായി താഴെ പറയുന്ന 7 കോളങ്ങളുള്ള ഒരു ടേബിൾ നിർമ്മിക്കുക:
      | Stock Name & Ticker | Category | Global & Sector Sentiment | Deep Technical Confluence | Trigger / Entry Point (₹) | Target & Strict Stop Loss | Conviction Level & Rationale |

    **ഭാഗം 2: SECTION 2 - COMPLETE MASTER LIST (ALL STOCKS)**
    - "<h3>2. Complete Master List of All Stocks</h3>" എന്ന് ഹെഡിങ് നൽകുക.
    - ഡാറ്റയിൽ നിന്നും നിങ്ങൾക്ക് കണ്ടെത്താൻ കഴിഞ്ഞ **എല്ലാ സ്റ്റോക്കുകളുടെയും പേരുകൾ/ടിക്കറുകൾ** കാറ്റഗറി തിരിച്ച് (Forming, Climbing, Fresh Breakouts) ഇവിടെ ലിസ്റ്റ് ചെയ്യുക.
    - ഈ ഭാഗത്ത് യാതൊരുവിധ അനാലിസിസും ആവശ്യമില്ല. വെറുമൊരു ലളിതമായ ടേബിളിലോ അല്ലെങ്കിൽ ബുള്ളറ്റ് പോയിന്റുകളിലോ (ul/li) സ്റ്റോക്കുകളുടെ പേരുകൾ മാത്രം നൽകുക.

    📋 OUTPUT FORMAT:
    മനോഹരമായ, പ്രൊഫഷണൽ HTML കോഡ് മാത്രം മറുപടി നൽകുക. കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം തരുക. 
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🚀 Banana Patterns: Top 15 Elite Picks & Complete Master List", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ & ഫെയിലിയർ അലേർട്ട് ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    wrapped_html = f"""
    <html><head><style>
      table {{ border-collapse: collapse; width: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; margin-bottom: 25px; }}
      th, td {{ border: 1px solid #dfe6e9; text-align: left; padding: 10px; vertical-align: top; line-height: 1.4; }}
      th {{ background-color: #1e272e; color: #f1c40f; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
      tr:nth-child(even) {{ background-color: #f8f9fa; }}
      tr:nth-child(odd) {{ background-color: #ffffff; }}
      .conviction {{ color: #27ae60; font-weight: bold; }}
      .stoploss {{ color: #c0392b; font-weight: bold; }}
      h2 {{ color: #1e272e; border-bottom: 3px solid #f1c40f; padding-bottom: 8px; }}
      h3 {{ color: #d35400; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
    </style></head><body>
    <h2>🍌 Banana Patterns: Elite Daily Report</h2>
    <p style='color: #636e72; font-size: 13px; margin-bottom: 18px;'>* Includes Top 15 High-Conviction setups and a Complete Master List of all scraped stocks.</p>
    {html_content}
    </body></html>
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
    msg["Subject"] = "❌ ALERT: Banana Patterns Ultimate Analysis Failed"
    html_content = f"""
    <html><body style="font-family: Arial, sans-serif;">
    <h3 style="color: #c0392b;">⚠️ Banana Agent Failed (After 3 Retries)</h3>
    <p><b>Error Details:</b></p>
    <pre style="background: #f8d7da; color: #721c24; padding: 12px; border-radius: 4px;">{error_message}</pre>
    <p>കുക്കി എക്സ്പയർ ആയോ അല്ലെങ്കിൽ നെറ്റ്‌വർക്ക് ഡ്രോപ്പ് ഉണ്ടായോ എന്ന് പരിശോധിക്കുക.</p>
    </body></html>
    """
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ==================== 6. MAIN EXECUTION WITH 3-RETRY LOGIC ====================
if __name__ == "__main__":
    if not BANANA_COOKIE:
        print("❌ BANANA_COOKIE കാണുന്നില്ല! GitHub Secrets പരിശോധിക്കുക.")
        send_failure_email("BANANA_COOKIE secret is missing in GitHub repository.")
        sys.exit(1)
        
    extracted_data = fetch_banana_data()
    
    if extracted_data.strip():
        max_retries = 3
        success = False
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                subject, content = analyze_data(extracted_data)
                send_email(subject, content)
                print("✅ Ultimate Top 15 & Master List റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
                success = True
                break 
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Attempt {attempt + 1} പരാജയപ്പെട്ടു: {e}")
                if attempt < max_retries - 1:
                    print("⏳ 1 മിനിറ്റിനുശേഷം റീട്രൈ ചെയ്യുന്നു (Waiting 60 seconds)...")
                    time.sleep(60)
        
        if not success:
            print("❌ 3 തവണ ശ്രമിച്ചിട്ടും പരാജയപ്പെട്ടു.")
            send_failure_email(last_error)
            sys.exit(1)
    else:
        print("❌ സ്ക്രാപ്പിംഗ് വഴി ഡാറ്റ ലഭിച്ചില്ല.")
        send_failure_email("Scraping returned zero data. Please check BANANA_COOKIE.")
        sys.exit(1)
