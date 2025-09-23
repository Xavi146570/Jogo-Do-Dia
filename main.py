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
import unicodedata

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
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Inicialização do Bot do Telegram (sincrono/async compat)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

# Controle de notificações
notified_matches = {
    'finished_0x0': set(),
    'halftime_0x0': set(),
    'elite_games': set(),
    'under_15': set()
}

# Top ligas monitoradas
TOP_LEAGUES = {
    39: "Premier League",     # Inglaterra
    140: "La Liga",           # Espanha
    78: "Bundesliga",         # Alemanha
    135: "Serie A",           # Itália
    61: "Ligue 1",            # França
    94: "Primeira Liga",      # Portugal
    88: "Eredivisie",         # Holanda
    144: "Jupiler Pro League",# Bélgica
    203: "Süper Lig",         # Turquia
    235: "Russian Premier League"  # Rússia (apenas como exemplo)
}

# Lista expandida de equipes de elite (nomes “canônicos” / tokens)
EQUIPAS_DE_TITULO = [
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea", "Tottenham",
    "Real Madrid", "Barcelona", "Atletico Madrid", "Real Sociedad", "Athletic Club",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig", "Eintracht Frankfurt",
    "Inter", "AC Milan", "Juventus", "Napoli", "AS Roma", "Lazio", "Atalanta",
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille", "Nice",
    "Benfica", "Porto", "Sporting CP", "Braga", "Vitoria de Guimaraes",
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar", "FC Twente",
    "Celtic", "Rangers", "Galatasaray", "Fenerbahce", "Besiktas"
]

# Normalizar tokens para comparação
def normalize_text(s: str) -> str:
    if not s:
        return ""
    s_n = unicodedata.normalize("NFKD", s)
    s_n = "".join(c for c in s_n if not unicodedata.combining(c))
    return s_n.casefold().strip()

ELITE_TOKENS = [normalize_text(x) for x in EQUIPAS_DE_TITULO]

def is_elite_team(name: str) -> bool:
    """Detecta se um nome de equipa corresponde a uma equipa de elite (substrings, case-insensitive)."""
    n = normalize_text(name)
    for token in ELITE_TOKENS:
        if token in n or n in token:
            return True
    return False

# Cache para evitar requests repetitivos
cache_team_stats = {}
cache_league_stats = {}
cache_elite_stats = {}

# =========================================================
# UTILITÁRIOS DE API e TELEGRAM
# =========================================================

async def send_telegram_message(message: str):
    """Envia mensagem assíncrona para o Telegram (usa a API sincrona do python-telegram-bot)"""
    if not bot or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram não configurado. Mensagem não enviada.")
        return
    try:
        # python-telegram-bot sync send_message chamado dentro de executor para não bloquear loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, bot.send_message, TELEGRAM_CHAT_ID, message, 'HTML')
        logger.info("✅ Mensagem enviada para o Telegram")
    except Exception as e:
        logger.exception(f"❌ Erro ao enviar mensagem para Telegram: {e}")

def make_api_request(endpoint: str, params: dict = None, retries: int = 3):
    """Faz requisição para a API com retry automático e logging detalhado"""
    if params is None:
        params = {}
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            try:
                data = r.json()
            except ValueError:
                logger.error(f"Resposta não-JSON de {url} com params {params}: {r.text[:200]}")
                return []
            # Em alguns casos API devolve chave 'errors' ou outros formatos
            if isinstance(data, dict) and "response" in data:
                return data["response"] or []
            # fallback se API já devolver lista
            if isinstance(data, list):
                return data
            logger.warning(f"Resposta inesperada de {url}: {data}")
            return []
        except Exception as e:
            logger.warning(f"Tentativa {attempt}/{retries} falhou para {url} params {params}: {e}")
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
            else:
                logger.error(f"Falha definitiva na requisição para {url}")
                return []

def get_current_hour_lisbon() -> int:
    return datetime.now(ZoneInfo("Europe/Lisbon")).hour

def should_run_monitoring() -> bool:
    current_hour = get_current_hour_lisbon()
    return 9 <= current_hour <= 23

