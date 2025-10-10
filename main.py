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

# Configuração - MANTIDO 10 DIAS para análise da rodada anterior
MAX_LAST_MATCH_AGE_DAYS = int(os.environ.get("MAX_LAST_MATCH_AGE_DAYS", "10"))

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
notified_matches = set()

# ========== LIGAS PRINCIPAIS VALIDADAS COM ESTATÍSTICAS REAIS ==========
TOP_LEAGUES_ONLY = {
    # EUROPA - TIER 1
    39: {"name": "Premier League", "country": "Inglaterra", "0x0_ft_percentage": 26, "over_15_percentage": 89, "tier": 1},
    140: {"name": "La Liga", "country": "Espanha", "0x0_ft_percentage": 23, "over_15_percentage": 78, "tier": 1},
    78: {"name": "Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 19, "over_15_percentage": 85, "tier": 1},
    135: {"name": "Serie A", "country": "Itália", "0x0_ft_percentage": 25, "over_15_percentage": 81, "tier": 1},
    61: {"name": "Ligue 1", "country": "França", "0x0_ft_percentage": 21, "over_15_percentage": 76, "tier": 1},
    94: {"name": "Liga NOS", "country": "Portugal", "0x0_ft_percentage": 27, "over_15_percentage": 83, "tier": 1},
    88: {"name": "Eredivisie", "country": "Holanda", "0x0_ft_percentage": 27, "over_15_percentage": 88, "tier": 1},
    144: {"name": "Pro League", "country": "Bélgica", "0x0_ft_percentage": 24, "over_15_percentage": 80, "tier": 1},
    203: {"name": "Süper Lig", "country": "Turquia", "0x0_ft_percentage": 23, "over_15_percentage": 76, "tier": 1},
    
    # EUROPA - TIER 2
    40: {"name": "Championship", "country": "Inglaterra", "0x0_ft_percentage": 25, "over_15_percentage": 82, "tier": 2},
    179: {"name": "2. Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 20, "over_15_percentage": 86, "tier": 2},
    136: {"name": "Serie B", "country": "Itália", "0x0_ft_percentage": 26, "over_15_percentage": 79, "tier": 2},
    141: {"name": "Segunda División", "country": "Espanha", "0x0_ft_percentage": 21, "over_15_percentage": 75, "tier": 2},
    62: {"name": "Ligue 2", "country": "França", "0x0_ft_percentage": 24, "over_15_percentage": 72, "tier": 2},
    
    # AMERICA DO SUL
    71: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 22, "over_15_percentage": 79, "tier": 1},
    128: {"name": "Liga Profesional", "country": "Argentina", "0x0_ft_percentage": 21, "over_15_percentage": 82, "tier": 1},
    
    # AMERICA DO NORTE
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 16, "over_15_percentage": 88, "tier": 1},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 22, "over_15_percentage": 79, "tier": 1},
}

ALLOWED_LEAGUES = set(TOP_LEAGUES_ONLY.keys())
logger.info(f"📊 Monitorando {len(ALLOWED_LEAGUES)} ligas validadas - Janela rodada anterior: {MAX_LAST_MATCH_AGE_DAYS} dias")

