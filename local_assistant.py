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
MONITOR_TICKER = "GBPJPY=X"
PRICE_UPPER_LIMIT = 205.00
PRICE_LOWER_LIMIT = 185.00
MARKET_CHECK_INTERVAL = 300  # 5 minutos

# Monitoramento de Sistema (Limites de CPU/Memória)
CPU_THRESHOLD = 90.0  # %
RAM_THRESHOLD = 90.0  # %
SYSTEM_CHECK_INTERVAL = 60  # 1 minuto

# Configuração de Voz do Jarvis (Mark II)
VOICE_REPLIES_ACTIVE = False
PROACTIVE_REPLIES_ACTIVE = True

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
        "EURUSD": "EURUSD=X",
        "GBPJPY": "GBPJPY=X",
        "CHFJPY": "CHFJPY=X",
        "Ouro (XAUUSD)": "GC=F",
        "Bitcoin": "BTC-USD",
        "Ibovespa (WIN)": "^BVSP",
        "S&P 500 (SPY)": "SPY"
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
        "🌅 **BOM DIA, SENHOR! O SEU DIÁRIO MATINAL ESTÁ PRONTO:**\n\n"
        f"{weather_desc}\n\n"
        "📰 **Principais Notícias de Economia:**\n"
        f"{news_block}\n\n"
        "📊 **Fechamento e Cotações Atuais:**\n"
        f"{market_block}\n\n"
        "💡 *Senhor, que suas operações de hoje tragam lucros extraordinários.*"
    )
    return briefing

