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
            print(f"📦 ഇൻസ്റ്റാൾ ചെയ്യുന്നു: {package}...", flush=True)
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
IPO_GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MC_COOKIE = os.getenv("MONEYCONTROL_COOKIE", "")

client = genai.Client(api_key=IPO_GEMINI_API_KEY)

# ==================== ജെമിനി 3 സീരീസ് ഫാസ്റ്റ് റീട്രൈ എൻജിൻ ====================
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.1-pro"
]

def generate_report_with_infinite_retry(prompt, max_attempts=5):
    """
    അനന്തമായി ഹാങ് ആകാതെ, കൃത്യമായ ഇടവേളകളിൽ റീ-ട്രൈ ചെയ്ത് റിപ്പോർട്ട് തയ്യാറാക്കുന്നു.
    """
    for attempt in range(1, max_attempts + 1):
        for model_name in GEMINI_MODELS:
            print(f"🤖 ശ്രമിക്കുന്നു: {model_name} (Attempt #{attempt}/{max_attempts})...", flush=True)
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    print(f"✅ വിജയകരമായി റിപ്പോർട്ട് തയ്യാറാക്കി ({model_name})!", flush=True)
                    return response.text.replace("```html", "").replace("```", "").strip()
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ {model_name} താൽക്കാലികമായി പരാജയപ്പെട്ടു: {err_str[:120]}...", flush=True)
                time.sleep(3)

        wait_seconds = attempt * 15 # 15s, 30s, 45s എന്നിങ്ങനെ പ്രായോഗികമായ സമയം
        print(f"⏳ സെർവർ തിരക്കിലാണ്. അടുത്ത റീട്രൈ {wait_seconds} സെക്കൻഡിൽ നടക്കും...", flush=True)
        time.sleep(wait_seconds)

    raise RuntimeError("❌ നിശ്ചിത ശ്രമങ്ങൾക്കുള്ളിൽ മോഡൽ റെസ്പോൺസ് നൽകിയില്ല.")

# ==================== 4. യൂണിവേഴ്സ് സെലക്ഷൻ ====================
def get_us_universe():
    return [
        "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "AMD", 
        "NFLX", "PLTR", "AVGO", "SMCI", "COIN", "MARA", "QCOM", "ARM", 
        "UBER", "CRWD", "PYPL", "INTC", "DIS", "CRM", "MSTR", "MU", 
        "CSCO", "ADBE", "PEP", "COST", "TMUS", "TXN", "INTU", "AMAT", 
        "ISRG", "NOW", "BKNG", "VRTX", "REGN", "ADI", "PANW", "SNPS"
    ]

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

