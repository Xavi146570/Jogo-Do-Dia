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
    'under_15': set(),
    'late_goals': set(),
    'period_alerts': set(),
    'over_under_alerts': set()
}

# =========================================================
# BASE DE DADOS ESTATÍSTICAS INTELIGENTES
# =========================================================

LEAGUE_STATS = {
    # Premier League (ID: 39)
    39: {
        "name": "Premier League",
        "country": "Inglaterra",
        "0x0_ht_percentage": 26,
        "0x0_ft_percentage": 6,
        "over_05_percentage": 93,
        "over_15_percentage": 75,
        "over_25_percentage": 57,
        "goals_after_75min": 21,
        "first_half_goals": 46,
        "second_half_goals": 53,
        "avg_odd_elite": 1.62
    },
    
    # La Liga (ID: 140)
    140: {
        "name": "La Liga",
        "country": "Espanha",
        "0x0_ht_percentage": 34,
        "0x0_ft_percentage": 8.6,
        "over_05_percentage": 91,
        "over_15_percentage": 71,
        "over_25_percentage": 45,
        "goals_after_75min": 23.6,
        "first_half_goals": 45,
        "second_half_goals": 54,
        "avg_odd_elite": 1.59
    },
    
    # Bundesliga (ID: 78)
    78: {
        "name": "Bundesliga",
        "country": "Alemanha",
        "0x0_ht_percentage": 25,
        "0x0_ft_percentage": 5.6,
        "over_05_percentage": 94.3,
        "over_15_percentage": 84,
        "over_25_percentage": 59,
        "goals_after_75min": 22,
        "first_half_goals": 45.6,
        "second_half_goals": 54.3,
        "avg_odd_elite": 2.02,
        "goals_by_15min": {
            "0-15": 14,
            "15-30": 14,
            "30-45": 18,
            "45-60": 14,
            "60-75": 17,
            "75-90": 20
        }
    },
    
    # Serie A (ID: 135)
    135: {
        "name": "Serie A",
        "country": "Itália",
        "0x0_ht_percentage": 26.6,
        "0x0_ft_percentage": 5.33,
        "over_05_percentage": 94.6,
        "over_15_percentage": 78,
        "over_25_percentage": 53,
        "goals_after_75min": 22,
        "first_half_goals": 45,
        "second_half_goals": 55,
        "avg_odd_elite": 1.53
    },
    
    # Primeira Liga (ID: 94)
    94: {
        "name": "Primeira Liga",
        "country": "Portugal",
        "0x0_ht_percentage": 30,
        "0x0_ft_percentage": 5,
        "over_05_percentage": 92,
        "over_15_percentage": 71,
        "over_25_percentage": 47,
        "goals_after_75min": 23,
        "first_half_goals": 45,
        "second_half_goals": 55,
        "goals_by_15min": {
            "0-15": 11,
            "15-30": 12,
            "30-45": 19,
            "45-60": 15,
            "60-75": 14,
            "75-90": 18
        }
    },
    
    # Ligue 1 (ID: 61)
    61: {
        "name": "Ligue 1",
        "country": "França",
        "0x0_ht_percentage": 26,
        "0x0_ft_percentage": 6.6,
        "over_05_percentage": 93.3,
        "over_15_percentage": 77,
        "over_25_percentage": 53,
        "goals_after_75min": 22,
        "first_half_goals": 45,
        "second_half_goals": 55
    },
    
    # Eredivisie (ID: 88)
    88: {
        "name": "Eredivisie",
        "country": "Holanda",
        "0x0_ht_percentage": 24,
        "0x0_ft_percentage": 4.5,
        "over_05_percentage": 95,
        "over_15_percentage": 82,
        "over_25_percentage": 65,
        "goals_after_75min": 24,
        "first_half_goals": 44,
        "second_half_goals": 56
    },
    
    # Jupiler Pro League (ID: 144)
    144: {
        "name": "Jupiler Pro League",
        "country": "Bélgica",
        "0x0_ht_percentage": 25,
        "0x0_ft_percentage": 5.3,
        "over_05_percentage": 95,
        "over_15_percentage": 81,
        "over_25_percentage": 57,
        "goals_after_75min": 24,
        "first_half_goals": 43,
        "second_half_goals": 57
    },
    
    # Süper Lig (ID: 203)
    203: {
        "name": "Süper Lig",
        "country": "Turquia",
        "0x0_ht_percentage": 27,
        "0x0_ft_percentage": 6,
        "over_05_percentage": 93,
        "over_15_percentage": 77.6,
        "over_25_percentage": 55,
        "goals_after_75min": 23,
        "first_half_goals": 45,
        "second_half_goals": 55
    }
}

