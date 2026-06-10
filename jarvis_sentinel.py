import os
import sys
import time
import json
import datetime
import sqlite3
import threading
import requests
import yfinance as yf
import xml.etree.ElementTree as ET
import hashlib

# Garante suporte a caracteres Unicode/Emojis no console Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# =====================================================================
# CONFIGURAÇÃO DE CREDENCIAIS DO TELEGRAM (Preencha aqui ou no perfil)
# =====================================================================
TELEGRAM_BOT_TOKEN = ""    # Token do Bot do Telegram (obtido com @BotFather)
TELEGRAM_CHAT_ID = ""      # Seu Chat ID de Administrador (para receber auditoria dos sinais)
TELEGRAM_CHANNEL_ID = ""   # Chat ID do seu Canal Premium de Sinais (Ex: "-100...")

# =====================================================================
# CONFIGURAÇÕES E PARÂMETROS OPERACIONAIS DAS 10 ESTRATÉGIAS
# =====================================================================
STRATEGY_CONFIGS = {
    "WIN": {
        "ticker": "WIN=F",
        "fallback_ticker": "^BVSP",
        "multiplier": 1.0,
        "deviation": 300.0,
        "target": 250.0,
        "stop": 1200.0,
        "unit": "pts",
        "type": "B3",
        "name": "Mini Indice (WIN)"
    },
    "WDO": {
        "ticker": "BRL=X",
        "fallback_ticker": None,
        "multiplier": 1000.0,
        "deviation": 20.0,
        "target": 15.0,
        "stop": 50.0,
        "unit": "pts",
        "type": "B3",
        "name": "Mini Dolar (WDO)"
    },
    "CL=F": {
        "ticker": "CL=F",
        "fallback_ticker": None,
        "multiplier": 1.0,
        "deviation": 1.0,
        "target": 0.5,
        "stop": 3.0,
        "unit": "USD",
        "type": "GLOBAL",
        "name": "Petroleo WTI"
    },
    "GC=F": {
        "ticker": "GC=F",
        "fallback_ticker": None,
        "multiplier": 1.0,
        "deviation": 25.0,
        "target": 12.0,
        "stop": 50.0,
        "unit": "USD",
        "type": "GLOBAL",
        "name": "Ouro Spot"
    },
    "ES=F": {
        "ticker": "ES=F",
        "fallback_ticker": "SPY",
        "multiplier": 1.0,
        "deviation": 20.0,
        "target": 20.0,
        "stop": 50.0,
        "unit": "pts",
        "type": "GLOBAL_INDEX",
        "name": "S&P 500 (US500)"
    },
    "YM=F": {
        "ticker": "YM=F",
        "fallback_ticker": "DIA",
        "multiplier": 1.0,
        "deviation": 100.0,
        "target": 100.0,
        "stop": 400.0,
        "unit": "pts",
        "type": "GLOBAL_INDEX",
        "name": "Dow Jones (US30)"
    },
    "BTC-USD": {
        "ticker": "BTC-USD",
        "fallback_ticker": None,
        "multiplier": 1.0,
        "deviation": 1200.0,
        "target": 400.0,
        "stop": 2000.0,
        "unit": "USD",
        "type": "CRYPTO",
        "name": "Bitcoin (BTC)"
    },
    "ETH-USD": {
        "ticker": "ETH-USD",
        "fallback_ticker": None,
        "multiplier": 1.0,
        "deviation": 80.0,
        "target": 30.0,
        "stop": 100.0,
        "unit": "USD",
        "type": "CRYPTO",
        "name": "Ethereum (ETH)"
    },
    "GBPJPY=X": {
        "ticker": "GBPJPY=X",
        "fallback_ticker": None,
        "multiplier": 100.0,
        "deviation": 40.0,
        "target": 20.0,
        "stop": 200.0,
        "unit": "pips",
        "type": "GLOBAL",
        "name": "GBP/JPY"
    },
    "CHFJPY=X": {
        "ticker": "CHFJPY=X",
        "fallback_ticker": None,
        "multiplier": 100.0,
        "deviation": 30.0,
        "target": 15.0,
        "stop": 200.0,
        "unit": "pips",
        "type": "GLOBAL",
        "name": "CHF/JPY"
    }
}

# Tickers monitorados para o radar quantitativo diário de média 111 e desvio-padrão
SCAN_TICKERS = [
    # Índices e Bonds
    "^BVSP", "^GSPC", "^IXIC", "^DJI", "^FTSE", "^GDAXI", "^N225", "^TNX",
    # Forex
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "GBPJPY=X", "CHFJPY=X", "AUDJPY=X", "BRL=X",
    # Commodities
    "GC=F", "SI=F", "CL=F", "HG=F",
    # Crypto
    "BTC-USD", "ETH-USD", "SOL-USD",
    # Equities
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN"
]