# ========== FUNÇÕES UTILITÁRIAS ==========
async def send_telegram_message(message):
    """Envia mensagem para o Telegram"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        logger.info("✅ Mensagem enviada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")

def make_api_request(endpoint, params=None, retries=3):
    """Faz requisição para a API com retry"""
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=20) 
            response.raise_for_status()
            data = response.json()
            result = data.get("response", [])
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("⏳ Rate limit atingido, aguardando 60s...")
                time.sleep(60)
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {e}")
                break
        except Exception as e:
            logger.warning(f"❌ API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
    
    return []

# ========== BUSCA APENAS JOGOS DE HOJE ==========
async def get_todays_matches_only():
    """Busca APENAS jogos de hoje com validação"""
    lisbon_tz = ZoneInfo("Europe/Lisbon")
    today_lisbon = datetime.now(lisbon_tz).date()
    today_utc_str = datetime.now(pytz.utc).strftime('%Y-%m-%d')
    
    todays_matches_raw = make_api_request("/fixtures", {
        "date": today_utc_str,
        "status": "NS"
    })
    
    if not todays_matches_raw:
        return []
    
    # Filtrar por ligas permitidas
    league_filtered = [
        match for match in todays_matches_raw 
        if match.get('league', {}).get('id') in ALLOWED_LEAGUES
    ]
    
    # Validar data é hoje em Lisboa
    final_matches = []
    for match in league_filtered:
        try:
            raw_date = match['fixture']['date']
            match_datetime_utc = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
            match_date_lisbon = match_datetime_utc.astimezone(lisbon_tz).date()
            
            if match_date_lisbon == today_lisbon:
                final_matches.append(match)
        except Exception as e:
            logger.error(f"❌ Erro validando jogo: {e}")
    
    return final_matches

# ========== VALIDAÇÃO DE LIGA (APENAS POR ID) ==========
def validate_league_consistency(league_id, api_league_name):
    """Valida se o ID da liga está na lista permitida"""
    if league_id in ALLOWED_LEAGUES:
        return True, f"Liga válida: ID {league_id}"
    return False, f"Liga ID {league_id} não permitida"

# ========== HISTÓRICO DE EQUIPAS ==========
async def get_team_recent_matches_validated(team_id, team_name, limit=5):
    """Busca histórico recente da equipa"""
    try:
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 1:
            return matches
        
        # Fallback por data
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=21)
        
        matches_fallback = make_api_request("/fixtures", {
            "team": team_id,
            "from": start_date.strftime('%Y-%m-%d'),
            "to": end_date.strftime('%Y-%m-%d'),
            "status": "FT"
        })
        
        if matches_fallback:
            return sorted(matches_fallback, key=lambda x: x['fixture']['date'], reverse=True)[:limit]
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== DETECÇÃO DE RESULTADOS ==========
def is_exact_0x0_result(match):
    """Detecta especificamente 0x0"""
    try:
        goals = match.get('goals', {})
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        return (home_goals == 0 and away_goals == 0)
    except Exception:
        return False

def is_under_15_result(match):
    """Detecta Under 1.5"""
    try:
        goals = match.get('goals', {})
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        return (home_goals + away_goals) < 2
    except Exception:
        return False

async def check_team_coming_from_under_15_validated(team_id, team_name, current_league_id=None):
    """Verifica se equipa vem de Under 1.5/0x0 na rodada anterior"""
    try:
        recent_matches = await get_team_recent_matches_validated(team_id, team_name, limit=5)
        
        if not recent_matches:
            return False, None
        
        # Usar o jogo mais recente
        last_match = recent_matches[0]
        
        is_zero_zero = is_exact_0x0_result(last_match)
        is_under_15 = is_under_15_result(last_match)
        
        if is_under_15:
            goals = last_match.get('goals', {})
            home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
            away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
            score = f"{home_goals}x{away_goals}"
            
            opponent = (last_match['teams']['away']['name'] 
                       if last_match['teams']['home']['id'] == team_id 
                       else last_match['teams']['home']['name'])
            
            match_date = datetime.fromisoformat(last_match['fixture']['date'].replace('Z', '+00:00'))
            days_ago = (datetime.now(pytz.utc) - match_date).days
            
            if days_ago > MAX_LAST_MATCH_AGE_DAYS:
                return False, None
            
            return True, {
                'opponent': opponent,
                'score': score,
                'date': match_date.strftime('%d/%m'),
                'is_0x0': is_zero_zero,
                'days_ago': days_ago,
                'league_name': last_match.get('league', {}).get('name', 'N/A')
            }
        
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando {team_name}: {e}")
        return False, None

# ========== MONITORAMENTO SILENCIOSO ==========
async def monitor_todays_games():
    """Monitoramento silencioso - apenas alertas relevantes"""
    try:
        todays_matches = await get_todays_matches_only()
        
        if not todays_matches:
            return  # Sem mensagem no Telegram
        
        lisbon_tz = ZoneInfo("Europe/Lisbon")
        current_lisbon_date = datetime.now(lisbon_tz).date()
        
        for match in todays_matches:
            try:
                fixture_id = match['fixture']['id']
                home_team = match['teams']['home']['name']
                away_team = match['teams']['away']['name']
                home_team_id = match['teams']['home']['id']
                away_team_id = match['teams']['away']['id']
                league_name = match['league']['name']
                league_id = match['league']['id']
                
                # Validação de liga (apenas por ID)
                is_valid_league, _ = validate_league_consistency(league_id, league_name)
                if not is_valid_league:
                    continue
                
                # Validação de data
                match_datetime_utc = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                match_date_lisbon = match_datetime_utc.astimezone(lisbon_tz).date()
                
                if match_date_lisbon != current_lisbon_date:
                    continue
                
                # Validação de horário
                match_time_lisbon = match_datetime_utc.astimezone(lisbon_tz)
                now_lisbon = datetime.now(lisbon_tz)
                
                if match_time_lisbon < now_lisbon - timedelta(minutes=30):
                    continue
                
                # Verificar rodada anterior
                home_from_under, home_info = await check_team_coming_from_under_15_validated(
                    home_team_id, home_team, league_id)
                away_from_under, away_info = await check_team_coming_from_under_15_validated(
                    away_team_id, away_team, league_id)
                
                if home_from_under or away_from_under:
                    notification_key = f"today_{current_lisbon_date}_{fixture_id}"
                    
                    if notification_key not in notified_matches:
                        
                        # Formatar alerta
                        teams_info = ""
                        priority = "NORMAL"
                        
                        if home_from_under and home_info:
                            indicator = "🔥 0x0" if home_info.get('is_0x0') else f"Under 1.5 ({home_info['score']})"
                            teams_info += f"🏠 <b>{home_team}</b> vem de <b>{indicator}</b> vs {home_info['opponent']} ({home_info['date']} - {home_info['days_ago']}d)\n"
                            if home_info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        if away_from_under and away_info:
                            indicator = "🔥 0x0" if away_info.get('is_0x0') else f"Under 1.5 ({away_info['score']})"
                            teams_info += f"✈️ <b>{away_team}</b> vem de <b>{indicator}</b> vs {away_info['opponent']} ({away_info['date']} - {away_info['days_ago']}d)\n"
                            if away_info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        confidence = "ALTÍSSIMA" if (home_from_under and away_from_under) else ("ALTA" if priority == "MÁXIMA" else "MÉDIA")
                        
                        league_info = TOP_LEAGUES_ONLY[league_id]
                        tier_indicator = "⭐" * league_info['tier']
                        
                        message = f"""🚨 <b>ALERTA REGRESSÃO À MÉDIA - PRIORIDADE {priority}</b>

