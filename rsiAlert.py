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
# 4. Calculate RSI and Signals
# -----------------------------
data["RSI"] = ta.rsi(close=close_prices, length=RSI_PERIOD)
data["RSI"] = data["RSI"].astype(float)

data["Signal"] = "HOLD"
data.loc[data["RSI"] < BUY_THRESHOLD, "Signal"] = "BUY"
data.loc[data["RSI"] > SELL_THRESHOLD, "Signal"] = "SELL"

# -----------------------------
# 5. Backtest
# -----------------------------
capital = INITIAL_CAPITAL
position = 0
trade_log = []

for i in range(len(data)):
    price = close_prices.iloc[i]
    signal = data["Signal"].iloc[i]

    if signal == "BUY" and position == 0:
        position = capital / price
        capital = 0
        trade_log.append(("BUY", data.index[i], price))
    elif signal == "SELL" and position > 0:
        capital = position * price
        position = 0
        trade_log.append(("SELL", data.index[i], price))

if position > 0:
    capital = position * close_prices.iloc[-1]
    trade_log.append(("SELL (End)", data.index[-1], close_prices.iloc[-1]))

# -----------------------------
# 6. Plot
# -----------------------------
plt.figure(figsize=(12,8))

plt.subplot(2,1,1)
plt.plot(data.index, close_prices, label="Gold Price", color="blue")
for action, date, price in trade_log:
    if "BUY" in action:
        plt.scatter(date, price, marker="^", color="green", s=100)
    else:
        plt.scatter(date, price, marker="v", color="red", s=100)
plt.title("Gold ETF RSI Strategy Backtest")
plt.ylabel("Price (₹)")
plt.legend(loc="upper left")

plt.subplot(2,1,2)
plt.plot(data.index, data["RSI"], label="RSI", color="purple")
plt.axhline(BUY_THRESHOLD, linestyle="--", color="green", alpha=0.5)
plt.axhline(SELL_THRESHOLD, linestyle="--", color="red", alpha=0.5)
plt.title("RSI Indicator")
plt.ylabel("RSI Value")
plt.xlabel("Date")
plt.legend(loc="upper left")

plt.tight_layout()
plot_file = "RSI_Plot.png"
plt.savefig(plot_file)

# -----------------------------
# 7. Daily Email Alert
# -----------------------------
latest_rsi = data["RSI"].iloc[-1]
latest_price = close_prices.iloc[-1]
today_signal = "HOLD"

if latest_rsi < BUY_THRESHOLD:
    today_signal = "BUY"
elif latest_rsi > SELL_THRESHOLD:
    today_signal = "SELL"

alert_subject = f"{ETF_TICKER} Alert: {today_signal}"
alert_body = f"""
Gold ETF: {ETF_TICKER}
Signal: {today_signal}
Price: {latest_price:.2f}
RSI: {latest_rsi:.2f}
"""

print(alert_body)

if EMAIL_ALERT and today_signal in ["BUY", "SELL"]:
    send_email_alert(alert_subject, alert_body, image_path=plot_file)
