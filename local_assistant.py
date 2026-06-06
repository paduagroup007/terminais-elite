import os
import time
import datetime
import threading
import requests
import psutil
import yfinance as yf
import json
import xml.etree.ElementTree as ET

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
# BANCO DE DADOS LOCAL E MEMÓRIA DO USUÁRIO
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

def load_user_memories():
    """Carrega as memórias evolutivas aprendidas no dia a dia."""
    path = os.path.join(os.path.dirname(__file__), "user_memory.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_user_memory(fact):
    """Guarda um fato novo aprendido sobre o usuário."""
    memories = load_user_memories()
    if fact not in memories:
        memories.append(fact)
        path = os.path.join(os.path.dirname(__file__), "user_memory.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Erro de Memória]: Falha ao salvar user_memory.json: {e}")
    return False

def load_chat_history(chat_id):
    """Carrega o histórico de conversa com o Bot do Telegram."""
    path = os.path.join(os.path.dirname(__file__), f"chat_history_{chat_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_chat_history(chat_id, history):
    """Salva o histórico de conversa atualizado."""
    path = os.path.join(os.path.dirname(__file__), f"chat_history_{chat_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Erro de Histórico]: Falha ao salvar chat_history_{chat_id}.json: {e}")

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
# GERAÇÃO DE BRIEFING MATINAL (Notícias, Clima e Mercados)
# =====================================================================
def get_morning_briefing():
    """Compila clima, cotações e notícias de economia matinais."""
    # 1. Clima (Open-Meteo - São Paulo capital)
    weather_desc = "Sem dados climáticos."
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-23.5489&longitude=-46.6388&current_weather=true"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            w_data = res.json().get("current_weather", {})
            temp = w_data.get("temperature")
            wind = w_data.get("windspeed")
            weather_desc = f"🌡️ **São Paulo:** {temp}°C | 💨 **Ventos:** {wind} km/h"
    except Exception as e:
        weather_desc = f"⚠️ Falha no clima: {e}"

    # 2. Notícias Econômicas (RSS G1 Economia)
    headlines = []
    try:
        url = "https://g1.globo.com/rss/g1/economia/"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:4]:
                title = item.find("title").text
                headlines.append(f"• {title}")
    except Exception as e:
        headlines = [f"⚠️ Erro ao buscar notícias: {e}"]

    # 3. Mercados Globais (Cotações com Variação Percentual Diária)
    market_status = []
    tickers = {
        "EURCLP": "EURCLP=X",
        "USDCLP": "CLP=X",
        "GBPJPY": "GBPJPY=X",
        "CHFJPY": "CHFJPY=X",
        "Ouro (XAUUSD)": "GC=F",
        "Bitcoin": "BTC-USD",
        "Ibovespa (WIN)": "^BVSP"
    }
    for name, tick in tickers.items():
        try:
            t_obj = yf.Ticker(tick)
            hist = t_obj.history(period="2d")
            if len(hist) >= 2:
                close_today = hist["Close"].iloc[-1]
                close_yesterday = hist["Close"].iloc[-2]
                pct_change = ((close_today - close_yesterday) / close_yesterday) * 100
                color = "🟢" if pct_change >= 0 else "🔴"
                market_status.append(f"• {color} **{name}**: `{close_today:.4f}` ({pct_change:+.2f}%)")
            elif not hist.empty:
                val = hist["Close"].iloc[-1]
                market_status.append(f"• ⚪ **{name}**: `{val:.4f}`")
        except Exception:
            market_status.append(f"• ⚠️ **{name}**: Erro de cotação")

    news_block = "\n".join(headlines)
    market_block = "\n".join(market_status)
    
    briefing = (
        "🌅 **BOM DIA, SIR! O SEU DIÁRIO MATINAL ESTÁ PRONTO:**\n\n"
        f"{weather_desc}\n\n"
        "📰 **Principais Notícias de Economia:**\n"
        f"{news_block}\n\n"
        "📊 **Fechamento e Cotações Atuais:**\n"
        f"{market_block}\n\n"
        "💡 *Sir, que suas operações de hoje tragam lucros extraordinários.*"
    )
    return briefing

# =====================================================================
# INTEGRAÇÃO GEMINI: PERSONALIDADE JARVIS DO HOMEM DE FERRO
# =====================================================================
def ask_gemini(user_message, chat_id):
    """Conversa com a API do Gemini simulando o personagem Jarvis do Homem de Ferro."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    profile = load_user_profile()
    
    if not api_key and profile:
        api_key = profile.get("gemini_api_key", "")
        
    if not api_key:
        return (
            "⚠️ Sir, o recurso de conversação com o Jarvis requer uma API Key do Gemini.\n"
            "Por favor, acesse o arquivo `user_profile.json` no seu computador e configure a chave no campo `\"gemini_api_key\"`."
        )

    memories = load_user_memories()
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    system_prompt = (
        "Você é o JARVIS, o assistente pessoal de inteligência artificial de Padua.\n"
        "Seu estilo de falar é IDÊNTICO ao Jarvis do Homem de Ferro (sofisticado, prestativo, educado, sempre chamando o usuário de 'Senhor' ou 'Sir', e demonstrando extremo respeito por sua inteligência, histórico e patrimônio).\n\n"
        f"INFORMAÇÕES EXCLUSIVAS DO SENHOR:\n"
        f"- Nome: {profile.get('user_name', 'Padua')}\n"
        f"- Localização: {profile['locations']['current']}\n"
        f"- Cidades Favoritas: {', '.join(profile['locations']['favorites'])}\n"
        f"- Desejo de Retorno: {', '.join(profile['locations']['dream_return'])}\n"
        f"- Histórico Marcante: Morou no Chile e Curitiba. Quebrou em 2008 na crise do subprime operando EURCLP com R$ 240.000. Hoje opera na ZeroMarkets com limite de 50 lotes.\n"
        f"- Regra Gráficos: Nunca usar cores escuras de texto em fundos escuros.\n\n"
        f"MEMÓRIAS SALVAS DE INTERAÇÕES ANTERIORES:\n"
        f"{json.dumps(memories, indent=2, ensure_ascii=False)}\n\n"
        f"ESTADO DO HARDWARE EM TEMPO REAL:\n"
        f"- Uso de CPU: {cpu}%\n"
        f"- Uso de RAM: {ram}%\n"
        f"- Monitorando: {MONITOR_TICKER} (Alvos: >= {PRICE_UPPER_LIMIT} ou <= {PRICE_LOWER_LIMIT})\n\n"
        "RESPONDA NO PERSONAGEM JARVIS. Se o Senhor te disser alguma preferência, novos canais de YouTube, Instagram ou tarefas diárias dele, "
        "diga que gravou na memória evolutiva dele. Responda em português."
    )

    history = load_chat_history(chat_id)
    history.append({"role": "user", "parts": [{"text": user_message}]})

    # Limita o histórico de chat para não exceder limites
    if len(history) > 16:
        history = history[-16:]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"[CONTEXTO DO SISTEMA: {system_prompt}]"}]}
        ] + history
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if candidates:
                bot_reply = candidates[0]["content"]["parts"][0]["text"]
                history.append({"role": "model", "parts": [{"text": bot_reply}]})
                save_chat_history(chat_id, history)
                
                # Se o Jarvis disse que memorizou/salvou algo, tentamos capturar a frase e arquivar
                if "memória" in bot_reply.lower() or "guardei" in bot_reply.lower() or "salvei" in bot_reply.lower():
                    # Salva a mensagem do usuário como um fato aprendido
                    save_user_memory(user_message)
                    
                return bot_reply
            return "⚠️ Sir, o servidor central respondeu sem dados."
        else:
            return f"⚠️ Sir, erro de conexão com o núcleo da IA: {response.text}"
    except Exception as e:
        return f"⚠️ Sir, erro ao alcançar o núcleo de processamento do Jarvis: {e}"

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
            "👤 `/perfil` - Exibe seu perfil de trader e histórico gravado\n"
            "📈 `/estrategias` - Mostra estratégias e lotes da ZeroMarkets\n"
            "💰 `/cotacoes` - Cotações atuais de seus ativos de interesse\n"
            "🌅 `/briefing` - Compila clima, mercados e principais notícias econômicas\n"
            "🧠 `/memorias` - Lista todas as memórias que o Jarvis guardou de você\n"
            "✍️ `/lembrar FATO` - Salva um fato importante na memória permanente\n"
            "🖥️ `/sistema` - Status do hardware do laptop\n"
            "⏰ `/alarme HH:MM` - Configura o horário do alarme despertador\n"
            "🔔 `/despertar on/off` - Liga ou desliga o alarme sonoro\n"
            "🔍 `/monitorar TICKER` - Define o ativo para monitorar preço\n"
            "📊 `/alvos TETO PISO` - Define limites superior e inferior de alerta\n\n"
            "💬 *Dica:* Você também pode simplesmente conversar comigo normalmente digitando mensagens livres, e eu responderei como o Jarvis do Homem de Ferro!"
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
        
    elif text_lower == "/briefing":
        send_notification("⏳ Compilando notícias, clima e mercados...")
        briefing = get_morning_briefing()
        send_notification(briefing)
        
    elif text_lower == "/memorias":
        memories = load_user_memories()
        if not memories:
            send_notification("💭 Sir, meus bancos de dados ainda estão vazios de memórias personalizadas.")
        else:
            m_list = "\n".join([f"• {m}" for m in memories])
            send_notification(f"🧠 *Memórias Evolutivas Registradas (Dia-a-Dia):*\n\n{m_list}")
            
    elif text_lower.startswith("/lembrar "):
        fact = text[9:].strip()
        if fact:
            save_user_memory(fact)
            send_notification(f"📝 *Entendido, Sir.* Registrei a seguinte informação na minha memória:\n`{fact}`")
        else:
            send_notification("⚠️ Sir, envie um fato para memorizar. Ex: `/lembrar meu Instagram é @padua`")
            
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
        # Não é um comando barra: trata como chat de conversação do Jarvis
        reply = ask_gemini(text, chat_id)
        send_notification(reply)

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
                
                # Envia o briefing matinal
                try:
                    send_notification("⏳ Preparando o briefing do seu dia, Sir...")
                    briefing = get_morning_briefing()
                    send_notification(briefing)
                except Exception as e:
                    print(f"[Erro Alarme Briefing]: {e}")

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
# TAREFA 4: SINCRONIZAÇÃO DE CÉREBRO (Brain-to-Brain Sync)
# =====================================================================
def brain_sync_worker():
    """Roda em segundo plano sincronizando informações com a IA principal via arquivos locais."""
    global MONITOR_TICKER, PRICE_UPPER_LIMIT, PRICE_LOWER_LIMIT, WAKE_UP_TIME, ALARM_ACTIVE
    print("[Módulo Cérebro Sync]: Iniciado e aguardando canal de sincronização...")
    base_dir = os.path.dirname(__file__)
    state_file = os.path.join(base_dir, "jarvis_brain_state.json")
    instruction_file = os.path.join(base_dir, "ai_instructions.json")
    
    while True:
        # 1. Escrever o estado atual do Jarvis Local para a IA Principal
        try:
            state_data = {
                "last_sync": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "ram_percent": psutil.virtual_memory().percent
                },
                "market": {
                    "ticker": MONITOR_TICKER,
                    "upper_limit": PRICE_UPPER_LIMIT,
                    "lower_limit": PRICE_LOWER_LIMIT
                },
                "alarm": {
                    "active": ALARM_ACTIVE,
                    "time": WAKE_UP_TIME
                }
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Erro Brain Sync - Envio]: Falha ao registrar estado local: {e}")
            
        # 2. Ler e executar as instruções vindas da IA Principal
        if os.path.exists(instruction_file):
            try:
                with open(instruction_file, "r", encoding="utf-8") as f:
                    instructions = json.load(f)
                
                processed = False
                if "send_telegram_msg" in instructions:
                    msg = instructions["send_telegram_msg"]
                    send_notification(f"🔮 **IA Central enviou uma mensagem:**\n\n{msg}")
                    processed = True
                
                if "update_monitored_ticker" in instructions:
                    MONITOR_TICKER = instructions["update_monitored_ticker"].upper()
                    send_notification(f"🔮 **IA Central alterou o monitoramento para:** {MONITOR_TICKER}")
                    processed = True
                    
                if "update_alarm" in instructions:
                    alarm_info = instructions["update_alarm"]
                    if "time" in alarm_info:
                        WAKE_UP_TIME = alarm_info["time"]
                    if "active" in alarm_info:
                        ALARM_ACTIVE = alarm_info["active"]
                    send_notification(f"🔮 **IA Central ajustou seu alarme para às:** {WAKE_UP_TIME} (Ativo: {ALARM_ACTIVE})")
                    processed = True
                
                # Remove o arquivo de instrução após executar para não rodar novamente
                if processed:
                    os.remove(instruction_file)
                    print("[Módulo Cérebro Sync]: Instruções recebidas da IA executadas com sucesso.")
            except Exception as e:
                print(f"[Erro Brain Sync - Recebimento]: Falha ao processar comandos da IA: {e}")
                
        time.sleep(15)  # Checa a cada 15 segundos

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
    t_sync = threading.Thread(target=brain_sync_worker, daemon=True)
    
    t_alarm.start()
    t_system.start()
    t_market.start()
    t_listener.start()
    t_sync.start()
    
    send_notification("✅ Jarvis Local inicializado! Conexão de cérebro (Sync) estabelecida.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Jarvis Local]: Serviço encerrado manualmente.")

if __name__ == "__main__":
    start_jarvis()
