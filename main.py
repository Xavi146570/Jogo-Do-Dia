#!/usr/bin/env python3
import logging
import os
from datetime import datetime
import asyncio
import sys
import threading
import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class Bot:
    def __init__(self):
        self.teams = {
            "FC Porto": {"zero_percent": 3.4, "tier": "elite"},
            "Manchester City": {"zero_percent": 1.8, "tier": "elite"},
            "Real Madrid": {"zero_percent": 1.9, "tier": "elite"},
            "Barcelona": {"zero_percent": 2.4, "tier": "elite"},
            "Bayern Munich": {"zero_percent": 2.1, "tier": "elite"},
            "Liverpool": {"zero_percent": 2.3, "tier": "elite"},
            "PSG": {"zero_percent": 2.1, "tier": "elite"},
            "Inter Milan": {"zero_percent": 2.7, "tier": "elite"}
        }
        
        self.users = set()
        self.games = {}
        self.app = None
        self.running = True
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.fixtures = [
            {"home": "FC Porto", "away": "Estrela Vermelha", "time": "21:00", "comp": "Liga Europa", "date": today}
        ]
        
        logger.info(f"Bot iniciado - {len(self.teams)} equipes")

    def start_monitor(self, application):
        self.app = application
        
        def monitor():
            time.sleep(10)
            while self.running:
                try:
                    asyncio.run(self.check())
                    time.sleep(300)
                except Exception as e:
                    logger.error(f"Erro: {e}")
                    time.sleep(60)
        
        threading.Thread(target=monitor, daemon=True).start()
        logger.info("Monitor iniciado")

    async def check(self):
        today = datetime.now().strftime("%Y-%m-%d")
        for game in self.fixtures:
            if game["date"] == today:
                home, away = game["home"], game["away"]
                if home in self.teams or away in self.teams:
                    key = f"{home}_{away}"
                    if key not in self.games:
                        self.games[key] = game
                        logger.info(f"Detectado: {home} vs {away}")
                        await self.alert(game)

    async def alert(self, game):
        if not self.users:
            return
        
        msg = f"""🚨 JOGO DETECTADO!

⚽ {game["home"]} vs {game["away"]}
🕒 {game["time"]}
🏆 {game["comp"]}

🤖 Sistema automatico"""
        
        for user in list(self.users):
            try:
                await self.app.bot.send_message(user, msg)
            except:
                self.users.discard(user)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"""🚀 Bot Automatico

✅ {len(self.teams)} equipes
✅ Sistema ativo

/ativar - Ativar alertas
/jogos - Ver jogos
/analise FC Porto - Analisar

🎯 HOJE: FC Porto vs Estrela Vermelha""")

    async def ativar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.users.add(update.effective_user.id)
        await update.message.reply_text(f"""🔔 ALERTAS ATIVADOS!

Detectados: {len(self.games)} jogos
Sistema: Funcionando""")

    async def jogos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.games:
            await update.message.reply_text("❌ Nenhum jogo detectado")
        else:
            text = f"📅 JOGOS ({len(self.games)})\n\n"
            for game in self.games.values():
                text += f"⚽ {game['home']} vs {game['away']}\n🕒 {game['time']}\n\n"
            await update.message.reply_text(text)

    async def analise(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Uso: /analise FC Porto")
            return
        
        team = " ".join(context.args)
        found = None
        for t in self.teams:
            if team.lower() in t.lower():
                found = t
                break
        
        if not found:
            await update.message.reply_text(f"❌ '{team}' nao encontrada")
            return
        
        info = self.teams[found]
        text = f"""🏆 {found.upper()}

📊 % 0x0: {info['zero_percent']}%
💰 Cash Out: DEIXAR_CORRER
🎯 Tier: {info['tier']}

🚨 JOGA HOJE vs Estrela Vermelha!"""
        
        await update.message.reply_text(text)

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        sys.exit(1)
    
    bot = Bot()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("ativar", bot.ativar))
    app.add_handler(CommandHandler("jogos", bot.jogos))
    app.add_handler(CommandHandler("analise", bot.analise))
    
    bot.start_monitor(app)
    
    try:
        app.run_polling(drop_pending_updates=True)
    except:
        bot.running = False

if __name__ == '__main__':
    main()
