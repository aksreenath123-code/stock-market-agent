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
    "lxml",
    "html5lib"
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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import feedparser
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from google import genai
import warnings
warnings.filterwarnings("ignore")

# 3. API കോൺഫിഗറേഷൻ & സീക്രട്ടുകൾ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MC_COOKIE = os.getenv("MONEYCONTROL_COOKIE", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==================== 4. യൂണിവേഴ്സ് സെലക്ഷൻ ====================
def get_sp500_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        tickers = table['Symbol'].tolist()
        return [t.replace('.', '-') for t in tickers]
    except:
        return ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "PLTR"]

def get_indian_universe():
    return [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", 
        "BAJFINANCE.NS", "LICINDIA.NS", "KOTAKBANK.NS", "LT.NS", "HINDUNILVR.NS", "AXISBANK.NS", "NTPC.NS", 
        "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "ULTRACEMCO.NS", "COALINDIA.NS", "ONGC.NS", "POWERGRID.NS", 
        "M&M.NS", "ADANIENT.NS", "TITAN.NS", "HAL.NS", "JSWSTEEL.NS", "BAJAJFINSV.NS", "TATASTEEL.NS", "ADANIPORTS.NS", 
        "HCLTECH.NS", "SIEMENS.NS", "ZOMATO.NS", "ASIANPAINT.NS", "GRASIM.NS", "VEDL.NS", "DLF.NS", "TRENT.NS", 
        "CHOLAFIN.NS", "INDIGO.NS", "PFC.NS", "RECLTD.NS", "IRFC.NS", "BHEL.NS", "GAIL.NS", "CIPLA.NS", "DRREDDY.NS",
        "EICHERMOT.NS", "APOLLOHOSP.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS", "TVSMOTOR.NS", "TECHM.NS", "HINDALCO.NS",
        "DIVISLAB.NS", "LTIM.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS", "GODREJCP.NS", "PIDILITIND.NS", "SHREECEM.NS",
        "TORNTPHARM.NS", "TATACOMM.NS", "OBEROIRLTY.NS", "LODHA.NS", "TATACHEM.NS", "VOLTAS.NS", "DIXON.NS",
        "POLYCAB.NS", "KEI.NS", "HAVELLS.NS", "CUMMINSIND.NS", "BEL.NS", "SUZLON.NS", "IREDA.NS", "NHPC.NS"
    ]

