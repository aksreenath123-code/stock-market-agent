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

# ==================== 3. അഡ്വാൻസ്ഡ് ഡീപ് സ്ക്രാപ്പിംഗ് (സബ്സ്ക്രിപ്ഷൻ ഉൾപ്പെടെ) ====================
def fetch_in_depth_ipo_data():
    # ജിഎംപിക്കും സബ്സ്ക്രിപ്ഷനും വേണ്ടി പ്രത്യേകം ലിങ്കുകൾ ഉൾപ്പെടുത്തിയിരിക്കുന്നു
    urls = [
        "https://www.investorgain.com/report/ipo-gmp-live/331/",
        "https://www.investorgain.com/report/live-ipo-subscription-status/333/", # ഇൻവെസ്റ്റർഗെയിൻ സബ്സ്ക്രിപ്ഷൻ
        "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/",
        "https://ipowatch.in/ipo-subscription-status/", # ഐപിഒ വാച്ച് സബ്സ്ക്രിപ്ഷൻ
        "https://www.chittorgarh.com/report/ipo_subscription_status_live/21/", # ചിറ്റോർഗഡ് സബ്സ്ക്രിപ്ഷൻ
        "https://www.chittorgarh.com/"
    ]
    
    print("🌐 ഐപിഒ സബ്സ്ക്രിപ്ഷൻ & ജിഎംപി ഡാറ്റ സ്ക്രാപ്പ് ചെയ്യുന്നു...")
    ipo_data = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # കൂടുതൽ ടേബിളുകൾ (8 എണ്ണം വരെ) എക്സ്ട്രാക്ട് ചെയ്യുന്നു
                tables = soup.find_all('table')
                page_data = ""
                for table in tables[:8]:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols:
                            page_data += " | ".join(cols) + "\n"
                
                if not page_data:
                    page_data = soup.get_text(separator=' | ', strip=True)[:20000]
                    
                # ഡാറ്റ ലിമിറ്റ് 30000 ആയി വർദ്ധിപ്പിച്ചു
                ipo_data.append(f"Source URL: {url}\nData:\n{page_data[:30000]}\n{'-'*50}")
                print(f"✅ വിജയകരമായി ഡാറ്റ എടുത്തു: {url}")
            else:
                print(f"⚠️ ഡാറ്റ എടുക്കാൻ കഴിഞ്ഞില്ല (Status {res.status_code}): {url}")
        except Exception as e:
            print(f"❌ എറർ {url}: {e}")
            
    return "\n".join(ipo_data)

# ==================== 4. AI അനാലിസിസ് ====================
def analyze_ipo_data(raw_data):
    print("🧠 AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു വിദഗ്ദ്ധനായ ഇന്ത്യൻ സ്റ്റോക്ക് മാർക്കറ്റ് & IPO അനലിസ്റ്റാണ്. 
    താഴെ നൽകിയിരിക്കുന്ന വിവിധ വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഡീറ്റെയിൽഡ് ടേബിൾ ഡാറ്റ വിശകലനം ചെയ്യുക.
    ഇന്നത്തെ തീയതി: {current_date}.
    
    🚨 കർശനമായ മാനദണ്ഡങ്ങൾ (CRITICAL RULES):
    1. **VALIDITY CHECK (100% ഗ്യാരണ്ടി):** ക്ലോസ് ചെയ്യാത്ത (Currently Open) ഐപിഒകളും, വരാനിരിക്കുന്ന (Upcoming) ഐപിഒകളും മാത്രമേ റിപ്പോർട്ടിൽ ഉൾപ്പെടുത്താവൂ. ക്ലോസിംഗ് തീയതി കഴിഞ്ഞവ പൂർണ്ണമായും ഒഴിവാക്കുക!
    2. **SUBSCRIPTION DETAILS:** ഡാറ്റയിലുള്ള സബ്സ്ക്രിപ്ഷൻ ടേബിളുകളിൽ നിന്നും QIB, NII, Retail എന്നിവ എത്ര മടങ്ങ് (x) സബ്സ്ക്രൈബ് ചെയ്തു എന്ന് കൃത്യമായി കണ്ടെത്തി 'Subscription' കോളത്തിൽ നൽകുക.
    3. **DAILY GMP TREND & AI STRATEGY:** 
       - ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ പ്രതീക്ഷിക്കുന്നുണ്ടെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക.
       - നിങ്ങളുടെ തീരുമാനത്തിനുള്ള കാരണം വ്യക്തമാക്കുക.
       - **പ്രധാനപ്പെട്ടത്:** ഇതോടൊപ്പം ഓരോ ദിവസത്തെയും GMP എങ്ങനെയായിരുന്നു എന്നുള്ള ഹിസ്റ്ററി (ഉദാ: Day 1: ₹10, Day 2: ₹15, Day 3: ₹12...) ഡാറ്റയിൽ നിന്നും കണ്ടെത്തി ഈ 'AI Analysis & Recommendation' കോളത്തിൽ തന്നെ ഒരു ലിസ്റ്റ് ആയി താഴെ നൽകണം.
    
    📋 OUTPUT FORMAT (CRITICAL):
    ഒരു Excel ഷീറ്റ് പോലെ തോന്നിക്കുന്ന മനോഹരമായ, പ്രൊഫഷണലായ ഒരു **HTML ടേബിൾ** രൂപത്തിൽ മാത്രം ഔട്ട്പുട്ട് നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ നിർബന്ധമായും ഉണ്ടായിരിക്കണം:
    
    | IPO Name | Dates (Start - End) | GMP & Listing Gain (%) | Subscription | GMP Trend | AI Analysis, Recommendation & Daily GMP |
    
    - ബോർഡറുകളോട് കൂടിയ (with solid borders) ആധുനിക HTML CSS സ്റ്റൈൽ ടേബിൾ ഉപയോഗിക്കുക.
    - കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക. 
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "📊 IPO Analysis: Consolidated Spreadsheet Report (With Daily GMP & Subs)", response.text.replace("```html", "").replace("```", "").strip()

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
      th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; vertical-align: top; }}
      th {{ background-color: #2c3e50; color: white; }}
      tr:nth-child(even) {{ background-color: #f2f2f2; color: #333; }}
      tr:nth-child(odd) {{ background-color: #ffffff; color: #333; }}
      ul {{ margin-top: 5px; padding-left: 20px; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50;'>IPO Analysis Report (Open & Upcoming)</h2>
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
