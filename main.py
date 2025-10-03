import requests
import time
import asyncio
from datetime import datetime, timedelta
import os
import logging
import sys

# Importações condicionais para compatibilidade
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone
    def ZoneInfo(tz_name):
        if tz_name == "Europe/Lisbon":
            return timezone(timedelta(hours=1))
        return timezone.utc

try:
    import telegram
except ImportError:
    logging.error("❌ python-telegram-bot não encontrado. Instale com: pip install python-telegram-bot")
    sys.exit(1)

# =========================================================
# CONFIGURAÇÕES E INICIALIZAÇÃO
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Verificar variáveis de ambiente
API_KEY = os.environ.get("LIVESCORE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") 
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logger.error("❌ VARIÁVEIS DE AMBIENTE OBRIGATÓRIAS:")
    logger.error(f"LIVESCORE_API_KEY: {'✅' if API_KEY else '❌ FALTANDO'}")
    logger.error(f"TELEGRAM_BOT_TOKEN: {'✅' if TELEGRAM_BOT_TOKEN else '❌ FALTANDO'}")
    logger.error(f"TELEGRAM_CHAT_ID: {'✅' if TELEGRAM_CHAT_ID else '❌ FALTANDO'}")
    sys.exit(1)

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Controle de notificações
notified_matches = {
    'finished_0x0': set(),
    'halftime_0x0': set(),
    'elite_games': set(),
    'under_15': set(),
    'late_goals': set(),
    'teams_from_0x0': set(),
    'under_15_opportunities': set(),
    'regression_both': set(),      # NOVO
    'regression_single': set()     # NOVO
}

