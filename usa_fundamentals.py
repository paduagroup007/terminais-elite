import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime

# --- TRANSLATIONS DICTIONARY ---
usa_translations = {
    "PT": {
        "title_radar": "Radar de Comando | Wall Street Elite",
        "title_efficiency": "Análise de Eficiência Operacional (USA)",
        "title_profitability": "Resultados e Margens Líquidas (USA)",
        "title_solvency": "Solvência e Altman Z-Score (USA)",
        "title_valuation": "Relatório de Valuation (USD)",
        "title_data": "Dados Estruturados (Anual)",
        "revenue_ttm": "RECEITA ANUAL (LTM)",
        "profit_ttm": "LUCRO LÍQUIDO (LTM)",
        "cash_current": "CAIXA E EQUIVALENTES",
        "equity": "PATRIMÔNIO LÍQUIDO",
        "net_margin": "Margem Líquida %",
        "ebitda_margin": "Margem EBITDA %",
        "net_profit": "Lucro Líquido",
        "ebitda": "EBITDA",
        "revenue": "Receita Líquida",
        "long_term_overview": "Visão Geral de Longo Prazo",
        "revenue_vs_ebitda": "Receita vs EBITDA (Geração de Caixa)",
        "equity_evolution": "Evolução do Patrimônio Líquido",
        "debt_vs_cash": "Dívida vs Caixa (Liquidez)",
        "gross_debt": "Dívida Bruta",
        "price_now": "PREÇO ATUAL",
        "graham_price": "P. JUSTO (GRAHAM)",
        "fcd_price": "P. JUSTO (FCD)",
        "earnings_yield": "EARNINGS YIELD",
        "dividend_yield": "DIVIDEND YIELD",
        "roe": "ROE ANUAL",
        "debt_ebitda": "DÍVIDA LÍQ / EBITDA",
        "caixa_liq": "CAIXA LÍQ",
        "insight_ai": "CÉREBRO ELITE IA",
    },
    "EN": {
        "title_radar": "Command Radar | Wall Street Elite",
        "title_efficiency": "Operational Efficiency Analysis (USA)",
        "title_profitability": "Results and Net Margins (USA)",
        "title_solvency": "Solvency and Altman Z-Score (USA)",
        "title_valuation": "Valuation Report (USD)",
        "title_data": "Structured Data (Annual)",
        "revenue_ttm": "ANNUAL REVENUE (LTM)",
        "profit_ttm": "NET PROFIT (LTM)",
        "cash_current": "CASH & EQUIVALENTS",
        "equity": "TOTAL EQUITY",
        "net_margin": "Net Margin %",
        "ebitda_margin": "EBITDA Margin %",
        "net_profit": "Net Profit",
        "ebitda": "EBITDA",
        "revenue": "Net Revenue",
        "long_term_overview": "Long-Term Overview",
        "revenue_vs_ebitda": "Revenue vs EBITDA (Cash Generation)",
        "equity_evolution": "Total Equity Evolution",
        "debt_vs_cash": "Debt vs Cash (Liquidity)",
        "gross_debt": "Gross Debt",
        "price_now": "CURRENT PRICE",
        "graham_price": "GRAHAM FAIR PRICE",
        "fcd_price": "DCF FAIR PRICE",
        "earnings_yield": "EARNINGS YIELD",
        "dividend_yield": "DIVIDEND YIELD",
        "roe": "ANNUAL ROE",
        "debt_ebitda": "NET DEBT / EBITDA",
        "caixa_liq": "NET CASH",
        "insight_ai": "ELITE AI BRAIN",
    },
    "ES": {
        "title_radar": "Radar de Mando | Wall Street Elite",
        "title_efficiency": "Análisis de Eficiencia Operacional (USA)",
        "title_profitability": "Resultados y Margenes Netos (USA)",
        "title_solvency": "Solvencia y Altman Z-Score (USA)",
        "title_valuation": "Informe de Valuación (USD)",
        "title_data": "Datos Estructurados (Anual)",
        "revenue_ttm": "INGRESOS ANUALES (LTM)",
        "profit_ttm": "BENEFICIO NETO (LTM)",
        "cash_current": "CAJA Y EQUIVALENTES",
        "equity": "PATRIMONIO NETO",
        "net_margin": "Margen Neto %",
        "ebitda_margin": "Margen EBITDA %",
        "net_profit": "Beneficio Neto",
        "ebitda": "EBITDA",
        "revenue": "Ingresos Netos",
        "long_term_overview": "Visión General de Largo Plazo",
        "revenue_vs_ebitda": "Ingresos vs EBITDA (Generación de Caja)",
        "equity_evolution": "Evolución del Patrimonio Neto",
        "debt_vs_cash": "Deuda vs Caja (Liquidez)",
        "gross_debt": "Deuda Bruta",
        "price_now": "PRECIO ACTUAL",
        "graham_price": "P. JUSTO (GRAHAM)",
        "fcd_price": "P. JUSTO (FCD)",
        "earnings_yield": "EARNINGS YIELD",
        "dividend_yield": "DIVIDEND YIELD",
        "roe": "ROE ANUAL",
        "debt_ebitda": "DEUDA NET / EBITDA",
        "caixa_liq": "CAJA NETO",
        "insight_ai": "CEREBRO ELITE IA",
    }
}

