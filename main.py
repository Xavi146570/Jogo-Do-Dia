import os
import requests
import json
from datetime import datetime, timedelta
import schedule
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pytz
from flask import Flask
from threading import Thread
import math

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask App
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot Eredivisie está rodando! ✅", 200

@flask_app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}, 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

@dataclass
class TeamStats:
    team_id: int
    name: str
    goals_avg_last4: float
    games_played: int
    last_update: datetime

@dataclass
class FixtureData:
    fixture_id: int
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    kickoff_time: datetime
    status: str
    elapsed_minutes: int
    score_home: int
    score_away: int

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown') -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False

class EredivisieHighPotentialBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.render_url = os.getenv("RENDER_EXTERNAL_URL", "")
        
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}
        self.bot = TelegramBot(self.bot_token)
        
        self.league_id = 88
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.current_season = 2025
        self.live_check_interval = 90
        self.sent_notifications = set()
        self.team_stats_cache = {}

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro na API: {e}")
            return None

    def poisson_cdf(self, k, lam):
        cdf = 0
        for i in range(k + 1):
            cdf += (math.exp(-lam) * (lam**i)) / math.factorial(i)
        return cdf

    def calculate_fair_odds(self, xg_home: float, xg_away: float, market: str = "over_2_5") -> float:
        total_xg = xg_home + xg_away
        if total_xg <= 0: return 999
        
        if market == "over_2_5":
            prob = 1 - self.poisson_cdf(2, total_xg)
            return round(1 / prob, 2) if prob > 0.01 else 999
        elif market == "over_1_5":
            prob = 1 - self.poisson_cdf(1, total_xg)
            return round(1 / prob, 2) if prob > 0.01 else 999
        return 999

    def get_today_fixtures(self) -> List[FixtureData]:
        today = datetime.now(self.timezone).strftime("%Y-%m-%d")
        params = {"league": self.league_id, "season": self.current_season, "date": today, "timezone": "Europe/Lisbon"}
        data = self.make_api_request("fixtures", params)
        if not data or not data.get("response"): return []
        
        fixtures = []
        for f in data["response"]:
            fix = f['fixture']
            teams = f['teams']
            goals = f['goals']
            fixtures.append(FixtureData(
                fixture_id=fix['id'],
                home_team=teams['home']['name'],
                away_team=teams['away']['name'],
                home_team_id=teams['home']['id'],
                away_team_id=teams['away']['id'],
                kickoff_time=datetime.fromisoformat(fix['date'].replace('Z', '+00:00')),
                status=fix['status']['short'],
                elapsed_minutes=fix['status']['elapsed'] or 0,
                score_home=goals['home'] or 0,
                score_away=goals['away'] or 0
            ))
        return fixtures

    def send_daily_fixtures_message(self):
        fixtures = self.get_today_fixtures()
        if not fixtures:
            msg = "📅 Hoje não há jogos da Eredivisie."
        else:
            msg = "📅 *Jogos da Eredivisie hoje:*\n\n"
            for f in fixtures:
                kickoff_str = f.kickoff_time.strftime("%H:%M")
                msg += f"• {f.home_team} vs {f.away_team} às {kickoff_str}\n"
        self.bot.send_message(self.chat_id, msg)

    def get_live_fixtures(self) -> List[FixtureData]:
        params = {"league": self.league_id, "season": self.current_season, "live": "all"}
        data = self.make_api_request("fixtures", params)
        if not data or not data.get("response"): return []
        
        fixtures = []
        for f in data["response"]:
            fix = f['fixture']
            teams = f['teams']
            goals = f['goals']
            fixtures.append(FixtureData(
                fixture_id=fix['id'],
                home_team=teams['home']['name'],
                away_team=teams['away']['name'],
                home_team_id=teams['home']['id'],
                away_team_id=teams['away']['id'],
                kickoff_time=datetime.fromisoformat(fix['date'].replace('Z', '+00:00')),
                status=fix['status']['short'],
                elapsed_minutes=fix['status']['elapsed'] or 0,
                score_home=goals['home'] or 0,
                score_away=goals['away'] or 0
            ))
        return fixtures

    def get_live_match_stats(self, fixture_id: int) -> Optional[Dict]:
        endpoint = f"fixtures/statistics"
        params = {"fixture": fixture_id}
        data = self.make_api_request(endpoint, params)
        if not data or not data.get("response"): return None

        stats = {}
        for stat_group in data["response"]:
            team_id = stat_group.get("team", {}).get("id")
            for stat in stat_group.get("statistics", []):
                stat_type = stat.get("type")
                value = stat.get("value")
                if stat_type in ["Shots on Goal", "Corners", "Big Chances", "Expected Goals"]:
                    key = stat_type.lower().replace(" ", "_")
                    stats[f"{key}_team_{team_id}"] = value
        return stats

    def run_live_check(self):
        logger.info("⚽ Verificando jogos ao vivo...")
        fixtures = self.get_live_fixtures()
        for f in fixtures:
            key_prefix = f"bala_{f.fixture_id}"
            
            if f.elapsed_minutes == 20 and f.score_home == 0 and f.score_away == 0:
                if f"{key_prefix}_20" not in self.sent_notifications:
                    msg = f"🎯 *1ª Bala:* {f.home_team} vs {f.away_team} aos 20'. Monitorizando xG e SOT..."
                    self.bot.send_message(self.chat_id, msg)
                    self.sent_notifications.add(f"{key_prefix}_20")

            elif 25 <= f.elapsed_minutes <= 35 and f.score_home == 0 and f.score_away == 0:
                if f"{key_prefix}_30" not in self.sent_notifications:
                    stats = self.get_live_match_stats(f.fixture_id)
                    if stats:
                        xg_h = float(stats.get(f"expected_goals_team_{f.home_team_id}", 0) or 0)
                        xg_a = float(stats.get(f"expected_goals_team_{f.away_team_id}", 0) or 0)
                        sot = (int(stats.get(f"shots_on_goal_team_{f.home_team_id}", 0) or 0) +
                               int(stats.get(f"shots_on_goal_team_{f.away_team_id}", 0) or 0))
                        
                        if (xg_h + xg_a) >= 0.8 and sot >= 3:
                            fair_o25 = self.calculate_fair_odds(xg_h, xg_a, "over_2_5")
                            msg = f"🎯 *2ª Bala:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n📊 xG: {xg_h+xg_a:.2f} | SOT: {sot}\n⚖️ Fair Odd O2.5: {fair_o25}"
                            self.bot.send_message(self.chat_id, msg)
                            self.sent_notifications.add(f"{key_prefix}_30")

            elif 60 <= f.elapsed_minutes <= 75:
                if f"{key_prefix}_65" not in self.sent_notifications:
                    stats = self.get_live_match_stats(f.fixture_id)
                    if stats:
                        xg_h = float(stats.get(f"expected_goals_team_{f.home_team_id}", 0) or 0)
                        xg_a = float(stats.get(f"expected_goals_team_{f.away_team_id}", 0) or 0)
                        sot = (int(stats.get(f"shots_on_goal_team_{f.home_team_id}", 0) or 0) +
                               int(stats.get(f"shots_on_goal_team_{f.away_team_id}", 0) or 0))
                        
                        if (xg_h + xg_a) >= 1.2 and sot >= 5:
                            msg = f"🎯 *3ª Bala:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n🔥 Pressão Máxima! xG: {xg_h+xg_a:.2f} | SOT: {sot}"
                            self.bot.send_message(self.chat_id, msg)
                            self.sent_notifications.add(f"{key_prefix}_65")

    def keep_alive_ping(self):
        try:
            url = f"https://{self.render_url}" if self.render_url else "http://localhost:10000"
            requests.get(url, timeout=5)
            logger.info("📡 Ping keep-alive enviado.")
        except Exception as e:
            logger.warning(f"⚠️ Erro keep-alive: {e}")

def main():
    Thread(target=run_flask, daemon=True).start()
    bot = EredivisieHighPotentialBot()

    schedule.every(bot.live_check_interval).seconds.do(bot.run_live_check)
    schedule.every(10).minutes.do(bot.keep_alive_ping)
    schedule.every().day.at("09:00").do(bot.send_daily_fixtures_message)

    logger.info("🚀 Bot iniciado com notificações diárias!")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
