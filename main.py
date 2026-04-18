import os
import requests
import json
from datetime import datetime
import schedule
import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import pytz
from flask import Flask
from threading import Thread

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

NOTIFICATIONS_FILE = "sent_notifications.json"
RENDER_URL = "https://jogo-do-dia.onrender.com"

@flask_app.route('/')
def home():
    return "🤖 Bot Top 5 & 3 Balas Ativo! ✅", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def self_ping():
    """Faz ping ao próprio serviço para evitar sleep do Render"""
    try:
        r = requests.get(RENDER_URL, timeout=10)
        logger.info(f"🔁 Self-ping OK ({r.status_code})")
    except Exception as e:
        logger.warning(f"⚠️ Self-ping falhou: {e}")

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
    league_id: int
    league_name: str
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    elapsed_minutes: int
    score_home: int
    score_away: int

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id: str, text: str) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": 'Markdown'}
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception: return False

class StrategyBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}
        self.bot = TelegramBot(self.bot_token)
        
        self.target_leagues = [88, 94, 323]  # Holanda, Portugal, Índia
        self.top_teams_cache: Dict[int, Set[int]] = {}
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.last_top_teams_update = None

        # Carrega notificações persistidas do disco
        self.sent_notifications: Set[str] = self._load_notifications()

    # ── Persistência de notificações ──────────────────────────────────────────

    def _load_notifications(self) -> Set[str]:
        """Carrega notificações já enviadas do ficheiro JSON (evita duplicados após reinício)"""
        try:
            if os.path.exists(NOTIFICATIONS_FILE):
                with open(NOTIFICATIONS_FILE, "r") as f:
                    data = json.load(f)
                    # Limpa entradas com mais de 2 dias para não crescer indefinidamente
                    cutoff = datetime.now().timestamp() - 172800  # 48h
                    cleaned = {k: v for k, v in data.items() if v > cutoff}
                    logger.info(f"📂 {len(cleaned)} notificações carregadas do disco.")
                    return set(cleaned.keys())
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar notificações: {e}")
        return set()

    def _save_notifications(self):
        """Guarda notificações no disco com timestamp"""
        try:
            # Lê o ficheiro existente para manter timestamps
            existing = {}
            if os.path.exists(NOTIFICATIONS_FILE):
                with open(NOTIFICATIONS_FILE, "r") as f:
                    existing = json.load(f)
            
            now_ts = datetime.now().timestamp()
            for key in self.sent_notifications:
                if key not in existing:
                    existing[key] = now_ts
            
            # Limpa entradas antigas (> 48h)
            cutoff = now_ts - 172800
            existing = {k: v for k, v in existing.items() if v > cutoff}

            with open(NOTIFICATIONS_FILE, "w") as f:
                json.dump(existing, f)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao guardar notificações: {e}")

    def _mark_sent(self, key: str):
        """Regista notificação como enviada e persiste"""
        self.sent_notifications.add(key)
        self._save_notifications()

    # ── Top 5 ─────────────────────────────────────────────────────────────────

    def update_top_teams(self):
        now = datetime.now()
        if self.last_top_teams_update and (now - self.last_top_teams_update).total_seconds() < 86400:
            return

        current_year = now.year
        for league_id in self.target_leagues:
            found_standings = False
            for season in [current_year, current_year - 1]:
                if found_standings: break
                logger.info(f"A procurar classificação para Liga {league_id} na época {season}...")
                params = {"league": league_id, "season": season}
                data = self.make_api_request("standings", params)
                if data and data.get("response") and len(data["response"]) > 0:
                    try:
                        league_data = data["response"][0]["league"]
                        standings = league_data["standings"][0]
                        top_5 = {team["team"]["id"] for team in standings[:5]}
                        self.top_teams_cache[league_id] = top_5
                        logger.info(f"✅ Top 5 carregado (Liga {league_id}, Época {season}): {len(top_5)} equipas.")
                        found_standings = True
                    except (KeyError, IndexError):
                        continue
            if not found_standings:
                logger.warning(f"⚠️ Não foi possível encontrar classificação para a Liga {league_id}.")

        self.last_top_teams_update = now

    # ── API ───────────────────────────────────────────────────────────────────

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=20)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro API: {e}")
            return None

    def get_live_match_stats(self, fixture_id: int) -> Optional[Dict]:
        data = self.make_api_request("fixtures/statistics", {"fixture": fixture_id})
        if not data or not data.get("response"): return None
        
        stats = {}
        for team_data in data["response"]:
            tid = team_data["team"]["id"]
            s_dict = {s["type"].lower(): s["value"] for s in team_data["statistics"] if s["type"]}
            sot = safe_float(s_dict.get("shots on goal"))
            off_target = safe_float(s_dict.get("shots off goal"))
            corners = safe_float(s_dict.get("corner kicks"))
            estimated_xg = (sot * 0.18) + (off_target * 0.06) + (corners * 0.03)
            stats[f"xg_{tid}"] = estimated_xg
            stats[f"sot_{tid}"] = sot
        return stats

    # ── Check principal ───────────────────────────────────────────────────────

    def run_live_check(self):
        self.update_top_teams()
        data = self.make_api_request("fixtures", {"live": "all"})
        if not data or not data.get("response"): return

        for f in data["response"]:
            l_id = f['league']['id']
            if l_id not in self.target_leagues: continue

            fix_id = f['fixture']['id']
            h_id, a_id = f['teams']['home']['id'], f['teams']['away']['id']

            top_teams = self.top_teams_cache.get(l_id, set())
            if h_id not in top_teams and a_id not in top_teams:
                continue

            elapsed = f['fixture']['status']['elapsed'] or 0
            score_h = f['goals']['home'] or 0
            score_a = f['goals']['away'] or 0
            total_goals = score_h + score_a

            key_prefix = f"match_{fix_id}"
            stats = self.get_live_match_stats(fix_id)
            if not stats: continue

            total_xg = round(stats.get(f"xg_{h_id}", 0) + stats.get(f"xg_{a_id}", 0), 2)
            total_sot = int(stats.get(f"sot_{h_id}", 0) + stats.get(f"sot_{a_id}", 0))

            # 1ª BALA: 15' - 25'
            if 15 <= elapsed <= 25 and total_goals == 0:
                key = f"{key_prefix}_b1"
                if key not in self.sent_notifications and total_xg >= 0.35:
                    self.send_alert("1ª BALA 🎯", f, elapsed, total_xg, total_sot)
                    self._mark_sent(key)

            # 2ª BALA: 30' - 40'
            elif 30 <= elapsed <= 40 and total_goals <= 1:
                key = f"{key_prefix}_b2"
                if key not in self.sent_notifications and total_xg >= 0.75:
                    self.send_alert("2ª BALA 🔥", f, elapsed, total_xg, total_sot)
                    self._mark_sent(key)

            # 3ª BALA: 60' - 75'
            elif 60 <= elapsed <= 75 and total_goals <= 2:
                key = f"{key_prefix}_b3"
                if key not in self.sent_notifications and total_xg >= 1.35:
                    self.send_alert("3ª BALA 🚀", f, elapsed, total_xg, total_sot)
                    self._mark_sent(key)

    def send_alert(self, title, f, minute, xg, sot):
        msg = (
            f"{title}\n"
            f"🏟 *Jogo:* {f['teams']['home']['name']} vs {f['teams']['away']['name']}\n"
            f"🏆 *Liga:* {f['league']['name']}\n"
            f"⏰ *Minuto:* {minute}' | 🟢 *Top 5 Ativo*\n"
            f"📊 *xG Total:* {xg:.2f} (Alinhado Tabela)\n"
            f"🎯 *SOT Total:* {sot}\n"
            f"💰 *Sugestão:* Over Golo HT/FT"
        )
        self.bot.send_message(self.chat_id, msg)

def main():
    Thread(target=run_flask, daemon=True).start()
    bot = StrategyBot()
    bot.bot.send_message(bot.chat_id, "🤖 *BOT TOP 5 & 3 BALAS ONLINE*\nFiltros de xG calibrados pela imagem. 🚀")

    schedule.every(60).seconds.do(bot.run_live_check)
    schedule.every(14).minutes.do(self_ping)  # ← Mantém o Render acordado

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
