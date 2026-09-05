import sys
import subprocess
import os
import smtplib
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# ==================== 1. ലൈബ്രറി ഇൻസ്റ്റാളേഷൻ ====================
REQUIRED_PACKAGES = ["yfinance", "pandas", "google-genai", "pandas-ta"]

def install_missing_packages():
    for package in REQUIRED_PACKAGES:
        try:
            # pandas-ta ഇംപോർട്ട് ചെയ്യുന്നത് pandas_ta എന്നാണ്
            pkg_name = "google.genai" if package == "google-genai" else ("pandas_ta" if package == "pandas-ta" else package)
            __import__(pkg_name)
        except ImportError:
            print(f"📦 ഇൻസ്റ്റാൾ ചെയ്യുന്നു: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

install_missing_packages()

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ==================== 2. API കോൺഫിഗറേഷൻ ====================
GEMINI_API_KEY = os.getenv("IPO_GEMINI_API_KEY") 
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

if not GEMINI_API_KEY:
    print("⚠️ പിഴവ്: API Key ലഭ്യമായില്ല. GitHub Secrets പരിശോധിക്കുക.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# നിരീക്ഷിക്കേണ്ട സ്റ്റോക്കുകളുടെ ലിസ്റ്റ്
tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "ZOMATO.NS", "SUZLON.NS", "TATAMOTORS.NS", "IRFC.NS"] 

# ==================== 3. AI ANALYSIS MODULE ====================
def get_ai_swing_analysis(ticker, current_price, gain, rsi, ema20, ema50, rvol, atr):
    print(f"🧠 {ticker} - പ്രൊഫഷണൽ AI അനാലിസിസ് നടക്കുന്നു...")
    
    prompt = f"""
    You are an elite technical analyst and swing trader. Analyze the following technical setup for {ticker}:
    
    - Current Price: ₹{current_price:.2f}
    - 30-Day Gain: {gain:.2f}%
    - RSI (14): {rsi:.2f} (Consider 50-65 as ideal, >70 as overbought)
    - 20 EMA: ₹{ema20:.2f} | 50 EMA: ₹{ema50:.2f} (Price > EMAs indicates uptrend)
    - Relative Volume (RVOL): {rvol:.2f}x (Higher means institutional buying)
    - ATR (14): ₹{atr:.2f} (Use this to calculate a safe Stop Loss)
    
    Based on these metrics, provide a strict swing trade analysis. Calculate a logical Entry point, Stop Loss (using ATR), and Target (Risk:Reward of at least 1:2).
    
    Return ONLY a valid JSON format with these exact keys:
    {{"trend": "Short technical summary", "entry": "₹...", "stop_loss": "₹...", "target": "₹...", "conviction": "High/Medium/Low", "probability_rate": "percentage like 80%"}}
    """
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt
            )
            result = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(result)
        except Exception as e:
            print(f"⚠️ API Error for {ticker} (Attempt {attempt+1}): {e}")
            time.sleep(3)
            
    return {"trend": "AI Failed", "entry": "N/A", "stop_loss": "N/A", "target": "N/A", "conviction": "N/A", "probability_rate": "N/A"}

# ==================== 4. അഡ്വാൻസ്ഡ് യാഹൂ ഫിനാൻസ് സ്ക്രീനർ ====================
def get_top_gainers_with_advanced_ai():
    gainers_info = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90) # EMA കാൽക്കുലേറ്റ് ചെയ്യാൻ 90 ദിവസത്തെ ഡാറ്റ
    
    print("📊 മാർക്കറ്റ് ഡാറ്റയും ഇൻഡിക്കേറ്ററുകളും പരിശോധിക്കുന്നു...")
    
    for ticker in tickers:
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if len(data) >= 50: # കുറഞ്ഞത് 50 ദിവസത്തെ ഡാറ്റയെങ്കിലും വേണം
                # 1. ഇൻഡിക്കേറ്ററുകൾ കാൽക്കുലേറ്റ് ചെയ്യുന്നു (pandas_ta)
                data.ta.ema(length=20, append=True)
                data.ta.ema(length=50, append=True)
                data.ta.rsi(length=14, append=True)
                data.ta.atr(length=14, append=True)
                
                # RVOL (Relative Volume) - കഴിഞ്ഞ 20 ദിവസത്തെ വോളിയത്തിന്റെ എത്ര ഇരട്ടിയാണ് ഇന്നത്തെ വോളിയം
                data['RVOL'] = data['Volume'] / data['Volume'].rolling(20).mean()
                
                # ഏറ്റവും പുതിയ ഡാറ്റ
                latest = data.iloc[-1]
                current_price = float(latest['Close'].item())
                rsi = float(latest['RSI_14'].item())
                ema20 = float(latest['EMA_20'].item())
                ema50 = float(latest['EMA_50'].item())
                atr = float(latest['ATRr_14'].item())
                rvol = float(latest['RVOL'].item())
                
                # 2. 30 ദിവസത്തെ ഗെയിൻ കാൽക്കുലേഷൻ
                # ട്രേഡിങ് ദിവസങ്ങൾ മാത്രം ഉള്ളതുകൊണ്ട് കഴിഞ്ഞ 21 റോൾ എടുത്താൽ ഏകദേശം 30 ദിവസം ആകും
                price_30_days_ago = float(data['Close'].iloc[-21].item()) 
                gain_percent = ((current_price - price_30_days_ago) / price_30_days_ago) * 100
                
                if gain_percent >= 15:
                    ai_report = get_ai_swing_analysis(ticker, current_price, gain_percent, rsi, ema20, ema50, rvol, atr)
                    
                    gainers_info.append({
                        "stock": ticker,
                        "gain": f"{gain_percent:.2f}%",
                        "price": f"₹{current_price:.2f}",
                        "technicals": f"RSI: {rsi:.1f} | RVOL: {rvol:.1f}x",
                        "trend": ai_report.get("trend", "N/A"),
                        "entry_sl_target": f"Entry: {ai_report.get('entry')} <br><span style='color:red;'>SL: {ai_report.get('stop_loss')}</span> <br><span style='color:green;'>Tgt: {ai_report.get('target')}</span>",
                        "conviction": ai_report.get("conviction", "N/A"),
                        "probability": ai_report.get("probability_rate", "N/A")
                    })
        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            
    return gainers_info

