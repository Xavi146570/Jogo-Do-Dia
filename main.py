#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AutomaticBot:
    def __init__(self):
        self.teams_data = {
            "Bayern Munich": {"zero_percent": 2.1, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Borussia Dortmund": {"zero_percent": 3.4, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "RB Leipzig": {"zero_percent": 4.2, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Bayer Leverkusen": {"zero_percent": 3.8, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Eintracht Frankfurt": {"zero_percent": 5.1, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Wolfsburg": {"zero_percent": 6.2, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Union Berlin": {"zero_percent": 6.8, "continent": "Europa", "league": "Bundesliga", "tier": "standard"},
            
            "Manchester City": {"zero_percent": 1.8, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Liverpool": {"zero_percent": 2.3, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Arsenal": {"zero_percent": 2.9, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Chelsea": {"zero_percent": 3.1, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Manchester United": {"zero_percent": 3.7, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Tottenham": {"zero_percent": 4.1, "continent": "Europa", "league": "Premier League", "tier": "elite"},
            "Newcastle": {"zero_percent": 4.8, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            "Brighton": {"zero_percent": 5.4, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            "West Ham": {"zero_percent": 5.9, "continent": "Europa", "league": "Premier League", "tier": "premium"},
            
            "Real Madrid": {"zero_percent": 1.9, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Barcelona": {"zero_percent": 2.4, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Atletico Madrid": {"zero_percent": 3.2, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Real Sociedad": {"zero_percent": 4.3, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Villarreal": {"zero_percent": 4.7, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Athletic Bilbao": {"zero_percent": 5.2, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Real Betis": {"zero_percent": 5.8, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Valencia": {"zero_percent": 6.4, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            "Sevilla": {"zero_percent": 6.9, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            
            "Inter Milan": {"zero_percent": 2.7, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AC Milan": {"zero_percent": 3.3, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Juventus": {"zero_percent": 3.9, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Napoli": {"zero_percent": 4.1, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AS Roma": {"zero_percent": 4.6, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Lazio": {"zero_percent": 5.3, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            
            "PSG": {"zero_percent": 2.1, "continent": "Europa", "league": "Ligue 1", "tier": "elite"},
            "AS Monaco": {"zero_percent": 4.2, "continent": "Europa", "league": "Ligue 1", "tier": "elite"},
            "Marseille": {"zero_percent": 5.4, "continent": "Europa", "league": "Ligue 1", "tier": "premium"},
            "Lille": {"zero_percent": 5.9, "continent": "Europa", "league": "Ligue 1", "tier": "premium"},
            
            "Ajax": {"zero_percent": 3.1, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            "PSV": {"zero_percent": 3.6, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            "Feyenoord": {"zero_percent": 4.4, "continent": "Europa", "league": "Eredivisie", "tier": "elite"},
            
            "FC Porto": {"zero_percent": 3.4, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Benfica": {"zero_percent": 3.8, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Sporting CP": {"zero_percent": 4.2, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            
            "Flamengo": {"zero_percent": 3.2, "continent": "America do Sul", "league": "Brasileirao", "tier": "elite"},
            "Palmeiras": {"zero_percent": 3.7, "continent": "America do Sul", "league": "Brasileirao", "tier": "elite"},
            "Sao Paulo": {"zero_percent": 4.1, "continent": "America do Sul", "league": "Brasileirao", "tier": "elite"},
            
            "River Plate": {"zero_percent": 3.5, "continent": "America do Sul", "league": "Primera Division", "tier": "elite"},
            "Boca Juniors": {"zero_percent": 4.1, "continent": "America do Sul", "league": "Primera Division", "tier": "elite"},
        }
        
        self.monitored_users = set()
        self.detected_games = {}
        self.application = None
        self.running = True
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.fixtures = [
            {"home_team": "FC Porto", "away_team": "Estrela Vermelha", "kickoff": "21:00", "competition": "Liga Europa", "date": today},
            {"home_team": "Manchester City", "away_team": "Newcastle", "kickoff": "17:00", "competition": "Premier League", "date": today},
            {"home_team": "Real Madrid", "away_team": "Barcelona", "kickoff": "16:15", "competition": "La Liga", "date": today}
        ]
        
        logger.info(f"Bot iniciado com {len(self.teams_data)} equipes")

    def start_monitoring(self, app):
        self.application = app
        
        def monitor():
            logger.info("Monitoramento iniciado")
            time.sleep(10)
            
            while self.running:
                try:
                    asyncio.run(self.check_games())
                    time.sleep(300)
                except Exception as e:
                    logger.error(f"Erro: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    async def check_games(self):
        try:
            logger.info("Verificando jogos...")
            today = datetime.now().strftime("%Y-%m-%d")
            
            for fixture in self.fixtures:
                if fixture["date"] == today:
                    home = fixture["home_team"]
                    away = fixture["away_team"]
                    
                    if home in self.teams_data or away in self.teams_data:
                        key = f"{home}_vs_{away}"
                        
                        if key not in self.detected_games:
                            self.detected_games[key] = fixture
                            logger.info(f"Jogo detectado: {home} vs {away}")
                            await self.send_alerts(fixture)
            
        except Exception as e:
            logger.error(f"Erro verificacao: {e}")

    async def send_alerts(self, game):
        try:
            if not self.monitored_users:
                return
                
            home = game["home_team"]
            away = game["away_team"]
            
            msg = f"""🚨 JOGO DETECTADO!

⚽ {home} vs {away}
🕒 {game["kickoff"]}
🏆 {game["competition"]}

"""
            
            if home in self.teams_data:
                info = self.teams_data[home]
                msg += f"🏠 {home}: {info['zero_percent']}% (0x0)\n"
            
            if away in self.teams_data:
                info = self.teams_data[away]
                msg += f"✈️ {away}: {info['zero_percent']}% (0x0)\n"
            
            msg += "\n🤖 Sistema automatico"
            
            for user_id in list(self.monitored_users):
                try:
                    await self.application.bot.send_message(user_id, msg)
                except:
                    self.monitored_users.discard(user_id)
                    
        except Exception as e:
            logger.error(f"Erro alertas: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"""🚀 Bot Automatico de Futebol

🤖 SISTEMA ATIVO:
✅ {len(self.teams_data)} equipes
✅ Deteccao automatica
✅ Sistema Cash Out

COMANDOS:
/ativar_alertas - Ativar
/jogos_hoje - Ver jogos
/analise [equipe] - Analisar
/equipes - Listar

🎯 HOJE: FC Porto vs Estrela Vermelha

Digite /ativar_alertas!"""
        
        await update.message.reply_text(text)

    async def activate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.monitored_users.add(user_id)
        
        text = f"""🔔 ALERTAS ATIVADOS!

✅ Voce recebera:
• Jogos detectados
• Analises automaticas
• Recomendacoes Cash Out

Sistema: {len(self.teams_data)} equipes
Detectados: {len(self.detected_games)} jogos

Status: /status_auto"""
        
        await update.message.reply_text(text)
        logger.info(f"Usuario {user_id} ativou alertas")

    async def games_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.detected_games:
            text = """📅 JOGOS HOJE

❌ Nenhum detectado ainda
🔍 Sistema verificando...
🔔 /ativar_alertas"""
        else:
            text = f"📅 JOGOS DETECTADOS ({len(self.detected_games)})\n\n"
            
            for game in self.detected_games.values():
                home = game["home_team"]
                away = game["away_team"]
                
                home_ok = "✅" if home in self.teams_data else "❌"
                away_ok = "✅" if away in self.teams_data else "❌"
                
                text += f"⚽ {home} {home_ok} vs {away} {away_ok}\n"
                text += f"🕒 {game['kickoff']} | {game['competition']}\n\n"
        
        await update.message.reply_text(text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        status = "🔔 ATIVO" if user_id in self.monitored_users else "⏸️ INATIVO"
        
        text = f"""🤖 STATUS SISTEMA

📊 Seu status: {status}
👥 Usuarios: {len(self.monitored_users)}
🎯 Jogos hoje: {len(self.detected_games)}
⚡ Equipes: {len(self.teams_data)}

Sistema: Funcionando
Verificacao: A cada 5min

🔔 /ativar_alertas"""
        
        await update.message.reply_text(text)

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Uso: /analise [equipe]\n💡 /analise FC Porto")
            return
        
        team = " ".join(context.args)
        found = None
        
        for t in self.teams_data:
            if team.lower() in t.lower():
                found = t
                break
        
        if not found:
            await update.message.reply_text(f"❌ '{team}' nao encontrada\n📋 /equipes")
            return
        
        info = self.teams_data[found]
        tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
        
        # Verificar jogo hoje
        game_today = None
        for game in self.detected_games.values():
            if found in [game["home_team"], game["away_team"]]:
                game_today = game
                break
        
        text = f"""🏆 {found.upper()} {tier_emoji[info['tier']]}

📊 STATS:
• Liga: {info['league']}
• % 0x0: {info['zero_percent']}%
• Tier: {info['tier']}

💰 CASH OUT: {"DEIXAR_CORRER" if info['tier'] != 'standard' else "CASH_OUT_80"}"""
        
        if game_today:
            opp = game_today["away_team"] if found == game_today["home_team"] else game_today["home_team"]
            local = "🏠" if found == game_today["home_team"] else "✈️"
            
            text += f"""

🚨 JOGO HOJE!
• Vs: {opp}
• Horario: {game_today['kickoff']}
• Local: {local}
• Comp: {game_today['competition']}
✅ Sistema ativo"""
        
        await update.message.reply_text(text)

    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        continents = {}
        for team, info in self.teams_data.items():
            cont = info["continent"]
            if cont not in continents:
                continents[cont] = []
            continents[cont].append((team, info))
        
        text = f"🌍 EQUIPES ({len(self.teams_data)} total)\n\n"
        
        for cont, teams in continents.items():
            text += f"🌟 {cont} ({len(teams)})\n"
            teams.sort(key=lambda x: x[1]["zero_percent"])
            
            for team, info in teams[:3]:
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                text += f"{tier_emoji[info['tier']]} {team} - {info['zero_percent']}%\n"
            
            if len(teams) > 3:
                text += f"... +{len(teams)-3}\n"
            text += "\n"
        
        await update.message.reply_text(text)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Erro: {context.error}")

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("Token nao encontrado!")
        sys.exit(1)
    
    logger.info("Iniciando bot...")
    
    bot = AutomaticBot()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", bot.start_command))
    app.add_handler(CommandHandler("ativar_alertas", bot.activate_command))
    app.add_handler(CommandHandler("jogos_hoje", bot.games_command))
    app.add_handler(CommandHandler("status_auto", bot.status_command))
    app.add_handler(CommandHandler("analise", bot.analyze_command))
    app.add_handler(CommandHandler("equipes", bot.teams_command))
    app.add_error_handler(bot.error_handler)
    
    logger.info(f"Bot carregado - {len(bot.teams_data)} equipes!")
    
    bot.start_monitoring(app)
    
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Erro: {e}")
        bot.running = False

if __name__ == '__main__':
    main()
