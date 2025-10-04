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

# ========== APENAS LIGAS PRINCIPAIS - SELEÇÃO RIGOROSA ==========
TOP_LEAGUES_ONLY = {
    # EUROPA - TIER 1 APENAS (LIGAS MAIS CONFIÁVEIS)
    39: {"name": "Premier League", "country": "Inglaterra", "0x0_ft_percentage": 7, "over_15_percentage": 75, "tier": 1},
    140: {"name": "La Liga", "country": "Espanha", "0x0_ft_percentage": 7, "over_15_percentage": 71, "tier": 1},
    78: {"name": "Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 7, "over_15_percentage": 84, "tier": 1},
    135: {"name": "Serie A", "country": "Itália", "0x0_ft_percentage": 7, "over_15_percentage": 78, "tier": 1},
    61: {"name": "Ligue 1", "country": "França", "0x0_ft_percentage": 7, "over_15_percentage": 77, "tier": 1},
    94: {"name": "Primeira Liga", "country": "Portugal", "0x0_ft_percentage": 7, "over_15_percentage": 71, "tier": 1},
    88: {"name": "Eredivisie", "country": "Holanda", "0x0_ft_percentage": 7, "over_15_percentage": 82, "tier": 1},
    144: {"name": "Jupiler Pro League", "country": "Bélgica", "0x0_ft_percentage": 7, "over_15_percentage": 81, "tier": 1},
    203: {"name": "Süper Lig", "country": "Turquia", "0x0_ft_percentage": 7, "over_15_percentage": 77, "tier": 1},
    
    # EUROPA - TIER 2 SELECIONADO (PRINCIPAIS SEGUNDAS DIVISÕES)
    40: {"name": "Championship", "country": "Inglaterra", "0x0_ft_percentage": 9, "over_15_percentage": 72, "tier": 2},
    179: {"name": "2. Bundesliga", "country": "Alemanha", "0x0_ft_percentage": 8, "over_15_percentage": 76, "tier": 2},
    136: {"name": "Serie B", "country": "Itália", "0x0_ft_percentage": 8, "over_15_percentage": 74, "tier": 2},
    141: {"name": "Segunda División", "country": "Espanha", "0x0_ft_percentage": 8, "over_15_percentage": 73, "tier": 2},
    62: {"name": "Ligue 2", "country": "França", "0x0_ft_percentage": 8, "over_15_percentage": 75, "tier": 2},
    
    # AMERICA DO SUL - PRINCIPAIS APENAS
    325: {"name": "Brasileirão", "country": "Brasil", "0x0_ft_percentage": 6, "over_15_percentage": 85, "tier": 1},
    128: {"name": "Liga Argentina", "country": "Argentina", "0x0_ft_percentage": 7, "over_15_percentage": 82, "tier": 1},
    218: {"name": "Primera División", "country": "Chile", "0x0_ft_percentage": 8, "over_15_percentage": 78, "tier": 1},
    239: {"name": "Primera División", "country": "Colômbia", "0x0_ft_percentage": 7, "over_15_percentage": 80, "tier": 1},
    
    # AMERICA DO NORTE - TOP APENAS
    253: {"name": "MLS", "country": "Estados Unidos", "0x0_ft_percentage": 5, "over_15_percentage": 88, "tier": 1},
    262: {"name": "Liga MX", "country": "México", "0x0_ft_percentage": 6, "over_15_percentage": 84, "tier": 1},
    
    # ASIA - PRINCIPAIS APENAS
    188: {"name": "J1 League", "country": "Japão", "0x0_ft_percentage": 7, "over_15_percentage": 79, "tier": 1},
    292: {"name": "A-League", "country": "Austrália", "0x0_ft_percentage": 6, "over_15_percentage": 83, "tier": 1},
    17: {"name": "K League 1", "country": "Coreia do Sul", "0x0_ft_percentage": 7, "over_15_percentage": 78, "tier": 1},
}

# Lista de ligas permitidas (apenas as principais)
ALLOWED_LEAGUES = set(TOP_LEAGUES_ONLY.keys())
logger.info(f"📊 Monitorando APENAS {len(ALLOWED_LEAGUES)} ligas principais")

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

# ========== BUSCA DE HISTÓRICO COM VALIDAÇÃO ==========
async def get_team_recent_matches_validated(team_id, team_name, limit=5):
    """Busca histórico com validação de dados"""
    try:
        logger.info(f"📊 Buscando histórico de {team_name} (ID: {team_id})")
        
        # Tentativa 1: last games
        matches = make_api_request("/fixtures", {
            "team": team_id, 
            "last": limit, 
            "status": "FT"
        })
        
        if matches and len(matches) >= 3:  # Mínimo 3 jogos para ser confiável
            logger.info(f"✅ {len(matches)} jogos encontrados para {team_name}")
            return matches
        
        # Tentativa 2: range de datas (apenas 21 dias para ser mais recente)
        logger.warning(f"⚠️ Fallback para {team_name}")
        
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=21)  # Apenas 3 semanas
        
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
            logger.info(f"✅ Fallback: {len(sorted_matches)} jogos")
            return sorted_matches
        
        # Se menos de 3 jogos, considerar dados insuficientes
        logger.warning(f"⚠️ Dados insuficientes para {team_name} ({len(matches_fallback) if matches_fallback else 0} jogos)")
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

