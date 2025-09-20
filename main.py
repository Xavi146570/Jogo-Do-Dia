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

# =========================================================
# CONFIGURAÇÕES GERAIS E INICIALIZAÇÃO
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variáveis de Ambiente e Configurações API
# IMPORTANTE: Os valores de token e ID foram removidos para segurança.
# Você deve defini-los nas variáveis de ambiente do seu serviço de hospedagem.
API_KEY = os.environ.get("LIVESCORE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Validar se as variáveis de ambiente estão definidas
if not all([API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logger.error("❌ Variáveis de ambiente API_KEY, TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não estão configuradas. O bot não pode ser iniciado.")
    exit(1)

# Inicialização do Bot do Telegram
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Controle de notificações
notified_matches = {
    'finished_0x0': set(),
    'halftime_0x0': set(),
    'elite_games': set(),
    'under_15': set()
}

# Top 10 campeonatos principais para monitoramento
TOP_LEAGUES = {
    39: "Premier League",      # Inglaterra
    140: "La Liga",          # Espanha  
    78: "Bundesliga",         # Alemanha
    135: "Serie A",          # Itália
    61: "Ligue 1",           # França
    94: "Primeira Liga",      # Portugal
    88: "Eredivisie",         # Holanda
    144: "Jupiler Pro League", # Bélgica
    203: "Süper Lig",          # Turquia
    235: "Premier League"      # Rússia
}

# Lista expandida de equipes de elite
EQUIPAS_DE_TITULO = [
    # Premier League
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea", "Tottenham",
    # La Liga  
    "Real Madrid", "Barcelona", "Atletico Madrid", "Real Sociedad", "Athletic Club",
    # Bundesliga
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", "Eintracht Frankfurt",
    # Serie A
    "Inter", "AC Milan", "Juventus", "Napoli", "AS Roma", "Lazio", "Atalanta",
    # Ligue 1
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille", "Nice",
    # Primeira Liga
    "Benfica", "Porto", "Sporting CP", "Braga", "Vitoria de Guimaraes",
    # Eredivisie  
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar", "FC Twente",
    # Outros grandes clubes europeus
    "Celtic", "Rangers", "Galatasaray", "Fenerbahce", "Besiktas"
]

# Cache para evitar requests repetitivos
cache_team_stats = {}
cache_league_stats = {}

# =========================================================
# FUNÇÕES UTILITÁRIAS E API
# =========================================================

async def send_telegram_message(message):
    """Envia mensagem assíncrona para o Telegram"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        logger.info("✅ Mensagem enviada para o Telegram")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")

def enviar_telegram_sync(msg: str):
    """Envia mensagem síncrona para o Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Credenciais do Telegram não configuradas")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,  
        "text": msg,  
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ Mensagem síncrona enviada")
    except Exception as e:
        logger.error(f"❌ Erro no envio síncrono: {e}")

def make_api_request(endpoint, params=None, retries=3):
    """Faz requisição para a API com retry automático"""
    if params is None:
        params = {}
        
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if "response" not in data:
                raise ValueError("Resposta inválida da API")
                
            return data["response"]
            
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1}/{retries} falhou: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Backoff exponencial
            else:
                logger.error(f"Falha definitiva na requisição para {endpoint}")
                return []

# =========================================================
# ANÁLISE HISTÓRICA DE DADOS
# =========================================================

def analyze_team_0x0_history(team_id, league_id):
    """Analisa histórico de 0x0 de uma equipe nas últimas 3 temporadas"""
    cache_key = f"team_{team_id}_{league_id}"
    
    # Verificar cache (válido por 1 hora)
    if cache_key in cache_team_stats:
        cached_data = cache_team_stats[cache_key]
        if datetime.now().timestamp() - cached_data['timestamp'] < 3600:
            return cached_data['data']
    
    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    
    total_matches = 0
    total_0x0 = 0
    
    for season in seasons:
        try:
            # Buscar jogos da equipe na temporada
            fixtures = make_api_request("/fixtures", {
                "team": team_id,
                "league": league_id,  
                "season": season,
                "status": "FT"
            })
            
            if fixtures:
                season_matches = len(fixtures)
                season_0x0 = sum(1 for match in fixtures  
                                if match['goals']['home'] == 0 and match['goals']['away'] == 0)
                
                total_matches += season_matches
                total_0x0 += season_0x0
                
                logger.info(f"Temporada {season}: {season_0x0}/{season_matches} jogos 0x0")
                
        except Exception as e:
            logger.warning(f"Erro ao analisar temporada {season} para equipe {team_id}: {e}")
    
    # Calcular percentual
    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10  # Critério: menos de 10%
    }
    
    # Salvar no cache
    cache_team_stats[cache_key] = {
        'data': result,
        'timestamp': datetime.now().timestamp()
    }
    
    return result

def analyze_league_0x0_history(league_id):
    """Analisa histórico de 0x0 de uma liga nas últimas 3 temporadas"""
    cache_key = f"league_{league_id}"
    
    if cache_key in cache_league_stats:
        cached_data = cache_league_stats[cache_key]
        if datetime.now().timestamp() - cached_data['timestamp'] < 3600:
            return cached_data['data']
    
    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    
    total_matches = 0
    total_0x0 = 0
    
    for season in seasons:
        try:
            fixtures = make_api_request("/fixtures", {
                "league": league_id,
                "season": season,
                "status": "FT"
            })
            
            if fixtures:
                season_matches = len(fixtures)
                season_0x0 = sum(1 for match in fixtures
                                if match['goals']['home'] == 0 and match['goals']['away'] == 0)
                
                total_matches += season_matches
                total_0x0 += season_0x0
                
        except Exception as e:
            logger.warning(f"Erro ao analisar temporada {season} da liga {league_id}: {e}")
    
    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10
    }
    
    cache_league_stats[cache_key] = {
        'data': result,
        'timestamp': datetime.now().timestamp()
    }
    
    return result