ELITE_TEAM_STATS = {
    # Premier League
    "Manchester City": {"win_rate": 73, "avg_odd": 1.35, "league": "Premier League"},
    "Arsenal": {"win_rate": 57, "avg_odd": 1.75, "league": "Premier League"},
    "Liverpool": {"win_rate": 67, "avg_odd": 1.49, "league": "Premier League"},
    "Tottenham": {"win_rate": 58, "avg_odd": 1.72, "league": "Premier League"},
    "Manchester United": {"win_rate": 56, "avg_odd": 1.78, "league": "Premier League"},
    "Chelsea": {"win_rate": 55, "avg_odd": 1.80, "league": "Premier League"},
    
    # La Liga
    "Barcelona": {"win_rate": 73, "avg_odd": 1.37, "league": "La Liga"},
    "Real Madrid": {"win_rate": 75, "avg_odd": 1.33, "league": "La Liga"},
    "Atletico Madrid": {"win_rate": 70, "avg_odd": 1.43, "league": "La Liga"},
    "Real Sociedad": {"win_rate": 55, "avg_odd": 1.82, "league": "La Liga"},
    "Athletic Club": {"win_rate": 52, "avg_odd": 1.92, "league": "La Liga"},
    
    # Bundesliga
    "Bayern Munich": {"win_rate": 69, "avg_odd": 1.45, "league": "Bundesliga"},
    "Borussia Dortmund": {"win_rate": 64, "avg_odd": 1.56, "league": "Bundesliga"},
    "RB Leipzig": {"win_rate": 56, "avg_odd": 1.78, "league": "Bundesliga"},
    "Bayer Leverkusen": {"win_rate": 47, "avg_odd": 2.13, "league": "Bundesliga"},
    "Eintracht Frankfurt": {"win_rate": 45, "avg_odd": 2.22, "league": "Bundesliga"},
    
    # Serie A
    "Inter": {"win_rate": 67, "avg_odd": 1.49, "league": "Serie A"},
    "AC Milan": {"win_rate": 61, "avg_odd": 1.63, "league": "Serie A"},
    "Napoli": {"win_rate": 66, "avg_odd": 1.51, "league": "Serie A"},
    "Juventus": {"win_rate": 57, "avg_odd": 1.75, "league": "Serie A"},
    "AS Roma": {"win_rate": 54, "avg_odd": 1.85, "league": "Serie A"},
    "Lazio": {"win_rate": 53, "avg_odd": 1.89, "league": "Serie A"},
    "Atalanta": {"win_rate": 58, "avg_odd": 1.72, "league": "Serie A"},
    
    # Primeira Liga
    "Benfica": {"win_rate": 72, "avg_odd": 1.37, "league": "Primeira Liga"},
    "Porto": {"win_rate": 78, "avg_odd": 1.27, "league": "Primeira Liga"},
    "Sporting CP": {"win_rate": 74, "avg_odd": 1.34, "league": "Primeira Liga"},
    "Braga": {"win_rate": 62, "avg_odd": 1.61, "league": "Primeira Liga"},
    "Vitoria de Guimaraes": {"win_rate": 48, "avg_odd": 2.08, "league": "Primeira Liga"},
    
    # Ligue 1
    "Paris Saint Germain": {"win_rate": 79, "avg_odd": 1.26, "league": "Ligue 1"},
    "Monaco": {"win_rate": 63, "avg_odd": 1.58, "league": "Ligue 1"},
    "Marseille": {"win_rate": 59, "avg_odd": 1.69, "league": "Ligue 1"},
    "Lyon": {"win_rate": 55, "avg_odd": 1.82, "league": "Ligue 1"},
    "Nice": {"win_rate": 50, "avg_odd": 2.00, "league": "Ligue 1"},
    "Lille": {"win_rate": 54, "avg_odd": 1.85, "league": "Ligue 1"},
    
    # Eredivisie
    "Ajax": {"win_rate": 65, "avg_odd": 1.54, "league": "Eredivisie"},
    "PSV Eindhoven": {"win_rate": 70, "avg_odd": 1.43, "league": "Eredivisie"},
    "Feyenoord": {"win_rate": 62, "avg_odd": 1.61, "league": "Eredivisie"},
    "AZ Alkmaar": {"win_rate": 55, "avg_odd": 1.82, "league": "Eredivisie"},
    "FC Twente": {"win_rate": 52, "avg_odd": 1.92, "league": "Eredivisie"},
    
    # Outros
    "Galatasaray": {"win_rate": 60, "avg_odd": 1.66, "league": "Süper Lig"},
    "Fenerbahce": {"win_rate": 69, "avg_odd": 1.45, "league": "Süper Lig"},
    "Besiktas": {"win_rate": 64, "avg_odd": 1.56, "league": "Süper Lig"},
    "Celtic": {"win_rate": 75, "avg_odd": 1.33, "league": "Scottish Premiership"},
    "Rangers": {"win_rate": 68, "avg_odd": 1.47, "league": "Scottish Premiership"}
}

# Lista expandida de equipes de elite
EQUIPAS_DE_TITULO = list(ELITE_TEAM_STATS.keys())

# Top campeonatos para monitoramento
TOP_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    78: "Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
    94: "Primeira Liga",
    88: "Eredivisie",
    144: "Jupiler Pro League",
    203: "Süper Lig",
    235: "Premier League"
}

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
                time.sleep(2 ** attempt)
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
# FUNÇÕES DE INTELIGÊNCIA AVANÇADA
# =========================================================

