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
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
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
    return "🚀 Banana Patterns: Top 15 Elite Picks (Color Coded)", response.text.replace("```html", "").replace("