# --- USD FORMATTER ---
def format_usd(val):
    if pd.isna(val):
        return "$ 0.00"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1e12:
        return f"{sign}$ {val / 1e12:.2f} T"
    elif val >= 1e9:
        return f"{sign}$ {val / 1e9:.2f} B"
    elif val >= 1e6:
        return f"{sign}$ {val / 1e6:.2f} M"
    else:
        return f"{sign}$ {val:,.2f}"

# --- LIVE YFINANCE STOCK PARSER ---
@st.cache_data(ttl=1800)
def fetch_us_company_financials(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow
    
    if fin.empty or bs.empty:
        return pd.DataFrame(), {}
        
    years = sorted(list(fin.columns))
    records = []
    
    for y in years:
        y_fin = fin[y] if y in fin.columns else pd.Series(dtype=float)
        y_bs = bs[y] if y in bs.columns else pd.Series(dtype=float)
        y_cf = cf[y] if y in cf.columns else pd.Series(dtype=float)
        
        rev = y_fin.get('Total Revenue', y_fin.get('Operating Revenue', np.nan))
        # Skip if revenue is nan or zero
        if pd.isna(rev) or rev == 0:
            continue
            
        net_inc = y_fin.get('Net Income', y_fin.get('Net Income Common Stockholders', 0.0))
        ebitda = y_fin.get('EBITDA', y_fin.get('Normalized EBITDA', 0.0))
        
        equity = y_bs.get('Stockholders Equity', y_bs.get('Common Stock Equity', 0.0))
        cash = y_bs.get('Cash Cash Equivalents And Short Term Investments', y_bs.get('Cash And Cash Equivalents', 0.0))
        debt = y_bs.get('Total Debt', y_bs.get('Total Liabilities Net Minority Interest', 0.0))
        
        working_cap = y_bs.get('Working Capital', 0.0)
        retained_earn = y_bs.get('Retained Earnings', 0.0)
        total_assets = y_bs.get('Total Assets', 0.0)
        total_liab = y_bs.get('Total Liabilities Net Minority Interest', 0.0)
        
        op_cash = y_cf.get('Operating Cash Flow', y_cf.get('Cash Flow From Continuing Operating Activities', 0.0))
        
        # Fallback if EBITDA is missing or bank
        if pd.isna(ebitda) or ebitda == 0.0:
            # Fallback EBITDA = Operating Income + Depreciation & Amortization
            op_inc = y_fin.get('Operating Income', 0.0)
            dep_amort = y_cf.get('Depreciation Amortization Depletion', y_cf.get('Depreciation And Amortization', 0.0))
            ebitda = float(op_inc) + float(dep_amort)
            
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
    
    metadata = {}
    try:
        fast = ticker.fast_info
        metadata['price'] = fast.get('lastPrice', 0.0) or fast.get('last_price', 0.0)
        metadata['shares'] = fast.get('shares', 0)
        metadata['marketCap'] = fast.get('marketCap', 0.0)
    except Exception:
        pass
        
    try:
        info = ticker.info
        if not metadata.get('price'):
            metadata['price'] = info.get('currentPrice', 0.0) or info.get('regularMarketPrice', 0.0)
        if not metadata.get('shares'):
            metadata['shares'] = info.get('sharesOutstanding', 0)
        if not metadata.get('marketCap'):
            metadata['marketCap'] = info.get('marketCap', 0.0)
            
        metadata['dy'] = info.get('dividendYield', 0.0) * 100 if info.get('dividendYield') else 0.0
        metadata['sector'] = info.get('sector', 'Technology')
        metadata['industry'] = info.get('industry', '')
        metadata['longName'] = info.get('longName', ticker_symbol)
    except Exception:
        pass
        
    if not metadata.get('price'):
        try:
            hist = ticker.history(period="1d")
            if not hist.empty:
                metadata['price'] = float(hist['Close'].iloc[-1])
        except Exception:
            pass
            
    # Default fallbacks
    if 'price' not in metadata: metadata['price'] = 0.0
    if 'shares' not in metadata: metadata['shares'] = 0
    if 'dy' not in metadata: metadata['dy'] = 0.0
    if 'longName' not in metadata: metadata['longName'] = ticker_symbol
    if 'sector' not in metadata: metadata['sector'] = ''
    if 'industry' not in metadata: metadata['industry'] = ''
    
    return df, metadata

# --- RENDERER FOR USA FUNDAMENTALS DASHBOARD ---
def render_us_fundamentals(lang, usa_ticker, active_module, risk_free_rate):
    t = usa_translations[lang]
    
    with st.spinner(f"Sincronizando Wall Street para {usa_ticker}..." if lang == "PT" else (f"Syncing Wall Street for {usa_ticker}..." if lang == "EN" else f"Sincronizando Wall Street para {usa_ticker}...")):
        df, metadata = fetch_us_company_financials(usa_ticker)
        
    if df.empty:
        st.error(
            "TICKER NÃO ENCONTRADO OU SEM DADOS HISTÓRICOS." if lang == "PT" else 
            ("TICKER NOT FOUND OR NO HISTORICAL DATA." if lang == "EN" else 
             "TICKER NO ENCONTRADO O SIN DATOS HISTÓRICOS.")
        )
        st.info(
            "Verifique se digitou o ticker de Wall Street corretamente (ex: AAPL, MSFT, NVDA, TSLA, JPM)." if lang == "PT" else
            ("Please verify if you entered the Wall Street ticker correctly (e.g., AAPL, MSFT, NVDA, TSLA, JPM)." if lang == "EN" else
             "Verifique si ingresó el ticker de Wall Street correctamente (ej: AAPL, MSFT, NVDA, TSLA, JPM).")
        )
        return

    # Basic Variables
    price_now = metadata['price']
    shares_total = metadata['shares']
    dy_atual = metadata['dy']
    is_bank = any(kw in metadata.get('sector', '').lower() or kw in metadata.get('industry', '').lower() for kw in ["bank", "financial", "insurance", "capital markets"])

    # Calculate metrics
    df['Margem_EBITDA'] = (df['EBITDA'] / df['Receita']) * 100
    df['Margem_Liquida'] = (df['Lucro'] / df['Receita']) * 100
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    receita_ttm = last['Receita']
    lucro_ttm = last['Lucro']
    ebitda_ttm = last['EBITDA']
    patrimonio_atual = last['Patrimonio']
    divida_liquida = last['Divida'] - last['Caixa']
    
    receita_prev_ttm = prev['Receita']
    lucro_prev_ttm = prev['Lucro']
    ebitda_prev_ttm = prev['EBITDA']
    
    roe = (lucro_ttm / patrimonio_atual) * 100 if patrimonio_atual > 0 else 0.0
    grow_rec = ((receita_ttm / receita_prev_ttm) - 1) * 100 if receita_prev_ttm > 0 else 0.0
    grow_luc = ((lucro_ttm / lucro_prev_ttm) - 1) * 100 if lucro_prev_ttm > 0 else 0.0
    
    lpa = lucro_ttm / shares_total if shares_total > 0 else 0.0
    vpa = patrimonio_atual / shares_total if shares_total > 0 else 0.0
    
    # Render Ticker Header
    st.markdown(f"""
    <div style='text-align:center; margin-bottom:20px;'>
        <h1 style='color:#bf953f; font-size:32px; font-weight:bold; margin-bottom:5px;'>{metadata['longName']}</h1>
        <p style='color:#ffffff; font-size:16px; margin:0;'>
            Ticker: <strong style='color:#bf953f;'>{usa_ticker}</strong> | 
            Setor: <strong>{metadata['sector']}</strong> | 
            Indústria: <strong>{metadata['industry']}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- 1. RADAR DE COMANDO (USA) ---
    if active_module == "Radar de Comando":
        st.markdown(f"<h2>{t['title_radar']}</h2>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1: st.metric(t["revenue_ttm"], format_usd(receita_ttm), f"{grow_rec:+.1f}%")
        with col2: st.metric(t["profit_ttm"], format_usd(lucro_ttm), f"{grow_luc:+.1f}%")
        with col3: st.metric(t["cash_current"], format_usd(last['Caixa']))
        with col4: st.metric(t["equity"], format_usd(last['Patrimonio']))
        
        # Plotly Area Chart for Revenue & Profit
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Data'], y=df['Receita'], name=t["revenue"], line=dict(color='#bf953f', width=3), fill='tozeroy', fillcolor='rgba(191, 149, 63, 0.05)'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['Lucro'], name=t["net_profit"], line=dict(color='#ffffff', width=3)))
        fig.update_layout(
            title=dict(text=t["long_term_overview"], font=dict(color='#d4af37', size=16)),
            template='plotly_dark',
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            xaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
            yaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
            legend=dict(font=dict(color='#ffffff'))
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- 2. EFICIÊNCIA OPERACIONAL (USA) ---
    elif active_module == "Eficiência Operacional":
        st.markdown(f"<h2>{t['title_efficiency']}</h2>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Receita'], name=t["revenue"], marker_color='#bf953f'))
            fig.add_trace(go.Bar(x=df['Data'], y=df['EBITDA'], name=t["ebitda"], marker_color='#ffffff'))
            fig.update_layout(
                title=dict(text=t["revenue_vs_ebitda"], font=dict(color='#d4af37', size=16)),
                barmode='group',
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                xaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                yaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                legend=dict(font=dict(color='#ffffff'))
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            ebitda_margin_val = last['Margem_EBITDA']
            fig_m = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = ebitda_margin_val,
                title = {'text': t["ebitda_margin"], 'font': {'color': '#d4af37', 'size': 14}},
                number = {'font': {'color': '#ffffff'}},
                gauge = {
                    'axis': {'range': [None, 60], 'tickfont': {'color': '#ffffff'}},
                    'bar': {'color': "#bf953f"},
                    'steps': [
                        {'range': [0, 15], 'color': "#161a23"},
                        {'range': [15, 30], 'color': "#212630"}
                    ],
                }
            ))
            fig_m.update_layout(
                template='plotly_dark',
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff')
            )
            st.plotly_chart(fig_m, use_container_width=True)

            # Cérebro Elite IA - Eficiência Operacional
            if is_bank:
                eff_desc = (
                    "**Insight Corporativo (Banco/Setor Financeiro):** Para instituições financeiras americanas, o EBITDA padrão não é um indicador ideal. "
                    f"A margem operacional é robusta e a receita cresceu **{grow_rec:+.1f}%** no acumulado anual. "
                    "Bancos de Wall Street operam de forma extremamente alavancada e rentabilizam seu balanço através de spreads em treasury yields e operações institucionais."
                )
            else:
                if ebitda_margin_val > 25:
                    rating = "EXCELENTE (Forte Vantagem Competitiva)" if lang == "PT" else "EXCELLENT (Strong Competitive Advantage)"
                    color = "#00ffa5"
                elif ebitda_margin_val > 15:
                    rating = "SAUDÁVEL (Moderada)" if lang == "PT" else "HEALTHY (Moderate)"
                    color = "lightgreen"
                else:
                    rating = "SOB PRESSÃO (Margem Estreita)" if lang == "PT" else "UNDER PRESSURE (Narrow Margin)"
                    color = "red"
                
                eff_desc = (
                    f"A **Margem EBITDA atual de {ebitda_margin_val:.1f}%** é classificada como <b style='color:{color};'>{rating}</b>. "
                    f"A receita líquida anual variou **{grow_rec:+.1f}%** YoY. "
                    "Empresas com margens acima de 25% em Wall Street geralmente possuem fossos econômicos (*Economic Moats*) formidáveis, permitindo forte poder de precificação e geração contínua de caixa livre."
                )

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(191, 149, 63, 0.08) 0%, rgba(7, 7, 10, 0.6) 100%); border: 1px solid rgba(191, 149, 63, 0.25); border-radius: 16px; padding: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);">
                <strong style="color: #bf953f; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">{t['insight_ai']} | {t['title_efficiency']}</strong>
                <p style="color: #e0e0e0; font-size: 12px; line-height: 1.6; margin: 10px 0 0 0;">
                    {eff_desc}
                </p>
            </div>
            """, unsafe_allow_html=True)

    # --- 3. ANÁLISE DE LUCRATIVIDADE (USA) ---
    elif active_module == "Análise de Lucratividade":
        st.markdown(f"<h2>{t['title_profitability']}</h2>", unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df['Data'], y=df['Lucro'], name=t["net_profit"], fill='tozeroy', line=dict(color='#bf953f')))
        fig2.add_trace(go.Scatter(x=df['Data'], y=df['Margem_Liquida'], name=t["net_margin"], yaxis='y2', line=dict(color='#ffffff', dash='dot')))
        fig2.update_layout(
            title=dict(text=t["title_profitability"], font=dict(color='#d4af37', size=16)),
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff'),
            xaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
            yaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
            yaxis2=dict(title=dict(text='Margem %', font=dict(color='#ffffff')), overlaying='y', side='right', gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
            legend=dict(font=dict(color='#ffffff'))
        )
        st.plotly_chart(fig2, use_container_width=True)

        net_margin = last['Margem_Liquida']
        if net_margin > 15:
            margin_rating = "EXCELENTE (Altamente Lucrativa)" if lang == "PT" else "EXCELLENT (Highly Profitable)"
            margin_color = "#00ffa5"
        elif net_margin > 6:
            margin_rating = "SAUDÁVEL (Adequada)" if lang == "PT" else "HEALTHY (Adequate)"
            margin_color = "lightgreen"
        else:
            margin_rating = "SOB PRESSÃO (Baixa Rentabilidade)" if lang == "PT" else "UNDER PRESSURE (Low Profitability)"
            margin_color = "red"

        luc_desc = (
            f"A **Margem Líquida consolidada de {net_margin:.1f}%** indica um perfil <span style='color:{margin_color}; font-weight:bold;'>{margin_rating}</span>. "
            f"O lucro líquido anual variou **{grow_luc:+.1f}%** YoY. "
            f"Com um **ROE atual de {roe:.1f}%**, a companhia demonstra forte eficiência de Wall Street na alocação de seu capital próprio para entregar dividendos e expansão aos acionistas."
        )

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(191, 149, 63, 0.08) 0%, rgba(7, 7, 10, 0.6) 100%); border: 1px solid rgba(191, 149, 63, 0.25); border-radius: 16px; padding: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);">
            <strong style="color: #bf953f; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">{t['insight_ai']} | Lucratividade e Retorno</strong>
            <p style="color: #e0e0e0; font-size: 12px; line-height: 1.6; margin: 10px 0 0 0;">
                {luc_desc}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- 4. SOLVÊNCIA PATRIMONIAL & ALTMAN Z-SCORE (USA) ---
    elif active_module == "Solvência Patrimonial":
        st.markdown(f"<h2>{t['title_solvency']}</h2>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=df['Data'], y=df['Patrimonio'], name=t["equity"], marker_color='#bf953f'))
            fig3.update_layout(
                title=dict(text=t["equity_evolution"], font=dict(color='#d4af37', size=16)),
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                xaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                yaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                legend=dict(font=dict(color='#ffffff'))
            )
            st.plotly_chart(fig3, use_container_width=True)
        with col_b:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(x=df['Data'], y=df['Divida'], name=t["gross_debt"], marker_color='#ffffff'))
            fig4.add_trace(go.Bar(x=df['Data'], y=df['Caixa'], name=t["cash_current"], marker_color='#bf953f'))
            fig4.update_layout(
                title=dict(text=t["debt_vs_cash"], font=dict(color='#d4af37', size=16)),
                barmode='group',
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ffffff'),
                xaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                yaxis=dict(gridcolor='rgba(191, 149, 63, 0.05)', tickfont=dict(color='#ffffff')),
                legend=dict(font=dict(color='#ffffff'))
            )
            st.plotly_chart(fig4, use_container_width=True)

        # Calculate Altman Z-Score
        market_cap = price_now * shares_total if shares_total > 0 else metadata.get('marketCap', 0.0)
        total_assets = last['Total_Assets']
        total_liabilities = last['Total_Liabilities']
        working_cap = last['Working_Capital']
        retained_earn = last['Retained_Earnings']
        ebitda = last['EBITDA']
        revenue = last['Receita']
        
        if total_assets > 0:
            X1 = working_cap / total_assets
            X2 = retained_earn / total_assets
            X3 = ebitda / total_assets
            X4 = market_cap / total_liabilities if total_liabilities > 0 else 999.0
            X5 = revenue / total_assets
            z_score = 1.2 * X1 + 1.4 * X2 + 3.3 * X3 + 0.6 * X4 + 0.999 * X5
        else:
            z_score = 0.0
            
        # Z-Score Status
        if z_score > 2.99:
            z_status = "ZONA SEGURA / SAFE ZONE (Excelente Solvência)" if lang == "PT" else "SAFE ZONE (Excellent Solvency)"
            z_color = "#00ffa5"
            z_desc = "O Z-Score está acima de 2.99, indicando uma probabilidade extremamente baixa de problemas financeiros ou falência contábil no curto/médio prazo. A saúde financeira está em perfeito estado."
        elif z_score >= 1.81:
            z_status = "ZONA CINZENTA / GREY ZONE (Risco Moderado)" if lang == "PT" else "GREY ZONE (Moderate Risk)"
            z_color = "#bf953f"
            z_desc = "O Z-Score está em patamar moderado (entre 1.81 e 2.99). A empresa possui solvência regular, mas o endividamento ou a contração operacional merecem monitoramento de longo prazo."
        else:
            z_status = "ZONA DE PERIGO / DISTRESS ZONE (Alerta de Insolvência)" if lang == "PT" else "DISTRESS ZONE (Insolvency Alert)"
            z_color = "#ff4b4b"
            z_desc = "ATENÇÃO: O Z-Score está abaixo de 1.81, classificando o ativo em alto risco financeiro. A empresa opera com alto endividamento bruto em relação aos seus ativos tangíveis, ou prejuízos operacionais agressivos. Risco elevado para investidores conservadores."

        # Piotroski F-Score (9 points)
        f_score = 0
        p_recs = []
        
        # 1. Net Income > 0
        if last['Lucro'] > 0:
            f_score += 1
            p_recs.append("✓ Net Income Positivo (+1)" if lang == "PT" else "✓ Positive Net Income (+1)")
        # 2. Operating Cash Flow > 0
        if last['Operating_Cash_Flow'] > 0:
            f_score += 1
            p_recs.append("✓ Fluxo de Caixa Operacional Positivo (+1)" if lang == "PT" else "✓ Positive Operating Cash Flow (+1)")
        # 3. ROA growth
        roa_now = last['Lucro'] / total_assets if total_assets > 0 else 0
        total_assets_prev = prev['Total_Assets']
        roa_prev = prev['Lucro'] / total_assets_prev if total_assets_prev > 0 else 0
        if roa_now > roa_prev:
            f_score += 1
            p_recs.append("✓ Crescimento de ROA (+1)" if lang == "PT" else "✓ ROA Growth (+1)")
        # 4. Cash Flow vs Net Income
        if last['Operating_Cash_Flow'] > last['Lucro']:
            f_score += 1
            p_recs.append("✓ Qualidade do Lucro (Caixa > Lucro) (+1)" if lang == "PT" else "✓ Quality of Earnings (Cash Flow > Net Income) (+1)")
        # 5. Leverage reduction
        lev_now = last['Divida'] / total_assets if total_assets > 0 else 0
        lev_prev = prev['Divida'] / total_assets_prev if total_assets_prev > 0 else 0
        if lev_now < lev_prev or (lev_now == 0 and lev_prev == 0):
            f_score += 1
            p_recs.append("✓ Alavancagem Reduzida ou Nula (+1)" if lang == "PT" else "✓ Reduced Leverage (+1)")
        # 6. Cash / Assets ratio growth
        cash_assets_now = last['Caixa'] / total_assets if total_assets > 0 else 0
        cash_assets_prev = prev['Caixa'] / total_assets_prev if total_assets_prev > 0 else 0
        if cash_assets_now > cash_assets_prev:
            f_score += 1
            p_recs.append("✓ Melhoria de Caixa/Ativo (+1)" if lang == "PT" else "✓ Cash to Assets Improved (+1)")
        # 7. EBITDA Margin Growth
        gm_now = last['EBITDA'] / last['Receita'] if last['Receita'] > 0 else 0
        gm_prev = prev['EBITDA'] / prev['Receita'] if prev['Receita'] > 0 else 0
        if gm_now > gm_prev:
            f_score += 1
            p_recs.append("✓ Crescimento de Margem Operacional (+1)" if lang == "PT" else "✓ Operating Margin Growth (+1)")
        # 8. Asset Turnover growth
        ato_now = last['Receita'] / total_assets if total_assets > 0 else 0
        ato_prev = prev['Receita'] / total_assets_prev if total_assets_prev > 0 else 0
        if ato_now > ato_prev:
            f_score += 1
            p_recs.append("✓ Eficiência de Ativos (Turnover) (+1)" if lang == "PT" else "✓ Asset Turnover Increased (+1)")
            
        f_score_pct = (f_score / 8.0) * 100

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(191, 149, 63, 0.08) 0%, rgba(7, 7, 10, 0.6) 100%); border: 1px solid rgba(191, 149, 63, 0.25); border-radius: 16px; padding: 25px; margin-top: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);">
            <h3 style="color: #bf953f; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-top: 0;">Solvência Corporativa: ALTMAN Z-SCORE</h3>
            <div style="font-size: 36px; font-weight: bold; color: {z_color}; margin: 10px 0;">{z_score:.2f}</div>
            <div style="font-weight: bold; color: #ffffff; margin-bottom: 10px;">{z_status}</div>
            <p style="color: #e0e0e0; font-size: 13px; line-height: 1.6; margin: 0 0 20px 0;">
                {z_desc}
            </p>
            <hr style="border: 0; border-top: 1px solid rgba(191, 149, 63, 0.15); margin: 20px 0;">
            <h3 style="color: #bf953f; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; margin-top: 0;">Pontuação de Força Fundamental: PIOTROSKI F-SCORE</h3>
            <div style="font-size: 36px; font-weight: bold; color: #bf953f; margin: 10px 0;">{f_score} / 8</div>
            <p style="color: #e0e0e0; font-size: 13px; line-height: 1.6; margin: 0 0 15px 0;">
                O Piotroski F-Score mede 8 parâmetros quantitativos YoY. Uma pontuação de <b>7 ou 8</b> indica excelente saúde, enquanto pontuações abaixo de <b>3</b> acendem o alerta de fraqueza nos lucros e passivos operacionais.
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                {" ".join([f"<span style='background-color:#161a23; color:#bf953f; border:1px solid #bf953f44; padding:5px 12px; border-radius:20px; font-size:11px; font-weight:600;'>{p}</span>" for p in p_recs])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- 5. VALUATION INTRÍNSECO (USA) ---
    elif active_module == "Valuation Intrínseco":
        st.markdown(f"<h2>{t['title_valuation']}</h2>", unsafe_allow_html=True)
        
        # Graham Formula
        # Price = sqrt(22.5 * LPA * VPA) adjusted by US Yields
        # ORIGINAL Graham Multiplier 22.5 assumes 4.4% risk free rate
        # Adjusted Graham multiplier = 22.5 * (4.4 / risk_free_rate)
        if risk_free_rate > 0:
            graham_mult = 22.5 * (4.4 / risk_free_rate)
        else:
            graham_mult = 22.5
            
        is_normalized = False
        lucro_para_valuation = lucro_ttm
        if lucro_ttm <= 0:
            is_normalized = True
            # Method 1: average historical profit
            lucro_normalizado = df['Lucro'].mean()
            # Method 2: ROE of 6% over equity
            if lucro_normalizado <= 0 and patrimonio_atual > 0:
                lucro_normalizado = patrimonio_atual * 0.06
            lucro_para_valuation = max(0.0, lucro_normalizado)
            
        lpa_val = lucro_para_valuation / shares_total if shares_total > 0 else 0.0
        
        if lpa_val > 0 and vpa > 0:
            preco_justo_graham = (graham_mult * lpa_val * vpa) ** 0.5
            margem_graham = ((preco_justo_graham / price_now) - 1) * 100 if price_now > 0 else 0
        else:
            preco_justo_graham, margem_graham = 0.0, 0.0
            
        # DCF / FCD dynamic model (Risk Free Rate + 5.0% Risk Premium)
        if shares_total > 0 and lucro_para_valuation > 0:
            rf_decimal = risk_free_rate / 100
            wacc = rf_decimal + 0.05
            g = 0.04
            if wacc <= g: wacc = g + 0.02
            
            valor_firma_fcd = lucro_para_valuation * (1 + g) / (wacc - g)
            preco_justo_fcd = valor_firma_fcd / shares_total
            margem_fcd = ((preco_justo_fcd / price_now) - 1) * 100 if price_now > 0 else 0
        else:
            preco_justo_fcd, margem_fcd = 0.0, 0.0
            
        # Metrics Display
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric(t["price_now"], f"$ {price_now:,.2f}")
        with col_m2: st.metric(t["graham_price"], f"$ {preco_justo_graham:,.2f}", f"{margem_graham:+.1f}%")
        with col_m3: st.metric(t["fcd_price"], f"$ {preco_justo_fcd:,.2f}", f"{margem_fcd:+.1f}%")
        
        # Interactive Margin of Safety
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(191, 149, 63, 0.08) 0%, rgba(7, 7, 10, 0.6) 100%); border: 1px solid rgba(191, 149, 63, 0.25); border-radius: 16px; padding: 25px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);">
            <strong style="color: #bf953f; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">{t['insight_ai']} | Avaliação e Desconto de Mercado</strong>
            <p style="color: #e0e0e0; font-size: 12.5px; line-height: 1.6; margin: 10px 0 0 0;">
                O valuation foi configurado de acordo com a taxa livre de risco de <b>{risk_free_rate:.1f}%</b> (Treasury de 10 anos americana). O multiplicador de Graham ajustado foi de <b>{graham_mult:.1f}x</b>. 
                <br><br>
                {"<b>Alerta de Lucro Normalizado:</b> Como o Lucro consolidado foi negativo ou muito reduzido, realizamos uma normalização matemática com base na média histórica operacional e patrimônio para evitar distorções no valuation de longo prazo." if is_normalized else "A empresa mantém lucros estáveis, o que valida a aplicação clássica direta das equações de Benjamin Graham."}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- 6. TABELA DE DADOS (USA) ---
    elif active_module == "Tabela de Dados":
        st.markdown(f"<h2>{t['title_data']}</h2>", unsafe_allow_html=True)
        # Format DataFrame nicely
        st.dataframe(
            df.style.format(precision=2).highlight_max(axis=0, color='#bf953f33'),
            use_container_width=True,
            height=450
        )