def formatar_contagem_regressiva(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "0min"
    horas, resto = divmod(total_seconds, 3600)
    minutos = resto // 60
    if horas > 0:
        return f"{horas}h {minutos}min"
    return f"{minutos}min"

# =========================================================
# ANÁLISES (cacheadas)
# =========================================================

def analyze_team_0x0_history(team_id: int, league_id: int):
    """Análise percentual de 0x0 em última 3 temporadas (cacheada 1h)"""
    cache_key = f"team_0x0_{team_id}_{league_id}"
    now_ts = datetime.now(timezone.utc).timestamp()
    if cache_key in cache_team_stats:
        cached = cache_team_stats[cache_key]
        if now_ts - cached['timestamp'] < 3600:
            return cached['data']

    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    total_matches = 0
    total_0x0 = 0

    for season in seasons:
        fixtures = make_api_request("/fixtures", {
            "team": team_id,
            "league": league_id,
            "season": season,
            "status": "FT"
        })
        if fixtures:
            season_matches = len(fixtures)
            season_0x0 = sum(1 for m in fixtures if (m.get('goals', {}).get('home') or 0) == 0 and (m.get('goals', {}).get('away') or 0) == 0)
            total_matches += season_matches
            total_0x0 += season_0x0

    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0.0
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10
    }
    cache_team_stats[cache_key] = {'data': result, 'timestamp': now_ts}
    return result

def analyze_league_0x0_history(league_id: int):
    cache_key = f"league_0x0_{league_id}"
    now_ts = datetime.now(timezone.utc).timestamp()
    if cache_key in cache_league_stats:
        cached = cache_league_stats[cache_key]
        if now_ts - cached['timestamp'] < 3600:
            return cached['data']

    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    total_matches = 0
    total_0x0 = 0

    for season in seasons:
        fixtures = make_api_request("/fixtures", {
            "league": league_id,
            "season": season,
            "status": "FT"
        })
        if fixtures:
            season_matches = len(fixtures)
            season_0x0 = sum(1 for m in fixtures if (m.get('goals', {}).get('home') or 0) == 0 and (m.get('goals', {}).get('away') or 0) == 0)
            total_matches += season_matches
            total_0x0 += season_0x0

    percentage = (total_0x0 / total_matches * 100) if total_matches > 0 else 0.0
    result = {
        'percentage': round(percentage, 2),
        'total_matches': total_matches,
        'total_0x0': total_0x0,
        'qualifies': percentage < 10
    }
    cache_league_stats[cache_key] = {'data': result, 'timestamp': now_ts}
    return result

def analyze_elite_team_stats(team_id: int, league_id: int):
    """Análise de vitórias e Over 1.5 das equipas de elite (cache 2h)"""
    cache_key = f"elite_stats_{team_id}_{league_id}"
    now_ts = datetime.now(timezone.utc).timestamp()
    if cache_key in cache_elite_stats:
        cached = cache_elite_stats[cache_key]
        if now_ts - cached['timestamp'] < 7200:
            return cached['data']

    current_year = datetime.now().year
    seasons = [current_year, current_year - 1, current_year - 2]
    total_matches = 0
    total_wins = 0
    total_over_15 = 0

    for season in seasons:
        fixtures = make_api_request("/fixtures", {
            "team": team_id,
            "league": league_id,
            "season": season,
            "status": "FT"
        })
        if fixtures:
            for m in fixtures:
                home_goals = m.get('goals', {}).get('home') or 0
                away_goals = m.get('goals', {}).get('away') or 0
                total_goals = home_goals + away_goals
                total_matches += 1

                team_is_home = m.get('teams', {}).get('home', {}).get('id') == team_id
                if team_is_home and home_goals > away_goals:
                    total_wins += 1
                elif not team_is_home and away_goals > home_goals:
                    total_wins += 1

                if total_goals > 1:  # Over 1.5
                    total_over_15 += 1

    win_percentage = (total_wins / total_matches * 100) if total_matches > 0 else 0.0
    over_15_percentage = (total_over_15 / total_matches * 100) if total_matches > 0 else 0.0

    result = {
        'win_percentage': round(win_percentage, 1),
        'over_15_percentage': round(over_15_percentage, 1),
        'total_matches': total_matches,
        'total_wins': total_wins,
        'total_over_15': total_over_15
    }
    cache_elite_stats[cache_key] = {'data': result, 'timestamp': now_ts}
    return result

# =========================================================
# MONITORAMENTO AO VIVO
# =========================================================

