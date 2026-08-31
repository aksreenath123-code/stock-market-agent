import sys
import subprocess
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import time
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

import requests
from bs4 import BeautifulSoup
from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 3. INTELLIGENT SCRAPER & RETRY LOGIC ====================
def clean_url(url_str):
    cleaned = re.sub(r'^\[.*?\]\((.*?)\)$', r'\1', str(url_str).strip())
    cleaned = cleaned.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    cleaned = cleaned.replace("'", "").replace('"', '').strip()
    return cleaned

def fetch_with_retry(url, retries=3):
    clean_u = clean_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for attempt in range(retries):
        try:
            res = requests.get(clean_u, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.text
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed for {clean_u}: {e}")
            time.sleep(2)
    return None

def get_active_and_upcoming_links():
    print("🔍 സ്റ്റെപ്പ് 1: ഐപിഒ ലിങ്കുകൾ കണ്ടെത്തുന്നു...")
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/"
    
    active_links = []
    all_links = [] 
    
    html_content = fetch_with_retry(url)
    if not html_content:
        print("❌ മെയിൻ പേജ് സ്ക്രാപ്പിംഗ് പരാജയപ്പെട്ടു.")
        return []

    try:
        soup = BeautifulSoup(html_content, "html.parser")
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
            a_tag = row.find('a')
            if not a_tag or 'href' not in a_tag.attrs:
                continue
                
            link = a_tag['href']
            if not link.startswith("http"):
                link = "https://www.investorgain.com" + link
                
            link = clean_url(link)
                
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
                        parsed_date = datetime.strptime(f"{close_date_str} {ist_now.year}", "%d %b %Y")
                        if parsed_date.date() >= ist_now.date():
                            is_active = True
                    except:
                        is_active = True 
            else:
                is_active = True
                    
            if is_active and link not in active_links:
                active_links.append(link)
                
    except Exception as e:
        print(f"❌ ഡാറ്റ പാഴ്സിങ് എറർ: {e}")
        
    if not active_links and all_links:
        print("⚠️ നിലവിൽ ഓപ്പൺ ആയ ഐപിഒകൾ കണ്ടെത്താനായില്ല. അവസാനത്തെ 3 ഐപിഒകൾ എടുക്കുന്നു (Fallback)...")
        return all_links[:3]
        
    return active_links[:10] 

def fetch_in_depth_ipo_data():
    target_links = get_active_and_upcoming_links()
    ipo_data = []
    
    if not target_links:
        print("⚠️ ഡീപ് ലിങ്കുകൾ കിട്ടിയില്ല. ബാക്കപ്പ് ഡാറ്റ ഉപയോഗിക്കുന്നു...")
        backup_html = fetch_with_retry("https://www.chittorgarh.com/")
        if backup_html:
            b_soup = BeautifulSoup(backup_html, "html.parser")
            b_data = "--- Fallback Main Data ---\n"
            for tb in b_soup.find_all('table')[:2]: 
                for tr in tb.find_all('tr'):
                    b_data += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
            ipo_data.append(b_data[:5000])
        return "\n\n".join(ipo_data)
        
    print(f"🎯 {len(target_links)} ഐപിഒകൾ കണ്ടെത്തി. സ്റ്റെപ്പ് 2: ഇൻഡെപ്ത് സ്ക്രാപ്പിംഗ് ആരംഭിക്കുന്നു...")
    
    for link in target_links:
        try:
            ip_html = fetch_with_retry(link)
            if not ip_html: continue
            
            ip_soup = BeautifulSoup(ip_html, "html.parser")
            details = f"--- Detailed Data for {link} ---\n"
            for tb in ip_soup.find_all('table')[:6]: 
                for tr in tb.find_all('tr'):
                    details += " | ".join([td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]) + "\n"
            ipo_data.append(details[:4000])
        except Exception:
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
    return "📊 IPO Analysis: Intelligent Scraped Report", response.text.replace("```html", "").replace("```", "").strip()

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
    <h2 style='color: #2c3e50; margin-bottom: 5px;'>🎯 IPO Analysis Report</h2>
    <p style='color: #7f8c8d; font-size: 13px; margin-bottom: 20px;'>* Features auto-cleaning, smart retries, and fallback logic for uninterrupted data fetching.</p>
    {html_content}
    </body>
    </html>
    """
    
    msg.attach(MIMEText(wrapped_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ==================== 6. MAIN EXECUTION WITH RETRY LOGIC ====================
if __name__ == "__main__":
    extracted_data = fetch_in_depth_ipo_data()
    
    if extracted_data.strip():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # എഐ അനാലിസിസും ഇമെയിൽ അയക്കലും ഇവിടെ നടക്കുന്നു
                subject, content = analyze_ipo_data(extracted_data)
                send_email(subject, content)
                print("✅ ഐപിഒ റിപ്പോർട്ട് വിജയകരമായി തയ്യാറാക്കി അയച്ചു!")
                break # എല്ലാം വിജയകരമായി കഴിഞ്ഞാൽ ലൂപ്പിൽ നിന്നും പുറത്ത് വരുന്നു
            
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} പരാജയപ്പെട്ടു (AI/Email Error): {e}")
                
                if attempt < max_retries - 1:
                    print("⏳ 1 മിനിറ്റിനുശേഷം വീണ്ടും ശ്രമിക്കുന്നു (Retrying in 60 seconds)...")
                    time.sleep(60) # 1 മിനിറ്റ് കാത്തിരിക്കുന്നു
                else:
                    print("❌ 3 തവണ ശ്രമിച്ചിട്ടും പരാജയപ്പെട്ടു. പ്രോഗ്രാം പൂർണ്ണമായും നിർത്തുന്നു.")
    else:
        print("ഡാറ്റയൊന്നും ലഭിച്ചില്ല. ഇമെയിൽ അയയ്ക്കുന്നില്ല.")
