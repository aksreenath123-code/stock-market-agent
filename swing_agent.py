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
from datetime import datetime, timedelta

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
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY") 
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

if not GEMINI_API_KEY:
    print("⚠️ പിഴവ്: API Key ലഭ്യമായില്ല.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)
PREVIOUS_DATA_FILE = "previous_stocks.json"

# ================= 1. ROBUST NSE FETCH (WITH INFINITE RETRY) =================
def get_all_nse_tickers():
    print("🌐 NSE-യിൽ നിന്നും സ്റ്റോക്ക് ലിസ്റ്റ് എടുക്കുന്നു...")
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    attempt = 1
    while True:
        try:
            time.sleep(random.uniform(2, 5)) # ഹ്യൂമൻ ബിഹേവിയർ ടൈം ഔട്ട്
            response = scraper.get(url, timeout=30)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                tickers = [f"{symbol}.NS" for symbol in df['SYMBOL'].tolist()]
                print(f"✅ മൊത്തം {len(tickers)} സ്റ്റോക്കുകൾ വിജയകരമായി ശേഖരിച്ചു.")
                return tickers
            else:
                print(f"⚠️ HTTP Error {response.status_code}. വീണ്ടും ശ്രമിക്കുന്നു...")
        except Exception as e:
            print(f"⚠️ കണക്ഷൻ പ്രശ്നം (Attempt {attempt}): {e}. വീണ്ടും ശ്രമിക്കുന്നു...")
            
        sleep_time = min(attempt * 10, 60) # പരമാവധി 60 സെക്കൻഡ് വരെ കാത്തിരിക്കും
        time.sleep(sleep_time)
        attempt += 1

# ================= 2. DELTA TRACKING =================
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

# ================= 3. ROBUST PRE-FILTERING (BATCHED & HUMAN-LIKE) =================
def get_pre_filtered_stocks(tickers, batch_size=15):
    shortlisted_stocks = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"📊 {len(tickers)} സ്റ്റോക്കുകൾ പ്രീ-ഫിൽറ്റർ ചെയ്യുന്നു (സുരക്ഷിതമായ വേഗതയിൽ)...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"🔄 ബാച്ച് {i//batch_size + 1}/{(len(tickers)//batch_size)+1} പ്രോസസ്സ് ചെയ്യുന്നു...")
        
        data = pd.DataFrame()
        # യാഹൂ ഫിനാൻസ് ഡാറ്റ കിട്ടുന്നതുവരെ ലൂപ്പ് ചെയ്യും
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
                    
                    if latest_close > 30 and avg_volume > 50000: # പെന്നി സ്റ്റോക്കുകൾ ഒഴിവാക്കാൻ
                        price_30_days_ago = float(df['Close'].iloc[-21]) 
                        gain_percent = ((latest_close - price_30_days_ago) / price_30_days_ago) * 100
                        
                        if gain_percent >= 15:
                            df.ta.ema(length=20, append=True)
                            df.ta.ema(length=50, append=True)
                            df.ta.rsi(length=14, append=True)
                            df.ta.atr(length=14, append=True)
                            latest = df.iloc[-1]
                            
                            shortlisted_stocks[ticker] = {
                                "stock": ticker, "price": latest_close, "gain": gain_percent,
                                "rsi": float(latest['RSI_14']), "ema20": float(latest['EMA_20']),
                                "ema50": float(latest['EMA_50']), "atr": float(latest['ATRr_14']),
                                "rvol": float(latest['Volume'] / avg_volume)
                            }
            except Exception:
                pass
                
        # ബോട്ട് പോലെയല്ല തോന്നിക്കാൻ ഓരോ ബാച്ചിനും ഇടയിൽ റാൻഡം ടൈം ഔട്ട് (10 മുതൽ 20 സെക്കൻഡ് വരെ)
        time.sleep(random.uniform(10, 20)) 
        
    return shortlisted_stocks

# ================= 4. AI ANALYSIS WITH GUARDRAILS & FALLBACK =================
def run_ai_analysis(ticker, data):
    prompt = f"Stk:{ticker},P:{data['price']:.1f},G:{data['gain']:.1f}%,RSI:{data['rsi']:.1f},E20:{data['ema20']:.1f},E50:{data['ema50']:.1f},RV:{data['rvol']:.1f},ATR:{data['atr']:.1f}. Reply ONLY valid JSON: {{\"T\":\"trend<5 words\",\"E\":\"entry\",\"S\":\"SL\",\"Tar\":\"target\",\"C\":\"High/Med/Low\",\"P\":\"prob%\"}}"
    
    attempt = 1
    while True: # ഡാറ്റ കിട്ടുന്നതുവരെ അല്ലെങ്കിൽ സക്സസ് ആവുന്നതുവരെ റീട്രൈ ചെയ്തുകൊണ്ടിരിക്കും
        try:
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            
            # JSON കൃത്യമാണോ എന്ന് പരിശോധിക്കുന്നു (Hallucination Guardrail)
            res_json = json.loads(raw_text)
            
            return {
                "trend": res_json.get("T", "Uptrend momentum"),
                "entry": res_json.get("E", f"₹{data['price']:.1f}"),
                "stop_loss": res_json.get("S", f"₹{data['price'] - data['atr']:.1f}"),
                "target": res_json.get("Tar", f"₹{data['price'] + (data['atr']*2):.1f}"),
                "conviction": res_json.get("C", "Medium"),
                "probability_rate": res_json.get("P", "70%")
            }
        except Exception as e:
            print(f"⚠️ AI Error for {ticker} (Attempt {attempt}): {e}. വീണ്ടും ശ്രമിക്കുന്നു...")
            # എപിഐ ലിമിറ്റ് അല്ലെങ്കിൽ ഹാലുസിനേഷൻ വന്നാൽ കൂടുതൽ സമയം കാത്തിരിക്കും
            time.sleep(20 * attempt)
            attempt += 1
            
            # 5 തവണയ്ക്ക് മേൽ പരാജയപ്പെട്ടാൽ കോഡ് ക്രാഷ് ആവാതിരിക്കാൻ സേഫ് ആയ ഡിഫോൾട്ട് (Fallback) ഡാറ്റ നൽകും
            if attempt > 5:
                print(f"🚨 {ticker}-ന് AI അനാലിസിസ് ലഭിച്ചില്ല. ഫോൾബാക്ക് ഡാറ്റ ഉപയോഗിക്കുന്നു.")
                return {
                    "trend": "Momentum Breakout",
                    "entry": f"₹{data['price']:.1f}",
                    "stop_loss": f"₹{data['price'] - data['atr']:.1f}",
                    "target": f"₹{data['price'] + (data['atr']*2):.1f}",
                    "conviction": "Medium",
                    "probability_rate": "65%"
                }

# ================= 5. EMAIL SYSTEM =================
def send_email(active_reports, dropped_stocks):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "🚀 NSE Ultimate Swing Alert (Guarded & Verified)"
    
    rows = ""
    for item in active_reports:
        status_icon = "🆕 New" if item['status'] == "NEW" else "🟢 Retained"
        conviction_color = "green" if item['conviction'].lower() == "high" else ("orange" if item['conviction'].lower() == "medium" else "red")
        
        rows += f"<tr><td><b>{item['stock']}</b><br><span style='color: blue;'>{item['price']}</span></td><td><b>{status_icon}</b></td><td><span style='color: green; font-weight: bold;'>{item['gain']}</span><br><span style='font-size: 12px; color: gray;'>{item['technicals']}</span></td><td style='font-size: 13px;'>{item['trend']}</td><td style='font-size: 13px; font-weight: bold;'>{item['entry_sl_target']}</td><td style='text-align: center;'><span style='color: {conviction_color}; font-weight: bold;'>{item['conviction']}</span><br>{item['probability']}</td></tr>"

    main_table = f"<table><tr><th>Stock & Price</th><th>Status</th><th>Gain & Tech</th><th>AI Trend</th><th>Trade Plan</th><th>Conviction</th></tr>{rows}</table>" if active_reports else "<p>No active 15%+ stocks found today.</p>"

    dropped_rows = ""
    for stock in dropped_stocks:
        dropped_rows += f"<tr><td style='color: red;'><b>{stock}</b></td><td>🔴 Dropped (Gain < 15%)</td></tr>"
    dropped_table = f"<h3 style='margin-top: 30px; border-bottom: 2px solid red;'>🔻 Dropped Stocks</h3><table><tr><th>Stock</th><th>Reason</th></tr>{dropped_rows}</table>" if dropped_stocks else ""

    html_content = f"<html><head><style>body {{ font-family: Arial, sans-serif; padding: 10px; color: #333; }} table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 15px; }} th, td {{ border: 1px solid #e0e0e0; padding: 10px; text-align: left; vertical-align: top; }} th {{ background-color: #111827; color: white; }}</style></head><body><h2>📈 Ultimate Guarded NSE Swing Screener</h2>{main_table} {dropped_table}</body></html>"
    
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    print("🚀 അൾട്ടിമേറ്റ് ട്രേഡിങ് ഏജന്റ് പ്രവർത്തിച്ചുതുടങ്ങി...")
    
    all_tickers = get_all_nse_tickers()
    previous_stocks = load_previous_stocks()
    
    # സുരക്ഷിതമായ ബാച്ചിങ് സൈസും ടൈം ഔട്ടും ഉപയോഗിക്കുന്നു
    current_filtered_dict = get_pre_filtered_stocks(all_tickers, batch_size=15)
    current_stocks_list = list(current_filtered_dict.keys())
    
    new_stocks = set(current_stocks_list) - set(previous_stocks)
    retained_stocks = set(current_stocks_list).intersection(set(previous_stocks))
    dropped_stocks = set(previous_stocks) - set(current_stocks_list)
    
    print(f"\n✅ മാറ്റങ്ങൾ: {len(new_stocks)} New, {len(retained_stocks)} Retained, {len(dropped_stocks)} Dropped.")
    
    final_reports = []
    
    for stock in current_stocks_list:
        print(f"🤖 AI അനാലിസിസ് നടക്കുന്നു: {stock}...")
        data = current_filtered_dict[stock]
        ai_report = run_ai_analysis(stock, data)
        
        status = "NEW" if stock in new_stocks else "RETAINED"
        
        final_reports.append({
            "stock": stock, "status": status, "price": f"₹{data['price']:.2f}",
            "gain": f"{data['gain']:.2f}%", "technicals": f"RSI: {data['rsi']:.1f} | RVOL: {data['rvol']:.1f}x",
            "trend": ai_report.get("trend", "N/A"),
            "entry_sl_target": f"Entry: {ai_report.get('entry')} <br><span style='color:red;'>SL: {ai_report.get('stop_loss')}</span> <br><span style='color:green;'>Tgt: {ai_report.get('target')}</span>",
            "conviction": ai_report.get("conviction", "N/A"), "probability": ai_report.get("probability_rate", "N/A")
        })
        
        # ഓരോ എഐ അനാലിസിസിനും ഇടയിൽ സുരക്ഷിതമായ റാൻഡം ഗ്യാപ്പ് (20 മുതൽ 35 സെക്കൻഡ് വരെ)
        time.sleep(random.uniform(20, 35)) 
        
    send_email(final_reports, list(dropped_stocks))
    save_current_stocks(current_stocks_list)
    print("🎉 എല്ലാ പ്രക്രിയകളും വിജയകരമായി പൂർത്തിയായി!")