# =========================================================
# BASE DE DADOS GLOBAL - Campeonatos de todos os continentes (≤7% de 0x0)
# Seleção mundial das ligas com menor probabilidade de empates 0x0
# =========================================================
LEAGUE_STATS = {
    # EUROPA
    39: {  # Premier League
        "name": "Premier League", "country": "Inglaterra",
        "0x0_ht_percentage": 26, "0x0_ft_percentage": 7,
        "over_15_percentage": 75, "over_25_percentage": 57,
        "goals_after_75min": 21, "first_half_goals": 46, "second_half_goals": 53
    },
    140: {  # La Liga
        "name": "La Liga", "country": "Espanha",
        "0x0_ht_percentage": 34, "0x0_ft_percentage": 7,
        "over_15_percentage": 71, "over_25_percentage": 45,
        "goals_after_75min": 23.6, "first_half_goals": 45, "second_half_goals": 54
    },
    78: {  # Bundesliga
        "name": "Bundesliga", "country": "Alemanha",
        "0x0_ht_percentage": 25, "0x0_ft_percentage": 7,
        "over_15_percentage": 84, "over_25_percentage": 59,
        "goals_after_75min": 22, "first_half_goals": 45.6, "second_half_goals": 54.3
    },
    135: {  # Serie A
        "name": "Serie A", "country": "Itália",
        "0x0_ht_percentage": 26.6, "0x0_ft_percentage": 7,
        "over_15_percentage": 78, "over_25_percentage": 53,
        "goals_after_75min": 22, "first_half_goals": 45, "second_half_goals": 55
    },
    94: {  # Primeira Liga
        "name": "Primeira Liga", "country": "Portugal",
        "0x0_ht_percentage": 30, "0x0_ft_percentage": 7,
        "over_15_percentage": 71, "over_25_percentage": 47,
        "goals_after_75min": 23, "first_half_goals": 45, "second_half_goals": 55
    },
    61: {  # Ligue 1
        "name": "Ligue 1", "country": "França",
        "0x0_ht_percentage": 26, "0x0_ft_percentage": 7,
        "over_15_percentage": 77, "over_25_percentage": 53,
        "goals_after_75min": 22, "first_half_goals": 45, "second_half_goals": 55
    },
    88: {  # Eredivisie
        "name": "Eredivisie", "country": "Holanda",
        "0x0_ht_percentage": 24, "0x0_ft_percentage": 7,
        "over_15_percentage": 82, "over_25_percentage": 65,
        "goals_after_75min": 24, "first_half_goals": 44, "second_half_goals": 56
    },
    144: {  # Jupiler Pro League
        "name": "Jupiler Pro League", "country": "Bélgica",
        "0x0_ht_percentage": 25, "0x0_ft_percentage": 7,
        "over_15_percentage": 81, "over_25_percentage": 57,
        "goals_after_75min": 24, "first_half_goals": 43, "second_half_goals": 57
    },
    203: {  # Süper Lig
        "name": "Süper Lig", "country": "Turquia",
        "0x0_ht_percentage": 27, "0x0_ft_percentage": 7,
        "over_15_percentage": 77.6, "over_25_percentage": 55,
        "goals_after_75min": 23, "first_half_goals": 45, "second_half_goals": 55
    },
    # AMÉRICA DO SUL
    325: {  # Campeonato Brasileiro Série A
        "name": "Brasileirão", "country": "Brasil",
        "0x0_ht_percentage": 22, "0x0_ft_percentage": 6,
        "over_15_percentage": 85, "over_25_percentage": 62,
        "goals_after_75min": 26, "first_half_goals": 44, "second_half_goals": 56
    },
    128: {  # Liga Profesional Argentina
        "name": "Liga Argentina", "country": "Argentina",
        "0x0_ht_percentage": 24, "0x0_ft_percentage": 7,
        "over_15_percentage": 82, "over_25_percentage": 58,
        "goals_after_75min": 25, "first_half_goals": 43, "second_half_goals": 57
    },
    # AMÉRICA DO NORTE
    253: {  # Major League Soccer
        "name": "MLS", "country": "Estados Unidos",
        "0x0_ht_percentage": 21, "0x0_ft_percentage": 5,
        "over_15_percentage": 88, "over_25_percentage": 65,
        "goals_after_75min": 28, "first_half_goals": 42, "second_half_goals": 58
    },
    262: {  # Liga MX
        "name": "Liga MX", "country": "México",
        "0x0_ht_percentage": 23, "0x0_ft_percentage": 6,
        "over_15_percentage": 84, "over_25_percentage": 61,
        "goals_after_75min": 27, "first_half_goals": 43, "second_half_goals": 57
    },
    # ÁSIA-OCEANIA
    188: {  # J1 League
        "name": "J1 League", "country": "Japão",
        "0x0_ht_percentage": 26, "0x0_ft_percentage": 7,
        "over_15_percentage": 79, "over_25_percentage": 54,
        "goals_after_75min": 24, "first_half_goals": 46, "second_half_goals": 54
    },
    292: {  # A-League
        "name": "A-League", "country": "Austrália",
        "0x0_ht_percentage": 24, "0x0_ft_percentage": 6,
        "over_15_percentage": 83, "over_25_percentage": 59,
        "goals_after_75min": 26, "first_half_goals": 44, "second_half_goals": 56
    }
}

ELITE_TEAMS = {
    # Premier League
    "Manchester City", "Arsenal", "Liverpool", "Tottenham", "Manchester United", "Chelsea",
    # La Liga  
    "Barcelona", "Real Madrid", "Atletico Madrid", "Real Sociedad", "Athletic Club",
    # Bundesliga
    "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
    # Serie A
    "Inter", "AC Milan", "Napoli", "Juventus", "AS Roma", "Lazio", "Atalanta",
    # Primeira Liga
    "Benfica", "Porto", "Sporting CP", "Braga",
    # Ligue 1
    "Paris Saint Germain", "Monaco", "Marseille", "Lyon",
    # Eredivisie
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar",
    # Outros
    "Galatasaray", "Fenerbahce", "Besiktas", "Celtic", "Rangers"
}

# Ligas globais monitoradas (todos os continentes representados)
TOP_LEAGUES = {
    # EUROPA
    39, 140, 78, 135, 94, 61, 88, 144, 203,
    # AMÉRICA DO SUL  
    325, 128,
    # AMÉRICA DO NORTE
    253, 262,
    # ÁSIA-OCEANIA
    188, 292
}