def get_league_intelligence(league_id):
    """Retorna análise inteligente baseada nas estatísticas reais"""
    if league_id not in LEAGUE_STATS:
        return None
    
    stats = LEAGUE_STATS[league_id]
    
    analysis = {
        'league_name': stats['name'],
        'country': stats['country'],
        '0x0_analysis': {
            'halftime_pct': stats['0x0_ht_percentage'],
            'fulltime_pct': stats['0x0_ft_percentage'],
            'ht_odd': round(100 / stats['0x0_ht_percentage'], 2),
            'ft_odd': round(100 / stats['0x0_ft_percentage'], 2),
            'recommendation': 'EXCELENTE' if stats['0x0_ft_percentage'] < 6 else 'BOA' if stats['0x0_ft_percentage'] < 8 else 'REGULAR'
        },
        'goals_timing': {
            'after_75min_pct': stats['goals_after_75min'],
            'after_75min_odd': round(100 / stats['goals_after_75min'], 2),
            'first_half_pct': stats['first_half_goals'],
            'second_half_pct': stats['second_half_goals']
        },
        'over_under': {
            'over_05_pct': stats.get('over_05_percentage', 0),
            'over_15_pct': stats['over_15_percentage'],
            'over_25_pct': stats['over_25_percentage'],
            'over_15_odd': round(100 / stats['over_15_percentage'], 2),
            'under_15_pct': 100 - stats['over_15_percentage'],
            'under_15_odd': round(100 / (100 - stats['over_15_percentage']), 2)
        },
        'value_opportunities': []
    }
    
    # Identificar oportunidades de valor
    if stats['0x0_ft_percentage'] < 7:
        analysis['value_opportunities'].append(f"✅ 0x0 Final ({stats['0x0_ft_percentage']}% - Odd: {analysis['0x0_analysis']['ft_odd']})")
    
    if stats['over_15_percentage'] > 75:
        analysis['value_opportunities'].append(f"✅ Over 1.5 ({stats['over_15_percentage']}% - Odd: {analysis['over_under']['over_15_odd']})")
    
    if stats['goals_after_75min'] > 22:
        analysis['value_opportunities'].append(f"✅ Gol após 75' ({stats['goals_after_75min']}% - Odd: {analysis['goals_timing']['after_75min_odd']})")
    
    if stats.get('over_25_percentage', 0) < 50:
        analysis['value_opportunities'].append(f"✅ Under 2.5 ({100 - stats.get('over_25_percentage', 0)}%)")
    
    return analysis

def analyze_15min_periods(league_id, current_minute=None):
    """Analisa probabilidades por períodos de 15 minutos"""
    if league_id not in LEAGUE_STATS or 'goals_by_15min' not in LEAGUE_STATS[league_id]:
        return None
    
    periods = LEAGUE_STATS[league_id]['goals_by_15min']
    
    analysis = {
        'league': LEAGUE_STATS[league_id]['name'],
        'periods': periods,
        'best_period': max(periods.items(), key=lambda x: x[1]),
        'worst_period': min(periods.items(), key=lambda x: x[1]),
        'current_period': None
    }
    
    if current_minute:
        if 0 <= current_minute <= 15:
            analysis['current_period'] = {"period": "0-15", "probability": periods["0-15"], "status": "ATIVO"}
        elif 15 < current_minute <= 30:
            analysis['current_period'] = {"period": "15-30", "probability": periods["15-30"], "status": "ATIVO"}
        elif 30 < current_minute <= 45:
            analysis['current_period'] = {"period": "30-45", "probability": periods["30-45"], "status": "ATIVO"}
        elif 45 < current_minute <= 60:
            analysis['current_period'] = {"period": "45-60", "probability": periods["45-60"], "status": "ATIVO"}
        elif 60 < current_minute <= 75:
            analysis['current_period'] = {"period": "60-75", "probability": periods["60-75"], "status": "ATIVO"}
        elif 75 < current_minute <= 90:
            analysis['current_period'] = {"period": "75-90", "probability": periods["75-90"], "status": "ATIVO"}
    
    return analysis

def get_team_intelligence(team_name):
    """Retorna dados de inteligência da equipe"""
    if team_name in ELITE_TEAM_STATS:
        team_data = ELITE_TEAM_STATS[team_name]
        return {
            'team_name': team_name,
            'win_rate': team_data['win_rate'],
            'avg_odd': team_data['avg_odd'],
            'league': team_data['league'],
            'classification': 'ELITE' if team_data['win_rate'] > 65 else 'BOA' if team_data['win_rate'] > 55 else 'REGULAR'
        }
    return None

def calculate_match_intelligence(home_team, away_team, league_id):
    """Calcula inteligência completa do confronto"""
    league_intel = get_league_intelligence(league_id)
    home_intel = get_team_intelligence(home_team)
    away_intel = get_team_intelligence(away_team)
    
    if not league_intel:
        return None
    
    match_analysis = {
        'league': league_intel,
        'home_team': home_intel,
        'away_team': away_intel,
        'match_type': 'UNKNOWN',
        'recommendations': []
    }
    
    # Classificar tipo de jogo
    if home_intel and away_intel:
        if home_intel['win_rate'] > 65 and away_intel['win_rate'] > 65:
            match_analysis['match_type'] = 'ELITE vs ELITE'
        elif home_intel['win_rate'] > 65 or away_intel['win_rate'] > 65:
            match_analysis['match_type'] = 'ELITE vs NORMAL'
        else:
            match_analysis['match_type'] = 'JOGO NORMAL'
    
    # Gerar recomendações
    if league_intel['0x0_analysis']['recommendation'] == 'EXCELENTE':
        match_analysis['recommendations'].append("🎯 Liga favorável para 0x0")
    
    if league_intel['over_under']['over_15_pct'] > 75:
        match_analysis['recommendations'].append("⚽ Alta probabilidade Over 1.5")
    
    if league_intel['goals_timing']['after_75min_pct'] > 22:
        match_analysis['recommendations'].append("⏰ Aguardar gols tardios (75'+)")
    
    return match_analysis

# =========================================================
# ANÁLISE HISTÓRICA APRIMORADA
# =========================================================

