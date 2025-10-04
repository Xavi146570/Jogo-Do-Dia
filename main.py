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
    
    # EUROPA - TIER 2 & 3
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
    113: {"name": "Allsvenskan", "country": "Suécia", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    103: {"name": "Eliteserien", "country": "Noruega", "0x0_ft_percentage": 8, "over_15_percentage": 77},
    244: {"name": "Veikkausliiga", "country": "Finlândia", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    204: {"name": "1. Lig", "country": "Turquia", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    
    # AMÉRICA DO SUL
    325: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85},
    390: {"name": "Série B", "country": "Brasil", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    128: {"name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    218: {"name": "Primera División", "country": "Chile", "0x0_ft_percentage": 8, "over_15_percentage": 78},
    239: {"name": "Primera División", "country": "Colômbia", "0x0_ft_percentage": 7, "over_15_percentage": 80},
    
    # AMÉRICA DO NORTE
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84},
    
    # ÁSIA-OCEANIA
    188: {"name": "J1 League", "country": "Japão", "0x0_ft_percentage": 7, "over_15_percentage": 79},
    292: {"name": "A-League", "country": "Austrália", "0x0_ft_percentage": 6, "over_15_percentage": 83},
    17: {"name": "K League 1", "country": "Coreia do Sul", "0x0_ft_percentage": 7, "over_15_percentage": 78},
}

ALL_MONITORED_LEAGUES = set(LEAGUE_STATS.keys())
logger.info(f"📊 Monitorando {len(ALL_MONITORED_LEAGUES)} ligas")

# ========== FUNÇÕES UTILITÁRIAS ==========
async def send_telegram_message(message):
    """Envia mensagem para o Telegram"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        logger.info("✅ Mensagem enviada")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")

def make_api_request(endpoint, params=None, retries=3):
    """Faz requisição para a API com retry"""
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            logger.info(f"🔍 API Call: {endpoint}")
            response = requests.get(url, headers=HEADERS, params=params, timeout=20) 
            response.raise_for_status()
            data = response.json()
            
            result = data.get("response", [])
            logger.info(f"✅ API retornou {len(result)} registros")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning(f"⏳ Rate limit atingido, aguardando...")
                time.sleep(60)
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {e}")
        except Exception as e:
            logger.warning(f"❌ API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
    
    logger.error("❌ Todas as tentativas da API falharam")
    return []

# ========== CORREÇÃO CRÍTICA 2: BUSCA EXPANDIDA COM MÚLTIPLOS STATUS ==========
async def get_team_recent_matches_ultra_robust(team_id, team_name, limit=8):
    """Versão ultra robusta para buscar histórico"""
    try:
        logger.info(f"📊 Buscando últimos {limit} jogos de {team_name} (ID: {team_id})")
        
        # Tentativa 1: Busca padrão
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 3:
            logger.info(f"✅ Encontrados {len(matches)} jogos para {team_name}")
            return matches
        
        # Tentativa 2: Range de datas expandido
        logger.warning(f"⚠️ Fallback para {team_name}")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=45)  # Expandido
        
        matches_fallback = make_api_request("/fixtures", {
            "team": team_id,
            "from": start_date.strftime('%Y-%m-%d'),
            "to": end_date.strftime('%Y-%m-%d'),
            "status": "FT"
        })
        
        if matches_fallback:
            sorted_matches = sorted(matches_fallback, 
                                  key=lambda x: x['fixture']['date'], 
                                  reverse=True)[:limit]
            logger.info(f"✅ Fallback encontrou {len(sorted_matches)} jogos")
            return sorted_matches
        
        logger.error(f"❌ Nenhum jogo encontrado para {team_name}")
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== CORREÇÃO CRÍTICA 3: DETECÇÃO ULTRA SENSÍVEL ==========
def is_exact_0x0_result(match):
    """Detecta especificamente 0x0"""
    try:
        goals = match.get('goals', {})
        score = match.get('score', {})
        
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        
        # Verificação adicional via score.fulltime
        if home_goals == 0 and away_goals == 0 and score:
            ft_score = score.get('fulltime', {})
            if ft_score:
                home_goals = ft_score.get('home', 0) if ft_score.get('home') is not None else 0
                away_goals = ft_score.get('away', 0) if ft_score.get('away') is not None else 0
        
        is_zero_zero = (home_goals == 0 and away_goals == 0)
        
        if is_zero_zero:
            logger.info(f"🔥 0x0 DETECTADO!")
            
        return is_zero_zero
        
    except Exception as e:
        logger.error(f"❌ Erro verificando 0x0: {e}")
        return False

def is_under_15_result(match):
    """Detecta Under 1.5"""
    try:
        goals = match.get('goals', {})
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        total_goals = home_goals + away_goals
        
        return total_goals < 2
        
    except Exception as e:
        logger.error(f"❌ Erro verificando Under 1.5: {e}")
        return False

async def check_team_coming_from_under_15_ultra_robust(team_id, team_name):
    """Verifica se equipe vem de Under 1.5 com foco em 0x0"""
    try:
        recent_matches = await get_team_recent_matches_ultra_robust(team_id, team_name, limit=8)
        
        if not recent_matches:
            logger.warning(f"⚠️ Nenhum jogo encontrado para {team_name}")
            return False, None
        
        # Verificar cada jogo
        for i, match in enumerate(recent_matches):
            is_zero_zero = is_exact_0x0_result(match)
            is_under_15 = is_under_15_result(match)
            
            if is_under_15:
                goals = match.get('goals', {})
                home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
                away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
                score = f"{home_goals}x{away_goals}"
                
                opponent = (match['teams']['away']['name'] 
                           if match['teams']['home']['id'] == team_id 
                           else match['teams']['home']['name'])
                
                match_date = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                
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
        
        logger.info(f"✅ {team_name} não vem de Under 1.5")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando Under 1.5 para {team_name}: {e}")
        return False, None

# ========== CORREÇÃO CRÍTICA 4: BUSCA COM MÚLTIPLOS STATUS ==========
async def monitor_over_potential_games_ultra_robust():
    """Monitoramento ultra robusto com múltiplos status"""
    logger.info("🔥 MONITORAMENTO ULTRA ROBUSTO INICIADO...")
    
    try:
        utc_zone = pytz.utc
        now_utc = datetime.now(utc_zone)
        
        # ========== BUSCA EXPANDIDA: HOJE, AMANHÃ E DEPOIS ==========
        today_utc = now_utc.strftime('%Y-%m-%d')
        tomorrow_utc = (now_utc + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after_tomorrow = (now_utc + timedelta(days=2)).strftime('%Y-%m-%d')
        
        logger.info(f"📅 Período: {today_utc} a {day_after_tomorrow}")
        
        # ========== CORREÇÃO CRÍTICA: MÚLTIPLOS STATUS ==========
        # PROBLEMA: Bot original só buscava "NS" (Not Started)
        # SOLUÇÃO: Buscar múltiplos status incluindo jogos em andamento
        
        all_matches = []
        status_list = ["NS", "1H", "HT", "2H", "ET", "BT", "LIVE"]  # Múltiplos status
        
        for status in status_list:
            matches = make_api_request("/fixtures", {
                "from": today_utc,
                "to": day_after_tomorrow,
                "status": status
            })
            all_matches.extend(matches)
            logger.info(f"Status {status}: {len(matches)} jogos")
        
        # Remover duplicatas por fixture_id
        unique_matches = {}
        for match in all_matches:
            fixture_id = match['fixture']['id']
            if fixture_id not in unique_matches:
                unique_matches[fixture_id] = match
        
        upcoming_matches = list(unique_matches.values())
        logger.info(f"📊 Total único: {len(upcoming_matches)} jogos para análise")
        
        # Analisar cada jogo
        analyzed_count = 0
        alerts_sent = 0
        zero_zero_teams_found = []
        
        for match in upcoming_matches:
            try:
                league_id = match['league']['id']
                league_name = match['league']['name']
                
                logger.info(f"🔍 {match['teams']['home']['name']} vs {match['teams']['away']['name']} - {league_name}")
                
                result = await process_upcoming_match_ultra_analysis(match)
                analyzed_count += 1
                
                if result and result.get('alert_sent'):
                    alerts_sent += 1
                    
                if result and result.get('zero_zero_teams'):
                    zero_zero_teams_found.extend(result['zero_zero_teams'])
                    
            except Exception as e:
                logger.error(f"❌ Erro processando jogo: {e}")
                continue
        
        # Relatório
        logger.info(f"✅ Análise concluída: {analyzed_count} jogos, {alerts_sent} alertas")
        
        if zero_zero_teams_found:
            debug_msg = "🔥 <b>EQUIPES VINDAS DE 0x0:</b>\n\n"
            for team_info in zero_zero_teams_found:
                debug_msg += f"• <b>{team_info['team']}</b> vs {team_info['opponent']} ({team_info['date']})\n"
            
            await send_telegram_message(debug_msg)
        
        if analyzed_count == 0:
            await send_telegram_message(
                "🐛 <b>DEBUG:</b> Nenhum jogo encontrado.\n"
                f"Período: {today_utc} a {day_after_tomorrow}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento: {e}")
        await send_telegram_message(f"⚠️ Erro: {e}")

async def process_upcoming_match_ultra_analysis(match):
    """Processa jogo com análise ultra robusta"""
    try:
        fixture_id = match['fixture']['id']
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        home_team_id = match['teams']['home']['id']
        away_team_id = match['teams']['away']['id']
        league_name = match['league']['name']
        league_id = match['league']['id']
        
        # Análise para ambas as equipes
        home_from_under, home_info = await check_team_coming_from_under_15_ultra_robust(home_team_id, home_team)
        away_from_under, away_info = await check_team_coming_from_under_15_ultra_robust(away_team_id, away_team)
        
        zero_zero_teams = []
        
        if home_from_under or away_from_under:
            
            notification_key = f"over_potential_{fixture_id}"
            
            if notification_key not in notified_matches['over_potential']:
                
                # Coletar 0x0
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
                
                # Formatar mensagem
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
                
                confidence = "ALTÍSSIMA" if (home_from_under and away_from_under) else ("ALTA" if priority == "MÁXIMA" else "MÉDIA")
                
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
📈 <b>Over 1.5 histórico:</b> {league_info.get('over_15_percentage', 75)}%

🎯 <b>Sugestões:</b> 
• 🟢 Over 1.5 Gols
• 🟢 Over 0.5 Gols
• 🟢 BTTS

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
🆔 Fixture: {fixture_id}
"""
                
                await send_telegram_message(message)
                notified_matches['over_potential'].add(notification_key)
                
                logger.info(f"✅ Alerta enviado: {home_team} vs {away_team}")
                
                return {
                    'alert_sent': True,
                    'zero_zero_teams': zero_zero_teams,
                    'priority': priority
                }
        
        return {
            'alert_sent': False,
            'zero_zero_teams': zero_zero_teams
        }
        
    except Exception as e:
        logger.error(f"❌ Erro processando jogo: {e}")
        return {'alert_sent': False, 'zero_zero_teams': []}

# ========== DEBUG DE JOGOS FINALIZADOS ==========
async def debug_todays_finished_matches():
    """Debug de jogos finalizados hoje"""
    try:
        logger.info("🔍 DEBUG: Jogos finalizados hoje...")
        
        today_utc = datetime.now(pytz.utc).strftime('%Y-%m-%d')
        
        finished_matches = make_api_request("/fixtures", {
            "date": today_utc,
            "status": "FT"
        })
        
        logger.info(f"📊 {len(finished_matches)} jogos finalizados")
        
        zero_zero_count = 0
        under_15_count = 0
        
        for match in finished_matches:
            try:
                is_0x0 = is_exact_0x0_result(match)
                is_under = is_under_15_result(match)
                
                if is_0x0:
                    zero_zero_count += 1
                if is_under:
                    under_15_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Erro analisando jogo: {e}")
        
        await send_telegram_message(f"""
🔍 <b>DEBUG - JOGOS FINALIZADOS HOJE:</b>

📊 <b>Total:</b> {len(finished_matches)} jogos
🔥 <b>0x0:</b> {zero_zero_count}
🎯 <b>Under 1.5:</b> {under_15_count}

<i>Candidatos para alertas amanhã!</i>
""")
        
    except Exception as e:
        logger.error(f"❌ Erro no debug: {e}")

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal ultra robusto"""
    logger.info("🚀 Bot Regressão à Média ULTRA ROBUSTO Iniciado!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot ULTRA ROBUSTO Ativo!</b>\n\n"
        "🔥 <b>Correções Críticas:</b>\n"
        f"• {len(ALL_MONITORED_LEAGUES)} ligas monitoradas\n"
        "• Busca com múltiplos status (NS, LIVE, etc.)\n"
        "• Detecção ultra-sensível de 0x0\n"
        "• Histórico expandido (45 dias)\n\n"
        "🎯 <b>Foco:</b> Detectar equipes vindas de 0x0"
    )
    
    # Debug inicial
    await debug_todays_finished_matches()
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                logger.info(f"🔍 Monitoramento às {current_hour}h")
                
                await monitor_over_potential_games_ultra_robust()
                
                logger.info("✅ Ciclo concluído")
                await asyncio.sleep(1800)  # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro: {e}")
            await asyncio.sleep(600)  # 10 minutos

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot ULTRA ROBUSTO...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