# ==================== 5. MTF സ്കോറിംഗ് എൻജിൻ (Weekly + Daily) ====================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def evaluate_stock_momentum(df):
    """ഡെയ്‌ലി, വീക്കിലി ചാർട്ടുകൾ പരിശോധിച്ച് പ്രോബബിലിറ്റി സ്കോർ നൽകുന്നു"""
    if len(df) < 60:
        return None
        
    # --- Daily Calculations ---
    df['EMA20_D'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['RSI_D'] = calculate_rsi(df['Close'])
    df['RVOL_D'] = df['Volume'] / df['Volume'].rolling(10).mean()
    
    # ക്രാബ് സോൺ കൺസോളിഡേഷൻ (കഴിഞ്ഞ 15 ദിവസത്തെ ടൈറ്റ് റേഞ്ച്)
    df['Max_15_D'] = df['High'].rolling(15).max()
    df['Min_15_D'] = df['Low'].rolling(15).min()
    consolidation_pct = ((df['Max_15_D'].iloc[-1] - df['Min_15_D'].iloc[-1]) / df['Min_15_D'].iloc[-1]) * 100

    # --- Weekly Calculations (Resampling) ---
    weekly_df = df.resample('W-FRI').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna()
    
    if len(weekly_df) < 10:
        return None
        
    weekly_df['EMA20_W'] = weekly_df['Close'].ewm(span=20, adjust=False).mean()
    weekly_df['RSI_W'] = calculate_rsi(weekly_df['Close'])

    # --- Current Values ---
    latest_D = df.iloc[-1]
    latest_W = weekly_df.iloc[-1]
    
    # ================= ALGORITHMIC SCORING (0 to 5) =================
    score = 0
    reasons = []
    
    # 1. Weekly Trend (പ്രധാന ട്രെൻഡ് മുകളിലേക്കാണോ?)
    if latest_W['Close'] > latest_W['EMA20_W'] and latest_W['RSI_W'] > 50:
        score += 1.5
        reasons.append("Strong Weekly Uptrend")
        
    # 2. Daily Momentum & Breakout
    if latest_D['RSI_D'] > 55 and latest_D['RSI_D'] < 75:
        score += 1.0
        reasons.append("Daily RSI Bullish")
        
    # 3. Institutional Volume Spurt
    if latest_D['RVOL_D'] > 1.5:
        score += 1.0
        reasons.append(f"High Volume Spurt ({latest_D['RVOL_D']:.1f}x)")
        
    # 4. Crab Zone Breakout Rebound
    if consolidation_pct < 6.0 and latest_D['Close'] > latest_D['EMA20_D']:
        score += 1.5
        reasons.append("Crab Zone Rebound")

    return {
        'LTP': latest_D['Close'],
        'RSI_D': latest_D['RSI_D'],
        'RSI_W': latest_W['RSI_W'],
        'RVOL': latest_D['RVOL_D'],
        'Consolidation': consolidation_pct,
        'Score': score,
        'Reasons': ", ".join(reasons)
    }

def chunked_market_scan(tickers, market_type="indian"):
    """API ഡ്രോപ്പ് ഒഴിവാക്കാൻ ചെറിയ ബാച്ചുകളായി ഡാറ്റ എടുക്കുന്നു"""
    chunk_size = 50
    scored_stocks = []
    currency = "₹" if market_type == "indian" else "$"
    
    print(f"📊 {len(tickers)} സ്റ്റോക്കുകളിൽ MTF പ്രീ-ഫിൽറ്ററിംഗ് നടത്തുന്നു...")
    
    for i in range(0, len(tickers), chunk_size):
        batch = tickers[i:i + chunk_size]
        # 6 മാസത്തെ ഡാറ്റ എടുക്കുന്നു (Weekly കാൽക്കുലേഷന് വേണ്ടി)
        data = yf.download(batch, period="6mo", interval="1d", group_by="ticker", progress=False)
        
        for ticker in batch:
            try:
                df = data.copy() if len(batch) == 1 else data[ticker].copy()
                df.dropna(inplace=True)
                
                result = evaluate_stock_momentum(df)
                if not result or result['Score'] < 2.5: # കുറഞ്ഞത് 2.5 സ്കോർ ഉള്ളവ മാത്രം
                    continue
                
                ltp = float(result['LTP'])
                entry_low = round(ltp * 0.995, 2)
                entry_high = round(ltp * 1.005, 2)
                target = round(ltp * 1.04, 2)
                stop_loss = round(ltp * 0.98, 2)
                
                clean_name = ticker.replace('.NS', '')
                scored_stocks.append({
                    'score': result['Score'],
                    'text': (
                        f"• {clean_name} ({ticker}): CMP {currency}{ltp:.2f} | "
                        f"Algorithmic Score: {result['Score']}/5 | Daily RSI: {result['RSI_D']:.1f} | Weekly RSI: {result['RSI_W']:.1f} | "
                        f"RVOL: {result['RVOL']:.1f}x | Triggers: {result['Reasons']} | "
                        f"[STRICT LEVELS -> Entry: {currency}{entry_low} - {currency}{entry_high}, Target: {currency}{target}, SL: {currency}{stop_loss}]"
                    )
                })
            except Exception:
                continue
        time.sleep(1) # API റിലാക്സേഷൻ
        
    # സ്കോർ അടിസ്ഥാനത്തിൽ സോർട്ട് ചെയ്ത് ഏറ്റവും മികച്ച 40 എണ്ണം മാത്രം തിരികെ നൽകുന്നു
    scored_stocks.sort(key=lambda x: x['score'], reverse=True)
    return [stock['text'] for stock in scored_stocks[:40]]

# ==================== 6. INDIAN MARKET EXECUTION ====================
def fetch_indian_market():
    indian_tickers = get_indian_universe()
    swing_candidates = chunked_market_scan(indian_tickers, "indian")
    
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
    നിങ്ങൾ ഒരു ക്വാണ്ട് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന ഇന്ത്യൻ മാർക്കറ്റ് ഡാറ്റ (പൈത്തൺ Algorithmic Score സഹിതം) അനലൈസ് ചെയ്യുക. ഈ സ്റ്റോക്കുകൾ Weekly & Daily ചാർട്ടുകൾ പരിശോധിച്ച് പ്രീ-ഫിൽറ്റർ ചെയ്തവയാണ്.
    
    🚨 കർശനമായ നിർദ്ദേശങ്ങൾ:
    1. NO PRICE HALLUCINATION: ബ്രാക്കറ്റിൽ നൽകിയിരിക്കുന്ന [STRICT LEVELS -> Entry, Target, SL] മാറ്റമില്ലാതെ ഉപയോഗിക്കുക.
    2. Algorithmic Score (ഉദാ: 4.5/5), Daily & Weekly RSI ഡാറ്റ എന്നിവ അടിസ്ഥാനമാക്കി ഓരോ സ്റ്റോക്കിനും AI Conviction Rate (%), Upside Probability (%) എന്നിവ നിശ്ചയിക്കുക.
    3. കൃത്യം 25 സ്റ്റോക്കുകൾ 4 വിഭാഗങ്ങളിലായി നൽകുക:
       - 🏆 ടോപ്പ് 10 സ്വിംഗ് പിക്കുകൾ.
       - 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ.
       - 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ.
       - 🦀 5 ക്രാബ് സോൺ റീബൗണ്ട് സ്റ്റോക്കുകൾ.
    4. റീഡബിലിറ്റി: കാർഡുകൾ ഡാർക്ക് ബാക്ക്ഗ്രൗണ്ട് ആണെങ്കിൽ അക്ഷരങ്ങൾ നിർബന്ധമായും പൂർണ്ണ വെള്ള നിറത്തിൽ നൽകുക.

    📊 സാങ്കേതിക ഡാറ്റ (MTF Filtered):
    {chr(10).join(swing_candidates)}

    💎 Moneycontrol Pro ഡാറ്റ:
    {chr(10).join(mc_news)}

    ഈ ഡാറ്റ വെച്ച് പ്രൊഫഷണൽ അനാലിസിസ് അടങ്ങിയ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """
    
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🇮🇳 Indian Market: MTF Pre-Filtered AI Radar", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 7. US MARKET EXECUTION ====================
def fetch_us_market():
    us_tickers = get_sp500_tickers()
    swing_candidates = chunked_market_scan(us_tickers, "us")
    
    prompt = f"""
    നിങ്ങൾ ഒരു ക്വാണ്ട് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന S&P 500 ഡാറ്റ (പൈത്തൺ Algorithmic Score സഹിതം) അനലൈസ് ചെയ്യുക. ഈ സ്റ്റോക്കുകൾ Weekly & Daily ചാർട്ടുകൾ പരിശോധിച്ച് പ്രീ-ഫിൽറ്റർ ചെയ്തവയാണ്.
    
    🚨 കർശനമായ നിർദ്ദേശങ്ങൾ:
    1. NO PRICE HALLUCINATION: ബ്രാക്കറ്റിൽ നൽകിയിരിക്കുന്ന [STRICT LEVELS -> Entry, Target, SL] മാറ്റമില്ലാതെ ഉപയോഗിക്കുക.
    2. Algorithmic Score, Daily & Weekly RSI എന്നിവ അടിസ്ഥാനമാക്കി ഓരോ സ്റ്റോക്കിനും AI Conviction Rate (%), Upside Probability (%) എന്നിവ നിശ്ചയിക്കുക.
    3. കൃത്യം 25 സ്റ്റോക്കുകൾ 4 വിഭാഗങ്ങളിലായി നൽകുക:
       - 🏆 ടോപ്പ് 10 സ്വിംഗ് പിക്കുകൾ.
       - 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ.
       - 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ.
       - 🦀 5 ക്രാബ് സോൺ റീബൗണ്ട് സ്റ്റോക്കുകൾ.
    4. റീഡബിലിറ്റി: കാർഡുകൾ ഡാർക്ക് ബാക്ക്ഗ്രൗണ്ട് ആണെങ്കിൽ അക്ഷരങ്ങൾ നിർബന്ധമായും പൂർണ്ണ വെള്ള നിറത്തിൽ നൽകുക.

    📊 യുഎസ് സാങ്കേതിക ഡാറ്റ (MTF Filtered):
    {chr(10).join(swing_candidates)}

    ഈ ഡാറ്റ വെച്ച് പ്രൊഫഷണൽ അനാലിസിസ് അടങ്ങിയ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """

    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    return "🇺🇸 US Market: S&P 500 MTF Pre-Filtered AI Radar", response.text.replace("```html", "").replace("```", "").strip()

# ==================== 8. ഇമെയിൽ അയക്കൽ ====================
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
    print(f"✅ {market_type.upper()} MTF അഡ്വാൻസ്ഡ് സ്കാൻ റിപ്പോർട്ട് വിജയകരമായി അയച്ചു!")
