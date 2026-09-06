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
GEMINI_API_KEY = os.getenv("SSH2_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

raw_cookie = os.getenv("BANANA_COOKIE")
BANANA_COOKIE = str(raw_cookie).strip().replace('\n', '').replace('\r', '') if raw_cookie else None

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. COOKIE-BASED DATA EXTRACTION ====================
def fetch_banana_data():
    print("🌐 ബനാന പാറ്റേൺസിൽ നിന്നും ഡീറ്റെയിൽഡ് ഡാറ്റ ശേഖരിക്കുന്നു...")
    
    url = "https://bananapatterns.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    print("🧠 90%+ Win-Rate അനാലിസിസും കളർ-കോഡഡ് ഡിസൈനും തയ്യാറാക്കുന്നു...")
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
    - 7 കോളങ്ങളുള്ള ഒരു ടേബിൾ നിർമ്മിക്കുക: | Stock Name & Ticker | Category | Global & Sector Sentiment | Deep Technical Confluence | Trigger / Entry Point (₹) | Target & Strict Stop Loss | Conviction Level & Rationale |
    - 🎨 **COLOR CODING RULE (CRITICAL):** 'Category' കോളത്തിലെ ടെക്സ്റ്റിന് നിർബന്ധമായും താഴെ പറയുന്ന HTML ക്ലാസുകൾ നൽകണം (അതായത് `<span class="category-forming">Forming</span>` എന്ന രീതിയിൽ):
      - Forming ആണെങ്കിൽ: `class="category-forming"`
      - Climbing ആണെങ്കിൽ: `class="category-climbing"`
      - Fresh Breakout ആണെങ്കിൽ: `class="category-fresh"`
    - ഇൻലൈൻ സ്റ്റൈലുകളോ (inline CSS) ഡാർക്ക് ബാക്ക്ഗ്രൗണ്ടുകളോ ഉപയോഗിക്കരുത്. വളരെ ക്ലീൻ ആയ ഡിസൈൻ ആയിരിക്കണം.

    **ഭാഗം 2: SECTION 2 - COMPLETE MASTER LIST (ALL STOCKS)**
    - "<h3>2. Complete Master List of All Stocks</h3>" എന്ന് ഹെഡിങ് നൽകുക.
    - ഡാറ്റയിൽ നിന്നും കണ്ടെത്താൻ കഴിഞ്ഞ എല്ലാ സ്റ്റോക്കുകളുടെയും പേരുകൾ കാറ്റഗറി തിരിച്ച് ലളിതമായ ബുള്ളറ്റ് പോയിന്റുകളിലോ (ul/li) ടേബിളിലോ ലിസ്റ്റ് ചെയ്യുക. ഇവിടെ അനാലിസിസ് ആവശ്യമില്ല.

    📋 OUTPUT FORMAT:
    മനോഹരമായ HTML കോഡ് മാത്രം മറുപടി നൽകുക. കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം തരുക. 
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🚀 Banana Patterns: Top 15 Elite Picks (Color Coded)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ & ഫെയിലിയർ അലേർട്ട് ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    wrapped_html = f"""
    <html><head><style>
      body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333333; padding: 10px; }}
      .container {{ background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
      table {{ border-collapse: collapse; width: 100%; margin-bottom: 25px; background-color: #ffffff; }}
      th, td {{ border: 1px solid #e0e0e0; text-align: left; padding: 14px; vertical-align: top; line-height: 1.5; color: #333333; font-size: 14px; }}
      th {{ background-color: #2c3e50; color: #ffffff; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
      tr:nth-child(even) {{ background-color: #f8f9fa; }}
      tr:hover {{ background-color: #f1f3f5; }}
      
      /* 🎨 കളർ കോഡിംഗ് ബാഡ്ജുകൾ (Color Badges) */
      .category-forming {{ background-color: #e3f2fd; color: #0d47a1; font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; border: 1px solid #bbdefb; }}
      .category-climbing {{ background-color: #fff3e0; color: #e65100; font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; border: 1px solid #ffe0b2; }}
      .category-fresh {{ background-color: #e8f5e9; color: #1b5e20; font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; border: 1px solid #c8e6c9; }}
      
      h2 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 8px; margin-top: 0; }}
      h3 {{ color: #2980b9; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
      p {{ color: #555555; }}
    </style></head><body>
    <div class="container">
        <h2>🍌 Banana Patterns: Elite Daily Report</h2>
        <p><i>* Highly readable format. Green/Orange/Blue badges represent different categories.</i></p>
        {html_content}
    </div>
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
    msg["Subject"] = "❌ ALERT: Banana Patterns Analysis Failed"
    html_content = f"""
    <html><body style="font-family: Arial, sans-serif;">
    <h3 style="color: #c0392b;">⚠️ Banana Agent Failed (After 3 Retries)</h3>
    <pre style="background: #f8d7da; color: #721c24; padding: 12px; border-radius: 4px;">{error_message}</pre>
    <p>കുക്കി എക്സ്പയർ ആയോ എന്ന് പരിശോധിക്കുക.</p>
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
                print("✅ Readable Top 15 & Master List റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
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
