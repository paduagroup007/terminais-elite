import yfinance as yf
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_ticker(symbol):
    print(f"\n=================== TESTING {symbol} ===================")
    ticker = yf.Ticker(symbol)
    
    # Financials
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow
    
    print("Financials Keys:")
    print([k for k in fin.index if "Revenue" in k or "Income" in k or "EBITDA" in k])
    
    print("\nBalance Sheet Keys:")
    print([k for k in bs.index if "Equity" in k or "Asset" in k or "Liabilit" in k or "Debt" in k or "Capital" in k or "Earnings" in k])
    
    print("\nCash Flow Keys:")
    print([k for k in cf.index if "Flow" in k or "Cash" in k])

def main():
    test_ticker("AAPL")
    test_ticker("MSFT")
    test_ticker("TSLA")
    test_ticker("JPM")  # Bank

if __name__ == "__main__":
    main()
