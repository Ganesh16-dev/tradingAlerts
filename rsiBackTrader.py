import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

# -----------------------------
st.set_page_config(layout="wide", page_title="Gold ETF Dashboard")
st.title("Gold ETF Strategy (RSI + EMA + MACD)")

ETF_TICKER = "GOLDETF.NS"
RSI_PERIOD = 14
BUY_THRESHOLD = 30
SELL_THRESHOLD = 70

# -----------------------------
# 1. Fetch data
data_raw = yf.download(ETF_TICKER, start="2022-01-01", interval="1d", auto_adjust=False)
if data_raw.empty:
    st.error("No data downloaded")
    st.stop()

# -----------------------------
# 2. Extract close prices and create a simple DataFrame
if isinstance(data_raw.columns, pd.MultiIndex):
    close_prices = data_raw[("Close", ETF_TICKER)]
else:
    close_prices = data_raw["Close"]

df = pd.DataFrame({"Close": pd.to_numeric(close_prices, errors="coerce")})
df.dropna(subset=["Close"], inplace=True)

# -----------------------------
# 3. Calculate indicators
df["RSI"] = ta.rsi(df["Close"], length=RSI_PERIOD)
df["EMA9"] = ta.ema(df["Close"], length=9)
df["EMA21"] = ta.ema(df["Close"], length=21)

macd = ta.macd(df["Close"])
if macd is not None:
    df["MACD"] = macd.get("MACD_12_26_9")
    df["MACD_SIGNAL"] = macd.get("MACDs_12_26_9")
else:
    df["MACD"] = pd.Series([None]*len(df))
    df["MACD_SIGNAL"] = pd.Series([None]*len(df))

# Drop rows where any indicator is NaN
df.dropna(subset=["RSI", "EMA9", "EMA21", "MACD", "MACD_SIGNAL"], inplace=True)

# -----------------------------
# 4. Latest signals
latest = df.iloc[-1]
rsi_signal = "BUY" if latest.RSI < BUY_THRESHOLD else "SELL" if latest.RSI > SELL_THRESHOLD else "HOLD"
ema_signal = "BUY" if latest.EMA9 > latest.EMA21 else "SELL"
macd_signal = "BUY" if latest.MACD > latest.MACD_SIGNAL else "SELL"

signals = [rsi_signal, ema_signal, macd_signal]

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
# Beautify latest signal output
st.subheader("Latest Signals (Gold ETF)")

signal_data = {
    "Price (₹)": f"{latest.Close:.2f}",
    "RSI": f"{latest.RSI:.2f}",
    "RSI Signal": rsi_signal + (" 🔻" if rsi_signal=="SELL" else " 🟢" if rsi_signal=="BUY" else " ⚪"),
    "EMA9": f"{latest.EMA9:.2f}",
    "EMA21": f"{latest.EMA21:.2f}",
    "EMA Signal": ema_signal + (" 🔻" if ema_signal=="SELL" else " 🟢"),
    "MACD": f"{latest.MACD:.4f}",
    "MACD Signal": macd_signal + (" 🔻" if macd_signal=="SELL" else " 🟢"),
    "Overall Signal": overall_signal
}

st.markdown(
    f"""
    **Price:** {signal_data['Price (₹)']}  
    **RSI:** {signal_data['RSI']} → {signal_data['RSI Signal']}  
    **EMA9 / EMA21:** {signal_data['EMA9']} / {signal_data['EMA21']} → {signal_data['EMA Signal']}  
    **MACD:** {signal_data['MACD']} → {signal_data['MACD Signal']}  
    **Overall Signal:** **{signal_data['Overall Signal']}**
    """,
    unsafe_allow_html=True
)

# -----------------------------
# 5. Plot
fig, ax = plt.subplots(3,1, figsize=(14,10), sharex=True)

ax[0].plot(df.index, df["Close"], label="Gold Price", color="blue")
ax[0].plot(df.index, df["EMA9"], label="EMA9", color="orange")
ax[0].plot(df.index, df["EMA21"], label="EMA21", color="red")
ax[0].set_title("Gold ETF Price with EMA")
ax[0].legend(loc="upper left")

ax[1].plot(df.index, df["RSI"], label="RSI", color="purple")
ax[1].axhline(BUY_THRESHOLD, linestyle="--", color="green", alpha=0.5)
ax[1].axhline(SELL_THRESHOLD, linestyle="--", color="red", alpha=0.5)
ax[1].set_title("RSI Indicator")
ax[1].legend(loc="upper left")

ax[2].plot(df.index, df["MACD"], label="MACD", color="blue")
ax[2].plot(df.index, df["MACD_SIGNAL"], label="Signal Line", color="red")
ax[2].axhline(0, linestyle="--", color="black", alpha=0.5)
ax[2].set_title("MACD Indicator")
ax[2].legend(loc="upper left")

plt.tight_layout()
st.pyplot(fig)

# -----------------------------
# 6. Show last 10 rows
st.subheader("Recent Data")
st.dataframe(df.tail(10))