# =====================================================================
# INTEGRAÇÃO GEMINI: PERSONALIDADE JARVIS DO HOMEM DE FERRO
# =====================================================================
def ask_gemini(user_message, chat_id, audio_b64=None):
    """Conversa com a API do Gemini simulando o personagem Jarvis do Homem de Ferro."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Tenta carregar do arquivo gemini.key local
    key_path = os.path.join(os.path.dirname(__file__), "gemini.key")
    if not api_key and os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                api_key = f.read().strip()
        except Exception:
            pass
            
    profile = load_user_profile()
    if not api_key and profile:
        api_key = profile.get("gemini_api_key", "")
        
    if not api_key:
        return (
            "⚠️ Senhor, o recurso de conversação com o Jarvis requer uma API Key do Gemini.\n"
            "Por favor, acesse o arquivo `user_profile.json` no seu computador e configure a chave no campo `\"gemini_api_key\"`."
        )

    memories = load_user_memories()
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    system_prompt = (
        "Você é o JARVIS, o assistente pessoal de inteligência artificial de Padua.\n"
        "Seu estilo de falar é IDÊNTICO ao Jarvis do Homem de Ferro (sofisticado, prestativo, educado, sempre chamando o usuário de 'Senhor' (e NUNCA de 'Sir'), e demonstrando extremo respeito por sua inteligência, histórico e patrimônio).\n\n"
        f"INFORMAÇÕES EXCLUSIVAS DO SENHOR:\n"
        f"- Nome: {profile.get('user_name', 'Padua')}\n"
        f"- Localização: {profile['locations']['current']}\n"
        f"- Cidades Favoritas: {', '.join(profile['locations']['favorites'])}\n"
        f"- Desejo de Retorno: {', '.join(profile['locations']['dream_return'])}\n"
        f"- Histórico Marcante: Quebrou em 2008 na crise do subprime operando Forex. Hoje opera na ZeroMarkets com limite de 50 lotes. ATENÇÃO: O Senhor NÃO quer saber e NÃO opera mais pares de moedas do Chile. Não fale nem mencione CLP ou Chile.\n"
        f"- METAS DE VIDA: Ficar extremamente rico (acumulando patrimônio através de ações, forex, cripto, índices e hedges), ficar mais magro, saudável e em forma, e evoluir diariamente em todos os aspectos da vida (mental, técnico, financeiro). Você deve sempre incentivá-lo e ajudá-lo ativamente a atingir essas metas em suas conversas e lembretes.\n"
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
    
    if audio_b64:
        history.append({
            "role": "user",
            "parts": [
                {"text": "O Senhor enviou uma mensagem de voz. Ouça, transcreva, execute a instrução e responda em português com o seu personagem Jarvis:"},
                {
                    "inlineData": {
                        "mimeType": "audio/ogg",
                        "data": audio_b64
                    }
                }
            ]
        })
    else:
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
                
                # Se foi enviado áudio, simplificamos o histórico para fins de consumo de tokens futuro
                if audio_b64:
                    history[-1] = {"role": "user", "parts": [{"text": "[Mensagem de Voz do Senhor]"}]}
                
                history.append({"role": "model", "parts": [{"text": bot_reply}]})
                save_chat_history(chat_id, history)
                
                # Se o Jarvis disse que memorizou/salvou algo, tentamos capturar a frase e arquivar
                if "memória" in bot_reply.lower() or "guardei" in bot_reply.lower() or "salvei" in bot_reply.lower():
                    # Salva a mensagem do usuário como um fato aprendido
                    save_user_memory(user_message if not audio_b64 else "[Instrução de voz guardada pelo Jarvis]")
                    
                return bot_reply
            return "⚠️ Senhor, o servidor central respondeu sem dados."
        else:
            return f"⚠️ Senhor, erro de conexão com o núcleo da IA: {response.text}"
    except Exception as e:
        return f"⚠️ Senhor, erro ao alcançar o núcleo de processamento do Jarvis: {e}"

# =====================================================================
# MÓDULO INTERATIVO: RECEPTOR DE COMANDOS DO TELEGRAM
# =====================================================================
def handle_command(text, chat_id):
    """Processa e executa comandos recebidos do usuário via Telegram."""
    global ALARM_ACTIVE, WAKE_UP_TIME, MONITOR_TICKER, PRICE_UPPER_LIMIT, PRICE_LOWER_LIMIT, VOICE_REPLIES_ACTIVE, PROACTIVE_REPLIES_ACTIVE
    
    text_lower = text.lower().strip()
    profile = load_user_profile()
    
    if text_lower.startswith("/start") or text_lower.startswith("/help") or text_lower.startswith("/ajuda"):
        menu = (
            "🤖 *Jarvis Local - Painel de Controle:*\n\n"
            "👤 `/perfil` - Exibe seu perfil de trader e histórico gravado\n"
            "📈 `/estrategias` - Mostra estratégias e lotes da ZeroMarkets\n"
            "💰 `/cotacoes` - Cotações atuais de seus ativos de interesse\n"
            "🌅 `/briefing` - Compila clima, mercados e principais notícias econômicas\n"
            "💼 `/carteiras` - Lista as carteiras de grandes fundos e VCs do site\n"
            "🔍 `/carteira NOME` - Detalha a carteira do fundo ou VC (Ex: `/carteira barsi`)\n"
            "🧠 `/memorias` - Lista todas as memórias que o Jarvis guardou de você\n"
            "✍️ `/lembrar FATO` - Salva um fato importante na memória permanente\n"
            "🖥️ `/sistema` - Status do hardware do laptop\n"
            "⏰ `/alarme HH:MM` - Configura o horário do alarme despertador\n"
            "🔔 `/despertar on/off` - Liga ou desliga o alarme sonoro\n"
            "🔍 `/monitorar TICKER` - Define o ativo para monitorar preço\n"
            "📊 `/alvos TETO PISO` - Define limites superior e inferior de alerta\n"
            "🎙️ `/voz` - Alterna respostas de voz automáticas ativas/inativas\n"
            "🔮 `/proativo` - Alterna alertas proativos das metas de vida\n"
            "🤖 `/interagir` - Força uma conversa proativa de metas agora\n\n"
            "💬 *Dica:* Você também pode simplesmente conversar comigo normalmente digitando mensagens livres (ou enviando áudios pelo Telegram), e eu responderei como o Jarvis do Homem de Ferro!"
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
            f"• Em 2008, operava capital de `R$ {profile['trading_profile']['historical_events'][0]['capital_brl']:,}` e quebrou na crise do subprime operando `{profile['trading_profile']['historical_events'][0]['asset']}`.\n\n"
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

    elif text_lower == "/carteiras":
        # Lista as carteiras disponíveis
        msg = (
            "💼 *Carteiras de Elite Disponíveis para Consulta:*\n\n"
            "🇧🇷 *Grandes Fundos da B3:*\n"
            "• `Verde` (Verde Asset Management)\n"
            "• `Dynamo` (Dynamo Capital)\n"
            "• `Atmos` (Atmos Capital)\n"
            "• `IP Capital` (IP Capital Partners)\n"
            "• `Constellation` (Constellation Asset)\n"
            "• `Bogari` (Bogari Capital)\n"
            "• `Lirio` (Lírio Parisotto)\n"
            "• `Luiz Alves` (Luiz Alves Paes)\n"
            "• `Ronaldo Cezar` (Samambaia)\n"
            "• `Barsi` (Luiz Barsi)\n\n"
            "🇺🇸 *Super Baleias Globais (SEC 13F):*\n"
            "• `Berkshire` (Warren Buffett)\n"
            "• `Vanguard` (Vanguard Group)\n"
            "• `Blackrock` (BlackRock Inc)\n"
            "• `Goldman` (Goldman Sachs)\n"
            "• `Morgan` (Morgan Stanley)\n"
            "• `JPMorgan` (JPMorgan Chase)\n\n"
            "🪙 *Grandes VCs de Cripto & Web3:*\n"
            "• `a16z` (a16z Crypto)\n"
            "• `Paradigm` (Paradigm Capital)\n"
            "• `Pantera` (Pantera Capital)\n"
            "• `Multicoin` (Multicoin Capital)\n\n"
            "💡 *Como consultar:* Digite `/carteira <nome>` (Ex: `/carteira barsi` ou `/carteira berkshire`)."
        )
        send_notification(msg)

    elif text_lower.startswith("/carteira"):
        query = text[9:].strip().lower()
        if not query:
            send_notification("⚠️ Senhor, forneça o nome da carteira. Ex: `/carteira barsi` ou `/carteira berkshire`.")
            return
            
        base_dir = os.path.dirname(__file__)
        cache_dir = os.path.join(base_dir, "cache")
        
        # 1. Carteiras de Cripto VCs
        crypto_vcs = {
            "a16z": {
                "name": "a16z Crypto (Andreessen Horowitz)",
                "holdings": [
                    {"asset": "Ethereum (ETH)", "weight": 35.0, "tip": "Liquid Restaking - APY ~4.5%"},
                    {"asset": "Solana (SOL)", "weight": 25.0, "tip": "MEV-Boosted Staking (JitoSOL) - APY ~7.5%"},
                    {"asset": "Near Protocol (NEAR)", "weight": 15.0, "tip": "Staking Nativo - APY ~8.0%"},
                    {"asset": "Uniswap (UNI)", "weight": 12.0, "tip": "Governança e Recompensas de Taxas"},
                    {"asset": "Maker (MKR)", "weight": 8.0, "tip": "Estabilidade Real Yield"},
                    {"asset": "Optimism (OP)", "weight": 5.0, "tip": "Provisão de Liquidez L2"}
                ]
            },
            "paradigm": {
                "name": "Paradigm Capital",
                "holdings": [
                    {"asset": "Ethereum (ETH)", "weight": 45.0, "tip": "Liquid Restaking - APY ~4.5%"},
                    {"asset": "Uniswap (UNI)", "weight": 20.0, "tip": "Provisão de Liquidez DeFi"},
                    {"asset": "Celestia (TIA)", "weight": 15.0, "tip": "Staking Modular - APY ~11.0%"},
                    {"asset": "Starknet (STRK)", "weight": 10.0, "tip": "Liquidez em L2"},
                    {"asset": "Blur (BLUR)", "weight": 6.0, "tip": "NFT Yield Pools L2"},
                    {"asset": "Lido DAO (LDO)", "weight": 4.0, "tip": "Liquid Staking"}
                ]
            },
            "pantera": {
                "name": "Pantera Capital",
                "holdings": [
                    {"asset": "Bitcoin (BTC)", "weight": 40.0, "tip": "Custódia Fria Offline"},
                    {"asset": "Ethereum (ETH)", "weight": 20.0, "tip": "Liquid Restaking - APY ~4.5%"},
                    {"asset": "Solana (SOL)", "weight": 18.0, "tip": "MEV-Boosted Staking - APY ~7.5%"},
                    {"asset": "Toncoin (TON)", "weight": 10.0, "tip": "TON Liquid Staking - APY ~5.2%"},
                    {"asset": "Render (RNDR)", "weight": 8.0, "tip": "Computação GPU Yield"},
                    {"asset": "Lido DAO (LDO)", "weight": 4.0, "tip": "Liquid Staking"}
                ]
            },
            "multicoin": {
                "name": "Multicoin Capital",
                "holdings": [
                    {"asset": "Solana (SOL)", "weight": 50.0, "tip": "JitoSOL - APY ~7.5%"},
                    {"asset": "Helium (HNT)", "weight": 18.0, "tip": "Telecom DePIN Yield"},
                    {"asset": "Render (RNDR)", "weight": 12.0, "tip": "GPU DePIN Yield"},
                    {"asset": "Pyth Network (PYTH)", "weight": 10.0, "tip": "Staking Oráculo - Airdrops"},
                    {"asset": "Ethena (ENA)", "weight": 7.0, "tip": "Delta-Neutral APY"},
                    {"asset": "Hivemapper (HONEY)", "weight": 3.0, "tip": "Mapping Rewards"}
                ]
            }
        }
        
        if query in crypto_vcs:
            vc = crypto_vcs[query]
            msg = f"🪙 *Carteira VC Cripto: {vc['name']}*\n\n"
            for h in vc["holdings"]:
                msg += f"• *{h['asset']}*: `{h['weight']}%` | _Defi: {h['tip']}_\n"
            send_notification(msg)
            return

        # 2. Fundos da B3 (brazil_elite_holdings.json)
        b3_file = os.path.join(cache_dir, "brazil_elite_holdings.json")
        if os.path.exists(b3_file):
            try:
                with open(b3_file, "r", encoding="utf-8") as f:
                    b3_data = json.load(f)
                
                funds = b3_data.get("funds", {})
                matched_fund = None
                for f_name in funds.keys():
                    short_name = f_name.lower()
                    if query in short_name or (query == "verde" and "verde" in short_name) or (query == "barsi" and "barsi" in short_name) or (query == "luiz alves" and "alves" in short_name) or (query == "ronaldo cezar" and "samambaia" in short_name) or (query == "lirio" and "lírio" in short_name):
                        matched_fund = f_name
                        break
                        
                if matched_fund:
                    fund_info = funds[matched_fund]
                    msg = f"🇧🇷 *Fundo B3: {matched_fund}*\n"
                    msg += f"💼 CNPJ: `{fund_info.get('cnpj', 'Sem CNPJ')}`\n"
                    msg += f"💰 AUM Estimado: `R$ {fund_info.get('total_portfolio_value', 0):,.2f}`\n"
                    msg += f"📅 Período: `{b3_data.get('cda_period', '09/2025')}`\n\n"
                    msg += "*Principais Posições (Top Holdings):*\n"
                    
                    # Lista as principais posições
                    for h in fund_info.get("holdings", [])[:10]:
                        msg += f"• *{h['ticker']}*: `{h['weight']:.2f}%` (Valor: R$ {h['value']:,.2f})\n"
                    send_notification(msg)
                    return
            except Exception as e:
                print(f"[Erro B3 Parser]: {e}")

        # 3. Whales do mercado americano (cache/xxx_holdings.json)
        us_whales_mapping = {
            "berkshire": "berkshire_hathaway",
            "buffett": "berkshire_hathaway",
            "vanguard": "vanguard",
            "blackrock": "blackrock",
            "goldman": "goldman_sachs",
            "morgan": "morgan_stanley",
            "jpmorgan": "jpmorgan_chase"
        }
        
        if query in us_whales_mapping:
            clean_name = us_whales_mapping[query]
            whale_file = os.path.join(cache_dir, f"{clean_name}_holdings.json")
            if os.path.exists(whale_file):
                try:
                    with open(whale_file, "r", encoding="utf-8") as f:
                        whale_data = json.load(f)
                    
                    msg = f"🇺🇸 *Baleia US: {whale_data.get('name', 'Baleia')}*\n"
                    msg += f"💼 CIK: `{whale_data.get('cik', 'Sem CIK')}`\n"
                    msg += f"📅 Atualizado: `{whale_data.get('last_updated', '2026-05-24')}`\n\n"
                    msg += "*Principais Posições (Top Holdings):*\n"
                    
                    # Lista as principais posições
                    for h in whale_data.get("data", [])[:10]:
                        shares_formatted = f"{h['shares']:,}"
                        msg += f"• *{h['name']}*: `{shares_formatted} ações` (Valor: $ {h['value']:,.2f})\n"
                    send_notification(msg)
                    return
                except Exception as e:
                    print(f"[Erro US Parser]: {e}")
            else:
                send_notification(f"⚠️ Senhor, o arquivo de cache da baleia `{query}` não foi localizado em seu computador.")
                return

        send_notification("⚠️ Senhor, carteira não localizada. Digite `/carteiras` para ver a lista de carteiras mapeadas.")
        
    elif text_lower == "/memorias":
        memories = load_user_memories()
        if not memories:
            send_notification("💭 Senhor, meus bancos de dados ainda estão vazios de memórias personalizadas.")
        else:
            m_list = "\n".join([f"• {m}" for m in memories])
            send_notification(f"🧠 *Memórias Evolutivas Registradas (Dia-a-Dia):*\n\n{m_list}")
            
    elif text_lower.startswith("/lembrar "):
        fact = text[9:].strip()
        if fact:
            save_user_memory(fact)
            send_notification(f"📝 *Entendido, Senhor.* Registrei a seguinte informação na minha memória:\n`{fact}`")
        else:
            send_notification("⚠️ Senhor, envie um fato para memorizar. Ex: `/lembrar meu Instagram é @padua`")
            
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
            send_notification("⚠️ Use: `/monitorar TICKER` (Ex: `/monitorar PETR4.SA`)")
            
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
            
    elif text_lower == "/voz":
        VOICE_REPLIES_ACTIVE = not VOICE_REPLIES_ACTIVE
        status = "ATIVADO" if VOICE_REPLIES_ACTIVE else "DESATIVADO"
        send_notification(f"🎙️ *Respostas de voz automáticas:* `{status}`")
             
    elif text_lower == "/proativo":
        PROACTIVE_REPLIES_ACTIVE = not PROACTIVE_REPLIES_ACTIVE
        status = "ATIVADO" if PROACTIVE_REPLIES_ACTIVE else "DESATIVADO"
        send_notification(f"🔮 *Mensagens proativas de metas:* `{status}`")
        
    elif text_lower == "/interagir":
        send_notification("⏳ Jarvis está analisando suas metas de evolução, riqueza e saúde...")
        prompt = (
            "Inicie uma conversa proativa e espontânea com o Senhor Padua. "
            "Diga que acabou de analisar o status do notebook, os mercados globais e as metas dele. "
            "Traga um insight inteligente sobre investimentos (como controle de risco/hedges) "
            "ou sobre saúde física (como perder peso e se manter ativo), sempre o motivando a evoluir em todos os aspectos da vida. "
            "Fale com o tom clássico e refinado do Jarvis do Homem de Ferro."
        )
        reply = ask_gemini(prompt, chat_id)
        send_notification(reply)
        if VOICE_REPLIES_ACTIVE:
            send_voice_reply(reply, chat_id)
             
    else:
        # Não é um comando barra: trata como chat de conversação do Jarvis
        reply = ask_gemini(text, chat_id)
        send_notification(reply)
        if VOICE_REPLIES_ACTIVE:
            send_voice_reply(reply, chat_id)

def send_voice_reply(reply, chat_id):
    """Gera um áudio local via SAPI e envia para o Telegram como mensagem de voz."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    import re
    clean_text = re.sub(r'[\*\_`#]', '', reply)
    clean_text = clean_text.replace("🤖", "").replace("⚠️", "").replace("✅", "").replace("🔔", "").strip()
    
    path = os.path.join(os.path.dirname(__file__), "jarvis_voice_reply.wav")
    try:
        import win32com.client
        filestream = win32com.client.Dispatch("SAPI.SpFileStream")
        filestream.Open(path, 3, False)
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # Tenta selecionar a voz padrão do Windows em Português
        voices = speaker.GetVoices()
        for i in range(voices.Count):
            voice = voices.Item(i)
            desc = voice.GetDescription().lower()
            if "1046" in voice.Id or "brazil" in desc or "portuguese" in desc:
                speaker.Voice = voice
                break
                
        speaker.AudioOutputStream = filestream
        speaker.Speak(clean_text)
        filestream.Close()
        
        # Envia como arquivo de voz para o Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
        with open(path, "rb") as f:
            files = {"voice": f}
            payload = {"chat_id": chat_id}
            response = requests.post(url, data=payload, files=files, timeout=25)
        
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        return response.status_code == 200
    except Exception as e:
        print(f"[Erro de Voz]: Não foi possível gerar/enviar áudio: {e}")
        return False

