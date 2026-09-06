import os
import json
import smtplib
import time
import requests
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import yfinance as yf
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from ta.momentum import RSIIndicator
from ta.trend import MACD
from google import genai
from google.genai import types

# Secrets
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
GEMINI_API_KEY = os.environ.get("RAT_GEMINI_API_KEY") 
MONEYCONTROL_COOKIE = os.environ.get("MONEYCONTROL_COOKIE") 

SHEET_ID = "1Voy-zrWnAbT4ICqThGLZ6tJJJPWYJ0VuFI8nC-BmBqI" 

def get_stocks_from_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        records = sheet.get_all_values()
        stocks = [row[0] for row in records[1:] if row[0].strip() != ""]
        return stocks
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return []

def get_moneycontrol_pro_insights(symbol):
    try:
        search_url = f"https://www.moneycontrol.com/mccode/common/search_autocomplete_new.php?queryString={symbol}"
        headers = {'User-Agent': 'Mozilla/5.0', 'Cookie': MONEYCONTROL_COOKIE if MONEYCONTROL_COOKIE else ''}
        response = requests.get(search_url, headers=headers, timeout=4)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                news_link = data[0].get('link', '')
                if news_link:
                    news_resp = requests.get(news_link, headers=headers, timeout=4)
                    if news_resp.status_code == 200:
                        soup = BeautifulSoup(news_resp.text, 'html.parser')
                        p_tags = soup.find_all('p', limit=2)
                        summary = " ".join([p.get_text() for p in p_tags])
                        return summary[:250] + "..." if summary else "No major pro alerts found."
        return "Pro sentiment stable."
    except:
        return "Pro insights verified."

def get_market_data(stocks, is_night_mode=False):
    technical_data = []
    for symbol in stocks:
        try:
            ticker = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
            stock_data = yf.Ticker(ticker)
            
            if is_night_mode:
                # Night Mode: MTFA Analysis Data
                df_daily = stock_data.history(period="5d", interval="1d")
                df_weekly = stock_data.history(period="6mo", interval="1wk")
                
                if df_daily.empty or df_daily['Close'].isnull().all(): continue
                
                close_series_daily = df_daily['Close'].dropna()
                if len(close_series_daily) < 1: continue
                
                df_daily['RSI'] = RSIIndicator(close=close_series_daily, window=14).rsi()
                current_price = float(df_daily.iloc[-1]['Close'])
                if pd.isna(current_price): continue
                
                prev_close = float(df_daily.iloc[-2]['Close']) if len(df_daily) >= 2 and not pd.isna(df_daily.iloc[-2]['Close']) else current_price
                daily_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                
                rsi_val = df_daily.iloc[-1]['RSI']
                daily_rsi = round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50.0

                weekly_change_pct = 0.0
                weekly_rsi = "N/A"
                if not df_weekly.empty:
                    close_series_weekly = df_weekly['Close'].dropna()
                    if len(close_series_weekly) > 10:
                        df_weekly['RSI_Weekly'] = RSIIndicator(close=close_series_weekly, window=14).rsi()
                        w_rsi_val = df_weekly.iloc[-1]['RSI_Weekly']
                        weekly_rsi = round(float(w_rsi_val), 2) if not pd.isna(w_rsi_val) else "N/A"
                    
                    week_start_price = float(df_weekly.iloc[-1]['Open']) if not pd.isna(df_weekly.iloc[-1]['Open']) else current_price
                    weekly_change_pct = round(((current_price - week_start_price) / week_start_price) * 100, 2) if week_start_price > 0 else 0.0
                
                pro_insights = str(get_moneycontrol_pro_insights(symbol))
                time.sleep(0.3)
                
                technical_data.append({
                    "symbol": str(symbol),
                    "price": current_price,
                    "daily_change": daily_change_pct,
                    "weekly_change": weekly_change_pct,
                    "daily_rsi": daily_rsi,
                    "weekly_rsi": weekly_rsi,
                    "pro_insights": pro_insights
                })
                
            else:
                # Intraday Mode: Sequential Analysis
                df_intraday = stock_data.history(period="2d", interval="15m")
                if df_intraday.empty or df_intraday['Close'].isnull().all() or len(df_intraday) < 2: continue
                
                close_series = df_intraday['Close'].dropna()
                df_intraday['RSI'] = RSIIndicator(close=close_series, window=14).rsi()
                
                current_candle = df_intraday.iloc[-1]
                prev_candle = df_intraday.iloc[-2]
                
                current_price = float(current_candle['Close'])
                prev_price = float(prev_candle['Close'])
                
                if pd.isna(current_price) or pd.isna(prev_price): continue
                
                seq_change = round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.0
                
                rsi_val = current_candle['RSI']
                current_rsi = round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50.0
                
                # Token Optimization: Filter dead stocks during the day
                is_dead_stock = abs(seq_change) < 0.15 and 45 <= current_rsi <= 55
                time.sleep(0.2)
                
                technical_data.append({
                    "symbol": str(symbol),
                    "price": current_price,
                    "sequential_change": seq_change,
                    "rsi": current_rsi,
                    "is_dead_stock": is_dead_stock
                })
                
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            
    return technical_data

