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
GEMINI_API_KEY = os.getenv("SSH2_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

raw_mc_cookie = os.getenv("MONEYCONTROL_COOKIE", "")
MONEYCONTROL_COOKIE = str(raw_mc_cookie).strip().replace('\n', '').replace('\r', '')

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. MULTI-SOURCE SCRAPING MODULES ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def generic_table_scraper(url, headers, source_name):
    scraper = cloudscraper.create_scraper()
    for attempt in range(2):
        try:
            time.sleep(random.uniform(4, 7))
            res = scraper.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tables = soup.find_all('table')
                scraped_data = f"--- Source: {source_name} ---\n"
                
                for table in tables[:3]: # ആദ്യത്തെ 3 ടേബിളുകൾ എടുക്കുന്നു
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols: scraped_data += " | ".join(cols) + "\n"
                
                if len(scraped_data) > 150:
                    print(f"✅ ഡാറ്റ ലഭിച്ചു: {source_name}")
                    return scraped_data[:25000]
        except Exception as e:
            pass
        
        # Fallback to pure requests
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tables = soup.find_all('table')
                scraped_data = f"--- Source: {source_name} ---\n"
                for table in tables[:3]:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols: scraped_data += " | ".join(cols) + "\n"
                if len(scraped_data) > 150:
                    print(f"✅ ഡാറ്റ ലഭിച്ചു (Requests വഴി): {source_name}")
                    return scraped_data[:25000]
        except:
            pass
            
    print(f"⚠️ പരാജയപ്പെട്ടു: {source_name}")
    return ""

def fetch_post_ipo_performance():
    print("🌐 Post-IPO പെർഫോമൻസ് ഡാറ്റ ശേഖരിക്കുന്നു (Multi-Source)...")
    
    ipo_sources = [
        {"url": "https://www.investorgain.com/report/live-ipo-performance/332/", "name": "InvestorGain"},
        {"url": "https://www.chittorgarh.com/report/mainboard-ipo-list-in-india-bse-nse/83/", "name": "Chittorgarh"},
        {"url": "https://ipowatch.in/ipo-performance/", "name": "IPO Watch"}
    ]
    
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    for source in ipo_sources:
        data = generic_table_scraper(source["url"], headers, source["name"])
        if data:
            return data # ഒരെണ്ണത്തിൽ നിന്ന് കിട്ടിയാൽ ഉടനെ അത് റിട്ടേൺ ചെയ്യും
            
    print("❌ Post-IPO ഡാറ്റ എല്ലാ സോഴ്സുകളിൽ നിന്നും പരാജയപ്പെട്ടു.")
    return ""

def fetch_earnings_data():
    print("🌐 കോർപ്പറേറ്റ് റിസൾട്ടുകൾ ശേഖരിക്കുന്നു (Multi-Source)...")
    
    earnings_sources = [
        {"url": "https://www.moneycontrol.com/markets/earnings/", "name": "Moneycontrol (Main)", "needs_cookie": True},
        {"url": "https://www.moneycontrol.com/stocks/marketstats/bse-results/", "name": "Moneycontrol (BSE)", "needs_cookie": True},
        {"url": "https://www.screener.in/results/latest/", "name": "Screener.in", "needs_cookie": False},
        {"url": "https://economictimes.indiatimes.com/markets/stocks/earnings", "name": "Economic Times", "needs_cookie": False}
    ]
    
    for source in earnings_sources:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        if source["needs_cookie"] and MONEYCONTROL_COOKIE:
            headers["Cookie"] = MONEYCONTROL_COOKIE
            
        data = generic_table_scraper(source["url"], headers, source["name"])
        if data:
            return data
            
    print("❌ Earnings ഡാറ്റ എല്ലാ സോഴ്സുകളിൽ നിന്നും പരാജയപ്പെട്ടു.")
    return ""

# ==================== 4. AI ANALYSIS MODULES (WITH RETRY LOGIC) ====================
def analyze_post_ipo_trend(raw_data):
    print("🧠 Post-IPO ട്രെൻഡ് വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് സ്വിംഗ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് അടുത്തിടെ ലിസ്റ്റ് ചെയ്ത IPO-കളുടെ ഡാറ്റയാണ് (ഏത് സോഴ്സ് ആണെന്ന് മുകളിൽ കൊടുത്തിട്ടുണ്ട്):
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്: കഴിഞ്ഞ 3 മാസത്തിനുള്ളിൽ ലിസ്റ്റ് ചെയ്ത, നിലവിൽ Base Breakout അല്ലെങ്കിൽ മികച്ച Uptrend കാണിക്കുന്ന മികച്ച 5 സ്റ്റോക്കുകൾ കണ്ടെത്തുക. ഡാറ്റ ഫോർമാറ്റ് വെബ്സൈറ്റിനനുസരിച്ച് മാറിയേക്കാം, അത് മനസ്സിലാക്കി ഉത്തരം നൽകുക.
    OUTPUT FORMAT: ഒരു HTML ടേബിൾ (കോളങ്ങൾ: Stock Name, Listing Date, Performance, Trend Analysis, AI Verdict). കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക. ഇൻലൈൻ CSS വേണ്ട.
    """
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            print(f"⚠️ API Error (Post-IPO attempt {attempt+1}): {e}")
            time.sleep(5)
            
    raise Exception("Gemini API failed for Post-IPO analysis.")

def analyze_earnings_momentum(raw_data):
    print("🧠 കോർപ്പറേറ്റ് റിസൾട്ടുകൾ & സ്വിംഗ് പ്രോബബിലിറ്റി വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു ഫണ്ടമെന്റൽ & ക്വാണ്ടിറ്റേറ്റീവ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് വിവിധ ഫിനാൻസ് വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഡെയിലി ഏണിങ്സ് ഡാറ്റയാണ്:
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്: മികച്ച റിസൾട്ടുകൾ (YoY/QoQ Growth അല്ലെങ്കിൽ Net Profit) കാണിച്ച ടോപ്പ് 5 സ്റ്റോക്കുകൾ കണ്ടെത്തുക. അവയുടെ പോസ്റ്റ്-ഏണിങ്സ് സ്വിംഗ് ട്രേഡിംഗ് സാധ്യതകൾ വിലയിരുത്തുക.
    OUTPUT FORMAT: ഒരു HTML ടേബിൾ മാത്രം നൽകുക.
    കോളങ്ങൾ: | Stock Name | Result Highlights | Swing Setup (Breakout/Volume) | Conviction Rate | AI Action |
    കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക. ഇൻലൈൻ CSS വേണ്ട.
    """
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            print(f"⚠️ API Error (Earnings attempt {attempt+1}): {e}")
            time.sleep(5)
            
    raise Exception("Gemini API failed for Earnings analysis.")

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
        <p>* Sourced dynamically from InvestorGain, Chittorgarh, or IPO Watch.</p>
        {ipo_html}
        
        <h2>💰 Section 2: Earnings Momentum (Top 5)</h2>
        <p>* Sourced dynamically from Moneycontrol, Screener.in, or Economic Times.</p>
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
    earnings_data = fetch_earnings_data()
    
    if ipo_data.strip() or earnings_data.strip():
        try:
            if ipo_data:
                ipo_result = analyze_post_ipo_trend(ipo_data)
            else:
                ipo_result = "<p style='color: #b91c1c; font-weight: bold;'>⚠️ Post-IPO data could not be fetched from any source today.</p>"
                
            if earnings_data:
                earnings_result = analyze_earnings_momentum(earnings_data)
            else:
                earnings_result = "<p style='color: #b91c1c; font-weight: bold;'>⚠️ Earnings data unavailable from all sources.</p>"
            
            send_combined_email(ipo_result, earnings_result)
            print("✅ മാസ്റ്റർ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ അനാലിസിസ് അല്ലെങ്കിൽ ഇമെയിൽ പരാജയപ്പെട്ടു: {e}")
            send_failure_email(str(e))
            sys.exit(1)
    else:
        print("❌ ഡാറ്റയൊന്നും ലഭിച്ചില്ല. സ്ക്രാപ്പിംഗ് പൂർണ്ണമായും പരാജയപ്പെട്ടു.")
        send_failure_email("All scraping sources for both Post-IPO and Earnings failed to return data.")
        sys.exit(1)
