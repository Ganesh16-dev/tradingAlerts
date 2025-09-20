import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os

# -----------------------------
# 1. Configuration
# -----------------------------
ETF_TICKER = "GOLDETF.NS"
RSI_PERIOD = 14
BUY_THRESHOLD = 30
SELL_THRESHOLD = 70
INITIAL_CAPITAL = 10000

# Email config from environment (GitHub Secrets)
EMAIL_ALERT = True
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")  # Comma-separated string of emails
SENDER_NAME = "Gold ETF Alerts"

# Convert comma-separated string to list
recipient_list = [email.strip() for email in EMAIL_TO.split(",")]

# -----------------------------
# 2. Email alert function with inline image
# -----------------------------
def send_email_alert(subject, body, image_path=None):
    msg = MIMEMultipart("related")
    msg['From'] = f"{SENDER_NAME} <{EMAIL_FROM}>"
    msg['To'] = ", ".join(recipient_list)
    msg['Subject'] = subject

    html_body = f"""
    <html>
        <body>
            <pre>{body}</pre>
            {f'<img src="cid:chart_image">' if image_path else ''}
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    if image_path:
        with open(image_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<chart_image>')
            msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Email alert sent to:", recipient_list)

# -----------------------------
# 3. Fetch historical data
# -----------------------------
data = yf.download(ETF_TICKER, start="2022-01-01", interval="1d", auto_adjust=False)
if data.empty:
    raise ValueError("No data downloaded")

if isinstance(data.columns, pd.MultiIndex):
    close_prices = data[("Close", ETF_TICKER)]
else:
    close_prices = data["Close"]

close_prices = pd.to_numeric(close_prices, errors="coerce")

# -----------------------------
# 4. Calculate Indicators
# -----------------------------
# RSI
data["RSI"] = ta.rsi(close=close_prices, length=RSI_PERIOD)

# EMA
data["EMA9"] = ta.ema(close=close_prices, length=9)
data["EMA21"] = ta.ema(close=close_prices, length=21)

# MACD
macd = ta.macd(close=close_prices, fast=12, slow=26, signal=9)
if macd is not None:
    data["MACD"] = macd["MACD_12_26_9"]
    data["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

# -----------------------------
# 5. Combined Daily Signal
# -----------------------------
latest_rsi = data["RSI"].iloc[-1]
latest_price = close_prices.iloc[-1]
latest_ema9 = data["EMA9"].iloc[-1]
latest_ema21 = data["EMA21"].iloc[-1]
latest_macd = data["MACD"].iloc[-1]
latest_signal_line = data["MACD_SIGNAL"].iloc[-1]

# Individual signals
rsi_signal = "BUY" if latest_rsi < BUY_THRESHOLD else "SELL" if latest_rsi > SELL_THRESHOLD else "HOLD"
ema_signal = "BUY" if latest_ema9 > latest_ema21 else "SELL"
macd_signal = "BUY" if latest_macd > latest_signal_line else "SELL"

signals = [rsi_signal, ema_signal, macd_signal]

# Overall decision
if signals.count("BUY") == 3:
    overall_signal = "SURE-SHOT BUY 🚀"
elif signals.count("BUY") == 2:
    overall_signal = "BUY"
elif signals.count("SELL") == 3:
    overall_signal = "SURE-SHOT SELL 🔻"
elif signals.count("SELL") == 2:
    overall_signal = "SELL"
else:
    overall_signal = "HOLD"

# -----------------------------
# 6. Plot
# -----------------------------
plt.figure(figsize=(14,10))

# Price with EMA
plt.subplot(3,1,1)
plt.plot(data.index, close_prices, label="Gold Price", color="blue")
plt.plot(data.index, data["EMA9"], label="EMA 9", color="orange")
plt.plot(data.index, data["EMA21"], label="EMA 21", color="red")
plt.title("Gold ETF with EMA")
plt.ylabel("Price (₹)")
plt.legend(loc="upper left")

# RSI
plt.subplot(3,1,2)
plt.plot(data.index, data["RSI"], label="RSI", color="purple")
plt.axhline(BUY_THRESHOLD, linestyle="--", color="green", alpha=0.5)
plt.axhline(SELL_THRESHOLD, linestyle="--", color="red", alpha=0.5)
plt.title("RSI Indicator")
plt.ylabel("RSI Value")
plt.legend(loc="upper left")

# MACD
plt.subplot(3,1,3)
plt.plot(data.index, data["MACD"], label="MACD", color="blue")
plt.plot(data.index, data["MACD_SIGNAL"], label="Signal Line", color="red")
plt.axhline(0, linestyle="--", color="black", alpha=0.5)
plt.title("MACD Indicator")
plt.ylabel("MACD")
plt.xlabel("Date")
plt.legend(loc="upper left")

plt.tight_layout()
plot_file = "Indicators_Plot.png"
plt.savefig(plot_file)

# -----------------------------
# 7. Detailed Report
# -----------------------------
alert_subject = f"{ETF_TICKER} Alert: {overall_signal}"
alert_body = f"""
Gold ETF: {ETF_TICKER}
Price: {latest_price:.2f}

🔎 Indicator Summary:
- RSI: {latest_rsi:.2f} → {rsi_signal}
- EMA9: {latest_ema9:.2f}, EMA21: {latest_ema21:.2f} → {ema_signal}
- MACD: {latest_macd:.2f}, Signal: {latest_signal_line:.2f} → {macd_signal}

✅ Overall Signal: {overall_signal}
"""

print(alert_body)

if EMAIL_ALERT and overall_signal not in ["HOLD"]:
    send_email_alert(alert_subject, alert_body, image_path=plot_file)
