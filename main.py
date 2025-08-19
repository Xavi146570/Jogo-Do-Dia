import requests
import os

API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"
headers = {"x-apisports-key": API_KEY}


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
    over15 = sum(1 for f in fixtures if f["goals"]["home"] + f["goals"]["away"] > 1)
    return (over15 / len(fixtures)) * 100


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
            over15 = stats["goals"]["for"]["total"]["over_1.5"] / played * 100

            last_match = stats["fixtures"]["last"]
            if not last_match:
                continue

            home = last_match["goals"]["home"]
            away = last_match["goals"]["away"]

            if win_rate > 60 and over15 > 70 and (home + away <= 1):
                msg = (f"⚽ [{league_name}] Equipa {team['team']['name']} "
                       f"tem {win_rate:.1f}% vitórias e {over15:.1f}% Over 1.5, "
                       f"mas no último jogo ficou {home}x{away}.")
                notify_telegram(msg)


if __name__ == "__main__":
    check_conditions(season=2024)
