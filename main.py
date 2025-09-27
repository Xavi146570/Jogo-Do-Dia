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
# Variável para rastrear se a primeira execução já ocorreu
first_run_complete = False

# Top 10 campeonatos principais para monitoramento
TOP_LEAGUES = {
    39: "Premier League",       # Inglaterra
    140: "La Liga",            # Espanha  
    78: "Bundesliga",           # Alemanha
    135: "Serie A",            # Itália
    61: "Ligue 1",              # França
    94: "Primeira Liga",        # Portugal
    88: "Eredivisie",           # Holanda
    144: "Jupiler Pro League",  # Bélgica
    203: "Süper Lig",           # Turquia
    235: "Premier League"       # Rússia
}

# Lista expandida de equipes de elite
EQUIPAS_DE_TITULO = [
    # Premier League
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea", "Tottenham", "Burnley",
    # La Liga  
    "Real Madrid", "Barcelona", "Atletico Madrid", "Real Sociedad", "Athletic Club",
    # Bundesliga
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", "Eintracht Frankfurt",
    # Serie A
    "Inter", "AC Milan", "Juventus", "Napoli", "AS Roma", "Lazio", "Atalanta",
    # Ligue 1
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille", "Nice",
    # Primeira Liga
    "Benfica", "SL Benfica", "Porto", "Sporting CP", "Braga", "Vitoria de Guimaraes",
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
                if data.get("errors"):
                    raise ValueError(f"Erro da API: {data['errors']}")
                raise ValueError("Resposta inválida da API")
                
            return data["response"]
            
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1}/{retries} falhou para {endpoint}: {e}")
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
# ANÁLISE HISTÓRICA DE DADOS 
# =========================================================

def analyze_team_0x0_history(team_id, league_id):
    """Analisa histórico de 0x0 de uma equipe nas últimas 3 temporadas"""
    cache_key = f"team_{team_id}_{league_id}"
    
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
                
        except Exception as e:
            logger.warning(f"Erro ao analisar temporada {season} para equipe {team_id}: {e}")
    
    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 5
    }
    
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
    """Analisa estatísticas detalhadas das equipes de elite"""
    cache_key = f"elite_{team_id}_{league_id}"
    
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
            fixtures = make_api_request("/fixtures", {
                "team": team_id,
                "league": league_id,
                "season": season,
                "status": "FT"
            })
            
            if fixtures:
                for match in fixtures:
                    total_matches += 1
                    
                    home_goals = match['goals']['home'] or 0
                    away_goals = match['goals']['away'] or 0
                    team_is_home = match['teams']['home']['id'] == team_id
                    
                    if team_is_home and home_goals > away_goals:
                        total_wins += 1
                    elif not team_is_home and away_goals > home_goals:
                        total_wins += 1
                    
                    total_goals = home_goals + away_goals
                    if total_goals > 1:
                        total_over_15 += 1
                        
        except Exception as e:
            logger.warning(f"Erro ao analisar estatísticas de elite para equipe {team_id}, temporada {season}: {e}")
    
    win_percentage = (total_wins / total_matches * 100) if total_matches > 0 else 0
    over_15_percentage = (total_over_15 / total_matches * 100) if total_matches > 0 else 0
    
    result = {
        'win_percentage': round(win_percentage, 1),
        'over_15_percentage': round(over_15_percentage, 1),
        'total_matches': total_matches,
        'total_wins': total_wins,
        'total_over_15': total_over_15
    }
    
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
    
    if league_id not in TOP_LEAGUES:
        return
    
    league_analysis = analyze_league_0x0_history(league_id)
    if not league_analysis['qualifies']:
        return
    
    home_analysis = analyze_team_0x0_history(match['teams']['home']['id'], league_id)
    away_analysis = analyze_team_0x0_history(match['teams']['away']['id'], league_id)
    
    teams_qualify = home_analysis['qualifies'] or away_analysis['qualifies']
    
    if not teams_qualify:
        return
    
    # Notificar intervalo 0x0
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        notification_key = f"halftime_{fixture_id}"
        if notification_key not in notified_matches['halftime_0x0']:
            message = (
                f"⏸️ <b>INTERVALO 0x0 DETECTADO</b> ⏸️\n\n"
                f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga desconhecida')}</b>\n"
                f"⚽ <b>{home_team} 0 x 0 {away_team}</b>\n\n"
                f"📊 <b>Análise Histórica (últimas 3 temporadas):</b>\n"
                f"• Liga: {league_analysis['percentage']}% de jogos 0x0\n"
                f"• {home_team}: {home_analysis['percentage']}% de jogos 0x0\n"
                f"• {away_team}: {away_analysis['percentage']}% de jogos 0x0\n\n"
                f"🎯 Condições atendidas: liga e equipes com menos de 10% de 0x0!\n\n"
                f"🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>"
            )
            
            await send_telegram_message(message)
            notified_matches['halftime_0x0'].add(notification_key)
    
    # Notificar jogo terminado 0x0
    elif status == 'FT' and home_goals == 0 and away_goals == 0:
        notification_key = f"finished_{fixture_id}"
        if notification_key not in notified_matches['finished_0x0']:
            message = (
                f"🚨 <b>JOGO TERMINOU 0x0</b> 🚨\n\n"
                f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga desconhecida')}</b>\n"
                f"⚽ <b>{home_team} 0 x 0 {away_team}</b>\n\n"
                f"📊 <b>Análise Histórica (últimas 3 temporadas):</b>\n"
                f"• Liga: {league_analysis['percentage']}% de jogos 0x0\n"
                f"• {home_team}: {home_analysis['percentage']}% de jogos 0x0\n"
                f"• {away_team}: {away_analysis['percentage']}% de jogos 0x0\n\n"
                f"🎯 Oportunidade confirmada: ambas as condições atendidas!\n\n"
                f"🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>"
            )
            
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(notification_key)

