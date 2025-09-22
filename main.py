import requests
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Um conjunto para evitar notificações duplicadas entre execuções
notified_matches = {
    'elite_games': set(),
    'under_15': set()
}

# ==============================
# EQUIPAS QUE LUTAM PELO TÍTULO
# ==============================
EQUIPAS_DE_TITULO = {
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea",
    "Real Madrid", "Barcelona", "Atletico Madrid", "Girona",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    "Inter", "AC Milan", "Juventus", "Napoli",
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille",
    "Benfica", "Porto", "Sporting CP", "Braga",
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar",
    "Celtic", "Rangers",
    "Palmeiras", "Flamengo", "Internacional", "Gremio", "Atletico Mineiro", "Corinthians", "Fluminense",
    "Boca Juniors", "River Plate", "Racing Club", "Rosario Central",
    "Shanghai Port", "Shanghai Shenhua", "Shandong Luneng", "Chengdu Rongcheng"
}

# IDs e nomes dos campeonatos de topo para estatísticas
TOP_LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    78: "Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
    94: "Primeira Liga",
    88: "Eredivisie",
    106: "Scottish Premiership",
    45: "Brasileirão Série A",
    276: "Superliga",
    128: "Primera División",
}

# ======================================
# Funções auxiliares (Agora assíncronas)
# ======================================
def safe_float(value):
    """Converte um valor para float, lidando com erros."""
    try:
        if value is None:
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

async def enviar_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Variáveis TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print(f"[{datetime.now().strftime('%H:%M')}] ✅ Mensagem enviada para o Telegram")
    except Exception as e:
        print("Erro ao enviar mensagem:", e)

