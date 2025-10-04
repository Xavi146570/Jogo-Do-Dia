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

# ========== LIGAS EXPANDIDAS ==========
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
    179: {"name": "2. Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 8, "over_15_percentage": 76},
    136: {"name": "Serie B", "country": "Itália", "0x0_ft_percentage": 8, "over_15_percentage": 74},
    141: {"name": "Segunda División", "country": "Espanha", "0x0_ft_percentage": 8, "over_15_percentage": 73},
    62: {"name": "Ligue 2", "country": "França", "0x0_ft_percentage": 8, "over_15_percentage": 75},
    
    # AMERICA DO SUL
    325: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85},
    128: {"name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82},
    218: {"name": "Primera División", "country": "Chile", "0x0_ft_percentage": 8, "over_15_percentage": 78},
    239: {"name": "Primera División", "country": "Colômbia", "0x0_ft_percentage": 7, "over_15_percentage": 80},
    
    # AMERICA DO NORTE
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84},
    
    # ASIA
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

# ========== BUSCA DE HISTÓRICO ==========
async def get_team_recent_matches(team_id, team_name, limit=8):
    """Busca histórico da equipe"""
    try:
        logger.info(f"📊 Buscando histórico de {team_name} (ID: {team_id})")
        
        # Tentativa 1: last games
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 2:
            logger.info(f"✅ Encontrados {len(matches)} jogos para {team_name}")
            return matches
        
        # Tentativa 2: range de datas
        logger.warning(f"⚠️ Fallback para {team_name}")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=30)
        
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
            logger.info(f"✅ Fallback: {len(sorted_matches)} jogos")
            return sorted_matches
        
        logger.error(f"❌ Nenhum jogo encontrado para {team_name}")
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro buscando histórico de {team_name}: {e}")
        return []

# ========== DETECÇÃO DE 0x0 E UNDER 1.5 ==========
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
        
        return total_goals < 2  # 0 ou 1 gol total
        
    except Exception as e:
        logger.error(f"❌ Erro verificando Under 1.5: {e}")
        return False

async def check_team_coming_from_under_15(team_id, team_name):
    """Verifica se equipe vem de Under 1.5 na rodada passada"""
    try:
        recent_matches = await get_team_recent_matches(team_id, team_name, limit=5)
        
        if not recent_matches:
            logger.warning(f"⚠️ Sem histórico para {team_name}")
            return False, None
        
        # Verificar o ÚLTIMO jogo (rodada passada)
        last_match = recent_matches[0]  # Jogo mais recente
        
        is_zero_zero = is_exact_0x0_result(last_match)
        is_under_15 = is_under_15_result(last_match)
        
        if is_under_15:  # Se foi Under 1.5
            goals = last_match.get('goals', {})
            home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
            away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
            score = f"{home_goals}x{away_goals}"
            
            # Identificar adversário
            opponent = (last_match['teams']['away']['name'] 
                       if last_match['teams']['home']['id'] == team_id 
                       else last_match['teams']['home']['name'])
            
            match_date = datetime.fromisoformat(last_match['fixture']['date'].replace('Z', '+00:00'))
            
            if is_zero_zero:
                logger.info(f"🔥 {team_name} vem de 0x0 vs {opponent}")
            else:
                logger.info(f"🎯 {team_name} vem de Under 1.5: {score} vs {opponent}")
            
            return True, {
                'opponent': opponent,
                'score': score,
                'date': match_date.strftime('%d/%m'),
                'is_0x0': is_zero_zero,
                'match_date_full': match_date
            }
        
        logger.info(f"✅ {team_name} não vem de Under 1.5")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando {team_name}: {e}")
        return False, None

