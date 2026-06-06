import os
import time
import datetime
import threading
import requests
import psutil
import yfinance as yf
import json

# Importação condicional do winsound para evitar quebras em outros SOs
try:
    import winsound
except ImportError:
    winsound = None

# =====================================================================
# CONFIGURAÇÕES DO ASSISTENTE LOCAL (Preencha com seus dados)
# =====================================================================
TELEGRAM_BOT_TOKEN = ""  # Seu Token obtido com o @BotFather (Ex: "123456789:ABCDefgh...")
TELEGRAM_CHAT_ID = ""    # Seu ID de Chat (Ex: "987654321")

# Alarme / Despertador (Formato HH:MM)
WAKE_UP_TIME = "07:00"
ALARM_ACTIVE = False

# Monitoramento de Mercado (B3 Ticker e Alvos de Preço)
MONITOR_TICKER = "EURCLP=X"
PRICE_UPPER_LIMIT = 980.00
PRICE_LOWER_LIMIT = 900.00
MARKET_CHECK_INTERVAL = 300  # 5 minutos

# Monitoramento de Sistema (Limites de CPU/Memória)
CPU_THRESHOLD = 90.0  # %
RAM_THRESHOLD = 90.0  # %
SYSTEM_CHECK_INTERVAL = 60  # 1 minuto

# =====================================================================
# SISTEMA DE LEITURA DE PERFIL DO USUÁRIO
# =====================================================================
def load_user_profile():
    """Carrega as informações de perfil e preferências do usuário."""
    path = os.path.join(os.path.dirname(__file__), "user_profile.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Erro de Perfil]: Não foi possível ler user_profile.json: {e}")
    return None

