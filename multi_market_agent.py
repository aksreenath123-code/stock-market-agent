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
#GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MC_COOKIE = os.getenv("MONEYCONTROL_COOKIE", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 4. ടെക്നിക്കൽ അനാലിസിസ് എൻജിൻ ====================
def calculate_indicators(df):
    if len(df) < 15:
        return None
    
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
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
    """എൽഎൽഎമ്മിന് കൂടുതൽ ഡാറ്റ നൽകാൻ ഫിൽറ്റർ റിലാക്സ് ചെയ്തിരിക്കുന്നു"""
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
            
            # AI-ക്ക് തിരഞ്ഞെടുക്കാൻ കൂടുതൽ സ്റ്റോക്കുകൾ നൽകുന്നു
            if ind['RSI'] >= 40 and ind['RVOL'] >= 0.8:
                clean_name = ticker.replace('.NS', '')
                screened_stocks.append(
                    f"• {clean_name} ({ticker}): Price {currency_symbol}{ind['LTP']} "
                    f"({ind['Change%']:+}%) | RSI: {ind['RSI']} | RVOL: {ind['RVOL']}x | >20EMA: {ind['IsAboveEMA']}"
                )
        except Exception:
            continue
            
    return screened_stocks

# ==================== 5. INDIAN MARKET SCANNER ====================
def fetch_indian_market():
    # 50 പ്രമുഖ ഇന്ത്യൻ സ്റ്റോക്കുകൾ
    indian_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "BHARTIARTL.NS", "LT.NS", "SBIN.NS", "TATASTEEL.NS", "TATAMOTORS.NS",
        "ADANIENT.NS", "KOTAKBANK.NS", "AXISBANK.NS", "ITC.NS", "SUNPHARMA.NS",
        "TITAN.NS", "BAJFINANCE.NS", "MARUTI.NS", "JSWSTEEL.NS", "BEL.NS",
        "M&M.NS", "HCLTECH.NS", "WIPRO.NS", "HAL.NS", "ZOMATO.NS", "TRENT.NS", 
        "BAJAJFINSV.NS", "COALINDIA.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", 
        "ULTRACEMCO.NS", "GRASIM.NS", "TECHM.NS", "HINDALCO.NS", "CIPLA.NS",
        "DRREDDY.NS", "EICHERMOT.NS", "APOLLOHOSP.NS", "HEROMOTOCO.NS", "DLF.NS",
        "INDUSINDBK.NS", "CHOLAFIN.NS", "TVSMOTOR.NS", "VEDL.NS", "GAIL.NS"
    ]
    
    print("🇮🇳 ഇന്ത്യൻ സ്റ്റോക്കുകളുടെ ഡാറ്റ സ്കാൻ ചെയ്യുന്നു...")
    swing_candidates = scan_tickers_for_swing(indian_tickers)
    
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
    നിങ്ങൾ ഒരു പ്രൊഫഷണൽ സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന ഇന്ത്യൻ ഡാറ്റ വിശകലനം ചെയ്യുക.
    
    🚨 കർത്തശനമായ നിർദ്ദേശങ്ങൾ (CRITICAL INSTRUCTIONS):
    1. STOCK NAME & SYMBOL MISSING ISSUE: ഓരോ സ്റ്റോക്കിന്റെയും പേരും സിംബലും കാർഡിന്റെ ഹെഡിംഗിൽ നിർബന്ധമായും നൽകിയിരിക്കണം. (ഉദാഹരണത്തിന്: <h3>RELIANCE (RELIANCE.NS)</h3>). ഇത് ഒഴിവാക്കരുത്!
    2. കൃത്യം 20 സ്റ്റോക്കുകൾ താഴെ പറയുന്ന 3 വിഭാഗങ്ങളിലായി തരംതിരിക്കുക:
       - സെക്ഷൻ 1: 🏆 ടോപ്പ് 10 സ്വിംഗ് ട്രേഡ് പിക്കുകൾ (Rank 1 മുതൽ 10 വരെ). ഏറ്റവും വിജയസാധ്യതയുള്ളത് (Highest Probability of 3-5% profit in 1 week) ഒന്നാമതായി നൽകുക.
       - സെക്ഷൻ 2: 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ (High RSI & Strong Uptrend).
       - സെക്ഷൻ 3: 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ (RVOL > 1.5x).

    ഓരോ സ്റ്റോക്കിനും Entry Zone, Target (3-5%), Stop Loss എന്നിവ നൽകുക.

    📊 സാങ്കേതിക ഡാറ്റ:
    {chr(10).join(swing_candidates)}

    💎 Moneycontrol Pro ഡാറ്റ:
    {chr(10).join(mc_news)}

    Modern Dark HTML കാർഡുകൾ ഉപയോഗിച്ച് മനോഹരമായ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🇮🇳 Indian Market: Top 10 Swing Picks & Breakouts", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 6. US MARKET SCANNER ====================