# =====================================================================
# GERENCIAMENTO DE BANCO DE DADOS (SQLite)
# =====================================================================
DB_FILE = os.path.join(os.path.dirname(__file__), "sentinel_trades.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT NOT NULL,
            date TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            target_price REAL NOT NULL,
            stop_price REAL NOT NULL,
            status TEXT NOT NULL, -- OPEN, CLOSED_TP, CLOSED_SL, CLOSED_TIME
            close_price REAL,
            pnl REAL,
            opened_at TEXT NOT NULL,
            closed_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_reference (
            date TEXT NOT NULL,
            asset TEXT NOT NULL,
            open_price REAL NOT NULL,
            upper_limit REAL NOT NULL,
            lower_limit REAL NOT NULL,
            status TEXT NOT NULL, -- PENDING, ACTIVE, COMPLETED
            PRIMARY KEY (date, asset)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_news (
            title_hash TEXT PRIMARY KEY,
            sent_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_reports (
            report_type TEXT NOT NULL,
            date TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            PRIMARY KEY (report_type, date)
        )
    """)
    
    conn.commit()
    conn.close()

# =====================================================================
# CARREGAMENTO DINÂMICO DE CREDENCIAIS
# =====================================================================
def get_telegram_credentials():
    """Retorna bot_token, chat_id e channel_id prioritariamente."""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHANNEL_ID
    
    bot_token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    channel_id = TELEGRAM_CHANNEL_ID
    
    # Se não configurado no topo, lê do perfil do usuário
    try:
        profile_path = os.path.join(os.path.dirname(__file__), "user_profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
                if not bot_token:
                    bot_token = profile.get("telegram_bot_token", "")
                if not chat_id:
                    chat_id = profile.get("telegram_chat_id", "")
                if not channel_id:
                    channel_id = profile.get("telegram_channel_id", "")
    except Exception:
        pass
        
    return bot_token, chat_id, channel_id

def send_sentinel_alert(message, is_signal=True, custom_chat_id=None):
    """Envia um alerta quantitativo formatado para o Telegram com divisão em chunks e fallback em caso de erro de markdown."""
    token, chat, channel = get_telegram_credentials()
    if not token:
        print(f"[Sentinel Offline Alert]: {message}")
        return False
        
    target_chats = []
    if custom_chat_id:
        target_chats.append(custom_chat_id)
    elif is_signal and channel:
        target_chats.append(channel)
        if chat and chat != channel:
            target_chats.append(chat)
    else:
        if chat:
            target_chats.append(chat)
            
    if not target_chats:
        print(f"[Sentinel Offline Alert - Sem chat]: {message}")
        return False
        
    # Divide a mensagem em pedaços de no máximo 4000 caracteres
    chunks = []
    text_remaining = message
    while len(text_remaining) > 4000:
        split_idx = text_remaining.rfind('\n', 0, 4000)
        if split_idx == -1 or split_idx < 2000:
            split_idx = 4000
        chunks.append(text_remaining[:split_idx])
        text_remaining = text_remaining[split_idx:].lstrip()
    chunks.append(text_remaining)
    
    success = True
    for chat_id in target_chats:
        for chunk in chunks:
            if not chunk:
                continue
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown"
            }
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code != 200:
                    print(f"[Sentinel Warning] Falha ao enviar chunk com Markdown para {chat_id} ({response.status_code}). Tentando fallback sem formatação...")
                    payload.pop("parse_mode", None)
                    response_fallback = requests.post(url, json=payload, timeout=10)
                    if response_fallback.status_code != 200:
                        success = False
                        print(f"[Sentinel Error] Falha definitiva no chunk para {chat_id}: {response_fallback.text}")
            except Exception as e:
                success = False
                print(f"[Sentinel Error] Falha ao enviar chunk para {chat_id}: {e}")
                
    return success

# =====================================================================
# TELEMETRIA DE MERCADO E VERIFICAÇÕES
# =====================================================================
def fetch_realtime_data():
    """Coleta o preço atual, abertura, máximo e mínimo do dia para os 10 ativos."""
    data = {}
    for asset, config in STRATEGY_CONFIGS.items():
        ticker_name = config["ticker"]
        fallback = config["fallback_ticker"]
        try:
            t_obj = yf.Ticker(ticker_name)
            df = t_obj.history(period="1d")
            if df.empty and fallback:
                t_obj = yf.Ticker(fallback)
                df = t_obj.history(period="1d")
                
            if not df.empty:
                open_price = float(df['Open'].iloc[-1])
                high_price = float(df['High'].iloc[-1])
                low_price = float(df['Low'].iloc[-1])
                current_price = float(df['Close'].iloc[-1])
                date_str = df.index[-1].strftime("%Y-%m-%d")
                
                data[asset] = {
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "current": current_price,
                    "date": date_str
                }
        except Exception as e:
            print(f"[Sentinel yfinance] Erro ao baixar {asset}: {e}")
    return data

def check_market_hours(asset_type):
    """Retorna True se o mercado do ativo estiver aberto."""
    now = datetime.datetime.now()
    if asset_type == "CRYPTO":
        return True
        
    day = now.weekday()
    hour = now.hour
    
    if day == 4 and hour >= 18:
        return False
    if day == 5:
        return False
    if day == 6 and hour < 18:
        return False
        
    if asset_type == "B3":
        if day in [5, 6]:
            return False
        if hour < 9 or hour >= 18:
            return False
            
    return True

# =====================================================================
# MONITOR DE PREÇOS (Sinalizador Intraday)
# =====================================================================
def run_sentinel_monitor():
    """Worker de monitoramento quantitativo (Sinais suspensos para refinamento de backtests M15)."""
    print("[Sentinel Monitor] Loop de cotações ativo (Envio de sinais suspenso)...")
    
    # Envia notificação de inicialização para o Administrador
    send_sentinel_alert(
        "🛡️ **JARVIS SENTINEL | DEPLOY AUTÔNOMO**\n\n"
        "O monitoramento de mercado foi inicializado em modo independente.\n"
        "Atenção: O envio de novos SINAIS de trade está temporariamente SUSPENSO para refinamento de backtests com dados M15.",
        is_signal=False
    )
    
    while True:
        try:
            prices = fetch_realtime_data()
            if not prices:
                time.sleep(30)
                continue
                
            now_dt = datetime.datetime.now()
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for asset, config in STRATEGY_CONFIGS.items():
                if asset not in prices:
                    continue
                    
                p_data = prices[asset]
                asset_type = config["type"]
                
                if not check_market_hours(asset_type):
                    continue
                    
                open_val = p_data["open"]
                curr_val = p_data["current"]
                session_date = p_data["date"]
                
                multiplier = config["multiplier"]
                dev_val = config["deviation"] / multiplier
                
                upper_limit = open_val + dev_val
                lower_limit = open_val - dev_val
                
                # Assegurar registro de referência
                cursor.execute(
                    "SELECT * FROM daily_reference WHERE date = ? AND asset = ?",
                    (session_date, asset)
                )
                ref = cursor.fetchone()
                if not ref:
                    cursor.execute(
                        "INSERT INTO daily_reference (date, asset, open_price, upper_limit, lower_limit, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (session_date, asset, open_val, upper_limit, lower_limit, "PENDING")
                    )
                    conn.commit()
                
                # SINAIS DE ENTRADA E SAÍDA DE TRADE SUSPENSOS TEMPORARIAMENTE
                # Aguardando refinamento de backtest de timeframe M15 para recalibração estatística.
                pass
            
            conn.close()
        except Exception as e:
            print(f"[Sentinel Loop Error]: {e}")
            
        time.sleep(30)

# =====================================================================
# COMANDOS DE DIAGNÓSTICO E PRESTAÇÃO DE CONTAS
# =====================================================================
def get_sentinel_status():
    """Gera um status do monitoramento diário atual."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_dt = datetime.datetime.now()
    today_str = now_dt.strftime("%Y-%m-%d")
    
    cursor.execute("SELECT * FROM daily_reference WHERE date = ?", (today_str,))
    references = cursor.fetchall()
    
    if not references:
        conn.close()
        return "🛡️ **Jarvis Sentinel:** Nenhuma referência de cotação diária criada ainda para hoje."
        
    msg = "🛡️ **Jarvis Sentinel | Telemetria Diária:**\n\n"
    for ref in references:
        asset = ref["asset"]
        config = STRATEGY_CONFIGS.get(asset, {})
        status = ref["status"]
        
        status_icon = "⚪"
        if status == "ACTIVE":
            status_icon = "🟡"
        elif status == "COMPLETED":
            status_icon = "🟢"
            
        curr_price_str = "N/A"
        try:
            t_obj = yf.Ticker(config["ticker"])
            df = t_obj.history(period="1d")
            if not df.empty:
                curr_price_str = f"{df['Close'].iloc[-1]:.4f}"
        except Exception:
            pass
            
        msg += (
            f"{status_icon} *{config.get('name', asset)}*:\n"
            f"  - Abertura: `{ref['open_price']:.4f}` | Atual: `{curr_price_str}`\n"
            f"  - Limite Venda (Teto): `{ref['upper_limit']:.4f}`\n"
            f"  - Limite Compra (Piso): `{ref['lower_limit']:.4f}`\n"
            f"  - Status: `{status}`\n\n"
        )
    
    conn.close()
    return msg

def get_sentinel_trades():
    """Retorna os últimos 10 trades realizados e salvos no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "💼 **Jarvis Sentinel:** Nenhuma operação realizada ou gravada ainda."
        
    msg = "💼 **Jarvis Sentinel | Últimos 10 Trades:**\n\n"
    for r in rows:
        icon = "🟢" if r["pnl"] >= 0 else "🔴"
        pnl_symbol = "+" if r["pnl"] >= 0 else ""
        config = STRATEGY_CONFIGS.get(r["asset"], {})
        
        msg += (
            f"{icon} *{config.get('name', r['asset'])}* ({r['date']}):\n"
            f"  - Operação: `{r['direction']}` | Entrada: `{r['entry_price']:.4f}`\n"
            f"  - Saída: `{r['close_price']:.4f}` | Status: `{r['status']}`\n"
            f"  - P&L: `{pnl_symbol}{r['pnl']:.1f} {config.get('unit', '')}`\n\n"
        )
    return msg

def get_sentinel_performance():
    """Compila estatísticas de assertividade acumuladas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM trades WHERE status != 'OPEN'")
    trades = cursor.fetchall()
    conn.close()
    
    if not trades:
        return "📈 **Jarvis Sentinel:** Nenhuma estatística acumulada disponível."
        
    total = len(trades)
    wins = len([t for t in trades if t["pnl"] >= 0])
    losses = total - wins
    win_rate = (wins / total) * 100 if total > 0 else 0
    
    total_brl = 0.0
    total_usd = 0.0
    
    for t in trades:
        asset = t["asset"]
        pnl = t["pnl"]
        
        if asset == "WIN":
            total_brl += pnl * 0.20
        elif asset == "WDO":
            total_brl += pnl * 10.00
        else:
            if asset in ["GBPJPY=X", "CHFJPY=X"]:
                total_usd += pnl
            elif asset == "GC=F":
                total_usd += pnl
            elif asset == "CL=F":
                total_usd += pnl * 10.0
            elif asset == "ES=F":
                total_usd += pnl * 10.0
            elif asset == "YM=F":
                total_usd += pnl * 1.0
            else:
                total_usd += pnl
                
    total_merged_brl = total_brl + (total_usd * 5.50)
    
    msg = (
        "📈 **Jarvis Sentinel | Performance Consolidada:**\n\n"
        f"• **Total de Trades Fechados**: `{total}`\n"
        f"• **Vitórias**: `{wins}` | **Derrotas**: `{losses}`\n"
        f"• **Taxa de Acerto**: `{win_rate:.2f}%`\n\n"
        f"💵 **P&L Estimado Acumulado:**\n"
        f"• Em Contratos B3: `R$ {total_brl:,.2f} BRL`\n"
        f"• Em CFDs Globais: `$ {total_usd:,.2f} USD`\n"
        f"• **Resultado Total Consolidado**: `R$ {total_merged_brl:,.2f} BRL`\n\n"
        f"💡 *Assertividade calculada a partir de operações em tempo real.*"
    )
    return msg

# =====================================================================
# AGENDADOR E MOTOR DE INTELIGÊNCIA MACRO E QUANT (Perfect Life Chronos)
# =====================================================================

def get_brt_time():
    """Retorna o datetime atual no horário de Brasília (UTC-3)."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    brt_now = utc_now - datetime.timedelta(hours=3)
    return brt_now

def is_news_allowed_hour():
    """Retorna True se estivermos na janela autorizada para notícias (06:00 às 00:00 BRT)."""
    brt_now = get_brt_time()
    return 6 <= brt_now.hour < 24

def ask_gemini(system_instruction, user_prompt, use_search=True):
    """Consulta a API do Gemini com instruções específicas e ferramenta de busca do Google."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    key_path = os.path.join(os.path.dirname(__file__), "gemini.key")
    if not api_key and os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                api_key = f.read().strip()
        except Exception:
            pass
            
    if not api_key:
        try:
            profile_path = os.path.join(os.path.dirname(__file__), "user_profile.json")
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                    api_key = profile.get("gemini_api_key", "")
        except Exception:
            pass
            
    if not api_key:
        print("[Sentinel Gemini] Erro: API Key não encontrada.")
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {
                "role": "user", 
                "parts": [
                    {"text": f"[INSTRUÇÕES DO SISTEMA: {system_instruction}]"},
                    {"text": user_prompt}
                ]
            }
        ]
    }
    
    if use_search:
        payload["tools"] = [{"google_search": {}}]
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"]
        print(f"[Sentinel Gemini Error] Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[Sentinel Gemini Exception]: {e}")
        
    return None

def get_morning_briefing_market_data():
    """Busca cotações matinais de abertura/fechamento global."""
    tickers = {
        "Nikkei 225": "^N225",
        "Hang Seng": "^HSI",
        "FTSE 100": "^FTSE",
        "DAX": "^GDAXI",
        "Ouro Spot": "GC=F",
        "Petróleo WTI": "CL=F",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "DXY": "DX-Y.NYB",
        "VIX": "^VIX",
        "US 10Y Treasury": "^TNX"
    }
    lines = []
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            df = t.history(period="2d")
            if len(df) >= 2:
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                lines.append(f"- {name} ({sym}): {curr:.2f} ({change:+.2f}%)")
            elif not df.empty:
                curr = df['Close'].iloc[-1]
                lines.append(f"- {name} ({sym}): {curr:.2f}")
            else:
                lines.append(f"- {name} ({sym}): N/A")
        except Exception:
            lines.append(f"- {name} ({sym}): Erro de cotação")
    return "\n".join(lines)

def send_morning_briefing():
    """Gera e emite o Perfect Life Morning Briefing para o canal."""
    data_str = get_morning_briefing_market_data()
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o seu assistente virtual de inteligência financeira. "
        "Você deve redigir o 'Perfect Life Morning Briefing', um relatório macro e de abertura matinal de altíssimo nível, elegante e perspicaz. "
        "Adote o tom característico do Jarvis: extremamente educado, sofisticado, técnico e direto, chamando a audiência de 'Senhores' ou 'Membros Premium'. "
        "Use o Google Search para complementar com as principais manchetes políticas/econômicas mundiais de hoje, a agenda de indicadores econômicos de alto impacto para o dia e possíveis balanços/dividendos relevantes. "
        "Crucial: Mantenha segredo total sobre nossas regras operacionais quantitativas internas (não mencione desvios operacionais ou pontos de entrada). "
        "Formate com Markdown premium com emojis elegantes."
    )
    user_prompt = f"Aqui estão os dados recentes dos mercados globais:\n{data_str}\n\nPor favor, escreva o Morning Briefing de hoje."
    report = ask_gemini(system_instruction, user_prompt, use_search=True)
    if report:
        return send_sentinel_alert(report, is_signal=True)
    return False

