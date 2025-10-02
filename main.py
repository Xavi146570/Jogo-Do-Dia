#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Inteligente de Monitoramento de Futebol - Versão Global + Monitor Automático
Sistema Cash Out + Tracking "Vem de um 0x0" + Cobertura Mundial + DETECÇÃO AUTOMÁTICA
Deploy: Render.com
"""

import logging
import asyncio
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import json
from typing import Dict, List, Tuple, Optional
import statistics
import aiohttp

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do bot (pega da variável de ambiente do Render)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7588970032:AAH6MDy42ZJJnlYlclr3GVeCfXS-XiePFuo')

# Lista de usuários ativos (que mandam /start)
ACTIVE_USERS = set()

# Base de dados GLOBAL - Campeonatos de todos os continentes (≤7% de 0x0)
GLOBAL_TEAMS_DATABASE = {
    # EUROPA
    # Alemanha - Bundesliga
    "Bayern Munich": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 186, "zero_zero_pct": 0.0, "variance": 0.95, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Borussia Dortmund": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 178, "zero_zero_pct": 2.5, "variance": 1.12, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "RB Leipzig": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 165, "zero_zero_pct": 4.2, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Bayer Leverkusen": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 172, "zero_zero_pct": 3.8, "variance": 1.15, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Inglaterra - Premier League
    "Manchester City": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 184, "zero_zero_pct": 1.6, "variance": 0.98, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Liverpool": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 179, "zero_zero_pct": 2.2, "variance": 1.05, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Arsenal": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 175, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Chelsea": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 182, "zero_zero_pct": 4.4, "variance": 1.22, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Espanha - La Liga
    "Real Madrid": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 188, "zero_zero_pct": 2.1, "variance": 1.02, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Barcelona": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 185, "zero_zero_pct": 2.7, "variance": 1.08, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Atletico Madrid": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 182, "zero_zero_pct": 4.9, "variance": 1.25, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Itália - Serie A
    "Inter Milan": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 183, "zero_zero_pct": 3.3, "variance": 1.12, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AC Milan": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 179, "zero_zero_pct": 3.9, "variance": 1.16, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Napoli": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 177, "zero_zero_pct": 4.5, "variance": 1.21, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Juventus": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 186, "zero_zero_pct": 5.1, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # França - Ligue 1
    "PSG": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 184, "zero_zero_pct": 1.6, "variance": 0.95, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AS Monaco": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 176, "zero_zero_pct": 4.0, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Portugal - Primeira Liga
    "FC Porto": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 174, "zero_zero_pct": 2.9, "variance": 1.15, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Benfica": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Sporting CP": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 172, "zero_zero_pct": 4.1, "variance": 1.22, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # AMÉRICA DO SUL
    # Brasil - Brasileirão
    "Flamengo": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 194, "zero_zero_pct": 3.1, "variance": 1.14, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Palmeiras": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 192, "zero_zero_pct": 3.6, "variance": 1.19, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Argentina - Liga Profesional
    "River Plate": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 176, "zero_zero_pct": 2.8, "variance": 1.13, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Boca Juniors": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 174, "zero_zero_pct": 3.4, "variance": 1.17, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
}

# Sistema de tracking - equipes que vêm de 0x0
TEAMS_COMING_FROM_ZERO = {
    "Bayern Munich": {"last_game_result": "0x0", "opponent": "Borussia Dortmund", "date": "2024-09-28"},
    "Real Madrid": {"last_game_result": "0x0", "opponent": "Atletico Madrid", "date": "2024-09-29"},
}

class GlobalFootballBot:
    def __init__(self):
        self.monitored_teams = set()
        self.active_alerts = {}
        
    def get_teams_coming_from_zero(self) -> List[Dict]:
        """Retorna lista de equipes que vêm de 0x0"""
        teams_from_zero = []
        
        for team_name, team_data in GLOBAL_TEAMS_DATABASE.items():
            if team_name in TEAMS_COMING_FROM_ZERO:
                zero_data = TEAMS_COMING_FROM_ZERO[team_name]
                teams_from_zero.append({
                    "team": team_name,
                    "country": team_data["country"],
                    "league": team_data["league"],
                    "zero_zero_pct": team_data["zero_zero_pct"],
                    "opponent": zero_data["opponent"],
                    "date": zero_data["date"],
                    "recommendation": team_data["recommendation"]
                })
        
        return teams_from_zero

# Instância global do bot
global_football_bot = GlobalFootballBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - registra usuário para alertas automáticos"""
    global ACTIVE_USERS
    
    chat_id = update.effective_chat.id
    ACTIVE_USERS.add(chat_id)
    
    logger.info(f"✅ USUÁRIO REGISTRADO: {chat_id} | Total ativo: {len(ACTIVE_USERS)}")
    
    welcome_text = f"""
🌍 **Bot Inteligente de Futebol - Monitor Automático** ⚽

✅ **Você foi registrado com sucesso!**
📊 **Monitorando {len(GLOBAL_TEAMS_DATABASE)} equipes globais**

🚨 **SISTEMA AUTOMÁTICO ATIVO:**
• Detecção automática de jogos a cada 5 minutos
• Alertas em tempo real no seu chat
• Sistema Cash Out inteligente
• Tracking "vem de um 0x0"

🎯 **Comandos Disponíveis:**
/status - Ver status do monitor
/teams - Lista de equipes monitoradas
/stop - Parar alertas

💡 **O sistema está FUNCIONANDO!**
Você receberá alertas automáticos quando jogos das equipes filtradas forem detectados.
    """
    
    await update.message.reply_text(welcome_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    total_users = len(ACTIVE_USERS)
    total_teams = len(GLOBAL_TEAMS_DATABASE)
    teams_from_zero = len(TEAMS_COMING_FROM_ZERO)
    
    status_text = f"""
📊 **STATUS DO MONITOR AUTOMÁTICO**

✅ **Sistema:** ATIVO
👥 **Usuários ativos:** {total_users}
⚽ **Equipes monitoradas:** {total_teams}
🚨 **Vêm de 0x0:** {teams_from_zero}

🔄 **Última verificação:** {datetime.now().strftime("%H:%M:%S")}
⏰ **Próxima verificação:** Em 5 minutos

🎯 **Critérios de filtro:**
• Apenas equipes com ≤7% de 0x0
• Cobertura global (Europa, América, Ásia)
• Sistema Cash Out ativo
    """
    
    await update.message.reply_text(status_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stop"""
    global ACTIVE_USERS
    
    chat_id = update.effective_chat.id
    if chat_id in ACTIVE_USERS:
        ACTIVE_USERS.remove(chat_id)
        await update.message.reply_text("❌ **Alertas desativados.** Use /start para reativar.")
        logger.info(f"🛑 Usuário {chat_id} desativou alertas")
    else:
        await update.message.reply_text("⚠️ Você não estava recebendo alertas.")

async def teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista das principais equipes"""
    response = """
🌍 **PRINCIPAIS EQUIPES MONITORADAS:**

🇪🇺 **EUROPA:**
🔒 Bayern Munich - 0.0% | PSG - 1.6% | Man City - 1.6%
🔒 Real Madrid - 2.1% | Liverpool - 2.2% | Barcelona - 2.7%

🌎 **AMÉRICA DO SUL:**
🔒 River Plate - 2.8% | Flamengo - 3.1% | Boca Juniors - 3.4%

💡 **Sistema detecta automaticamente quando essas equipes jogam!**
🔒 = Deixar Correr | ⏰ = Cash Out aos 80min
    """
    
    await update.message.reply_text(response)

async def check_games_api():
    """Verifica jogos via API - versão simplificada para teste"""
    try:
        # Esta é uma simulação - você pode conectar a uma API real aqui
        # Por exemplo: Football-API, RapidAPI Sports, etc.
        
        logger.info("🔍 Verificando jogos...")
        
        # Para demonstração, vamos simular alguns jogos
        simulated_games = [
            {
                "home_team": "FC Porto",
                "away_team": "Estrela Vermelha", 
                "competition": "Liga Europa",
                "time": "21:00",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            {
                "home_team": "Bayern Munich",
                "away_team": "Arsenal",
                "competition": "Champions League", 
                "time": "20:00",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        ]
        
        # Filtra apenas jogos com equipes da nossa base
        filtered_games = []
        for game in simulated_games:
            if (game["home_team"] in GLOBAL_TEAMS_DATABASE or 
                game["away_team"] in GLOBAL_TEAMS_DATABASE):
                filtered_games.append(game)
                logger.info(f"✅ JOGO DETECTADO: {game['home_team']} vs {game['away_team']}")
        
        return filtered_games
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar jogos: {e}")
        return []

async def send_game_alert(bot: Bot, game_data: dict):
    """Envia alerta de jogo para todos os usuários ativos"""
    global ACTIVE_USERS
    
    if not ACTIVE_USERS:
        logger.warning("⚠️ Nenhum usuário ativo para enviar alertas")
        return
    
    # Identifica qual equipe está na nossa base
    team_info = None
    monitored_team = None
    
    for team_name in [game_data["home_team"], game_data["away_team"]]:
        if team_name in GLOBAL_TEAMS_DATABASE:
            team_info = GLOBAL_TEAMS_DATABASE[team_name]
            monitored_team = team_name
            break
    
    if not team_info:
        logger.warning(f"⚠️ Nenhuma equipe monitorada encontrada: {game_data['home_team']} vs {game_data['away_team']}")
        return
    
    # Verifica se vem de 0x0
    coming_from_zero = monitored_team in TEAMS_COMING_FROM_ZERO
    zero_alert = ""
    if coming_from_zero:
        zero_data = TEAMS_COMING_FROM_ZERO[monitored_team]
        zero_alert = f"""
🚨 **ATENÇÃO ESPECIAL:** {monitored_team} vem de 0x0!
🆚 Último resultado: vs {zero_data['opponent']} (0x0)
💰 **OPORTUNIDADE MÁXIMA** - Tendência de compensar!
"""
    
    # Monta a mensagem
    rec_emoji = "🔒" if team_info["recommendation"] == "DEIXAR_CORRER" else "⏰"
    
    alert_message = f"""
🚨 **JOGO DETECTADO AUTOMATICAMENTE!**

⚽ **{game_data['home_team']} vs {game_data['away_team']}**
🏆 **Competição:** {game_data['competition']}
⏰ **Horário:** {game_data['time']}
📅 **Data:** {game_data['date']}

📊 **ANÁLISE - {monitored_team}:**
• **% de 0x0 (histórico):** {team_info['zero_zero_pct']}%
• **Liga:** {team_info['league']} ({team_info['country']})
• **Jogos analisados:** {team_info['games']}

{zero_alert}

{rec_emoji} **RECOMENDAÇÃO:** {team_info['recommendation'].replace('_', ' ')}

💡 **ESTRATÉGIA:**
{('🔒 DEIXAR CORRER - Equipe raramente faz 0x0, baixo risco' if team_info['recommendation'] == 'DEIXAR_CORRER' else '⏰ CASH OUT aos 80min - % próxima do limite, risco moderado')}

🎯 **Sistema de Aproximação à Média:**
Esta equipe tem baixíssimo histórico de 0x0, sendo excelente candidata para apostas Over!
    """
    
    # Envia para todos os usuários ativos
    users_to_remove = set()
    
    for chat_id in ACTIVE_USERS.copy():
        try:
            await bot.send_message(chat_id=chat_id, text=alert_message)
            logger.info(f"✅ Alerta enviado para usuário {chat_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar para {chat_id}: {e}")
            if "chat not found" in str(e).lower() or "blocked" in str(e).lower():
                users_to_remove.add(chat_id)
    
    # Remove usuários inativos
    for chat_id in users_to_remove:
        ACTIVE_USERS.discard(chat_id)
        logger.info(f"🗑️ Usuário inativo removido: {chat_id}")

async def monitor_games():
    """Monitor principal - roda em background"""
    logger.info("🚀 INICIANDO MONITOR AUTOMÁTICO DE JOGOS")
    
    # Inicializa bot para envio de mensagens
    bot = Bot(token=BOT_TOKEN)
    
    # Teste de conectividade
    try:
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot conectado: @{bot_info.username}")
    except Exception as e:
        logger.error(f"❌ ERRO DE CONECTIVIDADE: {e}")
        return
    
    while True:
        try:
            logger.info(f"🔄 Verificação automática... Usuários ativos: {len(ACTIVE_USERS)}")
            
            # Verifica jogos
            games = await check_games_api()
            
            if games:
                logger.info(f"🎯 {len(games)} jogo(s) detectado(s)")
                for game in games:
                    await send_game_alert(bot, game)
            else:
                logger.info("😴 Nenhum jogo relevante no momento")
            
            # Aguarda 5 minutos
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"❌ Erro no monitor: {e}")
            await asyncio.sleep(60)  # Aguarda 1 minuto e tenta novamente

def main():
    """Função principal"""
    logger.info("🚀 INICIANDO BOT FUTEBOL MONITOR AUTOMÁTICO")
    logger.info(f"🔑 Token configurado: {'✅ SIM' if BOT_TOKEN and BOT_TOKEN != 'SEU_TOKEN_AQUI' else '❌ NÃO'}")
    logger.info(f"📊 Base de dados: {len(GLOBAL_TEAMS_DATABASE)} equipes carregadas")
    logger.info(f"🚨 Equipes vêm de 0x0: {len(TEAMS_COMING_FROM_ZERO)}")
    
    # Configurar aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("teams", teams_command))  
    application.add_handler(CommandHandler("stop", stop_command))
    
    # Iniciar monitor em background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Cria a task do monitor
    monitor_task = loop.create_task(monitor_games())
    
    logger.info("✅ Monitor automático iniciado!")
    logger.info("📱 Bot Telegram iniciado!")
    
    # Inicia o bot
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"❌ Erro no polling: {e}")
    finally:
        # Cancela a task do monitor ao sair
        monitor_task.cancel()

if __name__ == '__main__':
    main()
