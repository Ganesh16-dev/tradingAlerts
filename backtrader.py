import backtrader as bt
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# 1. Define the RSI Strategy
class RSIStrategy(bt.Strategy):
    params = (("rsi_period", 14), ("rsi_low", 30), ("rsi_high", 70), ("printlog", False))

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt}: {txt}")

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.order = None
        self.buyprice = None
        self.trades = []

    def next(self):
        if self.order:
            return  # pending order

        if not self.position:
            if self.rsi < self.params.rsi_low:
                self.order = self.buy()
                self.log(f"BUY at {self.data.close[0]:.2f}")
        else:
            if self.rsi > self.params.rsi_high:
                self.order = self.sell()
                self.log(f"SELL at {self.data.close[0]:.2f}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.trades.append(("BUY", self.datas[0].datetime.date(0), self.buyprice))
            elif order.issell():
                sell_price = order.executed.price
                self.trades.append(("SELL", self.datas[0].datetime.date(0), sell_price))
            self.order = None

# 2. Download GLD data
df = yf.download("GLD", start="2022-01-01")
data = bt.feeds.PandasData(dataname=df)

# 3. Initialize Backtrader
cerebro = bt.Cerebro()
cerebro.addstrategy(RSIStrategy)
cerebro.adddata(data)
cerebro.broker.setcash(10000)
cerebro.broker.setcommission(commission=0.001)

# 4. Run backtest
print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())
results = cerebro.run()
final_value = cerebro.broker.getvalue()
print("Final Portfolio Value: %.2f" % final_value)

# 5. Print Trade Stats
strategy = results[0]
buy_trades = [t for t in strategy.trades if t[0]=="BUY"]
sell_trades = [t for t in strategy.trades if "SELL" in t[0]]

print("Total Trades:", len(sell_trades))
profits = [(sell_trades[i][2] - buy_trades[i][2]) for i in range(len(sell_trades))]
wins = len([p for p in profits if p > 0])
losses = len([p for p in profits if p <= 0])
win_rate = (wins / len(profits)) * 100 if profits else 0

print("Wins:", wins, "Losses:", losses, "Win Rate: %.2f%%" % win_rate)
print("Average Profit/Loss per Trade:", round(sum(profits)/len(profits),2) if profits else 0)

# 6. Plot Equity Curve
equity = cerebro.broker.getvalue()
cerebro.plot(style='candlestick')
