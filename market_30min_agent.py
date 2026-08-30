import os
import json
import smtplib
import time
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

# നിങ്ങളുടെ യഥാർത്ഥ ഗൂഗിൾ ഷീറ്റിന്റെ ID ഇവിടെ കൊടുക്കുക!
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

def get_technical_data(stocks, is_market_close=False):
    technical_data = []
    for symbol in stocks:
        try:
            ticker = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
            stock_data = yf.Ticker(ticker)
            
            interval = "1d" if is_market_close else "30m"
            period = "1mo" if is_market_close else "5d"
            
            df = stock_data.history(period=period, interval=interval)
            
            if df.empty or len(df) < 2:
                continue

            close_series = df['Close'].squeeze()
            df['RSI'] = RSIIndicator(close=close_series, window=14).rsi()
            macd = MACD(close=close_series)
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            
            # പ്രീവിയസ് ഡേ ഡാറ്റയും ഇന്നത്തെ നിലവിലെ ഡാറ്റയും വേർതിരിച്ചെടുക്കുന്നു
            prev_day_close = df.iloc[-2]['Close'] if len(df) >= 2 else df.iloc[-1]['Close']
            current_candle = df.iloc[-1]
            
            candle_history = []
            for idx, row in df.tail(5).iterrows():
                candle_history.append({
                    "date_time": str(idx),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume']),
                    "rsi": round(row['RSI'], 2) if not pd.isna(row['RSI']) else 50
                })

            current_price = current_candle['Close']
            current_volume = current_candle['Volume']
            avg_volume = df['Volume'].rolling(window=10).mean().iloc[-1] if len(df) >= 10 else current_volume
            
            technical_data.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "prev_day_close": round(prev_day_close, 2),
                "price_change_from_prev": round(current_price - prev_day_close, 2),
                "rsi": round(current_candle['RSI'], 2) if not pd.isna(current_candle['RSI']) else 50,
                "macd": round(current_candle['MACD'], 2) if not pd.isna(current_candle['MACD']) else 0,
                "volume": int(current_volume),
                "avg_volume": int(avg_volume),
                "history": candle_history
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            
    return technical_data

