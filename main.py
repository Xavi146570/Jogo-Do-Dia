import os
import requests
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# Variáveis de ambiente
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurações API
BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

# Flask
app = Flask(__name__)

def notify_telegram(message: str):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[ERRO TELEGRAM] {e}")

def get_leagues(season=2025):
    """Obtém todas as ligas da temporada"""
    url = f"{BASE_URL}/leagues?season={season}"
    res = requests.get(url, headers=headers).json()
    return res.get("response", [])

def get_league_stats(league_id, season=2025):
    """Calcula % de jogos Over 1.5 na liga"""
    url = f"{BASE_URL}/fixtures?league={league_id}&season={season}"
    res = requests.get(url, headers=headers).json()
    fixtures = res.get("response", [])
    if not fixtures:
        return 0

    valid_fixtures = [
        f for f in fixtures
        if f["goals"]["home"] is not None and f["goals"]["away"] is not None
    ]
    if not valid_fixtures:
        return 0

    over15 = sum(1 for f in valid_fixtures if f["goals"]["home"] + f["goals"]["away"] > 1)
    return (over15 / len(valid_fixtures)) * 100

def get_team_stats(team_id, league_id, season=2025):
    """Obtém estatísticas de um time específico"""
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season={season}&team={team_id}"
    res = requests.get(url, headers=headers).json()
    return res.get("response", {})

def check_conditions(season=2025):
    """Verifica as condições e envia alerta para o Telegram"""
    now = datetime.now().strftime("%H:%M %d/%m")
    print(f"[{now}] 🔎 Verificando condições para a época {season}...")

    leagues = get_leagues(season)
    found = False

    for league in leagues:
        league_id = league["league"]["id"]
        league_name = league["league"]["name"]

        over15_pct = get_league_stats(league_id, season)
        if over15_pct < 75:
            continue

        # Times da liga
        url = f"{BASE_URL}/teams?league={league_id}&season={season}"
        teams = requests.get(url, headers=headers).json().get("response", [])

        for team in teams:
            team_id = team["team"]["id"]
            stats = get_team_stats(team_id, league_id, season)
            if not stats:
                continue

            played = stats["fixtures"]["played"]["total"]
            if played == 0:
                continue

            win_rate = stats["fixtures"]["wins"]["total"] / played * 100
            over15 = stats.get("goals", {}).get("for", {}).get("over", {}).get("1.5", 0)

            last_match = stats["fixtures"].get("last")
            if not last_match:
                continue

            home = last_match["goals"]["home"]
            away = last_match["goals"]["away"]

            # Condição final
            if win_rate > 60 and over15 > 70 and (home + away <= 1):
                msg = (f"🔥 JOGO TOP DO DIA 🔥\n"
                       f"⚽ [{league_name}] Equipa {team['team']['name']} "
                       f"tem {win_rate:.1f}% vitórias e {over15:.1f}% Over 1.5, "
                       f"mas no último jogo ficou {home}x{away}.")
                notify_telegram(msg)
                found = True

    if not found:
        notify_telegram(f"Nenhum jogo encontrado nesta execução ({now}).")

# Flask rota principal
@app.route("/")
def home():
    return "✅ Bot de futebol ativo!"

# Scheduler (executa de hora em hora)
scheduler = BackgroundScheduler()
scheduler.add_job(check_conditions, "interval", hours=1, args=[2025])
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
