import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import yfinance as yf
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from ta.momentum import RSIIndicator
from ta.trend import MACD
import google.generativeai as genai

# GitHub Secrets-ൽ നിന്നുള്ള പഴയ ഡാറ്റകൾ തന്നെ ഉപയോഗിക്കുന്നു
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

# നിങ്ങളുടെ ഗൂഗിൾ ഡ്രൈവിലെ ഷീറ്റിന്റെ പേര് ഇവിടെ കൃത്യമായി നൽകുക
SHEET_NAME = "shares" 

# AI കോൺഫിഗറേഷൻ
genai.configure(api_key=GEMINI_API_KEY)

def get_stocks_from_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_values()
        
        # ആദ്യ കോളം സ്റ്റോക്ക് സിംബൽ ആണ് (Header ഒഴിവാക്കുന്നു)
        stocks = [row[0] for row in records[1:] if row[0].strip() != ""]
        return stocks
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return []

def get_technical_data(stocks):
    technical_data = []
    for symbol in stocks:
        try:
            # യാഹൂ ഫിനാൻസിനായി .NS ചേർക്കുന്നു
            ticker = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
            df = yf.download(ticker, period="5d", interval="30m", progress=False)
            
            if df.empty or len(df) < 20:
                continue

            df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
            macd = MACD(close=df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            current_price = last_candle['Close']
            current_volume = last_candle['Volume']
            avg_volume = df['Volume'].rolling(window=10).mean().iloc[-1]
            
            technical_data.append({
                "symbol": symbol,
                "price": round(current_price, 2),
                "rsi": round(last_candle['RSI'], 2),
                "macd": round(last_candle['MACD'], 2),
                "macd_signal": round(last_candle['MACD_Signal'], 2),
                "volume": int(current_volume),
                "avg_volume": int(avg_volume),
                "price_change": round(current_price - prev_candle['Close'], 2)
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            
    return technical_data

def get_ai_analysis(technical_data):
    if not technical_data:
        return []
    
    print("Asking AI for Market Analysis...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert intraday and short-term stock market technical analyst.
    Analyze the following 30-minute timeframe technical data for Indian stocks:
    {json.dumps(technical_data)}
    
    Based on Price action, RSI, MACD, and Volume crossover, provide a detailed analysis for EACH stock.
    Return the response strictly as a JSON array of objects with the following keys:
    - symbol: The stock symbol.
    - trend: "Bullish", "Bearish", or "Neutral".
    - suggestion: Choose one from ["BUY", "SELL", "HOLD", "BUY ON DIP", "AVERAGE"].
    - ai_reason: A sharp 2-sentence explanation of WHY this suggestion is given based on the provided technicals (mention RSI/Volume/MACD).
    
    Do not output any markdown formatting or extra text, just the raw JSON array.
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        ai_results = json.loads(cleaned_response)
        return ai_results
    except Exception as e:
        print(f"AI Analysis Failed: {e}")
        return []

def send_email(technical_data, ai_analysis):
    if not technical_data:
        print("No data to send.")
        return

    final_results = []
    for tech in technical_data:
        ai_data = next((item for item in ai_analysis if item["symbol"] == tech["symbol"]), None)
        if ai_data:
            tech.update(ai_data)
            final_results.append(tech)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"AI Market Intelligence: 30-Min Alert - {now}"

    html = f"""
    <html>
    <head>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 14px; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 10px; }}
            th {{ background-color: #f4f4f4; color: #333; }}
            .buy {{ color: green; font-weight: bold; }}
            .sell {{ color: red; font-weight: bold; }}
            .hold {{ color: gray; font-weight: bold; }}
            .avg {{ color: #007bff; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2 style="color: #2c3e50;">🤖 AI Market Intelligence Report (30-Min Timeframe)</h2>
        <p><b>Time:</b> {now}</p>
        <table>
            <tr>
                <th>Stock</th>
                <th>Price (₹)</th>
                <th>RSI</th>
                <th>AI Trend</th>
                <th>AI Suggestion</th>
                <th>AI Expert Analysis</th>
            </tr>
    """

    for res in final_results:
        sug = res.get('suggestion', 'HOLD').upper()
        color_class = "hold"
        if "BUY" in sug: color_class = "buy"
        elif "SELL" in sug: color_class = "sell"
        elif "AVERAGE" in sug: color_class = "avg"

        html += f"""
            <tr>
                <td><b>{res['symbol']}</b></td>
                <td>{res['price']}</td>
                <td>{res['rsi']}</td>
                <td>{res.get('trend', 'Neutral')}</td>
                <td class="{color_class}">{sug}</td>
                <td style="font-size: 13px; color: #555;">{res.get('ai_reason', 'Analysis pending.')}</td>
            </tr>
        """
    
    html += "</table><br><p>Happy Trading! - <i>Powered by Gemini AI & Market Agent Pro</i></p></body></html>"

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
        print("AI Intelligence Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    print("Fetching stocks from Google Sheets...")
    stocks = get_stocks_from_sheet()
    
    if not stocks:
        stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
        
    print(f"Calculating Technical Data for {len(stocks)} stocks...")
    tech_data = get_technical_data(stocks)
    
    if tech_data:
        ai_results = get_ai_analysis(tech_data)
        send_email(tech_data, ai_results)
    else:
        print("No technical data found.")
