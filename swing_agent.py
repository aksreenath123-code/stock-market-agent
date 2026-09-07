import sys
import subprocess
import os
import smtplib
import json
import time
import random
import requests
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

# പാക്കേജുകൾ ഓട്ടോമാറ്റായി ഇൻസ്റ്റാൾ ചെയ്യുന്നു
REQUIRED_PACKAGES = ["yfinance", "pandas", "google-genai", "pandas-ta", "requests", "cloudscraper"]
def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            pkg_name = "google.genai" if package == "google-genai" else ("pandas_ta" if package == "pandas-ta" else ("bs4" if package == "beautifulsoup4" else package))
            __import__(pkg_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
install_missing_packages()

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import cloudscraper
from google import genai

# API കോൺഫിഗറേഷൻ
IPO_GEMINI_API_KEY1 = os.getenv("IPO_GEMINI_API_KEY1") 
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

if not GEMINI_API_KEY:
    print("⚠️ പിഴവ്: API Key ലഭ്യമായില്ല.")
    sys.exit(1)

client = genai.Client(api_key=IPO_GEMINI_API_KEY1)
PREVIOUS_DATA_FILE = "previous_stocks.json"
CACHE_DATA_FILE = "cache_analysis.json"

def get_ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

# ================= 1. CACHE MANAGEMENT =================
def load_cache():
    if os.path.exists(CACHE_DATA_FILE):
        try:
            with open(CACHE_DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache_dict):
    with open(CACHE_DATA_FILE, "w") as f:
        json.dump(cache_dict, f)

# ================= 2. ROBUST NSE FETCH =================
def get_all_nse_tickers():
    print("🌐 NSE-യിൽ നിന്നും സ്റ്റോക്ക് ലിസ്റ്റ് എടുക്കുന്നു...")
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    attempt = 1
    while True:
        try:
            time.sleep(random.uniform(2, 5))
            response = scraper.get(url, timeout=30)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                tickers = [f"{symbol}.NS" for symbol in df['SYMBOL'].tolist()]
                print(f"✅ മൊത്തം {len(tickers)} സ്റ്റോക്കുകൾ വിജയകരമായി ശേഖരിച്ചു.")
                return tickers
        except Exception as e:
            print(f"⚠️ കണക്ഷൻ പ്രശ്നം (Attempt {attempt}): {e}. വീണ്ടും ശ്രമിക്കുന്നു...")
            
        time.sleep(min(attempt * 10, 60))
        attempt += 1

# ================= 3. DELTA TRACKING =================
def load_previous_stocks():
    if os.path.exists(PREVIOUS_DATA_FILE):
        try:
            with open(PREVIOUS_DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_current_stocks(stocks_list):
    with open(PREVIOUS_DATA_FILE, "w") as f:
        json.dump(stocks_list, f)

# ================= 4. PRE-FILTERING (MONTHLY & WEEKLY) =================
def get_filtered_stocks(tickers, batch_size=15):
    monthly_shortlisted = []
    weekly_shortlisted = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"📊 {len(tickers)} സ്റ്റോക്കുകൾ പ്രീ-ഫിൽറ്റർ ചെയ്യുന്നു (Monthly & Weekly)...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"🔄 ബാച്ച് {i//batch_size + 1}/{(len(tickers)//batch_size)+1} പ്രോസസ്സ് ചെയ്യുന്നു...")
        
        data = pd.DataFrame()
        while True:
            try:
                data = yf.download(batch, start=start_date, end=end_date, progress=False, group_by='ticker')
                if not data.empty:
                    break
            except Exception as e:
                print(f"⚠️ Yahoo Fetch Error: {e}. 15 സെക്കൻഡ് കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കുന്നു...")
                time.sleep(15)
        
        for ticker in batch:
            try:
                df = data[ticker] if len(batch) > 1 else data
                df = df.dropna()
                
                if len(df) >= 50:
                    latest_close = float(df['Close'].iloc[-1])
                    avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
                    
                    if latest_close > 30 and avg_volume > 50000: 
                        price_30_days_ago = float(df['Close'].iloc[-21]) 
                        price_7_days_ago = float(df['Close'].iloc[-6])   
                        
                        monthly_gain = ((latest_close - price_30_days_ago) / price_30_days_ago) * 100
                        weekly_gain = ((latest_close - price_7_days_ago) / price_7_days_ago) * 100
                        
                        df.ta.ema(length=20, append=True)
                        df.ta.ema(length=50, append=True)
                        df.ta.rsi(length=14, append=True)
                        df.ta.atr(length=14, append=True)
                        latest = df.iloc[-1]
                        
                        stock_meta = {
                            "stock": ticker, "price": latest_close, 
                            "monthly_gain": monthly_gain, "weekly_gain": weekly_gain,
                            "rsi": float(latest['RSI_14']), "ema20": float(latest['EMA_20']),
                            "ema50": float(latest['EMA_50']), "atr": float(latest['ATRr_14']),
                            "rvol": float(latest['Volume'] / avg_volume)
                        }
                        
                        if monthly_gain >= 15:
                            monthly_shortlisted.append(stock_meta)
                            
                        if weekly_gain >= 15:
                            weekly_shortlisted.append(stock_meta)
                            
            except Exception:
                pass
                
        time.sleep(random.uniform(5, 10)) 
        
    monthly_shortlisted = sorted(monthly_shortlisted, key=lambda x: x['monthly_gain'], reverse=True)
    weekly_shortlisted = sorted(weekly_shortlisted, key=lambda x: x['weekly_gain'], reverse=True)
    
    current_weekday = get_ist_now().weekday() # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    manual_mode = os.getenv("RUN_MODE", "auto")
    
    if manual_mode == "full":
        run_monthly, is_full_monthly, run_weekly, is_full_weekly = True, True, True, True
    elif manual_mode == "top_80":
        run_monthly, is_full_monthly, run_weekly, is_full_weekly = True, False, True, False
    else:
        run_monthly = (current_weekday == 5)
        is_full_monthly = (current_weekday == 5)
        run_weekly = current_weekday in [5, 6, 2, 4]
        is_full_weekly = (current_weekday == 6)
    
    selected_monthly = monthly_shortlisted if run_monthly else []
    if run_weekly:
        selected_weekly = weekly_shortlisted if is_full_weekly else weekly_shortlisted[:50]
    else:
        selected_weekly = []
        
    return selected_monthly, selected_weekly, is_full_monthly, is_full_weekly, run_monthly, run_weekly

# ================= 5. TOKEN-OPTIMIZED AI WITH CACHING =================
def run_ai_analysis(ticker, data, timeframe_type, cache_dict):
    gain_val = data['monthly_gain'] if timeframe_type == 'Monthly' else data['weekly_gain']
    cache_key = f"{ticker}_{timeframe_type}_{int(data['price'])}_{int(gain_val)}"
    
    # ക്യാഷിൽ ഉണ്ടെങ്കിൽ എഐ കോൾ ഒഴിവാക്കി ടോക്കൺ പൂർണ്ണമായും ലാഭിക്കാം
    if cache_key in cache_dict:
        print(f"   ⚡ Cache Hit: {ticker} ({timeframe_type})")
        return cache_dict[cache_key]

    # അതിസൂക്ഷ്മമായ ടോക്കൺ ഒപ്റ്റിമൈസ്ഡ് പ്രോംപ്റ്റ്
    prompt = f"Stk:{ticker},TF:{timeframe_type},P:{data['price']:.1f},G:{gain_val:.1f}%,RSI:{data['rsi']:.1f},E20:{data['ema20']:.1f},E50:{data['ema50']:.1f},RV:{data['rvol']:.1f},ATR:{data['atr']:.1f}. Reply ONLY valid JSON: {{\"T\":\"trend<5 words\",\"E\":\"entry\",\"S\":\"SL\",\"Tar\":\"target\",\"C\":\"High/Med/Low\",\"P\":\"prob%\"}}"
    
    attempt = 1
    while True:
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            res_json = json.loads(raw_text)
            
            result = {
                "trend": res_json.get("T", "Uptrend momentum"),
                "entry": res_json.get("E", f"₹{data['price']:.1f}"),
                "stop_loss": res_json.get("S", f"₹{data['price'] - data['atr']:.1f}"),
                "target": res_json.get("Tar", f"₹{data['price'] + (data['atr']*2):.1f}"),
                "conviction": res_json.get("C", "Medium"),
                "probability_rate": res_json.get("P", "70%")
            }
            
            # പുതിയ റിസൾട്ട് ക്യാഷിൽ സേവ് ചെയ്യുന്നു
            cache_dict[cache_key] = result
            return result
        except Exception as e:
            print(f"⚠️ AI Error for {ticker} (Attempt {attempt}): {e}. വീണ്ടും ശ്രമിക്കുന്നു...")
            time.sleep(15 * attempt)
            attempt += 1
            if attempt > 4:
                return {
                    "trend": "Momentum Breakout",
                    "entry": f"₹{data['price']:.1f}",
                    "stop_loss": f"₹{data['price'] - data['atr']:.1f}",
                    "target": f"₹{data['price'] + (data['atr']*2):.1f}",
                    "conviction": "Medium",
                    "probability_rate": "65%"
                }

# ================= 6. EMAIL SYSTEM (UNCHANGED COLOR CODING) =================
def send_email(monthly_reports, weekly_reports, dropped_stocks, run_monthly, run_weekly, is_full_weekly):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    
    day_name = get_ist_now().strftime('%A')
    msg["Subject"] = f"🚀 NSE Swing Alert ({day_name} Report)"
    
    def build_rows(reports):
        r_html = ""
        for item in reports:
            status_icon = "🆕 New" if item['status'] == "NEW" else "🟢 Retained"
            conv_color = "green" if item['conviction'].lower() == "high" else ("orange" if item['conviction'].lower() == "medium" else "red")
            r_html += f"<tr><td><b>{item['stock']}</b><br><span style='color: blue;'>{item['price']}</span></td><td><b>{status_icon}</b></td><td><span style='color: green; font-weight: bold;'>{item['gain']}</span><br><span style='font-size: 12px; color: gray;'>{item['technicals']}</span></td><td style='font-size: 13px;'>{item['trend']}</td><td style='font-size: 13px; font-weight: bold;'>{item['entry_sl_target']}</td><td style='text-align: center;'><span style='color: {conv_color}; font-weight: bold;'>{item['conviction']}</span><br>{item['probability']}</td></tr>"
        return r_html

    monthly_table = ""
    if run_monthly:
        monthly_rows = build_rows(monthly_reports)
        monthly_table = f"<h3>📈 Monthly Full Market Gainers</h3><table><tr><th>Stock & Price</th><th>Status</th><th>Monthly Gain & Tech</th><th>AI Trend</th><th>Trade Plan</th><th>Conviction</th></tr>{monthly_rows}</table>" if monthly_reports else "<h3>📈 Monthly Gainers</h3><p>No stocks found.</p>"

    weekly_table = ""
    if run_weekly:
        weekly_rows = build_rows(weekly_reports)
        w_title = "⚡ Weekly All Gainers (All Stocks)" if is_full_weekly else "⚡ Weekly 15%+ Gainers (Top 50)"
        weekly_table = f"<h3 style='margin-top: 30px;'>{w_title}</h3><table><tr><th>Stock & Price</th><th>Status</th><th>Weekly Gain & Tech</th><th>AI Trend</th><th>Trade Plan</th><th>Conviction</th></tr>{weekly_rows}</table>" if weekly_reports else f"<h3 style='margin-top: 30px;'>{w_title}</h3><p>No weekly stocks found.</p>"

    dropped_rows = ""
    for stock in dropped_stocks:
        dropped_rows += f"<tr><td style='color: red;'><b>{stock}</b></td><td>🔴 Dropped from List</td></tr>"
    dropped_table = f"<h3 style='margin-top: 30px; border-bottom: 2px solid red;'>" \
                    f"🔻 Dropped Stocks</h3><table><tr><th>Stock</th><th>Reason</th></tr>{dropped_rows}</table>" if dropped_stocks else ""

    html_content = f"""
    <html><head><style>
      body {{ font-family: Arial, sans-serif; padding: 10px; color: #333; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 10px; }}
      th, td {{ border: 1px solid #e0e0e0; padding: 10px; text-align: left; vertical-align: top; }}
      th {{ background-color: #111827; color: white; }}
      h3 {{ color: #1f2937; border-bottom: 2px solid #3b82f6; padding-bottom: 5px; }}
    </style></head>
    <body>
    <h2>🚀 NSE Swing Screener ({day_name})</h2>
    {monthly_table}
    {weekly_table}
    {dropped_table}
    </body></html>
    """
    
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    print(f"🚀 ഒപ്റ്റിമൈസ്ഡ് സ്വിങ് ഏജന്റ് പ്രവർത്തിച്ചുതുടങ്ങി...")
    
    all_tickers = get_all_nse_tickers()
    previous_stocks = load_previous_stocks()
    cache_dict = load_cache()
    
    selected_monthly, selected_weekly, is_full_monthly, is_full_weekly, run_monthly, run_weekly = get_filtered_stocks(all_tickers, batch_size=15)
    
    monthly_dict = {item['stock']: item for item in selected_monthly}
    weekly_dict = {item['stock']: item for item in selected_weekly}
    
    current_stocks_list = list(set(list(monthly_dict.keys()) + list(weekly_dict.keys())))
    new_stocks = set(current_stocks_list) - set(previous_stocks)
    retained_stocks = set(current_stocks_list).intersection(set(previous_stocks))
    dropped_stocks = set(previous_stocks) - set(current_stocks_list)
    
    monthly_reports = []
    weekly_reports = []
    
    if run_monthly:
        print("\n🤖 Monthly സ്റ്റോക്കുകളുടെ AI അനാലിസിസ്...")
        for stock, data in monthly_dict.items():
            print(f"   • Monthly: {stock}")
            status = "NEW" if stock in new_stocks else "RETAINED"
            ai_rep = run_ai_analysis(stock, data, 'Monthly', cache_dict)
            monthly_reports.append({
                "stock": stock, "status": status, "price": f"₹{data['price']:.2f}",
                "gain": f"{data['monthly_gain']:.2f}% (M)", "technicals": f"RSI: {data['rsi']:.1f} | RVOL: {data['rvol']:.1f}x",
                "trend": ai_rep.get("trend", "N/A"),
                "entry_sl_target": f"Entry: {ai_rep.get('entry')} <br><span style='color:red;'>SL: {ai_rep.get('stop_loss')}</span> <br><span style='color:green;'>Tgt: {ai_rep.get('target')}</span>",
                "conviction": ai_rep.get("conviction", "N/A"), "probability": ai_rep.get("probability_rate", "N/A")
            })
            time.sleep(random.uniform(5, 10))
        
    if run_weekly:
        print("\n🤖 Weekly സ്റ്റോക്കുകളുടെ AI അനാലിസിസ്...")
        for stock, data in weekly_dict.items():
            print(f"   • Weekly: {stock}")
            w_status = "NEW" if stock not in previous_stocks else "RETAINED"
            ai_rep = run_ai_analysis(stock, data, 'Weekly', cache_dict)
            weekly_reports.append({
                "stock": stock, "status": w_status, "price": f"₹{data['price']:.2f}",
                "gain": f"{data['weekly_gain']:.2f}% (W)", "technicals": f"RSI: {data['rsi']:.1f} | RVOL: {data['rvol']:.1f}x",
                "trend": ai_rep.get("trend", "N/A"),
                "entry_sl_target": f"Entry: {ai_rep.get('entry')} <br><span style='color:red;'>SL: {ai_rep.get('stop_loss')}</span> <br><span style='color:green;'>Tgt: {ai_rep.get('target')}</span>",
                "conviction": ai_rep.get("conviction", "N/A"), "probability": ai_rep.get("probability_rate", "N/A")
            })
            time.sleep(random.uniform(5, 10))
            
    # ക്യാഷ് ഫയൽ അപ്ഡേറ്റ് ചെയ്ത് സേവ് ചെയ്യുന്നു
    save_cache(cache_dict)
    send_email(monthly_reports, weekly_reports, list(dropped_stocks), run_monthly, run_weekly, is_full_weekly)
    save_current_stocks(current_stocks_list)
    print("🎉 എല്ലാ പ്രക്രിയകളും വിജയകരമായി പൂർത്തിയായി!")