def fetch_us_market():
    us_tickers = [
        "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "AMD",
        "NFLX", "PLTR", "AVGO", "SMCI", "COIN", "MARA", "QCOM", "ARM",
        "UBER", "CRWD", "PYPL", "INTC", "DIS", "CRM", "MSTR", "MU", 
        "CSCO", "ADBE", "PEP", "COST", "TMUS", "TXN", "INTU", "AMAT",
        "ISRG", "NOW", "BKNG", "VRTX", "REGN", "ADI", "PANW", "SNPS"
    ]
    
    print("🇺🇸 യുഎസ് സ്റ്റോക്കുകളുടെ ഡാറ്റ സ്കാൻ ചെയ്യുന്നു...")
    us_swing_candidates = scan_tickers_for_swing(us_tickers)
    
    prompt = f"""
    നിങ്ങൾ ഒരു Wall Street സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന യുഎസ് ഡാറ്റ വിശകലനം ചെയ്യുക.
    
    🚨 കർത്തശനമായ നിർദ്ദേശങ്ങൾ (CRITICAL INSTRUCTIONS):
    1. STOCK NAME & SYMBOL MISSING ISSUE: ഓരോ സ്റ്റോക്കിന്റെയും പേരും സിംബലും കാർഡിന്റെ ഹെഡിംഗിൽ നിർബന്ധമായും നൽകിയിരിക്കണം. (ഉദാഹരണത്തിന്: <h3>NVIDIA (NVDA)</h3>). ഇത് ഒഴിവാക്കരുത്!
    2. കൃത്യം 20 സ്റ്റോക്കുകൾ താഴെ പറയുന്ന 3 വിഭാഗങ്ങളിലായി തരംതിരിക്കുക:
       - സെക്ഷൻ 1: 🏆 ടോപ്പ് 10 സ്വിംഗ് ട്രേഡ് പിക്കുകൾ (Rank 1 മുതൽ 10 വരെ). ഏറ്റവും വിജയസാധ്യതയുള്ളത് (Highest Probability of 3-5% profit in 1 week) ഒന്നാമതായി നൽകുക.
       - സെക്ഷൻ 2: 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ (High RSI & Strong Uptrend).
       - സെക്ഷൻ 3: 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ (RVOL > 1.5x).

    ഓരോ സ്റ്റോക്കിനും Entry Zone, Target (3-5%), Stop Loss എന്നിവ നൽകുക.

    📊 യുഎസ് സാങ്കേതിക ഡാറ്റ:
    {chr(10).join(us_swing_candidates)}

    Modern Dark HTML കാർഡുകൾ ഉപയോഗിച്ച് മനോഹരമായ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """

    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🇺🇸 US Market: Top 10 Swing Picks & Breakouts", response.text.replace("```html", "").replace("```", "").strip()

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
    print(f"✅ {market_type.upper()} സ്വിംഗ് ട്രേഡിംഗ് റിപ്പോർട്ട് (10+5+5) വിജയകരമായി അയച്ചു!")