async def monitor_live_matches():
    if not should_run_monitoring():
        logger.info("Fora do horário de monitoramento (live).")
        return

    logger.info("🔍 Verificando jogos ao vivo...")
    live = make_api_request("/fixtures", {"live": "all"})
    if not live:
        logger.info("Nenhum jogo ao vivo encontrado.")
        return

    logger.info(f"Encontrados {len(live)} jogos ao vivo.")
    for match in live:
        try:
            await process_live_match(match)
        except Exception as e:
            logger.exception(f"Erro ao processar jogo ao vivo: {e}")

async def process_live_match(match: dict):
    fixture_id = match.get('fixture', {}).get('id')
    home_team = match.get('teams', {}).get('home', {}).get('name', '')
    away_team = match.get('teams', {}).get('away', {}).get('name', '')
    home_goals = match.get('goals', {}).get('home') or 0
    away_goals = match.get('goals', {}).get('away') or 0
    status = match.get('fixture', {}).get('status', {}).get('short', '')
    league_id = match.get('league', {}).get('id')

    if league_id not in TOP_LEAGUES:
        return

    league_analysis = analyze_league_0x0_history(league_id)
    if not league_analysis['qualifies']:
        return

    home_analysis = analyze_team_0x0_history(match.get('teams', {}).get('home', {}).get('id'), league_id)
    away_analysis = analyze_team_0x0_history(match.get('teams', {}).get('away', {}).get('id'), league_id)

    teams_qualify = home_analysis['qualifies'] or away_analysis['qualifies']
    if not teams_qualify:
        return

    # Intervalo 0x0
    if status == 'HT' and home_goals == 0 and away_goals == 0:
        key = f"halftime_{fixture_id}"
        if key not in notified_matches['halftime_0x0']:
            message = (
                f"⏸️ <b>INTERVALO 0x0 DETECTADO</b> ⏸️\n\n"
                f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga')}</b>\n"
                f"⚽ <b>{home_team} 0 x 0 {away_team}</b>\n\n"
                f"📊 Liga (ult.3 temporadas): {league_analysis['percentage']}% jogos 0x0\n"
                f"• {home_team}: {home_analysis['percentage']}% 0x0\n"
                f"• {away_team}: {away_analysis['percentage']}% 0x0\n\n"
                f"🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>"
            )
            await send_telegram_message(message)
            notified_matches['halftime_0x0'].add(key)

    # Jogo terminado 0x0
    elif status == 'FT' and home_goals == 0 and away_goals == 0:
        key = f"finished_{fixture_id}"
        if key not in notified_matches['finished_0x0']:
            message = (
                f"🚨 <b>JOGO TERMINOU 0x0</b> 🚨\n\n"
                f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga')}</b>\n"
                f"⚽ <b>{home_team} 0 x 0 {away_team}</b>\n\n"
                f"📊 Liga (ult.3 temporadas): {league_analysis['percentage']}% jogos 0x0\n"
                f"• {home_team}: {home_analysis['percentage']}% 0x0\n"
                f"• {away_team}: {away_analysis['percentage']}% 0x0\n\n"
                f"🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>"
            )
            await send_telegram_message(message)
            notified_matches['finished_0x0'].add(key)

# =========================================================
# MONITORAMENTO DE EQUIPES DE ELITE (FUTUROS E FINALIZADOS)
# =========================================================

async def monitor_elite_teams():
    if not should_run_monitoring():
        logger.info("Fora do horário de monitoramento (elite).")
        return

    logger.info("👑 Verificando jogos de equipes de elite...")
    # Usar datas em Lisboa para "hoje" e "amanhã"
    tz = ZoneInfo("Europe/Lisbon")
    today_dt = datetime.now(tz).date()
    tomorrow_dt = (datetime.now(tz) + timedelta(days=1)).date()

    # Buscar partidas NS (não iniciadas) entre hoje e amanhã
    upcoming = make_api_request("/fixtures", {
        "from": today_dt.isoformat(),
        "to": tomorrow_dt.isoformat(),
        "status": "NS"
    })

    # Buscar partidas FT do dia atual (para Under1.5 notification)
    finished = make_api_request("/fixtures", {
        "date": today_dt.isoformat(),
        "status": "FT"
    })

    logger.info(f"Upcoming (NS) retornados: {len(upcoming)} | Finished (FT) retornados: {len(finished)}")

    for m in upcoming:
        try:
            await process_elite_upcoming_match(m)
        except Exception as e:
            logger.exception(f"Erro processando upcoming match: {e}")

    for m in finished:
        try:
            await process_elite_finished_match(m)
        except Exception as e:
            logger.exception(f"Erro processando finished match: {e}")