def analyze_team_0x0_history(team_id, league_id):
    """Analisa histórico de 0x0 de uma equipe com inteligência"""
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
    
    # Usar inteligência da liga para comparação
    league_intel = get_league_intelligence(league_id)
    league_avg = league_intel['0x0_analysis']['fulltime_pct'] if league_intel else 8
    
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10,
        'vs_league_avg': round(percentage - league_avg, 2),
        'classification': 'BAIXO' if percentage < league_avg else 'MÉDIO' if percentage < league_avg + 2 else 'ALTO'
    }
    
    cache_team_stats[cache_key] = {
        'data': result,
        'timestamp': datetime.now().timestamp()
    }
    
    return result

def analyze_league_0x0_history(league_id):
    """Analisa histórico de 0x0 de uma liga com dados reais"""
    # Usar dados reais das estatísticas
    league_intel = get_league_intelligence(league_id)
    if not league_intel:
        return {'qualifies': False, 'percentage': 10}
    
    return {
        'percentage': league_intel['0x0_analysis']['fulltime_pct'],
        'qualifies': league_intel['0x0_analysis']['fulltime_pct'] < 8,
        'recommendation': league_intel['0x0_analysis']['recommendation'],
        'halftime_pct': league_intel['0x0_analysis']['halftime_pct']
    }

def analyze_elite_team_stats(team_id, league_id):
    """Analisa estatísticas de elite com dados reais"""
    cache_key = f"elite_{team_id}_{league_id}"
    
    if cache_key in cache_elite_stats:
        cached_data = cache_elite_stats[cache_key]
        if datetime.now().timestamp() - cached_data['timestamp'] < 7200:
            return cached_data['data']
    
    # Tentar obter dados da API
    current_year = datetime.now().year
    seasons = [current_year, current_year - 1]
    
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
            logger.warning(f"Erro ao analisar estatísticas de elite para equipe {team_id}: {e}")
    
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
# MONITORAMENTO INTELIGENTE AO VIVO
# =========================================================

async def monitor_live_matches():
    """Monitora jogos ao vivo com inteligência avançada"""
    if not should_run_monitoring():
        logger.info(f"Fora do horário de monitoramento (atual: {get_current_hour_lisbon()}h)")
        return
        
    logger.info("🧠 Verificando jogos ao vivo com inteligência...")
    
    try:
        live_matches = make_api_request("/fixtures", {"live": "all"})
        
        if not live_matches:
            logger.info("Nenhum jogo ao vivo no momento")
            return
            
        logger.info(f"Encontrados {len(live_matches)} jogos ao vivo")
        
        for match in live_matches:
            await process_intelligent_live_match(match)
            
    except Exception as e:
        logger.error(f"Erro no monitoramento ao vivo: {e}")

async def process_intelligent_live_match(match):
    """Processa jogo ao vivo com análise inteligente"""
    fixture_id = match['fixture']['id']
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    status = match['fixture']['status']['short']
    league_id = match['league']['id']
    current_minute = match['fixture']['status']['elapsed'] or 0
    
    # Verificar se é liga monitorada
    if league_id not in TOP_LEAGUES:
        return
    
    # Obter inteligência completa do confronto
    match_intel = calculate_match_intelligence(home_team, away_team, league_id)
    if not match_intel:
        return
    
    league_analysis = match_intel['league']
    
    # **1. ANÁLISE DE INTERVALO 0x0 INTELIGENTE**
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        notification_key = f"intelligent_halftime_{fixture_id}"
        if notification_key not in notified_matches['halftime_0x0']:
            
            message = f"""
🧠 <b>ANÁLISE INTELIGENTE - INTERVALO 0x0</b> 🧠

🏆 <b>{league_analysis['league_name']} ({league_analysis['country']})</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Inteligência da Liga:</b>
• 0x0 Intervalo: {league_analysis['0x0_analysis']['halftime_pct']}% (Odd: {league_analysis['0x0_analysis']['ht_odd']})
• 0x0 Final: {league_analysis['0x0_analysis']['fulltime_pct']}% (Odd: {league_analysis['0x0_analysis']['ft_odd']})
• Recomendação: {league_analysis['0x0_analysis']['recommendation']}

⚽ <b>Probabilidades 2º Tempo:</b>
• Gols 2º tempo: {league_analysis['goals_timing']['second_half_pct']}%
• Over 1.5 total: {league_analysis['over_under']['over_15_pct']}%
• Gols após 75': {league_analysis['goals_timing']['after_75min_pct']}%

🎯 <b>Oportunidades de Valor:</b>
{chr(10).join(['• ' + opp for opp in league_analysis['value_opportunities']]) if league_analysis['value_opportunities'] else '• Nenhuma oportunidade clara identificada'}

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['halftime_0x0'].add(notification_key)
    
    # **2. ANÁLISE DE JOGO FINALIZADO 0x0**
    elif status == 'FT' and home_goals == 0 and away_goals == 0:
        notification_key = f"intelligent_finished_{fixture_id}"
        if notification_key not in notified_matches['finished_0x0']:
            
            # Análise histórica das equipes
            home_analysis = analyze_team_0x0_history(match['teams']['home']['id'], league_id)
            away_analysis = analyze_team_0x0_history(match['teams']['away']['id'], league_id)
            
            message = f"""
🎯 <b>RESULTADO 0x0 CONFIRMADO - ANÁLISE COMPLETA</b> 🎯

🏆 <b>{league_analysis['league_name']} ({league_analysis['country']})</b>
⚽ <b>{home_team} 0 x 0 {away_team}</b>

