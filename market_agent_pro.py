
import sys
import subprocess

# ==================== 1. ഓട്ടോമാറ്റിക് ലൈബ്രറി ഇൻസ്റ്റാളേഷൻ ====================
REQUIRED_PACKAGES = [
    "requests",
    "feedparser",
    "google-genai",
    "yfinance",
    "pandas",
    "beautifulsoup4"
]

def install_missing_packages():
    """ആവശ്യമായ ലൈബ്രറികൾ ഇല്ലെങ്കിൽ തനിയെ ഇൻസ്റ്റാൾ ചെയ്യുന്നു"""
    for package in REQUIRED_PACKAGES:
        try:
            pkg_name = "google.genai" if package == "google-genai" else ("bs4" if package == "beautifulsoup4" else package)
            __import__(pkg_name)
        except ImportError:
            print(f"📦 ഇൻസ്റ്റാൾ ചെയ്യുന്നു: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_missing_packages()

# ==================== 2. പ്രധാന ഇമ്പോർട്ടുകൾ ====================
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import feedparser
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from google import genai

# 3. API കോൺഫിഗറേഷൻ & സീക്രട്ടുകൾ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MC_COOKIE = os.getenv("MONEYCONTROL_COOKIE", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 4. ടെക്നിക്കൽ അനാലിസിസ് എൻജിൻ ====================
def calculate_indicators(df):
    """RSI (14), 20 EMA, RVOL എന്നിവ കൃത്യമായി കണക്കുകൂട്ടുന്നു"""
    if len(df) < 15:
        return None
    
    # 20 EMA
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Relative Volume (RVOL) - കഴിഞ്ഞ 10 ദിവസത്തെ ശരാശരി വോളിയവുമായി താരതമ്യം
    avg_volume = df['Volume'].rolling(window=10).mean()
    df['RVOL'] = df['Volume'] / avg_volume
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    pct_change = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
    
    return {
        'LTP': round(float(latest['Close']), 2),
        'Change%': round(float(pct_change), 2),
        'RSI': round(float(latest['RSI']), 2) if not pd.isna(latest['RSI'].iloc[0] if isinstance(latest['RSI'], pd.Series) else latest['RSI']) else 50.0,
        'EMA20': round(float(latest['EMA20']), 2),
        'RVOL': round(float(latest['RVOL']), 2) if not pd.isna(latest['RVOL'].iloc[0] if isinstance(latest['RVOL'], pd.Series) else latest['RVOL']) else 1.0,
        'IsAboveEMA': bool(latest['Close'] > latest['EMA20'])
    }

def scan_tickers_for_swing(ticker_list):
    """RSI 48-70 & RVOL > 1.1x ഉള്ള ഹൈ-പ്രോബബിലിറ്റി സ്റ്റോക്കുകൾ ഫിൽട്ടർ ചെയ്യുന്നു"""
    screened_stocks = []
    currency_symbol = "₹" if any(t.endswith(".NS") for t in ticker_list) else "$"
    
    for ticker in ticker_list:
        try:
            data = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if data.empty:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns]
                
            ind = calculate_indicators(data)
            if not ind:
                continue
            
            # സ്വിംഗ് ക്രൈറ്റീരിയ: RSI 48-70 + വില 20 EMA-ക്ക് മുകളിൽ
            if 48 <= ind['RSI'] <= 70 and ind['IsAboveEMA']:
                clean_name = ticker.replace('.NS', '')
                screened_stocks.append(
                    f"• {clean_name}: Price {currency_symbol}{ind['LTP']} "
                    f"({ind['Change%']:+}%) | RSI(14): {ind['RSI']} | RVOL: {ind['RVOL']}x | Trend: > 20 EMA"
                )
        except Exception:
            continue
            
    return screened_stocks

