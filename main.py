import requests
import time
import telegram
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import asyncio
from aiohttp import web
import os
import json
import logging
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

# =========================================================
# CONFIGURAÇÕES GERAIS E INICIALIZAÇÃO
# =========================================================
# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Variáveis de Ambiente e Configurações API
API_KEY = os.environ.get("LIVESCORE_API_KEY", "968c152b0a72f3fa63087d74b04eee5d")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7588970032:AAH6MDy42ZJJnlYlclr3GVeCfXS-XiePFuo")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002682430417")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Inicialização do Bot do Telegram
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Dicionário para rastrear jogos já notificados (0x0)
notified_matches_zero_zero = {}

# Lista de equipes de elite para o monitoramento de jogos futuros
EQUIPAS_DE_TITULO = [
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea",
    "Real Madrid", "Barcelona", "Atletico Madrid", "Girona",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    "Inter", "AC Milan", "Juventus", "Napoli",
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille",
    "Benfica", "Porto", "Sporting CP", "Braga",
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar",
    "Celtic", "Rangers",
    "Palmeiras", "Flamengo", "Internacional", "Gremio", "Atletico Mineiro", "Corinthians", "Fluminense",
    "Boca Juniors", "River Plate", "Racing Club", "Rosario Central",
    "Shanghai Port", "Shanghai Shenhua", "Shandong Luneng", "Chengdu Rongcheng"
]

# Inicializar aplicação Flask e Socket.IO
app = Flask(__name__, template_folder="templates")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
server = app

# =========================================================
# FUNÇÕES DE LÓGICA DE NEGÓCIO E APIs
# =========================================================

# Funções de envio de mensagem e requisição
async def send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro ao enviar mensagem ao Telegram: {e}")

def enviar_telegram_sync(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Variáveis TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        logger.info(f"[{datetime.now().strftime('%H:%M')}] ✅ Mensagem enviada para o Telegram")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem (síncrona): {e}")

# Funções para o bot de 0x0
def get_recent_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/fixtures?status=FT&date={today}"
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            logger.debug(f"[{datetime.now()}] Status: {response.status_code}, Resposta: {response.text}")
            response.raise_for_status()
            data = response.json()
            if "response" not in data:
                raise ValueError("Resposta não contém 'response'")
            return data["response"]
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"[{datetime.now()}] Erro (tentativa {attempt + 1}/3): {e}")
            time.sleep(5)
    return []

def get_league_zero_zero_percentage(league_id, season):
    url = f"{BASE_URL}/fixtures?league={league_id}&season={season}&status=FT"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        logger.debug(f"[{datetime.now()}] Status (estatísticas liga {league_id}): {response.status_code}")
        data = response.json()
        if "response" not in data:
            return None
        matches = data["response"]
        total_games = len(matches)
        zero_zero_games = sum(1 for m in matches if f"{m['goals']['home']} - {m['goals']['away']}" == "0 - 0")
        return (zero_zero_games / total_games * 100) if total_games > 0 else 0
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro ao buscar estatísticas da liga {league_id}: {e}")
        return None

def get_next_match(league_id):
    for days_ahead in range(7):
        date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        url = f"{BASE_URL}/fixtures?status=NS&league={league_id}&date={date}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            logger.debug(f"[{datetime.now()}] Status (próximo jogo {date}): {response.status_code}")
            data = response.json()
            if "response" in data and data["response"]:
                return data["response"][0]
        except Exception as e:
            logger.error(f"[{datetime.now()}] Erro ao buscar próximo jogo em {date}: {e}")
    return None

