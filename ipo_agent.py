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

# ==================== 2. API കോൺഫിഗറേഷൻ (പുതിയ വേരിയബിൾ) ====================
# ഇവിടെ പുതിയ വേരിയബിൾ ആയ IPO_GEMINI_API_KEY നൽകിയിരിക്കുന്നു
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഡീപ് സ്ക്രാപ്പിംഗ് ====================
def fetch_in_depth_ipo_data():
    urls = [
        "https://www.investorgain.com/report/ipo-gmp-live/331/",
        "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/",
        "https://www.chittorgarh.com/"
    ]
    
    print("🌐 ഐപിഒ ഡാറ്റ ഡീപ് സ്ക്രാപ്പ് ചെയ്യുന്നു...")
    ipo_data = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                tables = soup.find_all('table')
                page_data = ""
                for table in tables[:4]:
                    for row in table.find_all('tr'):
                        cols = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
                        if cols:
                            page_data += " | ".join(cols) + "\n"
                
                if not page_data:
                    page_data = soup.get_text(separator=' | ', strip=True)[:15000]
                    
                ipo_data.append(f"Source URL: {url}\nData:\n{page_data[:20000]}\n{'-'*50}")
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
    താഴെ നൽകിയിരിക്കുന്ന 3 വെബ്സൈറ്റുകളിൽ നിന്നുള്ള ഡീറ്റെയിൽഡ് ടേബിൾ ഡാറ്റ വിശകലനം ചെയ്യുക.
    ഇന്നത്തെ തീയതി: {current_date}.
    
    🚨 കർശനമായ മാനദണ്ഡങ്ങൾ (CRITICAL RULES):
    1. **VALIDITY CHECK (100% ഗ്യാരണ്ടി):** ക്ലോസ് ചെയ്യാത്ത (Currently Open) ഐപിഒകളും, വരാനിരിക്കുന്ന (Upcoming) ഐപിഒകളും മാത്രമേ റിപ്പോർട്ടിൽ ഉൾപ്പെടുത്താവൂ. ക്ലോസിംഗ് തീയതി കഴിഞ്ഞവ പൂർണ്ണമായും ഒഴിവാക്കുക!
    2. **GMP TREND:** ഡാറ്റയിലുള്ള മുൻ ദിവസങ്ങളിലെ GMP പരിശോധിച്ച് ട്രെൻഡ് (ഉയരുന്നതാണോ, കുറയുന്നതാണോ, സ്ഥിരമാണോ) എന്ന് വ്യക്തമാക്കുക. പോസിറ്റീവ്/നെഗറ്റീവ് ട്രെൻഡ് സൂചിപ്പിക്കുക.
    3. **SUBSCRIPTION DETAILS:** ലഭ്യമായ സബ്സ്ക്രിപ്ഷൻ ഡാറ്റ (QIB, NII, Retail) എത്ര മടങ്ങ് എന്ന് ചേർക്കുക.
    4. **AI STRATEGY (>15% GAIN RULE):** 
       - ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ പ്രതീക്ഷിക്കുന്നുണ്ടെങ്കിൽ, കൂടാതെ GMP ട്രെൻഡ് പോസിറ്റീവ് ആണെങ്കിൽ മാത്രം "🟢 APPLY" എന്ന് നിർദ്ദേശിക്കുക.
       - 15%-ൽ താഴെയാണെങ്കിലോ, ട്രെൻഡ് നെഗറ്റീവ് ആണെങ്കിലോ "🔴 AVOID" എന്ന് നിർദ്ദേശിക്കുക.
       - നിങ്ങളുടെ തീരുമാനത്തിനുള്ള കാരണം വ്യക്തമാക്കുക.
    
    ഓരോ ഐപിഒയ്ക്കും ഈ ഫോർമാറ്റിൽ വിവരങ്ങൾ നൽകുക:
    - 📌 IPO Name (Mainboard / SME)
    - 📅 Dates (Open to Close)
    - 💰 Current GMP & Est. Listing Price
    - 📈 GMP Trend Analysis
    - 📊 Subscription Status
    - 🤖 AI Recommendation (APPLY or AVOID + Reason based on 15% rule)

    ഡാറ്റ:
    {raw_data}
    
    Modern Dark HTML കാർഡുകൾ ഉപയോഗിച്ച് മനോഹരമായ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക. കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക. ഏറ്റവും മികച്ചവ ആദ്യം നൽകുക.
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🚀 Advanced IPO Analysis: GMP Trends, Subscriptions & 15% Strategy", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))

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