# ========== BUSCA EXPANDIDA DE JOGOS FUTUROS ==========
async def get_all_upcoming_matches():
    """Busca TODOS os jogos futuros com múltiplas estratégias"""
    logger.info("🔍 BUSCA EXPANDIDA DE JOGOS FUTUROS...")
    
    all_matches = []
    utc_zone = pytz.utc
    now_utc = datetime.now(utc_zone)
    
    # ========== ESTRATÉGIA 1: POR DATA ==========
    dates_to_check = []
    for i in range(5):  # Hoje + próximos 4 dias
        date = (now_utc + timedelta(days=i)).strftime('%Y-%m-%d')
        dates_to_check.append(date)
    
    logger.info(f"📅 Verificando datas: {dates_to_check}")
    
    for date in dates_to_check:
        matches = make_api_request("/fixtures", {
            "date": date,
            "status": "NS"  # Not Started
        })
        if matches:
            all_matches.extend(matches)
            logger.info(f"📅 {date}: {len(matches)} jogos")
    
    # ========== ESTRATÉGIA 2: POR RANGE ==========
    if len(all_matches) < 10:  # Se poucos jogos, tentar range
        logger.info("🔄 Tentando busca por range...")
        
        start_date = now_utc.strftime('%Y-%m-%d')
        end_date = (now_utc + timedelta(days=7)).strftime('%Y-%m-%d')
        
        range_matches = make_api_request("/fixtures", {
            "from": start_date,
            "to": end_date,
            "status": "NS"
        })
        
        if range_matches:
            all_matches.extend(range_matches)
            logger.info(f"📊 Range: +{len(range_matches)} jogos")
    
    # ========== ESTRATÉGIA 3: PRINCIPAIS LIGAS ==========
    if len(all_matches) < 5:  # Se ainda poucos jogos
        logger.info("🔄 Buscando por ligas específicas...")
        
        top_leagues = [39, 140, 78, 135, 61, 94, 88, 325, 253, 188]  # Top 10 ligas
        
        for league_id in top_leagues:
            league_matches = make_api_request("/fixtures", {
                "league": league_id,
                "next": 3,  # Próximos 3 jogos da liga
                "status": "NS"
            })
            
            if league_matches:
                all_matches.extend(league_matches)
                logger.info(f"🏆 Liga {league_id}: +{len(league_matches)} jogos")
    
    # Remover duplicatas
    unique_matches = {}
    for match in all_matches:
        fixture_id = match['fixture']['id']
        if fixture_id not in unique_matches:
            unique_matches[fixture_id] = match
    
    final_matches = list(unique_matches.values())
    logger.info(f"📊 TOTAL ÚNICO: {len(final_matches)} jogos futuros encontrados")
    
    return final_matches

# ========== MONITORAMENTO PRINCIPAL ==========
async def monitor_over_potential_games():
    """Monitoramento de equipes vindas de Under 1.5"""
    logger.info("🔥 MONITORAMENTO INICIADO...")
    
    try:
        # Buscar jogos futuros
        upcoming_matches = await get_all_upcoming_matches()
        
        if not upcoming_matches:
            await send_telegram_message("⚠️ <b>ATENÇÃO:</b> Nenhum jogo futuro encontrado!")
            return
        
        analyzed_count = 0
        alerts_sent = 0
        candidates_found = []
        
        for match in upcoming_matches:
            try:
                fixture_id = match['fixture']['id']
                home_team = match['teams']['home']['name']
                away_team = match['teams']['away']['name']
                home_team_id = match['teams']['home']['id']
                away_team_id = match['teams']['away']['id']
                league_name = match['league']['name']
                league_id = match['league']['id']
                
                logger.info(f"🔍 Analisando: {home_team} vs {away_team}")
                
                # Verificar ambas as equipes
                home_from_under, home_info = await check_team_coming_from_under_15(home_team_id, home_team)
                away_from_under, away_info = await check_team_coming_from_under_15(away_team_id, away_team)
                
                analyzed_count += 1
                
                # Se pelo menos uma equipe vem de Under 1.5
                if home_from_under or away_from_under:
                    
                    notification_key = f"over_potential_{fixture_id}"
                    
                    if notification_key not in notified_matches['over_potential']:
                        
                        # Coletar candidatos
                        if home_from_under and home_info.get('is_0x0'):
                            candidates_found.append({
                                'team': home_team,
                                'opponent': home_info['opponent'],
                                'date': home_info['date']
                            })
                        
                        if away_from_under and away_info.get('is_0x0'):
                            candidates_found.append({
                                'team': away_team,
                                'opponent': away_info['opponent'],
                                'date': away_info['date']
                            })
                        
                        # Formatar alerta
                        match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
                        match_time = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
                        
                        teams_info = ""
                        priority = "NORMAL"
                        
                        if home_from_under:
                            info = home_info
                            indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                            teams_info += f"🏠 <b>{home_team}</b> vem de <b>{indicator}</b> vs {info['opponent']} ({info['date']})\n"
                            if info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        if away_from_under:
                            info = away_info
                            indicator = "🔥 0x0" if info.get('is_0x0') else f"Under 1.5 ({info['score']})"
                            teams_info += f"✈️ <b>{away_team}</b> vem de <b>{indicator}</b> vs {info['opponent']} ({info['date']})\n"
                            if info.get('is_0x0'):
                                priority = "MÁXIMA"
                        
                        confidence = "ALTÍSSIMA" if (home_from_under and away_from_under) else ("ALTA" if priority == "MÁXIMA" else "MÉDIA")
                        
                        league_info = LEAGUE_STATS.get(league_id, {
                            "name": league_name,
                            "country": match['league'].get('country', 'N/A'),
                            "over_15_percentage": 75
                        })
                        
                        message = f"""
🔥 <b>ALERTA REGRESSÃO À MÉDIA - PRIORIDADE {priority}</b>

🏆 <b>{league_info['name']} ({league_info.get('country', 'N/A')})</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Confiança:</b> {confidence}
📈 <b>Over 1.5 histórico:</b> {league_info.get('over_15_percentage', 75)}%

💡 <b>Estratégia:</b> Regressão à média após seca de gols

🎯 <b>Sugestões:</b> 
• 🟢 Over 1.5 Gols (Principal)
• 🟢 Over 0.5 Gols (Conservador)
• 🟢 BTTS (Ambas marcam)

🕐 <b>{match_time.strftime('%H:%M')} - {match_time.strftime('%d/%m/%Y')}</b>
🆔 Fixture ID: {fixture_id}
"""
                        
                        await send_telegram_message(message)
                        notified_matches['over_potential'].add(notification_key)
                        alerts_sent += 1
                        
                        logger.info(f"✅ Alerta enviado: {home_team} vs {away_team}")
                
            except Exception as e:
                logger.error(f"❌ Erro analisando jogo: {e}")
                continue
        
        # Relatório final
        logger.info(f"✅ Análise concluída: {analyzed_count} jogos, {alerts_sent} alertas")
        
        if candidates_found:
            debug_msg = "🔥 <b>EQUIPES VINDAS DE 0x0 DETECTADAS:</b>\n\n"
            for candidate in candidates_found:
                debug_msg += f"• <b>{candidate['team']}</b> vs {candidate['opponent']} ({candidate['date']})\n"
            
            await send_telegram_message(debug_msg)
        
        if analyzed_count == 0:
            await send_telegram_message("🐛 <b>DEBUG:</b> Nenhum jogo analisado. Verificar busca de jogos futuros.")
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento: {e}")