# =========================================================
# FUNÇÕES UTILITÁRIAS
# =========================================================
async def send_telegram_message(message):
    """Envia mensagem para o Telegram"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        logger.info("✅ Mensagem enviada")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")

def make_api_request(endpoint, params=None, retries=2):
    """Faz requisição para a API com retry"""
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            logger.warning(f"API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(3)
    
    return []

def get_current_hour_lisbon():
    """Retorna hora atual em Lisboa"""
    return datetime.now(ZoneInfo("Europe/Lisbon")).hour

def should_run_monitoring():
    """Verifica se deve monitorar (09h às 23h)"""
    return 9 <= get_current_hour_lisbon() <= 23

def get_league_intelligence(league_id):
    """Retorna análise da liga"""
    if league_id not in LEAGUE_STATS:
        return None
    
    stats = LEAGUE_STATS[league_id]
    return {
        'league_name': stats['name'],
        'country': stats['country'],
        '0x0_analysis': {
            'halftime_pct': stats['0x0_ht_percentage'],
            'fulltime_pct': stats['0x0_ft_percentage'],
            'ft_odd': round(100 / stats['0x0_ft_percentage'], 2)
        },
        'over_under': {
            'over_15_pct': stats['over_15_percentage'],
            'under_15_pct': 100 - stats['over_15_percentage'],
            'under_15_odd': round(100 / (100 - stats['over_15_percentage']), 2),
            'over_25_pct': stats['over_25_percentage']
        },
        'goals_timing': {
            'after_75min_pct': stats['goals_after_75min']
        }
    }

# =========================================================
# ANÁLISE DE EQUIPES VINDAS DE 0x0 (ORIGINAL)
# =========================================================
async def get_team_recent_matches(team_id, limit=3):
    """Obtém últimos jogos de uma equipe"""
    try:
        return make_api_request("/fixtures", {
            "team": team_id, "last": limit, "status": "FT"
        })
    except Exception as e:
        logger.error(f"Erro histórico equipe {team_id}: {e}")
        return []

async def check_team_coming_from_0x0(team_id):
    """Verifica se equipe vem de 0x0"""
    recent_matches = await get_team_recent_matches(team_id)
    
    for match in recent_matches:
        home_goals = match['goals']['home'] or 0
        away_goals = match['goals']['away'] or 0
        
        if home_goals == 0 and away_goals == 0:
            opponent = (match['teams']['away']['name'] 
                       if match['teams']['home']['id'] == team_id 
                       else match['teams']['home']['name'])
            
            match_date = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            return True, {
                'opponent': opponent,
                'date': match_date.strftime('%d/%m')
            }
    
    return False, None

async def analyze_under_15_potential(match):
    """Analisa potencial Under 1.5"""
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    
    # Verificar se vêm de 0x0
    home_from_0x0, home_0x0_info = await check_team_coming_from_0x0(home_team_id)
    away_from_0x0, away_0x0_info = await check_team_coming_from_0x0(away_team_id)
    
    # Calcular média de gols recentes
    home_recent = await get_team_recent_matches(home_team_id, 5)
    away_recent = await get_team_recent_matches(away_team_id, 5)
    
    home_avg = 0
    if home_recent:
        total = sum((m['goals']['home'] or 0) + (m['goals']['away'] or 0) for m in home_recent)
        home_avg = total / len(home_recent)
    
    away_avg = 0  
    if away_recent:
        total = sum((m['goals']['home'] or 0) + (m['goals']['away'] or 0) for m in away_recent)
        away_avg = total / len(away_recent)
    
    combined_avg = (home_avg + away_avg) / 2
    
    return {
        'home_from_0x0': home_from_0x0,
        'away_from_0x0': away_from_0x0,
        'home_0x0_info': home_0x0_info,
        'away_0x0_info': away_0x0_info,
        'combined_avg_goals': round(combined_avg, 2),
        'under_15_potential': combined_avg < 1.8 or home_from_0x0 or away_from_0x0
    }

# =========================================================
# NOVA FUNCIONALIDADE: REGRESSÃO À MÉDIA
# =========================================================

async def analyze_regression_to_mean(match):
    """Analisa oportunidades de regressão à média para OVERS"""
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    
    # Analisar cada equipe individualmente
    home_regression = await check_team_regression_potential(home_team_id, home_team)
    away_regression = await check_team_regression_potential(away_team_id, away_team)
    
    return {
        'home_regression': home_regression,
        'away_regression': away_regression,
        'both_teams_potential': home_regression['has_potential'] and away_regression['has_potential'],
        'at_least_one_potential': home_regression['has_potential'] or away_regression['has_potential']
    }

async def check_team_regression_potential(team_id, team_name):
    """Verifica potencial de regressão à média de uma equipe"""
    try:
        # Obter últimos 8 jogos para análise mais robusta
        recent_matches = await get_team_recent_matches(team_id, 8)
        
        if len(recent_matches) < 5:
            return {'has_potential': False, 'reason': 'Dados insuficientes'}
        
        # Separar último jogo dos anteriores
        last_match = recent_matches[0]  # Mais recente
        previous_matches = recent_matches[1:7]  # 6 jogos anteriores
        
        # Calcular média histórica (excluindo último jogo)
        total_goals_previous = []
        for match in previous_matches:
            home_goals = match['goals']['home'] or 0
            away_goals = match['goals']['away'] or 0
            total_goals_previous.append(home_goals + away_goals)
        
        historical_avg = sum(total_goals_previous) / len(total_goals_previous)
        
        # Verificar se último jogo foi atípico (0x0 ou Under 1.5)
        last_home_goals = last_match['goals']['home'] or 0
        last_away_goals = last_match['goals']['away'] or 0
        last_total_goals = last_home_goals + last_away_goals
        
        last_was_atypical = (
            last_total_goals == 0 or  # 0x0
            last_total_goals < 2      # Under 1.5
        )
        
        # Critérios para regressão à média
        high_avg_threshold = 2.3  # Média alta de gols
        has_potential = (
            historical_avg >= high_avg_threshold and  # Alta média histórica
            last_was_atypical  # Último jogo atípico
        )
        
        # Obter detalhes do último jogo
        last_opponent = (
            last_match['teams']['away']['name'] 
            if last_match['teams']['home']['id'] == team_id 
            else last_match['teams']['home']['name']
        )
        
        last_match_date = datetime.fromisoformat(last_match['fixture']['date'].replace('Z', '+00:00'))
        
        return {
            'has_potential': has_potential,
            'historical_avg': round(historical_avg, 2),
            'last_total_goals': last_total_goals,
            'last_opponent': last_opponent,
            'last_match_date': last_match_date.strftime('%d/%m'),
            'deviation': round(historical_avg - last_total_goals, 2),
            'confidence': 'ALTA' if historical_avg >= 2.8 else 'MÉDIA' if historical_avg >= 2.5 else 'BAIXA'
        }
        
    except Exception as e:
        logger.error(f"Erro análise regressão equipe {team_id}: {e}")
        return {'has_potential': False, 'reason': f'Erro: {e}'}

# =========================================================
# MONITORAMENTO PRINCIPAL
# =========================================================
async def monitor_live_matches():
    """Monitora jogos ao vivo"""
    logger.info("🔍 Verificando jogos ao vivo...")
    
    try:
        live_matches = make_api_request("/fixtures", {"live": "all"})
        
        if not live_matches:
            logger.info("Nenhum jogo ao vivo")
            return
        
        logger.info(f"Encontrados {len(live_matches)} jogos ao vivo")
        
        for match in live_matches:
            await process_live_match(match)
            
    except Exception as e:
        logger.error(f"Erro monitoramento: {e}")

async def process_live_match(match):
    """Processa jogo ao vivo"""
    fixture_id = match['fixture']['id']
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    status = match['fixture']['status']['short']
    league_id = match['league']['id']
    
    # Apenas ligas monitoradas
    if league_id not in TOP_LEAGUES:
        return
    
    league_intel = get_league_intelligence(league_id)
    if not league_intel:
        return
    
    # **INTERVALO 0x0**
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        notification_key = f"halftime_{fixture_id}"
        if notification_key not in notified_matches['halftime_0x0']:
            
            message = f"""