🏆 <b>{league_info['name']} ({league_info['country']}) {tier_indicator}</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Confiança:</b> {confidence}
📈 <b>Over 1.5 histórico da liga:</b> {league_info['over_15_percentage']}%
📉 <b>0x0 histórico da liga:</b> {league_info['0x0_ft_percentage']}%

💡 <b>Teoria:</b> Regressão à média após seca de gols na rodada anterior

🎯 <b>Sugestões:</b> 
• 🟢 Over 1.5 Gols (Principal)
• 🟢 Over 0.5 Gols (Conservador)
• 🟢 BTTS (Ambas marcam)

🕐 <b>HOJE às {match_time_lisbon.strftime('%H:%M')}</b>
📅 <b>{current_lisbon_date.strftime('%d/%m/%Y')}</b>
🆔 Fixture ID: {fixture_id}"""
                        
                        await send_telegram_message(message)
                        notified_matches.add(notification_key)
                        logger.info(f"✅ Alerta enviado: {home_team} vs {away_team}")
                
            except Exception as e:
                logger.error(f"❌ Erro analisando jogo: {e}")
                continue
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento: {e}")

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal silencioso"""
    logger.info("🚀 Bot Regressão à Média - MODO SILENCIOSO!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                await monitor_todays_games()
                await asyncio.sleep(1800)  # 30 minutos
            else:
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro no loop: {e}")
            await asyncio.sleep(600)

if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Silencioso...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