# =========================================================
# MONITORAMENTO DE EQUIPES DE ELITE (CORRIGIDO PARA FORÇAR DATA)
# =========================================================

async def monitor_elite_teams():
    """Monitora jogos de equipes de elite: futuros (NS) para notificação 'Jogo do Dia' e finalizados (FT) para 'Under 1.5'"""
    if not should_run_monitoring():
        return
        
    logger.info("👑 Verificando jogos de equipes de elite...")
    
    try:
        # Data de hoje em Lisboa
        today_date_str = datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%Y-%m-%d')
        all_matches_to_process = []
        
        # 1. BUSCAR JOGOS FUTUROS (NS) DE HOJE - APENAS POR DATA E STATUS (NOVO FOCO)
        fixtures_ns = make_api_request("/fixtures", {
            "date": today_date_str, # Usar a data de hoje para o filtro
            "status": "NS"          # Usar o status Not Started
        })
        if fixtures_ns:
            logger.info(f"Encontrados {len(fixtures_ns)} jogos futuros (NS) para {today_date_str}.")
            all_matches_to_process.extend(fixtures_ns)
            
        # 2. BUSCAR JOGOS FINALIZADOS (FT) DE HOJE NAS LIGAS TOP
        for league_id in TOP_LEAGUES.keys():
            fixtures_ft = make_api_request("/fixtures", {
                "date": today_date_str,
                "league": league_id,
                "status": "FT"
            })
            if fixtures_ft:
                all_matches_to_process.extend(fixtures_ft)
        
        if not all_matches_to_process:
            logger.info("Nenhum jogo relevante nas ligas top (NS ou FT de hoje).")
            return
            
        processed_fixture_ids = set()
        
        for match in all_matches_to_process:
            fixture_id = match['fixture']['id']
            
            if fixture_id in processed_fixture_ids:
                continue
            processed_fixture_ids.add(fixture_id)
            
            status = match['fixture']['status']['short']
            league_id = match['league']['id']
            
            # OBRIGATÓRIO: Filtrar aqui para garantir que é uma liga top
            if league_id not in TOP_LEAGUES:
                continue

            # Processar jogos que AINDA NÃO COMEÇARAM (Not Started)
            if status == 'NS':
                await process_elite_upcoming_match(match)
            
            # Processar jogos FINALIZADOS (Full Time)
            elif status == 'FT':
                await process_elite_finished_match(match)
                
    except Exception as e:
        logger.error(f"Erro no monitoramento de elite: {e}")