# =========================================================
# MONITORAMENTO DE JOGOS AO VIVO
# =========================================================

async def monitor_live_matches():
    """Monitora jogos ao vivo para detectar eventos"""
    logger.info("🔍 Verificando jogos ao vivo...")
    
    try:
        # Buscar jogos ao vivo
        live_matches = make_api_request("/fixtures", {"live": "all"})
        
        if not live_matches:
            logger.info("Nenhum jogo ao vivo no momento")
            return
            
        logger.info(f"Encontrados {len(live_matches)} jogos ao vivo")
        
        for match in live_matches:
            await process_live_match(match)
            
    except Exception as e:
        logger.error(f"Erro no monitoramento ao vivo: {e}")

async def process_live_match(match):
    """Processa um jogo ao vivo individual"""
    fixture_id = match['fixture']['id']
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    status = match['fixture']['status']['short']
    league_id = match['league']['id']
    
    # Verificar se a liga está nos top 10 campeonatos
    if league_id not in TOP_LEAGUES:
        return
    
    # Analisar histórico da liga
    league_analysis = analyze_league_0x0_history(league_id)
    if not league_analysis['qualifies']:
        return
    
    # Verificar equipes qualificadas
    home_analysis = analyze_team_0x0_history(match['teams']['home']['id'], league_id)
    away_analysis = analyze_team_0x0_history(match['teams']['away']['id'], league_id)
    
    teams_qualify = home_analysis['qualifies'] or away_analysis['qualifies']
    
    if not teams_qualify:
        return
    
    # **NOVO: Notificar intervalo 0x0**
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        notification_key = f"halftime_{fixture_id}"
        if notification_key not in notified_matches['halftime_0x0']:
            message = f"""
⏸️ <b>INTERVALO 0x0 DETECTADO</b> ⏸️

🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga desconhecida')}</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Análise Histórica:</b>
• Liga: {league_analysis['percentage']}% de jogos 0x0 (últimas 3 temporadas)
• {home_team}: {home_analysis['percentage']}% de jogos 0x0
• {away_team}: {away_analysis['percentage']}% de jogos 0x0

🕐 <i>{datetime.now().strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['halftime_0x0'].add(notification_key)
    
    # **Notificar jogo terminado 0x0**
    elif status == 'FT' and home_goals == 0 and away_goals == 0:
        notification_key = f"finished_{fixture_id}"
        if notification_key not in notified_matches['finished_0x0']:
            message = f"""
🚨 <b>JOGO TERMINOU 0x0</b> 🚨

🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga desconhecida')}</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Análise Histórica (últimas 3 temporadas):</b>
• Liga: {league_analysis['percentage']}% de jogos 0x0
• {home_team}: {home_analysis['percentage']}%  
• {away_team}: {away_analysis['percentage']}%

🎯 Ambas as condições atendidas: equipes e liga com <10% de 0x0!

🕐 <i>{datetime.now().strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(notification_key)

# =========================================================
# MONITORAMENTO DE EQUIPES DE ELITE
# =========================================================

async def monitor_elite_teams():
    """Monitora jogos de equipes de elite"""
    logger.info("👑 Verificando jogos de equipes de elite...")
    
    try:
        # Buscar jogos de hoje e amanhã
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Jogos futuros (para "jogo do dia")
        upcoming_matches = make_api_request("/fixtures", {
            "from": today,
            "to": tomorrow,
            "status": "NS"
        })
        
        # Jogos finalizados (para Under 1.5)
        finished_matches = make_api_request("/fixtures", {
            "date": today,
            "status": "FT"
        })
        
        # Processar jogos futuros
        for match in upcoming_matches:
            await process_elite_upcoming_match(match)
        
        # Processar jogos finalizados
        for match in finished_matches:
            await process_elite_finished_match(match)
            
    except Exception as e:
        logger.error(f"Erro no monitoramento de elite: {e}")

async def process_elite_upcoming_match(match):
    """Processa jogos futuros de equipes de elite"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Verificar se é um dos top 10 campeonatos
    if league_id not in TOP_LEAGUES:
        return
    
    # Verificar se ambas as equipes são de elite
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    if home_is_elite and away_is_elite:
        notification_key = f"elite_game_{fixture_id}"
        if notification_key not in notified_matches['elite_games']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time_local = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            message = f"""
⭐ <b>JOGO DO DIA - EQUIPES DE ELITE</b> ⭐

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} vs {away_team}</b>

