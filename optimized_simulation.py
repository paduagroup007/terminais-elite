import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def run_optimized_simulation():
    print("Downloading historical data...")
    
    # Mini Index Proxy (^BVSP)
    try:
        t_bvsp = yf.Ticker("^BVSP")
        df_bvsp = t_bvsp.history(period="730d", interval="1h")
        df_bvsp.index = df_bvsp.index.tz_convert('America/Sao_Paulo')
        df_bvsp = df_bvsp.ffill().bfill()
        print(f"BVSP downloaded. Datapoints: {len(df_bvsp)}")
    except Exception as e:
        print("Error downloading ^BVSP:", e)
        df_bvsp = pd.DataFrame()

    # Mini Dollar Proxy (BRL=X)
    try:
        t_usd = yf.Ticker("BRL=X")
        df_usd = t_usd.history(period="730d", interval="1h")
        df_usd.index = df_usd.index.tz_convert('America/Sao_Paulo')
        df_usd = df_usd[(df_usd.index.hour >= 9) & (df_usd.index.hour <= 17)]
        df_usd = df_usd.ffill().bfill()
        print(f"BRL=X downloaded and filtered. Datapoints: {len(df_usd)}")
    except Exception as e:
        print("Error downloading BRL=X:", e)
        df_usd = pd.DataFrame()

    stats_output = {
        "metadata": {
            "last_updated": pd.Timestamp.now('America/Sao_Paulo').strftime("%Y-%m-%d %H:%M:%S"),
            "data_period": "2 Years (730 days) - Hourly resolution"
        },
        "WIN": {},
        "WDO": {}
    }

    # -------------------------------------------------------------
    # SIMULATION FOR MINI INDEX (WIN)
    # -------------------------------------------------------------
    if not df_bvsp.empty:
        df_bvsp['DateOnly'] = df_bvsp.index.date
        grouped_win = list(df_bvsp.groupby('DateOnly'))
        total_days = len(grouped_win)
        
        # Parameters
        win_thresholds = [400, 600, 800, 1000, 1200, 1500, 1800, 2000, 2500]
        win_targets = [150, 250, 350, 500, 700, 1000]
        win_stops = [150, 250, 350, 500, 700, 1000, 1500, 2000]
        
        win_stats = {}
        
        print("\nProcessing WIN (Mini Índice) simulation...")
        for th in win_thresholds:
            entries = []
            tp_hits_count = {tp: 0 for tp in win_targets}
            raw_reversals = []
            
            for date, day_bars in grouped_win:
                if len(day_bars) < 2:
                    continue
                
                day_open = day_bars['Open'].iloc[0]
                day_high = day_bars['High'].max()
                day_low = day_bars['Low'].min()
                
                # Check if threshold was reached
                if not ((day_high >= day_open + th) or (day_low <= day_open - th)):
                    continue
                
                # Chronological trigger check
                entry_hour_idx = -1
                trade_direction = None
                entry_price = 0.0
                
                for h_idx in range(len(day_bars)):
                    row = day_bars.iloc[h_idx]
                    trig_short = row['High'] >= day_open + th
                    trig_long = row['Low'] <= day_open - th
                    
                    if trig_short and trig_long:
                        if abs(row['Open'] - row['High']) < abs(row['Open'] - row['Low']):
                            trade_direction = 'Short'
                            entry_price = day_open + th
                        else:
                            trade_direction = 'Long'
                            entry_price = day_open - th
                        entry_hour_idx = h_idx
                        break
                    elif trig_short:
                        trade_direction = 'Short'
                        entry_price = day_open + th
                        entry_hour_idx = h_idx
                        break
                    elif trig_long:
                        trade_direction = 'Long'
                        entry_price = day_open - th
                        entry_hour_idx = h_idx
                        break
                
                if entry_hour_idx == -1:
                    continue
                
                # Reversal calculations
                remaining_bars = day_bars.iloc[entry_hour_idx:]
                
                if trade_direction == 'Short':
                    lowest_after = remaining_bars['Low'].min()
                    max_rev = entry_price - lowest_after
                    close_profit = entry_price - day_bars['Close'].iloc[-1]
                else:
                    highest_after = remaining_bars['High'].max()
                    max_rev = highest_after - entry_price
                    close_profit = day_bars['Close'].iloc[-1] - entry_price
                
                raw_reversals.append({
                    "max_rev": float(max_rev),
                    "close_profit": float(close_profit)
                })
                
                for tp in win_targets:
                    if max_rev >= tp:
                        tp_hits_count[tp] += 1
                        
                entries.append({
                    "trade_direction": trade_direction,
                    "entry_price": entry_price,
                    "entry_hour_idx": entry_hour_idx,
                    "highs": day_bars['High'].values,
                    "lows": day_bars['Low'].values,
                    "closes": day_bars['Close'].values,
                    "last_idx": len(day_bars) - 1
                })
            
            triggered_days_count = len(entries)
            trigger_freq = (triggered_days_count / total_days) * 100
            
            # Reversal probabilities
            tp_probs = {}
            if triggered_days_count > 0:
                avg_max_rev = np.mean([r["max_rev"] for r in raw_reversals])
                avg_close_profit = np.mean([r["close_profit"] for r in raw_reversals])
                for tp in win_targets:
                    tp_probs[str(tp)] = float((tp_hits_count[tp] / triggered_days_count) * 100)
            else:
                avg_max_rev = 0
                avg_close_profit = 0
                for tp in win_targets:
                    tp_probs[str(tp)] = 0.0
            
            # Fast target & stop simulation
            sub_results = []
            for target in win_targets:
                for stop in win_stops:
                    wins = 0
                    losses = 0
                    net_profit = 0
                    
                    for entry in entries:
                        direction = entry["trade_direction"]
                        entry_price = entry["entry_price"]
                        entry_hour_idx = entry["entry_hour_idx"]
                        highs = entry["highs"]
                        lows = entry["lows"]
                        closes = entry["closes"]
                        last_idx = entry["last_idx"]
                        
                        for h_idx in range(entry_hour_idx, len(highs)):
                            h_high = highs[h_idx]
                            h_low = lows[h_idx]
                            h_close = closes[h_idx]
                            
                            if h_idx == last_idx:
                                if direction == 'Short':
                                    profit = entry_price - h_close
                                else:
                                    profit = h_close - entry_price
                                net_profit += profit
                                if profit > 0:
                                    wins += 1
                                else:
                                    losses += 1
                                break
                            
                            if direction == 'Short':
                                stop_hit = h_high >= entry_price + stop
                                target_hit = h_low <= entry_price - target
                                
                                if stop_hit and target_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif stop_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif target_hit:
                                    wins += 1
                                    net_profit += target
                                    break
                            else: # Long
                                stop_hit = h_low <= entry_price - stop
                                target_hit = h_high >= entry_price + target
                                
                                if stop_hit and target_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif stop_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif target_hit:
                                    wins += 1
                                    net_profit += target
                                    break
                                    
                    total_trades = wins + losses
                    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                    expectancy = net_profit / total_trades if total_trades > 0 else 0
                    
                    sub_results.append({
                        "target": target,
                        "stop": stop,
                        "trades": total_trades,
                        "win_rate": float(win_rate),
                        "expectancy": float(expectancy)
                    })
            
            sub_results_sorted = sorted(sub_results, key=lambda x: x["expectancy"], reverse=True)
            
            win_stats[str(th)] = {
                "threshold": th,
                "trigger_freq": float(trigger_freq),
                "triggered_days": triggered_days_count,
                "avg_max_reversal": float(avg_max_rev),
                "avg_close_profit": float(avg_close_profit),
                "tp_probabilities": tp_probs,
                "best_configs": sub_results_sorted[:15]
            }
        
        stats_output["WIN"] = {
            "total_days": total_days,
            "threshold_data": win_stats
        }
        print("WIN processing complete.")

    # -------------------------------------------------------------
    # SIMULATION FOR MINI DOLLAR (WDO)
    # -------------------------------------------------------------
    if not df_usd.empty:
        df_usd['DateOnly'] = df_usd.index.date
        grouped_usd = list(df_usd.groupby('DateOnly'))
        total_days_usd = len(grouped_usd)
        
        # Parameters (in points, 1 point = 0.001 rate)
        usd_thresholds = [15, 20, 25, 30, 35, 40, 50, 60, 70, 80]
        usd_targets = [5, 10, 15, 20, 25, 30, 40]
        usd_stops = [5, 10, 15, 20, 25, 30, 40, 50]
        
        usd_stats = {}
        
        print("\nProcessing WDO (Mini Dólar) simulation...")
        for th in usd_thresholds:
            entries = []
            tp_hits_count = {tp: 0 for tp in usd_targets}
            raw_reversals = []
            
            for date, day_bars in grouped_usd:
                if len(day_bars) < 2:
                    continue
                
                day_open = day_bars['Open'].iloc[0]
                day_high = day_bars['High'].max()
                day_low = day_bars['Low'].min()
                
                # In points: difference * 1000
                if not (((day_high - day_open) * 1000 >= th) or ((day_open - day_low) * 1000 >= th)):
                    continue
                
                # Chronological trigger check
                entry_hour_idx = -1
                trade_direction = None
                entry_price = 0.0
                
                for h_idx in range(len(day_bars)):
                    row = day_bars.iloc[h_idx]
                    trig_short = (row['High'] - day_open) * 1000 >= th
                    trig_long = (day_open - row['Low']) * 1000 >= th
                    
                    if trig_short and trig_long:
                        if abs(row['Open'] - row['High']) < abs(row['Open'] - row['Low']):
                            trade_direction = 'Short'
                            entry_price = day_open + (th / 1000.0)
                        else:
                            trade_direction = 'Long'
                            entry_price = day_open - (th / 1000.0)
                        entry_hour_idx = h_idx
                        break
                    elif trig_short:
                        trade_direction = 'Short'
                        entry_price = day_open + (th / 1000.0)
                        entry_hour_idx = h_idx
                        break
                    elif trig_long:
                        trade_direction = 'Long'
                        entry_price = day_open - (th / 1000.0)
                        entry_hour_idx = h_idx
                        break
                
                if entry_hour_idx == -1:
                    continue
                
                # Reversal details
                remaining_bars = day_bars.iloc[entry_hour_idx:]
                
                if trade_direction == 'Short':
                    lowest_after = remaining_bars['Low'].min()
                    max_rev = (entry_price - lowest_after) * 1000
                    close_profit = (entry_price - day_bars['Close'].iloc[-1]) * 1000
                else:
                    highest_after = remaining_bars['High'].max()
                    max_rev = (highest_after - entry_price) * 1000
                    close_profit = (day_bars['Close'].iloc[-1] - entry_price) * 1000
                
                raw_reversals.append({
                    "max_rev": float(max_rev),
                    "close_profit": float(close_profit)
                })
                
                for tp in usd_targets:
                    if max_rev >= tp:
                        tp_hits_count[tp] += 1
                        
                entries.append({
                    "trade_direction": trade_direction,
                    "entry_price": entry_price,
                    "entry_hour_idx": entry_hour_idx,
                    "highs": day_bars['High'].values,
                    "lows": day_bars['Low'].values,
                    "closes": day_bars['Close'].values,
                    "last_idx": len(day_bars) - 1
                })
            
            triggered_days_count = len(entries)
            trigger_freq = (triggered_days_count / total_days_usd) * 100
            
            tp_probs = {}
            if triggered_days_count > 0:
                avg_max_rev = np.mean([r["max_rev"] for r in raw_reversals])
                avg_close_profit = np.mean([r["close_profit"] for r in raw_reversals])
                for tp in usd_targets:
                    tp_probs[str(tp)] = float((tp_hits_count[tp] / triggered_days_count) * 100)
            else:
                avg_max_rev = 0
                avg_close_profit = 0
                for tp in usd_targets:
                    tp_probs[str(tp)] = 0.0
            
            # Fast target & stop simulation
            sub_results = []
            for target in usd_targets:
                for stop in usd_stops:
                    wins = 0
                    losses = 0
                    net_profit = 0
                    
                    for entry in entries:
                        direction = entry["trade_direction"]
                        entry_price = entry["entry_price"]
                        entry_hour_idx = entry["entry_hour_idx"]
                        highs = entry["highs"]
                        lows = entry["lows"]
                        closes = entry["closes"]
                        last_idx = entry["last_idx"]
                        
                        for h_idx in range(entry_hour_idx, len(highs)):
                            h_high = highs[h_idx]
                            h_low = lows[h_idx]
                            h_close = closes[h_idx]
                            
                            if h_idx == last_idx:
                                if direction == 'Short':
                                    profit = (entry_price - h_close) * 1000
                                else:
                                    profit = (h_close - entry_price) * 1000
                                net_profit += profit
                                if profit > 0:
                                    wins += 1
                                else:
                                    losses += 1
                                break
                            
                            if direction == 'Short':
                                stop_hit = h_high >= entry_price + (stop / 1000.0)
                                target_hit = h_low <= entry_price - (target / 1000.0)
                                
                                if stop_hit and target_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif stop_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif target_hit:
                                    wins += 1
                                    net_profit += target
                                    break
                            else: # Long
                                stop_hit = h_low <= entry_price - (stop / 1000.0)
                                target_hit = h_high >= entry_price + (target / 1000.0)
                                
                                if stop_hit and target_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif stop_hit:
                                    losses += 1
                                    net_profit -= stop
                                    break
                                elif target_hit:
                                    wins += 1
                                    net_profit += target
                                    break
                                    
                    total_trades = wins + losses
                    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
                    expectancy = net_profit / total_trades if total_trades > 0 else 0
                    
                    sub_results.append({
                        "target": target,
                        "stop": stop,
                        "trades": total_trades,
                        "win_rate": float(win_rate),
                        "expectancy": float(expectancy)
                    })
            
            sub_results_sorted = sorted(sub_results, key=lambda x: x["expectancy"], reverse=True)
            
            usd_stats[str(th)] = {
                "threshold": th,
                "trigger_freq": float(trigger_freq),
                "triggered_days": triggered_days_count,
                "avg_max_reversal": float(avg_max_rev),
                "avg_close_profit": float(avg_close_profit),
                "tp_probabilities": tp_probs,
                "best_configs": sub_results_sorted[:15]
            }
            
        stats_output["WDO"] = {
            "total_days": total_days_usd,
            "threshold_data": usd_stats
        }
        print("WDO processing complete.")

    # 2. Save stats to JSON cache
    # Get current file directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(current_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "b3_daytrade_stats.json")
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(stats_output, f, indent=4, ensure_ascii=False)
        
    print(f"\nAll daytrade statistics successfully saved to: {cache_path}")

if __name__ == "__main__":
    run_optimized_simulation()
