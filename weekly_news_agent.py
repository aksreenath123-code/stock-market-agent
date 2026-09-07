import sys
import subprocess
import os
import time

# ==================== 1. ഓട്ടോമാറ്റിക് ലൈബ്രറി ഇൻസ്റ്റാളേഷൻ ====================
REQUIRED_PACKAGES = [
    "requests",
    "feedparser",
    "google-genai",
    "yfinance",
    "pandas",
    "beautifulsoup4",
    "tenacity",
    "lxml",
    "html5lib"
]

def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            pkg_name = "google.genai" if package == "google-genai" else ("bs4" if package == "beautifulsoup4" else ("tenacity" if package == "tenacity" else package))
            __import__(pkg_name)
        except ImportError:
            print(f"📦 ഇൻസ്റ്റാൾ ചെയ്യുന്നു: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_missing_packages()

# ==================== 2. പ്രധാന ഇമ്പോർട്ടുകൾ ====================
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import feedparser
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import warnings
warnings.filterwarnings("ignore")

# 3. API കോൺഫിഗറേഷൻ & സീക്രട്ടുകൾ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MC_COOKIE = os.getenv("MONEYCONTROL_COOKIE", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 4. റീട്രൈ മെക്കാനിസം & ടൈംഔട്ട് സജ്ജീകരണങ്ങൾ ====================
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception))
)
def fetch_url_with_retry(url, headers=None, timeout=12):
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response