def get_ny_open_market_data():
    """Busca cotações da abertura de Nova York."""
    tickers = {
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Dow Jones": "^DJI",
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Nvidia": "NVDA",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META"
    }
    lines = []
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            df = t.history(period="2d")
            if len(df) >= 2:
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                lines.append(f"- {name} ({sym}): {curr:.2f} ({change:+.2f}%)")
            elif not df.empty:
                curr = df['Close'].iloc[-1]
                lines.append(f"- {name} ({sym}): {curr:.2f}")
            else:
                lines.append(f"- {name} ({sym}): N/A")
        except Exception:
            lines.append(f"- {name} ({sym}): Erro de cotação")
    return "\n".join(lines)

def send_ny_open_impact():
    """Gera e emite o Wall Street Open Impact para o canal."""
    data_str = get_ny_open_market_data()
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o seu assistente virtual de inteligência financeira. "
        "Você deve redigir o relatório 'Wall Street Open Impact' analisando a primeira hora de negócios em Nova York. "
        "Use o tom sofisticado, polido e autoritativo do Jarvis. "
        "Use o Google Search para puxar o sentimento atual que move as Big Techs hoje e possíveis reações a relatórios econômicos divulgados às 09:30/11:00 EST. "
        "Crucial: Não revele qualquer segredo operacional. "
        "Formate com Markdown premium."
    )
    user_prompt = f"Aqui estão os dados após uma hora de pregão em Nova York:\n{data_str}\n\nPor favor, escreva o relatório."
    report = ask_gemini(system_instruction, user_prompt, use_search=True)
    if report:
        return send_sentinel_alert(report, is_signal=True)
    return False

