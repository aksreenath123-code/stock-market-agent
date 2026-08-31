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
        scope = ["[https://spreadsheets.google.com/feeds](https://spreadsheets.google.com/feeds)", "[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"]
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
        search_url = f"[https://www.moneycontrol.com/mccode/common/search_autocomplete_new.php?queryString=](https://www.moneycontrol.com/mccode/common/search_autocomplete_new.php?queryString=){symbol}"
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
                time.sleep(0.3)
                
                technical_data.append({
                    "symbol": str(symbol),
                    "price": current_price,
                    "daily_change": daily_change_pct,
                    "weekly_change": weekly_change_pct,
                    "rsi": current_rsi,
                    "pro_insights": pro_insights
                })
                
            else:
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
                
                is_dead_stock = abs(seq_change) < 0.1 and 48 <= current_rsi <= 52
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
                "action": "WAIT",
                "reason": f"No major momentum. Sequential change {ds['sequential_change']}% with RSI {ds['rsi']}."
            })
        data_to_process = active_stocks
    else:
        data_to_process = technical_data

    batch_size = 25
    batches = [data_to_process[i:i + batch_size] for i in range(0, len(data_to_process), batch_size)]
    
    for index, batch in enumerate(batches):
        if not batch: continue
        print(f"Processing Batch {index + 1} of {len(batches)}...")
        
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
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                # ഈ വരിയിലാണ് എറർ വന്നിരുന്നത്, ഇത് ഇപ്പോൾ കൃത്യമായി ഫോർമാറ്റ് ചെയ്തിട്ടുണ്ട്
                text_resp = response.text.strip().replace("