def get_ai_analysis(technical_data, is_market_close=False):
    if not technical_data:
        return []
    
    print(f"Asking AI for Market Analysis (Market Close: {is_market_close})...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    all_ai_results = []
    
    batch_size = 25
    batches = [technical_data[i:i + batch_size] for i in range(0, len(technical_data), batch_size)]
    
    for index, batch in enumerate(batches):
        print(f"Processing Batch {index + 1} of {len(batches)}...")
        
        if is_market_close:
            prompt = f"""
            You are an elite stock market strategist. Analyze the FULL DAY closing technical data for these Indian stocks:
            {json.dumps(batch)}
            
            Provide a comprehensive daily wrap-up and STRATEGY FOR TOMORROW.
            Return ONLY a valid JSON array of objects. No markdown, no extra text. 
            Use exactly these keys:
            - "symbol": The stock symbol.
            - "trend": "Strong Bullish", "Bullish", "Neutral", "Bearish", or "Strong Bearish".
            - "suggestion": One of ["BUY FOR TOMORROW", "SELL/SHORT", "HOLD", "ACCUMULATE ON DIP"].
            - "ai_reason": A detailed 2-sentence wrap-up of today's behavior and specific actionable strategy/levels for tomorrow's opening.
            """
        else:
            # രാവിലെ ഡാറ്റ കുറവാണെങ്കിൽ പ്രീവിയസ് ക്ലോസിങ് വെച്ചും, പിന്നീട് സീക്വൻഷ്യൽ കാൻഡിലുകൾ വെച്ചും അനലൈസ് ചെയ്യാൻ നിർദ്ദേശം നൽകുന്നു
            prompt = f"""
            You are an elite stock market technical analyst. Analyze this 30-minute timeframe technical data including previous day close and recent history for Indian stocks:
            {json.dumps(batch)}
            
            Instructions:
            - If early morning (few candles available), compare the current price action and volume against the 'prev_day_close' to find opening momentum or gap behavior.
            - If multiple sequential candles are available, evaluate backward tracking (sequential momentum in RSI, volume, and price).
            
            Return ONLY a valid JSON array of objects. No markdown, no extra text. 
            Use exactly these keys:
            - "symbol": The stock symbol.
            - "trend": "Strong Bullish", "Bullish", "Neutral", "Bearish", or "Strong Bearish".
            - "suggestion": One of ["STRONG BUY", "BUY ON DIP", "HOLD", "SELL", "AVERAGE"].
            - "ai_reason": A crisp, professional 2-sentence technical justification mentioning previous day context or sequential momentum.
            """
        
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            batch_results = json.loads(response.text)
            if isinstance(batch_results, list):
                all_ai_results.extend(batch_results)
            elif isinstance(batch_results, dict):
                all_ai_results.append(batch_results)
                
        except Exception as e:
            print(f"AI Analysis Failed for Batch {index + 1}: {e}")
        
        if index < len(batches) - 1:
            time.sleep(2)
            
    return all_ai_results

def send_email(technical_data, ai_analysis, is_market_close=False):
    if not technical_data:
        print("No data to send.")
        return

    final_results = []
    for tech in technical_data:
        ai_data = next((item for item in ai_analysis if item.get("symbol") == tech["symbol"]), None)
        if ai_data:
            tech.update(ai_data)
        else:
            tech['trend'] = 'Neutral'
            tech['suggestion'] = 'HOLD'
            tech['ai_reason'] = 'Analyzing market context based on previous close and opening volume.'
        final_results.append(tech)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if is_market_close:
        subject = f"🚨 DAILY MARKET WRAP-UP & TOMORROW'S STRATEGY - {now}"
        title = "📊 Market Close Comprehensive Review & Next-Day Strategy"
    else:
        subject = f"PRO Market Intelligence: Intraday Alert - {now}"
        title = "🤖 Sequential & Previous-Day Context Intraday Report"

    html = f"""
    <html>
    <head>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 14px; box-shadow: 0 0 20px rgba(0, 0, 0, 0.1); }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
            th {{ background-color: #1a252f; color: #ffffff; text-transform: uppercase; font-size: 13px; }}
            tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .buy {{ color: #27ae60; font-weight: bold; }}
            .sell {{ color: #c0392b; font-weight: bold; }}
            .hold {{ color: #7f8c8d; font-weight: bold; }}
            .avg {{ color: #2980b9; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">{title}</h2>
        <p style="color: #555;"><b>Time:</b> {now}</p>
        <table>
            <tr>
                <th>Stock</th>
                <th>Price (₹)</th>
                <th>RSI (14)</th>
                <th>Trend</th>
                <th>Action / Suggestion</th>
                <th>{'Tomorrow Strategy & Wrap-up' if is_market_close else 'Context & Sequential Analysis'}</th>
            </tr>
    """

    for res in final_results:
        sug = res.get('suggestion', 'HOLD').upper()
        color_class = "hold"
        if "BUY" in sug or "ACCUMULATE" in sug: color_class = "buy"
        elif "SELL" in sug: color_class = "sell"
        elif "AVERAGE" in sug: color_class = "avg"

        html += f"""
            <tr>
                <td><b>{res['symbol']}</b></td>
                <td><b>{res['price']}</b></td>
                <td>{res['rsi']}</td>
                <td>{res.get('trend', 'Neutral')}</td>
                <td class="{color_class}">{sug}</td>
                <td style="font-size: 13px; color: #333; line-height: 1.4;">{res.get('ai_reason', 'Analysis pending.')}</td>
            </tr>
        """
    
    html += f"</table><br><p style='font-size: 12px; color: #999;'>Happy Trading! - <i>Powered by Gemini 3.6 Flash & Market Agent Pro</i></p></body></html>"

    msg = MIMEMultipart()
    msg['From'] = GMAIL_SENDER
    msg['To'] = GMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    print("Fetching stocks from Google Sheets...")
    stocks = get_stocks_from_sheet()
    
    if not stocks:
        stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
        
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    is_market_close = (current_hour == 10 and current_minute >= 0)
    
    print(f"Mode: {'Market Close Wrap-up' if is_market_close else 'Intraday with Previous-Day & Sequential Context'}")
    
    tech_data = get_technical_data(stocks, is_market_close=is_market_close)
    
    if tech_data:
        ai_results = get_ai_analysis(tech_data, is_market_close=is_market_close)
        send_email(tech_data, ai_results, is_market_close=is_market_close)
    else:
        print("No technical data found.")
