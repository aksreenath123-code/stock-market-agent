import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
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

from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. Intelligent Deep Scraper ====================
def fetch_in_depth_ipo_data():
    print("🌐 ഇന്റലിജന്റ് ഡീപ് സ്ക്രാപ്പിംഗ് ആരംഭിക്കുന്നു...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    ipo_data = []
    
    # സ്റ്റെപ്പ് 1: മെയിൻ പേജിൽ നിന്നും നിലവിലെ IPO-കളുടെ ലിങ്കുകൾ എടുക്കുന്നു
    main_url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    target_links = []
    
    try:
        res = requests.get(main_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        main_data = "--- Main GMP Dashboard ---\n"
        tables = soup.find_all('table')
        if tables:
            for row in tables[0].find_all('tr'):
                cols = row.find_all(['th', 'td'])
                main_data += " | ".join([c.get_text(strip=True) for c in cols]) + "\n"
                
                # IPO-യുടെ ഇൻഡിവിജ്വൽ പേജ് ലിങ്ക് കണ്ടെത്തുന്നു
                if cols:
                    a_tag = cols[0].find('a')
                    if a_tag and 'href' in a_tag.attrs:
                        target_links.append(a_tag['href'])
                        
        ipo_data.append(main_data[:5000])
    except Exception as e:
        print(f"❌ Main URL Error: {e}")

    # സ്റ്റെപ്പ് 2: കണ്ടെത്തിയ ലിങ്കുകളിൽ പോയി Day-by-Day GMP & Subscription എടുക്കുന്നു (ആദ്യത്തെ 8 എണ്ണം മാത്രം)
    print(f"🔗 {len(target_links)} ലിങ്കുകൾ കണ്ടെത്തി. ഇവയിൽ കയറി ഡാറ്റ എടുക്കുന്നു...")
    
    for link in target_links[:8]:
        if not link.startswith("http"):
            link = "https://www.investorgain.com" + link
        try:
            print(f"🔍 ഡീപ് സ്ക്രാപ്പിംഗ്: {link}")
            r = requests.get(link, headers=headers, timeout=10)
            ip_soup = BeautifulSoup(r.text, "html.parser")
            
            details = f"--- Detailed Data (Daily GMP & Subs) for {link} ---\n"
            # ഇൻഡിവിജ്വൽ പേജിലെ ആദ്യത്തെ 6 ടേബിളുകൾ എടുക്കുന്നു (ഇതിലാണ് ഹിസ്റ്ററി ഉള്ളത്)
            for tb in ip_soup.find_all('table')[:6]: 
                for tr in tb.find_all('tr'):
                    details += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
            ipo_data.append(details[:4000])
        except Exception as e:
            print(f"❌ Error scraping {link}")

    # സ്റ്റെപ്പ് 3: ചിറ്റോർഗഡിലെ സബ്സ്ക്രിപ്ഷൻ പേജ് കൂടി ബാക്കപ്പ് ആയി എടുക്കുന്നു
    try:
        c_url = "https://www.chittorgarh.com/report/ipo_subscription_status_live/21/"
        r = requests.get(c_url, headers=headers, timeout=10)
        c_soup = BeautifulSoup(r.text, "html.parser")
        c_data = "--- Chittorgarh Subscription Details ---\n"
        for tb in c_soup.find_all('table')[:2]:
            for tr in tb.find_all('tr'):
                c_data += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
        ipo_data.append(c_data[:5000])
    except Exception as e:
        pass
        
    return "\n\n".join(ipo_data)

# ==================== 4. AI അനാലിസിസ് ====================
def analyze_ipo_data(raw_data):
    print("🧠 AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു വിദഗ്ദ്ധനായ ഇന്ത്യൻ സ്റ്റോക്ക് മാർക്കറ്റ് & IPO അനലിസ്റ്റാണ്. 
    താഴെ നൽകിയിരിക്കുന്നത് മെയിൻ പേജുകളിൽ നിന്നും, ഓരോ ഐപിഒയുടെയും ഇൻഡിവിജ്വൽ പേജുകളിൽ നിന്നും (Deep Scraped) എടുത്ത വിശദമായ ഡാറ്റയാണ്. ഇതിൽ ഓരോ ദിവസത്തെയും GMP ഹിസ്റ്ററിയും കൃത്യമായ സബ്സ്ക്രിപ്ഷനും ഉൾപ്പെടുന്നു.
    ഇന്നത്തെ തീയതി: {current_date}.
    
    🚨 കർശനമായ മാനദണ്ഡങ്ങൾ (CRITICAL RULES):
    1. **VALIDITY CHECK:** ക്ലോസ് ചെയ്യാത്ത (Currently Open) ഐപിഒകളും, വരാനിരിക്കുന്ന (Upcoming) ഐപിഒകളും മാത്രമേ റിപ്പോർട്ടിൽ ഉൾപ്പെടുത്താവൂ.
    2. **SUBSCRIPTION DETAILS:** ഇൻഡിവിജ്വൽ പേജുകളുടെ ഡാറ്റയിൽ നിന്നും QIB, NII, Retail എന്നിവ കൃത്യമായി കണ്ടെത്തി 'Subscription' കോളത്തിൽ നൽകുക.
    3. **DAILY GMP HISTORY & AI STRATEGY:** 
       - ഡാറ്റയിലുള്ള തിയ്യതി തിരിച്ചുള്ള GMP വിവരങ്ങൾ (Date-wise GMP) പരിശോധിച്ച്, കഴിഞ്ഞ 4-5 ദിവസങ്ങളിലെ GMP ട്രെൻഡ് (ഉദാ: Day 1: ₹10, Day 2: ₹12...) 'AI Analysis & Recommendation' കോളത്തിൽ ലിസ്റ്റ് ആയി ചേർക്കുക.
       - ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY", അല്ലെങ്കിൽ "🔴 AVOID" എന്ന് നിർദ്ദേശിക്കുക. കാരണം വ്യക്തമാക്കുക.
    
    📋 OUTPUT FORMAT (CRITICAL):
    ഒരു Excel ഷീറ്റ് പോലെയുള്ള മനോഹരമായ **HTML ടേബിൾ** രൂപത്തിൽ മാത്രം ഔട്ട്പുട്ട് നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    
    | IPO Name | Dates (Start - End) | GMP & Listing Gain (%) | Subscription (QIB/NII/Retail) | GMP Trend (ഉയരുന്നു/കുറയുന്നു) | AI Analysis, Recommendation & Daily GMP History |
    
    - കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക. 
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "📊 Deep IPO Analysis: Daily GMP History & Exact Subscriptions", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കുന്നു...")
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
      .apply {{ color: #27ae60; font-weight: bold; }}
      .avoid {{ color: #c0392b; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50; margin-bottom: 5px;'>IPO Analysis Report</h2>
    <p style='color: #7f8c8d; font-size: 12px; margin-bottom: 20px;'>* Includes Day-by-Day GMP trends and Deep Subscription Analysis.</p>
    {html_content}
    </body>
    </html>
    """
    
    msg.attach(MIMEText(wrapped_html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("✅ ഐപിഒ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
    except Exception as e:
        print(f"❌ ഇമെയിൽ അയക്കുന്നതിൽ പരാജയപ്പെട്ടു: {e}")

if __name__ == "__main__":
    extracted_data = fetch_in_depth_ipo_data()
    if extracted_data.strip():
        subject, content = analyze_ipo_data(extracted_data)
        send_email(subject, content)
    else:
        print("ഡാറ്റ ലഭ്യമല്ല. പ്രോഗ്രാം നിർത്തുന്നു.")