async def process_elite_upcoming_match(match: dict):
    home_team = match.get('teams', {}).get('home', {}).get('name', '')
    away_team = match.get('teams', {}).get('away', {}).get('name', '')
    home_team_id = match.get('teams', {}).get('home', {}).get('id')
    away_team_id = match.get('teams', {}).get('away', {}).get('id')
    league_id = match.get('league', {}).get('id')
    fixture_id = match.get('fixture', {}).get('id')

    # Filtrar por ligas monitoradas
    if league_id not in TOP_LEAGUES:
        return

    # Detectar se pelo menos uma é de elite (mais robusto com normalize)
    home_is_elite = is_elite_team(home_team)
    away_is_elite = is_elite_team(away_team)

    if not (home_is_elite or away_is_elite):
        return

    key = f"elite_game_{fixture_id}"
    if key in notified_matches['elite_games']:
        return

    # Converter horário para Lisboa e calcular contagem regressiva
    date_str = match.get('fixture', {}).get('date')
    if not date_str:
        return
    try:
        match_dt_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        logger.warning(f"Formato data inválido para fixture {fixture_id}: {date_str}")
        return
    match_dt_local = match_dt_utc.astimezone(ZoneInfo("Europe/Lisbon"))
    time_to_start = match_dt_utc - datetime.now(timezone.utc)
    countdown = formatar_contagem_regressiva(time_to_start)

    # Montar seção de estatísticas
    stats_section = ""
    try:
        if home_is_elite and away_is_elite:
            home_stats = analyze_elite_team_stats(home_team_id, league_id)
            away_stats = analyze_elite_team_stats(away_team_id, league_id)
            stats_section = (
                f"📊 <b>Estatísticas (últimas 3 temporadas):</b>\n\n"
                f"🏠 <b>{home_team}:</b>\n"
                f"• Vitórias: {home_stats['win_percentage']}%\n"
                f"• Over 1.5: {home_stats['over_15_percentage']}%\n\n"
                f"✈️ <b>{away_team}:</b>\n"
                f"• Vitórias: {away_stats['win_percentage']}%\n"
                f"• Over 1.5: {away_stats['over_15_percentage']}%\n"
            )
        elif home_is_elite:
            home_stats = analyze_elite_team_stats(home_team_id, league_id)
            stats_section = (
                f"📊 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>\n"
                f"• Vitórias: {home_stats['win_percentage']}%\n"
                f"• Over 1.5: {home_stats['over_15_percentage']}%\n"
            )
        else:
            away_stats = analyze_elite_team_stats(away_team_id, league_id)
            stats_section = (
                f"📊 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>\n"
                f"• Vitórias: {away_stats['win_percentage']}%\n"
                f"• Over 1.5: {away_stats['over_15_percentage']}%\n"
            )
    except Exception as e:
        logger.warning(f"Erro ao obter estatísticas de elite para fixture {fixture_id}: {e}")
        stats_section = "📊 <i>Estatísticas indisponíveis no momento.</i>"

    elite_status = ("Ambas as equipes são de elite!" if home_is_elite and away_is_elite
                    else f"{home_team} é equipe de elite!" if home_is_elite else f"{away_team} é equipe de elite!")

    message = (
        f"⭐ <b>JOGO DO DIA - EQUIPE DE ELITE</b> ⭐\n\n"
        f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga')}</b>\n"
        f"⚽ <b>{home_team} vs {away_team}</b>\n\n"
        f"👑 {elite_status}\n\n"
        f"🕐 <b>{match_dt_local.strftime('%H:%M')} (Lisboa)</b>\n"
        f"📅 {match_dt_local.strftime('%d/%m/%Y')}\n"
        f"⏳ Começa em {countdown}\n\n"
        f"{stats_section}\n\n"
        f"🔥 Jogo de alto nível!"
    )

    await send_telegram_message(message)
    notified_matches['elite_games'].add(key)
    logger.info(f"Notificado Jogo do Dia (elite): {home_team} vs {away_team} às {match_dt_local.strftime('%H:%M')} (Lisboa)")

