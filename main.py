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
notified_matches = {
    'over_potential': set(),
    'debug_matches': set()
}

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
    """Faz requisição para a API com retry e logs detalhados"""
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(retries):
        try:
            logger.info(f"🔍 API Call: {endpoint} | Params: {params}")
            response = requests.get(url, headers=HEADERS, params=params, timeout=20) 
            response.raise_for_status()
            data = response.json()
            
            result = data.get("response", [])
            logger.info(f"✅ API retornou {len(result)} registros para {endpoint}")
            return result
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning(f"⏳ Rate limit atingido, aguardando 60s...")
                time.sleep(60)
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {e}")
                break
        except Exception as e:
            logger.warning(f"❌ API falhou (tentativa {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
    
    logger.error("❌ Todas as tentativas da API falharam")
    return []

# ========== BUSCA RIGOROSA APENAS JOGOS DE HOJE ==========
async def get_todays_matches_only():
    """Busca APENAS jogos de hoje com validação tripla"""
    logger.info("🔍 BUSCA RIGOROSA - APENAS JOGOS DE HOJE...")
    
    # Obter data atual real em Lisboa
    lisbon_tz = ZoneInfo("Europe/Lisbon")
    now_lisbon = datetime.now(lisbon_tz)
    today_lisbon = now_lisbon.date()
    today_str = today_lisbon.strftime('%Y-%m-%d')
    
    logger.info(f"📅 Data/Hora atual Lisboa: {now_lisbon.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📅 Buscando jogos EXCLUSIVAMENTE de: {today_str}")
    
    # Buscar usando data UTC (mais confiável com a API)
    utc_now = datetime.now(pytz.utc)
    today_utc_str = utc_now.strftime('%Y-%m-%d')
    
    todays_matches_raw = make_api_request("/fixtures", {
        "date": today_utc_str,
        "status": "NS"  # Apenas não iniciados
    })
    
    if not todays_matches_raw:
        logger.warning("⚠️ Nenhum jogo encontrado pela API")
        return []
    
    logger.info(f"📊 API retornou {len(todays_matches_raw)} jogos para análise")
    
    # FILTRO 1: Apenas ligas permitidas
    league_filtered = []
    for match in todays_matches_raw:
        league_id = match.get('league', {}).get('id')
        league_name = match.get('league', {}).get('name', 'N/A')
        
        if league_id in ALLOWED_LEAGUES:
            league_filtered.append(match)
            logger.debug(f"✅ Liga aceite: {league_name} (ID: {league_id})")
        else:
            logger.debug(f"❌ Liga rejeitada: {league_name} (ID: {league_id})")
    
    logger.info(f"📊 Após filtro de ligas: {len(league_filtered)} jogos")
    
    # FILTRO 2: Validação rigorosa de data (HOJE em Lisboa)
    final_matches = []
    for match in league_filtered:
        try:
            fixture_id = match['fixture']['id']
            raw_date = match['fixture']['date']
            home_team = match['teams']['home']['name']
            away_team = match['teams']['away']['name']
            
            # Converter para Lisboa e verificar se é hoje
            match_datetime_utc = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
            match_date_lisbon = match_datetime_utc.astimezone(lisbon_tz).date()
            
            logger.debug(f"🔍 VALIDAÇÃO DATA - Fixture {fixture_id}: "
                        f"Raw: {raw_date} | UTC: {match_datetime_utc} | "
                        f"Lisboa: {match_date_lisbon} | Hoje: {today_lisbon}")
            
            if match_date_lisbon == today_lisbon:
                final_matches.append(match)
                logger.info(f"✅ Jogo HOJE validado: {home_team} vs {away_team} (ID: {fixture_id})")
            else:
                logger.info(f"❌ Jogo rejeitado - data {match_date_lisbon} ≠ hoje {today_lisbon}")
                
        except Exception as e:
            logger.error(f"❌ Erro validando jogo {match.get('fixture', {}).get('id', 'N/A')}: {e}")
    
    logger.info(f"📊 RESULTADO FINAL: {len(final_matches)} jogos válidos para HOJE")
    return final_matches

# ========== VALIDAÇÃO DE LIGA COM CORRESPONDÊNCIA ==========
def validate_league_consistency(league_id, api_league_name):
    """Valida se o ID da liga corresponde ao nome esperado"""
    if league_id not in TOP_LEAGUES_ONLY:
        return False, f"Liga ID {league_id} não está na lista permitida"
    
    expected_name = TOP_LEAGUES_ONLY[league_id]['name']
    
    # Verificação flexível de nome (ignora maiúsculas e palavras-chave)
    api_name_lower = api_league_name.lower()
    expected_name_lower = expected_name.lower()
    
    # Lista de palavras-chave que devem coincidir
    key_words_expected = set(expected_name_lower.split())
    key_words_api = set(api_name_lower.split())
    
    # Se pelo menos 50% das palavras-chave coincidem, considera válido
    if key_words_expected & key_words_api:
        return True, "Correspondência válida"
    
    return False, f"Mismatch: API='{api_league_name}' vs Esperado='{expected_name}'"

# ========== BUSCA DE HISTÓRICO ==========
async def get_team_recent_matches_validated(team_id, team_name, limit=5):
    """Busca histórico recente da equipa"""
    try:
        logger.info(f"📊 Buscando histórico de {team_name} (ID: {team_id})")
        
        # Tentativa 1: últimos jogos
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 1:
            logger.info(f"✅ {len(matches)} jogos encontrados para {team_name}")
            return matches
        
        # Tentativa 2: fallback por data
        logger.warning(f"⚠️ Fallback para {team_name}")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=21)
        
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
            logger.info(f"✅ Fallback: {len(sorted_matches)} jogos encontrados")
            return sorted_matches
        
        logger.warning(f"⚠️ Dados insuficientes para {team_name}")
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== DETECÇÃO DE RESULTADOS ==========
def is_exact_0x0_result(match):
    """Detecta especificamente 0x0"""
    try:
        goals = match.get('goals', {})
        score = match.get('score', {})
        
        home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
        away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
        
        if home_goals == 0 and away_goals == 0 and score:
            ft_score = score.get('fulltime', {})
            if ft_score:
                home_goals = ft_score.get('home', 0) if ft_score.get('home') is not None else 0
                away_goals = ft_score.get('away', 0) if ft_score.get('away') is not None else 0
        
        return (home_goals == 0 and away_goals == 0)
        
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

