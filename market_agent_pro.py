
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import feedparser
from google import genai
from nsepython import nse_get_top_gainers, nse_get_top_losers

# 1. API കോൺഫിഗറേഷൻ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "YOUR_GMAIL_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "recipient_email@gmail.com")

client = genai.Client(api_key=GEMINI_API_KEY)

# 2. BSE കോർപ്പറേറ്റ് റിസൾട്ടുകളും അനൗൺസ്‌മെന്റുകളും നേരിട്ട് എടുക്കൽ
def get_bse_announcements():
    url = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Result&strPrevDate=&strScrip=&strSearch=P&strToDate=&strType=C"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bseindia.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        announcements = []
        
        # ഏറ്റവും പുതിയ 10 റിസൾട്ട് അനൗൺസ്‌മെന്റുകൾ
        for item in data.get("Table", [])[:10]:
            company = item.get("SLONGNAME", "Unknown")
            headline = item.get("NEWSSUB", "")
            announcements.append(f"• **{company}**: {headline}")
            
        return "\n".join(announcements) if announcements else "ഇന്നത്തെ റിസൾട്ടുകൾ ലഭ്യമല്ല."
    except Exception as e:
        return f"BSE ഡാറ്റ എടുക്കുന്നതിൽ തടസ്സം: {str(e)}"

# 3. NSE മാർക്കറ്റ് ഡാറ്റ (Gainers/Losers/Circuits)
def get_market_data():
    try:
        gainers = nse_get_top_gainers()
        losers = nse_get_top_losers()
        
        top_gainers = [
            f"{s['symbol']}: ₹{s['netPrice']} (+{s['pChange']}%)" 
            for s in gainers.get('data', [])[:6]
        ]
        top_losers = [
            f"{s['symbol']}: ₹{s['netPrice']} ({s['pChange']}%)" 
            for s in losers.get('data', [])[:6]
        ]
        return "\n".join(top_gainers), "\n".join(top_losers)
    except Exception:
        return "ഡാറ്റ ലഭ്യമല്ല", "ഡാറ്റ ലഭ്യമല്ല"

# 4. ബിസിനസ്സ് ന്യൂസ് ഫീഡ് (Google News RSS)
def get_market_news():
    rss_url = "https://news.google.com/rss/search?q=Indian+stock+market+OR+Nifty+OR+Sensex&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    return "\n".join([f"- {entry.title}" for entry in feed.entries[:8]])

# 5. ജെമിനി വഴി HTML റിപ്പോർട്ട് നിർമ്മിക്കൽ
def generate_html_report(gainers, losers, bse_results, news):
    prompt = f"""
    നിങ്ങൾ ഒരു പ്രൊഫഷണൽ സ്റ്റോക്ക് മാർക്കറ്റ് അനലിസ്റ്റാണ്. താഴെ നൽകിയിരിക്കുന്ന ഡാറ്റ വിശകലനം ചെയ്ത് പ്രൊഫഷണൽ ലുക്കുള്ള മനോഹരമായ ഒരു **HTML ഇമെയിൽ ബോഡി** നിർമ്മിക്കുക. 

    **നിർദ്ദേശങ്ങൾ:**
    - ഭാഷ: മലയാളം (സാങ്കേതിക പദങ്ങൾ ബ്രാക്കറ്റിൽ ഇംഗ്ലീഷിലും നൽകാം).
    - റെസ്പോൺസീവ് ആയ വൃത്തിയുള്ള ഇൻലൈൻ CSS സ്റ്റൈലിംഗ് ഉപയോഗിക്കുക (Modern Card Layout, Gradient Header, Clean Tables, Dark/Light accents).
    - ```html ... ``` ടാഗിനുള്ളിൽ മാത്രം കോഡ് നൽകുക.

    **ഇന്നത്തെ ഡാറ്റ:**
    1. BSE Corporate Results & Announcements:
    {bse_results}

    2. Top Gainers & Momentum (>5%):
    {gainers}

    3. Top Losers / Circuit Stocks:
    {losers}

    4. Top Financial News:
    {news}

    **HTML ലേഔട്ടിൽ ഉൾപ്പെടുത്തേണ്ട വിഭാഗങ്ങൾ:**
    - ഹെഡർ (ഇന്നത്തെ തീയതിയും തലക്കെട്ടും)
    - മാർക്കറ്റ് സംഗ്രഹം (Executive Summary)
    - പ്രധാന കമ്പനി റിസൾട്ടുകൾ (BSE Results Highlights)
    - Top Gainers & Losers (മനോഹരമായ ടേബിൾ അല്ലെങ്കിൽ ഗ്രിഡ് കാർഡുകൾ)
    - പ്രധാന മാർക്കറ്റ് വാർത്തകൾ
    - നിക്ഷേപകർക്കുള്ള മുന്നറിയിപ്പ് (Disclaimer)
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    # മാർക്ക്ഡൗൺ കോഡ് ബ്ലോക്കുകൾ നീക്കം ചെയ്ത് ശുദ്ധമായ HTML എടുക്കുന്നു
    html_content = response.text.replace("```html", "").replace("```", "").strip()
    return html_content

# 6. HTML ഇമെയിൽ അയക്കൽ
def send_html_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    # HTML ഉള്ളടക്കം അറ്റാച്ച് ചെയ്യുന്നു
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# മെയിൻ എക്സിക്യൂഷൻ
if __name__ == "__main__":
    print("1. ഡാറ്റ ശേഖരിക്കുന്നു...")
    bse_res = get_bse_announcements()
    gainers, losers = get_market_data()
    news = get_market_news()

    print("2. ജെമിനി വഴി HTML റിപ്പോർട്ട് തയ്യാറാക്കുന്നു...")
    html_report = generate_html_report(gainers, losers, bse_res, news)

    print("3. ഇമെയിൽ അയക്കുന്നു...")
    send_html_email("📈 ഡെയ്‌ലി മാർക്കറ്റ് ബുള്ളറ്റിൻ: BSE റിസൾട്ടുകളും അനാലിസിസും", html_report)
    print("വിജയകരമായി മെയിൽ അയച്ചു!")