🧠 <b>INTERVALO 0x0 - ANÁLISE INTELIGENTE</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Estatísticas da Liga:</b>
• 0x0 Intervalo: {league_intel['0x0_analysis']['halftime_pct']}%
• 0x0 Final: {league_intel['0x0_analysis']['fulltime_pct']}% (Odd: {league_intel['0x0_analysis']['ft_odd']})
• Under 1.5: {league_intel['over_under']['under_15_pct']}% (Odd: {league_intel['over_under']['under_15_odd']})

⚽ <b>Probabilidades 2º Tempo:</b>
• Over 1.5 total: {league_intel['over_under']['over_15_pct']}%
• Gols após 75': {league_intel['goals_timing']['after_75min_pct']}%

🎯 <b>Oportunidade identificada!</b>

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['halftime_0x0'].add(notification_key)
    
    # **FINAL 0x0**
    elif status == 'FT' and home_goals == 0 and away_goals == 0:
        notification_key = f"finished_{fixture_id}"
        if notification_key not in notified_matches['finished_0x0']:
            
            message = f"""
🎯 <b>RESULTADO 0x0 CONFIRMADO!</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Análise:</b>
• Taxa 0x0 da liga: {league_intel['0x0_analysis']['fulltime_pct']}%
• Odd esperada: ~{league_intel['0x0_analysis']['ft_odd']}

✅ <b>Resultado raro confirmado!</b>
Liga com apenas {league_intel['0x0_analysis']['fulltime_pct']}% de jogos 0x0.

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(notification_key)

async def monitor_teams_from_0x0():
    """Monitora equipes vindas de 0x0"""
    logger.info("🔍 Verificando equipes vindas de 0x0...")
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        upcoming_matches = make_api_request("/fixtures", {
            "from": today, "to": tomorrow, "status": "NS"
        })
        
        for match in upcoming_matches[:15]:  # Limitar para economizar requests
            await process_upcoming_match(match)
            
    except Exception as e:
        logger.error(f"Erro monitoramento 0x0: {e}")

async def process_upcoming_match(match):
    """Processa jogo futuro"""
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    if league_id not in TOP_LEAGUES:
        return
    
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    
    league_intel = get_league_intelligence(league_id)
    if not league_intel:
        return
    
    # Análise Under 1.5
    under15_analysis = await analyze_under_15_potential(match)
    
    # **EQUIPES VINDAS DE 0x0**
    if under15_analysis['home_from_0x0'] or under15_analysis['away_from_0x0']:
        notification_key = f"team_0x0_{fixture_id}"
        if notification_key not in notified_matches['teams_from_0x0']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            teams_info = ""
            if under15_analysis['home_from_0x0']:
                info = under15_analysis['home_0x0_info']
                teams_info += f"🏠 <b>{home_team}</b> vem de 0x0 vs {info['opponent']} ({info['date']})\n"
            
            if under15_analysis['away_from_0x0']:
                info = under15_analysis['away_0x0_info']
                teams_info += f"✈️ <b>{away_team}</b> vem de 0x0 vs {info['opponent']} ({info['date']})\n"
            
            message = f"""