# ==================== 5. EMAIL COMPOSITION (PRO FORMAT) ====================
def send_email(gainers_list):
    print("📧 പ്രൊഫഷണൽ റിപ്പോർട്ട് അയക്കുന്നു...")
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "🚀 PRO Swing Alert: AI + Technical Setups"
    
    if not gainers_list:
        html_content = "<html><body><h3>കഴിഞ്ഞ 30 ദിവസത്തിൽ 15% ഗെയിൻ ഉള്ള മികച്ച സെറ്റപ്പുകൾ ലഭ്യമല്ല.</h3></body></html>"
    else:
        rows = ""
        for item in gainers_list:
            # കൺവിക്ഷൻ ഹൈ ആണെങ്കിൽ ഹൈലൈറ്റ് ചെയ്യാൻ
            conviction_color = "green" if item['conviction'].lower() == "high" else ("orange" if item['conviction'].lower() == "medium" else "red")
            
            rows += f"""
            <tr>
                <td><b>{item['stock']}</b><br><span style="color: blue;">{item['price']}</span></td>
                <td><span style="color: green; font-weight: bold;">{item['gain']}</span><br><span style="font-size: 12px; color: gray;">{item['technicals']}</span></td>
                <td style="font-size: 13px;">{item['trend']}</td>
                <td style="font-size: 13px; font-weight: bold;">{item['entry_sl_target']}</td>
                <td style="text-align: center;"><span style="color: {conviction_color}; font-weight: bold;">{item['conviction']}</span><br>{item['probability']}</td>
            </tr>
            """
            
        html_content = f"""
        <html>
        <head>
        <style>
          body {{ background-color: #f4f4f9; color: #333333; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; }}
          .container {{ background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
          table {{ border-collapse: collapse; width: 100%; font-size: 14px; margin-top: 15px; }}
          th, td {{ border: 1px solid #e0e0e0; text-align: left; padding: 12px; vertical-align: top; line-height: 1.5; }}
          th {{ background-color: #111827; color: #ffffff; font-weight: bold; font-size: 13px; text-align: center; }}
          tr:nth-child(even) {{ background-color: #f9fafb; }}
          h2 {{ color: #111827; margin-bottom: 5px; border-bottom: 3px solid #3b82f6; padding-bottom: 5px; display: inline-block; font-size: 22px; }}
          .note {{ font-size: 12px; color: #666666; margin-top: 15px; }}
        </style>
        </head>
        <body>
            <div class="container">
                <h1 style="text-align: center; color: #111827;">📈 PRO Swing Trading Screener</h1>
                <h2>🚀 High Potential Breakouts & Setups</h2>
                <p>AI അനാലിസിസ് നൽകിയിരിക്കുന്നത് <b>RSI, EMA (20 & 50), ATR, RVOL</b> എന്നീ പ്രൊഫഷണൽ ഇൻഡിക്കേറ്ററുകളുടെ അടിസ്ഥാനത്തിലാണ്.</p>
                
                <table>
                    <tr>
                        <th>Stock & Price</th>
                        <th>Gain & Technicals</th>
                        <th>AI Setup Analysis</th>
                        <th>Trade Plan (Entry/SL/Target)</th>
                        <th>Conviction</th>
                    </tr>
                    {rows}
                </table>
                <p class="note">* Stop Loss കാൽക്കുലേറ്റ് ചെയ്തിരിക്കുന്നത് ATR (Average True Range) ഉപയോഗിച്ചാണ്. ഇത് ഒരു സാമ്പത്തിക ഉപദേശമല്ല, ട്രേഡ് എടുക്കുന്നതിന് മുൻപ് റിസ്ക് മാനേജ്മെന്റ് ഉറപ്പാക്കുക.</p>
            </div>
        </body>
        </html>
        """
        
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("✅ ഇമെയിൽ വിജയകരമായി അയച്ചു!")
    except Exception as e:
        print(f"❌ ഇമെയിൽ അയക്കുന്നതിൽ പരാജയപ്പെട്ടു: {e}")

if __name__ == "__main__":
    stocks_data = get_top_gainers_with_advanced_ai()
    send_email(stocks_data)
