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

# 🚨 ERROR FIX: കുക്കിയിലെ അനാവശ്യ സ്പേസുകളും പുതിയ ലൈനുകളും ഇവിടെ തനിയെ ഒഴിവാക്കുന്നു
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
    print("🧠 90%+ Win-Rate കൺവിക്ഷൻ & ഗ്ലോബൽ മാക്രോ അനാലിസിസ് റൺ ചെയ്യുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് ലെവൽ ക്വാണ്ടിറ്റേറ്റീവ് & മാക്രോ-ടെക്നിക്കൽ സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. നിങ്ങളുടെ പ്രധാന ലക്ഷ്യം നാളെ അപ്‌ട്രെൻഡിലേക്ക് പോകാൻ 90%-ലധികം വിജയസാധ്യതയുള്ള സ്റ്റോക്കുകൾ മാത്രം കണ്ടെത്തുക എന്നതാണ്.
    ഇന്നത്തെ തീയതി: {current_date}.
    
    താഴെ നൽകിയിരിക്കുന്നത് 'Banana Patterns' വെബ്സൈറ്റിൽ നിന്നുള്ള 'Forming', 'Climbing', 'Fresh breakouts' ഡാറ്റയാണ്:
    -----------------------------------------
    {raw_data}
    -----------------------------------------

    🚨 നിങ്ങളുടെ അനാലിസിസ് മാനദണ്ഡങ്ങൾ (ULTIMATE FILTERING STRICT RULES):
    1. **CROSS-REFERENCE WITH GLOBAL DATA:** ഈ ഡാറ്റയിൽ നിന്നും ലഭിക്കുന്ന സ്റ്റോക്ക് ടിക്കറുകളെ നിലവിലെ ഗ്ലോബൽ മാർക്കറ്റ് എൻവയോൺമെന്റ് (Global News, Sector Sentiment) എന്നിവയുമായി കൂട്ടിവായിക്കുക. മാർക്കറ്റ് പ്രതികൂലമാണെങ്കിൽ ആ സെക്ടറിലെ സ്റ്റോക്കുകൾ ഒഴിവാക്കുക.
    2. **MULTI-TIMEFRAME & ADVANCED TECHNICALS:** സ്ക്രാപ്പ് ചെയ്ത ചാർട്ട് ഡാറ്റയോടൊപ്പം ആ സ്റ്റോക്കുകളുടെ Weekly & Daily ട്രെൻഡുകൾ വിലയിരുത്തുക. 20, 50, 200 EMAs, RSI (55-68 zone), MACD crossovers, Volume surges എന്നിവ പൂർണ്ണമായും അനുകൂലമാണെന്ന് ഉറപ്പുവരുത്തുക.
    3. **EXACTLY 15 STOCKS:** മേൽപ്പറഞ്ഞ എല്ലാ കടമ്പകളും കടന്ന, ട്രേഡ് ചെയ്യാൻ ഏറ്റവും അനുയോജ്യമായ:
       - 'Forming' കാറ്റഗറിയിൽ നിന്നും 5 സ്റ്റോക്കുകൾ.
       - 'Climbing' കാറ്റഗറിയിൽ നിന്നും 5 സ്റ്റോക്കുകൾ.
       - 'Fresh breakouts' കാറ്റഗറിയിൽ നിന്നും 5 സ്റ്റോക്കുകൾ.
       (ഇങ്ങനെ മൊത്തം കൃത്യം 15 സ്റ്റോക്കുകൾ മാത്രം തിരഞ്ഞെടുക്കുക).

    📋 OUTPUT FORMAT (EXCEL-STYLE HTML SPREADSHEET):
    മനോഹരമായ, പ്രൊഫഷണൽ Dark/Navy ആക്സെന്റോടുകൂടിയ ഒരു HTML ടേബിൾ രൂപത്തിൽ മാത്രം മറുപടി നൽകുക. കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം തരുക. 
    
    ടേബിളിൽ താഴെ പറയുന്ന 7 കോളങ്ങൾ നിർബന്ധമായും ഉണ്ടായിരിക്കണം:
    1. **Stock Name & Ticker**
    2. **Category** (Forming / Climbing / Fresh Breakout)
    3. **Global & Sector Sentiment** (ഇപ്പോഴത്തെ ന്യൂസ്/സെക്ടർ സപ്പോർട്ട്)
    4. **Deep Technical Confluence** (Weekly Trend, Daily EMA20/50, RSI, MACD, Volume)
    5. **Trigger / Entry Point (₹)**
    6. **Target (5-10% Gain) & Strict Stop Loss (Max 2-3% Risk)**
    7. **Conviction Level & Trade Rationale** (>90% വിൻ-റേറ്റ് എങ്ങനെ ഉറപ്പാക്കുന്നു?)
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🚀 Banana Patterns: Ultimate Top 15 Pick (>90% Conviction)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ & ഫെയിലിയർ അലേർട്ട് ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    wrapped_html = f"""
    <html><head><style>
      table {{ border-collapse: collapse; width: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; }}
      th, td {{ border: 1px solid #dfe6e9; text-align: left; padding: 10px; vertical-align: top; line-height: 1.4; }}
      th {{ background-color: #1e272e; color: #f1c40f; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
      tr:nth-child(even) {{ background-color: #f8f9fa; }}
      tr:nth-child(odd) {{ background-color: #ffffff; }}
      .conviction {{ color: #27ae60; font-weight: bold; }}
      .stoploss {{ color: #c0392b; font-weight: bold; }}
    </style></head><body>
    <h2 style='color: #1e272e; border-bottom: 3px solid #f1c40f; padding-bottom: 8px;'>🍌 Banana Patterns: The Ultimate 15 Swing Setups</h2>
    <p style='color: #636e72; font-size: 13px; margin-bottom: 18px;'>* Filtered strictly with Global Sentiment, Multi-Timeframe Confluence, EMA/RSI/MACD momentum, and Volume. Exactly 5 Picks from each category targeting >90% win-rate.</p>
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
                print("✅ Ultimate Top 15 റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
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