async def process_elite_finished_match(match: dict):
    home_team = match.get('teams', {}).get('home', {}).get('name', '')
    away_team = match.get('teams', {}).get('away', {}).get('name', '')
    home_team_id = match.get('teams', {}).get('home', {}).get('id')
    away_team_id = match.get('teams', {}).get('away', {}).get('id')
    home_goals = match.get('goals', {}).get('home') or 0
    away_goals = match.get('goals', {}).get('away') or 0
    total_goals = home_goals + away_goals
    league_id = match.get('league', {}).get('id')
    fixture_id = match.get('fixture', {}).get('id')

    if league_id not in TOP_LEAGUES:
        return

    home_is_elite = is_elite_team(home_team)
    away_is_elite = is_elite_team(away_team)

    # Under 1.5 and at least one elite
    if (home_is_elite or away_is_elite) and total_goals < 2:
        key = f"under15_{fixture_id}"
        if key in notified_matches['under_15']:
            return

        try:
            if home_is_elite and away_is_elite:
                home_stats = analyze_elite_team_stats(home_team_id, league_id)
                away_stats = analyze_elite_team_stats(away_team_id, league_id)
                stats_section = (
                    f"📈 <b>Estatísticas das equipes (últimas 3 temporadas):</b>\n\n"
                    f"🏠 <b>{home_team}:</b>\n"
                    f"• Vitórias: {home_stats['win_percentage']}%\n"
                    f"• Over 1.5: {home_stats['over_15_percentage']}%\n\n"
                    f"✈️ <b>{away_team}:</b>\n"
                    f"• Vitórias: {away_stats['win_percentage']}%\n"
                    f"• Over 1.5: {away_stats['over_15_percentage']}\n"
                )
            elif home_is_elite:
                home_stats = analyze_elite_team_stats(home_team_id, league_id)
                stats_section = (
                    f"📈 <b>Estatísticas de {home_team} (últimas 3 temporadas):</b>\n"
                    f"• Vitórias: {home_stats['win_percentage']}%\n"
                    f"• Over 1.5: {home_stats['over_15_percentage']}%"
                )
            else:
                away_stats = analyze_elite_team_stats(away_team_id, league_id)
                stats_section = (
                    f"📈 <b>Estatísticas de {away_team} (últimas 3 temporadas):</b>\n"
                    f"• Vitórias: {away_stats['win_percentage']}%\n"
                    f"• Over 1.5: {away_stats['over_15_percentage']}%"
                )
        except Exception as e:
            logger.warning(f"Erro ao obter estatísticas para under15 notification: {e}")
            stats_section = "📈 <i>Estatísticas indisponíveis</i>"

        message = (
            f"📉 <b>UNDER 1.5 GOLS - EQUIPE DE ELITE</b> 📉\n\n"
            f"🏆 <b>{TOP_LEAGUES.get(league_id, 'Liga')}</b>\n"
            f"⚽ <b>{home_team} {home_goals} x {away_goals} {away_team}</b>\n\n"
            f"👑 {'Ambas as equipes são de elite!' if home_is_elite and away_is_elite else (home_team + ' é equipe de elite!' if home_is_elite else away_team + ' é equipe de elite!')}\n"
            f"📊 Total de gols: {total_goals} (Under 1.5 ✅)\n\n"
            f"{stats_section}\n\n"
            f"🕐 <i>{datetime.now(ZoneInfo('Europe/Lisbon')).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>"
        )

        await send_telegram_message(message)
        notified_matches['under_15'].add(key)
        logger.info(f"Notificado Under1.5 para {home_team} vs {away_team} ({home_goals}-{away_goals})")

# =========================================================
# AGENDAMENTO HORÁRIO E SERVIDOR WEB
# =========================================================

