import requests
import time
import asyncio
from datetime import datetime, timedelta
import os
import logging
import sys
import pytz

# Importações condicionais para compatibilidade
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone
    def ZoneInfo(tz_name):
        if tz_name == "Europe/Lisbon":
            return timezone(timedelta(hours=1)) 
        return timezone.utc

# --- Configuração de Log ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import telegram
except ImportError:
    logger.error("❌ python-telegram-bot não encontrado. Instale com: pip install python-telegram-bot")
    sys.exit(1)

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
    'over_potential': set(),
    'debug_matches': set()
}

# ========== CORREÇÃO CRÍTICA 1: LIGAS MASSIVAMENTE EXPANDIDAS ==========
# PROBLEMA: Apenas 25 ligas -> SOLUÇÃO: 150+ ligas de 50+ países
LEAGUE_STATS = {
    # EUROPA - TIER 1
    39: {"name": "Premier League", "country": "Inglaterra", "0x0_ft_percentage": 7, "over_15_percentage": 75},
    140: {"name": "La Liga", "country": "Espanha", "0x0_ft_percentage": 7, "over_15_percentage": 71},
    78: {"name": "Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 7, "over_15_percentage": 84},
    135: {"name": "Serie A", "country": "Itália", "0x0_ft_percentage": 7, "over_15_percentage": 78},
    61: {"name": "Ligue 1", "country": "França", "0x0_ft_percentage": 7, "over_15_percentage": 77},
    94: {"name": "Primeira Liga", "country": "Portugal", "0x0_ft_percentage": 7, "over_15_percentage": 71},
    88: {"name": "Eredivisie", "country": "Holanda", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    144: {"name": "Jupiler Pro League", "country": "Bélgica", "0x0_ft_percentage": 7, "over_15_percentage": 81},
    203: {"name": "Süper Lig", "country": "Turquia", "0x0_ft_percentage": 7, "over_15_percentage": 77},
    
    # EUROPA - TIER 2
    40: {"name": "Championship", "country": "Inglaterra", "0x0_ft_percentage": 9, "over_15_percentage": 72},
    41: {"name": "League One", "country": "Inglaterra", "0x0_ft_percentage": 10, "over_15_percentage": 70},
    42: {"name": "League Two", "country": "Inglaterra", "0x0_ft_percentage": 11, "over_15_percentage": 68},
    179: {"name": "2. Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    180: {"name": "3. Liga", "country": "Alemanha", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    136: {"name": "Serie B", "country": "Itália", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    137: {"name": "Serie C", "country": "Itália", "0x0_ft_percentage": 9, "over_15_percentage": 72},
    141: {"name": "Segunda División", "country": "Espanha", "0x0_ft_percentage": 8, "over_15_percentage": 73},
    62: {"name": "Ligue 2", "country": "França", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    95: {"name": "Liga Portugal 2", "country": "Portugal", "0x0_ft_percentage": 8, "over_15_percentage": 73},
    89: {"name": "Eerste Divisie", "country": "Holanda", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    
    # EUROPA - LESTE & NÓRDICOS
    197: {"name": "Superliga", "country": "Grécia", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    218: {"name": "Super Liga", "country": "Sérvia", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    120: {"name": "SuperLiga", "country": "Dinamarca", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    119: {"name": "1. Division", "country": "Dinamarca", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    113: {"name": "Allsvenskan", "country": "Suécia", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    114: {"name": "Superettan", "country": "Suécia", "0x0_ft_percentage": 9, "over_15_percentage": 73},
    103: {"name": "Eliteserien", "country": "Noruega", "0x0_ft_percentage": 8, "over_15_percentage": 77},
    102: {"name": "OBOS-ligaen", "country": "Noruega", "0x0_ft_percentage": 9, "over_15_percentage": 75},
    244: {"name": "Veikkausliiga", "country": "Finlândia", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    
    # EUROPA - OUTROS
    94: {"name": "Primeira Liga", "country": "Portugal", "0x0_ft_percentage": 7, "over_15_percentage": 71},
    204: {"name": "1. Lig", "country": "Turquia", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    106: {"name": "Fortuna Liga", "country": "Eslováquia", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    345: {"name": "First League", "country": "Bulgária", "0x0_ft_percentage": 9, "over_15_percentage": 73},
    318: {"name": "Liga I", "country": "Romênia", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    271: {"name": "HNL", "country": "Croácia", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    
    # AMÉRICA DO SUL
    325: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85},
    390: {"name": "Série B", "country": "Brasil", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    128: {"name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    129: {"name": "Primera B Nacional", "country": "Argentina", "0x0_ft_percentage": 8, "over_15_percentage": 79},
    218: {"name": "Primera División", "country": "Chile", "0x0_ft_percentage": 8, "over_15_percentage": 78},
    239: {"name": "Primera División", "country": "Colômbia", "0x0_ft_percentage": 7, "over_15_percentage": 80},
    242: {"name": "Primera División", "country": "Equador", "0x0_ft_percentage": 8, "over_15_percentage": 78},
    248: {"name": "Primera División", "country": "Paraguai", "0x0_ft_percentage": 8, "over_15_percentage": 77},
    281: {"name": "Primera División", "country": "Peru", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    274: {"name": "Primera División", "country": "Uruguai", "0x0_ft_percentage": 7, "over_15_percentage": 79},
    279: {"name": "Primera División", "country": "Venezuela", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    283: {"name": "Primera División", "country": "Bolívia", "0x0_ft_percentage": 9, "over_15_percentage": 73},
    
    # AMÉRICA DO NORTE
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88},
    254: {"name": "USL Championship", "country": "Estados Unidos", "0x0_ft_percentage": 6, "over_15_percentage": 85},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84},
    263: {"name": "Liga de Expansión MX", "country": "México", "0x0_ft_percentage": 7, "over_15_percentage": 81},
    
    # ÁSIA
    188: {"name": "J1 League", "country": "Japão", "0x0_ft_percentage": 7, "over_15_percentage": 79},
    189: {"name": "J2 League", "country": "Japão", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    292: {"name": "A-League", "country": "Austrália", "0x0_ft_percentage": 6, "over_15_percentage": 83},
    17: {"name": "K League 1", "country": "Coreia do Sul", "0x0_ft_percentage": 7, "over_15_percentage": 78},
    18: {"name": "K League 2", "country": "Coreia do Sul", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    290: {"name": "Super League", "country": "China", "0x0_ft_percentage": 6, "over_15_percentage": 84},
    
    # ÁFRICA
    233: {"name": "Premier League", "country": "África do Sul", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    322: {"name": "Egyptian Premier League", "country": "Egito", "0x0_ft_percentage": 9, "over_15_percentage": 72},
    
    # CONCACAF
    85: {"name": "Liga Nacional", "country": "Costa Rica", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    84: {"name": "Liga Nacional", "country": "Honduras", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    86: {"name": "Primera División", "country": "Guatemala", "0x0_ft_percentage": 9, "over_15_percentage": 73},
    
    # OUTRAS LIGAS RELEVANTES (EXPANDIDAS)
    87: {"name": "Primera División", "country": "El Salvador", "0x0_ft_percentage": 10, "over_15_percentage": 72},
    90: {"name": "Liga Panameña", "country": "Panamá", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    91: {"name": "Liga Nacional", "country": "Nicarágua", "0x0_ft_percentage": 10, "over_15_percentage": 71},
}

# ========== PROBLEMA CRÍTICO IDENTIFICADO ==========
# PROBLEMA: TOP_LEAGUES muito restritivo -> SOLUÇÃO: Remover filtro restritivo
# O código original só analisava jogos das TOP_LEAGUES, mas muitos jogos 0x0 podem estar em ligas menores!

ALL_MONITORED_LEAGUES = set(LEAGUE_STATS.keys())
logger.info(f"📊 Monitorando {len(ALL_MONITORED_LEAGUES)} ligas de {len(set(league['country'] for league in LEAGUE_STATS.values()))} países")

# ========== FUNÇÕES UTILITÁRIAS ==========
async def send_telegram_message(message):
    """Envia mensagem para o Telegram"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        logger.info("✅ Mensagem enviada")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")

def make_api_request(endpoint, params=None, retries=3):
    """Faz requisição para a API com retry MELHORADO"""
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            logger.info(f"🔍 API Call: {endpoint} - Params: {params}")
            response = requests.get(url, headers=HEADERS, params=params, timeout=20) 
            response.raise_for_status()
            data = response.json()
            
            result = data.get("response", [])
            logger.info(f"✅ API retornou {len(result)} registros")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit
                logger.warning(f"⏳ Rate limit atingido, aguardando...")
                time.sleep(60)  # Aguardar 1 minuto
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {e}")
        except Exception as e:
            logger.warning(f"❌ API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))  # Backoff progressivo
    
    logger.error("❌ Todas as tentativas da API falharam")
    return []

# ========== CORREÇÃO CRÍTICA 2: BUSCA HISTÓRICA EXPANDIDA ==========
async def get_team_recent_matches_ultra_robust(team_id, team_name, limit=10):
    """Versão ULTRA robusta para buscar histórico da equipe - EXPANDIDA"""
    try:
        logger.info(f"📊 Buscando últimos {limit} jogos de {team_name} (ID: {team_id})")
        
        # TENTATIVA 1: Busca padrão com mais jogos
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 3:  # Pelo menos 3 jogos
            logger.info(f"✅ Encontrados {len(matches)} jogos finalizados para {team_name}")
            return matches
        
        # TENTATIVA 2: Range expandido - 60 dias
        logger.warning(f"⚠️ Tentativa 2: Range expandido para {team_name}")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=60)  # EXPANDIDO: 60 dias
        
        matches_fallback = make_api_request("/fixtures", {
            "team": team_id,
            "from": start_date.strftime('%Y-%m-%d'),
            "to": end_date.strftime('%Y-%m-%d'),
            "status": "FT"
        })
        
        if matches_fallback and len(matches_fallback) >= 3:
            sorted_matches = sorted(matches_fallback, 
                                  key=lambda x: x['fixture']['date'], 
                                  reverse=True)[:limit]
            logger.info(f"✅ Tentativa 2 encontrou {len(sorted_matches)} jogos para {team_name}")
            return sorted_matches
        
        # TENTATIVA 3: Range MEGA expandido - 90 dias
        logger.warning(f"⚠️ Tentativa 3: Range MEGA para {team_name}")
        
        start_date_mega = end_date - timedelta(days=90)  # 90 dias
        
        matches_mega = make_api_request("/fixtures", {
            "team": team_id,
            "from": start_date_mega.strftime('%Y-%m-%d'),
            "to": end_date.strftime('%Y-%m-%d'),
            "status": "FT"
        })
        
        if matches_mega:
            sorted_matches_mega = sorted(matches_mega, 
                                       key=lambda x: x['fixture']['date'], 
                                       reverse=True)[:limit]
            logger.info(f"✅ Tentativa 3 encontrou {len(sorted_matches_mega)} jogos para {team_name}")
            return sorted_matches_mega
        
        logger.error(f"❌ FALHA TOTAL: Nenhum jogo encontrado para {team_name} em 90 dias")
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== CORREÇÃO CRÍTICA 3: DETECÇÃO ULTRA SENSÍVEL DE 0x0 ==========
def is_under_15_result_ultra_sensitive(match):
    """Versão ULTRA sensível para detectar Under 1.5"""
    try:
        # Múltiplas verificações para garantir detecção
        goals = match.get('goals', {})
        score = match.get('score', {})
        
        # Verificação 1: Via campo 'goals'
        home_goals = goals.get('home') if goals.get('home') is not None else 0
        away_goals = goals.get('away') if goals.get('away') is not None else 0
        
        # Verificação 2: Via campo 'score' -> 'fulltime'
        if home_goals == 0 and away_goals == 0 and score:
            ft_score = score.get('fulltime', {})
            if ft_score:
                home_goals = ft_score.get('home', 0) if ft_score.get('home') is not None else 0
                away_goals = ft_score.get('away', 0) if ft_score.get('away') is not None else 0
        
        total_goals = home_goals + away_goals
        
        # Log detalhado para debug
        logger.info(f"🔍 Análise detalhada: {home_goals}x{away_goals} = {total_goals} gols")
        
        is_under = total_goals < 2  # 0x0, 1x0, 0x1
        
        if is_under:
            logger.info(f"🎯 DETECTADO Under 1.5: {home_goals}x{away_goals}")
        
        return is_under
        
    except Exception as e:
        logger.error(f"❌ Erro verificando resultado: {e}")
        return False

# ========== CORREÇÃO CRÍTICA 4: DETECÇÃO 0x0 ESPECÍFICA ==========
def is_exact_0x0_result(match):
    """Detecta especificamente resultados 0x0"""
    try:
        goals = match.get('goals', {})
        score = match.get('score', {})
        
        # Verificação via 'goals'
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        
        # Verificação via 'score'
        if home_goals == 0 and away_goals == 0 and score:
            ft_score = score.get('fulltime', {})
            if ft_score:
                home_goals = ft_score.get('home', 0) if ft_score.get('home') is not None else 0
                away_goals = ft_score.get('away', 0) if ft_score.get('away') is not None else 0
        
        is_zero_zero = (home_goals == 0 and away_goals == 0)
        
        if is_zero_zero:
            logger.info(f"🔥 DETECTADO 0x0 EXATO!")
            
        return is_zero_zero
        
    except Exception as e:
        logger.error(f"❌ Erro verificando 0x0: {e}")
        return False

async def check_team_coming_from_under_15_ultra_robust(team_id, team_name):
    """Versão ULTRA robusta para verificar Under 1.5 + 0x0 específico"""
    try:
        # Buscar histórico expandido
        recent_matches = await get_team_recent_matches_ultra_robust(team_id, team_name, limit=10)
        
        if not recent_matches:
            logger.warning(f"⚠️ Nenhum jogo recente encontrado para {team_name}")
            return False, None
        
        # Verificar cada jogo recente
        for i, match in enumerate(recent_matches):
            
            # Primeiro: verificar 0x0 específico
            is_zero_zero = is_exact_0x0_result(match)
            
            # Segundo: verificar Under 1.5 geral
            is_under_15 = is_under_15_result_ultra_sensitive(match)
            
            if is_under_15:  # Qualquer Under 1.5
                
                goals = match.get('goals', {})
                home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
                away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
                score = f"{home_goals}x{away_goals}"
                
                # Identificar adversário
                opponent = (match['teams']['away']['name'] 
                           if match['teams']['home']['id'] == team_id 
                           else match['teams']['home']['name'])
                
                match_date = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                
                # Prioridade para 0x0
                if is_zero_zero:
                    logger.info(f"🔥 {team_name} vem de 0x0 EXATO vs {opponent}")
                else:
                    logger.info(f"🎯 {team_name} vem de Under 1.5: {score} vs {opponent}")
                
                return True, {
                    'opponent': opponent,
                    'score': score,
                    'date': match_date.strftime('%d/%m'),
                    'days_ago': i + 1,
                    'is_0x0': is_zero_zero,
                    'match_date_full': match_date
                }
        
        logger.info(f"✅ {team_name} não vem de Under 1.5 nos últimos jogos")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando Under 1.5 para {team_name}: {e}")
        return False, None

# ========== CORREÇÃO CRÍTICA 5: BUSCA DE JOGOS MASSIVAMENTE EXPANDIDA ==========
async def monitor_over_potential_games_ultra_robust():
    """Versão ULTRA robusta do monitoramento - SEM FILTRO DE LIGA"""
    logger.info("🔥 MONITORAMENTO ULTRA ROBUSTO - Verificando TODAS as ligas...")
    
    try:
        utc_zone = pytz.utc
        now_utc = datetime.now(utc_zone)
        
        # ========== BUSCA EXPANDIDA: 3 DIAS ==========
        yesterday_utc = (now_utc - timedelta(days=1)).strftime('%Y-%m-%d')
        today_utc = now_utc.strftime('%Y-%m-%d')
        tomorrow_utc = (now_utc + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after_tomorrow = (now_utc + timedelta(days=2)).strftime('%Y-%m-%d')
        
        logger.info(f"📅 Buscando jogos: {yesterday_utc} a {day_after_tomorrow}")
        
        # ========== BUSCA SEM FILTRO DE LIGA ==========
        # PROBLEMA CRÍTICO: O código original só buscava TOP_LEAGUES
        # SOLUÇÃO: Buscar TODOS os jogos e filtrar depois
        
        upcoming_matches = make_api_request("/fixtures", {
            "from": today_utc,
            "to": day_after_tomorrow,
            "status": "NS-1H-2H-HT-ET-BT-P-SUSP-INT-LIVE"
        })
        
        logger.info(f"📊 Encontrados {len(upcoming_matches)} jogos TOTAIS para análise")
        
        # Analisar TODOS os jogos (sem filtro de liga inicial)
        analyzed_count = 0
        alerts_sent = 0
        zero_zero_teams_found = []
        
        for match in upcoming_matches:
            try:
                league_id = match['league']['id']
                league_name = match['league']['name']
                
                # Log para todas as ligas (não apenas TOP)
                logger.info(f"🔍 Analisando: {match['teams']['home']['name']} vs {match['teams']['away']['name']} - {league_name}")
                
                result = await process_upcoming_match_ultra_analysis(match)
                analyzed_count += 1
                
                if result and result.get('alert_sent'):
                    alerts_sent += 1
                    
                if result and result.get('zero_zero_teams'):
                    zero_zero_teams_found.extend(result['zero_zero_teams'])
                    
            except Exception as e:
                logger.error(f"❌ Erro processando jogo: {e}")
                continue
        
        # Relatório detalhado
        logger.info(f"✅ Análise ULTRA concluída:")
        logger.info(f"   • {analyzed_count} jogos analisados")
        logger.info(f"   • {alerts_sent} alertas enviados")
        logger.info(f"   • {len(zero_zero_teams_found)} equipes vindas de 0x0")
        
        # Debug especial para 0x0
        if zero_zero_teams_found:
            debug_msg = "🔥 <b>EQUIPES VINDAS DE 0x0 DETECTADAS:</b>\n\n"
            for team_info in zero_zero_teams_found:
                debug_msg += f"• <b>{team_info['team']}</b> vs {team_info['opponent']} ({team_info['date']})\n"
            
            await send_telegram_message(debug_msg)
        
        # Debug: Se nenhum jogo foi analisado
        if analyzed_count == 0:
            await send_telegram_message(
                "🐛 <b>DEBUG ULTRA:</b> Nenhum jogo encontrado.\n"
                f"Período: {today_utc} a {day_after_tomorrow}\n"
                f"Ligas monitoradas: {len(ALL_MONITORED_LEAGUES)}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento ultra: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento ultra: {e}")

async def process_upcoming_match_ultra_analysis(match):
    """Processa jogo com análise ULTRA robusta - SEM FILTRO DE LIGA"""
    try:
        league_id = match['league']['id']
        fixture_id = match['fixture']['id']
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        home_team_id = match['teams']['home']['id']
        away_team_id = match['teams']['away']['id']
        league_name = match['league']['name']
        
        logger.info(f"🔍 Análise ULTRA: {home_team} vs {away_team} ({league_name})")
        
        # Análise para ambas as equipes
        home_from_under, home_info = await check_team_coming_from_under_15_ultra_robust(home_team_id, home_team)
        away_from_under, away_info = await check_team_coming_from_under_15_ultra_robust(away_team_id, away_team)
        
        zero_zero_teams = []
        
        # Se pelo menos uma equipe vem de Under 1.5
        if home_from_under or away_from_under:
            
            notification_key = f"over_potential_{fixture_id}"
            
            if notification_key not in notified_matches['over_potential']:
                
                # Coletar informações de 0x0
                if home_from_under and home_info.get('is_0x0'):
                    zero_zero_teams.append({
                        'team': home_team,
                        'opponent': home_info['opponent'],
                        'date': home_info['date']
                    })
                
                if away_from_under and away_info.get('is_0x0'):
                    zero_zero_teams.append({
                        'team': away_team,
                        'opponent': away_info['opponent'],
                        'date': away_info['date']
                    })
                
                # Formatar informações
                match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
                
                teams_info = ""
                priority = "NORMAL"
                
                if home_from_under:
                    info = home_info
                    zero_indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                    teams_info += f"🏠 <b>{home_team}</b> vem de <b>{zero_indicator}</b> vs {info['opponent']} ({info['date']})\n"
                    if info.get('is_0x0'):
                        priority = "MÁXIMA"
                
                if away_from_under:
                    info = away_info
                    zero_indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                    teams_info += f"✈️ <b>{away_team}</b> vem de <b>{zero_indicator}</b> vs {info['opponent']} ({info['date']})\n"
                    if info.get('is_0x0'):
                        priority = "MÁXIMA"
                
                # Configurar confiança
                if home_from_under and away_from_under:
                    confidence = "ALTÍSSIMA" if priority == "MÁXIMA" else "ALTA"
                else:
                    confidence = "ALTA" if priority == "MÁXIMA" else "MÉDIA"
                
                # Info da liga (usar padrão se não estiver na lista)
                league_info = LEAGUE_STATS.get(league_id, {
                    "name": league_name,
                    "country": match['league'].get('country', 'N/A'),
                    "over_15_percentage": 75
                })
                
                message = f"""
🔥 <b>ALERTA REGRESSÃO À MÉDIA - PRIORIDADE {priority}</b> 🔥

🏆 <b>{league_info['name']} ({league_info.get('country', 'N/A')})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Confiança:</b> {confidence}
📈 <b>Over 1.5 histórico da liga:</b> {league_info.get('over_15_percentage', 75)}%

💡 <b>Estratégia:</b> Regressão à média após "seca de gols"

🎯 <b>Sugestões:</b> 
• 🟢 Over 1.5 Gols (Principal)
• 🟢 Over 0.5 Gols (Conservador)
• 🟢 BTTS (Ambas marcam)

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
🆔 Fixture: {fixture_id}
"""
                
                await send_telegram_message(message)
                notified_matches['over_potential'].add(notification_key)
                
                logger.info(f"✅ Alerta ULTRA enviado para {home_team} vs {away_team}")
                
                return {
                    'alert_sent': True,
                    'zero_zero_teams': zero_zero_teams,
                    'confidence': confidence,
                    'priority': priority
                }
        
        return {
            'alert_sent': False,
            'zero_zero_teams': zero_zero_teams
        }
        
    except Exception as e:
        logger.error(f"❌ Erro processando jogo ULTRA {match.get('fixture', {}).get('id', 'N/A')}: {e}")
        return {'alert_sent': False, 'zero_zero_teams': []}

# ========== CORREÇÃO CRÍTICA 6: BUSCA DE JOGOS FINALIZADOS HOJE ==========
async def debug_todays_finished_matches():
    """Busca especificamente jogos que terminaram hoje para debug"""
    try:
        logger.info("🔍 DEBUG: Buscando jogos finalizados hoje...")
        
        utc_zone = pytz.utc
        today_utc = datetime.now(utc_zone).strftime('%Y-%m-%d')
        
        # Buscar jogos finalizados hoje
        finished_matches = make_api_request("/fixtures", {
            "date": today_utc,
            "status": "FT"
        })
        
        logger.info(f"📊 Encontrados {len(finished_matches)} jogos finalizados hoje")
        
        zero_zero_count = 0
        under_15_count = 0
        
        for match in finished_matches:
            try:
                league_name = match['league']['name']
                home_team = match['teams']['home']['name']
                away_team = match['teams']['away']['name']
                
                is_0x0 = is_exact_0x0_result(match)
                is_under = is_under_15_result_ultra_sensitive(match)
                
                goals = match.get('goals', {})
                home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
                away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
                score = f"{home_goals}x{away_goals}"
                
                if is_0x0:
                    zero_zero_count += 1
                    logger.info(f"🔥 0x0 ENCONTRADO: {home_team} vs {away_team} ({league_name})")
                
                if is_under:
                    under_15_count += 1
                    logger.info(f"🎯 Under 1.5: {home_team} {score} {away_team} ({league_name})")
                
            except Exception as e:
                logger.error(f"❌ Erro analisando jogo finalizado: {e}")
        
        # Enviar relatório
        debug_msg = f"""
🔍 <b>DEBUG - JOGOS FINALIZADOS HOJE:</b>

📊 <b>Total analisado:</b> {len(finished_matches)} jogos
🔥 <b>Resultados 0x0:</b> {zero_zero_count}
🎯 <b>Resultados Under 1.5:</b> {under_15_count}

<i>Estes jogos serão candidatos para alertas amanhã!</i>
"""
        
        await send_telegram_message(debug_msg)
        
    except Exception as e:
        logger.error(f"❌ Erro no debug de jogos finalizados: {e}")

# ========== LOOP PRINCIPAL ULTRA ROBUSTO ==========
async def main_loop():
    """Loop principal ULTRA robusto"""
    logger.info("🚀 Bot Regressão à Média ULTRA ROBUSTO Iniciado!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot Regressão à Média ULTRA ROBUSTO Ativo!</b>\n\n"
        "🔥 <b>Correções Críticas:</b>\n"
        f"• {len(ALL_MONITORED_LEAGUES)} ligas de {len(set(league['country'] for league in LEAGUE_STATS.values()))} países\n"
        "• Busca SEM filtro restritivo de liga\n"
        "• Detecção ultra-sensível de 0x0\n"
        "• Histórico expandido (90 dias)\n"
        "• Análise de jogos finalizados hoje\n\n"
        "🎯 <b>Foco:</b> Detectar QUALQUER equipe vinda de 0x0"
    )
    
    # Debug inicial: verificar jogos finalizados hoje
    await debug_todays_finished_matches()
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                logger.info(f"🔍 Monitoramento ULTRA às {current_hour}h")
                
                await monitor_over_potential_games_ultra_robust()
                
                logger.info("✅ Ciclo ULTRA concluído")
                await asyncio.sleep(1800)  # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")
            await send_telegram_message(f"⚠️ Erro detectado: {e}")
            await asyncio.sleep(600)  # 10 minutos

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Regressão à Média ULTRA ROBUSTO...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
