import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def run_generic_simulation(grouped_data, thresholds, targets, stops, multiplier, asset_name):
    total_days = len(grouped_data)
    asset_stats = {}
    
    print(f"Processando simulação para {asset_name}...")
    for th in thresholds:
        entries = []
        tp_hits_count = {tp: 0 for tp in targets}
        raw_reversals = []
        
        th_val = th / multiplier # Converter pontos/pips para variação de preço absoluto
        
        for date, day_bars in grouped_data:
            if len(day_bars) < 2:
                continue
            
            day_open = day_bars['Open'].iloc[0]
            day_high = day_bars['High'].max()
            day_low = day_bars['Low'].min()
            
            # Verificar se o desvio foi atingido
            if not ((day_high - day_open >= th_val) or (day_open - day_low >= th_val)):
                continue
            
            # Rastreamento cronológico de entrada
            entry_hour_idx = -1
            trade_direction = None
            entry_price = 0.0
            
            for h_idx in range(len(day_bars)):
                row = day_bars.iloc[h_idx]
                trig_short = row['High'] - day_open >= th_val
                trig_long = day_open - row['Low'] >= th_val
                
                if trig_short and trig_long:
                    if abs(row['Open'] - row['High']) < abs(row['Open'] - row['Low']):
                        trade_direction = 'Short'
                        entry_price = day_open + th_val
                    else:
                        trade_direction = 'Long'
                        entry_price = day_open - th_val
                    entry_hour_idx = h_idx
                    break
                elif trig_short:
                    trade_direction = 'Short'
                    entry_price = day_open + th_val
                    entry_hour_idx = h_idx
                    break
                elif trig_long:
                    trade_direction = 'Long'
                    entry_price = day_open - th_val
                    entry_hour_idx = h_idx
                    break
            
            if entry_hour_idx == -1:
                continue
            
            # Estatísticas de reversão intraday
            remaining_bars = day_bars.iloc[entry_hour_idx:]
            
            if trade_direction == 'Short':
                lowest_after = remaining_bars['Low'].min()
                max_rev = (entry_price - lowest_after) * multiplier
                close_profit = (entry_price - day_bars['Close'].iloc[-1]) * multiplier
            else:
                highest_after = remaining_bars['High'].max()
                max_rev = (highest_after - entry_price) * multiplier
                close_profit = (day_bars['Close'].iloc[-1] - entry_price) * multiplier
            
            raw_reversals.append({
                "max_rev": float(max_rev),
                "close_profit": float(close_profit)
            })
            
            for tp in targets:
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
        trigger_freq = (triggered_days_count / total_days) * 100 if total_days > 0 else 0
        
        tp_probs = {}
        if triggered_days_count > 0:
            avg_max_rev = np.mean([r["max_rev"] for r in raw_reversals])
            avg_close_profit = np.mean([r["close_profit"] for r in raw_reversals])
            for tp in targets:
                tp_probs[str(tp)] = float((tp_hits_count[tp] / triggered_days_count) * 100)
        else:
            avg_max_rev = 0
            avg_close_profit = 0
            for tp in targets:
                tp_probs[str(tp)] = 0.0
        
        # Simulação rápida com Target e Stop Loss
        sub_results = []
        target_val_dict = {tp: tp / multiplier for tp in targets}
        stop_val_dict = {st: st / multiplier for st in stops}
        
        for target in targets:
            tg_val = target_val_dict[target]
            for stop in stops:
                st_val = stop_val_dict[stop]
                wins = 0
                losses = 0
                net_profit = 0
                
                for entry in entries:
                    direction = entry["trade_direction"]
                    e_price = entry["entry_price"]
                    e_hour_idx = entry["entry_hour_idx"]
                    highs = entry["highs"]
                    lows = entry["lows"]
                    closes = entry["closes"]
                    last_idx = entry["last_idx"]
                    
                    for h_idx in range(e_hour_idx, len(highs)):
                        h_high = highs[h_idx]
                        h_low = lows[h_idx]
                        h_close = closes[h_idx]
                        
                        if h_idx == last_idx:
                            if direction == 'Short':
                                profit = (e_price - h_close) * multiplier
                            else:
                                profit = (h_close - e_price) * multiplier
                            net_profit += profit
                            if profit > 0:
                                wins += 1
                            else:
                                losses += 1
                            break
                        
                        if direction == 'Short':
                            stop_hit = h_high >= e_price + st_val
                            target_hit = h_low <= e_price - tg_val
                            
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
                            stop_hit = h_low <= e_price - st_val
                            target_hit = h_high >= e_price + tg_val
                            
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
        
        asset_stats[str(th)] = {
            "threshold": th,
            "trigger_freq": float(trigger_freq),
            "triggered_days": triggered_days_count,
            "avg_max_reversal": float(avg_max_rev),
            "avg_close_profit": float(avg_close_profit),
            "tp_probabilities": tp_probs,
            "best_configs": sub_results_sorted[:15]
        }
        
    return {
        "total_days": total_days,
        "threshold_data": asset_stats
    }

