import os
import time
import threading
import requests
from flask import Flask
from datetime import datetime

API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

app = Flask(__name__)

def notify_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

def get_leagues(season=2024):
    url = f"{BASE_URL}/leagues?season={season}"
    return requests.get(url, headers=headers).json().get("response", [])

def get_league_stats(league_id, season=2024):
    url = f"{BASE_URL}/fixtures?league={league_id}&season={season}"
    res = requests.get(url, headers=headers).json()
    fixtures = res.get("response", [])
    if not fixtures:
        return 0
    valid_fixtures = [f for f in fixtures if f["goals"]["home"] is not None and f["goals"]["away"] is not None]
    if not valid_fixtures:
        return 0
    over15 = sum(1 for f in valid_fixtures if f["goals"]["home"] + f["goals"]["away"] > 1)
    return (over15 / len(valid_fixtures)) * 100

def get_team_stats(team_id, league_id, season=2024):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season={season}&team={team_id}"
    return requests.get(url, headers=headers).json().get("response", {})

def check_conditions(season=2024):
    leagues = get_leagues(season)
    for league in leagues:
        league_id = league["league"]["id"]
        league_name = league["league"]["name"]

        over15_pct = get_league_stats(league_id, season)
        if over15_pct < 75:
            continue

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

            if win_rate > 60 and over15 > 70 and (home + away <= 1):
                msg = (f"⚽ [{league_name}] Equipa {team['team']['name']} "
                       f"tem {win_rate:.1f}% vitórias e {over15:.1f}% Over 1.5, "
                       f"mas no último jogo ficou {home}x{away}.")
                notify_telegram(msg)

# 🔹 Agendador: roda de hora em hora só aos sábados e domingos
def scheduler():
    last_run_hour = None
    while True:
        now = datetime.now()
        weekday = now.weekday()  # segunda=0 ... domingo=6

        if weekday in (5, 6):  # sábado (5) e domingo (6)
            if last_run_hour != now.hour:  # executa apenas uma vez por hora
                check_conditions(season=2024)
                last_run_hour = now.hour

        time.sleep(30)  # checa a cada 30 segundos

# 🔹 Rota web só para manter serviço ativo
@app.route("/")
def home():
    return "Bot de estatísticas ativo ✅"

if __name__ == "__main__":
    # inicia agendador em paralelo
    threading.Thread(target=scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
