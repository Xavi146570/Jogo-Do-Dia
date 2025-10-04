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
    'debug_matches': set()  # Para debug
}

# ========== CORREÇÃO 1: LIGAS EXPANDIDAS ==========
# Expandindo significativamente a lista de ligas monitoradas
LEAGUE_STATS = {
    # EUROPA - PRINCIPAIS
    39: {"name": "Premier League", "country": "Inglaterra", "0x0_ft_percentage": 7, "over_15_percentage": 75},
    140: {"name": "La Liga", "country": "Espanha", "0x0_ft_percentage": 7, "over_15_percentage": 71},
    78: {"name": "Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 7, "over_15_percentage": 84},
    135: {"name": "Serie A", "country": "Itália", "0x0_ft_percentage": 7, "over_15_percentage": 78},
    61: {"name": "Ligue 1", "country": "França", "0x0_ft_percentage": 7, "over_15_percentage": 77},
    94: {"name": "Primeira Liga", "country": "Portugal", "0x0_ft_percentage": 7, "over_15_percentage": 71},
    88: {"name": "Eredivisie", "country": "Holanda", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    144: {"name": "Jupiler Pro League", "country": "Bélgica", "0x0_ft_percentage": 7, "over_15_percentage": 81},
    203: {"name": "Süper Lig", "country": "Turquia", "0x0_ft_percentage": 7, "over_15_percentage": 77},
    
    # EUROPA - SECUNDÁRIAS (ADICIONADAS)
    40: {"name": "Championship", "country": "Inglaterra", "0x0_ft_percentage": 9, "over_15_percentage": 72},
    41: {"name": "League One", "country": "Inglaterra", "0x0_ft_percentage": 10, "over_15_percentage": 70},
    179: {"name": "2. Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    136: {"name": "Serie B", "country": "Itália", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    141: {"name": "Segunda División", "country": "Espanha", "0x0_ft_percentage": 8, "over_15_percentage": 73},
    62: {"name": "Ligue 2", "country": "França", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    
    # AMÉRICA DO SUL
    325: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85},
    128: {"name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    218: {"name": "Primera División", "country": "Chile", "0x0_ft_percentage": 8, "over_15_percentage": 78},
    
    # AMÉRICA DO NORTE
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84},
    
    # ÁSIA-OCEANIA
    188: {"name": "J1 League", "country": "Japão", "0x0_ft_percentage": 7, "over_15_percentage": 79},
    292: {"name": "A-League", "country": "Austrália", "0x0_ft_percentage": 6, "over_15_percentage": 83},
    
    # OUTRAS LIGAS RELEVANTES (ADICIONADAS)
    204: {"name": "1. Lig", "country": "Turquia", "0x0_ft_percentage": 9, "over_15_percentage": 74},
    119: {"name": "Superliga", "country": "Dinamarca", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    113: {"name": "Allsvenskan", "country": "Suécia", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    103: {"name": "Eliteserien", "country": "Noruega", "0x0_ft_percentage": 8, "over_15_percentage": 77},
}

TOP_LEAGUES = set(LEAGUE_STATS.keys())
logger.info(f"📊 Monitorando {len(TOP_LEAGUES)} ligas")

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

# ========== CORREÇÃO 2: BUSCA MELHORADA DE HISTÓRICO ==========
async def get_team_recent_matches_robust(team_id, team_name, limit=5):
    """Versão robusta para buscar histórico da equipe"""
    try:
        logger.info(f"📊 Buscando últimos {limit} jogos de {team_name} (ID: {team_id})")
        
        # Tentar busca padrão
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches:
            logger.info(f"✅ Encontrados {len(matches)} jogos finalizados para {team_name}")
            return matches
        
        # ========== CORREÇÃO 3: FALLBACK COM RANGE DE DATAS ==========
        # Se não encontrar com "last", tenta com range de datas
        logger.warning(f"⚠️ Tentativa fallback para {team_name} com range de datas")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=30)  # Últimos 30 dias
        
        matches_fallback = make_api_request("/fixtures", {
            "team": team_id,
            "from": start_date.strftime('%Y-%m-%d'),
            "to": end_date.strftime('%Y-%m-%d'),
            "status": "FT"
        })
        
        if matches_fallback:
            # Pegar os últimos jogos manualmente
            sorted_matches = sorted(matches_fallback, 
                                  key=lambda x: x['fixture']['date'], 
                                  reverse=True)[:limit]
            logger.info(f"✅ Fallback encontrou {len(sorted_matches)} jogos para {team_name}")
            return sorted_matches
        
        logger.error(f"❌ Nenhum jogo encontrado para {team_name}")
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== CORREÇÃO 4: DETECÇÃO MELHORADA DE 0x0 ==========
def is_under_15_result(match):
    """Verifica se resultado foi Under 1.5 (incluindo 0x0)"""
    try:
        home_goals = match['goals']['home'] if match['goals']['home'] is not None else 0
        away_goals = match['goals']['away'] if match['goals']['away'] is not None else 0
        total_goals = home_goals + away_goals
        
        logger.debug(f"🔍 Jogo: {home_goals}x{away_goals} = {total_goals} gols")
        return total_goals < 2  # 0x0, 1x0, 0x1
        
    except Exception as e:
        logger.error(f"❌ Erro verificando resultado: {e}")
        return False

async def check_team_coming_from_under_15_robust(team_id, team_name):
    """Versão robusta para verificar se equipe vem de Under 1.5"""
    try:
        # Buscar últimos jogos
        recent_matches = await get_team_recent_matches_robust(team_id, team_name, limit=3)
        
        if not recent_matches:
            logger.warning(f"⚠️ Nenhum jogo recente encontrado para {team_name}")
            return False, None
        
        # Verificar cada jogo recente
        for i, match in enumerate(recent_matches):
            if is_under_15_result(match):
                home_goals = match['goals']['home'] if match['goals']['home'] is not None else 0
                away_goals = match['goals']['away'] if match['goals']['away'] is not None else 0
                score = f"{home_goals}x{away_goals}"
                
                # Identificar adversário
                opponent = (match['teams']['away']['name'] 
                           if match['teams']['home']['id'] == team_id 
                           else match['teams']['home']['name'])
                
                match_date = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                
                logger.info(f"🎯 {team_name} vem de Under 1.5: {score} vs {opponent}")
                
                return True, {
                    'opponent': opponent,
                    'score': score,
                    'date': match_date.strftime('%d/%m'),
                    'days_ago': i + 1
                }
        
        logger.info(f"✅ {team_name} não vem de Under 1.5")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando Under 1.5 para {team_name}: {e}")
        return False, None

# ========== CORREÇÃO 5: MONITORAMENTO EXPANDIDO ==========
async def monitor_over_potential_games_robust():
    """Versão robusta do monitoramento"""
    logger.info("🔍 MONITORAMENTO ROBUSTO - Verificando regressão à média...")
    
    try:
        # ========== BUSCA EXPANDIDA DE JOGOS ==========
        utc_zone = pytz.utc
        now_utc = datetime.now(utc_zone)
        
        # Buscar jogos de hoje, amanhã E ontem (para debug)
        yesterday_utc = (now_utc - timedelta(days=1)).strftime('%Y-%m-%d')
        today_utc = now_utc.strftime('%Y-%m-%d')
        tomorrow_utc = (now_utc + timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"📅 Buscando jogos: {yesterday_utc} a {tomorrow_utc}")
        
        # Buscar jogos futuros (NS) e em andamento (LIVE)
        upcoming_matches = make_api_request("/fixtures", {
            "from": today_utc,
            "to": tomorrow_utc,
            "status": "NS-1H-2H-HT-ET-BT-P-SUSP-INT"  # Múltiplos status
        })
        
        logger.info(f"📊 Encontrados {len(upcoming_matches)} jogos para análise")
        
        # Analisar cada jogo
        analyzed_count = 0
        alerts_sent = 0
        
        for match in upcoming_matches:
            try:
                league_id = match['league']['id']
                
                # ========== CORREÇÃO: ANÁLISE MESMO SE NÃO FOR TOP LEAGUE ==========
                if league_id not in TOP_LEAGUES:
                    # Log para debug, mas continua analisando
                    logger.debug(f"🔍 Liga {match['league']['name']} não é TOP, mas analisando...")
                
                result = await process_upcoming_match_over_analysis_robust(match)
                analyzed_count += 1
                
                if result:
                    alerts_sent += 1
                    
            except Exception as e:
                logger.error(f"❌ Erro processando jogo: {e}")
                continue
        
        logger.info(f"✅ Análise concluída: {analyzed_count} jogos analisados, {alerts_sent} alertas enviados")
        
        # Debug: Se nenhum jogo foi encontrado
        if analyzed_count == 0:
            await send_telegram_message(
                "🐛 <b>DEBUG:</b> Nenhum jogo encontrado para análise.\n"
                f"Período: {today_utc} a {tomorrow_utc}\n"
                f"Total ligas monitoradas: {len(TOP_LEAGUES)}"
            )
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento robusto: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento: {e}")

async def process_upcoming_match_over_analysis_robust(match):
    """Processa jogo com análise robusta"""
    try:
        league_id = match['league']['id']
        fixture_id = match['fixture']['id']
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        home_team_id = match['teams']['home']['id']
        away_team_id = match['teams']['away']['id']
        
        logger.info(f"🔍 Analisando: {home_team} vs {away_team}")
        
        # Análise de regressão para ambas as equipes
        home_from_under, home_info = await check_team_coming_from_under_15_robust(home_team_id, home_team)
        away_from_under, away_info = await check_team_coming_from_under_15_robust(away_team_id, away_team)
        
        # Se pelo menos uma equipe vem de Under 1.5
        if home_from_under or away_from_under:
            
            notification_key = f"over_potential_{fixture_id}"
            
            if notification_key not in notified_matches['over_potential']:
                
                # Formatar informações
                match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
                
                teams_info = ""
                if home_from_under:
                    info = home_info
                    teams_info += f"🏠 <b>{home_team}</b> vem de <b>{info['score']}</b> vs {info['opponent']} ({info['date']}) - {info['days_ago']} jogo(s) atrás\n"
                
                if away_from_under:
                    info = away_info
                    teams_info += f"✈️ <b>{away_team}</b> vem de <b>{info['score']}</b> vs {info['opponent']} ({info['date']}) - {info['days_ago']} jogo(s) atrás\n"
                
                # Info da liga
                league_info = LEAGUE_STATS.get(league_id, {
                    "name": match['league']['name'],
                    "country": match['league']['country'],
                    "over_15_percentage": 75  # Default
                })
                
                confidence = "ALTA" if (home_from_under and away_from_under) else "MÉDIA"
                
                message = f"""
🔥 <b>ALERTA REGRESSÃO À MÉDIA - CONFIANÇA {confidence}</b> 🔥

🏆 <b>{league_info['name']} ({league_info.get('country', 'N/A')})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Análise da Liga:</b>
• Over 1.5 histórico: {league_info.get('over_15_percentage', 75)}%

💡 <b>Método:</b> Equipe(s) vem de "seca de gols" - Alta probabilidade de regressão à média!

🎯 <b>Sugestão:</b> 
• 🟢 Over 1.5 Gols (Recomendado)
• 🟢 Over 0.5 Gols (Conservador)

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
🆔 Fixture: {fixture_id}
"""
                
                await send_telegram_message(message)
                notified_matches['over_potential'].add(notification_key)
                
                logger.info(f"✅ Alerta enviado para {home_team} vs {away_team}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro processando jogo {match.get('fixture', {}).get('id', 'N/A')}: {e}")
        return False

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal do bot"""
    logger.info("🚀 Bot Regressão à Média ROBUSTO Iniciado!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot Regressão à Média ROBUSTO Ativo!</b>\n\n"
        "🧠 <b>Melhorias:</b>\n"
        f"• {len(TOP_LEAGUES)} ligas monitoradas\n"
        "• Busca robusta com fallbacks\n"
        "• Detecção melhorada de 0x0\n"
        "• Análise expandida de histórico\n\n"
        "🎯 <b>Foco:</b> Equipes vindas de Under 1.5 (regressão à média)"
    )
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:  # Horário expandido
                logger.info(f"🔍 Monitoramento robusto às {current_hour}h")
                
                await monitor_over_potential_games_robust()
                
                logger.info("✅ Ciclo robusto concluído")
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
    logger.info("🚀 Iniciando Bot Regressão à Média ROBUSTO...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