👑 Ambas as equipes lutam pelo título!

🕐 <b>{match_time_local.strftime('%H:%M')} (hora de Lisboa)</b>
📅 {match_time_local.strftime('%d/%m/%Y')}

🔥 Jogo de alto nível entre gigantes!
            """
            
            await send_telegram_message(message)
            notified_matches['elite_games'].add(notification_key)

async def process_elite_finished_match(match):
    """Processa jogos finalizados de equipes de elite para Under 1.5"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Verificar se é um dos top 10 campeonatos
    if league_id not in TOP_LEAGUES:
        return
    
    # Verificar se ambas as equipes são de elite
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    # **NOVO: Verificar Under 1.5 gols**
    if (home_is_elite and away_is_elite) and total_goals < 2:
        notification_key = f"under15_{fixture_id}"
        if notification_key not in notified_matches['under_15']:
            
            message = f"""
📉 <b>UNDER 1.5 GOLS - EQUIPES DE ELITE</b> 📉

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>

👑 Jogo entre equipes de elite com poucos gols!
📊 Total de gols: {total_goals} (Under 1.5 ✅)

🎯 Oportunidade identificada em jogo de alto nível!

🕐 <i>{datetime.now().strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['under_15'].add(notification_key)

# =========================================================
# SERVIDOR WEB E LOOP PRINCIPAL
# =========================================================

async def run_web_server():
    """Executa servidor web simples para o Render"""
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="Bot is running! ⚽", content_type="text/plain")
    
    async def status(request):
        status_info = {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "monitored_leagues": len(TOP_LEAGUES),
            "elite_teams": len(EQUIPAS_DE_TITULO),
            "notifications_sent": {
                "finished_0x0": len(notified_matches['finished_0x0']),
                "halftime_0x0": len(notified_matches['halftime_0x0']),
                "elite_games": len(notified_matches['elite_games']),
                "under_15": len(notified_matches['under_15'])
            }
        }
        return web.json_response(status_info)
    
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Servidor web iniciado na porta {port}")

async def monitoring_loop():
    """Loop principal de monitoramento, agora executando a cada 60 minutos."""
    logger.info("🤖 Iniciando loop de monitoramento...")
    
    # Enviar mensagem de inicialização
    await send_telegram_message("🚀 <b>Bot de Futebol Iniciado!</b>\n\nMonitorando jogos 0x0 e equipes de elite... ⚽")
    
    while True:
        try:
            # Executar monitoramentos
            await monitor_live_matches()
            await monitor_elite_teams()
            
            # Aguardar 60 minutos antes da próxima verificação
            logger.info("😴 Aguardando 60 minutos para próxima verificação...")
            await asyncio.sleep(3600)  # 60 minutos
            
        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")
            await send_telegram_message(f"⚠️ Erro no bot: {e}")
            await asyncio.sleep(60)  # Aguardar 1 minuto em caso de erro

async def daily_status():
    """Envia status diário do bot"""
    while True:
        try:
            # Aguardar 24 horas
            await asyncio.sleep(86400)
            
            status_message = f"""
📊 <b>Relatório Diário do Bot</b>

🎯 <b>Notificações enviadas hoje:</b>
• Jogos 0x0 finalizados: {len(notified_matches['finished_0x0'])}
• Intervalos 0x0: {len(notified_matches['halftime_0x0'])}
• Jogos do dia (elite): {len(notified_matches['elite_games'])}
• Under 1.5 (elite): {len(notified_matches['under_15'])}

🏆 Monitorando {len(TOP_LEAGUES)} ligas principais
👑 Acompanhando {len(EQUIPAS_DE_TITULO)} equipes de elite

✅ Bot funcionando perfeitamente!

🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """
            
            await send_telegram_message(status_message)
            
            # Limpar cache antigo
            notified_matches['finished_0x0'].clear()
            notified_matches['halftime_0x0'].clear()
            notified_matches['elite_games'].clear()
            notified_matches['under_15'].clear()
            
        except Exception as e:
            logger.error(f"Erro no status diário: {e}")

async def main():
    """Função principal que coordena todos os serviços"""
    logger.info("🚀 Iniciando Bot de Monitoramento de Futebol...")
    
    # Executar todos os serviços em paralelo
    await asyncio.gather(
        run_web_server(),
        monitoring_loop(),
        daily_status()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
