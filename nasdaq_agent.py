import sys
import subprocess
import os
import smtplib
import json
import time
import random
import ftplib
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

# പാക്കേജുകൾ ഇൻസ്റ്റാൾ ചെയ്യുന്നു
REQUIRED_PACKAGES = ["yfinance", "pandas", "google-genai", "pandas-ta"]
def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            pkg_name = "google.genai" if package == "google-genai" else ("pandas_ta" if package == "pandas-ta" else package)
            __import__(pkg_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
install_missing_packages()

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# API കോൺഫിഗറേഷൻ
IPO_GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY") 
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

if not IPO_GEMINI_API_KEY:
    print("⚠️ പിഴവ്: IPO_GEMINI_API_KEY ലഭ്യമായില്ല.")
    sys.exit(1)

client = genai.Client(api_key=IPO_GEMINI_API_KEY)

def get_ist_now():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

# ================= 1. NASDAQ FETCH =================
def get_all_nasdaq_tickers():
    print("🌐 Nasdaq FTP-യിൽ നിന്നും സ്റ്റോക്ക് ലിസ്റ്റ് എടുക്കുന്നു...")
    try:
        ftp = ftplib.FTP('ftp.nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        lines = []
        ftp.retrlines('RETR nasdaqtraded.txt', lines.append)
        ftp.quit()
        
        tickers = []
        for line in lines[1:-1]:
            parts = line.split('|')
            if len(parts) > 2 and parts[3] == 'Q' and parts[5] == 'N':
                tickers.append(parts[1])
        print(f"✅ മൊത്തം {len(tickers)} നാസ്ഡാക് സ്റ്റോക്കുകൾ ശേഖരിച്ചു.")
        return tickers
    except Exception as e:
        print(f"⚠️ FTP കണക്ഷൻ പ്രശ്നം: {e}. ഡിഫോൾട്ട് ലിസ്റ്റ് ഉപയോഗിക്കുന്നു.")
        return ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

# ================= 2. MARKET INDEX GUARDRAIL (QQQ Trend) =================
def get_market_trend():
    print("📈 നാസ്ഡാക് മാർക്കറ്റ് (QQQ) ട്രെൻഡ് പരിശോധിക്കുന്നു...")
    try:
        qqq = yf.download("QQQ", period="10d", progress=False)
        qqq_close = float(qqq['Close'].iloc[-1])
        qqq_prev = float(qqq['Close'].iloc[-4]) # 3 days ago
        qqq_chg = ((qqq_close - qqq_prev) / qqq_prev) * 100
        trend = "Bullish" if qqq_chg > 0 else "Bearish"
        print(f"✅ Market Trend: {trend} ({qqq_chg:.2f}% in last 3 days)")
        return trend, qqq_chg
    except Exception as e:
        print("⚠️ QQQ ഫെച്ച് ചെയ്യുന്നതിൽ പിഴവ്.")
        return "Neutral", 0.0

# ================= 3. WEEKLY PRE-FILTERING (15% GAIN + 9/21 EMA + RVOL + GAP) =================
def get_filtered_stocks(tickers, batch_size=20):
    weekly_shortlisted = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=40)
    
    print(f"📊 {len(tickers)} സ്റ്റോക്കുകൾ പ്രീ-ഫിൽറ്റർ ചെയ്യുന്നു...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"🔄 ബാച്ച് {i//batch_size + 1}/{(len(tickers)//batch_size)+1} പ്രോസസ്സ് ചെയ്യുന്നു...")
        
        data = pd.DataFrame()
        attempt = 1
        while attempt <= 3:
            try:
                data = yf.download(batch, start=start_date, end=end_date, progress=False, group_by='ticker')
                if not data.empty: break
            except Exception:
                time.sleep(10)
                attempt += 1
        
        for ticker in batch:
            try:
                df = data[ticker] if len(batch) > 1 else data
                df = df.dropna()
                
                if len(df) >= 20:
                    latest_close = float(df['Close'].iloc[-1])
                    avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
                    
                    if latest_close > 5 and avg_volume > 200000: 
                        price_7_days_ago = float(df['Close'].iloc[-6])   
                        weekly_gain = ((latest_close - price_7_days_ago) / price_7_days_ago) * 100
                        
                        if weekly_gain >= 15:
                            # Last 3 days momentum
                            last_3 = df['Close'].iloc[-3:].values
                            day1_chg = ((last_3[1] - last_3[0]) / last_3[0]) * 100
                            day2_chg = ((last_3[2] - last_3[1]) / last_3[1]) * 100
                            
                            # Gap Up Calculation (Today Open vs Yday Close)
                            today_open = float(df['Open'].iloc[-1])
                            yday_close = float(df['Close'].iloc[-2])
                            gap_up = ((today_open - yday_close) / yday_close) * 100
                            
                            # RVOL (Relative Volume)
                            rvol = float(df['Volume'].iloc[-1]) / avg_volume
                            
                            # 9 & 21 EMA for Short Term
                            df.ta.ema(length=9, append=True)
                            df.ta.ema(length=21, append=True)
                            
                            latest = df.iloc[-1]
                            
                            weekly_shortlisted.append({
                                "stock": ticker, "price": latest_close, 
                                "weekly_gain": weekly_gain,
                                "day1_chg": day1_chg, "day2_chg": day2_chg,
                                "gap_up": gap_up, "rvol": rvol,
                                "ema9": float(latest['EMA_9']), "ema21": float(latest['EMA_21'])
                            })
            except Exception:
                pass
                
        time.sleep(random.uniform(2, 5)) 
        
    weekly_shortlisted = sorted(weekly_shortlisted, key=lambda x: x['weekly_gain'], reverse=True)[:80]
    return weekly_shortlisted

# ================= 4. NEWS FETCHING =================
def get_latest_news(ticker):
    try:
        tk = yf.Ticker(ticker)
        news = tk.news
        if news:
            # ഏറ്റവും പുതിയ 2 വാർത്തകളുടെ ഹെഡ്‌ലൈനുകൾ
            return " | ".join([n['title'] for n in news[:2]])
    except:
        return "No recent news."
    return "No recent news."

# ================= 5. AI ANALYSIS WITH GUARDRAILS & CATALYSTS =================
def run_ai_analysis(ticker, data, market_trend, market_chg):
    news_headlines = get_latest_news(ticker)
    
    prompt = (
        f"Role: You are an expert short-term swing trader (1-3 days hold).\n"
        f"Market Context (QQQ): {market_trend} ({market_chg:.2f}% last 3 days).\n"
        f"Stock: {ticker}, Price: ${data['price']:.2f}, W_Gain: {data['weekly_gain']:.1f}%\n"
        f"Momentum (Last 2 Days): [{data['day1_chg']:.1f}%, {data['day2_chg']:.1f}%]\n"
        f"Gap-Up Today: {data['gap_up']:.1f}%, RVOL: {data['rvol']:.1f}x\n"
        f"Technicals: 9-EMA=${data['ema9']:.2f}, 21-EMA=${data['ema21']:.2f}\n"
        f"News Catalyst: {news_headlines}\n\n"
        "GUARDRAILS:\n"
        "1. If Market is 'Bearish', lower the Conviction unless RVOL is massive (>3.0) or News is highly bullish.\n"
        "2. If Momentum (Last 2 Days) is fading/negative, Conviction MUST be 'Low'.\n"
        "3. High Gap-Up and RVOL > 2.0 with positive news increases Conviction.\n"
        "Reply ONLY in valid JSON: {\"T\":\"trend <5 words\",\"E\":\"entry\",\"S\":\"SL\",\"Tar\":\"target\",\"C\":\"High/Med/Low\",\"P\":\"prob%\"}"
    )
    
    attempt = 1
    while True:
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            res_json = json.loads(raw_text)
            
            return {
                "trend": res_json.get("T", "Momentum Play"),
                "entry": res_json.get("E", f"${data['price']:.2f}"),
                "stop_loss": res_json.get("S", f"${data['ema9']:.2f}"), # SL typically around 9-EMA
                "target": res_json.get("Tar", f"${data['price'] * 1.05:.2f}"), # ~5% target
                "conviction": res_json.get("C", "Low"),
                "probability": res_json.get("P", "50%"),
                "news_snippet": news_headlines[:50] + "..." if len(news_headlines) > 50 else news_headlines
            }
        except Exception:
            time.sleep(10 * attempt)
            attempt += 1
            if attempt > 3:
                return {"trend": "Timeout", "entry": "-", "stop_loss": "-", "target": "-", "conviction": "Low", "probability": "0%", "news_snippet": "Error"}

# ================= 6. EMAIL SYSTEM (TOP 30 CURATION) =================
def send_email(weekly_reports, market_trend):
    valid_reports = [r for r in weekly_reports if r['conviction'].lower() in ['high', 'medium', 'med']]
    top_30_reports = sorted(valid_reports, key=lambda x: x['gain_raw'], reverse=True)[:30]

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    day_name = get_ist_now().strftime('%A')
    msg["Subject"] = f"🚀 Nasdaq Short-Term AI Screener ({day_name})"
    
    rows_html = ""
    for item in top_30_reports:
        conv_color = "green" if "high" in item['conviction'].lower() else "orange"
        rows_html += (
            f"<tr><td><b>{item['stock']}</b><br><span style='color: blue;'>{item['price']}</span></td>"
            f"<td><span style='color: green; font-weight: bold;'>{item['gain']}</span><br>"
            f"<span style='font-size: 11px; color: gray;'>RVOL: {item['rvol']}x | Gap: {item['gap']}%</span></td>"
            f"<td style='font-size: 12px; max-width: 150px;'><b>{item['trend']}</b><br><i>News: {item['news']}</i></td>"
            f"<td style='font-size: 13px; font-weight: bold;'>{item['plan']}</td>"
            f"<td style='text-align: center;'><span style='color: {conv_color}; font-weight: bold;'>{item['conviction']}</span><br>{item['probability']}</td></tr>"
        )

    html_content = f"""
    <html><head><style>
      body {{ font-family: Arial, sans-serif; padding: 10px; color: #333; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 10px; }}
      th, td {{ border: 1px solid #e0e0e0; padding: 10px; text-align: left; vertical-align: top; }}
      th {{ background-color: #111827; color: white; }}
      h3 {{ color: #1f2937; border-bottom: 2px solid #3b82f6; padding-bottom: 5px; }}
    </style></head>
    <body>
    <h2>🚀 Nasdaq 1-3 Day Momentum (Top 30)</h2>
    <p><b>Market Trend (QQQ):</b> {market_trend}</p>
    <p>RVOL ബ്രേക്ക്ഔട്ട്, ഗ്യാപ്പ് അപ്പ്, ലേറ്റസ്റ്റ് ന്യൂസ് എന്നിവയുടെ അടിസ്ഥാനത്തിൽ AI തിരഞ്ഞെടുത്ത സ്റ്റോക്കുകൾ.</p>
    <table><tr><th>Stock & Price</th><th>Gain, RVOL & Gap</th><th>AI Trend & Catalyst</th><th>Trade Plan</th><th>Conviction</th></tr>
    {rows_html}
    </table></body></html>
    """
    
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    print(f"🚀 Nasdaq സ്വിങ് ഏജന്റ് പ്രവർത്തിച്ചുതുടങ്ങി...")
    
    market_trend, market_chg = get_market_trend()
    all_tickers = get_all_nasdaq_tickers()
    selected_weekly = get_filtered_stocks(all_tickers, batch_size=30)
    
    weekly_reports = []
    print("\n🤖 സ്റ്റോക്കുകളുടെ AI അനാലിസിസ് (With News & Tech Guardrails)...")
    for data in selected_weekly:
        stock = data['stock']
        print(f"   • Analyzing: {stock}")
        ai_rep = run_ai_analysis(stock, data, market_trend, market_chg)
        
        weekly_reports.append({
            "stock": stock, "price": f"${data['price']:.2f}",
            "gain_raw": data['weekly_gain'], "gain": f"{data['weekly_gain']:.2f}%",
            "rvol": f"{data['rvol']:.1f}", "gap": f"{data['gap_up']:.1f}",
            "trend": ai_rep.get("trend", "N/A"),
            "news": ai_rep.get("news_snippet", "N/A"),
            "plan": f"Entry: {ai_rep.get('entry')} <br><span style='color:red;'>SL: {ai_rep.get('stop_loss')}</span> <br><span style='color:green;'>Tgt: {ai_rep.get('target')}</span>",
            "conviction": ai_rep.get("conviction", "Low"), 
            "probability": ai_rep.get("probability", "N/A")
        })
        time.sleep(random.uniform(3, 6)) # Rate limit സംരക്ഷിക്കാൻ
            
    send_email(weekly_reports, market_trend)
    print("🎉 എല്ലാ പ്രക്രിയകളും വിജയകരമായി പൂർത്തിയായി!")