async def check_team_coming_from_under_15_validated(team_id, team_name):
    """Verifica se equipe vem de Under 1.5 com validação rigorosa"""
    try:
        recent_matches = await get_team_recent_matches_validated(team_id, team_name, limit=5)
        
        if not recent_matches or len(recent_matches) < 3:
            logger.warning(f"⚠️ Dados insuficientes para {team_name}")
            return False, None
        
        # Verificar o ÚLTIMO jogo (mais recente)
        last_match = recent_matches[0]
        
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
            
            # Verificar se o jogo foi recente (máximo 10 dias)
            days_ago = (datetime.now(pytz.utc) - match_date).days
            if days_ago > 10:
                logger.info(f"⚠️ {team_name}: último jogo muito antigo ({days_ago} dias)")
                return False, None
            
            if is_zero_zero:
                logger.info(f"🔥 {team_name} vem de 0x0 vs {opponent} ({days_ago} dias)")
            else:
                logger.info(f"🎯 {team_name} vem de Under 1.5: {score} vs {opponent} ({days_ago} dias)")
            
            return True, {
                'opponent': opponent,
                'score': score,
                'date': match_date.strftime('%d/%m'),
                'is_0x0': is_zero_zero,
                'match_date_full': match_date,
                'days_ago': days_ago
            }
        
        logger.info(f"✅ {team_name} não vem de Under 1.5")
        return False, None
        
    except Exception as e:
        logger.error(f"❌ Erro verificando {team_name}: {e}")
        return False, None

# ========== BUSCA SELETIVA DE JOGOS FUTUROS ==========
async def get_upcoming_matches_selective():
    """Busca jogos futuros APENAS das ligas principais"""
    logger.info("🔍 BUSCA SELETIVA - APENAS LIGAS PRINCIPAIS...")
    
    all_matches = []
    utc_zone = pytz.utc
    now_utc = datetime.now(utc_zone)
    
    # ========== ESTRATÉGIA: BUSCAR POR LIGA ESPECÍFICA ==========
    # Mais eficiente: buscar diretamente nas ligas que queremos
    
    for league_id in ALLOWED_LEAGUES:
        league_info = TOP_LEAGUES_ONLY[league_id]
        logger.info(f"🏆 Buscando jogos da {league_info['name']}...")
        
        # Buscar próximos jogos desta liga
        league_matches = make_api_request("/fixtures", {
            "league": league_id,
            "next": 5,  # Próximos 5 jogos da liga
            "status": "NS"
        })
        
        if league_matches:
            all_matches.extend(league_matches)
            logger.info(f"✅ {league_info['name']}: {len(league_matches)} jogos")
        
        # Pequena pausa para não sobrecarregar a API
        time.sleep(0.5)
    
    # ========== FALLBACK: BUSCA POR DATA COM FILTRO ==========
    if len(all_matches) < 10:
        logger.info("🔄 Fallback: busca por data com filtro...")
        
        for i in range(3):  # Próximos 3 dias
            date = (now_utc + timedelta(days=i)).strftime('%Y-%m-%d')
            
            date_matches = make_api_request("/fixtures", {
                "date": date,
                "status": "NS"
            })
            
            # Filtrar apenas ligas permitidas
            filtered_matches = [
                match for match in date_matches 
                if match['league']['id'] in ALLOWED_LEAGUES
            ]
            
            if filtered_matches:
                all_matches.extend(filtered_matches)
                logger.info(f"📅 {date}: {len(filtered_matches)} jogos válidos")
    
    # Remover duplicatas
    unique_matches = {}
    for match in all_matches:
        fixture_id = match['fixture']['id']
        if fixture_id not in unique_matches:
            unique_matches[fixture_id] = match
    
    final_matches = list(unique_matches.values())
    logger.info(f"📊 TOTAL SELETIVO: {len(final_matches)} jogos das ligas principais")
    
    return final_matches

