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

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot Multi-Liga Ativo! ✅", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

@dataclass
class FixtureData:
    fixture_id: int
    league_name: str
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
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
        except Exception:
            return False

class EredivisieHighPotentialBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.render_url = os.getenv("RENDER_EXTERNAL_URL", "").replace("https://", "").replace("http://", "")
        
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}
        self.bot = TelegramBot(self.bot_token)
        
        # Ligas Ativas: Holanda (88), Portugal (94), Índia (323)
        self.target_leagues = [88, 94, 323]
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.live_check_interval = 90
        self.sent_notifications = set()
        self.match_history = {}

    def send_startup_message(self):
        """Envia confirmação de que o bot iniciou após o deploy"""
        agora = datetime.now(self.timezone).strftime("%d/%m/%Y às %H:%M")
        msg = (
            f"🤖 *BOT MULTI-LIGA ATIVADO*\n\n"
            f"✅ *Status:* Funcionando perfeitamente\n"
            f"🕐 *Iniciado:* {agora} (Lisboa)\n\n"
            f"🌍 *Ligas Monitorizadas:*\n"
            f"• Holanda (Eredivisie)\n"
            f"• Portugal (Liga Portugal)\n"
            f"• Índia (Super League)\n\n"
            f"🎯 *Estratégia:* 3 Balas (xG + SOT)\n"
            f"⚠️ *Alertas:* Estagnação e Momentum ativos\n\n"
            f"🔍 _Aguardando jogos ao vivo nestas ligas..._"
        )
        self.bot.send_message(self.chat_id, msg)

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

    def calculate_fair_odds(self, xg_home: float, xg_away: float) -> float:
        total_xg = xg_home + xg_away
        if total_xg <= 0: return 999
        prob = 1 - self.poisson_cdf(2, total_xg)
        return round(1 / prob, 2) if prob > 0.01 else 999

    def get_live_fixtures(self) -> List[FixtureData]:
        params = {"live": "all"}
        data = self.make_api_request("fixtures", params)
        if not data or not data.get("response"): return []
        
        fixtures = []
        for f in data["response"]:
            if f['league']['id'] in self.target_leagues:
                fix, teams, goals = f['fixture'], f['teams'], f['goals']
                fixtures.append(FixtureData(
                    fixture_id=fix['id'], league_name=f['league']['name'],
                    home_team=teams['home']['name'], away_team=teams['away']['name'],
                    home_team_id=teams['home']['id'], away_team_id=teams['away']['id'],
                    status=fix['status']['short'], elapsed_minutes=fix['status']['elapsed'] or 0,
                    score_home=goals['home'] or 0, score_away=goals['away'] or 0
                ))
        return fixtures

    def get_live_match_stats(self, fixture_id: int) -> Optional[Dict]:
        params = {"fixture": fixture_id}
        data = self.make_api_request("fixtures/statistics", params)
        if not data or not data.get("response"): return None
        stats = {}
        for sg in data["response"]:
            tid = sg.get("team", {}).get("id")
            for s in sg.get("statistics", []):
                if s.get("type") in ["Shots on Goal", "Expected Goals"]:
                    key = s.get("type").lower().replace(" ", "_")
                    stats[f"{key}_team_{tid}"] = s.get("value")
        return stats

    def check_momentum_and_stagnation(self, f: FixtureData):
        key = f"history_{f.fixture_id}"
        stats = self.get_live_match_stats(f.fixture_id)
        if not stats: return

        xg_h = float(stats.get(f"expected_goals_team_{f.home_team_id}", 0) or 0)
        xg_a = float(stats.get(f"expected_goals_team_{f.away_team_id}", 0) or 0)
        sot_h = int(stats.get(f"shots_on_goal_team_{f.home_team_id}", 0) or 0)
        sot_a = int(stats.get(f"shots_on_goal_team_{f.away_team_id}", 0) or 0)
        
        curr_xg, curr_sot = round(xg_h + xg_a, 2), sot_h + sot_a
        now = datetime.now()

        if key not in self.match_history:
            self.match_history[key] = {"time": now, "xg": curr_xg, "sot": curr_sot}
            return

        last = self.match_history[key]
        if (now - last["time"]).total_seconds() >= 600: # 10 minutos
            delta_xg = round(curr_xg - last["xg"], 2)
            delta_sot = curr_sot - last["sot"]

            if delta_xg <= 0.05:
                msg = f"⚠️ *Estagnação [{f.league_name}]:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n📊 xG: {curr_xg} (ΔxG: +{delta_xg})\n💡 Evitar Over."
                self.bot.send_message(self.chat_id, msg)
            elif delta_xg >= 0.15 or delta_sot >= 3:
                msg = f"🔥 *Momentum [{f.league_name}]:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n📊 xG: {curr_xg} (+{delta_xg})\n🎯 Jogo aqueceu!"
                self.bot.send_message(self.chat_id, msg)

            self.match_history[key] = {"time": now, "xg": curr_xg, "sot": curr_sot}

    def run_live_check(self):
        fixtures = self.get_live_fixtures()
        for f in fixtures:
            self.check_momentum_and_stagnation(f)
            key_prefix = f"bala_{f.fixture_id}"
            
            if f.elapsed_minutes == 20 and f.score_home == 0 and f.score_away == 0:
                if f"{key_prefix}_20" not in self.sent_notifications:
                    self.bot.send_message(self.chat_id, f"🎯 *1ª Bala [{f.league_name}]:* {f.home_team} vs {f.away_team} (20')")
                    self.sent_notifications.add(f"{key_prefix}_20")

            elif 25 <= f.elapsed_minutes <= 35 and f.score_home == 0 and f.score_away == 0:
                if f"{key_prefix}_30" not in self.sent_notifications:
                    stats = self.get_live_match_stats(f.fixture_id)
                    if stats:
                        xg = float(stats.get(f"expected_goals_team_{f.home_team_id}", 0) or 0) + float(stats.get(f"expected_goals_team_{f.away_team_id}", 0) or 0)
                        sot = int(stats.get(f"shots_on_goal_team_{f.home_team_id}", 0) or 0) + int(stats.get(f"shots_on_goal_team_{f.away_team_id}", 0) or 0)
                        if xg >= 0.8 and sot >= 3:
                            fair = self.calculate_fair_odds(xg, 0)
                            self.bot.send_message(self.chat_id, f"🎯 *2ª Bala [{f.league_name}]:* {f.home_team} vs {f.away_team}\n📊 xG: {xg:.2f} | SOT: {sot}\n⚖️ Fair Odd O2.5: {fair}")
                            self.sent_notifications.add(f"{key_prefix}_30")

    def keep_alive_ping(self):
        try:
            url = f"https://{self.render_url}" if self.render_url else "http://localhost:10000"
            requests.get(url, timeout=5)
        except Exception: pass

def main():
    Thread(target=run_flask, daemon=True).start()
    bot = EredivisieHighPotentialBot()
    
    # Envia a mensagem de inicialização assim que o bot começa
    bot.send_startup_message()
    
    schedule.every(bot.live_check_interval).seconds.do(bot.run_live_check)
    schedule.every(10).minutes.do(bot.keep_alive_ping)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