async def hourly_monitoring():
    logger.info("⏰ Iniciando monitoramento horário...")
    # mensagem inicial
    await send_telegram_message(
        f"🚀 <b>Bot de Futebol Iniciado!</b>\n\n"
        f"⏰ Monitoramento ativo das 09h às 23h (Lisboa)\n"
        f"🔍 Verificações a cada hora\n"
    )
    while True:
        try:
            now = datetime.now(ZoneInfo("Europe/Lisbon"))
            if should_run_monitoring():
                logger.info(f"🕐 Executando monitoramento às {now.strftime('%H:%M')} (Lisboa)")
                await monitor_live_matches()
                await monitor_elite_teams()
                logger.info("✅ Monitoramento concluído")
            else:
                logger.info("😴 Fora do horário de monitoramento")

            # Esperar até o início da próxima hora
            next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            wait_seconds = (next_hour - now).total_seconds()
            logger.info(f"⏳ Aguardando {int(wait_seconds/60)} minutos até próxima verificação...")
            await asyncio.sleep(wait_seconds)
        except Exception as e:
            logger.exception(f"Erro no loop horário: {e}")
            await send_telegram_message(f"⚠️ Erro no bot: {e}")
            await asyncio.sleep(300)

async def daily_status():
    while True:
        try:
            now = datetime.now(ZoneInfo("Europe/Lisbon"))
            # executar por volta das 08:00 (apenas se entre 08:00 e 08:29)
            if now.hour == 8 and now.minute < 30:
                status_message = (
                    f"📊 <b>Relatório Diário do Bot</b>\n\n"
                    f"• Jogos 0x0 finalizados: {len(notified_matches['finished_0x0'])}\n"
                    f"• Intervalos 0x0: {len(notified_matches['halftime_0x0'])}\n"
                    f"• Jogos do dia (elite): {len(notified_matches['elite_games'])}\n"
                    f"• Under 1.5 (elite): {len(notified_matches['under_15'])}\n\n"
                    f"🏆 Monitorando {len(TOP_LEAGUES)} ligas\n"
                    f"👑 Acompanhando {len(EQUIPAS_DE_TITULO)} equipes de elite\n"
                    f"🕐 {now.strftime('%d/%m/%Y %H:%M')} (Lisboa)"
                )
                await send_telegram_message(status_message)
                # limpar notificações antigas
                for k in notified_matches:
                    notified_matches[k].clear()
                # dormir quase 24h
                await asyncio.sleep(23 * 3600)
            else:
                # esperar até às 08h do próximo dia
                next_8 = (now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1))
                wait_seconds = (next_8 - now).total_seconds()
                await asyncio.sleep(wait_seconds)
        except Exception as e:
            logger.exception(f"Erro no daily_status: {e}")
            await asyncio.sleep(3600)

async def run_web_server():
    app = web.Application()

    async def health_check(request):
        now = datetime.now(ZoneInfo("Europe/Lisbon"))
        active = should_run_monitoring()
        html = f"""
        <html><head><meta charset="utf-8"><title>Bot Futebol - Status</title></head><body>
        <h1>🤖 Bot de Monitoramento de Futebol</h1>
        <p><strong>Hora (Lisboa):</strong> {now.strftime('%H:%M %d/%m/%Y')}</p>
        <p><strong>Status:</strong> {'🟢 ATIVO' if active else '🔴 INATIVO'}</p>
        <p><strong>Jogos 0x0 finalizados:</strong> {len(notified_matches['finished_0x0'])}</p>
        <p><strong>Intervalos 0x0:</strong> {len(notified_matches['halftime_0x0'])}</p>
        <p><strong>Jogos do dia (elite):</strong> {len(notified_matches['elite_games'])}</p>
        <p><strong>Under 1.5 (elite):</strong> {len(notified_matches['under_15'])}</p>
        </body></html>
        """
        return web.Response(text=html, content_type='text/html')

    async def status_json(request):
        now = datetime.now(ZoneInfo("Europe/Lisbon"))
        obj = {
            "status": "active" if should_run_monitoring() else "standby",
            "time_lisbon": now.isoformat(),
            "notifications": {k: len(v) for k, v in notified_matches.items()}
        }
        return web.json_response(obj)

    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status_json)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Servidor web iniciado na porta {port}")

# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================

async def main():
    logger.info("🚀 Iniciando Bot de Monitoramento de Futebol...")
    logger.info("⏰ Horário de funcionamento: 09h às 23h (Lisboa)")
    await asyncio.gather(
        run_web_server(),
        hourly_monitoring(),
        daily_status()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception:
        logger.exception("❌ Erro fatal")
