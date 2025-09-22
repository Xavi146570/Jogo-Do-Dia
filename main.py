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
API_KEY = os.environ.get("LIVESCORE_API_KEY", "968c152b0a72f3fa63087d74b04eee5d")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7588970032:AAH6MDy42ZJJnlYlclr3GVeCfXS-XiePFuo")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1002682430417")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

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
    39: "Premier League",     # Inglaterra
    140: "La Liga",          # Espanha  
    78: "Bundesliga",        # Alemanha
    135: "Serie A",          # Itália
    61: "Ligue 1",           # França
    94: "Primeira Liga",     # Portugal
    88: "Eredivisie",        # Holanda
    144: "Jupiler Pro League", # Bélgica
    203: "Süper Lig",        # Turquia
    235: "Premier League"     # Rússia
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
cache_elite_stats = {}

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

def get_current_hour_lisbon():
    """Retorna a hora atual em Lisboa"""
    return datetime.now(ZoneInfo("Europe/Lisbon")).hour

def should_run_monitoring():
    """Verifica se deve executar o monitoramento (09h às 23h)"""
    current_hour = get_current_hour_lisbon()
    return 9 <= current_hour <= 23

# =========================================================
# ANÁLISE HISTÓRICA DE DADOS (Melhorada)
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
                
                logger.debug(f"Equipe {team_id} - Temporada {season}: {season_0x0}/{season_matches} jogos 0x0")
                
        except Exception as e:
            logger.warning(f"Erro ao analisar temporada {season} para equipe {team_id}: {e}")
    
    # Calcular percentual
    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10
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

def analyze_elite_team_stats(team_id, league_id):
    """NOVO: Analisa estatísticas detalhadas das equipes de elite (% vitórias e Over 1.5)"""
    cache_key = f"elite_{team_id}_{league_id}"
    
    # Cache válido por 2 horas para estatísticas de elite
    if cache_key in cache_elite_stats:
        cached_data = cache_elite_stats[cache_key]
        if datetime.now().timestamp() - cached_data['timestamp'] < 7200:
            return cached_data['data']
    
    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    
    total_matches = 0
    total_wins = 0
    total_over_15 = 0
    
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
                for match in fixtures:
                    total_matches += 1
                    
                    # Verificar vitórias
                    home_goals = match['goals']['home'] or 0
                    away_goals = match['goals']['away'] or 0
                    team_is_home = match['teams']['home']['id'] == team_id
                    
                    if team_is_home and home_goals > away_goals:
                        total_wins += 1
                    elif not team_is_home and away_goals > home_goals:
                        total_wins += 1
                    
                    # Verificar Over 1.5 gols
                    total_goals = home_goals + away_goals
                    if total_goals > 1:  # Over 1.5 = 2 ou mais gols
                        total_over_15 += 1
                        
        except Exception as e:
            logger.warning(f"Erro ao analisar estatísticas de elite para equipe {team_id}, temporada {season}: {e}")
    
    # Calcular percentuais
    win_percentage = (total_wins / total_matches * 100) if total_matches > 0 else 0
    over_15_percentage = (total_over_15 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'win_percentage': round(win_percentage, 1),
        'over_15_percentage': round(over_15_percentage, 1),
        'total_matches': total_matches,
        'total_wins': total_wins,
        'total_over_15': total_over_15
    }
    
    # Salvar no cache
    cache_elite_stats[cache_key] = {
        'data': result,
        'timestamp': datetime.now().timestamp()
    }
    
    return result

# =========================================================
# MONITORAMENTO DE JOGOS AO VIVO
# =========================================================