# ==================== 5. INDIAN MARKET SCANNER (8:00 AM IST) ====================
def fetch_indian_market():
    indian_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "BHARTIARTL.NS", "LT.NS", "SBIN.NS", "TATASTEEL.NS", "TATAMOTORS.NS",
        "ADANIENT.NS", "KOTAKBANK.NS", "AXISBANK.NS", "ITC.NS", "SUNPHARMA.NS",
        "TITAN.NS", "BAJFINANCE.NS", "MARUTI.NS", "JSWSTEEL.NS", "BEL.NS"
    ]
    
    print("🇮🇳 ഇന്ത്യൻ സ്റ്റോക്കുകളുടെ RSI, RVOL, Price Action സ്കാൻ ചെയ്യുന്നു...")
    swing_candidates = scan_tickers_for_swing(indian_tickers)
    
    # Moneycontrol Pro റിസർച്ച്
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": MC_COOKIE}
    mc_news = []
    try:
        res = requests.get("https://www.moneycontrol.com/news/mcpro-technical-analysis/", headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for art in soup.select("li.clearfix, div.news_card")[:5]:
                t = art.find(["h2", "h3"])
                if t: mc_news.append(f"• MC Pro: {t.get_text(strip=True)}")
    except Exception:
        pass

    prompt = f"""
    നിങ്ങൾ ഒരു ഷോർട്ട് ടേം സ്വിംഗ് ട്രേഡിംഗ് വിദഗ്ദ്ധനാണ്. 
    താഴെ നൽകിയിരിക്കുന്ന ഇന്ത്യൻ മാർക്കറ്റ് RSI, RVOL, Price Action ഡാറ്റ പരിശോധിച്ച് പ്രീ-മാർക്കറ്റ് ഓപ്പണിംഗിനായി (8:00 AM IST) **അടുത്ത 3-5 ദിവസത്തിൽ (1 Week) 3% - 5% ടാർഗെറ്റ്** നൽകുന്ന മികച്ച സ്വിംഗ് ട്രേഡുകൾ തിരഞ്ഞെടുക്കുക.

    📊 സാങ്കേതിക ഡാറ്റ (RSI, RVOL & 20 EMA):
    {chr(10).join(swing_candidates)}

    💎 Moneycontrol Pro & Market Catalysts:
    {chr(10).join(mc_news)}

    🎨 HTML ലേഔട്ട് നിർദ്ദേശങ്ങൾ:
    - ഭാഷ: മലയാളം (സാങ്കേതിക പദങ്ങളായ Entry, Target 3-5%, SL എന്നിവ വ്യക്തമായി നൽകുക).
    - Modern Dark Theme Header, Clean Responsive Cards, Green & Gold Badges.
    - **സെക്ഷൻ 1:** 🎯 **ടോപ്പ് 1-വീക്ക് സ്വിംഗ് പിക്കുകൾ (Target: 3% - 5% Profit in 3-5 Days)** - (കമ്പനി, Entry Zone, Target Price, Stop Loss, RSI & Volume കാരണം).
    - **സെക്ഷൻ 2:** ⚡ **ഹൈ വോളിയം & RSI മൊമെന്റം ബ്രേക്ക്ഔട്ടുകൾ**.
    - **സെക്ഷൻ 3:** 🛡️ **സ്വിംഗ് ട്രേഡിംഗ് സ്ട്രാറ്റജിയും റിസ്ക് മാനേജ്മെന്റും**.

    ```html ... ``` ഫോർമാറ്റിൽ മാത്രം HTML ബോഡി നൽകുക.
    """
    
    response = client.models.generate_content(
        model="gemini-3.1-pro",
        contents=prompt
    )
    return "🇮🇳 Indian Market: 1-Week Swing Radar (RSI + Volume 3-5% Target)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 6. US MARKET SCANNER (6:00 PM IST) ====================
def fetch_us_market():
    us_tickers = [
        "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "AMD",
        "NFLX", "PLTR", "AVGO", "SMCI", "COIN", "MARA", "QCOM", "ARM"
    ]
    
    print("🇺🇸 യുഎസ് സ്റ്റോക്കുകളുടെ RSI, RVOL, Price Action സ്കാൻ ചെയ്യുന്നു...")
    us_swing_candidates = scan_tickers_for_swing(us_tickers)
    
    # US News RSS
    rss_feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    us_news = [f"• {e.title}" for e in rss_feed.entries[:6]]

    prompt = f"""
    നിങ്ങൾ ഒരു Wall Street ക്വാണ്ട് & സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്.
    ഇന്ന് വൈകുന്നേരം യുഎസ് മാർക്കറ്റ് ഓപ്പണിംഗിനായി (6:00 PM IST) താഴെ നൽകിയിരിക്കുന്ന RSI, RVOL, Price Action എന്നിവ പരിശോധിച്ച് **1 ആഴ്ചയ്ക്കുള്ളിൽ 3% - 5% മൂവ്മെന്റ്** തരാൻ സാധ്യതയുള്ള യുഎസ് സ്വിംഗ് ട്രേഡുകൾ തയാറാക്കുക.

    📊 യുഎസ് സാങ്കേതിക ഡാറ്റ (RSI, RVOL, 20 EMA):
    {chr(10).join(us_swing_candidates)}

    📰 പ്രധാന യുഎസ് കാറ്റലിസ്റ്റുകൾ & വാർത്തകൾ:
    {chr(10).join(us_news)}

    🎨 HTML ലേഔട്ട് നിർദ്ദേശങ്ങൾ:
    - ഭാഷ: മലയാളം (Tickers, Entry, Target 3-5%, Stop Loss എന്നിവ കൃത്യമായി നൽകുക).
    - Modern Responsive CSS, Dark Header, Blue & Green Badges.
    - **സെക്ഷൻ 1:** 🇺🇸 **ടോപ്പ് യുഎസ് സ്വിംഗ് ട്രേഡ് പിക്കുകൾ (3% - 5% Profit in 3-5 Days)**.
    - **സെക്ഷൻ 2:** ⚡ **RSI & Relative Volume (RVOL) ബ്രേക്ക്ഔട്ടുകൾ**.
    - **സെക്ഷൻ 3:** ⚠️ **Wall Street ഓപ്പണിംഗ് ലെവലുകൾ & മുന്നറിയിപ്പുകൾ**.

    ```html ... ``` ഫോർമാറ്റിൽ മാത്രം HTML ബോഡി നൽകുക.
    """

    response = client.models.generate_content(
        model="gemini-3.1-pro",
        contents=prompt
    )
    return "🇺🇸 US Market: Pre-Opening Swing Radar (RSI + Volume 3-5% Target)", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 7. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    market_type = sys.argv[1] if len(sys.argv) > 1 else "indian"
    
    if market_type == "us":
        subject, content = fetch_us_market()
    else:
        subject, content = fetch_indian_market()

    send_email(subject, content)
    print(f"✅ {market_type.upper()} സ്വിംഗ് ട്രേഡിംഗ് റിപ്പോർട്ട് (Gemini 3.1 Pro വഴി) വിജയകരമായി അയച്ചു!")
