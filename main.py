import os
import requests
import datetime
import time
import threading
from flask import Flask, jsonify

# ========= CONFIG =========
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}

# ========= FLASK APP =========
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Bot de Futebol ativo ✅"})

# ========= FUNÇÕES =========
def notify_telegram(message):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def get_leagues(season):
    url = f"{BASE_URL}/leagues?season={season}"
    return requests.get(url, headers=headers).json().get("response", [])

def get_league_stats(league_id, season):
    url = f"{BASE_URL}/fixtures?league={league_id}&season={season}"
    res = requests.get(url, headers=headers).json()
    fixtures = res.get("response", [])
    if not fixtures:
        return 0
    valid = [f for f in fixtures if f["goals"]["home"] is not None and f["goals"]["away"] is not None]
    if not valid:
        return 0
    over15 = sum(1 for f in valid if f["goals"]["home"] + f["goals"]["away"] > 1)
    return (over15 / len(valid)) * 100

def get_team_stats(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season={season}&team={team_id}"
    return requests.get(url, headers=headers).json().get("response", {})

def check_conditions():
    """Verifica condições e envia resultados"""
    current_year = datetime.datetime.now().year
    now = datetime.datetime.now().strftime("%H:%M %d/%m")

    notify_telegram(f"[{now}] 🔎 Verificando condições para a época {current_year}...")

    leagues = get_leagues(current_year)
    found_any = False

    for league in leagues:
        league_id = league["league"]["id"]
        league_name = league["league"]["name"]

        over15_pct = get_league_stats(league_id, current_year)
        if over15_pct < 75:
            continue

        url = f"{BASE_URL}/teams?league={league_id}&season={current_year}"
        teams = requests.get(url, headers=headers).json().get("response", [])

        for team in teams:
            team_id = team["team"]["id"]
            stats = get_team_stats(team_id, league_id, current_year)
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
                msg = (f"⚽ [{league_name}] {team['team']['name']} "
                       f"- {win_rate:.1f}% vitórias, {over15:.1f}% Over 1.5, "
                       f"último jogo {home}x{away}")
                notify_telegram(msg)
                found_any = True

    if not found_any:
        notify_telegram(f"[{now}] Nenhum jogo encontrado nesta execução.")

# ========= LOOP EM BACKGROUND =========
def job_loop():
    while True:
        try:
            check_conditions()
        except Exception as e:
            notify_telegram(f"⚠️ Erro na execução: {e}")
        time.sleep(3600)  # espera 1 hora

threading.Thread(target=job_loop, daemon=True).start()

# ========= START =========
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