📊 <b>Análise da Liga:</b>
• Média de 0x0: {league_analysis['0x0_analysis']['fulltime_pct']}% (Odd: {league_analysis['0x0_analysis']['ft_odd']})
• Status: {league_analysis['0x0_analysis']['recommendation']}

📈 <b>Análise das Equipes (3 temporadas):</b>
• {home_team}: {home_analysis['percentage']}% 0x0 ({home_analysis['classification']} vs liga)
• {away_team}: {away_analysis['percentage']}% 0x0 ({away_analysis['classification']} vs liga)

✅ <b>Oportunidade Confirmada!</b>
Liga com baixa % de 0x0 e resultado raro alcançado!

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(notification_key)
    
    # **3. ANÁLISE DE PERÍODOS DE 15 MINUTOS**
    await monitor_15min_periods_live(match, match_intel)
    
    # **4. ALERTAS DE GOLS TARDIOS**
    await monitor_late_goals_live(match, match_intel)

async def monitor_15min_periods_live(match, match_intel):
    """Monitora períodos de 15 minutos em tempo real"""
    current_minute = match['fixture']['status']['elapsed'] or 0
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    period_analysis = analyze_15min_periods(league_id, current_minute)
    if not period_analysis or not period_analysis['current_period']:
        return
    
    current_period = period_analysis['current_period']
    
    # Alertar apenas se estiver em período favorável (>17%)
    if current_period['probability'] >= 17:
        notification_key = f"period_alert_{fixture_id}_{current_period['period']}"
        if notification_key not in notified_matches['period_alerts']:
            
            message = f"""
⏱️ <b>PERÍODO FAVORÁVEL PARA GOLS</b> ⏱️

🏆 <b>{period_analysis['league']}</b>
⚽ <b>{match['teams']['home']['name']} vs {match['teams']['away']['name']}</b>

📊 <b>Período Atual ({current_period['period']} min):</b>
• Probabilidade: {current_period['probability']}% 
• Status: {current_period['status']}
• Odd estimada: ~{round(100/current_period['probability'], 2)}

🎯 <b>Contexto dos Períodos:</b>
• Melhor período: {period_analysis['best_period'][0]} ({period_analysis['best_period'][1]}%)
• Pior período: {period_analysis['worst_period'][0]} ({period_analysis['worst_period'][1]}%)

⏰ <b>MOMENTO FAVORÁVEL!</b>

🕐 Minuto {current_minute}' - <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M')}</i>
            """
            
            await send_telegram_message(message)
            notified_matches['period_alerts'].add(notification_key)

async def monitor_late_goals_live(match, match_intel):
    """Monitora oportunidades de gols tardios"""
    current_minute = match['fixture']['status']['elapsed'] or 0
    fixture_id = match['fixture']['id']
    
    # Alertar quando chegar aos 75 minutos em ligas favoráveis
    if current_minute >= 75 and current_minute <= 77:  # Janela de 2 minutos
        league_analysis = match_intel['league']
        
        if league_analysis['goals_timing']['after_75min_pct'] >= 22:
            notification_key = f"late_goals_{fixture_id}"
            if notification_key not in notified_matches['late_goals']:
                
                home_goals = match['goals']['home'] or 0
                away_goals = match['goals']['away'] or 0
                total_goals = home_goals + away_goals
                
                message = f"""
🚨 <b>ALERTA - ZONA DE GOLS TARDIOS</b> 🚨

⏱️ <b>Minuto {current_minute}'</b>
🏆 <b>{league_analysis['league_name']}</b>
⚽ <b>{match['teams']['home']['name']} {home_goals} x {away_goals} {match['teams']['away']['name']}</b>

📊 <b>Estatística da Liga:</b>
• Gols após 75': {league_analysis['goals_timing']['after_75min_pct']}%
• Odd estimada: ~{league_analysis['goals_timing']['after_75min_odd']}
• Total atual: {total_goals} gols

⚡ <b>MOMENTO CRÍTICO!</b>
Estatisticamente, esta é a zona de maior probabilidade para gols tardios nesta liga.

🎯 <b>Atenção para:</b>
• Próximo gol (qualquer equipe)
• Over 1.5 se ainda 0x0 ou 1x0
• Over 2.5 se já tiver 2 gols

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M')}</i>
                """
                
                await send_telegram_message(message)
                notified_matches['late_goals'].add(notification_key)

# =========================================================
# MONITORAMENTO DE EQUIPES DE ELITE APRIMORADO
# =========================================================

async def monitor_elite_teams():
    """Monitora equipes de elite com inteligência avançada"""
    if not should_run_monitoring():
        return
        
    logger.info("👑 Verificando jogos de elite com inteligência...")
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        upcoming_matches = make_api_request("/fixtures", {
            "from": today,
            "to": tomorrow,
            "status": "NS"
        })
        
        finished_matches = make_api_request("/fixtures", {
            "date": today,
            "status": "FT"
        })
        
        if upcoming_matches:
            for match in upcoming_matches:
                await process_elite_upcoming_intelligent(match)
        
        if finished_matches:
            for match in finished_matches:
                await process_elite_finished_intelligent(match)
            
    except Exception as e:
        logger.error(f"Erro no monitoramento de elite: {e}")