# =====================================================================
# SISTEMA DE NOTIFICAÇÕES (Telegram Seguro)
# =====================================================================
def send_notification(message):
    """Envia uma mensagem segura para o seu Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Notificação Local]: {message}")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🤖 **Jarvis Local:**\n\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[Erro de Conexão]: Não foi possível enviar notificação Telegram: {e}")
        return False

# =====================================================================
# MÓDULO INTERATIVO: RECEPTOR DE COMANDOS DO TELEGRAM
# =====================================================================
def handle_command(text, chat_id):
    """Processa e executa comandos recebidos do usuário via Telegram."""
    global ALARM_ACTIVE, WAKE_UP_TIME, MONITOR_TICKER, PRICE_UPPER_LIMIT, PRICE_LOWER_LIMIT
    
    text_lower = text.lower().strip()
    profile = load_user_profile()
    
    if text_lower.startswith("/start") or text_lower.startswith("/help") or text_lower.startswith("/ajuda"):
        menu = (
            "🤖 *Jarvis Local - Painel de Controle:*\n\n"
            "👤 `/perfil` - Exibe o seu perfil de trader e histórico gravado\n"
            "📈 `/estrategias` - Mostra estratégias quantitativas e lotes da ZeroMarkets\n"
            "💰 `/cotacoes` - Cotações atuais de seus ativos de interesse\n"
            "🖥️ `/sistema` - Status do hardware do laptop\n"
            "⏰ `/alarme HH:MM` - Configura o horário do alarme despertador\n"
            "🔔 `/despertar on/off` - Liga ou desliga o alarme sonoro\n"
            "🔍 `/monitorar TICKER` - Define o ativo para monitorar preço\n"
            "📊 `/alvos TETO PISO` - Define limites superior e inferior de alerta"
        )
        send_notification(menu)
        
    elif text_lower == "/perfil":
        if not profile:
            send_notification("⚠️ Perfil do usuário não encontrado localmente.")
            return
        
        perfil_msg = (
            f"👤 *Perfil do Trader:* {profile.get('user_name')}\n"
            f"📍 *Localização Atual:* {profile['locations']['current']}\n"
            f"✈️ *Desejo de Retorno:* {', '.join(profile['locations']['dream_return'])}\n\n"
            f"💼 *Parâmetros Operacionais:*\n"
            f"• Corretora: `{profile['trading_profile']['broker']}`\n"
            f"• Volume Máximo: `{profile['trading_profile']['max_broker_lots']} lotes`\n"
            f"• Capital Alvo: `USD {profile['trading_profile']['target_capital_usd']}`\n\n"
            f"⚠️ *Histórico de Mercado (Subprime 2008):*\n"
            f"• Morando no Chile, operava capital de `R$ {profile['trading_profile']['historical_events'][0]['capital_brl']:,}` e quebrou na crise do subprime operando `{profile['trading_profile']['historical_events'][0]['asset']}`.\n\n"
            f"🎨 *Diretriz de Design (Inviolável):*\n"
            f"• Nunca usar textos escuros sobre fundo escuro em legendas de gráficos."
        )
        send_notification(perfil_msg)
        
    elif text_lower == "/estrategias":
        if not profile:
            send_notification("⚠️ Informações de estratégias não disponíveis no perfil.")
            return
        
        est_msg = "📈 *Parâmetros de Estratégias (ZeroMarkets):*\n\n"
        for asset, details in profile.get("strategies_reference", {}).items():
            est_msg += f"• *{asset}*:\n"
            for k, v in details.items():
                est_msg += f"  - {k}: `{v}`\n"
        send_notification(est_msg)
        
    elif text_lower == "/cotacoes":
        send_notification("⏳ Coletando cotações com Yahoo Finance...")
        tickers = {
            "EURCLP": "EURCLP=X",
            "USDCLP": "CLP=X",
            "GBPJPY": "GBPJPY=X",
            "CHFJPY": "CHFJPY=X",
            "Gold (XAUUSD)": "GC=F",
            "Brent Crude": "BZ=F",
            "Bitcoin": "BTC-USD",
            "Mini Índice": "WIN=F",
            "Mini Dólar": "WDO=F",
            "PETR4": "PETR4.SA"
        }
        res_msg = "💰 *Preços e Cotações Atuais:*\n\n"
        for name, tick in tickers.items():
            try:
                t_obj = yf.Ticker(tick)
                hist = t_obj.history(period="1d")
                if not hist.empty:
                    val = float(hist["Close"].iloc[-1])
                    res_msg += f"• *{name}*: `{val:.4f}`\n"
                else:
                    res_msg += f"• *{name}*: `Sem dados`\n"
            except Exception as e:
                res_msg += f"• *{name}*: `Erro: {e}`\n"
        send_notification(res_msg)
        
    elif text_lower == "/sistema":
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        sys_msg = (
            "🖥️ *Diagnóstico de Recursos do Laptop:*\n\n"
            f"• **CPU:** `{cpu}%` (Alerta em > `{CPU_THRESHOLD}%`)\n"
            f"• **RAM:** `{ram}%` (Alerta em > `{RAM_THRESHOLD}%`)\n"
            f"• **Armazenamento:** `{disk}%`"
        )
        send_notification(sys_msg)
        
    elif text_lower.startswith("/alarme "):
        parts = text.split()
        if len(parts) == 2:
            h_m = parts[1]
            try:
                datetime.datetime.strptime(h_m, "%H:%M")
                WAKE_UP_TIME = h_m
                send_notification(f"⏰ Despertador configurado para às *{WAKE_UP_TIME}*.")
            except ValueError:
                send_notification("⚠️ Formato inválido! Envie no padrão HH:MM (Ex: `/alarme 06:30`).")
        else:
            send_notification("⚠️ Use: `/alarme HH:MM`")
            
    elif text_lower.startswith("/despertar "):
        cmd = text_lower.split()
        if len(cmd) == 2:
            act = cmd[1]
            if act in ["on", "ligar", "ativar"]:
                ALARM_ACTIVE = True
                send_notification(f"🔔 Despertador ATIVADO para às *{WAKE_UP_TIME}*.")
            elif act in ["off", "desligar", "desativar"]:
                ALARM_ACTIVE = False
                send_notification("🔕 Despertador DESATIVADO.")
            else:
                send_notification("⚠️ Use `/despertar on` ou `/despertar off`")
                
    elif text_lower.startswith("/monitorar "):
        parts = text.split()
        if len(parts) == 2:
            MONITOR_TICKER = parts[1].upper()
            send_notification(f"🔍 Ticker alterado para: *{MONITOR_TICKER}*.")
        else:
            send_notification("⚠️ Use: `/monitorar TICKER` (Ex: `/monitorar EURCLP=X`)")
            
    elif text_lower.startswith("/alvos "):
        parts = text.split()
        if len(parts) == 3:
            try:
                PRICE_UPPER_LIMIT = float(parts[1])
                PRICE_LOWER_LIMIT = float(parts[2])
                send_notification(
                    f"🎯 Limites de Alerta atualizados para *{MONITOR_TICKER}*:\n"
                    f"• Teto: `{PRICE_UPPER_LIMIT}`\n"
                    f"• Piso: `{PRICE_LOWER_LIMIT}`"
                )
            except ValueError:
                send_notification("⚠️ Insira valores válidos. Ex: `/alvos 980.0 900.0`")
        else:
            send_notification("⚠️ Use: `/alvos TETO PISO` (Ex: `/alvos 980 900`)")
            
    else:
        send_notification("❓ Comando desconhecido. Digite `/help` para listar os comandos.")

def telegram_listener_worker():
    """Roda em segundo plano ouvindo mensagens enviadas pelo usuário ao Bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("[Módulo Ouvinte]: Telegram Bot Token não configurado. Listener inativo.")
        return
        
    print("[Módulo Ouvinte]: Iniciando monitoramento de comandos via Telegram...")
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
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
                            chat_id = str(msg["chat"]["id"])
                            
                            # Filtra mensagens apenas do Chat ID configurado para segurança
                            if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
                                continue
                            
                            if text:
                                handle_command(text, chat_id)
        except Exception as e:
            print(f"[Erro no Ouvinte Telegram]: {e}")
        time.sleep(1)

