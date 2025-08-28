import os
import requests
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# Credenciais e configs
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

app = Flask(__name__)

def notify_telegram(message):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def get_leagues(season):
    url = f"{BASE_URL}/leagues?season={season}"
    return requests.get(url, headers=headers).json().get("response", [])

def get_league_stats(league_id, season):
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

def get_team_stats(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season={season}&team={team_id}"
    return requests.get(url, headers=headers).json().get("response", {})

def check_conditions():
    """Verifica condições e envia mensagem"""
    now = datetime.now().strftime("%H:%M %d/%m")
    notify_telegram(f"🔎 Verificando condições para a época 2025... ({now})")

    leagues = get_leagues(2025)  # começa já em 2025
    found = False

    for league in leagues:
        league_id = league["league"]["id"]
        league_name = league["league"]["name"]

        over15_pct = get_league_stats(league_id, 2025)
        if over15_pct < 75:
            continue

        url = f"{BASE_URL}/teams?league={league_id}&season={2025}"
        teams = requests.get(url, headers=headers).json().get("response", [])

        for team in teams:
            team_id = team["team"]["id"]
            stats = get_team_stats(team_id, league_id, 2025)
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

            if win_rate > 60 and over15 > 70 and (home + away <= 1):
                msg = (f"⚽ [{league_name}] Equipa {team['team']['name']} "
                       f"tem {win_rate:.1f}% vitórias e {over15:.1f}% Over 1.5, "
                       f"mas no último jogo ficou {home}x{away}.")
                notify_telegram(msg)
                found = True

    if not found:
        notify_telegram(f"❌ Nenhum jogo encontrado nesta execução ({now})")

# rota só para teste
@app.route("/")
def home():
    return "✅ Bot ativo e a correr de hora em hora!"

# inicia scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_conditions, "interval", hours=1)
scheduler.start()

if __name__ == "__main__":
    # Executa uma vez no arranque
    check_conditions()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