def get_london_close_market_data():
    """Busca cotações do fechamento europeu."""
    tickers = {
        "FTSE 100 (Londres)": "^FTSE",
        "DAX (Frankfurt)": "^GDAXI",
        "CAC 40 (Paris)": "^FCHI",
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X"
    }
    lines = []
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            df = t.history(period="2d")
            if len(df) >= 2:
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                lines.append(f"- {name} ({sym}): {curr:.4f} ({change:+.2f}%)")
            elif not df.empty:
                curr = df['Close'].iloc[-1]
                lines.append(f"- {name} ({sym}): {curr:.4f}")
            else:
                lines.append(f"- {name} ({sym}): N/A")
        except Exception:
            lines.append(f"- {name} ({sym}): Erro de cotação")
    return "\n".join(lines)

def send_london_close_bulletin():
    """Gera e emite o London Close Bulletin para o canal."""
    data_str = get_london_close_market_data()
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o seu assistente virtual de inteligência financeira. "
        "Você deve redigir o 'London Close Bulletin', resumindo o desfecho da sessão europeia e a movimentação do EURUSD/GBPUSD. "
        "Use o tom clássico e refinado do Jarvis. "
        "Use o Google Search para agregar o contexto por trás do comportamento das bolsas europeias no fechamento e a dinâmica de liquidez global. "
        "Crucial: Não abra estratégias confidenciais. "
        "Formate com Markdown premium."
    )
    user_prompt = f"Aqui estão os dados pós-fechamento europeu:\n{data_str}\n\nPor favor, escreva o boletim."
    report = ask_gemini(system_instruction, user_prompt, use_search=True)
    if report:
        return send_sentinel_alert(report, is_signal=True)
    return False