async def process_elite_upcoming_match(match):
    """Processa jogos futuros quando pelo menos uma equipe é de elite"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Redundante, mas OK
    if league_id not in TOP_LEAGUES:
        return
    
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    if not (home_is_elite or away_is_elite):
        return
    
    notification_key = f"elite_game_{fixture_id}"
    
    if notification_key not in notified_matches['elite_games']:
        
        try:
            match_datetime_utc = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
        except ValueError:
            match_datetime_utc = datetime.fromisoformat(match['fixture']['date'])

        match_time_local = match_datetime_utc.astimezone(ZoneInfo("Europe/Lisbon"))
        
        # Tenta carregar estatísticas, senão usa texto padrão
        stats_section = "📊 <i>Estatísticas em breve...</i>"
        try:
            home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
            away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)
            
            if home_is_elite and away_is_elite:
                elite_status = "Ambas as equipes são de elite!"
                stats_section = f"""
📊 <b>Estatísticas (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
"""
            elif home_is_elite:
                elite_status = f"{home_team} é uma equipe de elite!"
                stats_section = f"""
📊 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%
"""
            else:
                elite_status = f"{away_team} é uma equipe de elite!"
                stats_section = f"""
📊 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
"""
        except Exception:
            if home_is_elite and away_is_elite:
                elite_status = "Ambas as equipes são de elite!"
            elif home_is_elite:
                elite_status = f"{home_team} é uma equipe de elite!"
            else:
                elite_status = f"{away_team} é uma equipe de elite!"


        message = f"""
⭐ <b>JOGO DO DIA - EQUIPE DE ELITE</b> ⭐

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} vs {away_team}</b>

👑 {elite_status}

🕐 <b>{match_time_local.strftime('%H:%M')} (Lisboa)</b>
📅 {match_time_local.strftime('%d/%m/%Y')}

{stats_section}

🔥 Jogo de alto nível!
"""
        
        await send_telegram_message(message)
        notified_matches['elite_games'].add(notification_key)
        logger.info(f"✅ Jogo do dia notificado: {home_team} vs {away_team}")

async def process_elite_finished_match(match):
    """Processa jogos finalizados quando pelo menos uma equipe é de elite para Under 1.5"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    if league_id not in TOP_LEAGUES:
        return
    
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    
    if (home_is_elite or away_is_elite) and total_goals < 2:
        notification_key = f"under15_{fixture_id}"
        if notification_key not in notified_matches['under_15']:
            
            stats_section = "📈 <i>Estatísticas em breve...</i>"
            try:
                home_elite_stats = analyze_elite_team_stats(home_team_id, league_id)
                away_elite_stats = analyze_elite_team_stats(away_team_id, league_id)

                if home_is_elite and away_is_elite:
                    elite_status = "Ambas as equipes são de elite!"
                    stats_section = f"""
📈 <b>Estatísticas das equipes (últimas 3 temporadas):</b>

🏠 <b>{home_team}:</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%

✈️ <b>{away_team}:</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
"""
                elif home_is_elite:
                    elite_status = f"{home_team} é uma equipe de elite!"
                    stats_section = f"""
📈 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>
• Vitórias: {home_elite_stats['win_percentage']}%
• Over 1.5 gols: {home_elite_stats['over_15_percentage']}%
"""
                else:
                    elite_status = f"{away_team} é uma equipe de elite!"
                    stats_section = f"""
📈 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>
• Vitórias: {away_elite_stats['win_percentage']}%
• Over 1.5 gols: {away_elite_stats['over_15_percentage']}%
"""
            except Exception:
                if home_is_elite and away_is_elite:
                    elite_status = "Ambas as equipes são de elite!"
                elif home_is_elite:
                    elite_status = f"{home_team} é uma equipe de elite!"
                else:
                    elite_status = f"{away_team} é uma equipe de elite!"
            
            message = f"""
📉 <b>UNDER 1.5 GOLS - EQUIPE DE ELITE</b> 📉

🏆 <b>{TOP_LEAGUES[league_id]}</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>

👑 {elite_status}
📊 Total de gols: {total_goals} (Under 1.5 ✅)

{stats_section}

🎯 Oportunidade identificada com equipe de elite!

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
"""
            
            await send_telegram_message(message)
            notified_matches['under_15'].add(notification_key)