async def buscar_estatisticas(equipe_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?team={equipe_id}&league={league_id}&season={season}"
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        stats = r.json()["response"]
        if not stats:
            return None
        
        played_total = stats["fixtures"]["played"]["total"]
        wins_total = stats["fixtures"]["wins"]["total"]

        media_gols = stats["goals"]["for"]["average"]["total"]
        perc_vitorias = (wins_total / played_total) * 100 if played_total > 0 else 0
        return {'media_gols': media_gols, 'perc_vitorias': perc_vitorias}
    except Exception as e:
        print(f"Erro ao buscar estatísticas para a equipe {equipe_id}: {e}")
        return None

async def buscar_ultimo_jogo(equipe_id):
    url = f"{BASE_URL}/fixtures?team={equipe_id}&last=1"
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        jogo = r.json()["response"][0]
        mandante = jogo["teams"]["home"]["name"]
        visitante = jogo["teams"]["away"]["name"]
        placar = f"{jogo['goals']['home']}x{jogo['goals']['away']}"
        return f"{mandante} {placar} {visitante}"
    except Exception as e:
        print(f"Erro ao buscar último jogo para a equipe {equipe_id}: {e}")
        return "<i>Último jogo não disponível.</i>"

def formatar_contagem_regressiva(delta: timedelta) -> str:
    horas, resto = divmod(int(delta.total_seconds()), 3600)
    minutos = resto // 60
    return f"{horas}h {minutos}min" if horas > 0 else f"{minutos}min"

# ======================================
# Funções de processamento dos jogos
# ======================================
async def process_upcoming_match(match):
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    
    if home_team not in EQUIPAS_DE_TITULO and away_team not in EQUIPAS_DE_TITULO:
        return
        
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']

    if fixture_id in notified_matches['elite_games']:
        return

    match_datetime = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
    match_time_local = match_datetime.astimezone(ZoneInfo("Europe/Lisbon"))
    
    elite_status = "Ambas as equipes são de elite!" if home_is_elite and away_is_elite else f"{home_team if home_is_elite else away_team} é uma equipe de elite!"
    stats_section = "📊 <i>Estatísticas não disponíveis.</i>"
    
    if home_is_elite or away_is_elite:
        try:
            if home_is_elite and away_is_elite:
                home_elite_stats = await buscar_estatisticas(match['teams']['home']['id'], league_id, match['league']['season'])
                away_elite_stats = await buscar_estatisticas(match['teams']['away']['id'], league_id, match['league']['season'])

                if home_elite_stats and away_elite_stats:
                    stats_section = f"""
📊 <b>Estatísticas de {TOP_LEAGUES.get(league_id, '...')}:</b>

🏠 <b>{home_team}:</b>
• Gols/jogo: {safe_float(home_elite_stats['media_gols']):.2f}
• Vitórias: {safe_float(home_elite_stats['perc_vitorias']):.1f}%

✈️ <b>{away_team}:</b>
• Gols/jogo: {safe_float(away_elite_stats['media_gols']):.2f}
• Vitórias: {safe_float(away_elite_stats['perc_vitorias']):.1f}%
                    """
            
            else:
                team_id = match['teams']['home']['id'] if home_is_elite else match['teams']['away']['id']
                team_name = home_team if home_is_elite else away_team
                team_stats = await buscar_estatisticas(team_id, league_id, match['league']['season'])
                
                if team_stats:
                    stats_section = f"""
📊 <b>Estatísticas de {team_name} ({TOP_LEAGUES.get(league_id, '...')}):</b>
• Gols/jogo: {safe_float(team_stats['media_gols']):.2f}
• Vitórias: {safe_float(team_stats['perc_vitorias']):.1f}%
                    """
        except Exception as e:
            print(f"❌ Erro ao formatar estatísticas: {e}")
            stats_section = "📊 <i>Erro ao carregar estatísticas.</i>"

    falta = formatar_contagem_regressiva(match_datetime - datetime.now(timezone.utc))
    message = f"""
⭐ <b>JOGO DE ELITE</b> ⭐

⚽ <b>{home_team} vs {away_team}</b>
🏆 <b>{TOP_LEAGUES.get(league_id, 'Campeonato Desconhecido')}</b>
👑 {elite_status}
🕐 <b>{match_time_local.strftime('%H:%M')} (Lisboa)</b>
⏳ Começa em: {falta}

{stats_section}
"""
    await enviar_telegram(message)
    notified_matches['elite_games'].add(fixture_id)

async def process_finished_match(match):
    home_team = match['teams']['home']['name']
    away_team = match['teams']['away']['name']
    home_goals = match['goals']['home'] or 0
    away_goals = match['goals']['away'] or 0
    total_goals = home_goals + away_goals
    league_id = match['league']['id']
    fixture_id = match['fixture']['id']

    if fixture_id in notified_matches['under_15']:
        return
        
    if league_id not in TOP_LEAGUES or total_goals >= 2:
        return
        
    home_is_elite = home_team in EQUIPAS_DE_TITULO
    away_is_elite = away_team in EQUIPAS_DE_TITULO

    if not (home_is_elite or away_is_elite):
        return
        
    elite_status = "Ambas as equipes são de elite!" if home_is_elite and away_is_elite else f"{home_team if home_is_elite else away_team} é uma equipe de elite!"
    
    home_goals_str = str(home_goals) if home_goals is not None else '0'
    away_goals_str = str(away_goals) if away_goals is not None else '0'
    
    message = f"""
📉 <b>FIM DE JOGO - UNDER 1.5 GOLS</b> 📉

⚽ <b>{home_team} {home_goals_str} x {away_goals_str} {away_team}</b>
🏆 <b>{TOP_LEAGUES.get(league_id, 'Campeonato Desconhecido')}</b>
👑 {elite_status}
📊 Total de gols: {total_goals} (Under 1.5 ✅)

🕐 <i>{datetime.now(ZoneInfo("Europe/Lisbon")).strftime('%H:%M %d/%m/%Y')} (Lisboa)</i>
"""
    await enviar_telegram(message)
    notified_matches['under_15'].add(fixture_id)

# ======================================
# Função principal que orquestra tudo
# ======================================
async def main():
    agora_utc = datetime.now(timezone.utc)
    hoje_str = agora_utc.date().isoformat()

    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos...")

    url_upcoming = f"{BASE_URL}/fixtures?date={hoje_str}"
    
    try:
        r = requests.get(url_upcoming, headers=HEADERS)
        r.raise_for_status()
        jogos = r.json().get("response", [])
        print(f"API retornou {len(jogos)} jogos no total para hoje.")
    except Exception as e:
        await enviar_telegram(f"❌ Erro na requisição principal da API: {e}")
        return

    for jogo in jogos:
        status = jogo['fixture']['status']['short']
        
        if status in ['TBD', 'NS', '1H', 'HT', '2H', 'ET', 'P', 'BT', 'INT']:
            await process_upcoming_match(jogo)
        elif status == 'FT':
            await process_finished_match(jogo)
            
    if not any(jogos):
        await enviar_telegram(f"⚽ Nenhum jogo encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')}).")

# Executar
if __name__ == "__main__":
    asyncio.run(main())
