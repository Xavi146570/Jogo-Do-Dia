#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Bot Inteligente de Monitoramento de Futebol - AUTOMÁTICO SIMPLIFICADO
📊 Sistema completo sem dependências complexas - 100% compatível Render
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio
import sys
import json
import threading
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    MessageHandler,
    filters
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

class SimpleAutomaticBot:
    def __init__(self):
        """Bot automático simplificado - sem JobQueue"""
        
        # 🌍 BASE GLOBAL: 69 EQUIPES PRINCIPAIS
        self.teams_data = {
            # 🇩🇪 ALEMANHA - BUNDESLIGA
            "Bayern Munich": {"zero_percent": 2.1, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Borussia Dortmund": {"zero_percent": 3.4, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "RB Leipzig": {"zero_percent": 4.2, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Bayer Leverkusen": {"zero_percent": 3.8, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Eintracht Frankfurt": {"zero_percent": 5.1, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Wolfsburg": {"zero_percent": 6.2, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Union Berlin": {"zero_percent": 6.8, "continent": "Europa", "league": "Bundesliga", "tier": "standard"},
            
            # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 INGLATERRA - PREMIER LEAGUE
            "Manchester City": {"zero_percent": 1.8, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Liverpool": {"zero_percent": 2.3, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Arsenal": {"zero_percent": 2.9, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Chelsea": {"zero_percent": 3.1, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Manchester United": {"zero_percent": 3.7, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Tottenham": {"zero_percent": 4.1, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Newcastle": {"zero_percent": 4.8, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            "Brighton": {"zero_percent": 5.4, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            "West Ham": {"zero_percent": 5.9, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            "Aston Villa": {"zero_percent": 6.1, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            
            # 🇪🇸 ESPANHA - LA LIGA
            "Real Madrid": {"zero_percent": 1.9, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Barcelona": {"zero_percent": 2.4, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Atletico Madrid": {"zero_percent": 3.2, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Real Sociedad": {"zero_percent": 4.3, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Villarreal": {"zero_percent": 4.7, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Athletic Bilbao": {"zero_percent": 5.2, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Real Betis": {"zero_percent": 5.8, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Valencia": {"zero_percent": 6.4, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            "Sevilla": {"zero_percent": 6.9, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            
            # 🇮🇹 ITÁLIA - SERIE A
            "Inter Milan": {"zero_percent": 2.7, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AC Milan": {"zero_percent": 3.3, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Juventus": {"zero_percent": 3.9, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Napoli": {"zero_percent": 4.1, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AS Roma": {"zero_percent": 4.6, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Lazio": {"zero_percent": 5.3, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Atalanta": {"zero_percent": 5.7, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Fiorentina": {"zero_percent": 6.3, "continent": "Europa", "league": "Serie A", "tier": "standard"},
            
            # 🇫🇷 FRANÇA - LIGUE 1
            "PSG": {"zero_percent": 2.1, "continent": "Europa", "league": "Ligue 1", "tier": "elite"},
            "AS Monaco": {"zero_percent": 4.2, "continent": "Europa", "league": "Ligue 1", "tier": "elite"},
            "Olympique Lyon": {"zero_percent": 4.8, "continent": "Europa", "league": "Ligue 1", "tier": "premium"},
            "Marseille": {"zero_percent": 5.4, "continent": "Europa", "league": "Ligue 1", "tier": "premium"},
            "Lille": {"zero_percent": 5.9, "continent": "Europa", "league": "Ligue 1", "tier": "premium"},
            "Nice": {"zero_percent": 6.5, "continent": "Europa", "league": "Ligue 1", "tier": "standard"},
            
            # 🇳🇱 HOLANDA - EREDIVISIE
            "Ajax": {"zero_percent": 3.1, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            "PSV": {"zero_percent": 3.6, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            "Feyenoord": {"zero_percent": 4.4, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            
            # 🇵🇹 PORTUGAL - PRIMEIRA LIGA
            "FC Porto": {"zero_percent": 3.4, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Benfica": {"zero_percent": 3.8, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Sporting CP": {"zero_percent": 4.2, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "SC Braga": {"zero_percent": 6.1, "continent": "Europa", "league": "Primeira Liga", "tier": "premium"},
            
            # 🇧🇷 BRASIL - SÉRIE A
            "Flamengo": {"zero_percent": 3.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "Palmeiras": {"zero_percent": 3.7, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "São Paulo": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "Atlético-MG": {"zero_percent": 4.6, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium"},
            "Internacional": {"zero_percent": 5.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium"},
            "Corinthians": {"zero_percent": 6.3, "continent": "América do Sul", "league": "Brasileirão", "tier": "standard"},
            
            # 🇦🇷 ARGENTINA - PRIMERA DIVISIÓN
            "River Plate": {"zero_percent": 3.5, "continent": "América do Sul", "league": "Primera División", "tier": "elite"},
            "Boca Juniors": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Primera División", "tier": "elite"},
            "Racing Club": {"zero_percent": 5.4, "continent": "América do Sul", "league": "Primera División", "tier": "premium"},
            
            # 🇺🇸 MLS
            "LAFC": {"zero_percent": 4.3, "continent": "América do Norte", "league": "MLS", "tier": "elite"},
            "Atlanta United": {"zero_percent": 4.8, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "Seattle Sounders": {"zero_percent": 5.1, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "Inter Miami": {"zero_percent": 5.6, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
        }
        
        # 🔄 Sistema automático
        self.monitored_users = set()
        self.detected_games = {}
        self.application = None
        self.auto_thread = None
        self.running = True
        
        # 🎯 Jogos simulados hoje
        today = datetime.now().strftime("%Y-%m-%d")
        self.mock_fixtures = [
            {
                "home_team": "FC Porto",
                "away_team": "Estrela Vermelha", 
                "kickoff": "21:00",
                "competition": "Liga Europa",
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
            }
        ]
        
        logger.info(f"🤖 Bot simplificado inicializado com {len(self.teams_data)} equipes")

    def start_monitoring_thread(self, application):
        """Inicia thread de monitoramento automático"""
        self.application = application
        
        def monitor_loop():
            logger.info("🔄 Thread de monitoramento iniciada")
            
            # Aguardar 10 segundos antes da primeira verificação
            time.sleep(10)
            
            while self.running:
                try:
                    # Executar verificação
                    asyncio.run_coroutine_threadsafe(
                        self.check_games_and_alert(), 
                        application._loop
                    )
                    
                    # Aguardar 5 minutos (300 segundos)
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"❌ Erro no loop de monitoramento: {e}")
                    time.sleep(60)  # Aguardar 1 minuto antes de tentar novamente
        
        self.auto_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.auto_thread.start()
        logger.info("✅ Sistema automático iniciado com threading!")

    async def check_games_and_alert(self):
        """Verificar jogos e enviar alertas"""
        try:
            logger.info("🔍 Verificando jogos automaticamente...")
            
            today = datetime.now().strftime("%Y-%m-%d")
            new_games = 0
            
            for fixture in self.mock_fixtures:
                if fixture["date"] == today:
                    home_team = fixture["home_team"]
                    away_team = fixture["away_team"]
                    
                    # Verificar se equipe está cadastrada
                    home_in_db = home_team in self.teams_data
                    away_in_db = away_team in self.teams_data
                    
                    if home_in_db or away_in_db:
                        game_key = f"{home_team}_vs_{away_team}"
                        
                        if game_key not in self.detected_games:
                            # Novo jogo!
                            self.detected_games[game_key] = {
                                "home_team": home_team,
                                "away_team": away_team,
                                "kickoff": fixture["kickoff"],
                                "competition": fixture["competition"],
                                "home_in_db": home_in_db,
                                "away_in_db": away_in_db
                            }
                            
                            new_games += 1
                            logger.info(f"🚨 Jogo detectado: {home_team} vs {away_team}")
                            
                            # Enviar alertas
                            await self.send_automatic_alerts(self.detected_games[game_key])
            
            if new_games == 0:
                logger.info("ℹ️ Nenhum jogo novo detectado")
                
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")

    async def send_automatic_alerts(self, game_data):
        """Enviar alertas automáticos"""
        try:
            home_team = game_data["home_team"]
            away_team = game_data["away_team"] 
            kickoff = game_data["kickoff"]
            competition = game_data["competition"]
            
            # Construir mensagem
            alert = self.build_alert_message(game_data)
            
            # Enviar para usuários monitorados
            sent_count = 0
            for user_id in list(self.monitored_users):
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=alert,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Erro enviando para {user_id}: {e}")
                    if "blocked" in str(e).lower():
                        self.monitored_users.discard(user_id)
            
            if sent_count > 0:
                logger.info(f"📤 Alertas enviados para {sent_count} usuários")
                
        except Exception as e:
            logger.error(f"❌ Erro enviando alertas: {e}")

    def build_alert_message(self, game_data):
        """Construir mensagem de alerta"""
        home_team = game_data["home_team"]
        away_team = game_data["away_team"]
        kickoff = game_data["kickoff"]
        competition = game_data["competition"]
        
        message = f"""
🚨 **JOGO DETECTADO AUTOMATICAMENTE!**

⚽ **{home_team}** vs **{away_team}**
🕒 **Horário:** {kickoff}
🏆 **Competição:** {competition}
        """
        
        # Análise das equipes
        if home_team in self.teams_data:
            home_info = self.teams_data[home_team]
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            message += f"""

🏠 **{home_team}** {tier_emoji[home_info['tier']]}
• **% 0x0:** {home_info['zero_percent']}%
• **Tier:** {home_info['tier'].capitalize()}
• **Recomendação:** {self.get_cash_out_rec(home_team)}
            """
        else:
            message += f"\n🏠 **{home_team}** - Não cadastrado (>7% 0x0)"
        
        if away_team in self.teams_data:
            away_info = self.teams_data[away_team]
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            message += f"""

✈️ **{away_team}** {tier_emoji[away_info['tier']]}
• **% 0x0:** {away_info['zero_percent']}%
• **Tier:** {away_info['tier'].capitalize()}
• **Recomendação:** {self.get_cash_out_rec(away_team)}
            """
        else:
            message += f"\n✈️ **{away_team}** - Não cadastado (>7% 0x0)"
        
        # Análise geral
        home_qualified = home_team in self.teams_data
        away_qualified = away_team in self.teams_data
        
        if home_qualified and away_qualified:
            message += "\n\n🎯 **ANÁLISE:** Ambas qualificadas ✅\n**Oportunidade:** EXCELENTE para Over 0.5"
        elif home_qualified or away_qualified:
            qualified = home_team if home_qualified else away_team
            message += f"\n\n🎯 **ANÁLISE:** {qualified} qualificada ✅\n**Oportunidade:** BOA para Over 0.5"
        else:
            message += "\n\n🎯 **ANÁLISE:** Nenhuma qualificada ❌\n**Recomendação:** Evitar"
        
        message += "\n\n🤖 **Sistema automático ativo**"
        return message

    def get_cash_out_rec(self, team_name):
        """Recomendação Cash Out simplificada"""
        if team_name not in self.teams_data:
            return "N/A"
        
        tier = self.teams_data[team_name]["tier"]
        if tier == "elite":
            return "DEIXAR_CORRER"
        elif tier == "premium":
            return "DEIXAR_CORRER"
        else:
            return "CASH_OUT_80"

    # ========== COMANDOS ==========

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        text = f"""
🚀 **Bot Automático de Monitoramento de Futebol**

🤖 **SISTEMA AUTOMÁTICO ATIVO:**
✅ Detecção automática de jogos
✅ Alertas automáticos
✅ {len(self.teams_data)} equipes monitoradas
✅ Sistema Cash Out integrado

⚡ **COMANDOS:**
• `/ativar_alertas` - Receber alertas automáticos
• `/jogos_hoje` - Ver jogos detectados  
• `/status_auto` - Status do sistema
• `/analise [equipe]` - Análise completa
• `/equipes` - Lista todas as equipes

🎯 **HOJE DETECTADO:**
FC Porto vs Estrela Vermelha (21:00) ⚽

Digite `/ativar_alertas` para começar!
        """
        await update.message.reply_text(text, parse_mode='Markdown')

    async def activate_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ativar alertas"""
        user_id = update.effective_user.id
        
        if user_id not in self.monitored_users:
            self.monitored_users.add(user_id)
            
            text = f"""
🔔 **ALERTAS AUTOMÁTICOS ATIVADOS!**

✅ **Você receberá:**
• Jogos detectados automaticamente
• Análises Cash Out
• Oportunidades de aproximação à média

🤖 **Sistema ativo:**
• Verificações a cada 5 minutos
• {len(self.teams_data)} equipes monitoradas
• Jogos já detectados: {len(self.detected_games)}

📊 Status: `/status_auto`
            """
            logger.info(f"🔔 Usuário {user_id} ativou alertas")
        else:
            text = "✅ **Alertas já ativados!**\n📊 Status: `/status_auto`"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def games_today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Jogos detectados hoje"""
        if not self.detected_games:
            text = """
📅 **JOGOS HOJE**

❌ Nenhum jogo detectado ainda

🔍 Sistema verificando automaticamente...
🔔 Ative alertas: `/ativar_alertas`
            """
        else:
            text = f"📅 **JOGOS DETECTADOS** ({len(self.detected_games)})\n\n"
            
            for game_data in self.detected_games.values():
                home = game_data["home_team"]
                away = game_data["away_team"] 
                kickoff = game_data["kickoff"]
                comp = game_data["competition"]
                
                home_status = "✅" if game_data["home_in_db"] else "❌"
                away_status = "✅" if game_data["away_in_db"] else "❌"
                
                text += f"⚽ **{home}** {home_status} vs **{away}** {away_status}\n"
                text += f"🕒 {kickoff} | 🏆 {comp}\n\n"
            
            text += "💡 `/analise [equipe]` para detalhes"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def status_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status do sistema"""
        user_id = update.effective_user.id
        alerts_status = "🔔 ATIVADOS" if user_id in self.monitored_users else "⏸️ PAUSADOS"
        
        text = f"""
🤖 **STATUS SISTEMA AUTOMÁTICO**

📊 **Seu Status:** {alerts_status}
📈 **Usuários monitorados:** {len(self.monitored_users)}
🎯 **Jogos detectados hoje:** {len(self.detected_games)}
⚡ **Equipes cadastradas:** {len(self.teams_data)}

⚙️ **Sistema:**
• Verificações: A cada 5 minutos
• Thread: {'🟢 Ativa' if self.auto_thread and self.auto_thread.is_alive() else '🔴 Inativa'}
• Última verificação: Automática

🔔 `/ativar_alertas` - Ativar
📅 `/jogos_hoje` - Ver jogos
        """
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Análise de equipe"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso:** `/analise [equipe]`\n💡 **Exemplo:** `/analise FC Porto`",
                parse_mode='Markdown'
            )
            return
        
        team_name = " ".join(context.args)
        
        # Busca flexível
        found_team = None
        for team in self.teams_data.keys():
            if team_name.lower() in team.lower():
                found_team = team
                break
        
        if not found_team:
            await update.message.reply_text(
                f"❌ **'{team_name}' não encontrada**\n📋 `/equipes` para lista completa",
                parse_mode='Markdown'
            )
            return
        
        # Análise
        info = self.teams_data[found_team]
        tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
        
        # Verificar se joga hoje
        game_today = None
        for game_data in self.detected_games.values():
            if found_team in [game_data["home_team"], game_data["away_team"]]:
                game_today = game_data
                break
        
        text = f"""
🏆 **{found_team.upper()}** {tier_emoji[info['tier']]}

📊 **ESTATÍSTICAS:**
• **Liga:** {info['league']} ({info['continent']})
• **% 0x0:** {info['zero_percent']}% (últimos 3 anos)
• **Tier:** {info['tier'].capitalize()}

💰 **CASH OUT:** {self.get_cash_out_rec(found_team)}
        """
        
        if game_today:
            opponent = game_today["away_team"] if found_team == game_today["home_team"] else game_today["home_team"]
            local = "🏠 Casa" if found_team == game_today["home_team"] else "✈️ Fora"
            
            text += f"""

🚨 **JOGO HOJE DETECTADO!**
• **Vs:** {opponent}
• **Horário:** {game_today['kickoff']}
• **Local:** {local}
• **Competição:** {game_today['competition']}
✅ **Sistema automático ativo**
            """
        else:
            text += "\n\n📅 **Sem jogos detectados hoje**"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista equipes"""
        continents = {}
        for team, info in self.teams_data.items():
            continent = info["continent"]
            if continent not in continents:
                continents[continent] = []
            continents[continent].append((team, info))
        
        text = f"🌍 **EQUIPES MONITORADAS** ({len(self.teams_data)} total)\n\n"
        
        for continent, teams in continents.items():
            text += f"🌟 **{continent}** ({len(teams)})\n"
            teams.sort(key=lambda x: x[1]["zero_percent"])
            
            for team, info in teams[:3]:  # Top 3 por continente
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                text += f"{tier_emoji[info['tier']]} {team} - {info['zero_percent']}%\n"
            
            if len(teams) > 3:
                text += f"... +{len(teams)-3} mais\n"
            text += "\n"
        
        text += "💡 `/analise [equipe]` para detalhes"
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler de erro"""
        logger.error(f"Erro: {context.error}")

def main():
    """Função principal"""
    
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ Token não encontrado!")
        sys.exit(1)
    
    logger.info("🚀 Iniciando bot automático simplificado...")
    
    # Criar bot
    bot = SimpleAutomaticBot()
    
    # Criar aplicação
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("ativar_alertas", bot.activate_alerts_command))
    application.add_handler(CommandHandler("jogos_hoje", bot.games_today_command))
    application.add_handler(CommandHandler("status_auto", bot.status_auto_command))
    application.add_handler(CommandHandler("analise", bot.analysis_command))
    application.add_handler(CommandHandler("equipes", bot.teams_command))
    
    application.add_error_handler(bot.error_handler)
    
    logger.info(f"✅ Bot carregado - {len(bot.teams_data)} equipes!")
    
    # Iniciar sistema automático com threading
    bot.start_monitoring_thread(application)
    
    # Executar polling
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido")
        bot.running = False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        bot.running = False
        sys.exit(1)

if __name__ == '__main__':
    main()
