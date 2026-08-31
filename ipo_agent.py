import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
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

from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. SMART FILTERING & IN-DEPTH SCRAPER ====================
def get_active_and_upcoming_links():
    """ആദ്യം മെയിൻ പേജിൽ പോയി ഓപ്പൺ/അപ്കമിംഗ് ഐപിഒകളുടെ ലിങ്ക് മാത്രം ഫിൽറ്റർ ചെയ്ത് എടുക്കുന്നു"""
    print("🔍 സ്റ്റെപ്പ് 1: Active & Upcoming ഐപിഒകളെ കണ്ടെത്തുന്നു...")
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    active_links = []
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find('table')
        if not table: return []
        
        # ടേബിളിൽ 'Close' ഡേറ്റ് ഏത് കോളത്തിൽ ആണെന്ന് കണ്ടുപിടിക്കുന്നു
        ths = table.find_all('th')
        header_texts = [th.get_text(strip=True).lower() for th in ths]
        close_idx = -1
        for i, h in enumerate(header_texts):
            if 'close' in h:
                close_idx = i
                break
        
        # ഇന്ത്യൻ സമയം എടുക്കുന്നു
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if not cols: continue
            
            a_tag = cols[0].find('a')
            if not a_tag or 'href' not in a_tag.attrs:
                continue
                
            link = a_tag['href']
            if not link.startswith("http"):
                link = "https://www.investorgain.com" + link
            
            is_active = False
            if close_idx != -1 and len(cols) > close_idx:
                close_date_str = cols[close_idx].get_text(strip=True)
                # തീയതി ഇല്ലെങ്കിലോ (TBA), അല്ലെങ്കിൽ ക്ലോസ് ഡേറ്റ് ഇന്നോ അതിനുശേഷമോ ആണെങ്കിലോ Active ആയി കണക്കാക്കും
                if close_date_str == "-" or close_date_str == "" or "tba" in close_date_str.lower():
                    is_active = True
                else:
                    try:
                        close_date = datetime.strptime(f"{close_date_str}-{ist_now.year}", "%d-%b-%Y")
                        if close_date.date() >= ist_now.date():
                            is_active = True
                    except:
                        is_active = True # തീയതി വായിക്കാൻ കഴിഞ്ഞില്ലെങ്കിൽ ബാക്കപ്പ് ആയി എടുക്കുന്നു
            else:
                if len(active_links) < 8: is_active = True
                    
            if is_active:
                active_links.append(link)
                
    except Exception as e:
        print(f"❌ മെയിൻ പേജ് അനാലിസിസ് എറർ: {e}")
        
    return active_links

