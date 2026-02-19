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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot Multi-Liga Ativo! ✅", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def safe_float(value) -> float:
    try:
        if value is None: return 0.0
        if isinstance(value, str):
            value = value.replace('%', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0

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
        
        self.target_leagues = [88, 94, 323]
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.live_check_interval = 90
        self.sent_notifications = set()
        self.match_history = {}

    def send_startup_message(self):
        agora = datetime.now(self.timezone).strftime("%d/%m/%Y às %H:%M")
        msg = (
            f"🤖 *BOT MULTI-LIGA ATIVADO*\n\n"
            f"✅ *Status:* Funcionando perfeitamente\n"
            f"🕐 *Iniciado:* {agora} (Lisboa)\n\n"
            f"🌍 *Ligas:* Holanda, Portugal, Índia\n"
            f"🎯 *Estratégia:* 3 Balas (xG Estimado Ativo)\n"
            f"🔍 _Aguardando jogos ao vivo..._"
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
            s_dict = {str(s.get("type", "")).lower().replace("_", " ").strip(): s.get("value") for s in sg.get("statistics", [])}
            
            # 1. Tentar pegar xG Real
            xg = safe_float(s_dict.get("expected goals"))
            
            # 2. Se não houver xG, estimar baseado em SOT, Remates e Cantos
            if xg == 0:
                sot = safe_float(s_dict.get("shots on goal"))
                off_target = safe_float(s_dict.get("shots off goal"))
                corners = safe_float(s_dict.get("corner kicks"))
                xg = (sot * 0.25) + (off_target * 0.08) + (corners * 0.04)
            
            stats[f"xg_{tid}"] = xg
            stats[f"sot_{tid}"] = safe_float(s_dict.get("shots on goal"))
            
        return stats

    def check_momentum_and_stagnation(self, f: FixtureData):
        key = f"history_{f.fixture_id}"
        stats = self.get_live_match_stats(f.fixture_id)
        if not stats: return

        xg_h = stats.get(f"xg_{f.home_team_id}", 0.0)
        xg_a = stats.get(f"xg_{f.away_team_id}", 0.0)
        sot_h = stats.get(f"sot_{f.home_team_id}", 0.0)
        sot_a = stats.get(f"sot_{f.away_team_id}", 0.0)
        
        curr_xg = round(xg_h + xg_a, 2)
        curr_sot = int(sot_h + sot_a)
        now = datetime.now()

        if key not in self.match_history:
            self.match_history[key] = {"time": now, "xg": curr_xg, "sot": curr_sot}
            return

        last = self.match_history[key]
        if (now - last["time"]).total_seconds() >= 600:
            delta_xg = round(curr_xg - last["xg"], 2)
            delta_sot = curr_sot - last["sot"]

            if delta_xg <= 0.05 and f.elapsed_minutes < 85:
                msg = f"⚠️ *Estagnação [{f.league_name}]:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n📊 xG Estimado: {curr_xg} (ΔxG: +{delta_xg})\n💡 Evitar Over."
                self.bot.send_message(self.chat_id, msg)
            elif delta_xg >= 0.20 or delta_sot >= 2:
                msg = f"🔥 *Momentum [{f.league_name}]:* {f.home_team} vs {f.away_team} ({f.elapsed_minutes}')\n📊 xG Estimado: {curr_xg} (+{delta_xg})\n🎯 Jogo aqueceu!"
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
                        xg = stats.get(f"xg_{f.home_team_id}", 0.0) + stats.get(f"xg_{f.away_team_id}", 0.0)
                        sot = stats.get(f"sot_{f.home_team_id}", 0.0) + stats.get(f"sot_{f.away_team_id}", 0.0)
                        if xg >= 0.7 or sot >= 3:
                            self.bot.send_message(self.chat_id, f"🎯 *2ª Bala [{f.league_name}]:* {f.home_team} vs {f.away_team}\n📊 xG Est: {xg:.2f} | SOT: {int(sot)}\n🔥 Pressão detetada!")
                            self.sent_notifications.add(f"{key_prefix}_30")

    def keep_alive_ping(self):
        try:
            url = f"https://{self.render_url}" if self.render_url else "http://localhost:10000"
            requests.get(url, timeout=5)
        except Exception: pass

def main():
    Thread(target=run_flask, daemon=True).start()
    bot = EredivisieHighPotentialBot()
    bot.send_startup_message()
    schedule.every(bot.live_check_interval).seconds.do(bot.run_live_check)
    schedule.every(10).minutes.do(bot.keep_alive_ping)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
