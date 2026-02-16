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

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot Eredivisie Ativo! ✅", 200

@flask_app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}, 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

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
            logger.error(f"Erro Telegram: {e}")
            return False

class EredivisieHighPotentialBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.render_url = os.getenv("RENDER_EXTERNAL_URL", "") # URL do seu app no Render
        
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}
        self.bot = TelegramBot(self.bot_token)
        
        self.league_id = 88 
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.current_season = 2025 # Ajuste conforme a época
        
        self.min_goals_avg = 2.3
        self.live_check_interval = 90
        self.sent_notifications = set()
        self.team_stats_cache = {}

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro API: {e}")
            return None

    def keep_alive(self):
        """Evita que o Render adormeça chamando a própria URL"""
        if self.render_url:
            try:
                requests.get(self.render_url, timeout=10)
                logger.info("📡 Keep-alive: Ping enviado com sucesso.")
            except Exception as e:
                logger.error(f"❌ Erro no Keep-alive: {e}")

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

    def run_live_check(self):
        """Lógica principal de monitorização ao vivo"""
        logger.info("⚽ Verificando jogos ao vivo...")
        fixtures = self.get_live_fixtures()
        for f in fixtures:
            # Exemplo: Alerta no minuto 20 se estiver 0-0 (Início da estratégia das 3 balas)
            if f.elapsed_minutes == 20 and f.score_home == 0 and f.score_away == 0:
                msg = f"🎯 *Estratégia 3 Balas:* {f.home_team} vs {f.away_team} aos 20'. Monitorizar xG e Odd Neutra!"
                self.bot.send_message(self.chat_id, msg)

def main():
    # Iniciar Servidor Web
    Thread(target=run_flask, daemon=True).start()
    
    bot = EredivisieHighPotentialBot()
    
    # Agendamentos
    schedule.every(bot.live_check_interval).seconds.do(bot.run_live_check)
    schedule.every(10).minutes.do(bot.keep_alive) # Ping a cada 10 min
    
    logger.info("🚀 Bot iniciado e protegido contra hibernação!")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
