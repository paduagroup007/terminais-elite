import yfinance as yf
import pandas as pd

def main():
    ticker = yf.Ticker("AAPL")
    print("--- AAPL FINANCIALS ---")
    print(ticker.financials.index.tolist())
    print("Financials Columns:", ticker.financials.columns.tolist())
    
    print("\n--- AAPL BALANCE SHEET ---")
    print(ticker.balance_sheet.index.tolist())
    print("Balance Sheet Columns:", ticker.balance_sheet.columns.tolist())
    
    print("\n--- AAPL CASH FLOW ---")
    print(ticker.cashflow.index.tolist())
    print("Cash Flow Columns:", ticker.cashflow.columns.tolist())

if __name__ == "__main__":
    main()
