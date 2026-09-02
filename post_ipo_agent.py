import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

# പുതിയ മണികൺട്രോൾ കുക്കി
raw_mc_cookie = os.getenv("MONEYCONTROL_COOKIE")
MONEYCONTROL_COOKIE = str(raw_mc_cookie).strip().replace('\n', '').replace('\r', '') if raw_mc_cookie else None

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. SCRAPING MODULES ====================

def fetch_post_ipo_performance():
    """InvestorGain-ൽ നിന്നും Post-IPO ഡാറ്റ എടുക്കുന്നു"""
    print("🌐 കഴിഞ്ഞ മാസങ്ങളിലെ ഐപിഒ പെർഫോമൻസ് ഡാറ്റ ശേഖരിക്കുന്നു...")
    url = "https://www.investorgain.com/report/live-ipo-performance/332/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    scraped_data = ""
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find('table')
            if table:
                for row in table.find_all('tr'):
                    cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                    if cols: scraped_data += " | ".join(cols) + "\n"
        return scraped_data[:25000]
    except Exception as e:
        print(f"❌ Post-IPO സ്ക്രാപ്പിംഗ് എറർ: {e}")
        return ""

def fetch_moneycontrol_earnings():
    """Moneycontrol Pro വഴി ഡെയിലി റിസൾട്ടുകൾ എടുക്കുന്നു"""
    print("🌐 മണികൺട്രോളിൽ നിന്നും ഡെയിലി കോർപ്പറേറ്റ് റിസൾട്ടുകൾ ശേഖരിക്കുന്നു...")
    url = "https://www.moneycontrol.com/stocks/marketinfo/results/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": MONEYCONTROL_COOKIE if MONEYCONTROL_COOKIE else ""
    }
    
    scraped_data = ""
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            tables = soup.find_all('table')
            for table in tables[:3]: # പ്രധാനപ്പെട്ട ആദ്യത്തെ ടേബിളുകൾ മാത്രം
                for row in table.find_all('tr'):
                    cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                    if cols: scraped_data += " | ".join(cols) + "\n"
        return scraped_data[:25000]
    except Exception as e:
        print(f"❌ Earnings സ്ക്രാപ്പിംഗ് എറർ: {e}")
        return ""

# ==================== 4. AI ANALYSIS MODULES ====================

