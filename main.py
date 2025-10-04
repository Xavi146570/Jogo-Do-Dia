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
            # UTC+1 (Para ter a hora certa em Lisboa no inverno, no verão é UTC+2)
            # Simplificação: assume UTC+1 para a maior parte do tempo de monitoramento
            return timezone(timedelta(hours=1)) 
        return timezone.utc

# --- Configuração de Log e Dependências ---
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

# Controle de notificações (Redefinido para o novo foco)
notified_matches = {
    'over_potential': set()
}

# --- Base de Dados Global (LEAGUE_STATS) ---
# A BASE DE DADOS GLOBAL PERMANECE A MESMA (Ligas com boa média de gols e baixo 0x0)
# Para este código focado em Over, ela é perfeita.
LEAGUE_STATS = {
    # EUROPA
    39: { "name": "Premier League", "country": "Inglaterra", "0x0_ft_percentage": 7, "over_15_percentage": 75, "over_25_percentage": 57, "goals_after_75min": 21, "first_half_goals": 46, "second_half_goals": 53, "0x0_ht_percentage": 26 },
    140: { "name": "La Liga", "country": "Espanha", "0x0_ft_percentage": 7, "over_15_percentage": 71, "over_25_percentage": 45, "goals_after_75min": 23.6, "first_half_goals": 45, "second_half_goals": 54, "0x0_ht_percentage": 34 },
    78: { "name": "Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 7, "over_15_percentage": 84, "over_25_percentage": 59, "goals_after_75min": 22, "first_half_goals": 45.6, "second_half_goals": 54.3, "0x0_ht_percentage": 25 },
    135: { "name": "Serie A", "country": "Itália", "0x0_ft_percentage": 7, "over_15_percentage": 78, "over_25_percentage": 53, "goals_after_75min": 22, "first_half_goals": 45, "second_half_goals": 55, "0x0_ht_percentage": 26.6 },
    94: { "name": "Primeira Liga", "country": "Portugal", "0x0_ft_percentage": 7, "over_15_percentage": 71, "over_25_percentage": 47, "goals_after_75min": 23, "first_half_goals": 45, "second_half_goals": 55, "0x0_ht_percentage": 30 },
    61: { "name": "Ligue 1", "country": "França", "0x0_ft_percentage": 7, "over_15_percentage": 77, "over_25_percentage": 53, "goals_after_75min": 22, "first_half_goals": 45, "second_half_goals": 55, "0x0_ht_percentage": 26 },
    88: { "name": "Eredivisie", "country": "Holanda", "0x0_ft_percentage": 7, "over_15_percentage": 82, "over_25_percentage": 65, "goals_after_75min": 24, "first_half_goals": 44, "second_half_goals": 56, "0x0_ht_percentage": 24 },
    144: { "name": "Jupiler Pro League", "country": "Bélgica", "0x0_ft_percentage": 7, "over_15_percentage": 81, "over_25_percentage": 57, "goals_after_75min": 24, "first_half_goals": 43, "second_half_goals": 57, "0x0_ht_percentage": 25 },
    203: { "name": "Süper Lig", "country": "Turquia", "0x0_ft_percentage": 7, "over_15_percentage": 77.6, "over_25_percentage": 55, "goals_after_75min": 23, "first_half_goals": 45, "second_half_goals": 55, "0x0_ht_percentage": 27 },
    # AMÉRICA DO SUL
    325: { "name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85, "over_25_percentage": 62, "goals_after_75min": 26, "first_half_goals": 44, "second_half_goals": 56, "0x0_ht_percentage": 22 },
    128: { "name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82, "over_25_percentage": 58, "goals_after_75min": 25, "first_half_goals": 43, "second_half_goals": 57, "0x0_ht_percentage": 24 },
    # AMÉRICA DO NORTE
    253: { "name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88, "over_25_percentage": 65, "goals_after_75min": 28, "first_half_goals": 42, "second_half_goals": 58, "0x0_ht_percentage": 21 },
    262: { "name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84, "over_25_percentage": 61, "goals_after_75min": 27, "first_half_goals": 43, "second_half_goals": 57, "0x0_ht_percentage": 23 },
    # ÁSIA-OCEANIA
    188: { "name": "J1 League", "country": "Japão", "0x0_ft_percentage": 7, "over_15_percentage": 79, "over_25_percentage": 54, "goals_after_75min": 24, "first_half_goals": 46, "second_half_goals": 54, "0x0_ht_percentage": 26 },
    292: { "name": "A-League", "country": "Austrália", "0x0_ft_percentage": 6, "over_15_percentage": 83, "over_25_percentage": 59, "goals_after_75min": 26, "first_half_goals": 44, "second_half_goals": 56, "0x0_ht_percentage": 24 }
}

TOP_LEAGUES = set(LEAGUE_STATS.keys())

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
            # Aumentando timeout para APIs externas
            response = requests.get(url, headers=HEADERS, params=params, timeout=15) 
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            logger.warning(f"API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(5) # Aumentando o tempo de espera entre retries
    
    return []

def get_current_hour_lisbon():
    """Retorna hora atual em Lisboa"""
    return datetime.now(ZoneInfo("Europe/Lisbon")).hour

def should_run_monitoring():
    """Verifica se deve monitorar (09h às 23h, ajustado para cobrir a maior parte dos jogos globais)"""
    # Mantém o horário 09h às 23h de Lisboa
    return 9 <= get_current_hour_lisbon() <= 23

def get_league_intelligence(league_id):
    """Retorna análise da liga"""
    if league_id not in LEAGUE_STATS:
        return None
    
    stats = LEAGUE_STATS[league_id]
    return {
        'league_name': stats['name'],
        'country': stats['country'],
        'over_under': {
            'over_15_pct': stats['over_15_percentage'],
            'over_25_pct': stats['over_25_percentage'],
            'over_15_odd': round(100 / stats['over_15_percentage'], 2),
            'over_25_odd': round(100 / stats['over_25_percentage'], 2)
        },
        'goals_timing': {
            'after_75min_pct': stats['goals_after_75min']
        }
    }

# =========================================================
# ANÁLISE DE REGRESSÃO À MÉDIA (FOCO: OVER GOLS)
# =========================================================

async def get_team_recent_matches(team_id, limit=5):
    """Obtém últimos 5 jogos de uma equipe (limite aumentado para 5)"""
    try:
        return make_api_request("/fixtures", {
            "team": team_id, "last": limit, "status": "FT"
        })
    except Exception as e:
        logger.error(f"Erro histórico equipe {team_id}: {e}")
        return []

def is_under_15_result(match):
    """Verifica se o resultado final foi 0x0 ou 1x0/0x1 (Under 1.5)"""
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    
    # Critério: 0x0, 1x0, ou 0x1
    return total_goals < 2

async def check_team_coming_from_under_15(team_id):
    """Verifica se equipe vem de um resultado Under 1.5"""
    # Apenas verifica o último jogo (last=1)
    recent_matches = await get_team_recent_matches(team_id, limit=1) 
    
    if not recent_matches:
        return False, None
    
    last_match = recent_matches[0]
    
    if is_under_15_result(last_match):
        home_goals = last_match['goals']['home'] or 0
        away_goals = last_match['goals']['away'] or 0
        score = f"{home_goals} x {away_goals}"
        
        # Identifica o adversário do último jogo
        opponent = (last_match['teams']['away']['name'] 
                    if last_match['teams']['home']['id'] == team_id 
                    else last_match['teams']['home']['name'])
        
        match_date = datetime.fromisoformat(last_match['fixture']['date'].replace('Z', '+00:00'))
        
        return True, {
            'opponent': opponent,
            'score': score,
            'date': match_date.strftime('%d/%m')
        }
        
    return False, None

async def analyze_over_potential(match):
    """Analisa potencial Over Gols (Regressão à Média)"""
    home_team_id = match['teams']['home']['id']
    away_team_id = match['teams']['away']['id']
    
    # Verifica o último jogo de cada equipe
    home_from_under_15, home_info = await check_team_coming_from_under_15(home_team_id)
    away_from_under_15, away_info = await check_team_coming_from_under_15(away_team_id)
    
    # O potencial Over é alto se UMA ou AMBAS vierem de um Under 1.5
    over_potential = home_from_under_15 or away_from_under_15
    
    return {
        'home_from_under_15': home_from_under_15,
        'away_from_under_15': away_from_under_15,
        'home_info': home_info,
        'away_info': away_info,
        'over_potential': over_potential
    }

# =========================================================
# MONITORAMENTO PRINCIPAL
# =========================================================

# (O código anterior tinha um ')' aqui. Ele deve ser REMOVIDO.)

async def monitor_over_potential_games():
    """Monitora jogos futuros com alto potencial de Over Gols"""
    logger.info("🔍 Verificando equipes vindas de Under 1.5 (Regressão à Média)...")
    # ... (o restante da função segue normalmente)
    
    try:
        # AGORA SEM LIMITE DE DATA E SEM LIMITE DE ARRAY
        # Isso garante que a API retorne TODOS os jogos NS, e o loop processa TODOS eles.
        upcoming_matches = make_api_request("/fixtures", {
            "status": "NS" 
        })
        
        logger.info(f"Encontrados {len(upcoming_matches)} jogos futuros 'Not Started'.")
        
        # Processa TODOS os jogos futuros retornados pela API
        for match in upcoming_matches:
            await process_upcoming_match_over_analysis(match)
            
    except Exception as e:
        logger.error(f"Erro monitoramento Over: {e}")

# ... (restante do código)
async def process_upcoming_match_over_analysis(match):
    """Processa jogo futuro com foco em Over Gols"""
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']
    
    if league_id not in TOP_LEAGUES:
        return
    
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    
    league_intel = get_league_intelligence(league_id)
    if not league_intel:
        return
    
    # Análise de Regressão à Média (Over Gols)
    over_analysis = await analyze_over_potential(match)
    
    if over_analysis['over_potential']:
        notification_key = f"over_potential_{fixture_id}"
        
        if notification_key not in notified_matches['over_potential']:
            
            match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
            
            teams_info = ""
            if over_analysis['home_from_under_15']:
                info = over_analysis['home_info']
                teams_info += f"🏠 <b>{home_team}</b> vem de <b>{info['score']}</b> vs {info['opponent']} ({info['date']})\n"
            
            if over_analysis['away_from_under_15']:
                info = over_analysis['away_info']
                teams_info += f"✈️ <b>{away_team}</b> vem de <b>{info['score']}</b> vs {info['opponent']} ({info['date']})\n"
            
            message = f"""
🔥 <b>ALERTA OVER GOLS - REGRESSÃO À MÉDIA</b> 🔥

🏆 <b>{league_intel['league_name']} ({league_intel['country']})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Análise da Liga:</b>
• Over 1.5 da liga: {league_intel['over_under']['over_15_pct']}%
• Over 2.5 da liga: {league_intel['over_under']['over_25_pct']}%
• % Gols Após 75': {league_intel['goals_timing']['after_75min_pct']}%

💡 <b>Insight:</b> Equipe(s) vem de resultado de 'seca' de gols. Alta probabilidade de Regressão à Média para o Over!

🎯 <b>Sugestões:</b>
• 🟢 **Over 1.5 Gols** (Odd Esperada: ~{league_intel['over_under']['over_15_odd']})
• 🟢 **Over 2.5 Gols** (Odd Esperada: ~{league_intel['over_under']['over_25_odd']})

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
"""
            
            await send_telegram_message(message)
            notified_matches['over_potential'].add(notification_key)


# =========================================================
# LOOP PRINCIPAL (Simplificado - Foco Apenas em Pré-Jogo/Over)
# =========================================================

async def main_loop():
    """Loop principal do bot"""
    logger.info("🚀 Bot Regressão à Média (Over Gols) Iniciado!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot de Regressão à Média (Over Gols) Ativo!</b>\n\n"
        "🧠 <b>Foco:</b> Detectar jogos onde equipes vêm de resultados 0x0 ou Under 1.5, sugerindo Over Gols.\n"
        f"🌍 Cobertura: {len(TOP_LEAGUES)} ligas de elite globais (Alto % de Over)."
    )
    
    while True:
        try:
            current_hour = get_current_hour_lisbon()
            
            if should_run_monitoring():
                logger.info(f"🧠 Monitoramento às {current_hour}h")
                
                # Executa APENAS o monitoramento Over/Pré-Jogo
                await monitor_over_potential_games() 
                
                logger.info("✅ Ciclo concluído")
                await asyncio.sleep(1800) # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600) # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro detectado: {e}")
            await asyncio.sleep(600)

# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Regressão à Média (Over Gols)...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
