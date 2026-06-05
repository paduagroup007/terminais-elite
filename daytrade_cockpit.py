import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import os
import json
import traceback
import optimized_simulation

# Translations dictionary
DT_TRANS = {
    "PT": {
        "title": "COCKPIT QUANT: DAY-TRADE & DESVIOS 111",
        "desc": "Análise estatística intraday de reversão à média e monitoramento de desvios da média móvel simples de 111 períodos.",
        "select_asset": "SELECIONE O ATIVO",
        "live_telemetry": "TELEMETRIA EM TEMPO REAL (B3 & GLOBAL PROXY)",
        "current_price": "Preço Atual",
        "day_open": "Abertura do Dia",
        "day_range": "Amplitude Média (H-L)",
        "sma_analysis": "ANÁLISE DE CONFLUÊNCIA - DESVIOS DA MÉDIA 111",
        "tf_daily": "Diário (D1)",
        "tf_weekly": "Semanal (W1)",
        "tf_h4": "4 Horas (H4)",
        "curr_val": "Preço",
        "sma_val": "Média 111",
        "dev_val": "Desvio",
        "reversal_prob": "ESTATÍSTICAS DE REVERSÃO INTRADAY",
        "reversal_title": "Matriz de Pullback Estatístico (Day-Trade)",
        "reversal_desc": "Mede a probabilidade de o preço corrigir X pontos/pips a partir da abertura após atingir o desvio, liquidando a posição no encerramento do dia.",
        "raw_pullback": "Probabilidade de Pullback (Sem Stop Loss)",
        "target": "Alvo (TP)",
        "prob": "Probabilidade",
        "best_configs": "Configurações Otimizadas (Com Stop Loss)",
        "recalc_btn": "🔄 Recalcular Base Estatística (2 Anos de Histórico)",
        "active_alert": "🚨 DETECTOR DE DESVIO INTRADAY EM CURSO",
        "active_signal": "O ativo **{asset}** está com um desvio de **{dev:+.0f}** em relação à abertura! Historicamente, desvios de **{th}** corrigem pelo menos **{tp}** em **{prob:.1f}%** das vezes (Expectativa: {exp:+.1f}).",
        "alert_no_trigger": "Sem desvios atípicos ativos no momento (< {th_min} pts/pips da abertura).",
        "chart_title": "Gráfico Histórico de Preço & Média 111",
        "select_tf": "Selecionar Tempo Gráfico para o Gráfico",
        "run_points": "Desvio da Abertura",
        "last_update": "Última atualização da base: {date}"
    },
    "EN": {
        "title": "QUANT COCKPIT: DAY-TRADE & 111 DEVIATIONS",
        "desc": "Intraday statistical mean reversion analysis and tracking of deviations from the 111-period simple moving average.",
        "select_asset": "SELECT ACTIVE ASSET",
        "live_telemetry": "REAL-TIME TELEMETRY (B3 & GLOBAL PROXY)",
        "current_price": "Current Price",
        "day_open": "Day Open",
        "day_range": "Average Range (H-L)",
        "sma_analysis": "CONFLUENCE ANALYSIS - 111 SMA DEVIATIONS",
        "tf_daily": "Daily (D1)",
        "tf_weekly": "Weekly (W1)",
        "tf_h4": "4 Hours (H4)",
        "curr_val": "Price",
        "sma_val": "111 SMA",
        "dev_val": "Deviation",
        "reversal_prob": "INTRADAY REVERSAL STATISTICS",
        "reversal_title": "Statistical Pullback Matrix (Day-Trade)",
        "reversal_desc": "Measures the probability of price correcting X points/pips from the open after hitting the deviation, force-closing at market end.",
        "raw_pullback": "Pullback Probability (No Stop Loss)",
        "target": "Target (TP)",
        "prob": "Probability",
        "best_configs": "Optimized Configurations (With Stop Loss)",
        "recalc_btn": "🔄 Recalculate Stats Database (2-Year History)",
        "active_alert": "🚨 ACTIVE INTRADAY DEVIATION DETECTED",
        "active_signal": "The asset **{asset}** has a deviation of **{dev:+.0f}** from the open! Historically, deviations of **{th}** pull back by at least **{tp}** in **{prob:.1f}% of cases (Expectancy: {exp:+.1f}).",
        "alert_no_trigger": "No active abnormal deviations at this moment (< {th_min} pts/pips from open).",
        "chart_title": "Historical Price & 111 SMA Chart",
        "select_tf": "Select Chart Timeframe",
        "run_points": "Deviation from Open",
        "last_update": "Last database update: {date}"
    },
    "ES": {
        "title": "COCKPIT QUANT: DAY-TRADE & DESVÍOS 111",
        "desc": "Análisis estadístico intradía de reversión a la media y monitoreo de desvíos de la media móvil simple de 111 períodos.",
        "select_asset": "SELECCIONE EL ACTIVO",
        "live_telemetry": "TELEMETRÍA EN TIEMPO REAL (B3 & GLOBAL PROXY)",
        "current_price": "Precio Actual",
        "day_open": "Apertura del Día",
        "day_range": "Rango Promedio (H-L)",
        "sma_analysis": "ANÁLISIS DE CONFLUENCIA - DESVÍOS DE LA MEDIA 111",
        "tf_daily": "Diario (D1)",
        "tf_weekly": "Semanal (W1)",
        "tf_h4": "4 Horas (H4)",
        "curr_val": "Precio",
        "sma_val": "Media 111",
        "dev_val": "Desvío",
        "reversal_prob": "ESTADÍSTICAS DE REVERSIÓN INTRADÍA",
        "reversal_title": "Matriz de Pullback Estadístico (Day-Trade)",
        "reversal_desc": "Mide la probabilidad de que el precio corrija X puntos/pips a partir de la apertura tras alcanzar el desvío, liquidando al cierre.",
        "raw_pullback": "Probabilidad de Pullback (Sin Stop Loss)",
        "target": "Objetivo (TP)",
        "prob": "Probabilidad",
        "best_configs": "Configuraciones Optimizadas (Con Stop Loss)",
        "recalc_btn": "🔄 Recalcular Base Estadística (Historial 2 Años)",
        "active_alert": "🚨 DETECTOR DE DESVÍO INTRADÍA EN CURSO",
        "active_signal": "¡El activo **{asset}** tiene un desvío de **{dev:+.0f}** de la apertura! Históricamente, desvíos de **{th}** corrigen al menos **{tp}** el **{prob:.1f}%** de las veces (Expectativa: {exp:+.1f}).",
        "alert_no_trigger": "Sin desvíos atípicos activos en este momento (< {th_min} pts/pips de la apertura).",
        "chart_title": "Gráfico Histórico de Precio & Media 111",
        "select_tf": "Seleccionar Temporalidad para el Gráfico",
        "run_points": "Desvío de la Apertura",
        "last_update": "Última actualización de la base: {date}"
    }
}

