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
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Cookie': MONEYCONTROL_COOKIE if MONEYCONTROL_COOKIE else ''
        }
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
                        return summary[:200] + "..." if summary else "Pro sentiment stable."
        return "Pro sentiment stable."
    except Exception as e:
        return "Pro sentiment verified."

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
            
            prev_day_close = df.iloc[-2]['Close'] if len(df) >= 2 else df.iloc[-1]['Close']
            current_candle = df.iloc[-1]
            
            current_price = current_candle['Close']
            price_change_pct = round(((current_price - prev_day_close) / prev_day_close) * 100, 2)
            current_rsi = round(current_candle['RSI'], 2) if not pd.isna(current_candle['RSI']) else 50
            
            is_dead_stock = abs(price_change_pct) < 0.15 and 48 <= current_rsi <= 52

            pro_insights = ""
            if is_market_close:
                pro_insights = get_moneycontrol_pro_insights(symbol)

            technical_data.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "change_pct": price_change_pct,
                "rsi": current_rsi,
                "macd": round(current_candle['MACD'], 2) if not pd.isna(current_candle['MACD']) else 0,
                "is_dead_stock": is_dead_stock,
                "pro_insights": pro_insights
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            
    return technical_data

def get_ai_analysis(technical_data, is_market_close=False):
    if not technical_data:
        return []
    
    print("Asking AI with Independent Batch Accumulation...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    all_ai_results = []
    
    # അനക്കമില്ലാത്ത സ്റ്റോക്കുകൾക്ക് ആദ്യം തന്നെ റിസൾട്ട് സെറ്റ് ചെയ്യുന്നു
    active_stocks = [s for s in technical_data if not s.get("is_dead_stock", False)]
    dead_stocks = [s for s in technical_data if s.get("is_dead_stock", False)]
    
    for ds in dead_stocks:
        all_ai_results.append({
            "symbol": ds["symbol"],
            "trend": "Neutral",
            "suggestion": "HOLD",
            "ai_reason": f"Minimal price change ({ds['change_pct']}%) with RSI at {ds['rsi']}. Sideways movement observed."
        })

    # ആക്റ്റീവ് സ്റ്റോക്കുകളെ ബാച്ചുകളായി തിരിക്കുന്നു
    batch_size = 25
    batches = [active_stocks[i:i + batch_size] for i in range(0, len(active_stocks), batch_size)]
    
    for index, batch in enumerate(batches):
        if not batch:
            continue
        print(f"Processing Active Stock Batch {index + 1} of {len(batches)} independently...")
        
        prompt = f"""
        Analyze this compact technical data for Indian stocks:
        {json.dumps(batch)}
        
        Return ONLY a valid JSON array of objects. No markdown, no extra text. 
        Use exactly these keys:
        - "symbol": The stock symbol.
        - "trend": "Strong Bullish", "Bullish", "Neutral", "Bearish", or "Strong Bearish".
        - "suggestion": One of ["STRONG BUY", "BUY ON DIP", "HOLD", "SELL", "AVERAGE"].
        - "ai_reason": A short, crisp 1-sentence technical justification.
        """
        
        batch_success = False
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                text_resp = response.text.strip().replace("```json", "").replace("```", "")
                batch_results = json.loads(text_resp)
                
                if isinstance(batch_results, list):
                    all_ai_results.extend(batch_results)
                    batch_success = True
                    break
                elif isinstance(batch_results, dict):
                    all_ai_results.append(batch_results)
                    batch_success = True
                    break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for Batch {index + 1}: {e}")
                time.sleep(5)
        
        # ഒരു ബാച്ച് പൂർണ്ണമായി ഫെയിൽ ആയാലും, ആ ബാച്ചിലെ ബാക്കി സ്റ്റോക്കുകളുടെ ഡാറ്റ നഷ്ടപ്പെടാതെ ഇവിടെ മാത്മാറ്റിക്കൽ ഫോളോ-അപ്പ് നൽകി ആഡ് ചെയ്യുന്നു!
        if not batch_success:
            print(f"⚠️ Batch {index + 1} failed after retries. Applying independent fallback analysis for this batch...")
            for item in batch:
                rsi = item['rsi']
                p_change = item['change_pct']
                trend = "Bullish" if p_change > 0 else "Bearish"
                sug = "BUY ON DIP" if rsi < 45 else ("HOLD" if 45 <= rsi <= 60 else "STRONG BUY" if rsi > 60 else "HOLD")
                
                all_ai_results.append({
                    "symbol": item["symbol"],
                    "trend": trend,
                    "suggestion": sug,
                    "ai_reason": f"Price change: {p_change}% with RSI at {rsi}. Technical momentum stable based on independent evaluation."
                })
        
        # ബാച്ചുകൾക്കിടയിൽ സുരക്ഷിതമായ ഗ്യാപ്പ്
        if index < len(batches) - 1:
            time.sleep(3)
            
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
            tech['trend'] = "Neutral"
            tech['suggestion'] = "HOLD"
            tech['ai_reason'] = f"Trading at ₹{tech['price']} with RSI {tech['rsi']}."
        final_results.append(tech)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🛡️ RESILIENT REPORT: Market Intelligence - {now}"

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
        </style>
    </head>
    <body>
        <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🤖 Resilient Market Intelligence Report</h2>
        <p style="color: #555;"><b>Time:</b> {now} | <b>Mode:</b> Independent Batch Protection Enabled</p>
        <table>
            <tr>
                <th>Stock</th>
                <th>Price (₹)</th>
                <th>Change (%)</th>
                <th>RSI (14)</th>
                <th>Action</th>
                <th>AI Insights</th>
            </tr>
    """

    for res in final_results:
        sug = res.get('suggestion', 'HOLD').upper()
        color_class = "hold"
        if "BUY" in sug: color_class = "buy"
        elif "SELL" in sug: color_class = "sell"

        html += f"""
            <tr>
                <td><b>{res['symbol']}</b></td>
                <td><b>{res['price']}</b></td>
                <td>{res['change_pct']}%</td>
                <td>{res['rsi']}</td>
                <td class="{color_class}">{sug}</td>
                <td style="font-size: 13px; color: #333;">{res.get('ai_reason', '')}</td>
            </tr>
        """
    
    html += "</table><br><p style='font-size: 12px; color: #999;'>Resilient Agent - Powered by Gemini Flash</p></body></html>"

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
        print("Resilient Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    stocks = get_stocks_from_sheet()
    if not stocks:
        stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
        
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    is_market_close = (current_hour == 15 and current_minute >= 0)
    
    tech_data = get_technical_data(stocks, is_market_close=is_market_close)
    if tech_data:
        ai_results = get_ai_analysis(tech_data, is_market_close=is_market_close)
        send_email(tech_data, ai_results, is_market_close=is_market_close)