# ========== DEBUG ==========
async def debug_todays_finished_matches():
    """Debug de jogos finalizados hoje"""
    try:
        logger.info("🔍 DEBUG: Jogos finalizados hoje...")
        
        today_utc = datetime.now(pytz.utc).strftime('%Y-%m-%d')
        
        finished_matches = make_api_request("/fixtures", {
            "date": today_utc,
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
                logger.error(f"❌ Erro analisando jogo: {e}")
        
        await send_telegram_message(f"""
🔍 <b>JOGOS FINALIZADOS HOJE:</b>

📊 <b>Total analisado:</b> {len(finished_matches)} jogos
🔥 <b>Resultados 0x0:</b> {zero_zero_count}
🎯 <b>Resultados Under 1.5:</b> {under_15_count}

<i>Estas equipes serão candidatas para alertas nos próximos jogos!</i>
""")
        
    except Exception as e:
        logger.error(f"❌ Erro no debug: {e}")

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal"""
    logger.info("🚀 Bot Regressão à Média INICIADO!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot Regressão à Média ATIVO!</b>\n\n"
        "🎯 <b>OBJETIVO:</b>\n"
        "Detectar equipes que vão jogar HOJE/AMANHÃ\n"
        "e vêm de 0x0 ou Under 1.5 na rodada passada\n\n"
        f"📊 <b>Monitorando:</b> {len(ALL_MONITORED_LEAGUES)} ligas\n"
        "🔍 <b>Busca:</b> Expandida (múltiplas estratégias)\n"
        "⚡ <b>Foco:</b> Regressão à média"
    )
    
    # Debug inicial
    await debug_todays_finished_matches()
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                logger.info(f"🔍 Monitoramento às {current_hour}h")
                
                await monitor_over_potential_games()
                
                logger.info("✅ Ciclo concluído")
                await asyncio.sleep(1800)  # 30 minutos
            else:
                logger.info(f"😴 Fora do horário ({current_hour}h)")
                await asyncio.sleep(3600)  # 1 hora
                
        except Exception as e:
            logger.error(f"❌ Erro no loop: {e}")
            await send_telegram_message(f"⚠️ Erro detectado: {e}")
            await asyncio.sleep(600)  # 10 minutos

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
