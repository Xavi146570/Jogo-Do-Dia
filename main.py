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

@flask_app.route('/')
def home():
    return "🤖 Bot Top 5 & 3 Balas Ativo! ✅", 200

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
        
        self.target_leagues = [88, 94, 323] # Holanda, Portugal, Índia
        self.top_teams_cache: Dict[int, Set[int]] = {}
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.sent_notifications = set()
        self.last_top_teams_update = None

    def update_top_teams(self):
        """Busca o Top 5 de cada liga alvo com detecção automática de época"""
        now = datetime.now()
        # Atualiza a cada 24 horas
        if self.last_top_teams_update and (now - self.last_top_teams_update).total_seconds() < 86400:
            return 

        current_year = now.year
        
        for league_id in self.target_leagues:
            found_standings = False
            # Tenta o ano atual e o anterior (cobre 2024, 2025, 2026...)
            for season in [current_year, current_year - 1]:
                if found_standings: break
                
                logger.info(f"A procurar classificação para Liga {league_id} na época {season}...")
                params = {"league": league_id, "season": season}
                data = self.make_api_request("standings", params)
                
                if data and data.get("response") and len(data["response"]) > 0:
                    try:
                        # A estrutura da API pode variar, tentamos capturar a tabela
                        league_data = data["response"][0]["league"]
                        standings = league_data["standings"][0]
                        
                        # Extrair IDs do Top 5
                        top_5 = {team["team"]["id"] for team in standings[:5]}
                        self.top_teams_cache[league_id] = top_5
                        
                        logger.info(f"✅ Top 5 carregado (Liga {league_id}, Época {season}): {len(top_5)} equipas.")
                        found_standings = True
                    except (KeyError, IndexError):
                        continue
            
            if not found_standings:
                logger.warning(f"⚠️ Não foi possível encontrar classificação para a Liga {league_id}.")

        self.last_top_teams_update = now

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
            
            # xG Estimado (Baseado na tua tabela e modelo de pressão)
            sot = safe_float(s_dict.get("shots on goal"))
            off_target = safe_float(s_dict.get("shots off goal"))
            corners = safe_float(s_dict.get("corner kicks"))
            
            # Modelo calibrado: SOT tem peso maior, cantos e chutes fora ajudam no volume
            estimated_xg = (sot * 0.18) + (off_target * 0.06) + (corners * 0.03)
            
            stats[f"xg_{tid}"] = estimated_xg
            stats[f"sot_{tid}"] = sot
        return stats

    def run_live_check(self):
        self.update_top_teams()
        data = self.make_api_request("fixtures", {"live": "all"})
        if not data or not data.get("response"): return

        for f in data["response"]:
            l_id = f['league']['id']
            if l_id not in self.target_leagues: continue

            fix_id = f['fixture']['id']
            h_id, a_id = f['teams']['home']['id'], f['teams']['away']['id']
            
            # FILTRO TOP 5: Pelo menos uma equipa deve estar no Top 5 da liga
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

            # --- LÓGICA DAS 3 BALAS (ALINHADA COM A IMAGEM) ---
            
            # 1ª BALA: 15' - 25' (xG Total Normal/Alto >= 0.35)
            if 15 <= elapsed <= 25 and total_goals == 0:
                if f"{key_prefix}_b1" not in self.sent_notifications and total_xg >= 0.35:
                    self.send_alert("1ª BALA 🎯", f, elapsed, total_xg, total_sot)
                    self.sent_notifications.add(f"{key_prefix}_b1")

            # 2ª BALA: 30' - 40' (xG Total Normal/Alto >= 0.75)
            elif 30 <= elapsed <= 40 and total_goals <= 1:
                if f"{key_prefix}_b2" not in self.sent_notifications and total_xg >= 0.75:
                    self.send_alert("2ª BALA 🔥", f, elapsed, total_xg, total_sot)
                    self.sent_notifications.add(f"{key_prefix}_b2")

            # 3ª BALA: 60' - 75' (xG Total Normal/Alto >= 1.35)
            elif 60 <= elapsed <= 75 and total_goals <= 2:
                if f"{key_prefix}_b3" not in self.sent_notifications and total_xg >= 1.35:
                    self.send_alert("3ª BALA 🚀", f, elapsed, total_xg, total_sot)
                    self.sent_notifications.add(f"{key_prefix}_b3")

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
    # Alerta de Inicialização
    bot.bot.send_message(bot.chat_id, "🤖 *BOT TOP 5 & 3 BALAS ONLINE*\nFiltros de xG calibrados pela imagem. 🚀")
    
    schedule.every(60).seconds.do(bot.run_live_check)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
