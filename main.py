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

# Criar app Flask para o Render
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 Bot Eredivisie está rodando! ✅", 200

@flask_app.route('/health')
def health():
    return {"status": "ok", "bot": "running", "service": "eredivisie_bot"}, 200

def run_flask():
    """Roda o servidor Flask em uma thread separada"""
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
    """Cliente simples do Telegram usando requests"""
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'Markdown') -> bool:
        """Envia mensagem via API do Telegram"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False

class EredivisieHighPotentialBot:
    def __init__(self):
        # Validação das variáveis de ambiente
        self.api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        
        # Debug das variáveis
        logger.info("🔍 Verificando variáveis de ambiente...")
        logger.info(f"FOOTBALL_API_KEY: {'✅ Definida' if self.api_key else '❌ Não definida'}")
        logger.info(f"TELEGRAM_BOT_TOKEN: {'✅ Definida' if self.bot_token else '❌ Não definida'}")
        logger.info(f"TELEGRAM_CHAT_ID: {'✅ Definida' if self.chat_id else '❌ Não definida'}")
        
        # Validação rigorosa
        missing_vars = []
        if not self.api_key:
            missing_vars.append("FOOTBALL_API_KEY")
        if not self.bot_token:
            missing_vars.append("TELEGRAM_BOT_TOKEN")
        if not self.chat_id:
            missing_vars.append("TELEGRAM_CHAT_ID")
            
        if missing_vars:
            error_msg = f"❌ Variáveis de ambiente não configuradas: {', '.join(missing_vars)}"
            logger.error(error_msg)
            logger.error("💡 Configure as variáveis no Render Dashboard > Environment")
            raise ValueError(error_msg)
        
        # Inicialização dos componentes
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": self.api_key}
        
        try:
            # Criar bot do Telegram (versão simplificada com requests)
            self.bot = TelegramBot(self.bot_token)
            logger.info("✅ Bot do Telegram inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar bot do Telegram: {e}")
            raise ValueError(f"Token do Telegram inválido: {e}")
        
        # Configurações da liga
        self.league_id = 88  # Eredivisie
        self.timezone = pytz.timezone('Europe/Lisbon')
        self.current_season = self._get_current_eredivisie_season()
        
        # Critérios definidos pelo usuário
        self.min_goals_avg = 2.3
        self.last_n_games = 4
        self.min_games_required = 4
        self.pre_game_hours = 4
        self.peak_minutes = [60, 75, 85]
        self.live_check_interval = 90
        
        # Padrões mínimos históricos da Eredivisie (últimos 5 anos)
        self.league_patterns_min = {
            "avg_goals_per_game": 2.89,
            "avg_ht_goals": 1.18,
            "btts_percentage": 58.0,
            "over_25_percentage": 58.0,
            "over_35_percentage": 32.0,
            "over_15_percentage": 80.0,
            "second_half_percentage": 53.0,
            "goals_46_60_min": 16.0,
            "goals_61_75_min": 17.0,
            "goals_76_90_min": 22.0
        }
        
        # Cache e controle de notificações
        self.team_stats_cache = {}
        self.cache_ttl_hours = 4
        self.sent_notifications = set()
        
        logger.info(f"✅ Bot Eredivisie inicializado - Temporada {self.current_season}/{self.current_season + 1}")

    def _get_current_eredivisie_season(self) -> int:
        """Calcula a temporada atual da Eredivisie dinamicamente"""
        now = datetime.now(self.timezone)
        # Eredivisie: Agosto-Maio (temporada inicia em agosto)
        if now.month >= 8:  # Agosto em diante = nova temporada
            return now.year
        else:  # Janeiro-Julho = temporada anterior
            return now.year - 1

    def test_connections(self) -> bool:
        """Testa conexões com API e Telegram"""
        logger.info("🧪 Testando conexões...")
        
        # Teste da API Football
        try:
            test_url = f"{self.base_url}/status"
            response = requests.get(test_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                requests_remaining = data.get("response", {}).get("requests", {}).get("current", "N/A")
                logger.info(f"✅ API-Sports OK - Requests restantes: {requests_remaining}")
            else:
                logger.error(f"❌ Erro na API-Sports: Status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Erro ao testar API-Sports: {e}")
            return False
        
        # Teste do Telegram com mensagem inicial
        try:
            test_message = f"""🤖 **BOT EREDIVISIE ATIVADO**