🚨 <b>ALERTA - EQUIPE(S) VINDAS DE 0x0!</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Análise da Liga:</b>
• Under 1.5: {league_intel['over_under']['under_15_pct']}% (Odd: {league_intel['over_under']['under_15_odd']})
• 0x0 Final: {league_intel['0x0_analysis']['fulltime_pct']}% (Odd: {league_intel['0x0_analysis']['ft_odd']})
• Média gols recente: {under15_analysis['combined_avg_goals']}

💡 <b>Insight:</b> Padrão defensivo recente identificado!

🎯 <b>Sugestões:</b>
• Under 1.5 gols
• Under 2.5 gols  
• 0x0 (valor especial)

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>

⚠️ <b>JOGO PARA MONITORAR!</b>
            """
            
            await send_telegram_message(message)
            notified_matches['teams_from_0x0'].add(notification_key)
    
    # **OPORTUNIDADE UNDER 1.5**
    elif under15_analysis['under_15_potential']:
        notification_key = f"under15_{fixture_id}"
        if notification_key not in notified_matches['under_15_opportunities']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            message = f"""
📉 <b>OPORTUNIDADE UNDER 1.5 DETECTADA!</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

📊 <b>Análise:</b>
• Under 1.5 da liga: {league_intel['over_under']['under_15_pct']}%
• Odd esperada: ~{league_intel['over_under']['under_15_odd']}
• Média gols recente: {under15_analysis['combined_avg_goals']}