# =====================================================================
# TAREFA 1: DESPERTADOR / ALARME (winsound do Windows)
# =====================================================================
def alarm_worker():
    """Roda em segundo plano checando o horário para tocar o alarme."""
    global ALARM_ACTIVE
    print("[Módulo Alarme]: Ativado e aguardando...")
    while True:
        if ALARM_ACTIVE:
            now = datetime.datetime.now().strftime("%H:%M")
            if now == WAKE_UP_TIME:
                msg = f"🔔 HORA DE ACORDAR! O relógio marcou {WAKE_UP_TIME}."
                print(msg)
                send_notification(msg)
                
                # Toca bip no alto-falante físico do laptop (Windows)
                if winsound:
                    for _ in range(10):
                        try:
                            winsound.Beep(2000, 500)
                        except Exception:
                            pass
                        time.sleep(0.5)
                else:
                    print("[Som]: Winsound indisponível neste SO. Apenas notificação enviada.")
                
                # Evita disparar repetidamente no mesmo minuto
                time.sleep(65)
        time.sleep(10)

# =====================================================================
# TAREFA 2: MONITOR DE RECURSOS (Laptop Health Check)
# =====================================================================
def system_monitor_worker():
    """Monitora o uso de hardware do laptop para evitar travamentos."""
    print("[Módulo Sistema]: Monitoramento de hardware ativado.")
    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        
        if cpu_usage > CPU_THRESHOLD:
            send_notification(f"⚠️ Alerta de Performance: Uso de CPU em {cpu_usage:.1f}%!")
        if ram_usage > RAM_THRESHOLD:
            send_notification(f"⚠️ Alerta de Performance: Uso de Memória RAM em {ram_usage:.1f}%!")
            
        time.sleep(SYSTEM_CHECK_INTERVAL)

# =====================================================================
# TAREFA 3: MONITOR DE PREÇO (B3 & Forex Market Watcher)
# =====================================================================
def market_monitor_worker():
    """Acompanha ativos e avisa quando atingem metas de preço."""
    global MONITOR_TICKER, PRICE_UPPER_LIMIT, PRICE_LOWER_LIMIT
    if not MONITOR_TICKER:
        return
        
    print(f"[Módulo Mercado]: Acompanhando {MONITOR_TICKER}...")
    last_triggered_price = None
    
    while True:
        try:
            ticker_data = yf.Ticker(MONITOR_TICKER)
            history = ticker_data.history(period="1d")
            if not history.empty:
                current_price = float(history["Close"].iloc[-1])
                
                if current_price != last_triggered_price:
                    if current_price >= PRICE_UPPER_LIMIT:
                        send_notification(f"📈 Alvo Atingido: {MONITOR_TICKER} subiu para {current_price:.4f} (Alvo: >= {PRICE_UPPER_LIMIT:.4f})!")
                        last_triggered_price = current_price
                    elif current_price <= PRICE_LOWER_LIMIT:
                        send_notification(f"📉 Alvo Atingido: {MONITOR_TICKER} caiu para {current_price:.4f} (Alvo: <= {PRICE_LOWER_LIMIT:.4f})!")
                        last_triggered_price = current_price
        except Exception as e:
            print(f"[Erro de Cotação]: Falha ao monitorar mercado: {e}")
            
        time.sleep(MARKET_CHECK_INTERVAL)

# =====================================================================
# INICIALIZADOR DE SERVIÇO
# =====================================================================
def start_jarvis():
    print("=====================================================================")
    print("           JARVIS LOCAL ASSISTANT - SERVIÇO ATIVADO 24h               ")
    print("=====================================================================")
    print(f"Data/Hora de Inicialização: {datetime.datetime.now()}")
    
    # Carrega informações de perfil do Padua
    profile = load_user_profile()
    if profile:
        print(f"[Jarvis]: Perfil de {profile.get('user_name')} carregado com sucesso.")
    else:
        print("[Jarvis]: user_profile.json não foi localizado.")

    # Disparar as threads em segundo plano (background workers)
    t_alarm = threading.Thread(target=alarm_worker, daemon=True)
    t_system = threading.Thread(target=system_monitor_worker, daemon=True)
    t_market = threading.Thread(target=market_monitor_worker, daemon=True)
    t_listener = threading.Thread(target=telegram_listener_worker, daemon=True)
    
    t_alarm.start()
    t_system.start()
    t_market.start()
    t_listener.start()
    
    send_notification("✅ Jarvis Local inicializado! Pronto para receber comandos e monitorar.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Jarvis Local]: Serviço encerrado manualmente.")

if __name__ == "__main__":
    start_jarvis()
