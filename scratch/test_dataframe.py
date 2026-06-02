import yfinance as yf
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

def fetch_us_company_financials(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    
    # Financials
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow
    
    # Get sorted list of years
    years = sorted(list(fin.columns))
    
    records = []
    for y in years:
        # Get data for year y
        y_fin = fin[y] if y in fin.columns else pd.Series()
        y_bs = bs[y] if y in bs.columns else pd.Series()
        y_cf = cf[y] if y in cf.columns else pd.Series()
        
        # Extract fields
        rev = y_fin.get('Total Revenue', y_fin.get('Operating Revenue', 0.0))
        ebitda = y_fin.get('EBITDA', y_fin.get('Normalized EBITDA', 0.0))
        net_inc = y_fin.get('Net Income', y_fin.get('Net Income Common Stockholders', 0.0))
        
        equity = y_bs.get('Stockholders Equity', y_bs.get('Common Stock Equity', 0.0))
        cash = y_bs.get('Cash Cash Equivalents And Short Term Investments', y_bs.get('Cash And Cash Equivalents', 0.0))
        debt = y_bs.get('Total Debt', y_bs.get('Total Liabilities Net Minority Interest', 0.0))
        
        working_cap = y_bs.get('Working Capital', 0.0)
        retained_earn = y_bs.get('Retained Earnings', 0.0)
        total_assets = y_bs.get('Total Assets', 0.0)
        total_liab = y_bs.get('Total Liabilities Net Minority Interest', 0.0)
        
        op_cash = y_cf.get('Operating Cash Flow', y_cf.get('Cash Flow From Continuing Operating Activities', 0.0))
        
        date_str = str(y).split(' ')[0]
        
        records.append({
            "Data": date_str,
            "Receita": float(rev) if pd.notna(rev) else 0.0,
            "EBITDA": float(ebitda) if pd.notna(ebitda) else 0.0,
            "Lucro": float(net_inc) if pd.notna(net_inc) else 0.0,
            "Patrimonio": float(equity) if pd.notna(equity) else 0.0,
            "Caixa": float(cash) if pd.notna(cash) else 0.0,
            "Divida": float(debt) if pd.notna(debt) else 0.0,
            "Working_Capital": float(working_cap) if pd.notna(working_cap) else 0.0,
            "Retained_Earnings": float(retained_earn) if pd.notna(retained_earn) else 0.0,
            "Total_Assets": float(total_assets) if pd.notna(total_assets) else 0.0,
            "Total_Liabilities": float(total_liab) if pd.notna(total_liab) else 0.0,
            "Operating_Cash_Flow": float(op_cash) if pd.notna(op_cash) else 0.0,
        })
        
    df = pd.DataFrame(records)
    return df

def main():
    df = fetch_us_company_financials("AAPL")
    print(df)

if __name__ == "__main__":
    main()