async def monitor_matches_zero_zero():
    logger.info(f"[{datetime.now()}] Iniciando monitoramento 0x0...")
    matches = get_recent_matches()
    if not matches:
        await send_telegram_message("ℹ️ Nenhuma partida finalizada encontrada hoje.")
        return
    
    zero_zero_found = False
    today = datetime.now().strftime("%Y-%m-%d")
    league_percentages = {}

    for match in matches:
        score = f"{match['goals']['home']} - {match['goals']['away']}"
        fixture_id = match['fixture']['id']
        if score == "0 - 0" and fixture_id not in notified_matches_zero_zero:
            league_id = match['league']['id']
            season = match['league']['season']
            
            if league_id not in league_percentages:
                percentage = get_league_zero_zero_percentage(league_id, season)
                league_percentages[league_id] = percentage
            else:
                percentage = league_percentages[league_id]
            
            if percentage is not None and percentage <= 5:
                home_team = match['teams']['home']['name']
                away_team = match['teams']['away']['name']
                league_name = match['league']['name']
                match_date = match['fixture']['date'].split("T")[0]
                
                next_match = get_next_match(league_id)
                next_game_info = "Não encontrado nos próximos 14 dias."
                if next_match:
                    next_home = next_match['teams']['home']['name']
                    next_away = next_match['teams']['away']['name']
                    next_date = next_match['fixture']['date'].split("T")[0]
                    next_time = next_match['fixture']['date'].split("T")[1].split("+")[0]
                    next_game_info = f"{next_home} x {next_away} ({next_date} às {next_time} UTC)"
                
                message = (
                    f"⚽ Resultado 0x0 detectado!\n"
                    f"Liga: {league_name}\n"
                    f"Jogo: {home_team} 0 x 0 {away_team}\n"
                    f"Data: {match_date}\n"
                    f"Percentagem de 0x0 na liga (temporada {season}): {percentage:.1f}%\n"
                    f"Próximo jogo: {next_game_info}"
                )
                await send_telegram_message(message)
                logger.info(f"[{datetime.now()}] Notificação 0x0 enviada para {home_team} vs {away_team}")
                notified_matches_zero_zero[fixture_id] = True
                zero_zero_found = True
    
    if not zero_zero_found:
        await send_telegram_message(f"ℹ️ Monitoramento concluído: {len(matches)} partidas de {today} analisadas, nenhum 0x0 novo em ligas com até 5%.")
    else:
        await send_telegram_message(f"ℹ️ Monitoramento concluído: {len(matches)} partidas de {today} analisadas.")