async def process_elite_upcoming_intelligent(match):
    """Processa jogos futuros de elite com inteligência"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    if league_id not in TOP_LEAGUES:
        return
    
    # Obter inteligência completa
    match_intel = calculate_match_intelligence(home_team, away_team, league_id)
    if not match_intel:
        return
    
    home_intel = match_intel['home_team']
    away_intel = match_intel['away_team']
    
    # Só notificar se pelo menos uma equipe for de elite
    if not (home_intel or away_intel):
        return
    
    notification_key = f"elite_intelligent_{fixture_id}"
    if notification_key not in notified_matches['elite_games']:
        
        match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
        match_time_local = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
        
        league_analysis = match_intel['league']
        
        # Montar análise das equipes
        teams_analysis = ""
        if home_intel and away_intel:
            teams_analysis = f"""
🏠 <b>{home_team}</b> ({home_intel['classification']})
• Taxa vitórias: {home_intel['win_rate']}%
• Odd média: {home_intel['avg_odd']}

✈️ <b>{away_team}</b> ({away_intel['classification']})  
• Taxa vitórias: {away_intel['win_rate']}%
• Odd média: {away_intel['avg_odd']}

🏆 <b>Tipo:</b> {match_intel['match_type']}
            """
        elif home_intel:
            teams_analysis = f"""
🏠 <b>{home_team}</b> ({home_intel['classification']})
• Taxa vitórias: {home_intel['win_rate']}%
• Odd média: {home_intel['avg_odd']}

✈️ <b>{away_team}</b> (Time normal)

🏆 <b>Tipo:</b> {match_intel['match_type']}
            """
        elif away_intel:
            teams_analysis = f"""
🏠 <b>{home_team}</b> (Time normal)

✈️ <b>{away_team}</b> ({away_intel['classification']})
• Taxa vitórias: {away_intel['win_rate']}%  
• Odd média: {away_intel['avg_odd']}

🏆 <b>Tipo:</b> {match_intel['match_type']}
            """
        
        message = f"""
⭐ <b>JOGO DO DIA - ANÁLISE COMPLETA</b> ⭐