def handle_voice_message(voice_obj, chat_id):
    """Processa áudios enviados pelo Telegram e responde com voz sintetizada."""
    if not TELEGRAM_BOT_TOKEN:
        return
    
    file_id = voice_obj["file_id"]
    get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        res = requests.get(get_file_url, timeout=15)
        if res.status_code == 200:
            file_path = res.json().get("result", {}).get("file_path")
            if file_path:
                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                audio_res = requests.get(download_url, timeout=25)
                if audio_res.status_code == 200:
                    import base64
                    audio_b64 = base64.b64encode(audio_res.content).decode("utf-8")
                    
                    # Envia áudio para o Gemini
                    reply = ask_gemini("", chat_id, audio_b64=audio_b64)
                    
                    # Envia a resposta em texto
                    send_notification(reply)
                    
                    # Envia a resposta em áudio (voz)
                    send_voice_reply(reply, chat_id)
        else:
            send_notification("⚠️ Senhor, falha ao obter o arquivo de áudio dos servidores do Telegram.")
    except Exception as e:
        send_notification(f"⚠️ Senhor, erro ao processar o seu comando de voz: {e}")

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
                            elif "voice" in msg:
                                handle_voice_message(msg["voice"], chat_id)
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
                    send_notification("⏳ Preparando o briefing do seu dia, Senhor...")
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
# TAREFA 5: INTERAÇÃO PROATIVA COM O SENHOR (Life Goals Reminder)
# =====================================================================
def proactive_interaction_worker():
    """Roda em segundo plano e envia mensagens proativas ao Senhor em horários chave."""
    global PROACTIVE_REPLIES_ACTIVE, VOICE_REPLIES_ACTIVE
    print("[Módulo Proativo]: Ativado e aguardando horários agendados.")
    last_sent_key = ""
    
    while True:
        try:
            if PROACTIVE_REPLIES_ACTIVE and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                now = datetime.datetime.now()
                hour_minute = now.strftime("%H:%M")
                date_key = now.strftime("%Y-%m-%d")
                
                # Horários agendados para interagir proativamente: 10:30 (manhã), 15:30 (tarde) e 20:30 (noite)
                target_times = ["10:30", "15:30", "20:30"]
                
                for t_time in target_times:
                    if hour_minute == t_time:
                        current_key = f"{date_key}_{t_time}"
                        if last_sent_key != current_key:
                            last_sent_key = current_key
                            
                            period = "manhã" if t_time == "10:30" else ("tarde" if t_time == "15:30" else "noite")
                            prompt = (
                                f"Inicie uma conversa proativa com o Senhor Padua neste período da {period}. "
                                "Diga que estava analisando o status e os mercados e pensou em novas formas de ajudá-lo. "
                                "Pergunte sobre o andamento das operações ou do dia. "
                                "Lembre-o e incentive-o de forma inteligente e sofisticada (Stark style) a focar em suas metas de vida:\n"
                                "1. Acumular riqueza (investimentos, B3, forex, cripto, hedges).\n"
                                "2. Ficar mais magro, saudável e ativo.\n"
                                "3. Evoluir mental e financeiramente hoje.\n"
                                "Mantenha a mensagem curta, instigante e educada. Não mencione CLP ou Chile."
                            )
                            
                            reply = ask_gemini(prompt, TELEGRAM_CHAT_ID)
                            send_notification(reply)
                            
                            if VOICE_REPLIES_ACTIVE:
                                send_voice_reply(reply, TELEGRAM_CHAT_ID)
        except Exception as e:
            print(f"[Erro Módulo Proativo]: {e}")
            
        time.sleep(30)  # Verifica a cada 30 segundos

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
    t_proactive = threading.Thread(target=proactive_interaction_worker, daemon=True)
    
    t_alarm.start()
    t_system.start()
    t_market.start()
    t_listener.start()
    t_sync.start()
    t_proactive.start()
    
    send_notification("✅ Jarvis Local inicializado! Conexão de cérebro (Sync) estabelecida.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Jarvis Local]: Serviço encerrado manualmente.")

if __name__ == "__main__":
    start_jarvis()