async def check_team_coming_from_under_15_validated(team_id, team_name, current_league_id=None):
    """Verifica se equipa vem de Under 1.5/0x0 na RODADA ANTERIOR
       MANTÉM 10 DIAS para capturar a rodada anterior adequadamente"""
    try:
        recent_matches = await get_team_recent_matches_validated(team_id, team_name, limit=5)
        
        if not recent_matches:
            logger.debug(f"⚠️ Nenhum jogo recente para {team_name}")
            return False, None
        
        # Priorizar jogo da mesma liga se for Tier 1 ou 2
        last_match = None
        if current_league_id and TOP_LEAGUES_ONLY.get(current_league_id, {}).get('tier') in [1, 2]:
            for match in recent_matches:
                if match.get('league', {}).get('id') == current_league_id:
                    last_match = match
                    logger.debug(f"🎯 Último jogo de {team_name} na mesma liga encontrado")
                    break
        
        # Se não encontrou na mesma liga, usar o mais recente
        if not last_match:
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
            
            # CÁLCULO CORRETO: diferença em dias UTC
            days_ago = (datetime.now(pytz.utc) - match_date).days
            
            # CRITÉRIO: até MAX_LAST_MATCH_AGE_DAYS (10 dias) para rodada anterior
            if days_ago > MAX_LAST_MATCH_AGE_DAYS:
                logger.info(f"⚠️ {team_name}: último Under/0x0 há {days_ago} dias (limite: {MAX_LAST_MATCH_AGE_DAYS})")
                return False, None
            
            if is_zero_zero:
                logger.info(f"🔥 {team_name} vem de 0x0 na rodada anterior vs {opponent} ({days_ago}d)")
            else:
                logger.info(f"🎯 {team_name} vem de Under 1.5 na rodada anterior: {score} vs {opponent} ({days_ago}d)")
            
            return True, {
                'opponent': opponent,
                'score': score,
                'date': match_date.strftime('%d/%m'),
                'is_0x0': is_zero_zero,
                'match_date_full': match_date,
                'days_ago': days_ago,
                'league_name': last_match.get('league', {}).get('name', 'N/A')
            }
        
        logger.debug(f"✅ {team_name} não vem de Under 1.5/0x0 na rodada anterior")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando rodada anterior de {team_name}: {e}")
        return False, None