def run_optimized_simulation():
    print("Baixando base de dados históricos...")
    
    # 1. Mini Índice (^BVSP)
    df_win = pd.DataFrame()
    try:
        t_bvsp = yf.Ticker("^BVSP")
        df_win = t_bvsp.history(period="730d", interval="1h")
        if not df_win.empty:
            df_win.index = df_win.index.tz_convert('America/Sao_Paulo')
            df_win = df_win.ffill().bfill()
            print(f"WIN (^BVSP) baixado. Registros: {len(df_win)}")
    except Exception as e:
        print("Erro WIN:", e)

    # 2. Mini Dólar (BRL=X)
    df_wdo = pd.DataFrame()
    try:
        t_usd = yf.Ticker("BRL=X")
        df_wdo = t_usd.history(period="730d", interval="1h")
        if not df_wdo.empty:
            df_wdo.index = df_wdo.index.tz_convert('America/Sao_Paulo')
            df_wdo = df_wdo[(df_wdo.index.hour >= 9) & (df_wdo.index.hour <= 17)]
            df_wdo = df_wdo.ffill().bfill()
            print(f"WDO (BRL=X) baixado. Registros: {len(df_wdo)}")
    except Exception as e:
        print("Erro WDO:", e)

    # 3. EUR/USD (EURUSD=X)
    df_eur = pd.DataFrame()
    try:
        t_eur = yf.Ticker("EURUSD=X")
        df_eur = t_eur.history(period="730d", interval="1h")
        if not df_eur.empty:
            df_eur.index = df_eur.index.tz_convert('UTC')
            df_eur = df_eur.ffill().bfill()
            print(f"EUR/USD baixado. Registros: {len(df_eur)}")
    except Exception as e:
        print("Erro EUR/USD:", e)

    # 4. GBP/USD (GBPUSD=X)
    df_gbp = pd.DataFrame()
    try:
        t_gbp = yf.Ticker("GBPUSD=X")
        df_gbp = t_gbp.history(period="730d", interval="1h")
        if not df_gbp.empty:
            df_gbp.index = df_gbp.index.tz_convert('UTC')
            df_gbp = df_gbp.ffill().bfill()
            print(f"GBP/USD baixado. Registros: {len(df_gbp)}")
    except Exception as e:
        print("Erro GBP/USD:", e)

    # 5. USD/JPY (USDJPY=X)
    df_jpy = pd.DataFrame()
    try:
        t_jpy = yf.Ticker("USDJPY=X")
        df_jpy = t_jpy.history(period="730d", interval="1h")
        if not df_jpy.empty:
            df_jpy.index = df_jpy.index.tz_convert('UTC')
            df_jpy = df_jpy.ffill().bfill()
            print(f"USD/JPY baixado. Registros: {len(df_jpy)}")
    except Exception as e:
        print("Erro USD/JPY:", e)

    # 6. Ouro (GC=F)
    df_gold = pd.DataFrame()
    try:
        t_gold = yf.Ticker("GC=F")
        df_gold = t_gold.history(period="730d", interval="1h")
        if not df_gold.empty:
            df_gold.index = df_gold.index.tz_convert('UTC')
            df_gold = df_gold.ffill().bfill()
            print(f"Ouro (GC=F) baixado. Registros: {len(df_gold)}")
    except Exception as e:
        print("Erro Ouro:", e)

    stats_output = {
        "metadata": {
            "last_updated": pd.Timestamp.now('America/Sao_Paulo').strftime("%Y-%m-%d %H:%M:%S"),
            "data_period": "2 Anos (730 dias) - Resolução Horária"
        },
        "WIN": {},
        "WDO": {},
        "EURUSD": {},
        "GBPUSD": {},
        "USDJPY": {},
        "XAUUSD": {}
    }

    # --- SIMULAÇÃO WIN ---
    if not df_win.empty:
        df_win['DateOnly'] = df_win.index.date
        win_grouped = list(df_win.groupby('DateOnly'))
        win_thresholds = [300, 400, 500, 600, 800, 1000, 1200, 1500, 1800, 2000, 2500]
        win_targets = [150, 250, 350, 500, 700, 1000]
        win_stops = [350, 500, 700, 1000, 1200, 1500, 2000]
        stats_output["WIN"] = run_generic_simulation(win_grouped, win_thresholds, win_targets, win_stops, 1.0, "Mini Índice (WIN)")

    # --- SIMULAÇÃO WDO ---
    if not df_wdo.empty:
        df_wdo['DateOnly'] = df_wdo.index.date
        wdo_grouped = list(df_wdo.groupby('DateOnly'))
        wdo_thresholds = [15, 20, 25, 30, 35, 40, 50, 60, 70, 80]
        wdo_targets = [5, 10, 15, 20, 25, 30, 40]
        wdo_stops = [15, 20, 25, 30, 40, 50, 80]
        stats_output["WDO"] = run_generic_simulation(wdo_grouped, wdo_thresholds, wdo_targets, wdo_stops, 1000.0, "Mini Dólar (WDO)")

    # --- SIMULAÇÃO EUR/USD ---
    if not df_eur.empty:
        df_eur['DateOnly'] = df_eur.index.date
        eur_grouped = list(df_eur.groupby('DateOnly'))
        eur_thresholds = [15, 20, 25, 30, 40, 50]
        eur_targets = [5, 10, 15, 20, 25, 30]
        eur_stops = [15, 20, 30, 45, 60, 90, 120]
        stats_output["EURUSD"] = run_generic_simulation(eur_grouped, eur_thresholds, eur_targets, eur_stops, 10000.0, "EUR/USD")

    # --- SIMULAÇÃO GBP/USD ---
    if not df_gbp.empty:
        df_gbp['DateOnly'] = df_gbp.index.date
        gbp_grouped = list(df_gbp.groupby('DateOnly'))
        gbp_thresholds = [15, 20, 25, 30, 40, 50]
        gbp_targets = [5, 10, 15, 20, 25, 30]
        gbp_stops = [15, 20, 30, 45, 60, 90, 120]
        stats_output["GBPUSD"] = run_generic_simulation(gbp_grouped, gbp_thresholds, gbp_targets, gbp_stops, 10000.0, "GBP/USD")

    # --- SIMULAÇÃO USD/JPY ---
    if not df_jpy.empty:
        df_jpy['DateOnly'] = df_jpy.index.date
        jpy_grouped = list(df_jpy.groupby('DateOnly'))
        jpy_thresholds = [20, 30, 40, 50, 60, 80]
        jpy_targets = [10, 15, 20, 30, 40]
        jpy_stops = [30, 45, 60, 90, 120]
        stats_output["USDJPY"] = run_generic_simulation(jpy_grouped, jpy_thresholds, jpy_targets, jpy_stops, 100.0, "USD/JPY")

    # --- SIMULAÇÃO OURO ---
    if not df_gold.empty:
        df_gold['DateOnly'] = df_gold.index.date
        gold_grouped = list(df_gold.groupby('DateOnly'))
        gold_thresholds = [5, 8, 10, 12, 15, 20, 25, 30]
        gold_targets = [2, 3, 5, 8, 10, 12, 15]
        gold_stops = [8, 10, 15, 20, 30, 40, 50, 60]
        stats_output["XAUUSD"] = run_generic_simulation(gold_grouped, gold_thresholds, gold_targets, gold_stops, 1.0, "Ouro (XAU/USD)")

    # Salvar cache
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(current_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "b3_daytrade_stats.json")
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(stats_output, f, indent=4, ensure_ascii=False)
        
    print(f"\nEstatísticas quantitativas salvas em: {cache_path}")

if __name__ == "__main__":
    run_optimized_simulation()