def analyze_post_ipo_trend(raw_data):
    """Post-IPO AI അനാലിസിസ്"""
    print("🧠 Post-IPO ട്രെൻഡ് വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു എലൈറ്റ് സ്വിംഗ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് അടുത്തിടെ ലിസ്റ്റ് ചെയ്ത IPO-കളുടെ ഡാറ്റയാണ്:
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്: കഴിഞ്ഞ 3 മാസത്തിനുള്ളിൽ ലിസ്റ്റ് ചെയ്ത, നിലവിൽ Base Breakout അല്ലെങ്കിൽ മികച്ച Uptrend കാണിക്കുന്ന മികച്ച 5 സ്റ്റോക്കുകൾ കണ്ടെത്തുക.
    OUTPUT FORMAT: ഒരു ലൈറ്റ് തീം HTML ടേബിൾ (കോളങ്ങൾ: Stock Name, Listing Date, Issue vs CMP, Trend Analysis, AI Verdict). കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക.
    """
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text.replace("```html", "").replace("```", "").strip()

def analyze_earnings_momentum(raw_data):
    """Earnings AI അനാലിസിസ് (YoY, QoQ & Swing Conviction)"""
    print("🧠 കോർപ്പറേറ്റ് റിസൾട്ടുകൾ & YoY/QoQ സ്വിംഗ് പ്രോബബിലിറ്റി വിശകലനം ചെയ്യുന്നു...")
    prompt = f"""
    നിങ്ങൾ ഒരു ഫണ്ടമെന്റൽ & ക്വാണ്ടിറ്റേറ്റീവ് ട്രേഡിംഗ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്നത് മണികൺട്രോളിൽ നിന്നുള്ള ഡെയിലി ഏണിങ്സ് (Earnings Results) ഡാറ്റയാണ്:
    {raw_data}
    
    നിങ്ങളുടെ ടാസ്ക്:
    1. **YoY & QoQ Growth:** ഈ ഡാറ്റയിൽ നിന്നും Year-on-Year (YoY), Quarter-on-Quarter (QoQ) എന്നിവയിൽ മികച്ച വളർച്ച കാണിച്ച ടോപ്പ് 5 സ്റ്റോക്കുകൾ മാത്രം കണ്ടെത്തുക.
    2. **Swing Trading Probability:** ഈ മികച്ച റിസൾട്ടുകൾ കാരണം വരുന്ന മൊമെന്റം (Trailing stop-loss, EMA/RSI breakouts എന്നിവ പരിഗണിച്ച്) വെച്ച് ഇതിൽ സ്വിംഗ് ട്രേഡ് ചെയ്യാനുള്ള സാധ്യതകൾ വിലയിരുത്തുക.
    3. **Conviction Rate:** ഓരോ ട്രേഡിന്റെയും സക്സസ് കൺവിക്ഷൻ റേറ്റ് (ഉദാ: 92%) ഉൾപ്പെടുത്തുക.
    
    OUTPUT FORMAT: ഒരു ലൈറ്റ് തീം HTML ടേബിൾ മാത്രം നൽകുക.
    കോളങ്ങൾ: | Stock Name | Result Highlights (YoY/QoQ Growth) | Technical Swing Setup (Breakout/Volume Potential) | Conviction Rate (%) | AI Action |
    കോഡ് ബ്ലോക്കിൽ മാത്രം മറുപടി നൽകുക.
    """
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. EMAIL COMPOSITION ====================
def send_combined_email(ipo_html, earnings_html):
    print("📧 സംയോജിപ്പിച്ച മാസ്റ്റർ റിപ്പോർട്ട് മെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "🚀 Daily Master Swing Agent: Post-IPO & Earnings Breakouts"
    
    wrapped_html = f"""
    <html><head><style>
      body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 15px; color: #333; }}
      .container {{ background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
      table {{ border-collapse: collapse; width: 100%; margin-bottom: 35px; }}
      th, td {{ border: 1px solid #e0e0e0; text-align: left; padding: 12px; line-height: 1.5; font-size: 13.5px; }}
      th {{ background-color: #1e3799; color: #ffffff; font-weight: 600; font-size: 13px; text-transform: uppercase; }}
      h2 {{ color: #1e3799; border-bottom: 3px solid #4a69bd; padding-bottom: 8px; margin-top: 20px; }}
      .header-title {{ color: #2c3e50; text-align: center; border-bottom: none; margin-bottom: 30px; font-size: 24px; }}
    </style></head><body>
    <div class="container">
        <h1 class="header-title">📈 Daily Elite Swing Trading Report</h1>
        
        <h2>🚀 Section 1: Post-IPO Base Breakouts (Top 5)</h2>
        <p style="color: #7f8c8d; font-size: 13px;">* Multi-timeframe analysis on IPOs listed in the last 3 months showing strong base breakouts.</p>
        {ipo_html}
        
        <h2>💰 Section 2: Earnings Momentum & QoQ/YoY Stars (Top 5)</h2>
        <p style="color: #7f8c8d; font-size: 13px;">* Analyzed using Moneycontrol Pro data. Focusing on high conviction PEAD (Post-Earnings Announcement Drift) swing setups.</p>
        {earnings_html}
    </div>
    </body></html>
    """
    msg.attach(MIMEText(wrapped_html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ==================== 6. MAIN EXECUTION ====================
if __name__ == "__main__":
    ipo_data = fetch_post_ipo_performance()
    earnings_data = fetch_moneycontrol_earnings()
    
    if ipo_data.strip() or earnings_data.strip():
        try:
            # പാരലൽ ആയി രണ്ട് അനാലിസിസും ചെയ്യുന്നു
            ipo_result = analyze_post_ipo_trend(ipo_data) if ipo_data else "<p>No Post-IPO data available.</p>"
            earnings_result = analyze_earnings_momentum(earnings_data) if earnings_data else "<p>No Earnings data available or Cookie expired.</p>"
            
            send_combined_email(ipo_result, earnings_result)
            print("✅ മാസ്റ്റർ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ അനാലിസിസ് അല്ലെങ്കിൽ ഇമെയിൽ പരാജയപ്പെട്ടു: {e}")
            sys.exit(1)
    else:
        print("❌ ഡാറ്റയൊന്നും ലഭിച്ചില്ല. കുക്കികൾ പരിശോധിക്കുക.")
        sys.exit(1)