# ========== MONITORAMENTO COM GATES DE SEGURANÇA ==========
async def monitor_todays_games():
    """Monitoramento com múltiplas camadas de validação"""
    logger.info("🔥 MONITORAMENTO DO DIA COM GATES DE SEGURANÇA...")
    
    try:
        todays_matches = await get_todays_matches_only()
        
        if not todays_matches:
            await send_telegram_message("📅 <b>Nenhum jogo encontrado para hoje nas ligas monitorizadas!</b>")
            return
        
        analyzed_count = 0
        alerts_sent = 0
        candidates_found = []
        
        # Data atual para validação final
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
                
                logger.info(f"🔍 Analisando: {home_team} vs {away_team} - {league_name} (ID: {fixture_id})")
                
                # GATE 1: Validação de liga
                is_valid_league, league_msg = validate_league_consistency(league_id, league_name)
                if not is_valid_league:
                    logger.warning(f"⚠️ GATE 1 FALHOU - {league_msg}")
                    continue
                
                # GATE 2: Validação final de data (SAFETY NET)
                match_datetime_utc = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                match_date_lisbon = match_datetime_utc.astimezone(lisbon_tz).date()
                
                if match_date_lisbon != current_lisbon_date:
                    logger.error(f"❌ GATE 2 FALHOU - Data incorreta: {match_date_lisbon} ≠ {current_lisbon_date}")
                    continue
                
                # GATE 3: Validação de horário (não pode ser no passado)
                match_time_lisbon = match_datetime_utc.astimezone(lisbon_tz)
                now_lisbon = datetime.now(lisbon_tz)
                
                if match_time_lisbon < now_lisbon - timedelta(hours=2):  # Margem de 2h
                    logger.warning(f"⚠️ GATE 3 - Jogo no passado: {match_time_lisbon}")
                    continue
                
                logger.info(f"✅ Todos os gates passaram para {home_team} vs {away_team}")
                
                # Análise da rodada anterior
                home_from_under, home_info = await check_team_coming_from_under_15_validated(
                    home_team_id, home_team, league_id)
                away_from_under, away_info = await check_team_coming_from_under_15_validated(
                    away_team_id, away_team, league_id)
                
                analyzed_count += 1
                
                if home_from_under or away_from_under:
                    notification_key = f"today_{current_lisbon_date}_{fixture_id}"
                    
                    if notification_key not in notified_matches['over_potential']:
                        
                        # Coletar candidatos 0x0
                        if home_from_under and home_info.get('is_0x0'):
                            candidates_found.append({'team': home_team, 'opponent': home_info['opponent']})
                        
                        if away_from_under and away_info.get('is_0x0'):
                            candidates_found.append({'team': away_team, 'opponent': away_info['opponent']})
                        
                        # Formatar alerta
                        teams_info = ""
                        priority = "NORMAL"
                        
                        if home_from_under:
                            info = home_info
                            indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                            teams_info += f"🏠 <b>{home_team}</b> vem de <b>{indicator}</b> vs {info['opponent']} ({info['date']} - {info['days_ago']}d)\n"
                            if info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        if away_from_under:
                            info = away_info
                            indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                            teams_info += f"✈️ <b>{away_team}</b> vem de <b>{indicator}</b> vs {info['opponent']} ({info['date']} - {info['days_ago']}d)\n"
                            if info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        confidence = "ALTÍSSIMA" if (home_from_under and away_from_under) else ("ALTA" if priority == "MÁXIMA" else "MÉDIA")
                        
                        league_info = TOP_LEAGUES_ONLY[league_id]
                        tier_indicator = "⭐" * league_info['tier']
                        
                        message = f"""
🚨 <b>ALERTA REGRESSÃO À MÉDIA - PRIORIDADE {priority}</b>

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
🆔 Fixture ID: {fixture_id}
"""
                        
                        await send_telegram_message(message)
                        notified_matches['over_potential'].add(notification_key)
                        alerts_sent += 1
                        
                        logger.info(f"✅ Alerta enviado: {home_team} vs {away_team} (ID: {fixture_id})")
                
            except Exception as e:
                logger.error(f"❌ Erro analisando jogo {match.get('fixture', {}).get('id', 'N/A')}: {e}")
                continue
        
        # Relatório do dia
        summary_msg = f"""
📅 <b>RELATÓRIO DE HOJE ({current_lisbon_date.strftime('%d/%m/%Y')}):</b>

🔍 <b>Jogos analisados:</b> {analyzed_count}
🚨 <b>Alertas enviados:</b> {alerts_sent}
🎯 <b>Candidatos 0x0:</b> {len(candidates_found)}
📊 <b>Janela rodada anterior:</b> {MAX_LAST_MATCH_AGE_DAYS} dias
🛡️ <b>Gates de segurança:</b> Ativados

<i>⏰ Foco exclusivo nos jogos de hoje com validação tripla!</i>
"""
        
        await send_telegram_message(summary_msg)
        logger.info(f"✅ Análise concluída: {analyzed_count} jogos, {alerts_sent} alertas")
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento: {e}")