# =========================================================
# AGENDAMENTO HORÁRIO
# =========================================================

def should_execute_now(current_time):
    """Verifica se é o momento de executar o monitoramento principal (primeira execução ou a cada hora cheia)"""
    global first_run_complete
    
    if not first_run_complete:
        return True
        
    return current_time.minute < 5

async def hourly_monitoring():
    """Executa monitoramento a cada hora das 09h às 23h"""
    global first_run_complete
    logger.info("⏰ Iniciando sistema de monitoramento horário...")
    
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
            
            if should_run_monitoring() and should_execute_now(current_time):
                
                logger.info(f"🕐 Executando monitoramento às {current_hour}h (Lisboa)")
                
                await monitor_live_matches()
                await monitor_elite_teams()
                
                logger.info(f"✅ Monitoramento das {current_hour}h concluído")
                first_run_complete = True
            
            else:
                logger.info(f"😴 Fora do horário de monitoramento/janela de execução (atual: {current_hour}h)")
            
            time_to_next_hour = (current_time.replace(minute=0, second=0, microsecond=0) + 
                                 timedelta(hours=1) - current_time).total_seconds()
                                 
            sleep_duration = min(time_to_next_hour, 300) 
            
            logger.info(f"⏳ Aguardando {int(sleep_duration)} segundos até próxima verificação...")
            await asyncio.sleep(sleep_duration)
            
        except Exception as e:
            logger.error(f"❌ Erro no loop horário: {e}")
            await send_telegram_message(f"⚠️ Erro no bot: {e}")
            await asyncio.sleep(300)

# =========================================================
# RELATÓRIOS E STATUS
# =========================================================

async def daily_status():
    """Envia relatório diário às 08h"""
    while True:
        try:
            current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
            
            if current_time.hour == 8 and current_time.minute < 30:
                
                status_message = (
                    f"📊 <b>Relatório Diário do Bot</b>\n\n"
                    f"🎯 <b>Notificações enviadas ontem:</b>\n"
                    f"• Jogos 0x0 finalizados: {len(notified_matches['finished_0x0'])}\n"
                    f"• Intervalos 0x0: {len(notified_matches['halftime_0x0'])}\n"
                    f"• Jogos do dia (elite): {len(notified_matches['elite_games'])}\n"
                    f"• Under 1.5 (elite): {len(notified_matches['under_15'])}\n\n"
                    f"🏆 Monitorando {len(TOP_LEAGUES)} ligas principais\n"
                    f"👑 Acompanhando {len(EQUIPAS_DE_TITULO)} equipes de elite\n\n"
                    f"⏰ <b>Horário de funcionamento:</b>\n"
                    f"• Das 09h às 23h (Lisboa)\n"
                    f"• Verificações a cada hora\n\n"
                    f"✅ Bot funcionando perfeitamente!\n\n"
                    f"🕐 {current_time.strftime('%d/%m/%Y %H:%M')} (Lisboa)"
                )
                
                await send_telegram_message(status_message)
                
                notified_matches['finished_0x0'].clear()
                notified_matches['halftime_0x0'].clear()
                notified_matches['elite_games'].clear()
                notified_matches['under_15'].clear()
                
                await asyncio.sleep(23 * 3600)
            else:
                next_day_8am = (current_time.replace(hour=8, minute=0, second=0, microsecond=0) + 
                                timedelta(days=1))
                wait_time = (next_day_8am - current_time).total_seconds()
                
                sleep_duration = min(wait_time, 3600) 
                await asyncio.sleep(sleep_duration)
                
        except Exception as e:
            logger.error(f"Erro no relatório diário: {e}")
            await asyncio.sleep(3600)

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
                <li><strong>Próxima verificação:</strong> Na próxima hora cheia</li>
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
    app.router.add_get('/status', status_json)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Servidor web iniciado na porta {port}")

# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================

async def main():
    logger.info("🚀 Iniciando Bot de Monitoramento de Futebol...")
    logger.info("⏰ Horário de funcionamento: 09h às 23h (Lisboa)")
    logger.info("🔄 Verificações a cada hora")
    
    await run_web_server()
    
    await asyncio.gather(
        hourly_monitoring(),
        daily_status()
    )

if __name__ == '__main__':
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass 
        
    asyncio.run(main())