🏆 <b>{league_analysis['league_name']} ({league_analysis['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_analysis}

📊 <b>Inteligência da Liga:</b>
• Over 1.5: {league_analysis['over_under']['over_15_pct']}% (Odd: {league_analysis['over_under']['over_15_odd']})
• Under 1.5: {league_analysis['over_under']['under_15_pct']}% (Odd: {league_analysis['over_under']['under_15_odd']})
• 0x0 Final: {league_analysis['0x0_analysis']['fulltime_pct']}% (Odd: {league_analysis['0x0_analysis']['ft_odd']})

🎯 <b>Recomendações:</b>
{chr(10).join(['• ' + rec for rec in match_intel['recommendations']]) if match_intel['recommendations'] else '• Aguardar desenvolvimento do jogo'}

🕐 <b>{match_time_local.strftime('%H:%M')} (Lisboa)</b>
📅 {match_time_local.strftime('%d/%m/%Y')}

🔥 <b>Jogo de alto interesse!</b>
        """
        
        await send_telegram_message(message)
        notified_matches['elite_games'].add(notification_key)

async def process_elite_finished_intelligent(match):
    """Processa resultados de jogos de elite com inteligência"""
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    if league_id not in TOP_LEAGUES:
        return
    
    match_intel = calculate_match_intelligence(home_team, away_team, league_id)
    if not match_intel:
        return
    
    home_intel = match_intel['home_team']
    away_intel = match_intel['away_team']
    
    # Só processar se pelo menos uma equipe for de elite
    if not (home_intel or away_intel):
        return
    
    league_analysis = match_intel['league']
    
    # **ANÁLISE UNDER 1.5 GOLS**
    if total_goals < 2:
        notification_key = f"elite_under15_{fixture_id}"
        if notification_key not in notified_matches['under_15']:
            
            winner = "Empate"
            if home_goals > away_goals:
                winner = home_team
            elif away_goals > home_goals:
                winner = away_team
            
            message = f"""
📉 <b>UNDER 1.5 CONFIRMADO - EQUIPE DE ELITE</b> 📉

🏆 <b>{league_analysis['league_name']} ({league_analysis['country']})</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>
🏆 <b>Resultado:</b> {winner}

📊 <b>Análise do Resultado:</b>
• Total gols: {total_goals} (Under 1.5 ✅)
• Probabilidade Under 1.5: {league_analysis['over_under']['under_15_pct']}%
• Odd esperada: ~{league_analysis['over_under']['under_15_odd']}

👑 <b>Equipes Envolvidas:</b>
{f"• {home_team}: {home_intel['win_rate']}% vitórias ({home_intel['classification']})" if home_intel else f"• {home_team}: Time normal"}
{f"• {away_team}: {away_intel['win_rate']}% vitórias ({away_intel['classification']})" if away_intel else f"• {away_team}: Time normal"}

💡 <b>Insight:</b>
Jogo com equipe(s) de elite terminou com poucos gols, confirmando padrão defensivo ou eficiência baixa no ataque.

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['under_15'].add(notification_key)
    
    # **ANÁLISE OVER 2.5 GOLS**
    elif total_goals > 2:
        notification_key = f"elite_over25_{fixture_id}"
        if notification_key not in notified_matches.get('over_25', set()):
            if 'over_25' not in notified_matches:
                notified_matches['over_25'] = set()
            
            message = f"""
⚽ <b>OVER 2.5 CONFIRMADO - EQUIPE DE ELITE</b> ⚽

🏆 <b>{league_analysis['league_name']} ({league_analysis['country']})</b>
⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>

📊 <b>Análise do Resultado:</b>
• Total gols: {total_goals} (Over 2.5 ✅)
• Probabilidade Over 2.5: {league_analysis['over_under']['over_25_pct']}%
• Jogo ofensivo/aberto

👑 <b>Equipes de Elite:</b>
{f"• {home_team}: {home_intel['classification']}" if home_intel else ""}
{f"• {away_team}: {away_intel['classification']}" if away_intel else ""}

🔥 <b>Jogo movimentado com equipe(s) de elite!</b>

🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
            """
            
            await send_telegram_message(message)
            notified_matches['over_25'].add(notification_key)

# =========================================================
# SISTEMA DE MONITORAMENTO HORÁRIO
# =========================================================

async def hourly_monitoring():
    """Executa monitoramento inteligente a cada hora"""
    logger.info("🧠 Iniciando sistema de monitoramento inteligente...")
    
    await send_telegram_message(
        f"🚀 <b>Bot Inteligente de Futebol Iniciado!</b>\n\n"
        f"🧠 <b>Recursos Avançados:</b>\n"
        f"• Análise por períodos de 15 min\n"
        f"• Alertas de gols tardios (75'+)\n"
        f"• Inteligência de ligas e equipes\n"
        f"• Recomendações de valor\n\n"
        f"⏰ Ativo das 09h às 23h (Lisboa)\n"
        f"🔍 Verificações horárias inteligentes\n"
        f"⚽ Monitorando {len(TOP_LEAGUES)} ligas principais!"
    )
    
    while True:
        try:
            current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
            current_hour = current_time.hour
            
            if should_run_monitoring():
                logger.info(f"🧠 Executando monitoramento inteligente às {current_hour}h")
                
                # Executar todos os monitoramentos
                await monitor_live_matches()
                await monitor_elite_teams()
                await send_hourly_intelligence_summary()
                
                logger.info(f"✅ Monitoramento inteligente das {current_hour}h concluído")
            else:
                logger.info(f"😴 Fora do horário (atual: {current_hour}h)")
            
            # Aguardar próxima hora
            next_hour = (current_time.replace(minute=0, second=0, microsecond=0) + 
                        timedelta(hours=1))
            wait_time = (next_hour - current_time).total_seconds()
            
            logger.info(f"⏳ Próxima verificação em {int(wait_time/60)} minutos...")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Erro no loop inteligente: {e}")
            await send_telegram_message(f"⚠️ Erro no bot inteligente: {e}")
            await asyncio.sleep(300)

async def send_hourly_intelligence_summary():
    """Envia resumo inteligente a cada 4 horas"""
    current_hour = get_current_hour_lisbon()
    
    # Enviar resumo às 12h, 16h e 20h
    if current_hour in [12, 16, 20]:
        summary_counts = {
            'halftime_0x0': len(notified_matches.get('halftime_0x0', [])),
            'finished_0x0': len(notified_matches.get('finished_0x0', [])),
            'elite_games': len(notified_matches.get('elite_games', [])),
            'under_15': len(notified_matches.get('under_15', [])),
            'late_goals': len(notified_matches.get('late_goals', [])),
            'period_alerts': len(notified_matches.get('period_alerts', []))
        }
        
        total_alerts = sum(summary_counts.values())
        
        if total_alerts > 0:
            message = f"""
📊 <b>RESUMO INTELIGENTE - {current_hour}h</b>

🎯 <b>Alertas de Hoje:</b>
• Intervalos 0x0: {summary_counts['halftime_0x0']}
• Finais 0x0: {summary_counts['finished_0x0']}
• Jogos elite: {summary_counts['elite_games']}
• Under 1.5: {summary_counts['under_15']}
• Gols tardios: {summary_counts['late_goals']}
• Períodos favoráveis: {summary_counts['period_alerts']}

<b>Total: {total_alerts} oportunidades identificadas!</b>

🧠 Sistema inteligente em funcionamento ✅
🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')}</i>
            """
            
            await send_telegram_message(message)

# =========================================================
# RELATÓRIOS DIÁRIOS INTELIGENTES
# =========================================================

async def daily_status():
    """Envia relatório diário inteligente às 08h"""
    while True:
        try:
            current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
            
            if current_time.hour == 8 and current_time.minute < 30:
                
                # Contar todas as notificações
                total_notifications = sum(len(notifications) for notifications in notified_matches.values())
                
                status_message = f"""
📊 <b>RELATÓRIO DIÁRIO INTELIGENTE</b>

🎯 <b>Atividade de Ontem:</b>
• Intervalos 0x0: {len(notified_matches.get('halftime_0x0', []))}
• Finais 0x0: {len(notified_matches.get('finished_0x0', []))}
• Jogos de elite: {len(notified_matches.get('elite_games', []))}
• Under 1.5: {len(notified_matches.get('under_15', []))}
• Alertas gols tardios: {len(notified_matches.get('late_goals', []))}
• Períodos favoráveis: {len(notified_matches.get('period_alerts', []))}

<b>Total: {total_notifications} oportunidades identificadas!</b>

🧠 <b>Sistema Inteligente:</b>
• {len(LEAGUE_STATS)} ligas com dados reais
• {len(ELITE_TEAM_STATS)} equipes com perfil completo
• Análise por períodos de 15 min
• Alertas de gols tardios
• Recomendações de valor

⏰ Funcionamento: 09h-23h (Lisboa)
✅ Todos os sistemas operacionais!

🕐 {current_time.strftime('%d/%m/%Y %H:%M')} (Lisboa)
                """
                
                await send_telegram_message(status_message)
                
                # Limpar contadores
                for key in notified_matches:
                    notified_matches[key].clear()
                
                await asyncio.sleep(23 * 3600)
            else:
                next_day_8am = (current_time.replace(hour=8, minute=0, second=0, microsecond=0) + 
                               timedelta(days=1))
                wait_time = (next_day_8am - current_time).total_seconds()
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"Erro no relatório diário: {e}")
            await asyncio.sleep(3600)

# =========================================================
# SERVIDOR WEB APRIMORADO
# =========================================================

async def run_web_server():
    """Executa servidor web com status inteligente"""
    app = web.Application()
    
    async def health_check(request):
        current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
        is_active = should_run_monitoring()
        total_notifications = sum(len(notifications) for notifications in notified_matches.values())
        
        status_html = f"""
        <html>
        <head>
            <title>Bot Inteligente de Futebol - Status</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .active {{ color: green; }}
                .inactive {{ color: red; }}
                .stats {{ background: #f5f5f5; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>🧠 Bot Inteligente de Monitoramento de Futebol</h1>
            
            <div class="stats">
                <h2>📊 Status Atual</h2>
                <ul>
                    <li><strong>Hora (Lisboa):</strong> {current_time.strftime('%H:%M %d/%m/%Y')}</li>
                    <li><strong>Status:</strong> <span class="{'active' if is_active else 'inactive'}">{'🟢 ATIVO' if is_active else '🔴 INATIVO'}</span></li>
                    <li><strong>Funcionamento:</strong> 09h às 23h (Lisboa)</li>
                    <li><strong>Total alertas hoje:</strong> {total_notifications}</li>
                </ul>
            </div>
            
            <div class="stats">
                <h2>🎯 Alertas de Hoje</h2>
                <ul>
                    <li><strong>Intervalos 0x0:</strong> {len(notified_matches.get('halftime_0x0', []))}</li>
                    <li><strong>Finais 0x0:</strong> {len(notified_matches.get('finished_0x0', []))}</li>
                    <li><strong>Jogos de elite:</strong> {len(notified_matches.get('elite_games', []))}</li>
                    <li><strong>Under 1.5:</strong> {len(notified_matches.get('under_15', []))}</li>
                    <li><strong>Gols tardios:</strong> {len(notified_matches.get('late_goals', []))}</li>
                    <li><strong>Períodos favoráveis:</strong> {len(notified_matches.get('period_alerts', []))}</li>
                </ul>
            </div>
            
            <div class="stats">
                <h2>🧠 Sistema Inteligente</h2>
                <ul>
                    <li><strong>Ligas com dados:</strong> {len(LEAGUE_STATS)}</li>
                    <li><strong>Equipes mapeadas:</strong> {len(ELITE_TEAM_STATS)}</li>
                    <li><strong>Ligas monitoradas:</strong> {len(TOP_LEAGUES)}</li>
                </ul>
            </div>
            
            <div class="stats">
                <h2>⚙️ Recursos Avançados</h2>
                <ul>
                    <li>✅ Análise por períodos de 15 minutos</li>
                    <li>✅ Alertas de gols tardios (75'+)</li>
                    <li>✅ Inteligência de ligas com dados reais</li>
                    <li>✅ Perfil completo de equipes de elite</li>
                    <li>✅ Recomendações de apostas de valor</li>
                    <li>✅ Análise Over/Under inteligente</li>
                </ul>
            </div>
            
            <p><em>🚀 Bot inteligente funcionando perfeitamente! ⚽</em></p>
        </body>
        </html>
        """
        
        return web.Response(text=status_html, content_type="text/html")
    
    async def status_json(request):
        current_time = datetime.now(ZoneInfo("Europe/Lisbon"))
        status_info = {
            "status": "active" if should_run_monitoring() else "standby",
            "current_time_lisbon": current_time.isoformat(),
            "system_type": "intelligent_football_bot",
            "features": {
                "15min_periods": True,
                "late_goals_alerts": True,
                "league_intelligence": True,
                "elite_team_profiles": True,
                "value_recommendations": True
            },
            "monitored_leagues": len(TOP_LEAGUES),
            "leagues_with_data": len(LEAGUE_STATS),
            "elite_teams": len(ELITE_TEAM_STATS),
            "notifications_today": {
                "halftime_0x0": len(notified_matches.get('halftime_0x0', [])),
                "finished_0x0": len(notified_matches.get('finished_0x0', [])),
                "elite_games": len(notified_matches.get('elite_games', [])),
                "under_15": len(notified_matches.get('under_15', [])),
                "late_goals": len(notified_matches.get('late_goals', [])),
                "period_alerts": len(notified_matches.get('period_alerts', []))
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
    
    logger.info(f"🌐 Servidor web inteligente iniciado na porta {port}")

# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================

async def main():
    """Função principal do bot inteligente"""
    logger.info("🧠 Iniciando Bot Inteligente de Monitoramento de Futebol...")
    logger.info(f"📊 {len(LEAGUE_STATS)} ligas com dados reais")
    logger.info(f"👑 {len(ELITE_TEAM_STATS)} equipes com perfil completo")
    logger.info(f"⏰ Funcionamento: 09h às 23h (Lisboa)")
    logger.info(f"🔄 Verificações horárias com inteligência avançada")
    
    # Executar todos os serviços inteligentes
    await asyncio.gather(
        run_web_server(),
        hourly_monitoring(),
        daily_status()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot inteligente interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal no bot inteligente: {e}")