🔍 <b>Fatores:</b>
• Baixa média de gols das equipes
• Liga favorável para Under 1.5

🎯 <b>Recomendação:</b> Under 1.5 gols

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
            """
            
            await send_telegram_message(message)
            notified_matches['under_15_opportunities'].add(notification_key)

# =========================================================
# MONITORAMENTO DE REGRESSÃO À MÉDIA
# =========================================================

async def monitor_regression_opportunities():
    """Monitora oportunidades de regressão à média"""
    if not should_run_monitoring():
        return
        
    logger.info("📈 Verificando oportunidades de regressão à média...")
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        upcoming_matches = make_api_request("/fixtures", {
            "from": today, "to": tomorrow, "status": "NS"
        })
        
        for match in upcoming_matches[:20]:  # Limitar requests
            await process_regression_analysis(match)
            
    except Exception as e:
        logger.error(f"Erro monitoramento regressão: {e}")

async def process_regression_analysis(match):
    """Processa análise de regressão à média"""
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    # Apenas ligas monitoradas
    if league_id not in TOP_LEAGUES:
        return
    
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    
    league_intel = get_league_intelligence(league_id)
    if not league_intel:
        return
    
    # Análise de regressão à média
    regression_analysis = await analyze_regression_to_mean(match)
    
    # **AMBAS AS EQUIPES COM POTENCIAL (OPORTUNIDADE MÁXIMA)**
    if regression_analysis['both_teams_potential']:
        notification_key = f"regression_both_{fixture_id}"
        if notification_key not in notified_matches['regression_both']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            home_data = regression_analysis['home_regression']
            away_data = regression_analysis['away_regression']
            
            message = f"""
🚀 <b>REGRESSÃO À MÉDIA - OPORTUNIDADE MÁXIMA!</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

📈 <b>AMBAS AS EQUIPES COM POTENCIAL:</b>

🏠 <b>{home_team}:</b>
• Média histórica: {home_data['historical_avg']} gols/jogo
• Último jogo: {home_data['last_total_goals']} gols vs {home_data['last_opponent']} ({home_data['last_match_date']})
• Desvio: -{home_data['deviation']} gols (ATÍPICO!)
• Confiança: {home_data['confidence']}

✈️ <b>{away_team}:</b>
• Média histórica: {away_data['historical_avg']} gols/jogo  
• Último jogo: {away_data['last_total_goals']} gols vs {away_data['last_opponent']} ({away_data['last_match_date']})
• Desvio: -{away_data['deviation']} gols (ATÍPICO!)
• Confiança: {away_data['confidence']}

📊 <b>Estatísticas da Liga:</b>
• Over 1.5: {league_intel['over_under']['over_15_pct']}%
• Over 2.5: {league_intel['over_under']['over_25_pct']}%

🎯 <b>RECOMENDAÇÕES FORTES:</b>
• 🔥 Over 2.5 gols (PRIORIDADE)
• 🔥 Over 1.5 gols  
• 🔥 Ambas marcam
• ⚽ Total de gols: Acima da média