async def monitor_live_matches():
    """Monitora jogos ao vivo para detectar eventos"""
    if not should_run_monitoring():
        logger.info(f"Fora do horário de monitoramento (atual: {get_current_hour_lisbon()}h)")
        return
        
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
    
    # **Notificar intervalo 0x0**
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        notification_key = f"halftime_{fixture_id}"
        if notification_key not in notified_matches['halftime_0x0']:
            message = f"""
⏸️ <b>INTERVALO 0x0 DETECTADO</b> ⏸️

🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga desconhecida')}</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Análise Histórica (últimas 3 temporadas):</b>
• Liga: {league_analysis['percentage']}% de jogos 0x0
• {home_team}: {home_analysis['percentage']}% de jogos 0x0
• {away_team}: {away_analysis['percentage']}% de jogos 0x0

🎯 Condições atendidas: liga e equipes com <10% de 0x0!

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
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
• {home_team}: {home_analysis['percentage']}% de jogos 0x0
• {away_team}: {away_analysis['percentage']}% de jogos 0x0

🎯 Oportunidade confirmada: ambas as condições atendidas!

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(notification_key)

# =========================================================
# MONITORAMENTO DE EQUIPES DE ELITE (Melhorado)
# =========================================================

async def monitor_elite_teams():
    """Monitora jogos de equipes de elite"""
    if not should_run_monitoring():
        return
        
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
    """Processa jogos futuros de equipes de elite com estatísticas detalhadas"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
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
            
            # **NOVO: Buscar estatísticas detalhadas das equipes de elite**
            home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
            away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
            
            message = f"""
⭐ <b>JOGO DO DIA - EQUIPES DE ELITE</b> ⭐

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} vs {away_team}</b>

👑 Ambas as equipes lutam pelo título!

🕐 <b>{match_time_local.strftime('%H:%M')} (Lisboa)</b>
📅 {match_time_local.strftime('%d/%m/%Y')}

📊 <b>Estatísticas (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%

🔥 Confronto de alto nível entre gigantes!
            """
            
            await send_telegram_message(message)
            notified_matches['elite_games'].add(notification_key)

async def process_elite_finished_match(match):
    """Processa jogos finalizados de equipes de elite para Under 1.5"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
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
    
    # **Verificar Under 1.5 gols**
    if (home_is_elite and away_is_elite) and total_goals < 2:
        notification_key = f"under15_{fixture_id}"
        if notification_key not in notified_matches['under_15']:
            
            # **NOVO: Incluir estatísticas detalhadas na notificação Under 1.5**
            home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
            away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
            
            message = f"""
📉 <b>UNDER 1.5 GOLS - EQUIPES DE ELITE</b> 📉

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>

👑 Jogo entre equipes de elite com poucos gols!
📊 Total de gols: {total_goals} (Under 1.5 ✅)

📈 <b>Estatísticas das equipes (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%

🎯 Oportunidade rara: gigantes com poucos gols!

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['under_15'].add(notification_key)

# =========================================================
# AGENDAMENTO HORÁRIO (NOVO)
# =========================================================

async def hourly_monitoring():
    """Executa monitoramento a cada hora das 09h às 23h"""
    logger.info("⏰ Iniciando sistema de monitoramento horário...")
    
    # Enviar mensagem de inicialização
    await send_telegram_message(
        f"🚀 <b>Bot de Futebol Iniciado!</b>\n\n"
        f"⏰ Monitoramento ativo das 09h às 23h (Lisboa)\n"
        f"🔍 Verificações a cada hora\n"
        f"⚽ Pronto para detectar oportunidades!"
    )
    
    while True:
        try:
            current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
            current_hour = current_time.hour
            
            if should_run_monitoring():
                logger.info(f"🕐 Executando monitoramento às {current_hour}h (Lisboa)")
                
                # Executar monitoramentos
                await monitor_live_matches()
                await monitor_elite_teams()
                
                logger.info(f"✅ Monitoramento das {current_hour}h concluído")
            else:
                logger.info(f"😴 Fora do horário de monitoramento (atual: {current_hour}h)")
            
            # Calcular tempo até a próxima hora
            next_hour = (current_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1))
            wait_time = (next_hour - current_time).total_seconds()
            
            logger.info(f"⏳ Aguardando {int(wait_time/60)} minutos até próxima verificação...")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Erro no loop horário: {e}")
            await send_telegram_message(f"⚠️ Erro no bot: {e}")
            await asyncio.sleep(300)  # Aguardar 5 minutos em caso de erro

# =========================================================
# RELATÓRIOS E STATUS
# =========================================================

