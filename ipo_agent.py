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
    print("🔍 സ്റ്റെപ്പ് 1: ഐപിഒ ലിങ്കുകൾ കണ്ടെത്തുന്നു...")
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    active_links = []
    all_links = [] # Fallback-ന് വേണ്ടി എല്ലാ ലിങ്കുകളും സേവ് ചെയ്യുന്നു
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find('table')
        if not table: return []
        
        ths = table.find_all('th')
        header_texts = [th.get_text(strip=True).lower() for th in ths]
        close_idx = -1
        for i, h in enumerate(header_texts):
            if 'close' in h:
                close_idx = i
                break
        
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        for row in table.find_all('tr')[1:]:
            # റോയിലെ എവിടെയെങ്കിലും ലിങ്ക് ഉണ്ടോ എന്ന് പരിശോധിക്കുന്നു (കൂടുതൽ സുരക്ഷിതം)
            a_tag = row.find('a')
            if not a_tag or 'href' not in a_tag.attrs:
                continue
                
            link = a_tag['href']
            if not link.startswith("http"):
                link = "https://www.investorgain.com" + link
                
            if link not in all_links:
                all_links.append(link)
            
            is_active = False
            cols = row.find_all('td')
            if close_idx != -1 and len(cols) > close_idx:
                close_date_str = cols[close_idx].get_text(strip=True).strip()
                if close_date_str in ["", "-", "TBA", "tba"]:
                    is_active = True
                else:
                    try:
                        # തീയതി ഫോർമാറ്റ് "31 Aug" ആണെങ്കിൽ അത് പാഴ്സ് ചെയ്യാൻ ശ്രമിക്കുന്നു
                        parsed_date = datetime.strptime(f"{close_date_str} {ist_now.year}", "%d %b %Y")
                        if parsed_date.date() >= ist_now.date():
                            is_active = True
                    except:
                        # പാഴ്സിങ് ഫെയിൽ ആയാലും സേഫ്റ്റിക്ക് വേണ്ടി ആഡ് ചെയ്യുന്നു
                        is_active = True 
            else:
                is_active = True
                    
            if is_active and link not in active_links:
                active_links.append(link)
                
    except Exception as e:
        print(f"❌ മെയിൻ പേജ് അനാലിസിസ് എറർ: {e}")
        
    # ഫിൽറ്റർ ചെയ്തപ്പോൾ ഒന്നുമില്ലെങ്കിൽ, ഏറ്റവും പുതിയ 3 ലിങ്കുകൾ (Fallback) എടുക്കുന്നു
    if not active_links and all_links:
        print("⚠️ നിലവിൽ ഓപ്പൺ ആയ ഐപിഒകൾ കണ്ടെത്താനായില്ല. അവസാനത്തെ 3 ഐപിഒകൾ എടുക്കുന്നു (Fallback)...")
        return all_links[:3]
        
    return active_links[:10] # പരമാവധി 10 എണ്ണം മാത്രം

def fetch_in_depth_ipo_data():
    target_links = get_active_and_upcoming_links()
    
    if not target_links:
        print("❌ ഡാറ്റയൊന്നും കണ്ടെത്താനായില്ല.")
        return ""
        
    print(f"🎯 {len(target_links)} ഐപിഒകൾ കണ്ടെത്തി. സ്റ്റെപ്പ് 2: ഇൻഡെപ്ത് സ്ക്രാപ്പിംഗ് ആരംഭിക്കുന്നു...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    ipo_data = []
    
    for link in target_links:
        try:
            r = requests.get(link, headers=headers, timeout=15)
            ip_soup = BeautifulSoup(r.text, "html.parser")
            
            details = f"--- Detailed Data for {link} ---\n"
            for tb in ip_soup.find_all('table')[:6]: 
                for tr in tb.find_all('tr'):
                    details += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
            ipo_data.append(details[:4000])
        except Exception as e:
            pass
            
    return "\n\n".join(ipo_data)

# ==================== 4. AI അനാലിസിസ് ====================
def analyze_ipo_data(raw_data):
    print("🧠 സ്റ്റെപ്പ് 3: AI ഡാറ്റ വിശകലനം ചെയ്യുന്നു...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    നിങ്ങൾ ഒരു വിദഗ്ദ്ധനായ ഇന്ത്യൻ സ്റ്റോക്ക് മാർക്കറ്റ് & IPO അനലിസ്റ്റാണ്. 
    താഴെ നൽകിയിരിക്കുന്ന ഡാറ്റ പരിശോധിക്കുക. ഇതിൽ ഓപ്പൺ ആയിട്ടുള്ളതോ അല്ലെങ്കിൽ അടുത്തിടെ ക്ലോസ് ചെയ്തതോ ആയ ഐപിഒകൾ ഉണ്ടാകാം.
    ഇന്നത്തെ തീയതി: {current_date}
    
    🚨 നിങ്ങളുടെ ടാസ്ക്കുകൾ:
    1. **SUBSCRIPTION DETAILS:** ഇൻഡിവിജ്വൽ പേജുകളുടെ ഡാറ്റയിൽ നിന്നും ഓരോ ഐപിഒയുടെയും QIB, NII, Retail സബ്സ്ക്രിപ്ഷൻ വിവരങ്ങൾ (എത്ര മടങ്ങ് എന്ന്) കൃത്യമായി കണ്ടെത്തി 'Subscription' കോളത്തിൽ നൽകുക.
    2. **DAILY GMP HISTORY & AI STRATEGY:** 
       - ഡാറ്റയിലുള്ള തിയ്യതി തിരിച്ചുള്ള GMP വിവരങ്ങൾ പരിശോധിച്ച്, കഴിഞ്ഞ 4-5 ദിവസങ്ങളിലെ ഡെയിലി GMP ഹിസ്റ്ററി (ഉദാ: Day 1: ₹10, Day 2: ₹12...) 'AI Analysis & Recommendation' കോളത്തിൽ ലിസ്റ്റ് ആയി ചേർക്കുക.
       - ഐപിഒ നിലവിൽ ഓപ്പൺ ആണെങ്കിൽ, ലിസ്റ്റിംഗ് ഗെയിൻ 15%-ന് മുകളിൽ ആണെങ്കിൽ "🟢 APPLY" എന്നും, അല്ലെങ്കിൽ "🔴 AVOID" എന്നും നിർദ്ദേശിക്കുക. ഐപിഒ ക്ലോസ് ആയതാണെങ്കിൽ (Closed) എന്ന് മാത്രം രേഖപ്പെടുത്തുക.
    
    📋 OUTPUT FORMAT (CRITICAL):
    ഒരു Excel ഷീറ്റ് പോലെയുള്ള മനോഹരമായ **HTML ടേബിൾ** രൂപത്തിൽ മാത്രം ഔട്ട്പുട്ട് നൽകുക. ടേബിളിൽ താഴെ പറയുന്ന 6 കോളങ്ങൾ ഉണ്ടായിരിക്കണം:
    
    | IPO Name | Dates (Start - End) | GMP & Listing Gain (%) | Subscription (QIB/NII/Retail) | GMP Trend (ഉയരുന്നു/കുറയുന്നു) | AI Analysis, Recommendation & Daily GMP History |
    
    - കോഡ് ബ്ലോക്ക് ഫോർമാറ്റിൽ (```html ... ```) മാത്രം മറുപടി നൽകുക.
    
    ഡാറ്റ:
    {raw_data}
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "📊 IPO Analysis: Scraped Report (Active/Recent)", response.text.replace("```html", "").replace("
