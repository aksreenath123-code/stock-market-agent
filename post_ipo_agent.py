import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import random
from datetime import datetime

# ==================== 1. ലൈബ്രറി ഇൻസ്റ്റാളേഷൻ ====================
REQUIRED_PACKAGES = ["requests", "google-genai", "beautifulsoup4", "cloudscraper"]

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
import cloudscraper
from bs4 import BeautifulSoup
from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

raw_mc_cookie = os.getenv("MONEYCONTROL_COOKIE", "")
MONEYCONTROL_COOKIE = str(raw_mc_cookie).strip().replace('\n', '').replace('\r', '')

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. ADVANCED SCRAPING MODULES ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

def fetch_post_ipo_performance():
    print("🌐 InvestorGain-ൽ നിന്നും Post-IPO പെർഫോമൻസ് ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://www.investorgain.com/report/live-ipo-performance/332/"
    
    scraper = cloudscraper.create_scraper()
    for attempt in range(2):
        try:
            res = scraper.get(url, timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.find('table')
                scraped_data = ""
                if table:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols: scraped_data += " | ".join(cols) + "\n"
                
                if len(scraped_data) > 100:
                    print("✅ Cloudscraper വഴി Post-IPO ഡാറ്റ ലഭിച്ചു.")
                    return scraped_data[:25000]
        except Exception as e:
            pass
        time.sleep(random.uniform(3, 6))

    print("⚠️ Cloudscraper പരാജയപ്പെട്ടു. ബദൽ മാർഗ്ഗം (Requests) ഉപയോഗിക്കുന്നു...")
    for attempt in range(2):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                table = soup.find('table')
                scraped_data = ""
                if table:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols: scraped_data += " | ".join(cols) + "\n"
                
                if len(scraped_data) > 100:
                    print("✅ Requests വഴി Post-IPO ഡാറ്റ ലഭിച്ചു.")
                    return scraped_data[:25000]
        except Exception as e:
            print(f"⚠️ Post-IPO ശ്രമം പരാജയപ്പെട്ടു: {e}")
        time.sleep(random.uniform(3, 6))
        
    print("❌ Post-IPO ഡാറ്റ പൂർണ്ണമായും ലഭ്യമല്ല.")
    return ""

def fetch_moneycontrol_earnings():
    print("🌐 മണികൺട്രോളിൽ നിന്നും ഡെയിലി കോർപ്പറേറ്റ് റിസൾട്ടുകൾ ശേഖരിക്കുന്നു...")
    if not MONEYCONTROL_COOKIE:
        print("⚠️ MONEYCONTROL_COOKIE ലഭ്യമല്ല.")
        return ""
        
    mc_urls = [
        "https://www.moneycontrol.com/markets/earnings/",
        "https://www.moneycontrol.com/stocks/marketstats/bse-results/",
        "https://www.moneycontrol.com/stocks/marketinfo/results/boardmeating.php"
    ]
    
    headers = {
        "Cookie": MONEYCONTROL_COOKIE,
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    scraper = cloudscraper.create_scraper()
    
    for url in mc_urls:
        try:
            time.sleep(random.uniform(4, 7))
            res = scraper.get(url, headers=headers, timeout=30)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tables = soup.find_all('table')
                scraped_data = ""
                for table in tables[:3]:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols: scraped_data += " | ".join(cols) + "\n"
                
                if len(scraped_data) > 100:
                    print(f"✅ Earnings ഡാറ്റ ലഭിച്ചു (URL: {url}).")
                    return scraped_data[:25000]
                else:
                    print(f"⚠️ URL ({url}) വർക്ക് ചെയ്തു, പക്ഷേ ടേബിൾ ഇല്ല.")
            else:
                print(f"⚠️ Moneycontrol HTTP Error: {res.status_code} for {url}")
        except Exception as e:
            print(f"⚠️ Earnings സ്ക്രാപ്പിംഗ് പരാജയപ്പെട്ടു ({url}): {e}")
            
    return ""

# ==================== 4. AI ANALYSIS MODULES (WITH RETRY LOGIC) ====================
def analyze_post_ipo_trend(raw_data):
    print("🧠 Post-IPO ട്രെൻഡ് വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് സ്വിംഗ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് അടുത്തിടെ ലിസ്റ്റ് ചെയ്ത IPO-കളുടെ ഡാറ്റയാണ്:
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്: കഴിഞ്ഞ 3 മാസത്തിനുള്ളിൽ ലിസ്റ്റ് ചെയ്ത, നിലവിൽ Base Breakout അല്ലെങ്കിൽ മികച്ച Uptrend കാണിക്കുന്ന മികച്ച 5 സ്റ്റോക്കുകൾ കണ്ടെത്തുക.
    OUTPUT FORMAT: ഒരു HTML ടേബിൾ (കോളങ്ങൾ: Stock Name, Listing Date, Issue vs CMP, Trend Analysis, AI Verdict). കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക. ഇൻലൈൻ CSS വേണ്ട.
    """
    
    # 🚨 API Disconnect ഒഴിവാക്കാനുള്ള റീട്രൈ ലോജിക്
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            print(f"⚠️ API Error (Post-IPO attempt {attempt+1}): {e}")
            time.sleep(5) # എറർ വന്നാൽ 5 സെക്കൻഡ് കാത്തിരിക്കുന്നു
            
    raise Exception("Gemini API completely failed for Post-IPO analysis after 3 retries.")

def analyze_earnings_momentum(raw_data):
    print("🧠 കോർപ്പറേറ്റ് റിസൾട്ടുകൾ & YoY/QoQ സ്വിംഗ് പ്രോബബിലിറ്റി വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു ഫണ്ടമെന്റൽ & ക്വാണ്ടിറ്റേറ്റീവ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് മണികൺട്രോളിൽ നിന്നുള്ള ഡെയിലി ഏണിങ്സ് ഡാറ്റയാണ്:
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്: മികച്ച YoY/QoQ വളർച്ച കാണിച്ച ടോപ്പ് 5 സ്റ്റോക്കുകൾ കണ്ടെത്തുക. അവയുടെ പോസ്റ്റ്-ഏണിങ്സ് സ്വിംഗ് ട്രേഡിംഗ് സാധ്യതകൾ വിലയിരുത്തുക.
    OUTPUT FORMAT: ഒരു HTML ടേബിൾ മാത്രം നൽകുക.
    കോളങ്ങൾ: | Stock Name | Result Highlights | Swing Setup (Breakout/Volume) | Conviction Rate | AI Action |
    കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക. ഇൻലൈൻ CSS വേണ്ട.
    """
    
    # 🚨 API Disconnect ഒഴിവാക്കാനുള്ള റീട്രൈ ലോജിക്
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            print(f"⚠️ API Error (Earnings attempt {attempt+1}): {e}")
            time.sleep(5)
            
    raise Exception("Gemini API completely failed for Earnings analysis after 3 retries.")

# ==================== 5. EMAIL COMPOSITION ====================
def send_combined_email(ipo_html, earnings_html):
    print("📧 സംയോജിപ്പിച്ച മാസ്റ്റർ റിപ്പോർട്ട് മെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "🚀 Daily Elite Swing Agent: Post-IPO & Earnings"
    
    wrapped_html = f"""
    <html>
    <head>
    <style>
      body {{ background-color: #ffffff; color: #000000; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 10px; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 14px; margin-top: 10px; margin-bottom: 30px; background-color: #ffffff; }}
      th, td {{ border: 1px solid #cccccc; text-align: left; padding: 12px; vertical-align: top; line-height: 1.5; color: #000000; }}
      th {{ background-color: #111827; color: #ffffff; font-weight: bold; text-transform: uppercase; font-size: 13px; }}
      tr:nth-child(even) {{ background-color: #f9fafb; }}
      tr:nth-child(odd) {{ background-color: #ffffff; }}
      h2 {{ color: #111827; margin-bottom: 5px; border-bottom: 2px solid #2563eb; padding-bottom: 5px; display: inline-block; font-size: 20px; }}
      p {{ color: #374151; font-size: 13px; margin-bottom: 10px; }}
    </style>
    </head>
    <body>
        <h1 style="text-align: center; color: #111827;">📈 Daily Elite Swing Trading Report</h1>
        
        <h2>🚀 Section 1: Post-IPO Base Breakouts (Top 5)</h2>
        <p>* Multi-timeframe analysis on recently listed IPOs showing strong base breakouts.</p>
        {ipo_html}
        
        <h2>💰 Section 2: Earnings Momentum (Top 5)</h2>
        <p>* High conviction PEAD (Post-Earnings Announcement Drift) swing setups.</p>
        {earnings_html}
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
    msg["Subject"] = "❌ ALERT: Master Agent Failed!"
    html_content = f"<html><body><h3 style='color: #000000;'>⚠️ Swing Agent Failed</h3><pre style='color: #000000;'>{error_message}</pre></body></html>"
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ==================== 6. MAIN EXECUTION ====================
if __name__ == "__main__":
    ipo_data = fetch_post_ipo_performance()
    earnings_data = fetch_moneycontrol_earnings()
    
    if ipo_data.strip() or earnings_data.strip():
        try:
            if ipo_data:
                ipo_result = analyze_post_ipo_trend(ipo_data)
            else:
                ipo_result = "<p style='color: #b91c1c; font-weight: bold;'>⚠️ Post-IPO data could not be fetched today (Bot protection active).</p>"
                
            if earnings_data:
                earnings_result = analyze_earnings_momentum(earnings_data)
            else:
                earnings_result = "<p style='color: #b91c1c; font-weight: bold;'>⚠️ Earnings data unavailable (URLs changed or Cookie expired).</p>"
            
            send_combined_email(ipo_result, earnings_result)
            print("✅ മാസ്റ്റർ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ അനാലിസിസ് അല്ലെങ്കിൽ ഇമെയിൽ പരാജയപ്പെട്ടു: {e}")
            send_failure_email(str(e))
            sys.exit(1)
    else:
        print("❌ ഡാറ്റയൊന്നും ലഭിച്ചില്ല. സ്ക്രാപ്പിംഗ് പൂർണ്ണമായും പരാജയപ്പെട്ടു.")
        send_failure_email("Both scraping sources (InvestorGain & Moneycontrol) failed to return data.")
        sys.exit(1)
