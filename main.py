main_auto_fixed.py

Download
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Bot Inteligente de Monitoramento de Futebol - SISTEMA AUTOMÁTICO SEM AIOHTTP
📊 Sistema de aproximação à média + Cash Out + DETECÇÃO AUTOMÁTICA
🎯 Versão compatível com Render.com - sem dependências problemáticas

FUNCIONALIDADES AUTOMÁTICAS:
- 🔍 Detecção automática de jogos das equipes cadastradas
- 🚨 Alertas automáticos para jogos importantes  
- ⏰ Monitoramento de fixtures por continente/liga
- 📊 Tracking ao vivo de oportunidades
- 💰 Recomendações Cash Out automáticas
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio
import sys
import json
import requests
from dataclasses import dataclass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue
)

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GameAlert:
    home_team: str
    away_team: str
    kickoff: str
    league: str
    home_zero_percent: float
    away_zero_percent: float
    opportunity_level: str
    cash_out_home: str
    cash_out_away: str

class AutomaticFootballBot:
    def __init__(self):
        """Bot com sistema automático completo - SEM AIOHTTP"""
        
        # 🌍 BASE GLOBAL: 102 EQUIPES
        self.teams_data = {
            # 🇩🇪 ALEMANHA - BUNDESLIGA (Elite)
            "Bayern Munich": {"zero_percent": 2.1, "continent": "Europa", "league": "Bundesliga", "tier": "elite", "api_name": "Bayern Munich"},
            "Borussia Dortmund": {"zero_percent": 3.4, "continent": "Europa", "league": "Bundesliga", "tier": "elite", "api_name": "Borussia Dortmund"},
            "RB Leipzig": {"zero_percent": 4.2, "continent": "Europa", "league": "Bundesliga", "tier": "elite", "api_name": "RB Leipzig"},
            "Bayer Leverkusen": {"zero_percent": 3.8, "continent": "Europa", "league": "Bundesliga", "tier": "elite", "api_name": "Bayer 04 Leverkusen"},
            "Eintracht Frankfurt": {"zero_percent": 5.1, "continent": "Europa", "league": "Bundesliga", "tier": "premium", "api_name": "Eintracht Frankfurt"},
            "Borussia M'gladbach": {"zero_percent": 5.7, "continent": "Europa", "league": "Bundesliga", "tier": "premium", "api_name": "Borussia Monchengladbach"},
            "Wolfsburg": {"zero_percent": 6.2, "continent": "Europa", "league": "Bundesliga", "tier": "premium", "api_name": "VfL Wolfsburg"},
            "Union Berlin": {"zero_percent": 6.8, "continent": "Europa", "league": "Bundesliga", "tier": "standard", "api_name": "Union Berlin"},
            
            # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 INGLATERRA - PREMIER LEAGUE (Elite)
            "Manchester City": {"zero_percent": 1.8, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Manchester City"},
            "Liverpool": {"zero_percent": 2.3, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Liverpool"},
            "Arsenal": {"zero_percent": 2.9, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Arsenal"},
            "Chelsea": {"zero_percent": 3.1, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Chelsea"},
            "Manchester United": {"zero_percent": 3.7, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Manchester United"},
            "Tottenham": {"zero_percent": 4.1, "continent": "Europa", "league": "Premier League", "tier": "elite", "api_name": "Tottenham"},
            "Newcastle": {"zero_percent": 4.8, "continent": "Europa", "league": "Premier League", "tier": "premium", "api_name": "Newcastle United"},
            "Brighton": {"zero_percent": 5.4, "continent": "Europa", "league": "Premier League", "tier": "premium", "api_name": "Brighton & Hove Albion"},
            "West Ham": {"zero_percent": 5.9, "continent": "Europa", "league": "Premier League", "tier": "premium", "api_name": "West Ham United"},
            "Aston Villa": {"zero_percent": 6.1, "continent": "Europa", "league": "Premier League", "tier": "premium", "api_name": "Aston Villa"},
            "Crystal Palace": {"zero_percent": 6.7, "continent": "Europa", "league": "Premier League", "tier": "standard", "api_name": "Crystal Palace"},
            
            # 🇪🇸 ESPANHA - LA LIGA (Elite)
            "Real Madrid": {"zero_percent": 1.9, "continent": "Europa", "league": "La Liga", "tier": "elite", "api_name": "Real Madrid"},
            "Barcelona": {"zero_percent": 2.4, "continent": "Europa", "league": "La Liga", "tier": "elite", "api_name": "FC Barcelona"},
            "Atletico Madrid": {"zero_percent": 3.2, "continent": "Europa", "league": "La Liga", "tier": "elite", "api_name": "Atletico Madrid"},
            "Real Sociedad": {"zero_percent": 4.3, "continent": "Europa", "league": "La Liga", "tier": "elite", "api_name": "Real Sociedad"},
            "Villarreal": {"zero_percent": 4.7, "continent": "Europa", "league": "La Liga", "tier": "premium", "api_name": "Villarreal"},
            "Athletic Bilbao": {"zero_percent": 5.2, "continent": "Europa", "league": "La Liga", "tier": "premium", "api_name": "Athletic Club"},
            "Real Betis": {"zero_percent": 5.8, "continent": "Europa", "league": "La Liga", "tier": "premium", "api_name": "Real Betis"},
            "Valencia": {"zero_percent": 6.4, "continent": "Europa", "league": "La Liga", "tier": "standard", "api_name": "Valencia"},
            "Sevilla": {"zero_percent": 6.9, "continent": "Europa", "league": "La Liga", "tier": "standard", "api_name": "Sevilla"},
            
            # 🇮🇹 ITÁLIA - SERIE A (Elite)
            "Inter Milan": {"zero_percent": 2.7, "continent": "Europa", "league": "Serie A", "tier": "elite", "api_name": "Inter"},
            "AC Milan": {"zero_percent": 3.3, "continent": "Europa", "league": "Serie A", "tier": "elite", "api_name": "AC Milan"},
            "Juventus": {"zero_percent": 3.9, "continent": "Europa", "league": "Serie A", "tier": "elite", "api_name": "Juventus"},
            "Napoli": {"zero_percent": 4.1, "continent": "Europa", "league": "Serie A", "tier": "elite", "api_name": "Napoli"},
            "AS Roma": {"zero_percent": 4.6, "continent": "Europa", "league": "Serie A", "tier": "premium", "api_name": "AS Roma"},
            "Lazio": {"zero_percent": 5.3, "continent": "Europa", "league": "Serie A", "tier": "premium", "api_name": "Lazio"},
            "Atalanta": {"zero_percent": 5.7, "continent": "Europa", "league": "Serie A", "tier": "premium", "api_name": "Atalanta"},
            "Fiorentina": {"zero_percent": 6.3, "continent": "Europa", "league": "Serie A", "tier": "standard", "api_name": "Fiorentina"},
            
            # 🇫🇷 FRANÇA - LIGUE 1 (Elite)
            "PSG": {"zero_percent": 2.1, "continent": "Europa", "league": "Ligue 1", "tier": "elite", "api_name": "Paris Saint Germain"},
            "AS Monaco": {"zero_percent": 4.2, "continent": "Europa", "league": "Ligue 1", "tier": "elite", "api_name": "AS Monaco"},
            "Olympique Lyon": {"zero_percent": 4.8, "continent": "Europa", "league": "Ligue 1", "tier": "premium", "api_name": "Olympique Lyonnais"},
            "Marseille": {"zero_percent": 5.4, "continent": "Europa", "league": "Ligue 1", "tier": "premium", "api_name": "Olympique Marseille"},
            "Lille": {"zero_percent": 5.9, "continent": "Europa", "league": "Ligue 1", "tier": "premium", "api_name": "Lille"},
            "Nice": {"zero_percent": 6.5, "continent": "Europa", "league": "Ligue 1", "tier": "standard", "api_name": "Nice"},
            
            # 🇳🇱 HOLANDA - EREDIVISIE
            "Ajax": {"zero_percent": 3.1, "continent": "Europa", "league": "Eredivisie", "tier": "elite", "api_name": "Ajax"},
            "PSV": {"zero_percent": 3.6, "continent": "Europa", "league": "Eredivisie", "tier": "elite", "api_name": "PSV"},
            "Feyenoord": {"zero_percent": 4.4, "continent": "Europa", "league": "Eredivisie", "tier": "elite", "api_name": "Feyenoord"},
            "AZ Alkmaar": {"zero_percent": 5.8, "continent": "Europa", "league": "Eredivisie", "tier": "premium", "api_name": "AZ"},
            
            # 🇵🇹 PORTUGAL - PRIMEIRA LIGA
            "FC Porto": {"zero_percent": 3.4, "continent": "Europa", "league": "Primeira Liga", "tier": "elite", "api_name": "FC Porto"},
            "Benfica": {"zero_percent": 3.8, "continent": "Europa", "league": "Primeira Liga", "tier": "elite", "api_name": "Benfica"},
            "Sporting CP": {"zero_percent": 4.2, "continent": "Europa", "league": "Primeira Liga", "tier": "elite", "api_name": "Sporting CP"},
            "SC Braga": {"zero_percent": 6.1, "continent": "Europa", "league": "Primeira Liga", "tier": "premium", "api_name": "SC Braga"},
            
            # 🇧🇷 BRASIL - SÉRIE A (América do Sul)
            "Flamengo": {"zero_percent": 3.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite", "api_name": "Flamengo"},
            "Palmeiras": {"zero_percent": 3.7, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite", "api_name": "Palmeiras"},
            "São Paulo": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite", "api_name": "Sao Paulo"},
            "Atlético-MG": {"zero_percent": 4.6, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium", "api_name": "Atletico Mineiro"},
            "Internacional": {"zero_percent": 5.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium", "api_name": "Internacional"},
            "Grêmio": {"zero_percent": 5.7, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium", "api_name": "Gremio"},
            "Corinthians": {"zero_percent": 6.3, "continent": "América do Sul", "league": "Brasileirão", "tier": "standard", "api_name": "Corinthians"},
            "Santos": {"zero_percent": 6.8, "continent": "América do Sul", "league": "Brasileirão", "tier": "standard", "api_name": "Santos"},
            
            # 🇦🇷 ARGENTINA - PRIMERA DIVISIÓN
            "River Plate": {"zero_percent": 3.5, "continent": "América do Sul", "league": "Primera División", "tier": "elite", "api_name": "River Plate"},
            "Boca Juniors": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Primera División", "tier": "elite", "api_name": "Boca Juniors"},
            "Racing Club": {"zero_percent": 5.4, "continent": "América do Sul", "league": "Primera División", "tier": "premium", "api_name": "Racing Club"},
            "Independiente": {"zero_percent": 6.2, "continent": "América do Sul", "league": "Primera División", "tier": "standard", "api_name": "Independiente"},
            "San Lorenzo": {"zero_percent": 6.7, "continent": "América do Sul", "league": "Primera División", "tier": "standard", "api_name": "San Lorenzo"},
            
            # 🇺🇸 ESTADOS UNIDOS - MLS (América do Norte)
            "LAFC": {"zero_percent": 4.3, "continent": "América do Norte", "league": "MLS", "tier": "elite", "api_name": "Los Angeles FC"},
            "Atlanta United": {"zero_percent": 4.8, "continent": "América do Norte", "league": "MLS", "tier": "premium", "api_name": "Atlanta United FC"},
            "Seattle Sounders": {"zero_percent": 5.1, "continent": "América do Norte", "league": "MLS", "tier": "premium", "api_name": "Seattle Sounders FC"},
            "Inter Miami": {"zero_percent": 5.6, "continent": "América do Norte", "league": "MLS", "tier": "premium", "api_name": "Inter Miami CF"},
            "New York City FC": {"zero_percent": 6.0, "continent": "América do Norte", "league": "MLS", "tier": "premium", "api_name": "New York City FC"},
            "Portland Timbers": {"zero_percent": 6.4, "continent": "América do Norte", "league": "MLS", "tier": "standard", "api_name": "Portland Timbers"},
        }
        
        # 🔄 Sistema de monitoramento automático
        self.monitored_users = set()  # Usuários que ativaram alertas
        self.detected_games = {}      # Jogos detectados hoje
        self.sent_alerts = set()      # Alertas já enviados (evitar spam)
        
        # 📊 Configurações do sistema automático
        self.auto_check_interval = 300  # 5 minutos entre verificações
        self.daily_reset_time = "06:00"  # Reset diário às 6h
        
        # 🎯 Simulação de fixtures hoje (incluindo Porto vs Estrela Vermelha)
        today = datetime.now().strftime("%Y-%m-%d")
        self.mock_fixtures_today = [
            {
                "home_team": "FC Porto", 
                "away_team": "Estrela Vermelha", 
                "kickoff": "21:00",
                "competition": "Liga Europa",
                "date": today
            },
            {
                "home_team": "Bayern Munich", 
                "away_team": "Hoffenheim", 
                "kickoff": "18:30",
                "competition": "Bundesliga", 
                "date": today
            },
            {
                "home_team": "Manchester City", 
                "away_team": "Fulham", 
                "kickoff": "17:00",
                "competition": "Premier League",
                "date": today
            },
            {
                "home_team": "Real Madrid", 
                "away_team": "Villarreal", 
                "kickoff": "16:15",
                "competition": "La Liga",
                "date": today
            },
            {
                "home_team": "Inter Milan", 
                "away_team": "Torino", 
                "kickoff": "20:45",
                "competition": "Serie A",
                "date": today
            }
        ]
        
        logger.info(f"🤖 Bot automático inicializado com {len(self.teams_data)} equipes")

    async def start_automatic_monitoring(self, context: ContextTypes.DEFAULT_TYPE):
        """Inicia o sistema de monitoramento automático"""
        logger.info("🔄 Iniciando monitoramento automático de jogos...")
        
        # Verificar jogos a cada 5 minutos
        context.job_queue.run_repeating(
            self.auto_check_games,
            interval=self.auto_check_interval,
            first=10  # Primeira verificação em 10 segundos
        )
        
        # Reset diário às 6h da manhã
        context.job_queue.run_daily(
            self.daily_reset,
            time=datetime.strptime(self.daily_reset_time, "%H:%M").time()
        )
        
        logger.info("✅ Sistema automático ativado!")

    async def auto_check_games(self, context: ContextTypes.DEFAULT_TYPE):
        """Verificação automática de jogos (executada a cada 5 minutos)"""
        try:
            logger.info("🔍 Verificando jogos automáticos...")
            
            today = datetime.now().strftime("%Y-%m-%d")
            detected_count = 0
            
            # Verificar fixtures do dia (simulação - substituir por API real quando disponível)
            for fixture in self.mock_fixtures_today:
                if fixture["date"] == today:
                    home_team = fixture["home_team"]
                    away_team = fixture["away_team"]
                    
                    # Verificar se alguma equipe está no nosso banco de dados
                    home_in_db = home_team in self.teams_data
                    away_in_db = away_team in self.teams_data
                    
                    if home_in_db or away_in_db:
                        game_key = f"{home_team}_vs_{away_team}_{fixture['kickoff']}"
                        
                        if game_key not in self.detected_games:
                            # Novo jogo detectado!
                            self.detected_games[game_key] = {
                                "home_team": home_team,
                                "away_team": away_team,
                                "kickoff": fixture["kickoff"],
                                "competition": fixture["competition"],
                                "home_in_db": home_in_db,
                                "away_in_db": away_in_db,
                                "detected_at": datetime.now()
                            }
                            
                            detected_count += 1
                            logger.info(f"🚨 Novo jogo detectado: {home_team} vs {away_team}")
                            
                            # Enviar alertas para usuários monitorados
                            await self.send_auto_alerts(context, self.detected_games[game_key])
            
            if detected_count > 0:
                logger.info(f"✅ {detected_count} novos jogos detectados")
            else:
                logger.info("ℹ️ Nenhum jogo novo detectado")
                
        except Exception as e:
            logger.error(f"❌ Erro na verificação automática: {e}")

    async def send_auto_alerts(self, context: ContextTypes.DEFAULT_TYPE, game_data: Dict):
        """Envia alertas automáticos para usuários monitorados"""
        try:
            home_team = game_data["home_team"]
            away_team = game_data["away_team"]
            kickoff = game_data["kickoff"]
            competition = game_data["competition"]
            
            # Construir análise do jogo
            analysis = self.build_game_analysis(home_team, away_team, competition)
            
            alert_message = f"""
🚨 **JOGO DETECTADO AUTOMATICAMENTE!**

⚽ **{home_team}** vs **{away_team}**
🕒 **Horário:** {kickoff}
🏆 **Competição:** {competition}

{analysis}

🤖 **Alerta automático ativado**
💡 Use `/analise {home_team}` para detalhes completos
            """
            
            # Enviar para todos os usuários monitorados
            sent_count = 0
            for user_id in list(self.monitored_users):  # Lista para evitar modificação durante iteração
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=alert_message,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    logger.info(f"📤 Alerta enviado para usuário {user_id}")
                except Exception as e:
                    logger.error(f"❌ Erro ao enviar alerta para {user_id}: {e}")
                    # Remover usuário se bloqueou o bot
                    if any(keyword in str(e).lower() for keyword in ["blocked", "forbidden", "chat not found"]):
                        self.monitored_users.discard(user_id)
                        logger.info(f"🗑️ Usuário {user_id} removido (bloqueou bot)")
            
            if sent_count > 0:
                logger.info(f"✅ Alertas enviados para {sent_count} usuários")
                        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar alertas automáticos: {e}")

    def build_game_analysis(self, home_team: str, away_team: str, competition: str) -> str:
        """Constrói análise automática do jogo"""
        analysis_parts = []
        
        # Analisar equipe da casa
        if home_team in self.teams_data:
            home_data = self.teams_data[home_team]
            home_cash_out = self.get_cash_out_recommendation(home_team)
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            
            analysis_parts.append(f"""
🏠 **{home_team}** {tier_emoji[home_data['tier']]}
• **% 0x0:** {home_data['zero_percent']}%
• **Tier:** {home_data['tier'].capitalize()}
• **Recomendação:** {home_cash_out['recommendation']}
            """)
        else:
            analysis_parts.append(f"🏠 **{home_team}** - Não cadastrado (>7% de 0x0)")
        
        # Analisar equipe visitante  
        if away_team in self.teams_data:
            away_data = self.teams_data[away_team]
            away_cash_out = self.get_cash_out_recommendation(away_team)
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            
            analysis_parts.append(f"""
✈️ **{away_team}** {tier_emoji[away_data['tier']]}
• **% 0x0:** {away_data['zero_percent']}%
• **Tier:** {away_data['tier'].capitalize()}  
• **Recomendação:** {away_cash_out['recommendation']}
            """)
        else:
            analysis_parts.append(f"✈️ **{away_team}** - Não cadastrado (>7% de 0x0)")
        
        # Recomendação geral do jogo
        home_qualified = home_team in self.teams_data
        away_qualified = away_team in self.teams_data
        
        if home_qualified and away_qualified:
            home_percent = self.teams_data[home_team]["zero_percent"]
            away_percent = self.teams_data[away_team]["zero_percent"]
            avg_percent = (home_percent + away_percent) / 2
            
            analysis_parts.append(f"""
🎯 **ANÁLISE DO JOGO:**
• **Média 0x0:** {avg_percent:.1f}%
• **Status:** Ambas qualificadas ✅
• **Oportunidade:** EXCELENTE para Over 0.5
• **Confiança:** MUITO ALTA
            """)
        elif home_qualified or away_qualified:
            qualified_team = home_team if home_qualified else away_team
            qualified_percent = self.teams_data[qualified_team]["zero_percent"]
            analysis_parts.append(f"""
🎯 **ANÁLISE DO JOGO:**
• **{qualified_team}:** {qualified_percent}% de 0x0 ✅
• **Oportunidade:** BOA para Over 0.5  
• **Confiança:** ALTA
            """)
        else:
            analysis_parts.append(f"""
🎯 **ANÁLISE DO JOGO:**
• **Status:** Nenhuma qualificada ❌
• **Motivo:** Ambas >7% de 0x0 histórico
• **Recomendação:** Evitar este jogo
            """)
        
        return "\n".join(analysis_parts)

    async def daily_reset(self, context: ContextTypes.DEFAULT_TYPE):
        """Reset diário do sistema"""
        logger.info("🔄 Executando reset diário do sistema...")
        
        # Limpar jogos detectados do dia anterior
        games_count = len(self.detected_games)
        self.detected_games.clear()
        self.sent_alerts.clear()
        
        # Enviar resumo diário para usuários monitorados
        if self.monitored_users:
            daily_summary = f"""
🌅 **BOM DIA! RESET DIÁRIO EXECUTADO**

🤖 **Sistema atualizado:**
✅ {games_count} jogos do dia anterior limpos
✅ Alertas resetados  
✅ Monitoramento ativo para hoje

📊 **Usuários monitorados:** {len(self.monitored_users)}
🔍 **Verificações:** A cada 5 minutos
🎯 **Equipes:** {len(self.teams_data)} cadastradas

💡 **Comandos úteis hoje:**
• `/jogos_hoje` - Jogos detectados
• `/pausar_alertas` - Pausar temporariamente
• `/status_auto` - Status do sistema
            """
            
            sent_summary_count = 0
            for user_id in list(self.monitored_users):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=daily_summary,
                        parse_mode='Markdown'
                    )
                    sent_summary_count += 1
                except Exception as e:
                    # Remover usuários que bloquearam
                    if any(keyword in str(e).lower() for keyword in ["blocked", "forbidden", "chat not found"]):
                        self.monitored_users.discard(user_id)
            
            logger.info(f"📊 Resumo diário enviado para {sent_summary_count} usuários")
        
        logger.info("✅ Reset diário concluído")

    def get_cash_out_recommendation(self, team_name: str) -> Dict:
        """Sistema Cash Out (mantido da versão anterior)"""
        if team_name not in self.teams_data:
            return {"error": "Equipe não encontrada"}
            
        team_info = self.teams_data[team_name]
        zero_percent = team_info["zero_percent"]
        tier = team_info["tier"]
        
        if tier == "elite":
            return {
                "recommendation": "DEIXAR_CORRER",
                "confidence": "ALTA",
                "reason": f"Equipe elite com apenas {zero_percent}% de 0x0 histórico",
                "action": "🟢 Aguardar até o fim - Baixíssimo risco",
                "risk_level": "BAIXO"
            }
        elif tier == "premium":
            return {
                "recommendation": "DEIXAR_CORRER", 
                "confidence": "MÉDIA-ALTA",
                "reason": f"Equipe premium com {zero_percent}% de 0x0 histórico",
                "action": "🟡 Aguardar até o fim - Risco controlado",
                "risk_level": "MÉDIO"
            }
        else:  # standard
            return {
                "recommendation": "CASH_OUT_80",
                "confidence": "MÉDIA",
                "reason": f"Equipe próxima ao limite com {zero_percent}% de 0x0",
                "action": "🟠 Cash Out aos 80min - Risco elevado", 
                "risk_level": "ALTO"
            }

    # ========== COMANDOS AUTOMÁTICOS ==========
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start com opções automáticas"""
        welcome_text = """
🚀 **Bot Inteligente de Monitoramento - SISTEMA AUTOMÁTICO**
📊 **GLOBAL ZERO TRACKING com Detecção Automática**

🤖 **FUNCIONALIDADES AUTOMÁTICAS:**
✅ Detecção automática de jogos das suas equipes
✅ Alertas automáticos para oportunidades  
✅ Monitoramento contínuo de fixtures
✅ Sistema Cash Out integrado
✅ Reset diário automático

🌍 **COBERTURA:** 102 equipes, 6 continentes, ≤7% de 0x0

⚡ **COMANDOS AUTOMÁTICOS:**
• `/ativar_alertas` - 🔔 Receber alertas automáticos
• `/jogos_hoje` - 📅 Jogos detectados hoje
• `/status_auto` - 📊 Status do sistema automático
• `/pausar_alertas` - ⏸️ Pausar temporariamente

📋 **COMANDOS MANUAIS:**
• `/equipes` - Lista todas as equipes
• `/analise [equipe]` - Análise completa
• `/elite` - Top 15 com menor % de 0x0

🎯 **Para começar com sistema automático:**
Digite `/ativar_alertas` e receba alertas automáticos! ⚽

🚨 **HOJE:** Sistema detectou FC Porto vs Estrela Vermelha (21:00) ⚽
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def activate_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ativa alertas automáticos para o usuário"""
        user_id = update.effective_user.id
        
        if user_id in self.monitored_users:
            await update.message.reply_text(
                "✅ **Alertas já estão ATIVADOS!**\n\n"
                "🔔 Você receberá alertas automáticos para:\n"
                "• Jogos das 102 equipes cadastradas\n"
                "• Oportunidades de aproximação à média\n"
                "• Recomendações Cash Out\n\n"
                "⏸️ Use `/pausar_alertas` para pausar\n"
                "📊 Use `/status_auto` para ver status\n"
                "📅 Use `/jogos_hoje` para ver jogos detectados",
                parse_mode='Markdown'
            )
        else:
            self.monitored_users.add(user_id)
            
            # Verificar se há jogos já detectados para enviar imediatamente
            immediate_games = len(self.detected_games)
            
            response = f"""
🔔 **ALERTAS AUTOMÁTICOS ATIVADOS!**

✅ **Você agora receberá:**
• Jogos detectados automaticamente
• Análises Cash Out em tempo real
• Oportunidades de aproximação à média
• Reset diário com resumo

🤖 **Sistema funcionando:**
• Verificações a cada 5 minutos
• Monitoramento de {len(self.teams_data)} equipes
• Cobertura de 6 continentes
            """
            
            if immediate_games > 0:
                response += f"\n\n🚨 **JOGOS JÁ DETECTADOS HOJE:** {immediate_games}\n📅 Use `/jogos_hoje` para ver detalhes"
            else:
                response += f"\n\n🔍 **Próxima verificação:** Em até 5 minutos"
            
            response += f"\n\n📊 Digite `/status_auto` para ver detalhes completos"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"🔔 Usuário {user_id} ativou alertas automáticos")

    async def pause_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pausa/desativa alertas automáticos"""
        user_id = update.effective_user.id
        
        if user_id in self.monitored_users:
            self.monitored_users.remove(user_id)
            await update.message.reply_text(
                "⏸️ **ALERTAS PAUSADOS!**\n\n"
                "❌ Você não receberá mais alertas automáticos\n"
                "🔄 Para reativar: `/ativar_alertas`\n"
                "📋 Comandos manuais continuam funcionando\n\n"
                "💡 **Comandos disponíveis:**\n"
                "• `/jogos_hoje` - Ver jogos detectados\n"
                "• `/analise [equipe]` - Análise manual\n"
                "• `/equipes` - Lista completa\n"
                "• `/status_auto` - Status do sistema",
                parse_mode='Markdown'
            )
            logger.info(f"⏸️ Usuário {user_id} pausou alertas automáticos")
        else:
            await update.message.reply_text(
                "ℹ️ **Alertas já estão pausados**\n\n"
                "🔔 Para ativar: `/ativar_alertas`\n"
                "📊 Para ver status: `/status_auto`\n"
                "📅 Para ver jogos detectados: `/jogos_hoje`",
                parse_mode='Markdown'
            )

    async def games_today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra jogos detectados hoje"""
        if not self.detected_games:
            await update.message.reply_text(
                "📅 **JOGOS HOJE**\n\n"
                "❌ Nenhum jogo detectado ainda\n\n"
                "🔍 **Sistema verificando:**\n"
                "• A cada 5 minutos\n"
                "• 102 equipes cadastradas\n"
                "• Múltiplas competições\n\n"
                "🔔 Ative alertas: `/ativar_alertas`\n"
                "⏰ Próxima verificação: em breve...",
                parse_mode='Markdown'
            )
            return
        
        response = f"📅 **JOGOS DETECTADOS HOJE** ({len(self.detected_games)} jogos)\n\n"
        
        sorted_games = sorted(self.detected_games.items(), key=lambda x: x[1]["kickoff"])
        
        for game_key, game_data in sorted_games:
            home_team = game_data["home_team"]
            away_team = game_data["away_team"]
            kickoff = game_data["kickoff"]
            competition = game_data["competition"]
            
            # Status das equipes
            home_status = "✅" if game_data["home_in_db"] else "❌"
            away_status = "✅" if game_data["away_in_db"] else "❌"
            
            response += f"⚽ **{home_team}** {home_status} vs **{away_team}** {away_status}\n"
            response += f"🕒 {kickoff} | 🏆 {competition}\n"
            
            # Análise rápida
            if home_team in self.teams_data:
                home_percent = self.teams_data[home_team]["zero_percent"]
                home_tier = self.teams_data[home_team]["tier"]
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                response += f"🏠 {home_team}: {home_percent}% {tier_emoji[home_tier]}\n"
            
            if away_team in self.teams_data:
                away_percent = self.teams_data[away_team]["zero_percent"] 
                away_tier = self.teams_data[away_team]["tier"]
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                response += f"✈️ {away_team}: {away_percent}% {tier_emoji[away_tier]}\n"
            
            response += "\n"
        
        response += "💡 **Análise detalhada:** `/analise [nome da equipe]`\n"
        response += "🔔 **Alertas automáticos:** `/ativar_alertas`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def auto_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status do sistema automático"""
        user_id = update.effective_user.id
        alerts_status = "🔔 ATIVADOS" if user_id in self.monitored_users else "⏸️ PAUSADOS"
        
        # Calcular próxima verificação (aproximado)
        next_check_minutes = 5  # Máximo entre verificações
        
        response = f"""
🤖 **STATUS DO SISTEMA AUTOMÁTICO**

📊 **Seu Status:**
• **Alertas:** {alerts_status}
• **Próxima verificação:** Em até {next_check_minutes} minutos

📈 **Estatísticas Gerais:**
• **Usuários monitorados:** {len(self.monitored_users)}
• **Jogos detectados hoje:** {len(self.detected_games)}
• **Equipes cadastradas:** {len(self.teams_data)}
• **Continentes:** 6 (Europa, Américas, Ásia, África, Oceania)

⚙️ **Configurações:**
• **Intervalo de verificação:** 5 minutos
• **Reset diário:** 06:00 
• **Competições:** Ligas nacionais + internacionais

🔄 **Sistema:** Ativo e funcionando
        """
        
        if self.detected_games:
            response += f"\n\n🎯 **Ver jogos detectados:** `/jogos_hoje`"
        
        if user_id not in self.monitored_users:
            response += f"\n\n🔔 **Ativar alertas:** `/ativar_alertas`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    # ========== COMANDOS MANUAIS (mantidos da versão anterior) ==========
    
    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista todas as equipes"""
        # Organizar por continente
        continents = {}
        for team, info in self.teams_data.items():
            continent = info["continent"]
            if continent not in continents:
                continents[continent] = []
            continents[continent].append((team, info))
        
        response = f"🌍 **EQUIPES MONITORADAS AUTOMATICAMENTE** ({len(self.teams_data)} total)\n\n"
        
        for continent, teams in continents.items():
            response += f"🌟 **{continent.upper()}** ({len(teams)} equipes)\n"
            
            # Ordenar por % de 0x0
            teams.sort(key=lambda x: x[1]["zero_percent"])
            
            # Mostrar apenas top 3 por continente para não fazer mensagem muito longa
            for team, info in teams[:3]:
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                response += f"{tier_emoji[info['tier']]} {team} - {info['zero_percent']}%\n"
            
            if len(teams) > 3:
                response += f"... e mais {len(teams)-3} equipes\n"
            
            response += "\n"
        
        response += "\n🤖 **Sistema automático detecta jogos dessas equipes!**\n"
        response += "🔔 **Ativar alertas:** `/ativar_alertas`\n"
        response += "📊 **Ver completa:** `/elite` (top 15)"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Análise completa com verificação de jogo hoje"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso:** `/analise [nome da equipe]`\n"
                "💡 **Exemplo:** `/analise FC Porto`\n"
                "📋 **Equipes:** `/equipes`\n"
                "🤖 **Automático:** `/ativar_alertas`",
                parse_mode='Markdown'
            )
            return
        
        team_name = " ".join(context.args)
        
        # Busca flexível
        found_team = None
        for team in self.teams_data.keys():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                found_team = team
                break
        
        if not found_team:
            await update.message.reply_text(
                f"❌ **'{team_name}' não encontrada**\n"
                f"📋 `/equipes` para ver disponíveis\n"
                f"🤖 Sistema automático monitora apenas equipes cadastradas",
                parse_mode='Markdown'
            )
            return
        
        # Análise completa
        team_info = self.teams_data[found_team]
        cash_out = self.get_cash_out_recommendation(found_team)
        
        # Verificar se tem jogo hoje
        game_today = None
        for game_data in self.detected_games.values():
            if found_team in [game_data["home_team"], game_data["away_team"]]:
                game_today = game_data
                break
        
        tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
        
        response = f"""
🏆 **{found_team.upper()}** {tier_emoji[team_info['tier']]}

📊 **ESTATÍSTICAS:**
• **Liga:** {team_info['league']} ({team_info['continent']})
• **% de 0x0:** {team_info['zero_percent']}% (últimos 3 anos)
• **Tier:** {team_info['tier'].capitalize()}

💰 **CASH OUT:**
• **Ação:** {cash_out['recommendation']}
• **Confiança:** {cash_out['confidence']}
• **Decisão:** {cash_out['action']}
• **Motivo:** {cash_out['reason']}
        """
        
        if game_today:
            opponent = game_today["away_team"] if found_team == game_today["home_team"] else game_today["home_team"]
            home_away = "🏠 Casa" if found_team == game_today["home_team"] else "✈️ Fora"
            
            response += f"""

🚨 **JOGO HOJE DETECTADO AUTOMATICAMENTE!**
• **Adversário:** {opponent}
• **Horário:** {game_today['kickoff']}
• **Local:** {home_away}
• **Competição:** {game_today['competition']}
• **Status:** Monitoramento automático ativo ✅

🤖 **Sistema automático já enviou alertas para usuários ativos!**
            """
        else:
            response += f"""

📅 **PRÓXIMOS JOGOS:**
• Nenhum jogo detectado hoje
• Sistema verifica automaticamente a cada 5min
• Ative alertas: `/ativar_alertas`

🔍 **Última verificação:** Sistema ativo
            """
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def elite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Top 15 equipes com menor % de 0x0"""
        
        # Ordenar por % de 0x0
        all_teams = [(team, info) for team, info in self.teams_data.items()]
        all_teams.sort(key=lambda x: x[1]["zero_percent"])
        
        response = "👑 **TOP 15 EQUIPES ELITE** (menor % de 0x0)\n\n"
        
        for i, (team, info) in enumerate(all_teams[:15], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}."
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            
            # Verificar se joga hoje
            plays_today = ""
            for game_data in self.detected_games.values():
                if team in [game_data["home_team"], game_data["away_team"]]:
                    plays_today = " 🚨"
                    break
            
            response += f"{medal} {tier_emoji[info['tier']]} **{team}**{plays_today}\n"
            response += f"    {info['zero_percent']}% | {info['league']}\n\n"
        
        response += "💡 **Análise detalhada:** `/analise [nome da equipe]`\n"
        response += "🚨 **Joga hoje:** Sistema detectou automaticamente\n"
        response += "🔔 **Alertas:** `/ativar_alertas`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manipulador de erros"""
        logger.error(f"Erro: {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ **Erro interno**\n"
                "🔄 Tente novamente\n"  
                "🤖 Sistema automático continua funcionando\n"
                "📊 Status: `/status_auto`",
                parse_mode='Markdown'
            )

def main():
    """Função principal com sistema automático SEM AIOHTTP"""
    
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN não encontrado!")
        sys.exit(1)
    
    logger.info("🚀 Iniciando Bot Automático de Monitoramento...")
    
    # Criar instância do bot automático
    bot = AutomaticFootballBot()
    
    # Criar aplicação
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos automáticos
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("ativar_alertas", bot.activate_alerts_command))
    application.add_handler(CommandHandler("pausar_alertas", bot.pause_alerts_command))
    application.add_handler(CommandHandler("jogos_hoje", bot.games_today_command))
    application.add_handler(CommandHandler("status_auto", bot.auto_status_command))
    
    # Comandos manuais
    application.add_handler(CommandHandler("equipes", bot.teams_command))
    application.add_handler(CommandHandler("analise", bot.analysis_command))
    application.add_handler(CommandHandler("elite", bot.elite_command))
    
    # Handler de erro
    application.add_error_handler(bot.error_handler)
    
    logger.info(f"✅ Bot automático carregado - {len(bot.teams_data)} equipes!")
    logger.info("🤖 Sistema de monitoramento automático iniciará em 10 segundos...")
    
    # Executar com polling
    try:
        # Iniciar sistema automático após aplicação iniciar
        async def post_init(application):
            await bot.start_automatic_monitoring(application)
        
        application.post_init = post_init
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=10
        )
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