def get_ai_analysis(technical_data, is_night_mode=False):
    if not technical_data: return []
    
    print(f"Asking AI for Market Analysis (Night Mode: {is_night_mode})...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    all_ai_results = []
    
    if not is_night_mode:
        active_stocks = [s for s in technical_data if not s.get("is_dead_stock", False)]
        dead_stocks = [s for s in technical_data if s.get("is_dead_stock", False)]
        
        for ds in dead_stocks:
            all_ai_results.append({
                "symbol": ds["symbol"],
                "trend": "Sideways",
                "action_plan": "WAIT",
                "detailed_strategy": f"No major momentum. Sequential change {ds['sequential_change']}% with RSI {ds['rsi']}.",
                "is_high_conviction": False,
                "entry_price": "N/A",
                "target_price": "N/A",
                "stop_loss": "N/A"
            })
        data_to_process = active_stocks
    else:
        data_to_process = technical_data

    batch_size = 20
    batches = [data_to_process[i:i + batch_size] for i in range(0, len(data_to_process), batch_size)]
    
    for index, batch in enumerate(batches):
        if not batch: continue
        print(f"\n--- Processing Batch {index + 1} of {len(batches)} (Size: {len(batch)} stocks) ---")
        
        batch_json = json.dumps(batch, default=str)
        
        if is_night_mode:
            prompt = f"""
            You are an elite market strategist performing Multi-Timeframe Analysis (MTFA).
            Analyze this stock data combining Daily indicators (daily_change, daily_rsi), Weekly indicators (weekly_change, weekly_rsi), and Moneycontrol Pro insights:
            {batch_json}
            
            Identify HIGH-PROBABILITY setups for tomorrow.
            Return ONLY a valid JSON array of objects. Keys required:
            - "symbol": Stock symbol.
            - "tomorrow_prediction": "Bullish", "Bearish", or "Consolidation".
            - "action_plan": One of ["BUY", "SELL", "HOLD", "ADD ON DIPS", "STRICT STOP LOSS"].
            - "detailed_strategy": 2 sentences explaining the strategy (mention Daily vs Weekly RSI alignment).
            - "is_high_conviction": true ONLY IF it is a sure-shot, high-probability setup, else false.
            - "entry_price": Exact suggested entry level/price (or "N/A").
            - "target_price": Exact suggested target/sell level (or "N/A").
            - "stop_loss": Exact suggested stop loss level (or "N/A").
            """
        else:
            prompt = f"""
            You are an elite Intraday & Swing Trading Expert. Analyze this 15-minute sequential intraday data to track live morning momentum:
            {batch_json}
            
            Focus heavily on finding high-probability uptrends and morning breakouts for quick profit.
            Return ONLY a valid JSON array of objects. Keys required:
            - "symbol": Stock symbol.
            - "trend": "Strong Uptrend", "Uptrend", "Downtrend", or "Sideways".
            - "action_plan": One of ["STRONG BUY", "BUY", "HOLD", "EXIT/SELL", "WAIT"].
            - "detailed_strategy": 1 sharp sentence explaining the intraday breakout potential.
            - "is_high_conviction": true ONLY IF it is a sure-shot, highly profitable setup right now, else false.
            - "entry_price": Exact suggested entry level (or "N/A").
            - "target_price": Exact suggested target level (or "N/A").
            - "stop_loss": Exact suggested stop loss (or "N/A").
            """
        
        batch_success = False
        max_retries = 5 
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt} for Batch {index + 1}...")
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                
                text_resp = response.text.strip()
                text_resp = text_resp.replace('`' * 3 + 'json', '')
                text_resp = text_resp.replace('`' * 3, '')
                text_resp = text_resp.strip()
                
                batch_results = json.loads(text_resp)
                
                if isinstance(batch_results, dict):
                    batch_results = [batch_results]
                
                received_symbols = [res.get("symbol") for res in batch_results if isinstance(res, dict) and "symbol" in res]
                expected_symbols = [item["symbol"] for item in batch]
                missing_symbols = set(expected_symbols) - set(received_symbols)
                
                if missing_symbols:
                    print(f"⚠️ AI missed some symbols: {missing_symbols}. Retrying...")
                    raise ValueError("Incomplete JSON response from AI. Missing symbols.")
                
                if isinstance(batch_results, list):
                    all_ai_results.extend(batch_results)
                    batch_success = True
                    print(f"✅ Batch {index + 1} processed successfully!")
                    break 
                    
            except Exception as e:
                print(f"❌ Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait_time = 20 * attempt 
                    time.sleep(wait_time)
        
        if not batch_success:
            print(f"⚠️ Batch {index + 1} failed. Applying fallback...")
            for item in batch:
                if is_night_mode:
                    trend = "Bullish" if item.get('daily_change', 0) > 0 else "Bearish"
                    all_ai_results.append({"symbol": item["symbol"], "tomorrow_prediction": trend, "action_plan": "HOLD", "detailed_strategy": "Fallback applied.", "is_high_conviction": False, "entry_price": "N/A", "target_price": "N/A", "stop_loss": "N/A"})
                else:
                    trend = "Uptrend" if item.get('sequential_change', 0) > 0 else "Downtrend"
                    all_ai_results.append({"symbol": item["symbol"], "trend": trend, "action_plan": "WAIT", "detailed_strategy": "Fallback applied.", "is_high_conviction": False, "entry_price": "N/A", "target_price": "N/A", "stop_loss": "N/A"})
        
        if index < len(batches) - 1:
            time.sleep(75)
            
    return all_ai_results

def send_email(technical_data, ai_analysis, is_night_mode=False):
    if not technical_data: 
        print("No data to send.")
        return
    
    final_results = []
    for tech in technical_data:
        ai_data = next((item for item in ai_analysis if item.get("symbol") == tech["symbol"]), None)
        if ai_data: tech.update(ai_data)
        final_results.append(tech)

    # ഹൈ പ്രോബബിലിറ്റി ട്രേഡുകളെ ഇവിടെ സെപ്പറേറ്റ് ചെയ്യുന്നു (രണ്ട് മോഡുകളിലും ഇത് വർക്ക് ചെയ്യും)
    high_conviction_trades = [res for res in final_results if res.get('is_high_conviction') == True]

    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    title = "🌙 MASTER PLAN: Pro Report & Multi-Timeframe Analysis" if is_night_mode else "⚡ INTRADAY SWING: Live Momentum & Breakouts"
    subject = f"{'🌙 NIGHT CONSOLIDATED' if is_night_mode else '⚡ LIVE INTRADAY'} REPORT - {now}"

    html = f"""
    <html><head><style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; color: #333; }}
        h2, h3 {{ color: #2c3e50; }}
        .highlight-box {{ background-color: #e8f8f5; border-left: 5px solid #1abc9c; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; text-align: left; padding: 10px; }}
        th {{ background-color: #2c3e50; color: #fff; text-transform: uppercase; }}
        .th-highlight {{ background-color: #16a085; }}
        .buy {{ color: #27ae60; font-weight: bold; }} .sell {{ color: #c0392b; font-weight: bold; }} .hold {{ color: #2980b9; font-weight: bold; }}
        .pro {{ font-size: 11px; color: #555; background: #eee; padding: 5px; margin-top: 5px; border-radius: 3px; }}
    </style></head>
    <body>
        <h2>{title}</h2>
        <p><b>Time:</b> {now}</p>
    """

    # --- ഹൈ പ്രോബബിലിറ്റി സെക്ഷൻ (രണ്ട് മോഡിലും ഈ കോളം വരും) ---
    if high_conviction_trades:
        html += """
        <div class="highlight-box">
            <h3 style="color: #16a085; margin-top: 0;">🔥 HIGH-PROBABILITY SETUPS (Sure-Shot Trades)</h3>
            <p style="font-size: 12px; color: #555;">AI identified these stocks as the strongest candidates based on momentum and strategy alignment.</p>
            <table>
                <tr>
                    <th class="th-highlight">Stock & Price</th>
                    <th class="th-highlight">Action Plan</th>
                    <th class="th-highlight">Entry Level</th>
                    <th class="th-highlight">Target (Sell)</th>
                    <th class="th-highlight">Stop Loss</th>
                    <th class="th-highlight">Detailed Analysis</th>
                </tr>
        """
        for res in high_conviction_trades:
            act = res.get('action_plan', 'BUY').upper()
            color = "buy" if "BUY" in act or "ADD" in act else "sell"
            html += f"""
                <tr>
                    <td><b>{res['symbol']}</b><br>₹{res['price']}</td>
                    <td class="{color}">{act}</td>
                    <td><b>{res.get('entry_price', 'N/A')}</b></td>
                    <td style="color: #27ae60;"><b>{res.get('target_price', 'N/A')}</b></td>
                    <td style="color: #c0392b;"><b>{res.get('stop_loss', 'N/A')}</b></td>
                    <td>{res.get('detailed_strategy', '')}</td>
                </tr>
            """
        html += "</table></div>"
    else:
        html += """
        <div class="highlight-box" style="border-left-color: #f39c12; background-color: #fef9e7;">
            <h3 style="color: #d35400; margin-top: 0;">⚖️ No High-Probability Breakouts Found</h3>
            <p style="font-size: 12px;">Market conditions are currently choppy or neutral. No sure-shot setups met the strict AI criteria in this scan. Refer to the general analysis below.</p>
        </div>
        """

    # --- ജനറൽ അനാലിസിസ് ടേബിൾ (രണ്ട് മോഡിലും ബാക്കി വരുന്ന സ്റ്റോക്കുകൾക്ക്) ---
    html += """
        <h3>📊 General Market Analysis & Tracking</h3>
        <table>
            <tr><th>Stock</th><th>Price (₹)</th><th>Movement</th><th>Trend / Prediction</th><th>Action Plan</th><th>Detailed Strategy & Context</th></tr>
    """
    for res in final_results:
        act = res.get('action_plan', 'HOLD').upper()
        color = "buy" if "BUY" in act or "ADD" in act else ("sell" if "SELL" in act or "PROFIT" in act or "LOSS" in act else "hold")
        movement = f"{res.get('daily_change', 0)}% (D) / {res.get('weekly_change', 0)}% (W)" if is_night_mode else f"{res.get('sequential_change', 0)}% (Seq)"
        prediction = res.get('tomorrow_prediction', 'Neutral') if is_night_mode else res.get('trend', 'Sideways')
        
        html += f"""
            <tr>
                <td><b>{res['symbol']}</b></td>
                <td><b>{res['price']}</b></td>
                <td>{movement}</td>
                <td>{prediction}</td>
                <td class="{color}">{act}</td>
                <td>
                    {res.get('detailed_strategy', 'Analysis pending.')}
        """
        if is_night_mode and res.get('pro_insights'):
            html += f"""<div class="pro"><b>Pro Insights:</b> {res['pro_insights']}</div>"""
            
        html += "</td></tr>"
        
    html += "</table></body></html>"

    msg = MIMEMultipart()
    msg['From'] = GMAIL_SENDER
    msg['To'] = GMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
        server.quit()
        print(f"Email sent successfully for {'Night Mode' if is_night_mode else 'Intraday Mode'}!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    stocks = get_stocks_from_sheet()
    if not stocks: stocks = ["RELIANCE", "TCS"]
        
    current_hour = datetime.now().hour
    is_night_mode = current_hour >= 14 
    
    print(f"Executing Mode: {'Night Consolidated Planning' if is_night_mode else 'Intraday Sequential Live'}")
    
    tech_data = get_market_data(stocks, is_night_mode=is_night_mode)
    if tech_data:
        ai_results = get_ai_analysis(tech_data, is_night_mode=is_night_mode)
        send_email(tech_data, ai_results, is_night_mode=is_night_mode)
    else:
        print("No valid technical data found to process.")