# ========== MONITORAMENTO SELETIVO ==========
async def monitor_selective_games():
    """Monitoramento seletivo - apenas ligas principais"""
    logger.info("🔥 MONITORAMENTO SELETIVO INICIADO...")
    
    try:
        # Buscar jogos futuros das ligas principais
        upcoming_matches = await get_upcoming_matches_selective()
        
        if not upcoming_matches:
            await send_telegram_message("⚠️ <b>Nenhum jogo encontrado nas ligas principais!</b>")
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
                
                # FILTRO CRÍTICO: Apenas ligas permitidas
                if league_id not in ALLOWED_LEAGUES:
                    logger.info(f"⏭️ Pulando {home_team} vs {away_team} - Liga não permitida ({league_name})")
                    continue
                
                logger.info(f"🔍 Analisando: {home_team} vs {away_team} - {league_name}")
                
                # Verificar ambas as equipes com validação rigorosa
                home_from_under, home_info = await check_team_coming_from_under_15_validated(home_team_id, home_team)
                away_from_under, away_info = await check_team_coming_from_under_15_validated(away_team_id, away_team)
                
                analyzed_count += 1
                
                # Se pelo menos uma equipe vem de Under 1.5 E tem dados confiáveis
                if home_from_under or away_from_under:
                    
                    notification_key = f"over_potential_{fixture_id}"
                    
                    if notification_key not in notified_matches['over_potential']:
                        
                        # Coletar candidatos 0x0
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
🔥 <b>ALERTA REGRESSÃO À MÉDIA - PRIORIDADE {priority}</b>

🏆 <b>{league_info['name']} ({league_info['country']}) {tier_indicator}</b>
⚽ <b>{home_team} vs {away_team}</b>

{teams_info}
📊 <b>Confiança:</b> {confidence}
📈 <b>Over 1.5 histórico da liga:</b> {league_info['over_15_percentage']}%

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
        logger.info(f"✅ Análise seletiva concluída: {analyzed_count} jogos, {alerts_sent} alertas")
        
        # Relatório de resumo
        summary_msg = f"""
📊 <b>RELATÓRIO DE MONITORAMENTO:</b>

🔍 <b>Jogos analisados:</b> {analyzed_count}
🔥 <b>Alertas enviados:</b> {alerts_sent}
🏆 <b>Ligas monitoradas:</b> {len(ALLOWED_LEAGUES)} principais
🎯 <b>Candidatos 0x0:</b> {len(candidates_found)}

<i>Foco: Apenas ligas de qualidade com dados confiáveis!</i>
"""
        
        await send_telegram_message(summary_msg)
            
    except Exception as e:
        logger.error(f"❌ Erro no monitoramento seletivo: {e}")
        await send_telegram_message(f"⚠️ Erro no monitoramento: {e}")

# ========== DEBUG SIMPLIFICADO ==========
async def debug_todays_finished_matches():
    """Debug simplificado"""
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

📊 <b>Total:</b> {len(finished_matches)} jogos
🔥 <b>0x0:</b> {zero_zero_count}
🎯 <b>Under 1.5:</b> {under_15_count}

<i>Candidatos para alertas nos próximos jogos!</i>
""")
        
    except Exception as e:
        logger.error(f"❌ Erro no debug: {e}")

# ========== LOOP PRINCIPAL ==========
async def main_loop():
    """Loop principal seletivo"""
    logger.info("🚀 Bot Regressão à Média SELETIVO Iniciado!")
    
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ Erro Telegram: {e}")
        return
    
    await send_telegram_message(
        "🚀 <b>Bot Regressão à Média SELETIVO Ativo!</b>\n\n"
        "🎯 <b>FOCO:</b> Apenas ligas principais\n"
        "📊 <b>Critério:</b> Equipes com dados confiáveis\n"
        "⭐ <b>Qualidade:</b> Tier 1 e Tier 2 selecionados\n\n"
        f"🏆 <b>Ligas monitoradas:</b> {len(ALLOWED_LEAGUES)}\n"
        "🔍 <b>Validação:</b> Mínimo 3 jogos recentes\n"
        "⏰ <b>Recência:</b> Máximo 10 dias do último jogo"
    )
    
    # Debug inicial
    await debug_todays_finished_matches()
    
    while True:
        try:
            current_hour = datetime.now(ZoneInfo("Europe/Lisbon")).hour
            
            if 8 <= current_hour <= 23:
                logger.info(f"🔍 Monitoramento seletivo às {current_hour}h")
                
                await monitor_selective_games()
                
                logger.info("✅ Ciclo seletivo concluído")
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
    logger.info("🚀 Iniciando Bot Seletivo...")
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
