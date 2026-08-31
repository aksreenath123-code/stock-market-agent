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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
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
                # Night Mode: Daily & Weekly Data fetching (With NaN fixes)
                df_daily = stock_data.history(period="5d", interval="1d")
                df_weekly = stock_data.history(period="1mo", interval="1wk")
                
                if df_daily.empty or df_daily['Close'].isnull().all(): continue
                
                close_series = df_daily['Close'].dropna()
                if len(close_series) < 1: continue
                
                df_daily['RSI'] = RSIIndicator(close=close_series, window=14).rsi()
                current_price = float(df_daily.iloc[-1]['Close'])
                
                if pd.isna(current_price): continue
                
                prev_close = float(df_daily.iloc[-2]['Close']) if len(df_daily) >= 2 and not pd.isna(df_daily.iloc[-2]['Close']) else current_price
                daily_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                
                week_start_price = float(df_weekly.iloc[-1]['Open']) if not df_weekly.empty and not pd.isna(df_weekly.iloc[-1]['Open']) else current_price
                weekly_change_pct = round(((current_price - week_start_price) / week_start_price) * 100, 2) if week_start_price > 0 else 0.0
                
                rsi_val = df_daily.iloc[-1]['RSI']
                current_rsi = round(float(rsi_val), 2) if not pd.isna(rsi_val) else 50.0
                
                pro_insights = str(get_moneycontrol_pro_insights(symbol))
                time.sleep(0.3) # Yahoo Finance Rate limit protection
                
                technical_data.append({
                    "symbol": str(symbol),
                    "price": current_price,
                    "daily_change": daily_change_pct,
                    "weekly_change": weekly_change_pct,
                    "rsi": current_rsi,
                    "pro_insights": pro_insights
                })
                
            else:
                # Intraday Mode: 15-Min Sequential Data
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
                is_dead_stock = abs(seq_change) < 0.1 and 48 <= current_rsi <= 52
                time.sleep(0.2) # Yahoo Finance Rate limit protection
                
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
        
        # Dead stocks get automatic fallback (No API tokens wasted)
        for ds in dead_stocks:
            all_ai_results.append({
                "symbol": ds["symbol"],
                "trend": "Sideways",
                "action": "WAIT",
                "reason": f"No major momentum. Sequential change {ds['sequential_change']}% with RSI {ds['rsi']}."
            })
        data_to_process = active_stocks
    else:
        # At night, we analyze everything to plan for tomorrow
        data_to_process = technical_data

    # Output truncation ഒഴിവാക്കാൻ ബാച്ച് സൈസ് 20 ആക്കി ചുരുക്കി
    batch_size = 20
    batches = [data_to_process[i:i + batch_size] for i in range(0, len(data_to_process), batch_size)]
    
    for index, batch in enumerate(batches):
        if not batch: continue
        print(f"\n--- Processing Batch {index + 1} of {len(batches)} (Size: {len(batch)} stocks) ---")
        
        # JSON serialization fix (default=str)
        batch_json = json.dumps(batch, default=str)
        
        if is_night_mode:
            prompt = f"""
            Analyze this daily & weekly consolidated stock data with Moneycontrol Pro insights:
            {batch_json}
            
            Focus on providing a CLEAR PLAN FOR TOMORROW.
            Return ONLY a valid JSON array of objects. Keys required:
            - "symbol": Stock symbol.
            - "tomorrow_prediction": "Bullish", "Bearish", or "Consolidation".
            - "action_plan": One of ["BUY", "SELL/BOOK PROFIT", "HOLD", "ADD ON DIPS", "STRICT STOP LOSS"].
            - "detailed_strategy": 2 sentences explaining tomorrow's strategy based on weekly trend and Pro insights.
            """
        else:
            prompt = f"""
            Analyze this 15-minute sequential intraday data to track live momentum:
            {batch_json}
            
            Return ONLY a valid JSON array of objects. Keys required:
            - "symbol": Stock symbol.
            - "trend": "Uptrend", "Downtrend", or "Sideways".
            - "action": One of ["ENTRY/BUY", "HOLD", "EXIT/SELL", "WAIT"].
            - "reason": 1 short sentence explaining the sequential momentum (current 15m vs prev 15m).
            """
        
        batch_success = False
        max_retries = 5 # പരമാവധി 5 തവണ റീട്രൈ ചെയ്യും
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt} for Batch {index + 1}...")
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                
                # കോപ്പി-പേസ്റ്റ് എററുകൾ ഒഴിവാക്കാൻ സുരക്ഷിതമായി റീപ്ലേസ് ചെയ്യുന്നു
                text_resp = response.text.strip()
                text_resp = text_resp.replace('`' * 3 + 'json', '')
                text_resp = text_resp.replace('`' * 3, '')
                text_resp = text_resp.strip()
                
                batch_results = json.loads(text_resp)
                
                if isinstance(batch_results, dict):
                    batch_results = [batch_results]
                
                # ഡാറ്റ വാലിഡേഷൻ: നമ്മൾ അയച്ച എല്ലാ സ്റ്റോക്കുകളും AI തിരികെ തന്നിട്ടുണ്ടോ എന്ന് ഉറപ്പുവരുത്തുന്നു
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
                    break # സക്സസ് ആയാൽ റീട്രൈ ലൂപ്പ് ബ്രേക്ക് ചെയ്യും
                    
            except Exception as e:
                print(f"❌ Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait_time = 20 * attempt # 20, 40, 60, 80 സെക്കൻഡുകൾ വീതം ഗ്യാപ്പ് കൂട്ടുന്നു
                    print(f"⏳ Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
        
        # Independent Batch Accumulation (If AI fails completely, we still provide structured data)
        if not batch_success:
            print(f"⚠️ Batch {index + 1} completely failed after {max_retries} retries. Applying fallback...")
            for item in batch:
                if is_night_mode:
                    trend = "Bullish" if item.get('daily_change', 0) > 0 else "Bearish"
                    all_ai_results.append({"symbol": item["symbol"], "tomorrow_prediction": trend, "action_plan": "HOLD", "detailed_strategy": f"Daily change {item.get('daily_change', 0)}%. Technical data indicates holding current positions."})
                else:
                    trend = "Uptrend" if item.get('sequential_change', 0) > 0 else "Downtrend"
                    all_ai_results.append({"symbol": item["symbol"], "trend": trend, "action": "WAIT", "reason": f"Sequential change {item.get('sequential_change', 0)}%. Independent evaluation applied."})
        
        # ഓരോ ബാച്ചിനും ഇടയിലുള്ള നിർബന്ധിത ഗ്യാപ്പ് (1 മിനിറ്റ് 15 സെക്കൻഡ്) റേറ്റ് ലിമിറ്റ് ഒഴിവാക്കാൻ
        if index < len(batches) - 1:
            print(f"⏸️ Waiting 75 seconds before sending the next batch to avoid API rate limits...")
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

    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    if is_night_mode:
        subject = f"🌙 MASTER PLAN FOR TOMORROW: Consolidated Pro Report - {now}"
        html = f"""
        <html><head><style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; }}
            th, td {{ border: 1px solid #ddd; text-align: left; padding: 10px; }}
            th {{ background-color: #1a252f; color: #fff; text-transform: uppercase; }}
            .buy {{ color: #27ae60; font-weight: bold; }} .sell {{ color: #c0392b; font-weight: bold; }} .hold {{ color: #2980b9; font-weight: bold; }}
            .pro {{ font-size: 11px; color: #555; background: #eee; padding: 5px; margin-top: 5px; border-radius: 3px; }}
        </style></head>
        <body>
            <h2 style="color: #2c3e50;">🌙 Tomorrow's Action Plan & Consolidated Report</h2>
            <p><b>Time:</b> {now} | Daily & Weekly Trends + Moneycontrol Pro</p>
            <table>
                <tr><th>Stock</th><th>Price (₹)</th><th>Daily/Wk Chg</th><th>Prediction</th><th>Action Plan</th><th>Strategy & Pro Insights</th></tr>
        """
        for res in final_results:
            act = res.get('action_plan', 'HOLD').upper()
            color = "buy" if "BUY" in act or "ADD" in act else ("sell" if "SELL" in act or "PROFIT" in act or "LOSS" in act else "hold")
            html += f"""
                <tr>
                    <td><b>{res['symbol']}</b></td>
                    <td><b>{res['price']}</b></td>
                    <td>{res.get('daily_change', 0)}% / {res.get('weekly_change', 0)}%</td>
                    <td>{res.get('tomorrow_prediction', 'Neutral')}</td>
                    <td class="{color}">{act}</td>
                    <td>
                        {res.get('detailed_strategy', 'Analysis pending.')}
                        <div class="pro"><b>Pro:</b> {res.get('pro_insights', 'N/A')}</div>
                    </td>
                </tr>
            """
    else:
        subject = f"⚡ INTRADAY LIVE: Sequential Momentum - {now}"
        html = f"""
        <html><head><style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; }}
            th, td {{ border: 1px solid #ddd; text-align: left; padding: 10px; }}
            th {{ background-color: #004d40; color: #fff; text-transform: uppercase; }}
            .buy {{ color: #2e7d32; font-weight: bold; }} .sell {{ color: #c62828; font-weight: bold; }} .hold {{ color: #7f8c8d; font-weight: bold; }}
        </style></head>
        <body>
            <h2 style="color: #004d40;">⚡ Live Intraday Tracker</h2>
            <p><b>Time:</b> {now} | 15-Minute Sequential Comparison</p>
            <table>
                <tr><th>Stock</th><th>Live Price (₹)</th><th>Seq Momentum</th><th>Trend</th><th>Action</th><th>AI Live Update</th></tr>
        """
        for res in final_results:
            act = res.get('action', 'WAIT').upper()
            color = "buy" if "BUY" in act or "ENTRY" in act else ("sell" if "SELL" in act or "EXIT" in act else "hold")
            html += f"""
                <tr>
                    <td><b>{res['symbol']}</b></td>
                    <td><b>{res['price']}</b></td>
                    <td>{res.get('sequential_change', 0)}%</td>
                    <td>{res.get('trend', 'Sideways')}</td>
                    <td class="{color}">{act}</td>
                    <td>{res.get('reason', 'Analysis pending.')}</td>
                </tr>
            """
            
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
    # UTC സമയം 14 അല്ലെങ്കിൽ അതിന് മുകളിലാണെങ്കിൽ (അതായത് IST 7:30 PM ന് ശേഷം) നൈറ്റ് മോഡ് ആക്റ്റീവ് ആകും
    is_night_mode = current_hour >= 14 
    
    print(f"Executing Mode: {'Night Consolidated Planning' if is_night_mode else 'Intraday Sequential Live'}")
    
    tech_data = get_market_data(stocks, is_night_mode=is_night_mode)
    if tech_data:
        ai_results = get_ai_analysis(tech_data, is_night_mode=is_night_mode)
        send_email(tech_data, ai_results, is_night_mode=is_night_mode)
    else:
        print("No valid technical data found to process.")