@st.cache_data(ttl=120, max_entries=5)
def fetch_live_b3_daytrade_data(ticker):
    t = yf.Ticker(ticker)
    df_d1 = t.history(period="250d", interval="1d")
    df_w1 = t.history(period="3y", interval="1wk")
    df_h1 = t.history(period="150d", interval="1h")
    
    # Convert indexes to America/Sao_Paulo local time for UI display
    if not df_d1.empty and df_d1.index.tz is not None:
        df_d1.index = df_d1.index.tz_convert('America/Sao_Paulo')
    if not df_w1.empty and df_w1.index.tz is not None:
        df_w1.index = df_w1.index.tz_convert('America/Sao_Paulo')
    if not df_h1.empty:
        if df_h1.index.tz is not None:
            df_h1.index = df_h1.index.tz_convert('America/Sao_Paulo')
        # Filter standard B3 hours (09:00 to 18:00) only for BRL=X
        if ticker == "BRL=X":
            df_h1 = df_h1[(df_h1.index.hour >= 9) & (df_h1.index.hour <= 17)]
            
    return df_d1, df_w1, df_h1

def render_daytrade_cockpit(lang):
    tx = DT_TRANS.get(lang, DT_TRANS["PT"])
    
    st.markdown(f"<h2>{tx['title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#bf953f; font-weight:600; font-size:13px; margin-top:-10px; margin-bottom:25px;'>{tx['desc'].upper()}</p>", unsafe_allow_html=True)
    
    # Secret area in the sidebar
    admin_mode = False
    with st.sidebar:
        st.markdown("<h4 style='color:#bf953f; font-size:12px; font-weight:700; margin-bottom:5px; text-transform:uppercase;'>Área do Administrador</h4>", unsafe_allow_html=True)
        admin_pass = st.text_input("Chave Quant Privada", type="password", key="quant_admin_pass")
        if admin_pass == "jarvis23" or admin_pass == "elite23":
            admin_mode = True
            st.success("Modo Quant Privado Ativo!")
            
    # Recalculate stats handler
    if st.sidebar.button(tx["recalc_btn"], key="recalc_daytrade_stats_btn", use_container_width=True):
        with st.spinner("Executando backtests históricos..." if lang == "PT" else "Running historical backtests..."):
            try:
                optimized_simulation.run_optimized_simulation()
                st.success("Estatísticas recalculadas com sucesso!" if lang == "PT" else "Stats recalculated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao recalcular: {e}")
    
    # Asset selection
    options = ["WIN (Mini Índice)", "WDO (Mini Dólar)"]
    if admin_mode:
        options = ["WIN (Mini Índice)", "WDO (Mini Dólar)", "EUR/USD", "GBP/USD", "USD/JPY", "Ouro (XAU/USD)"]
        
    # Safeguard session state selection
    if "daytrade_asset_sel" in st.session_state and st.session_state["daytrade_asset_sel"] not in options:
        st.session_state["daytrade_asset_sel"] = "WIN (Mini Índice)"
        
    asset_option = st.segmented_control(
        tx["select_asset"],
        options=options,
        default="WIN (Mini Índice)",
        key="daytrade_asset_sel"
    )

    
    # Map parameters based on selection
    if "WIN" in asset_option:
        ticker = "^BVSP"
        asset_code = "WIN"
        val_suffix = "pts"
        multiplier = 1.0
        price_format = "{:,.2f}"
    elif "WDO" in asset_option:
        ticker = "BRL=X"
        asset_code = "WDO"
        val_suffix = "pts"
        multiplier = 1000.0
        price_format = "{:.4f}"
    elif "EUR/USD" in asset_option:
        ticker = "EURUSD=X"
        asset_code = "EURUSD"
        val_suffix = "pips"
        multiplier = 10000.0
        price_format = "{:.5f}"
    elif "GBP/USD" in asset_option:
        ticker = "GBPUSD=X"
        asset_code = "GBPUSD"
        val_suffix = "pips"
        multiplier = 10000.0
        price_format = "{:.5f}"
    elif "USD/JPY" in asset_option:
        ticker = "USDJPY=X"
        asset_code = "USDJPY"
        val_suffix = "pips"
        multiplier = 100.0
        price_format = "{:.3f}"
    else: # Ouro (XAU/USD)
        ticker = "GC=F"
        asset_code = "XAUUSD"
        val_suffix = "USD"
        multiplier = 1.0
        price_format = "{:,.2f}"
    
    with st.spinner("Carregando cotações e calculando desvios..." if lang == "PT" else "Loading quotes and calculating deviations..."):
        try:
            df_d1, df_w1, df_h1 = fetch_live_b3_daytrade_data(ticker)
        except Exception as e:
            st.error(f"Erro ao buscar dados do Yahoo Finance: {e}")
            return
            
    if df_d1.empty or df_w1.empty or df_h1.empty:
        st.warning("Dados incompletos retornados do Yahoo Finance. Tente novamente em instantes.")
        return
        
    # Process H4 resample
    df_h4 = df_h1.resample('4h').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    # Calculate 111 SMAs
    df_d1['SMA_111'] = df_d1['Close'].rolling(111).mean()
    df_w1['SMA_111'] = df_w1['Close'].rolling(111).mean()
    df_h4['SMA_111'] = df_h4['Close'].rolling(111).mean()
    
    # Current day details
    # Get current price
    current_price = df_h1['Close'].iloc[-1]
    
    # Extract today's open/high/low in correct timezone
    if asset_code in ["WIN", "WDO"]:
        last_date = df_h1.index[-1].date()
        today_bars = df_h1[df_h1.index.date == last_date]
        if not today_bars.empty:
            today_open = today_bars['Open'].iloc[0]
            today_high = today_bars['High'].max()
            today_low = today_bars['Low'].min()
        else:
            today_open = df_d1['Open'].iloc[-1]
            today_high = df_d1['High'].iloc[-1]
            today_low = df_d1['Low'].iloc[-1]
    else:
        # International assets: use UTC daily grouping (rollover at 21:00 BRT / 00:00 UTC)
        df_h1_utc = df_h1.tz_convert('UTC')
        last_date_utc = df_h1_utc.index[-1].date()
        today_bars_utc = df_h1_utc[df_h1_utc.index.date == last_date_utc]
        if not today_bars_utc.empty:
            today_open = today_bars_utc['Open'].iloc[0]
            today_high = today_bars_utc['High'].max()
            today_low = today_bars_utc['Low'].min()
        else:
            df_d1_utc = df_d1.tz_convert('UTC') if df_d1.index.tz is not None else df_d1
            today_open = df_d1_utc['Open'].iloc[-1]
            today_high = df_d1_utc['High'].iloc[-1]
            today_low = df_d1_utc['Low'].iloc[-1]
        
    # Deviations from open
    deviation_pts = (current_price - today_open) * multiplier
    deviation_pct = (current_price / today_open - 1) * 100

    # 1. LIVE TELEMETRY
    st.markdown(f"<h3>{tx['live_telemetry']}</h3>", unsafe_allow_html=True)
    
    # Formatting values for live telemetry
    current_price_str = price_format.format(current_price)
    today_open_str = price_format.format(today_open)
    if asset_code == "WDO":
        current_price_str = f"R$ {current_price_str}"
        today_open_str = f"R$ {today_open_str}"
    elif asset_code in ["EURUSD", "GBPUSD"]:
        current_price_str = f"$ {current_price_str}"
        today_open_str = f"$ {today_open_str}"
    elif asset_code == "USDJPY":
        current_price_str = f"¥ {current_price_str}"
        today_open_str = f"¥ {today_open_str}"
    elif asset_code == "XAUUSD":
        current_price_str = f"$ {current_price_str} /oz"
        today_open_str = f"$ {today_open_str} /oz"
        
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.metric(tx["current_price"], current_price_str)
    with col_t2:
        st.metric(tx["day_open"], today_open_str)
    with col_t3:
        color_style = "color:#00ffa5;" if deviation_pts >= 0 else "color:#ff4a4a;"
        sign = "+" if deviation_pts >= 0 else ""
        st.markdown(
            f"<div style='background-color:#161a23; padding:10px; border-radius:6px; border:1px solid #ffffff10; text-align:center;'>"
            f"<div style='font-size:11px; color:#888888; font-weight:700;'>{tx['run_points'].upper()}</div>"
            f"<div style='font-size:16px; font-weight:900; {color_style}'>{sign}{deviation_pts:,.1f} {val_suffix}</div>"
            f"<div style='font-size:11px; {color_style}'>{sign}{deviation_pct:+.2f}%</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_t4:
        day_range = (today_high - today_low) * multiplier
        st.metric(tx["day_range"], f"{day_range:,.1f} {val_suffix}")

    # 2. SMA 111 DEVIATIONS
    st.write("")
    st.markdown(f"<h3>{tx['sma_analysis']}</h3>", unsafe_allow_html=True)
    
    # D1, W1, H4 Deviation calcs
    sma_d1 = df_d1['SMA_111'].iloc[-1]
    sma_w1 = df_w1['SMA_111'].iloc[-1]
    sma_h4 = df_h4['SMA_111'].iloc[-1]
    
    dev_d1_pts = (current_price - sma_d1) * multiplier
    dev_d1_pct = (current_price / sma_d1 - 1) * 100
    
    dev_w1_pts = (current_price - sma_w1) * multiplier
    dev_w1_pct = (current_price / sma_w1 - 1) * 100
    
    dev_h4_pts = (current_price - sma_h4) * multiplier
    dev_h4_pct = (current_price / sma_h4 - 1) * 100
    
    col_d1, col_w1, col_h4 = st.columns(3)
    
    # Custom HTML Card Helper
    def render_sma_card(tf_name, price, sma, dev_pts, dev_pct, suffix):
        sign = "+" if dev_pts >= 0 else ""
        color = "#00ffa5" if dev_pts >= 0 else "#ff4a4a"
        arrow = "▲" if dev_pts >= 0 else "▼"
        
        html = f"""
        <div style="background-color:#161a23; border:1px solid #bf953f33; border-radius:8px; padding:15px; box-shadow:0 4px 15px rgba(0,0,0,0.3); font-family:'Inter', sans-serif;">
            <div style="color:#bf953f; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;">{tf_name}</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
                <span style="color:#888888;">{tx['curr_val']}:</span>
                <span style="color:#ffffff; font-weight:700;">{price_format.format(price)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:12px;">
                <span style="color:#888888;">{tx['sma_val']}:</span>
                <span style="color:#ffffff; font-weight:700;">{price_format.format(sma)}</span>
            </div>
            <div style="border-top:1px solid #ffffff10; padding-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#888888; font-size:11px;">{tx['dev_val']}:</span>
                <span style="color:{color}; font-weight:900; font-size:14px;">
                    {arrow} {sign}{dev_pts:,.1f} {suffix} ({sign}{dev_pct:+.2f}%)
                </span>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        
    with col_d1:
        render_sma_card(tx["tf_daily"], current_price, sma_d1, dev_d1_pts, dev_d1_pct, val_suffix)
    with col_w1:
        render_sma_card(tx["tf_weekly"], current_price, sma_w1, dev_w1_pts, dev_w1_pct, val_suffix)
    with col_h4:
        render_sma_card(tx["tf_h4"], current_price, sma_h4, dev_h4_pts, dev_h4_pct, val_suffix)

    # 3. REVERSAL PROBABILITIES
    st.write("")
    st.markdown(f"<h3>{tx['reversal_prob']}</h3>", unsafe_allow_html=True)
    
    # Load Stats Cache JSON
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "b3_daytrade_stats.json")
    if not os.path.exists(json_path):
        st.warning("Base de estatísticas não encontrada localmente. Por favor, clique no botão 'Recalcular Base Estatística' no menu lateral para inicializar os dados históricos." if lang == "PT" else "Statistics database not found. Please click the 'Recalculate Stats Database' button in the sidebar to initialize historical data.")
        return
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            stats_db = json.load(f)
    except Exception as e:
        st.error(f"Erro ao abrir arquivo de cache estatístico: {e}")
        return
        
    asset_stats = stats_db.get(asset_code, {})
    if not asset_stats:
        st.error("Dados estatísticos para o ativo selecionado não encontrados no cache.")
        return
        
    threshold_data = asset_stats.get("threshold_data", {})
    available_thresholds = sorted([int(k) for k in threshold_data.keys()])
    
    if not available_thresholds:
        st.error("Nenhum limite (threshold) disponível no banco de dados.")
        return
        
    # Active Volatility Scanner Callout
    abs_dev = abs(deviation_pts)
    matched_th = None
    # Find largest threshold that is <= current deviation
    for th in reversed(available_thresholds):
        if abs_dev >= th:
            matched_th = th
            break
            
    if matched_th is not None:
        th_str = str(matched_th)
        th_info = threshold_data[th_str]
        best_cfg = th_info["best_configs"][0] if th_info["best_configs"] else {}
        
        st.markdown(
            f"<div style='background-color:#bf953f15; border:1px solid #bf953f; border-radius:8px; padding:15px; margin-bottom:20px; font-family:\"Inter\", sans-serif;'>"
            f"<div style='font-weight:900; color:#bf953f; font-size:13px; letter-spacing:0.5px; margin-bottom:5px;'>{tx['active_alert']}</div>"
            f"<p style='color:#ffffff; font-size:12px; margin:0; line-height:1.5;'>"
            + tx["active_signal"].format(
                asset=asset_option,
                dev=deviation_pts,
                th=matched_th,
                tp=best_cfg.get("target", "N/A"),
                prob=th_info["tp_probabilities"].get(str(best_cfg.get("target")), 0),
                exp=best_cfg.get("expectancy", 0)
            ) +
            f"</p></div>",
            unsafe_allow_html=True
        )
    else:
        th_min = available_thresholds[0]
        st.info(tx["alert_no_trigger"].format(th_min=th_min))
        
    # Subheader with date info
    db_date = stats_db.get("metadata", {}).get("last_updated", "N/A")
    st.markdown(f"<p style='font-size:11px; color:#888888; text-align:right;'>{tx['last_update'].format(date=db_date)}</p>", unsafe_allow_html=True)
    
    # Custom Selector for Threshold Investigation
    default_select_idx = available_thresholds.index(matched_th) if matched_th in available_thresholds else (len(available_thresholds) // 2)
    
    selected_th = st.selectbox(
        "INVESTIGAR DESVIO DA ABERTURA (Threshold)" if lang == "PT" else ("INVESTIGATE OPEN DEVIATION (Threshold)" if lang == "EN" else "INVESTIGAR DESVÍO DE LA APERTURA (Threshold)"),
        options=available_thresholds,
        index=default_select_idx,
        format_func=lambda x: f"{x:,.0f} {val_suffix}"
    )
    
    th_key = str(selected_th)
    th_info = threshold_data[th_key]
    
    # Trigger details
    st.markdown(
        f"**Frequência Histórica:** Ocorre em **{th_info['trigger_freq']:.1f}%** dos dias "
        f"({th_info['triggered_days']} de {asset_stats['total_days']} dias analisados).  \n"
        f"**Correção Média do Extremo:** **{th_info['avg_max_reversal']:.1f} {val_suffix}** de recuo a partir da máxima/mínima alcançada.  \n"
        f"**Resultado Médio no Fim do Dia:** **{th_info['avg_close_profit']:+.1f} {val_suffix}** (se mantido sem stops até o fechamento)."
    )
    
    # Two Columns for Tables
    st.write("")
    col_mat1, col_mat2 = st.columns([2, 3])
    
    with col_mat1:
        st.subheader(tx["raw_pullback"])
        
        raw_tp_list = []
        for tp_k, tp_v in th_info["tp_probabilities"].items():
            raw_tp_list.append({
                tx["target"]: f"{int(tp_k):,} {val_suffix}",
                tx["prob"]: f"{tp_v:.1f}%"
            })
        df_raw_tp = pd.DataFrame(raw_tp_list)
        st.dataframe(df_raw_tp, use_container_width=True, hide_index=True)
        
    with col_mat2:
        st.subheader(tx["best_configs"])
        
        best_configs = th_info["best_configs"]
        cfg_list = []
        for cfg in best_configs[:8]: # top 8
            cfg_list.append({
                "TP": f"{cfg['target']:,} {val_suffix}",
                "SL": f"{cfg['stop']:,} {val_suffix}",
                "Trades": cfg["trades"],
                "Win Rate": f"{cfg['win_rate']:.1f}%",
                "Expectancy": f"{cfg['expectancy']:+.1f} {val_suffix}"
            })
        df_cfg = pd.DataFrame(cfg_list)
        st.dataframe(df_cfg, use_container_width=True, hide_index=True)
        
        # Recommendation Banner
        if best_configs:
            top_cfg = best_configs[0]
            rec_tp = top_cfg["target"]
            rec_sl = top_cfg["stop"]
            rec_wr = top_cfg["win_rate"]
            rec_exp = top_cfg["expectancy"]
            
            st.markdown(
                f"<div style='background-color:#10141d; border-left:4px solid #bf953f; border-radius:4px; padding:10px; font-size:11.5px; color:#ffffff; font-family:\"Inter\", sans-serif;'>"
                f"💡 <b>RECOMENDAÇÃO QUANT:</b> O par ótimo de Stop/Alvo para o desvio de <b>{selected_th:,}</b> é Alvo de <b>{rec_tp:,} {val_suffix}</b> e Stop de <b>{rec_sl:,} {val_suffix}</b>. "
                f"Essa configuração gerou <b>{rec_wr:.1f}% de Win Rate</b> com expectativa matemática de <b>{rec_exp:+.1f} {val_suffix}</b> por operação."
                f"</div>",
                unsafe_allow_html=True
            )

    # 4. CHART
    st.write("")
    st.markdown(f"<h3>{tx['chart_title']}</h3>", unsafe_allow_html=True)
    
    chart_tf = st.radio(
        tx["select_tf"],
        options=[tx["tf_daily"], tx["tf_weekly"], tx["tf_h4"]],
        horizontal=True,
        key="daytrade_chart_tf"
    )
    
    if chart_tf == tx["tf_daily"]:
        chart_df = df_d1.tail(120)
        chart_name = "Daily (D1)"
    elif chart_tf == tx["tf_weekly"]:
        chart_df = df_w1.tail(80)
        chart_name = "Weekly (W1)"
    else:
        chart_df = df_h4.tail(100)
        chart_name = "4 Hours (H4)"
        
    # Plotly Line Chart
    fig = go.Figure()
    
    # Add Price Line
    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df['Close'],
        mode='lines',
        name='Preço' if lang == 'PT' else 'Price',
        line=dict(color='#bf953f', width=2)
    ))
    
    # Add SMA Line
    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df['SMA_111'],
        mode='lines',
        name='Média 111 SMA' if lang == 'PT' else '111 SMA',
        line=dict(color='#00ffa5', width=1.5, dash='dash')
    ))
    
    fig.update_layout(
        title=f"{asset_option} - {chart_name}",
        title_font=dict(color='#ffffff', size=14),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=True,
            gridcolor='#222831',
            tickfont=dict(color='#888888', size=10),
            title_font=dict(color='#ffffff')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#222831',
            tickfont=dict(color='#888888', size=10),
            title_font=dict(color='#ffffff')
        ),
        legend=dict(
            font=dict(color='#ffffff', size=10),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)