✅ **Status:** Funcionando perfeitamente
🕐 **Iniciado:** {datetime.now(self.timezone).strftime('%d/%m/%Y às %H:%M')} (Lisboa)
📅 **Temporada:** {self.current_season}/{self.current_season + 1}

📋 **Configurações:**
• Filtro: ≥ 1 equipe com 2.3+ gols/jogo (últimos 4)
• Pré-jogo: 4h antes do início
• Ao vivo: Minutos 60', 75', 85' (se 0x0)
• Verificação: A cada 30min + ao vivo 90s

🔍 **Aguardando jogos que atendam aos critérios...**

💡 Você só receberá notificações quando houver jogos qualificados!

🎯 Próxima rodada típica: Sábados 16:30-20:00 / Domingos 12:15-16:45"""

            if self.bot.send_message(self.chat_id, test_message):
                logger.info("✅ Mensagem de ativação enviada")
                return True
            else:
                logger.error("❌ Falha ao enviar mensagem de teste")
                return False
        except Exception as e:
            logger.error(f"❌ Erro ao testar Telegram: {e}")
            return False

    def make_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Faz requisição à API com tratamento robusto de erros"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("response"):
                logger.debug(f"API retornou resposta vazia para {endpoint}")
                return None
                
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("❌ API Key inválida ou expirada")
            elif e.response.status_code == 403:
                logger.error("❌ Acesso negado - verifique seu plano da API")
            elif e.response.status_code == 429:
                logger.error("❌ Limite de requests excedido")
            else:
                logger.error(f"HTTP Error {e.response.status_code} para {endpoint}")
        except Exception as e:
            logger.error(f"Erro na requisição para {endpoint}: {e}")
            
        return None

    def get_team_last_n_fixtures(self, team_id: int) -> List[Dict]:
        """Busca os últimos N jogos finalizados de uma equipe"""
        params = {
            "team": team_id,
            "league": self.league_id,
            "season": self.current_season,
            "last": self.last_n_games * 2,
            "status": "FT"
        }
        
        data = self.make_api_request("fixtures", params)
        if not data:
            return []
        
        finished_games = [
            f for f in data["response"] 
            if f.get("fixture", {}).get("status", {}).get("short") == "FT"
        ]
        
        return finished_games[:self.last_n_games]

    def calculate_team_goals_avg(self, team_id: int, team_name: str) -> Optional[TeamStats]:
        """Calcula média de gols dos últimos 4 jogos com cache inteligente"""
        
        # Verificar cache
        cache_key = f"team_{team_id}"
        if cache_key in self.team_stats_cache:
            cached_stats = self.team_stats_cache[cache_key]
            cache_age = datetime.now() - cached_stats.last_update
            if cache_age.total_seconds() < self.cache_ttl_hours * 3600:
                return cached_stats
        
        fixtures = self.get_team_last_n_fixtures(team_id)
        
        if len(fixtures) < self.min_games_required:
            logger.debug(f"{team_name} tem apenas {len(fixtures)} jogos, mínimo {self.min_games_required}")
            return None
        
        total_goals = 0
        games_count = 0
        
        for fixture in fixtures:
            score = fixture.get("score", {}).get("fulltime", {})
            teams = fixture.get("teams", {})
            
            home_id = teams.get("home", {}).get("id")
            away_id = teams.get("away", {}).get("id")
            home_goals = score.get("home", 0) or 0
            away_goals = score.get("away", 0) or 0
            
            if home_id == team_id:
                total_goals += home_goals
            elif away_id == team_id:
                total_goals += away_goals
            else:
                continue
                
            games_count += 1
        
        if games_count == 0:
            return None
        
        avg_goals = total_goals / games_count
        
        stats = TeamStats(
            team_id=team_id,
            name=team_name,
            goals_avg_last4=avg_goals,
            games_played=games_count,
            last_update=datetime.now()
        )
        
        self.team_stats_cache[cache_key] = stats
        logger.debug(f"{team_name}: {avg_goals:.2f} gols/jogo (últimos {games_count} jogos)")
        return stats

    def get_today_fixtures(self) -> List[FixtureData]:
        """Busca jogos de hoje da Eredivisie"""
        today = datetime.now(self.timezone).strftime("%Y-%m-%d")
        
        params = {
            "league": self.league_id,
            "season": self.current_season,
            "date": today,
            "timezone": "Europe/Lisbon"
        }
        
        data = self.make_api_request("fixtures", params)
        if not data:
            return []
        
        fixtures = []
        for fixture in data["response"]:
            fixture_data = self._parse_fixture(fixture)
            if fixture_data:
                fixtures.append(fixture_data)
        
        if fixtures:
            logger.info(f"Encontrados {len(fixtures)} jogos para hoje")
        
        return fixtures

    def get_live_fixtures(self) -> List[FixtureData]:
        """Busca jogos ao vivo da Eredivisie"""
        params = {
            "league": self.league_id,
            "season": self.current_season,
            "live": "all"
        }
        
        data = self.make_api_request("fixtures", params)
        if not data:
            return []
        
        fixtures = []
        for fixture in data["response"]:
            fixture_data = self._parse_fixture(fixture)
            if fixture_data and fixture_data.status in ["1H", "2H", "HT"]:
                fixtures.append(fixture_data)
        
        return fixtures

    def _parse_fixture(self, fixture: Dict) -> Optional[FixtureData]:
        """Converte dados da API para FixtureData"""
        try:
            fixture_info = fixture.get("fixture", {})
            teams = fixture.get("teams", {})
            score = fixture.get("score", {}).get("fulltime", {})
            goals = fixture.get("goals", {})  # Para jogos ao vivo
            
            # Parse da data
            date_str = fixture_info.get("date")
            if date_str:
                kickoff_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                kickoff_time = kickoff_time.astimezone(self.timezone)
            else:
                kickoff_time = datetime.now(self.timezone)
            
            # Usar goals para jogos ao vivo, score para finalizados
            if goals.get("home") is not None:
                score_home = goals.get("home", 0) or 0
                score_away = goals.get("away", 0) or 0
            else:
                score_home = score.get("home", 0) or 0
                score_away = score.get("away", 0) or 0
            
            return FixtureData(
                fixture_id=fixture_info.get("id"),
                home_team=teams.get("home", {}).get("name", ""),
                away_team=teams.get("away", {}).get("name", ""),
                home_team_id=teams.get("home", {}).get("id"),
                away_team_id=teams.get("away", {}).get("id"),
                kickoff_time=kickoff_time,
                status=fixture_info.get("status", {}).get("short", ""),
                elapsed_minutes=fixture_info.get("status", {}).get("elapsed", 0) or 0,
                score_home=score_home,
                score_away=score_away
            )
        except Exception as e:
            logger.error(f"Erro ao processar fixture: {e}")
            return None

    def check_qualifying_fixture(self, fixture: FixtureData) -> Optional[Tuple[TeamStats, TeamStats]]:
        """Verifica se o jogo atende aos critérios (pelo menos uma equipe ≥ 2.3)"""
        
        home_stats = self.calculate_team_goals_avg(fixture.home_team_id, fixture.home_team)
        away_stats = self.calculate_team_goals_avg(fixture.away_team_id, fixture.away_team)
        
        if not home_stats or not away_stats:
            return None
        
        # Critério: pelo menos uma equipe ≥ 2.3 gols/jogo
        home_qualifies = home_stats.goals_avg_last4 >= self.min_goals_avg
        away_qualifies = away_stats.goals_avg_last4 >= self.min_goals_avg
        
        if home_qualifies or away_qualifies:
            logger.info(f"✅ Qualificado: {fixture.home_team} ({home_stats.goals_avg_last4:.2f}) vs {fixture.away_team} ({away_stats.goals_avg_last4:.2f})")
            return home_stats, away_stats
        
        return None

    def is_peak_minute(self, elapsed_minutes: int) -> bool:
        """Verifica se está em minuto de pico (60', 75', 85')"""
        for peak in self.peak_minutes:
            if abs(elapsed_minutes - peak) <= 2:
                return True
        return False

    def get_peak_period_info(self, elapsed_minutes: int) -> Tuple[str, float]:
        """Retorna informações do período de pico atual"""
        if 58 <= elapsed_minutes <= 62:
            return "46-60'", self.league_patterns_min["goals_46_60_min"]
        elif 73 <= elapsed_minutes <= 77:
            return "61-75'", self.league_patterns_min["goals_61_75_min"]
        elif 83 <= elapsed_minutes <= 90:
            return "76-90+'", self.league_patterns_min["goals_76_90_min"]
        else:
            return "Período de Pico", 20.0

    def generate_pre_game_message(self, fixture: FixtureData, home_stats: TeamStats, away_stats: TeamStats) -> str:
        """Gera mensagem pré-jogo formatada"""
        
        kickoff_str = fixture.kickoff_time.strftime("%H:%M")
        
        # Identificar equipes que atendem ao critério
        home_check = "✅" if home_stats.goals_avg_last4 >= self.min_goals_avg else ""
        away_check = "✅" if away_stats.goals_avg_last4 >= self.min_goals_avg else ""
        
        message = f"""🇳🇱 **EREDIVISIE - JOGO EM DESTAQUE HOJE!**

⚽ **{fixture.home_team} vs {fixture.away_team}**
🕐 Hoje às {kickoff_str} (Lisboa)

📊 **CRITÉRIO ATENDIDO - Médias Últimos 4 Jogos:**
• {home_stats.name}: {home_stats.goals_avg_last4:.2f} gols/jogo {home_check}
• {away_stats.name}: {away_stats.goals_avg_last4:.2f} gols/jogo {away_check}
(Pelo menos uma ≥ 2.30)

🎯 **MINUTOS DE PICO (Mínimos Históricos):**
• 60': ≥{self.league_patterns_min['goals_46_60_min']:.0f}% probabilidade
• 75': ≥{self.league_patterns_min['goals_61_75_min']:.0f}% probabilidade
• 85': ≥{self.league_patterns_min['goals_76_90_min']:.0f}% probabilidade

📈 **PADRÕES EREDIVISIE (Mínimos dos Últimos 5 Anos):**
• Média: ≥{self.league_patterns_min['avg_goals_per_game']:.2f} gols/jogo
• BTTS: ≥{self.league_patterns_min['btts_percentage']:.0f}% | Over 2.5: ≥{self.league_patterns_min['over_25_percentage']:.0f}%
• Over 3.5: ≥{self.league_patterns_min['over_35_percentage']:.0f}% | 2º tempo: ≥{self.league_patterns_min['second_half_percentage']:.0f}%

💡 **Alto potencial ofensivo confirmado - fique atento!**

📅 {datetime.now(self.timezone).strftime('%d/%m/%Y %H:%M')}"""

        return message

    def generate_live_message(self, fixture: FixtureData, home_stats: TeamStats, away_stats: TeamStats) -> str:
        """Gera mensagem para jogo ao vivo 0x0"""
        
        period_info, min_percentage = self.get_peak_period_info(fixture.elapsed_minutes)
        
        if fixture.elapsed_minutes >= 83:
            alert_msg = "🔥 RETA FINAL - PICO MÁXIMO!"
        elif fixture.elapsed_minutes >= 73:
            alert_msg = "⚡ ENTRANDO NO PICO PRINCIPAL!"
        else:
            alert_msg = "📈 INÍCIO DO PERÍODO DE PICO!"
        
        message = f"""🚨 **AO VIVO - EREDIVISIE {fixture.elapsed_minutes}'**

⚽ **{fixture.home_team} {fixture.score_home}-{fixture.score_away} {fixture.away_team}**
{alert_msg}

⏱️ **ALERTA:** Período {period_info} = ≥{min_percentage:.0f}% dos gols
• Baseado nos mínimos históricos da liga

📊 **POTENCIAL OFENSIVO (Últimos 4 jogos):**
• {home_stats.name}: {home_stats.goals_avg_last4:.2f} gols/jogo
• {away_stats.name}: {away_stats.goals_avg_last4:.2f} gols/jogo

📈 **Liga {self.current_season}/{self.current_season + 1} (Mínimos Garantidos):**
• ≥{self.league_patterns_min['avg_goals_per_game']:.2f} gols/jogo | BTTS ≥{self.league_patterns_min['btts_percentage']:.0f}% | Over 2.5 ≥{self.league_patterns_min['over_25_percentage']:.0f}%

💡 **Período crítico para gols ativado - momento ideal!**

📅 {datetime.now(self.timezone).strftime('%d/%m/%Y %H:%M')}"""

        return message

    def send_notification(self, message: str) -> bool:
        """Envia notificação via Telegram"""
        try:
            success = self.bot.send_message(self.chat_id, message)
            if success:
                logger.info("✅ Notificação enviada com sucesso")
            return success
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação: {e}")
            return False

    def check_pre_game_notifications(self):
        """Verifica e envia notificações pré-jogo"""
        logger.info("🔍 Verificando jogos de hoje...")
        
        fixtures = self.get_today_fixtures()
        if not fixtures:
            logger.info("📅 Nenhum jogo da Eredivisie hoje")
            return
        
        current_time = datetime.now(self.timezone)
        qualified_games = 0
        
        for fixture in fixtures:
            time_until_kickoff = fixture.kickoff_time - current_time
            hours_until = time_until_kickoff.total_seconds() / 3600
            
            if 0 <= hours_until <= self.pre_game_hours:
                notification_key = f"pre_{fixture.fixture_id}"
                
                if notification_key not in self.sent_notifications:
                    qualifying_stats = self.check_qualifying_fixture(fixture)
                    
                    if qualifying_stats:
                        home_stats, away_stats = qualifying_stats
                        message = self.generate_pre_game_message(fixture, home_stats, away_stats)
                        
                        if self.send_notification(message):
                            self.sent_notifications.add(notification_key)
                            qualified_games += 1
        
        if qualified_games == 0:
            logger.info("📊 Nenhum jogo atende aos critérios hoje")

    def check_live_notifications(self):
        """Verifica e envia notificações para jogos ao vivo"""
        fixtures = self.get_live_fixtures()
        
        for fixture in fixtures:
            if (fixture.score_home == 0 and fixture.score_away == 0 and 
                self.is_peak_minute(fixture.elapsed_minutes)):
                
                notification_key = f"live_{fixture.fixture_id}_{fixture.elapsed_minutes//5*5}"
                
                if notification_key not in self.sent_notifications:
                    qualifying_stats = self.check_qualifying_fixture(fixture)
                    
                    if qualifying_stats:
                        home_stats, away_stats = qualifying_stats
                        message = self.generate_live_message(fixture, home_stats, away_stats)
                        
                        if self.send_notification(message):
                            self.sent_notifications.add(notification_key)

    def cleanup_old_notifications(self):
        """Limpa cache de notificações antigas"""
        if len(self.sent_notifications) > 200:
            self.sent_notifications.clear()
            logger.info("🧹 Cache de notificações limpo")

    def run_daily_check(self):
        """Execução diária - verificar jogos de hoje"""
        logger.info("📅 Verificação diária iniciada")
        self.check_pre_game_notifications()
        self.cleanup_old_notifications()

    def run_live_check(self):
        """Execução contínua - verificar jogos ao vivo"""
        self.check_live_notifications()

def main():
    """Função principal com teste inicial e agendamentos otimizados"""
    try:
        logger.info("🚀 Iniciando Bot Eredivisie...")
        
        # Iniciar Flask em thread separada PRIMEIRO
        logger.info("🌐 Iniciando servidor Flask...")
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info(f"✅ Servidor Flask rodando na porta {os.environ.get('PORT', 10000)}")
        
        # Aguardar Flask iniciar
        time.sleep(2)
        
        # Inicializar bot
        bot = EredivisieHighPotentialBot()
        
        # Teste de conexões e envio de mensagem inicial
        if not bot.test_connections():
            logger.error("❌ Falha nos testes de conexão - verifique as configurações")
            return
        
        # Verificação inicial
        logger.info("🔍 Executando verificação inicial...")
        bot.run_daily_check()
        
        # Agendamentos otimizados
        schedule.every().day.at("09:00").do(bot.run_daily_check)
        schedule.every(30).minutes.do(bot.run_daily_check)  # Verificar a cada 30min
        schedule.every(bot.live_check_interval).seconds.do(bot.run_live_check)
        
        logger.info("📋 Agendamentos configurados:")
        logger.info(f"   - Verificação principal: 09:00 (Lisboa)")
        logger.info(f"   - Verificação contínua: a cada 30 minutos")
        logger.info(f"   - Verificação ao vivo: a cada {bot.live_check_interval} segundos")
        logger.info("🔄 Bot em funcionamento...")
        
        # Loop principal
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("🛑 Bot interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro no loop principal: {e}")
                time.sleep(60)
                
    except Exception as e:
        logger.error(f"❌ Erro crítico na inicialização: {e}")
        time.sleep(300)
        raise

if __name__ == "__main__":
    main()