# ==================== 5. പെർഫെക്റ്റ് പ്രൈസ് & MTF സ്കാനിംഗ് എൻജിൻ ====================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def evaluate_stock_momentum(ticker):
    try:
        stock = yf.Ticker(ticker)
        # ടൈംഔട്ട് നൽകി ഹാങ് ആകുന്നത് തടയുന്നു
        df = stock.history(period="6mo", interval="1d", timeout=8)
        if df.empty or len(df) < 50:
            return None
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df['EMA20_D'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['RSI_D'] = calculate_rsi(df['Close'])
        df['RVOL_D'] = df['Volume'] / df['Volume'].rolling(10).mean()
        
        df['Max_15_D'] = df['High'].rolling(15).max()
        df['Min_15_D'] = df['Low'].rolling(15).min()
        consolidation_pct = ((df['Max_15_D'].iloc[-1] - df['Min_15_D'].iloc[-1]) / df['Min_15_D'].iloc[-1]) * 100

        weekly_df = df.resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(weekly_df) < 10:
            return None
            
        weekly_df['EMA20_W'] = weekly_df['Close'].ewm(span=20, adjust=False).mean()
        weekly_df['RSI_W'] = calculate_rsi(weekly_df['Close'])

        latest_D = df.iloc[-1]
        latest_W = weekly_df.iloc[-1]
        
        score = 0
        reasons = []
        
        if latest_W['Close'] > latest_W['EMA20_W'] and latest_W['RSI_W'] > 50:
            score += 1.5
            reasons.append("Strong Weekly Uptrend")
            
        if latest_D['RSI_D'] > 55 and latest_D['RSI_D'] < 75:
            score += 1.0
            reasons.append("Daily RSI Bullish")
            
        if latest_D['RVOL_D'] > 1.3:
            score += 1.0
            reasons.append(f"High Volume Spurt ({latest_D['RVOL_D']:.1f}x)")
            
        if consolidation_pct < 6.0 and latest_D['Close'] > latest_D['EMA20_D']:
            score += 1.5
            reasons.append("Crab Zone Rebound")

        return {
            'LTP': float(latest_D['Close']),
            'RSI_D': float(latest_D['RSI_D']),
            'RSI_W': float(latest_W['RSI_W']),
            'RVOL': float(latest_D['RVOL_D']),
            'Consolidation': float(consolidation_pct),
            'Score': score,
            'Reasons': ", ".join(reasons)
        }
    except Exception:
        return None

def robust_market_scan(tickers, market_type="indian"):
    scored_stocks = []
    currency = "₹" if market_type == "indian" else "$"
    
    print(f"📊 {len(tickers)} സ്റ്റോക്കുകൾ സ്കാൻ ചെയ്യുന്നു...", flush=True)
    
    for idx, ticker in enumerate(tickers, start=1):
        if idx % 10 == 0:
            print(f"⏳ പുരോഗതി: {idx}/{len(tickers)} സ്റ്റോക്കുകൾ പൂർത്തിയായി...", flush=True)
            
        result = evaluate_stock_momentum(ticker)
        if not result or result['Score'] < 1.5:
            continue
            
        ltp = result['LTP']
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
        time.sleep(0.1)
        
    scored_stocks.sort(key=lambda x: x['score'], reverse=True)
    print(f"✅ സ്കാനിംഗ് പൂർത്തിയായി. {len(scored_stocks)} അനുയോജ്യമായ സ്റ്റോക്കുകൾ കണ്ടെത്തി.", flush=True)
    return [stock['text'] for stock in scored_stocks[:30]]

# ==================== 6. INDIAN MARKET EXECUTION ====================
def fetch_indian_market():
    indian_tickers = get_indian_universe()
    swing_candidates = robust_market_scan(indian_tickers, "indian")
    
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": MC_COOKIE}
    mc_news = []
    try:
        res = requests.get("https://www.moneycontrol.com/news/mcpro-technical-analysis/", headers=headers, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for art in soup.select("li.clearfix, div.news_card")[:5]:
                t = art.find(["h2", "h3"])
                if t: mc_news.append(f"• MC Pro: {t.get_text(strip=True)}")
    except Exception:
        pass

    prompt = f"""
    നിങ്ങൾ ഒരു പ്രൊഫഷണൽ ക്വാണ്ട് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന ഇന്ത്യൻ മാർക്കറ്റ് ഡാറ്റ അനലൈസ് ചെയ്യുക.
    
    🚨 കർശനമായ നിർദ്ദേശങ്ങൾ:
    1. NO PRICE HALLUCINATION: [STRICT LEVELS -> Entry, Target, SL] ലെവലുകൾ ഒരുകാരണവശാലും മാറ്റരുത്.
    2. AI Conviction Rate (%), Upside Probability (%) എന്നിവ സ്റ്റോക്കിന്റെ സ്കോറും ഇൻഡിക്കേറ്ററുകളും വെച്ച് കണക്കാക്കുക.
    3. കൃത്യം 25 സ്റ്റോക്കുകൾ 4 വിഭാഗങ്ങളിലായി നൽകുക:
       - 🏆 ടോപ്പ് 10 സ്വിംഗ് ട്രേഡ് പിക്കുകൾ.
       - 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ.
       - 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ.
       - 🦀 5 ക്രാബ് സോൺ റീബൗണ്ട് സ്റ്റോക്കുകൾ.
    4. റീഡബിലിറ്റി: കാർഡുകൾ ഡാർക്ക് ബാക്ക്ഗ്രൗണ്ട് ആണെങ്കിൽ അക്ഷരങ്ങൾ നിർബന്ധമായും പൂർണ്ണ വെള്ള നിറത്തിൽ നൽകുക.

    📊 സാങ്കേതിക ഡാറ്റ:
    {chr(10).join(swing_candidates)}

    💎 Moneycontrol Pro ഡാറ്റ:
    {chr(10).join(mc_news)}

    ഈ ഡാറ്റ വെച്ച് പ്രൊഫഷണൽ അനാലിസിസ് അടങ്ങിയ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """
    
    report_html = generate_report_with_infinite_retry(prompt)
    return "🇮🇳 Indian Market: Accurate Price Swing Radar", report_html

# ==================== 7. US MARKET EXECUTION ====================
def fetch_us_market():
    us_tickers = get_us_universe()
    swing_candidates = robust_market_scan(us_tickers, "us")
    
    prompt = f"""
    നിങ്ങൾ ഒരു Wall Street സ്വിംഗ് ട്രേഡിംഗ് സ്പെഷ്യലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന യുഎസ് മാർക്കറ്റ് ഡാറ്റ അനലൈസ് ചെയ്യുക.
    
    🚨 കർശനമായ നിർദ്ദേശങ്ങൾ:
    1. NO PRICE HALLUCINATION: [STRICT LEVELS -> Entry, Target, SL] ലെവലുകൾ ഒരുകാരണവശാലും മാറ്റരുത്.
    2. AI Conviction Rate (%), Upside Probability (%) എന്നിവ സ്റ്റോക്കിന്റെ സ്കോറും ഇൻഡിക്കേറ്ററുകളും വെച്ച് കണക്കാക്കുക.
    3. കൃത്യം 25 സ്റ്റോക്കുകൾ 4 വിഭാഗങ്ങളിലായി നൽകുക:
       - 🏆 ടോപ്പ് 10 സ്വിംഗ് ട്രേഡ് പിക്കുകൾ.
       - 🚀 5 ഹൈ മൊമെന്റം സ്റ്റോക്കുകൾ.
       - 💥 5 ഹൈ വോളിയം ബ്രേക്ക്ഔട്ട് സ്റ്റോക്കുകൾ.
       - 🦀 5 ക്രാബ് സോൺ റീബൗണ്ട് സ്റ്റോക്കുകൾ.
    4. റീഡബിലിറ്റി: കാർഡുകൾ ഡാർക്ക് ബാക്ക്ഗ്രൗണ്ട് ആണെങ്കിൽ അക്ഷരങ്ങൾ നിർബന്ധമായും പൂർണ്ണ വെള്ള നിറത്തിൽ നൽകുക.

    📊 യുഎസ് സാങ്കേതിക ഡാറ്റ:
    {chr(10).join(swing_candidates)}

    ഈ ഡാറ്റ വെച്ച് പ്രൊഫഷണൽ അനാലിസിസ് അടങ്ങിയ ഇമെയിൽ ബോഡി മലയാളത്തിൽ തയ്യാറാക്കുക (```html ... ``` ഫോർമാറ്റിൽ മാത്രം).
    """

    report_html = generate_report_with_infinite_retry(prompt)
    return "🇺🇸 US Market: Accurate Price Swing Radar", report_html

# ==================== 8. ഇമെയിൽ അയക്കൽ ====================
def send_email(subject, html_content):
    print("📧 ഇമെയിൽ അയക്കാൻ തുടങ്ങുന്നു...", flush=True)
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)
    print("📬 ഇമെയിൽ വിജയകരമായി അയച്ചു കഴിഞ്ഞു!", flush=True)

if __name__ == "__main__":
    market_type = sys.argv[1] if len(sys.argv) > 1 else "indian"
    
    if market_type == "us":
        subject, content = fetch_us_market()
    else:
        subject, content = fetch_indian_market()

    send_email(subject, content)
    print(f"🎉 {market_type.upper()} റിപ്പോർട്ട് പൂർണ്ണമായും വിജയകരമായി അയച്ചു!", flush=True)