# ==================== 5. റിലയബിൾ ന്യൂസ് ഫെച്ചിംഗ് (Pro + Financial Feeds) ====================
def fetch_reliable_market_news():
    news_items = []
    
    rss_sources = [
        "https://www.moneycontrol.com/rss/MCproideas.xml",
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://finance.yahoo.com/news/rssindex"
    ]
    
    for url in rss_sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = getattr(entry, 'title', '').strip()
                summary = getattr(entry, 'summary', '').strip()
                if title and len(title) > 5:
                    news_items.append(f"• [Financial News]: {title} - {summary[:250]}")
        except Exception:
            continue

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": MC_COOKIE
    }
    pro_urls = [
        "https://www.moneycontrol.com/news/mcpro-technical-analysis/",
        "https://www.moneycontrol.com/news/mcpro-ideas/",
        "https://www.moneycontrol.com/news/business/earnings/"
    ]
    
    for url in pro_urls:
        try:
            res = fetch_url_with_retry(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                articles = soup.select("li.clearfix, div.news_card, div.pro_art")[:6]
                for art in articles:
                    title_elem = art.find(["h2", "h3", "a"])
                    summary_elem = art.find(["p", "span"])
                    if title_elem:
                        t = title_elem.get_text(strip=True)
                        s = summary_elem.get_text(strip=True) if summary_elem else ""
                        if len(t) > 10:
                            news_items.append(f"• [MC Pro Exclusive Catalyst]: {t} | Rationale: {s[:200]}")
        except Exception:
            continue

    return news_items

# ==================== 6. അഡ്വാൻസ്ഡ് ന്യൂസ് സ്വിംഗ് അനാലിസിസ് എൻജിൻ ====================
def generate_news_swing_report():
    print("📰 ഈ ആഴ്ചയിലെ വിശ്വാസയോഗ്യമായ സാമ്പത്തിക വാർത്തകളും കാറ്റലിസ്റ്റുകളും ശേഖരിക്കുന്നു...")
    raw_news = fetch_reliable_market_news()
    
    if not raw_news or len(raw_news) < 3:
        raw_news = [
            "• [Market Catalyst]: മാക്രോ ഇക്കണോമിക് ഡാറ്റകളും ഇൻസ്റ്റിറ്റ്യൂഷണൽ മണി ഫ്ലോയും അടുത്ത ആഴ്ചത്തെ സ്വിംഗ് ട്രെൻഡ് നിർണ്ണയിക്കും.",
            "• [Sector Outlook]: സെമികണ്ടക്ടർ, ഓട്ടോമൊബൈൽ, ബാങ്കിംഗ് സെക്ടറുകളിൽ ശക്തമായ മൊമെന്റം പ്രതീക്ഷിക്കുന്നു."
        ]

    print("🧠 വാർത്തകളും സപ്ലൈ ചെയിൻ റിപ്പിൾ ഇഫക്റ്റും വിശകലനം ചെയ്ത് റാങ്ക് ചെയ്യുന്നു...")

    prompt = f"""
    നിങ്ങൾ ഒരു പ്രൊഫഷണൽ ന്യൂസ്-ബേസ്ഡ് സ്വിംഗ് ട്രേഡിംഗ് ക്വാണ്ട് അനലിസ്റ്റാണ്. 
    ശനിയാഴ്ച ലഭിച്ച ഫിനാൻഷ്യൽ വാർത്തകളും പ്രോ കാറ്റലിസ്റ്റുകളും താഴെ നൽകിയിരിക്കുന്നു.
    
    🎯 **പ്രധാന നിർദ്ദേശങ്ങൾ (CRITICAL STYLING & SORTING INSTRUCTIONS):**
    1. **Agent Header:** ഇമെയിലിന്റെ തുടക്കത്തിൽ **"📰 Weekly News-Driven Swing Intelligence Agent"** എന്ന ഹെഡിംഗ് വളരെ വ്യക്തമായി നൽകുക.
    2. **Readability & Styling (White Theme & Bold Letters):** 
       - പശ്ചാത്തലം (Background) ശുദ്ധമായ വെള്ളയോ (White / #ffffff) വളരെ സോഫ്റ്റ് ആയ ലൈറ്റ് ഗ്രേയോ ആയിരിക്കണം.
       - അക്ഷരങ്ങൾ നിർബന്ധമായും കറുത്തതോ വളരെ ഇരുണ്ടതോ ആയ **ബോൾഡ് ലെറ്റേഴ്സിൽ (Bold & Dark Text)** നൽകുക. ഫാൻസി കളറുകൾ ഒഴിവാക്കുക.
    3. **Color-Coded Conviction & Probability Badges:** 
       - കൺവിക്ഷൻ റേറ്റിനും പ്രോബബിലിറ്റിക്കും അനുസരിച്ച് എളുപ്പം തിരിച്ചറിയാൻ കളർ കോഡിംഗ് നൽകുക (ഉദാ: >90% ഉള്ളവയ്ക്ക് ഡാർക്ക് ഗ്രീൻ ബാക്ക്ഗ്രൗണ്ട് വിത്ത് വൈറ്റ് ടെക്സ്റ്റ്, 80-89% ഉള്ളവയ്ക്ക് ബ്ലൂ ബാക്ക്ഗ്രൗണ്ട്).
    4. **Descending Sorting (Highest First):** 
       - ഏറ്റവും ഉയർന്ന കൺവിക്ഷൻ റേറ്റും പ്രോബബിലിറ്റിയുമുള്ള സ്റ്റോക്കുകൾ ഏറ്റവും മുകളിലായി (Rank 1 മുതൽ ഏറ്റവും കുറഞ്ഞതിലേക്ക്) അസെൻഡിങ്/ഡിസെൻഡിങ് ഓർഡറിൽ (Highest to Lowest) കൃത്യമായി സോർട്ട് ചെയ്ത് ലിസ്റ്റ് ചെയ്യുക.
    5. **Trade Setup:** Stock Name & Symbol, Entry Price, Target Price (3-5% for 1 week), Stop Loss എന്നിവ വ്യക്തമായി നൽകുക. പൂർണ്ണമായും **മലയാളത്തിൽ** (സാങ്കേതിക പദങ്ങൾ ഇംഗ്ലീഷിൽ) തയ്യാറാക്കുക.

    📊 ശേഖരിച്ച വാർത്തകളും കാറ്റലിസ്റ്റുകളും:
    {chr(10).join(raw_news)}

    ```html ... ``` ഫോർമാറ്റിൽ മാത്രം കോഡ് തിരികെ നൽകുക.
    """

    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    html_content = response.text.replace("```html", "").replace("```", "").strip()
    
    return "📰 Weekly News-Driven Swing Intelligence Agent Report", html_content

# ==================== 7. ഇമെയിൽ അയക്കൽ (Retry സഹിതം) ====================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=15))
def send_email_with_retry(subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    print("🚀 ന്യൂസ് സ്വിംഗ് ഇന്റലിജൻസ് ഏജന്റ് വർക്ക് ചെയ്തുതുടങ്ങുന്നു...")
    subject, content = generate_news_swing_report()
    send_email_with_retry(subject, content)
    print("✅ ന്യൂസ് ഏജന്റ് റിപ്പോർട്ട് വിജയകരമായി അയച്ചു കഴിഞ്ഞു!")
