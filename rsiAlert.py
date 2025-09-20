import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import matplotlib.pyplot as plt
import pandas_ta as ta
import yfinance as yf

# --------------------------
# CONFIG
# --------------------------
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO").split(",")  # multiple recipients comma-separated
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

TICKER = "GOLDBEES.NS"
START_DATE = "2022-01-01"

# --------------------------
# FETCH DATA
# --------------------------
data = yf.download(TICKER, start=START_DATE, interval="1d")
data = data.dropna()

# Indicators
data["RSI"] = ta.rsi(data["Close"], length=14)
data["EMA9"] = ta.ema(data["Close"], length=9)
data["EMA21"] = ta.ema(data["Close"], length=21)
macd = ta.macd(data["Close"], fast=12, slow=26, signal=9)
data["MACD"] = macd["MACD_12_26_9"]
data["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

# --------------------------
# SIGNAL GENERATION
# --------------------------
latest = data.iloc[-1]

signals = []

# RSI
if latest["RSI"] < 30:
    signals.append("RSI → BUY (oversold)")
elif latest["RSI"] > 70:
    signals.append("RSI → SELL (overbought)")
else:
    signals.append("RSI → HOLD")

# EMA crossover
if latest["EMA9"] > latest["EMA21"]:
    signals.append("EMA Crossover → BULLISH (9 > 21)")
else:
    signals.append("EMA Crossover → BEARISH (9 < 21)")

# MACD
if latest["MACD"] > latest["MACD_SIGNAL"]:
    signals.append("MACD → BULLISH (MACD > Signal)")
else:
    signals.append("MACD → BEARISH (MACD < Signal)")

alert_body = f"""
Ticker: {TICKER}
Date: {latest.name.date()}

Signals:
- {signals[0]}
- {signals[1]}
- {signals[2]}

Latest Price: {latest['Close']:.2f}
"""

# --------------------------
# PLOT
# --------------------------
plt.figure(figsize=(10,6))
plt.plot(data.index, data["Close"], label="Close Price", color="blue")
plt.plot(data.index, data["EMA9"], label="EMA 9", color="green")
plt.plot(data.index, data["EMA21"], label="EMA 21", color="red")
plt.title(f"{TICKER} Price with EMA (9, 21)")
plt.legend()
plot_file = "chart.png"
plt.savefig(plot_file)
plt.close()

# --------------------------
# EMAIL FUNCTION
# --------------------------
def send_email_alert(subject, body, image_path=None):
    msg = MIMEMultipart()
    msg["From"] = f"Gold ETF Alerts <{EMAIL_FROM}>"
    msg["To"] = ", ".join(EMAIL_TO)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    if image_path:
        with open(image_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(image_path)}")
        msg.attach(part)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Email alert sent!")

# --------------------------
# SEND ALERT
# --------------------------
alert_subject = f"{TICKER} Trading Signals"
send_email_alert(alert_subject, alert_body, image_path=plot_file)