def scan_insider_purchases():
    """Rastreia compras significativas de executivos de grandes corporações (> $100k)."""
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC"]
    purchases = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            insiders = t.insider_transactions
            if insiders is not None and not insiders.empty:
                for idx, row in insiders.iterrows():
                    text_val = str(row.get('Text', '')).lower()
                    trans_val = str(row.get('Transaction', '')).lower()
                    val_amt = row.get('Value', 0)
                    if ('purchase' in text_val or 'purchase' in trans_val) and val_amt >= 100000:
                        start_date = str(row.get('Start Date', ''))
                        shares = row.get('Shares', 0)
                        insider = row.get('Insider', 'N/A')
                        pos = row.get('Position', 'Insider')
                        url_filing = row.get('URL', '')
                        purchases.append({
                            "Ticker": sym,
                            "Insider": insider,
                            "Position": pos,
                            "Shares": shares,
                            "Value": val_amt,
                            "Date": start_date,
                            "URL": url_filing
                        })
        except Exception as e:
            print(f"[Insider Tracker] Erro ao buscar {sym}: {e}")
    return purchases

def get_sentinel_daily_pnl_summary():
    """Retorna um resumo elegante do desempenho do robô no dia atual."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today_str = get_brt_time().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM trades WHERE date = ?", (today_str,))
    trades = cursor.fetchall()
    conn.close()
    
    if not trades:
        return "Nenhuma operação quantitativa finalizada pelo robô no dia de hoje."
        
    lines = []
    for t in trades:
        icon = "🟢" if t["pnl"] >= 0 else "🔴"
        pnl_sign = "+" if t["pnl"] >= 0 else ""
        config = STRATEGY_CONFIGS.get(t["asset"], {})
        unit = config.get("unit", "")
        lines.append(f"- {icon} {config.get('name', t['asset'])}: {t['direction']} | Entrada: {t['entry_price']:.4f} | Saída: {t['close_price']:.4f} | P&L: {pnl_sign}{t['pnl']:.1f} {unit} ({t['status']})")
    return "\n".join(lines)

def get_closing_market_data():
    """Coleta cotações de fechamento diário."""
    tickers = {
        "Ibovespa": "^BVSP",
        "Dólar BRL": "BRL=X",
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Dow Jones": "^DJI",
        "Ouro Spot": "GC=F",
        "Petróleo WTI": "CL=F",
        "Bitcoin": "BTC-USD"
    }
    lines = []
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            df = t.history(period="2d")
            if len(df) >= 2:
                curr = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                change = ((curr - prev) / prev) * 100
                lines.append(f"- {name} ({sym}): {curr:.2f} ({change:+.2f}%)")
            elif not df.empty:
                curr = df['Close'].iloc[-1]
                lines.append(f"- {name} ({sym}): {curr:.2f}")
            else:
                lines.append(f"- {name} ({sym}): N/A")
        except Exception:
            lines.append(f"- {name} ({sym}): Erro de cotação")
    return "\n".join(lines)

def send_closing_report():
    """Gera e emite o Perfect Life Closing Report & Whale Tracker para o canal."""
    market_data = get_closing_market_data()
    pnl_summary = get_sentinel_daily_pnl_summary()
    
    insider_list = scan_insider_purchases()
    insider_str = ""
    if insider_list:
        insider_list = sorted(insider_list, key=lambda x: x["Date"], reverse=True)[:5]
        for p in insider_list:
            insider_str += (
                f"- **{p['Ticker']}**: {p['Insider']} ({p['Position']}) adquiriu {p['Shares']:,} ações "
                f"no montante de **${p['Value']:,.2f}** em {p['Date']}. [Form 4]({p['URL']})\n"
            )
    else:
        insider_str = "Nenhuma compra institucional ou corporativa de insiders relevante (> $100k) detectada hoje."
        
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o seu assistente virtual de inteligência financeira. "
        "Você deve redigir o 'Perfect Life Closing Report & Whale Tracker' (relatório de fechamento diário e fluxo de grandes investidores/insiders). "
        "Adote o estilo Jarvis: requintado, preciso e confiável. "
        "Use o Google Search para contextualizar o fechamento da B3, das bolsas de Nova York e principais eventos corporativos do dia. "
        "Apresente também o P&L diário das estratégias quantitativas Sentinel de forma polida. "
        "Apresente de maneira muito especial e atraente a seção de Compras de Insiders (Smart Money), enfatizando que executivos de elite estão comprando suas próprias ações. "
        "Crucial: NÃO apresente parâmetros ou regras proprietárias internas do Sentinel. "
        "Formate com Markdown premium."
    )
    
    user_prompt = (
        f"FECHAMENTO DO MERCADO:\n{market_data}\n\n"
        f"PNL DIÁRIO DO SENTINEL:\n{pnl_summary}\n\n"
        f"COMPRAS DE INSIDERS HOJE:\n{insider_str}\n\n"
        "Por favor, estruture e redija o relatório de fechamento."
    )
    
    report = ask_gemini(system_instruction, user_prompt, use_search=True)
    if report:
        return send_sentinel_alert(report, is_signal=True)
    return False

def run_daily_ema_scan():
    """Varre 30 ativos globais para identificar cruzamentos ou afastamentos extremos da EMA 111."""
    alerts = []
    for sym in SCAN_TICKERS:
        try:
            t = yf.Ticker(sym)
            df = t.history(period="1y")
            if len(df) < 120:
                continue
                
            df['EMA_111'] = df['Close'].ewm(span=111, adjust=False).mean()
            
            # Cruzamento
            prev_close = df['Close'].iloc[-2]
            prev_ema = df['EMA_111'].iloc[-2]
            curr_close = df['Close'].iloc[-1]
            curr_ema = df['EMA_111'].iloc[-1]
            
            crossover = None
            if prev_close <= prev_ema and curr_close > curr_ema:
                crossover = "Cruzamento BULLISH (Preço cruzou a média de 111 períodos para CIMA)"
            elif prev_close >= prev_ema and curr_close < curr_ema:
                crossover = "Cruzamento BEARISH (Preço cruzou a média de 111 períodos para BAIXO)"
                
            # Desvio-padrão (z-score da distância em %)
            dist = (df['Close'] - df['EMA_111']) / df['EMA_111']
            lookback = dist.iloc[-100:]
            mean_dist = lookback.mean()
            std_dist = lookback.std()
            curr_dist = dist.iloc[-1]
            
            z_score = (curr_dist - mean_dist) / std_dist if std_dist > 0 else 0
            
            deviation_alert = None
            if z_score >= 2.0:
                deviation_alert = f"Afastamento Extremo de Alta (Z-Score: +{z_score:.2f} desvios-padrão da média 111)"
            elif z_score <= -2.0:
                deviation_alert = f"Afastamento Extremo de Baixa (Z-Score: {z_score:.2f} desvios-padrão da média 111)"
                
            if crossover or deviation_alert:
                name = STRATEGY_CONFIGS.get(sym, {}).get("name", sym)
                alerts.append({
                    "ticker": sym,
                    "name": name,
                    "price": curr_close,
                    "ema_111": curr_ema,
                    "crossover": crossover,
                    "deviation": deviation_alert
                })
        except Exception as e:
            print(f"[EMA Scan] Erro ao varrer {sym}: {e}")
            
    if not alerts:
        return False
        
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o seu assistente virtual de inteligência financeira. "
        "Você recebeu alertas do Radar de Média Móvel de 111 períodos e Desvios-Padrão Extremos das últimas 100 sessões. "
        "Redija um relatório sofisticado detalhando estes sinais, explicando de forma qualitativa o que significa "
        "um cruzamento ou um afastamento estatístico extremo de alta/baixa (exaustão ou reversão) de forma didática e muito profissional. "
        "Use o tom requintado e perspicaz do Jarvis. "
        "Crucial: NÃO revele parâmetros de trading confidenciais de nossas outras estratégias proprietárias de desvio do dia. "
        "Formate com Markdown premium."
    )
    
    alerts_str = json.dumps(alerts, indent=2, ensure_ascii=False)
    user_prompt = f"Aqui estão as anomalias e cruzamentos quantitativos detectados:\n{alerts_str}\n\nPor favor, escreva o relatório."
    
    report = ask_gemini(system_instruction, user_prompt, use_search=False)
    if report:
        return send_sentinel_alert(report, is_signal=True)
    return False

def fetch_news_headlines():
    """Coleta manchetes econômicas recentes de fontes confiáveis (G1 e CNBC)."""
    feeds = [
        "https://g1.globo.com/rss/g1/economia/",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    ]
    items = []
    for url in feeds:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text
                    link = item.find("link").text
                    desc = item.find("description")
                    desc_text = desc.text if desc is not None else ""
                    items.append({
                        "title": title,
                        "link": link,
                        "description": desc_text
                    })
        except Exception as e:
            print(f"[News Parser] Erro ao carregar feed {url}: {e}")
    return items

def is_news_already_sent(title):
    """Verifica se uma determinada notícia já foi postada anteriormente."""
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sent_news WHERE title_hash = ?", (title_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def mark_news_as_sent(title):
    """Marca uma notícia como postada no banco de dados SQLite."""
    title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sent_news (title_hash, sent_at) VALUES (?, ?)", (title_hash, datetime.datetime.now().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def check_and_send_breaking_news():
    """Filtra e analisa se as notícias recentes são de alto impacto de mercado e emite alertas (06:00 às 00:00)."""
    if not is_news_allowed_hour():
        return
        
    all_news = fetch_news_headlines()
    unsent_news = []
    for n in all_news:
        if not is_news_already_sent(n["title"]):
            unsent_news.append(n)
            
    if not unsent_news:
        return
        
    for n in unsent_news:
        mark_news_as_sent(n["title"])
        
    system_instruction = (
        "Você é o Jarvis da Perfect Life - Elite Investors, o curador de inteligência financeira. "
        "Você está revisando um conjunto de manchetes recém-coletadas. "
        "Analise se alguma delas representa uma notícia extraordinária ou de ALTÍSSIMO IMPACTO de mercado "
        "(ex: decisões de bancos centrais sobre taxas de juros, pânicos bancários, dados agudos de inflação/PIB, escaladas geopolíticas bruscas, "
        "reestruturações ou falências corporativas de grande escala). "
        "Se e somente se houver, escreva um alerta de notícias de mercado urgente chamado '🛡️ PERFECT LIFE FLASH NEWS' no seu tom requintado e sofisticado de Jarvis, "
        "explicando de maneira inteligente a relevância imediata para as economias mundiais e locais. "
        "Se não houver notícias extraordinárias e apenas manchetes normais de mercado, responda estritamente com a palavra 'NENHUMA'."
    )
    
    headlines_str = "\n".join([f"- Título: {n['title']}\n  Descrição: {n['description']}" for n in unsent_news])
    
    report = ask_gemini(system_instruction, f"Aqui estão as novas manchetes:\n{headlines_str}", use_search=True)
    if report and report.strip() != "NENHUMA":
        send_sentinel_alert(report, is_signal=True)

def is_report_already_sent(report_type, date_str):
    """Verifica se um relatório diário específico já foi emitido."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sent_reports WHERE report_type = ? AND date = ?", (report_type, date_str))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def mark_report_as_sent(report_type, date_str):
    """Marca um relatório diário específico como emitido no banco de dados SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sent_reports (report_type, date, sent_at) VALUES (?, ?, ?)", (report_type, date_str, datetime.datetime.now().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def run_chronos_scheduler():
    """Worker background do Perfect Life Chronos Scheduler para controle temporal dos relatórios e notícias."""
    print("[Chronos Scheduler] Incializando o Perfect Life Chronos Scheduler background thread...")
    
    # Executa verificação inicial de notícias
    try:
        check_and_send_breaking_news()
    except Exception as e:
        print(f"[Chronos Scheduler] Erro ao executar verificação inicial: {e}")
        
    last_news_check = time.time()
    
    while True:
        try:
            brt_now = get_brt_time()
            date_str = brt_now.strftime("%Y-%m-%d")
            time_str = brt_now.strftime("%H:%M")
            
            # Verificação de Relatórios Diários Agendados
            if time_str == "07:00":
                if not is_report_already_sent("morning_briefing", date_str):
                    print(f"[Chronos] Disparando Perfect Life Morning Briefing em {date_str}...")
                    if send_morning_briefing():
                        mark_report_as_sent("morning_briefing", date_str)
                        
            elif time_str == "11:30":
                if not is_report_already_sent("ny_open_impact", date_str):
                    print(f"[Chronos] Disparando Wall Street Open Impact em {date_str}...")
                    if send_ny_open_impact():
                        mark_report_as_sent("ny_open_impact", date_str)
                        
            elif time_str == "14:00":
                if not is_report_already_sent("london_close", date_str):
                    print(f"[Chronos] Disparando London Close Bulletin em {date_str}...")
                    if send_london_close_bulletin():
                        mark_report_as_sent("london_close", date_str)
                        
            elif time_str == "18:00":
                if not is_report_already_sent("closing_report", date_str):
                    print(f"[Chronos] Disparando Perfect Life Closing Report & Whale Tracker em {date_str}...")
                    if send_closing_report():
                        mark_report_as_sent("closing_report", date_str)
                        
            elif time_str == "19:00":
                if not is_report_already_sent("ema_scan", date_str):
                    print(f"[Chronos] Disparando Radar 111 EMA diário em {date_str}...")
                    if run_daily_ema_scan():
                        mark_report_as_sent("ema_scan", date_str)
            
            # Polling de notícias a cada 60 minutos
            if time.time() - last_news_check >= 3600:
                check_and_send_breaking_news()
                last_news_check = time.time()
                
        except Exception as e:
            print(f"[Chronos Scheduler Error]: {e}")
            
        time.sleep(30)

# =====================================================================
# OUVINTE INDEPENDENTE DE COMANDOS TELEGRAM (Long Polling)
# =====================================================================
def run_telegram_command_listener():
    """Escuta e responde a comandos operacionais no chat privado ou canal do Telegram."""
    token, chat_id, channel_id = get_telegram_credentials()
    if not token:
        print("[Sentinel Listener] Telegram Bot Token não configurado. Listener inativo.")
        return
        
    print("[Sentinel Listener] Ouvindo comandos do Telegram em modo standalone...")
    last_update_id = 0
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    while True:
        try:
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    for update in data["result"]:
                        last_update_id = update["update_id"]
                        if "message" in update:
                            msg = update["message"]
                            text = msg.get("text", "").strip()
                            sender_chat_id = str(msg["chat"]["id"])
                            
                            # Aceita comandos apenas do Administrador privado
                            valid_chats = []
                            if chat_id:
                                valid_chats.append(chat_id)
                                
                            if valid_chats and sender_chat_id not in valid_chats:
                                continue
                                
                            text_lower = text.lower().strip()
                            if text_lower in ["/status", "/sentinela", "/sentinel"]:
                                status_msg = get_sentinel_status()
                                send_sentinel_alert(status_msg, custom_chat_id=sender_chat_id)
                            elif text_lower in ["/performance", "/sentinel_perf", "/perf"]:
                                perf_msg = get_sentinel_performance()
                                send_sentinel_alert(perf_msg, custom_chat_id=sender_chat_id)
                            elif text_lower in ["/trades", "/sentinel_trades", "/sentinel_log", "/log"]:
                                trades_msg = get_sentinel_trades()
                                send_sentinel_alert(trades_msg, custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_briefing":
                                send_sentinel_alert("⚡ *Iniciando Morning Briefing manual...*", custom_chat_id=sender_chat_id)
                                success = send_morning_briefing()
                                send_sentinel_alert(f"Morning Briefing concluído: {'SUCESSO' if success else 'FALHA'}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_ny":
                                send_sentinel_alert("⚡ *Iniciando NY Open Impact manual...*", custom_chat_id=sender_chat_id)
                                success = send_ny_open_impact()
                                send_sentinel_alert(f"NY Open Impact concluído: {'SUCESSO' if success else 'FALHA'}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_london":
                                send_sentinel_alert("⚡ *Iniciando London Close Bulletin manual...*", custom_chat_id=sender_chat_id)
                                success = send_london_close_bulletin()
                                send_sentinel_alert(f"London Close Bulletin concluído: {'SUCESSO' if success else 'FALHA'}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_close":
                                send_sentinel_alert("⚡ *Iniciando Closing Report & Whale Tracker manual...*", custom_chat_id=sender_chat_id)
                                success = send_closing_report()
                                send_sentinel_alert(f"Closing Report concluído: {'SUCESSO' if success else 'FALHA'}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_radar":
                                send_sentinel_alert("⚡ *Iniciando Radar 111 EMA diário manual...*", custom_chat_id=sender_chat_id)
                                success = run_daily_ema_scan()
                                send_sentinel_alert(f"Radar 111 EMA concluído: {'SUCESSO' if success else 'FALHA'}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_insiders":
                                send_sentinel_alert("⚡ *Iniciando Rastreamento de Insiders manual...*", custom_chat_id=sender_chat_id)
                                try:
                                    insiders = scan_insider_purchases()
                                    if insiders:
                                        msg_insiders = "🛡️ **JARVIS SENTINEL | COMPRAS DE INSIDERS (Smart Money):**\n\n"
                                        insiders = sorted(insiders, key=lambda x: x["Date"], reverse=True)[:10]
                                        for p in insiders:
                                            msg_insiders += (
                                                f"- **{p['Ticker']}**: {p['Insider']} ({p['Position']}) comprou {p['Shares']:,} ações "
                                                f"no valor de **${p['Value']:,.2f}** em {p['Date']}. [Form 4]({p['URL']})\n"
                                            )
                                    else:
                                        msg_insiders = "🛡️ **JARVIS SENTINEL:** Nenhuma compra recente de insiders detectada."
                                    send_sentinel_alert(msg_insiders, custom_chat_id=sender_chat_id)
                                except Exception as e:
                                    send_sentinel_alert(f"Erro ao rastrear insiders: {e}", custom_chat_id=sender_chat_id)
                            elif text_lower == "/force_news":
                                send_sentinel_alert("⚡ *Verificando notícias de alto impacto...*", custom_chat_id=sender_chat_id)
                                check_and_send_breaking_news()
                                send_sentinel_alert("Varredura de notícias finalizada.", custom_chat_id=sender_chat_id)
                            elif text_lower in ["/start", "/ajuda", "/help"]:
                                help_msg = (
                                    "🛡️ **Jarvis Sentinel | Standalone Control:**\n\n"
                                    "• `/status` ou `/sentinela` - Telemetria em tempo real dos 10 ativos\n"
                                    "• `/perf` - Métricas de assertividade e P&L consolidado\n"
                                    "• `/log` ou `/trades` - Lista os últimos 10 trades\n\n"
                                    "⚡ **Comandos de Comando e Controle (Admin):**\n"
                                    "• `/force_briefing` - Emite o briefing matinal (07:00 BRT)\n"
                                    "• `/force_ny` - Emite o radar de abertura NY (11:30 BRT)\n"
                                    "• `/force_london` - Emite o fechamento europeu (14:00 BRT)\n"
                                    "• `/force_close` - Emite o fechamento diário & baleias (18:00 BRT)\n"
                                    "• `/force_radar` - Executa a varredura da média 111 (19:00 BRT)\n"
                                    "• `/force_insiders` - Executa o rastreamento de compras de insiders (SEC Form 4)\n"
                                    "• `/force_news` - Varre notícias econômicas de alto impacto"
                                )
                                send_sentinel_alert(help_msg, custom_chat_id=sender_chat_id)
                                
        except Exception as e:
            print(f"[Sentinel Listener Error]: {e}")
        time.sleep(1)

# =====================================================================
# ENTRADA DE EXECUÇÃO PRINCIPAL
# =====================================================================
def main():
    print("=====================================================================")
    print("                JARVIS SENTINEL - DAEMON AUTÔNOMO                    ")
    print("=====================================================================")
    print(f"Data de Inicialização: {datetime.datetime.now()}")
    
    init_db()
    
    # Inicia Threads
    t_monitor = threading.Thread(target=run_sentinel_monitor, daemon=True)
    t_listener = threading.Thread(target=run_telegram_command_listener, daemon=True)
    t_scheduler = threading.Thread(target=run_chronos_scheduler, daemon=True)
    
    t_monitor.start()
    t_listener.start()
    t_scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Sentinel] Encerrado manualmente.")

if __name__ == "__main__":
    main()