async def daily_status():
    """Envia relatório diário às 08h"""
    while True:
        try:
            current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
            
            # Verificar se é 08h (antes do início do monitoramento)
            if current_time.hour == 8 and current_time.minute < 30:
                
                status_message = f"""
📊 <b>Relatório Diário do Bot</b>

🎯 <b>Notificações enviadas ontem:</b>
• Jogos 0x0 finalizados: {len(notified_matches['finished_0x0'])}
• Intervalos 0x0: {len(notified_matches['halftime_0x0'])}
• Jogos do dia (elite): {len(notified_matches['elite_games'])}
• Under 1.5 (elite): {len(notified_matches['under_15'])}

🏆 Monitorando {len(TOP_LEAGUES)} ligas principais
👑 Acompanhando {len(EQUIPAS_DE_TITULO)} equipes de elite

⏰ <b>Horário de funcionamento:</b>
• Das 09h às 23h (Lisboa)
• Verificações a cada hora

✅ Bot funcionando perfeitamente!

🕐 {current_time.strftime('%d/%m/%Y %H:%M')} (Lisboa)
                """
                
                await send_telegram_message(status_message)
                
                # Limpar contadores do dia anterior
                notified_matches['finished_0x0'].clear()
                notified_matches['halftime_0x0'].clear()
                notified_matches['elite_games'].clear()
                notified_matches['under_15'].clear()
                
                # Aguardar até o próximo dia
                await asyncio.sleep(23 * 3600)  # 23 horas
            else:
                # Aguardar até às 08h do próximo dia
                next_day_8am = (current_time.replace(hour=8, minute=0, second=0, microsecond=0) + 
                               timedelta(days=1))
                wait_time = (next_day_8am - current_time).total_seconds()
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Erro no relatório diário: {e}")
            await asyncio.sleep(3600)  # Aguardar 1 hora

# =========================================================
# SERVIDOR WEB
# =========================================================

async def run_web_server():
    """Executa servidor web simples para o Render"""
    app = web.Application()
    
    async def health_check(request):
        current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
        is_active = should_run_monitoring()
        
        status_html = f"""
        <html>
        <head>
            <title>Bot de Futebol - Status</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>🤖 Bot de Monitoramento de Futebol</h1>
            
            <h2>📊 Status Atual</h2>
            <ul>
                <li><strong>Hora atual (Lisboa):</strong> {current_time.strftime('%H:%M %d/%m/%Y')}</li>
                <li><strong>Status:</strong> {'🟢 ATIVO' if is_active else '🔴 INATIVO'}</li>
                <li><strong>Horário de funcionamento:</strong> 09h às 23h (Lisboa)</li>
                <li><strong>Próxima verificação:</strong> No início da próxima hora</li>
            </ul>
            
            <h2>🎯 Estatísticas de Hoje</h2>
            <ul>
                <li><strong>Jogos 0x0 finalizados:</strong> {len(notified_matches['finished_0x0'])}</li>
                <li><strong>Intervalos 0x0:</strong> {len(notified_matches['halftime_0x0'])}</li>
                <li><strong>Jogos do dia (elite):</strong> {len(notified_matches['elite_games'])}</li>
                <li><strong>Under 1.5 (elite):</strong> {len(notified_matches['under_15'])}</li>
            </ul>
            
            <h2>🏆 Configuração</h2>
            <ul>
                <li><strong>Ligas monitoradas:</strong> {len(TOP_LEAGUES)}</li>
                <li><strong>Equipes de elite:</strong> {len(EQUIPAS_DE_TITULO)}</li>
            </ul>
            
            <p><em>Bot funcionando perfeitamente! ⚽</em></p>
        </body>
        </html>
        """
        
        return web.Response(text=status_html, content_type="text/html")
    
    async def status_json(request):
        current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
        status_info = {
            "status": "active" if should_run_monitoring() else "standby",
            "current_time_lisbon": current_time.isoformat(),
            "current_hour": current_time.hour,
            "active_hours": "09:00-23:00 Lisboa",
            "monitored_leagues": len(TOP_LEAGUES),
            "elite_teams": len(EQUIPAS_DE_TITULO),
            "notifications_today": {
                "finished_0x0": len(notified_matches['finished_0x0']),
                "halftime_0x0": len(notified_matches['halftime_0x0']),
                "elite_games": len(notified_matches['elite_games']),
                "under_15": len(notified_matches['under_15'])
            }
        }
        return web.json_response(status_info)
    
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status_json)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Servidor web iniciado na porta {port}")

# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================

async def main():
    """Função principal que coordena todos os serviços"""
    logger.info("🚀 Iniciando Bot de Monitoramento de Futebol...")
    logger.info(f"⏰ Horário de funcionamento: 09h às 23h (Lisboa)")
    logger.info(f"🔄 Verificações a cada hora")
    
    # Executar todos os serviços em paralelo
    await asyncio.gather(
        run_web_server(),
        hourly_monitoring(),
        daily_status()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