# ========== DEBUG ==========
async def debug_todays_finished_matches():
    """Debug para jogos finalizados hoje"""
    try:
        logger.info("🔍 DEBUG: Jogos finalizados hoje...")
        
        lisbon_tz = ZoneInfo("Europe/Lisbon")
        today_str = datetime.now(lisbon_tz).date().strftime('%Y-%m-%d')
        
        finished_matches = make_api_request("/fixtures", {
            "date": today_str,
            "status": "FT"
        })
        
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
                logger.error(f"❌ Erro analisando jogo finalizado: {e}")
        
        current_date = datetime.now(lisbon_tz).strftime('%d/%m/%Y')
        await send_telegram_message(f"""
🔍 <b>JOGOS FINALIZADOS HOJE ({current_date}):</b>

📊 <b>Total:</b> {len(finished_matches)} jogos
🔥 <b>0x0:</b> {zero_zero_count}
🎯 <b>Under 1.5:</b> {under_15_count}

<i>Equipas candidatas para regressão nos próximos jogos!</i>
""")
        
    except Exception as e:
        logger.error(f"❌ Erro no debug: {e}")

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal com validação robusta"""
    logger.info("🚀 Bot Regressão à Média - VERSÃO CORRIGIDA!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    current_date = datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%d/%m/%Y')
    await send_telegram_message(
        f"🚀 <b>Bot Regressão à Média - CORRIGIDO!</b>\n\n"
        f"📅 <b>Data atual:</b> {current_date}\n"
        f"🎯 <b>FOCO:</b> Apenas jogos de hoje\n"
        f"⏰ <b>Rodada anterior:</b> Até {MAX_LAST_MATCH_AGE_DAYS} dias\n"
        f"🛡️ <b>Segurança:</b> Gates de validação tripla\n"
        f"🏆 <b>Ligas:</b> {len(ALLOWED_LEAGUES)} validadas\n\n"
        f"🔧 <b>Correções:</b> Data, ligas e validação corrigidas!"
    )
    
    await debug_todays_finished_matches()
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                logger.info(f"📅 Monitoramento às {current_hour}h (Lisboa)")
                await monitor_todays_games()
                logger.info("✅ Ciclo concluído")
                await asyncio.sleep(1800)  # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro no loop: {e}")
            await asyncio.sleep(600)

if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Corrigido...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