# Funções para o bot de times de elite
def buscar_estatisticas(equipe_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?team={equipe_id}&league={league_id}&season={season}"
    try:
        r = requests.get(url, headers=HEADERS).json()
        if "response" not in r or not r["response"]:
            return None
        stats = r["response"]
        media_gols = stats["goals"]["for"]["average"]["total"]
        perc_vitorias = stats["fixtures"]["wins"]["total"] / stats["fixtures"]["played"]["total"] * 100
        return media_gols, perc_vitorias
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas da equipe {equipe_id}: {e}")
        return None

def buscar_ultimo_jogo(equipe_id):
    url = f"{BASE_URL}/fixtures?team={equipe_id}&last=1"
    try:
        r = requests.get(url, headers=HEADERS).json()
        if "response" not in r or not r["response"]:
            return None
        jogo = r["response"][0]
        mandante = jogo["teams"]["home"]["name"]
        visitante = jogo["teams"]["away"]["name"]
        placar = f"{jogo['goals']['home']}x{jogo['goals']['away']}"
        return f"{mandante} {placar} {visitante}"
    except Exception as e:
        logger.error(f"Erro ao buscar último jogo da equipe {equipe_id}: {e}")
        return None

def formatar_contagem_regressiva(delta: timedelta) -> str:
    horas, resto = divmod(int(delta.total_seconds()), 3600)
    minutos = resto // 60
    if horas > 0:
        return f"{horas}h {minutos}min"
    else:
        return f"{minutos}min"

def verificar_jogos_elite():
    agora_utc = datetime.now(timezone.utc)
    daqui_24h_utc = agora_utc + timedelta(hours=24)
    hoje_str = agora_utc.date().isoformat()
    amanha_str = daqui_24h_utc.date().isoformat()

    logger.info(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos de equipas de elite nas próximas 24h...")

    encontrados = 0
    jogos_monitorados = []

    url_all_fixtures = f"{BASE_URL}/fixtures?from={hoje_str}&to={amanha_str}"
    
    try:
        r = requests.get(url_all_fixtures, headers=HEADERS).json()
        jogos = r.get("response", [])
        logger.debug(f"API retornou {len(jogos)} jogos no total para as próximas 24h.")
    except Exception as e:
        enviar_telegram_sync(f"❌ Erro na requisição principal da API: {e}")
        return

    for jogo in jogos:
        home = jogo["teams"]["home"]["name"]
        away = jogo["teams"]["away"]["name"]
        data_jogo_utc = datetime.fromisoformat(jogo["fixture"]["date"].replace("Z", "+00:00"))
        
        if agora_utc < data_jogo_utc <= daqui_24h_utc:
            if home in EQUIPAS_DE_TITULO or away in EQUIPAS_DE_TITULO:
                if jogo["fixture"]["id"] not in [j["id"] for j in jogos_monitorados]:
                    jogos_monitorados.append({"id": jogo["fixture"]["id"], "data": jogo})
                    encontrados += 1
                    
                    equipe_id = jogo["teams"]["home"]["id"] if home in EQUIPAS_DE_TITULO else jogo["teams"]["away"]["id"]
                    league_id = jogo["league"]["id"]
                    season = jogo["league"]["season"]
                    
                    stats = buscar_estatisticas(equipe_id, league_id, season)
                    ultimo_jogo = buscar_ultimo_jogo(equipe_id)
                    
                    data_jogo_lisboa = data_jogo_utc.astimezone(ZoneInfo("Europe/Lisbon"))
                    falta = formatar_contagem_regressiva(data_jogo_utc - agora_utc)
                    
                    if stats:
                        media_gols, perc_vitorias = stats
                        msg = (
                            f"🏆 <b>Equipa de Elite em campo</b> 🏆\n"
                            f"⏰ {data_jogo_lisboa.strftime('%H:%M')} (hora Lisboa) - {home} vs {away}\n"
                            f"⏳ Começa em {falta}\n\n"
                            f"📊 Estatísticas recentes do <b>{home if home in EQUIPAS_DE_TITULO else away}</b>:\n"
                            f"• Gols/jogo: {media_gols}\n"
                            f"• Vitórias: {perc_vitorias:.1f}%\n"
                            f"• Último resultado: {ultimo_jogo}\n\n"
                            f"⚔️ Esta equipa normalmente luta pelo título!"
                        )
                        enviar_telegram_sync(msg)
                        
    if encontrados == 0:
        enviar_telegram_sync(f"⚽ Nenhum jogo de equipa monitorada encontrado nas próximas 24h ({datetime.now().strftime('%H:%M %d/%m')}).")

# =========================================================
# LÓGICA DE SERVIDOR WEB (FLASK/AIOHTTP) E AGENDAMENTO
# =========================================================

# Rota principal para renderizar o dashboard (do código Flask)
@app.route('/')
def index():
    try:
        # Adapte a lógica para obter os dados de alertas, se necessário
        alerts = [] # Exemplo
        stats = {
            "total_alerts": len(alerts),
            "resolved_alerts": 0,
            "escalated_alerts": 0
        }
        return render_template('index.html', alerts=alerts, stats=stats)
    except Exception as e:
        logger.error(f"Erro ao renderizar index: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Rota para verificar se o servidor está funcionando
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Evento Socket.IO: Conexão estabelecida
@socketio.on('connect')
def handle_connect():
    logger.debug("Cliente conectado via Socket.IO")
    # A lógica de envio de alertas iniciais pode ser adicionada aqui, se houver um dashboard

# Rota de teste para simular um novo alerta
@app.route('/test_alert/<message>')
def test_alert(message):
    try:
        # A lógica de enviar um novo alerta via Socket.IO precisaria ser adaptada
        socketio.emit('new_alert', {"message": message, "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")})
        return jsonify({"status": "success", "message": "Alerta de teste enviado"})
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de teste: {str(e)}")
        return jsonify({"status": "error", "message": "Falha ao enviar alerta"}), 500

async def run_server_aiohttp():
    aiohttp_app = web.Application()
    aiohttp_app.add_routes([web.get('/', lambda r: web.Response(text="Bot is running")),
                           web.get('/health', lambda r: web.Response(text="Bot is running"))])
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info(f"[{datetime.now()}] Servidor AIOHTTP iniciado na porta 8080")

async def monitor_loops():
    """Roda as checagens dos bots em loops agendados."""
    while True:
        try:
            verificar_jogos_elite()
        except Exception as e:
            logger.error(f"Erro no loop de jogos de elite: {e}")
            enviar_telegram_sync(f"⚠️ Erro no bot de elite: {e}")
        
        try:
            await monitor_matches_zero_zero()
        except Exception as e:
            logger.error(f"Erro no loop do bot 0x0: {e}")
            await send_telegram_message(f"⚠️ Erro no bot 0x0: {e}")
            
        logger.info(f"[{datetime.now()}] Aguardando próxima verificação...")
        await asyncio.sleep(86300) # 86300 segundos = ~24 horas, ajustado para evitar conflitos de tempo

async def main():
    """Função principal que inicia todos os serviços."""
    await asyncio.gather(
        run_server_aiohttp(),
        monitor_loops()
    )

if __name__ == "__main__":
    # Para o ambiente de produção, use gunicorn ou equivalente
    if 'GUNICORN_WORKERS' in os.environ:
        logger.info("Modo de produção: Gunicorn/Eventlet. Iniciando servidor Flask.")
        socketio.run(app, debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        logger.info("Modo de desenvolvimento: executando loops assíncronos e servidor AIOHTTP.")
        asyncio.run(main())