def fetch_in_depth_ipo_data():
    """കണ്ടെത്തിയ ലിങ്കുകളിൽ മാത്രം പോയി ഇൻഡെപ്ത് സ്ക്രാപ്പിംഗ് നടത്തുന്നു"""
    target_links = get_active_and_upcoming_links()
    
    if not target_links:
        return ""
        
    print(f"🎯 {len(target_links)} Active/Upcoming ഐപിഒകൾ കണ്ടെത്തി. സ്റ്റെപ്പ് 2: ഇൻഡെപ്ത് സ്ക്രാപ്പിംഗ് ആരംഭിക്കുന്നു...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    ipo_data = []
    
    for link in target_links:
        try:
            print(f"   👉 സ്ക്രാപ്പ് ചെയ്യുന്നു: {link}")
            r = requests.get(link, headers=headers, timeout=10)
            ip_soup = BeautifulSoup(r.text, "html.parser")
            
            details = f"--- Detailed Data for {link} ---\n"
            # സബ്സ്ക്രിപ്ഷനും ഡെയിലി ജിഎംപിയും ഉൾപ്പെടുന്ന ആദ്യത്തെ 6 ടേബിളുകൾ മാത്രം എടുക്കുന്നു
            for tb in ip_soup.find_all('table')[:6]: 
                for tr in tb.find_all('tr'):
                    details += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
            ipo_data.append(details[:4000])
        except Exception as e:
            print(f"❌ Error scraping {link}: {e}")
            
    return "\n\n".join(ipo_data)

# ==================== 4. AI അനാലിസിസ് ====================
def analyze_ipo_data(raw_data):
    print("🧠 സ്റ്റെപ്പ് 3: AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു വിദഗ്ദ്ധനായ ഇന്ത്യൻ സ്റ്റോക്ക് മാർക്കറ്റ് & IPO അനലിസ്റ്റാണ്. 
    താഴെ നൽകിയിരിക്കുന്ന ഡാറ്റ നിലവിൽ ഓപ്പൺ ആയിട്ടുള്ളതും (Active), വരാനിരിക്കുന്നതുമായ (Upcoming) ഐപിഒകളുടേത് മാത്രമാണ് (ഇതിൽ ക്ലോസ് ആയവ ഒന്നുമില്ല).
    
    🚨 നിങ്ങളുടെ ടാസ്ക്കുകൾ:
    1. **SUBSCRIPTION DETAILS:** ഇൻഡിവിജ്വൽ പേജുകളുടെ ഡാറ്റയിൽ നിന്നും ഓരോ ഐപിഒയുടെയും QIB, NII, Retail സബ്സ്ക്രിപ്ഷൻ വിവരങ്ങൾ (എത്ര മടങ്ങ് എന്ന്) കൃത്യമായി കണ്ടെത്തി 'Subscription' കോളത്തിൽ നൽകുക.
    2. **DAILY GMP HISTORY & AI STRATEGY:** 
       - ഡാറ്റയിലുള്ള തിയ്യതി തിരിച്ചുള്ള GMP വിവരങ്ങൾ പരിശോധിച്ച്, കഴിഞ്ഞ 4-5 ദിവസങ്ങളിലെ ഡെയിലി GMP ഹിസ്റ്ററി (ഉദാ: Day 1: ₹10, Day 2: ₹12...) 'AI Analysis & Recommendation' കോളത്തിൽ ലിസ്റ്റ് ആയി ചേർക്കുക.
       - പ്രതീക്ഷിക്കുന്ന ലിസ്റ്റിംഗ് ഗെയിൻ (Listing Gain) 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക. നിങ്ങളുടെ തീരുമാനത്തിനുള്ള കാരണം വ്യക്തമാക്കുക.
    
    📋 OUTPUT FORMAT (CRITICAL):
    ഒരു Excel ഷീറ്റ് പോലെയുള്ള മനോഹരമായ **HTML ടേബിൾ** രൂപത്തിൽ മാത്രം ഔട്ട്പുട്ട് നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    
    | IPO Name | Dates (Start - End) | GMP & Listing Gain (%) | Subscription (QIB/NII/Retail) | GMP Trend (ഉയരുന്നു/കുറയുന്നു) | AI Analysis, Recommendation & Daily GMP History |
    
    - കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക. കാർഡുകൾ ഉപയോഗിക്കരുത്.
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "📊 IPO Analysis: Active & Upcoming Scraped Report", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 5. ഇമെയിൽ അയക്കൽ ====================
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
      .apply {{ color: #27ae60; font-weight: bold; }}
      .avoid {{ color: #c0392b; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h2 style='color: #2c3e50; margin-bottom: 5px;'>🎯 Active & Upcoming IPO Analysis Report</h2>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 20px;'>* Only currently open and upcoming IPOs are strictly filtered and analyzed in-depth for Subscriptions and Daily GMP trends.</p>
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
        print("നിലവിൽ ഓപ്പൺ ആയിട്ടുള്ളതോ വരാനിരിക്കുന്നതോ ആയ ഐപിഒകൾ ഒന്നും കണ്ടെത്തിയില്ല. ഇമെയിൽ അയയ്ക്കുന്നില്ല.")
