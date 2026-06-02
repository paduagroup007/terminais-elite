import yfinance as yf

def main():
    ticker = yf.Ticker("AAPL")
    print("--- FAST INFO ---")
    try:
        print(dict(ticker.fast_info))
    except Exception as e:
        print("fast_info failed:", e)
        
    print("\n--- INFO ---")
    try:
        info = ticker.info
        print("currentPrice:", info.get("currentPrice"))
        print("dividendYield:", info.get("dividendYield"))
        print("marketCap:", info.get("marketCap"))
        print("sharesOutstanding:", info.get("sharesOutstanding"))
    except Exception as e:
        print("info failed:", e)
        
    print("\n--- HISTORY LAST CLOSE ---")
    try:
        hist = ticker.history(period="1d")
        print("History Close:", hist['Close'].iloc[-1] if not hist.empty else "Empty")
    except Exception as e:
        print("history failed:", e)

if __name__ == "__main__":
    main()