💡 <b>Conceito:</b> Regressão à média - equipes tendem a voltar ao padrão histórico após jogos atípicos!

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>

⭐ <b>JOGO PRIORITÁRIO PARA OVERS!</b>
            """
            
            await send_telegram_message(message)
            notified_matches['regression_both'].add(notification_key)
    
    # **UMA EQUIPE COM POTENCIAL**
    elif regression_analysis['at_least_one_potential']:
        notification_key = f"regression_single_{fixture_id}"
        if notification_key not in notified_matches['regression_single']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            # Identificar qual equipe tem potencial
            if regression_analysis['home_regression']['has_potential']:
                team_data = regression_analysis['home_regression']
                team_name = home_team
                team_icon = "🏠"
            else:
                team_data = regression_analysis['away_regression']
                team_name = away_team
                team_icon = "✈️"
            
            message = f"""
📈 <b>REGRESSÃO À MÉDIA DETECTADA!</b>

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

{team_icon} <b>{team_name} - POTENCIAL IDENTIFICADO:</b>
• Média histórica: {team_data['historical_avg']} gols/jogo
• Último jogo: {team_data['last_total_goals']} gols vs {team_data['last_opponent']} ({team_data['last_match_date']})
• Desvio: -{team_data['deviation']} gols (ABAIXO DA MÉDIA!)
• Confiança: {team_data['confidence']}

📊 <b>Análise da Liga:</b>
• Over 1.5: {league_intel['over_under']['over_15_pct']}%
• Over 2.5: {league_intel['over_under']['over_25_pct']}%

🎯 <b>Recomendações:</b>
• Over 1.5 gols
• Over 2.5 gols (se confiança ALTA)
• Considerar ambas marcam

💡 <b>Insight:</b> Equipe com histórico ofensivo teve jogo defensivo atípico - tendência de retorno à média!

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
            """
            
            await send_telegram_message(message)
            notified_matches['regression_single'].add(notification_key)

# =========================================================
# LOOP PRINCIPAL
# =========================================================
async def main_loop():
    """Loop principal do bot"""
    logger.info("🚀 Bot Inteligente de Futebol v2.0 Iniciado!")
    
    # Testar conexão Telegram
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    # Mensagem de inicialização
    await send_telegram_message(
        "🚀 <b>Bot Inteligente v2.0 com Regressão à Média!</b>\n\n"
        "🧠 <b>Recursos:</b>\n"
        "• Monitoramento ao vivo\n"
        "• 🆕 Detecção equipes vindas de 0x0\n"
        "• 🆕 Oportunidades Under 1.5\n"  
        "• 🆕 Taxa 0x0 atualizada para 7%\n"
        "• 🔥 REGRESSÃO À MÉDIA para OVERS\n\n"
        "⏰ Ativo: 09h-23h (Lisboa)\n"
        f"🌍 Cobertura global: {len(TOP_LEAGUES)} ligas de todos os continentes!\n"
        f"🎯 Critério: Apenas ligas com ≤7% de empates 0x0"
    )
    
    while True:
        try:
            current_hour = get_current_hour_lisbon()
            
            if should_run_monitoring():
                logger.info(f"🧠 Monitoramento às {current_hour}h")
                
                # Executar monitoramentos
                await monitor_live_matches()
                await monitor_teams_from_0x0()
                await monitor_regression_opportunities()  # NOVO
                
                logger.info("✅ Ciclo concluído")
                await asyncio.sleep(1800)  # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro detectado: {e}")
            await asyncio.sleep(600)  # 10 minutos

# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Inteligente de Futebol...")
    logger.info(f"📊 {len(LEAGUE_STATS)} ligas globais configuradas (≤7% de 0x0)")
    logger.info(f"👑 {len(ELITE_TEAMS)} equipes de elite")
    logger.info("⚙️ Todas as funcionalidades ativas")
    logger.info("🔥 NOVA: Regressão à média para OVERS")
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
