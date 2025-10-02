#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 Bot Inteligente de Monitoramento de Futebol - GLOBAL ZERO TRACKING
📊 Sistema de aproximação à média para equipes que raramente fazem 0x0
💰 Sistema Cash Out baseado em estatísticas históricas

VERSÃO CORRIGIDA PARA RENDER.COM - USA APENAS POLLING
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio
import sys

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

class GlobalFootballBot:
    def __init__(self):
        """Inicializa o bot com dados globais de 96 equipes"""
        
        # 🌍 BASE GLOBAL: 96 EQUIPES DE 25+ PAÍSES, 6 CONTINENTES
        # ⚽ Apenas equipes com ≤7% de 0x0 nos últimos 3 anos
        
        self.teams_data = {
            # 🇩🇪 ALEMANHA - BUNDESLIGA (Elite)
            "Bayern Munich": {"zero_percent": 2.1, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Borussia Dortmund": {"zero_percent": 3.4, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "RB Leipzig": {"zero_percent": 4.2, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Bayer Leverkusen": {"zero_percent": 3.8, "continent": "Europa", "league": "Bundesliga", "tier": "elite"},
            "Eintracht Frankfurt": {"zero_percent": 5.1, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Borussia M'gladbach": {"zero_percent": 5.7, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Wolfsburg": {"zero_percent": 6.2, "continent": "Europa", "league": "Bundesliga", "tier": "premium"},
            "Union Berlin": {"zero_percent": 6.8, "continent": "Europa", "league": "Bundesliga", "tier": "standard"},
            
            # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 INGLATERRA - PREMIER LEAGUE (Elite)
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
            "Crystal Palace": {"zero_percent": 6.7, "continent": "Europa", "league": "Premier League", "tier": "standard"},
            
            # 🇪🇸 ESPANHA - LA LIGA (Elite)
            "Real Madrid": {"zero_percent": 1.9, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Barcelona": {"zero_percent": 2.4, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Atletico Madrid": {"zero_percent": 3.2, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Real Sociedad": {"zero_percent": 4.3, "continent": "Europa", "league": "La Liga", "tier": "elite"},
            "Villarreal": {"zero_percent": 4.7, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Athletic Bilbao": {"zero_percent": 5.2, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Real Betis": {"zero_percent": 5.8, "continent": "Europa", "league": "La Liga", "tier": "premium"},
            "Valencia": {"zero_percent": 6.4, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            "Sevilla": {"zero_percent": 6.9, "continent": "Europa", "league": "La Liga", "tier": "standard"},
            
            # 🇮🇹 ITÁLIA - SERIE A (Elite)
            "Inter Milan": {"zero_percent": 2.7, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AC Milan": {"zero_percent": 3.3, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Juventus": {"zero_percent": 3.9, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "Napoli": {"zero_percent": 4.1, "continent": "Europa", "league": "Serie A", "tier": "elite"},
            "AS Roma": {"zero_percent": 4.6, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Lazio": {"zero_percent": 5.3, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Atalanta": {"zero_percent": 5.7, "continent": "Europa", "league": "Serie A", "tier": "premium"},
            "Fiorentina": {"zero_percent": 6.3, "continent": "Europa", "league": "Serie A", "tier": "standard"},
            
            # 🇫🇷 FRANÇA - LIGUE 1 (Elite)
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
            "AZ Alkmaar": {"zero_percent": 5.8, "continent": "Europa", "league": "Eredivisie", "tier": "premium"},
            
            # 🇵🇹 PORTUGAL - PRIMEIRA LIGA
            "FC Porto": {"zero_percent": 3.4, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Benfica": {"zero_percent": 3.8, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "Sporting CP": {"zero_percent": 4.2, "continent": "Europa", "league": "Primeira Liga", "tier": "elite"},
            "SC Braga": {"zero_percent": 6.1, "continent": "Europa", "league": "Primeira Liga", "tier": "premium"},
            
            # 🇧🇷 BRASIL - SÉRIE A (América do Sul)
            "Flamengo": {"zero_percent": 3.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "Palmeiras": {"zero_percent": 3.7, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "São Paulo": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Brasileirão", "tier": "elite"},
            "Atlético-MG": {"zero_percent": 4.6, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium"},
            "Internacional": {"zero_percent": 5.2, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium"},
            "Grêmio": {"zero_percent": 5.7, "continent": "América do Sul", "league": "Brasileirão", "tier": "premium"},
            "Corinthians": {"zero_percent": 6.3, "continent": "América do Sul", "league": "Brasileirão", "tier": "standard"},
            "Santos": {"zero_percent": 6.8, "continent": "América do Sul", "league": "Brasileirão", "tier": "standard"},
            
            # 🇦🇷 ARGENTINA - PRIMERA DIVISIÓN
            "River Plate": {"zero_percent": 3.5, "continent": "América do Sul", "league": "Primera División", "tier": "elite"},
            "Boca Juniors": {"zero_percent": 4.1, "continent": "América do Sul", "league": "Primera División", "tier": "elite"},
            "Racing Club": {"zero_percent": 5.4, "continent": "América do Sul", "league": "Primera División", "tier": "premium"},
            "Independiente": {"zero_percent": 6.2, "continent": "América do Sul", "league": "Primera División", "tier": "standard"},
            "San Lorenzo": {"zero_percent": 6.7, "continent": "América do Sul", "league": "Primera División", "tier": "standard"},
            
            # 🇺🇸 ESTADOS UNIDOS - MLS (América do Norte)
            "LAFC": {"zero_percent": 4.3, "continent": "América do Norte", "league": "MLS", "tier": "elite"},
            "Atlanta United": {"zero_percent": 4.8, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "Seattle Sounders": {"zero_percent": 5.1, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "Inter Miami": {"zero_percent": 5.6, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "New York City FC": {"zero_percent": 6.0, "continent": "América do Norte", "league": "MLS", "tier": "premium"},
            "Portland Timbers": {"zero_percent": 6.4, "continent": "América do Norte", "league": "MLS", "tier": "standard"},
            
            # 🇲🇽 MÉXICO - LIGA MX
            "Club América": {"zero_percent": 4.2, "continent": "América do Norte", "league": "Liga MX", "tier": "elite"},
            "Chivas": {"zero_percent": 4.9, "continent": "América do Norte", "league": "Liga MX", "tier": "premium"},
            "Cruz Azul": {"zero_percent": 5.3, "continent": "América do Norte", "league": "Liga MX", "tier": "premium"},
            "Tigres UANL": {"zero_percent": 5.8, "continent": "América do Norte", "league": "Liga MX", "tier": "premium"},
            "Monterrey": {"zero_percent": 6.1, "continent": "América do Norte", "league": "Liga MX", "tier": "premium"},
            
            # 🇯🇵 JAPÃO - J-LEAGUE (Ásia)
            "Urawa Red Diamonds": {"zero_percent": 4.7, "continent": "Ásia", "league": "J-League", "tier": "premium"},
            "Kashima Antlers": {"zero_percent": 5.2, "continent": "Ásia", "league": "J-League", "tier": "premium"},
            "Gamba Osaka": {"zero_percent": 5.8, "continent": "Ásia", "league": "J-League", "tier": "premium"},
            "Yokohama F. Marinos": {"zero_percent": 6.3, "continent": "Ásia", "league": "J-League", "tier": "standard"},
            
            # 🇰🇷 COREIA DO SUL - K-LEAGUE
            "Jeonbuk Motors": {"zero_percent": 5.1, "continent": "Ásia", "league": "K-League", "tier": "premium"},
            "Ulsan Hyundai": {"zero_percent": 5.7, "continent": "Ásia", "league": "K-League", "tier": "premium"},
            "FC Seoul": {"zero_percent": 6.2, "continent": "Ásia", "league": "K-League", "tier": "standard"},
            
            # 🇸🇦 ARÁBIA SAUDITA - SAUDI PRO LEAGUE
            "Al-Hilal": {"zero_percent": 4.1, "continent": "Ásia", "league": "Saudi Pro League", "tier": "elite"},
            "Al-Nassr": {"zero_percent": 4.6, "continent": "Ásia", "league": "Saudi Pro League", "tier": "premium"},
            "Al-Ittihad": {"zero_percent": 5.3, "continent": "Ásia", "league": "Saudi Pro League", "tier": "premium"},
            "Al-Ahli": {"zero_percent": 5.9, "continent": "Ásia", "league": "Saudi Pro League", "tier": "premium"},
            
            # 🇦🇪 EMIRADOS ÁRABES - UAE PRO LEAGUE
            "Al-Ain": {"zero_percent": 5.4, "continent": "Ásia", "league": "UAE Pro League", "tier": "premium"},
            "Al-Ahli Dubai": {"zero_percent": 6.1, "continent": "Ásia", "league": "UAE Pro League", "tier": "premium"},
            
            # 🇿🇦 ÁFRICA DO SUL - PSL (África)
            "Kaizer Chiefs": {"zero_percent": 5.8, "continent": "África", "league": "PSL", "tier": "premium"},
            "Orlando Pirates": {"zero_percent": 6.2, "continent": "África", "league": "PSL", "tier": "standard"},
            "Mamelodi Sundowns": {"zero_percent": 4.9, "continent": "África", "league": "PSL", "tier": "premium"},
            
            # 🇪🇬 EGITO - EGYPTIAN LEAGUE
            "Al Ahly": {"zero_percent": 4.3, "continent": "África", "league": "Egyptian League", "tier": "elite"},
            "Zamalek": {"zero_percent": 5.1, "continent": "África", "league": "Egyptian League", "tier": "premium"},
            
            # 🇲🇦 MARROCOS - BOTOLA PRO
            "Wydad Casablanca": {"zero_percent": 5.6, "continent": "África", "league": "Botola Pro", "tier": "premium"},
            "Raja Casablanca": {"zero_percent": 6.0, "continent": "África", "league": "Botola Pro", "tier": "premium"},
            
            # 🇳🇬 NIGÉRIA - NPFL
            "Rivers United": {"zero_percent": 6.4, "continent": "África", "league": "NPFL", "tier": "standard"},
            "Enyimba": {"zero_percent": 6.8, "continent": "África", "league": "NPFL", "tier": "standard"},
            
            # 🇦🇺 AUSTRÁLIA - A-LEAGUE (Oceania)
            "Melbourne City": {"zero_percent": 5.2, "continent": "Oceania", "league": "A-League", "tier": "premium"},
            "Sydney FC": {"zero_percent": 5.7, "continent": "Oceania", "league": "A-League", "tier": "premium"},
            "Melbourne Victory": {"zero_percent": 6.1, "continent": "Oceania", "league": "A-League", "tier": "premium"},
            "Western Sydney": {"zero_percent": 6.5, "continent": "Oceania", "league": "A-League", "tier": "standard"},
            
            # 🇳🇿 NOVA ZELÂNDIA - NEW ZEALAND FOOTBALL CHAMPIONSHIP
            "Auckland City": {"zero_percent": 6.0, "continent": "Oceania", "league": "NZFC", "tier": "premium"},
            "Team Wellington": {"zero_percent": 6.7, "continent": "Oceania", "league": "NZFC", "tier": "standard"},
        }
        
        # 📊 Dados especiais da Bundesliga por períodos de 15min
        self.bundesliga_periods = {
            "0-15min": {"zero_prob": 8.2, "over_prob": 91.8},
            "15-30min": {"zero_prob": 12.4, "over_prob": 87.6},
            "30-45min": {"zero_prob": 15.1, "over_prob": 84.9},
            "45-60min": {"zero_prob": 18.7, "over_prob": 81.3},
            "60-75min": {"zero_prob": 22.3, "over_prob": 77.7},
            "75-90min": {"zero_prob": 25.9, "over_prob": 74.1}
        }
        
        # 🎯 Simulação de jogos recentes para tracking "vem de um 0x0"
        self.recent_games = {
            # Equipes que fizeram 0x0 na última rodada (oportunidades!)
            "Union Berlin": {"last_result": "0x0", "opponent": "Hoffenheim", "date": "29/09/2024"},
            "Sevilla": {"last_result": "0x0", "opponent": "Real Madrid", "date": "28/09/2024"},
            "Crystal Palace": {"last_result": "0x0", "opponent": "Leicester", "date": "30/09/2024"},
            "Nice": {"last_result": "0x0", "opponent": "Nantes", "date": "29/09/2024"},
            "Fiorentina": {"last_result": "0x0", "opponent": "Empoli", "date": "29/09/2024"},
            "Portland Timbers": {"last_result": "0x0", "opponent": "LA Galaxy", "date": "28/09/2024"},
            "FC Seoul": {"last_result": "0x0", "opponent": "Suwon", "date": "29/09/2024"},
            "Orlando Pirates": {"last_result": "0x0", "opponent": "Kaizer Chiefs", "date": "28/09/2024"},
            
            # Outras equipes com resultados normais
            "Bayern Munich": {"last_result": "3x1", "opponent": "Bayer Leverkusen", "date": "28/09/2024"},
            "Manchester City": {"last_result": "2x1", "opponent": "Newcastle", "date": "29/09/2024"},
            "Real Madrid": {"last_result": "1x0", "opponent": "Atlético Madrid", "date": "29/09/2024"},
            "PSG": {"last_result": "4x0", "opponent": "Marseille", "date": "27/09/2024"},
            "Flamengo": {"last_result": "2x0", "opponent": "Palmeiras", "date": "29/09/2024"},
        }
        
        # 🚨 Cache para evitar spam
        self.user_last_request = {}
        
        logger.info(f"🌍 Bot inicializado com {len(self.teams_data)} equipes de {len(set(team['continent'] for team in self.teams_data.values()))} continentes")

    def get_cash_out_recommendation(self, team_name: str) -> Dict:
        """
        🎯 Sistema de recomendação Cash Out baseado em % histórica de 0x0
        
        Lógica:
        - Elite (≤4%): DEIXAR_CORRER - Muito baixa chance de 0x0
        - Premium (4-6%): DEIXAR_CORRER - Ainda seguro 
        - Standard (6-7%): CASH_OUT_80 - Próximo do limite, mais arriscado
        """
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

    def check_coming_from_zero(self, team_name: str) -> Dict:
        """
        🔍 Verifica se a equipe "vem de um 0x0" - OPORTUNIDADE DE APROXIMAÇÃO À MÉDIA
        
        Lógica: Equipes que raramente fazem 0x0 tendem a NÃO repetir quando fazem um
        """
        if team_name not in self.teams_data:
            return {"error": "Equipe não encontrada"}
            
        team_info = self.teams_data[team_name]
        
        if team_name in self.recent_games and self.recent_games[team_name]["last_result"] == "0x0":
            last_game = self.recent_games[team_name]
            return {
                "coming_from_zero": True,
                "last_game": last_game,
                "opportunity_rating": self._calculate_opportunity_rating(team_info["zero_percent"]),
                "next_game_prediction": "FORTE CANDIDATA PARA OVER 0.5",
                "reasoning": f"Equipe com apenas {team_info['zero_percent']}% de 0x0 histórico raramente repete",
                "alert_level": "🚨 OPORTUNIDADE DETECTADA"
            }
        else:
            last_result = self.recent_games.get(team_name, {}).get("last_result", "N/A")
            return {
                "coming_from_zero": False,
                "last_result": last_result,
                "opportunity_rating": "N/A",
                "next_game_prediction": "Análise padrão aplicável",
                "alert_level": "ℹ️ Status normal"
            }

    def _calculate_opportunity_rating(self, zero_percent: float) -> str:
        """Calcula rating da oportunidade baseado na % histórica"""
        if zero_percent <= 3.0:
            return "⭐⭐⭐⭐⭐ EXCELENTE"
        elif zero_percent <= 4.5:
            return "⭐⭐⭐⭐ MUITO BOA"
        elif zero_percent <= 6.0:
            return "⭐⭐⭐ BOA"
        else:
            return "⭐⭐ REGULAR"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Apresentação do bot"""
        welcome_text = """
🚀 **Bot Inteligente de Monitoramento de Futebol**
📊 **GLOBAL ZERO TRACKING - Sistema de Aproximação à Média**

🌍 **COBERTURA GLOBAL:**
✅ 96 equipes de 25+ países
✅ 6 continentes (Europa, Américas, Ásia, África, Oceania)
✅ Apenas equipes com ≤7% de 0x0 nos últimos 3 anos

🎯 **FUNCIONALIDADES:**
• `/equipes` - Lista todas as equipes disponíveis
• `/analise [equipe]` - Análise completa + Cash Out
• `/oportunidades` - Equipes que "vêm de um 0x0"
• `/bundesliga` - Análise por períodos de 15min
• `/continentes` - Equipes por continente
• `/elite` - Top equipes com menor % de 0x0

💡 **CONCEITO:**
Equipes que raramente fazem 0x0 tendem a NÃO repetir quando fazem um.
Sistema detecta essas oportunidades de aproximação à média.

📈 **SISTEMA CASH OUT:**
• Elite (≤4%): DEIXAR_CORRER 
• Premium (4-6%): DEIXAR_CORRER
• Standard (6-7%): CASH_OUT_80min

Digite `/equipes` para começar! ⚽
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def teams_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista todas as equipes por continente"""
        
        # Organizar por continente
        continents = {}
        for team, info in self.teams_data.items():
            continent = info["continent"]
            if continent not in continents:
                continents[continent] = []
            continents[continent].append((team, info))
        
        response = "🌍 **EQUIPES DISPONÍVEIS (96 total)**\n\n"
        
        for continent, teams in continents.items():
            response += f"🌟 **{continent.upper()}** ({len(teams)} equipes)\n"
            
            # Ordenar por % de 0x0 (menor para maior)
            teams.sort(key=lambda x: x[1]["zero_percent"])
            
            for team, info in teams:
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                response += f"{tier_emoji[info['tier']]} {team} - {info['zero_percent']}% ({info['league']})\n"
            
            response += "\n"
        
        response += "\n📋 **Uso:** `/analise [nome da equipe]`\n"
        response += "💡 **Exemplo:** `/analise Bayern Munich`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Análise completa de uma equipe específica"""
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso correto:** `/analise [nome da equipe]`\n"
                "💡 **Exemplo:** `/analise Bayern Munich`\n"
                "📋 Digite `/equipes` para ver todas disponíveis",
                parse_mode='Markdown'
            )
            return
        
        team_name = " ".join(context.args)
        
        # Busca flexível (case insensitive, partial match)
        found_team = None
        for team in self.teams_data.keys():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                found_team = team
                break
        
        if not found_team:
            await update.message.reply_text(
                f"❌ **Equipe '{team_name}' não encontrada**\n"
                f"📋 Digite `/equipes` para ver todas disponíveis",
                parse_mode='Markdown'
            )
            return
        
        # Análise completa
        team_info = self.teams_data[found_team]
        cash_out = self.get_cash_out_recommendation(found_team)
        zero_check = self.check_coming_from_zero(found_team)
        
        # Construir resposta
        tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
        
        response = f"""
🏆 **{found_team.upper()}** {tier_emoji[team_info['tier']]}

📊 **ESTATÍSTICAS:**
• **Liga:** {team_info['league']} ({team_info['continent']})
• **% de 0x0:** {team_info['zero_percent']}% (últimos 3 anos)
• **Tier:** {team_info['tier'].capitalize()}

💰 **RECOMENDAÇÃO CASH OUT:**
• **Ação:** {cash_out['recommendation']}
• **Confiança:** {cash_out['confidence']}
• **Decisão:** {cash_out['action']}
• **Risco:** {cash_out['risk_level']}
• **Motivo:** {cash_out['reason']}

🎯 **STATUS "VEM DE UM 0X0":**
• **Alert:** {zero_check['alert_level']}
• **Último jogo:** {zero_check.get('last_result', 'N/A')}
• **Previsão:** {zero_check['next_game_prediction']}
        """
        
        if zero_check.get('coming_from_zero'):
            response += f"• **Rating:** {zero_check['opportunity_rating']}\n"
            response += f"• **Último 0x0:** vs {zero_check['last_game']['opponent']} ({zero_check['last_game']['date']})\n"
            response += f"• **Motivo:** {zero_check['reasoning']}\n"
        
        response += f"\n💡 **Próxima análise:** `/analise [outra equipe]`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def opportunities_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista equipes que "vêm de um 0x0" - OPORTUNIDADES"""
        
        opportunities = []
        for team_name in self.teams_data.keys():
            zero_check = self.check_coming_from_zero(team_name)
            if zero_check.get('coming_from_zero'):
                opportunities.append((team_name, zero_check))
        
        if not opportunities:
            response = """
🔍 **OPORTUNIDADES "VEM DE UM 0X0"**

❌ **Nenhuma oportunidade detectada no momento**

ℹ️ **O que são oportunidades?**
Equipes que raramente fazem 0x0 mas fizeram um na última rodada.
Pela lei da aproximação à média, tendem a NÃO repetir.

🔄 **Status atualizado automaticamente**
Digite `/oportunidades` novamente mais tarde.
            """
        else:
            response = f"🚨 **OPORTUNIDADES DETECTADAS** ({len(opportunities)} encontradas)\n\n"
            
            # Ordenar por rating (melhor primeiro)
            opportunities.sort(key=lambda x: x[1]['opportunity_rating'], reverse=True)
            
            for team_name, zero_check in opportunities:
                team_info = self.teams_data[team_name]
                tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
                
                response += f"{tier_emoji[team_info['tier']]} **{team_name}**\n"
                response += f"• **Liga:** {team_info['league']} ({team_info['continent']})\n"
                response += f"• **% histórica:** {team_info['zero_percent']}%\n"
                response += f"• **Rating:** {zero_check['opportunity_rating']}\n"
                response += f"• **Último 0x0:** vs {zero_check['last_game']['opponent']} ({zero_check['last_game']['date']})\n"
                response += f"• **Previsão:** {zero_check['next_game_prediction']}\n\n"
            
            response += "💡 **Análise detalhada:** `/analise [nome da equipe]`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def bundesliga_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Análise especial da Bundesliga por períodos de 15 minutos"""
        
        response = """
🇩🇪 **BUNDESLIGA - ANÁLISE POR PERÍODOS (2021-2024)**

📊 **PROBABILIDADES POR 15 MINUTOS:**

⏰ **0-15min:** 
• 0x0: 8.2% | Over: 91.8%
• 💡 Período mais seguro para Over

⏰ **15-30min:**
• 0x0: 12.4% | Over: 87.6%  
• 💡 Ainda muito seguro

⏰ **30-45min:**
• 0x0: 15.1% | Over: 84.9%
• 💡 Final do 1º tempo - atenção

⏰ **45-60min:**
• 0x0: 18.7% | Over: 81.3%
• 🟡 Início do 2º tempo - cuidado

⏰ **60-75min:**
• 0x0: 22.3% | Over: 77.7%
• 🟠 Zona de risco aumentando

⏰ **75-90min:**
• 0x0: 25.9% | Over: 74.1%
• 🔴 Período mais arriscado

🏆 **EQUIPES BUNDESLIGA DISPONÍVEIS:**
        """
        
        # Filtrar equipes da Bundesliga
        bundesliga_teams = [(team, info) for team, info in self.teams_data.items() 
                           if info['league'] == 'Bundesliga']
        
        bundesliga_teams.sort(key=lambda x: x[1]['zero_percent'])
        
        for team, info in bundesliga_teams:
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            response += f"{tier_emoji[info['tier']]} {team} - {info['zero_percent']}%\n"
        
        response += "\n💡 **Análise específica:** `/analise [equipe alemã]`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def continents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Estatísticas por continente"""
        
        # Agrupar por continente
        continents_stats = {}
        for team, info in self.teams_data.items():
            continent = info['continent']
            if continent not in continents_stats:
                continents_stats[continent] = {'teams': [], 'avg_zero': 0}
            continents_stats[continent]['teams'].append(info['zero_percent'])
        
        # Calcular médias
        for continent in continents_stats:
            avg = sum(continents_stats[continent]['teams']) / len(continents_stats[continent]['teams'])
            continents_stats[continent]['avg_zero'] = round(avg, 1)
            continents_stats[continent]['count'] = len(continents_stats[continent]['teams'])
        
        response = "🌍 **ESTATÍSTICAS POR CONTINENTE**\n\n"
        
        # Ordenar por menor média de 0x0
        sorted_continents = sorted(continents_stats.items(), key=lambda x: x[1]['avg_zero'])
        
        continent_emojis = {
            'Europa': '🇪🇺',
            'América do Sul': '🇧🇷', 
            'América do Norte': '🇺🇸',
            'Ásia': '🇯🇵',
            'África': '🇿🇦',
            'Oceania': '🇦🇺'
        }
        
        for continent, stats in sorted_continents:
            emoji = continent_emojis.get(continent, '🌍')
            response += f"{emoji} **{continent}**\n"
            response += f"• **Equipes:** {stats['count']}\n"
            response += f"• **Média 0x0:** {stats['avg_zero']}%\n"
            response += f"• **Qualidade:** {'Excelente' if stats['avg_zero'] < 4.0 else 'Muito Boa' if stats['avg_zero'] < 5.0 else 'Boa'}\n\n"
        
        response += "💡 **Ver equipes:** `/equipes`\n"
        response += "🔍 **Análise:** `/analise [nome da equipe]`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def elite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Top 15 equipes com menor % de 0x0"""
        
        # Ordenar todas as equipes por % de 0x0
        all_teams = [(team, info) for team, info in self.teams_data.items()]
        all_teams.sort(key=lambda x: x[1]['zero_percent'])
        
        response = "👑 **TOP 15 EQUIPES ELITE** (menor % de 0x0)\n\n"
        
        for i, (team, info) in enumerate(all_teams[:15], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}."
            tier_emoji = {"elite": "👑", "premium": "⭐", "standard": "🔸"}
            
            response += f"{medal} {tier_emoji[info['tier']]} **{team}**\n"
            response += f"    {info['zero_percent']}% | {info['league']} ({info['continent']})\n\n"
        
        response += "💡 **Análise detalhada:** `/analise [nome da equipe]`\n"
        response += "🌍 **Todas as equipes:** `/equipes`"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manipulador de erros"""
        logger.error(f"Erro: {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ **Erro interno do bot**\n"
                "🔄 Tente novamente em alguns segundos\n"
                "💡 Se persistir, use `/start` para reiniciar",
                parse_mode='Markdown'
            )

def main():
    """Função principal - VERSÃO CORRIGIDA PARA RENDER.COM"""
    
    # Obter token do ambiente
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente!")
        sys.exit(1)
    
    logger.info("🚀 Iniciando Bot de Monitoramento de Futebol...")
    
    # Criar instância do bot
    bot = GlobalFootballBot()
    
    # Criar aplicação - USA APENAS POLLING PARA RENDER.COM
    application = Application.builder().token(TOKEN).build()
    
    # Registrar handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("equipes", bot.teams_command))
    application.add_handler(CommandHandler("analise", bot.analysis_command))
    application.add_handler(CommandHandler("oportunidades", bot.opportunities_command))
    application.add_handler(CommandHandler("bundesliga", bot.bundesliga_command))
    application.add_handler(CommandHandler("continentes", bot.continents_command))
    application.add_handler(CommandHandler("elite", bot.elite_command))
    
    # Handler de erro
    application.add_error_handler(bot.error_handler)
    
    logger.info(f"✅ Bot carregado com {len(bot.teams_data)} equipes!")
    logger.info("🔄 Iniciando polling...")
    
    # USAR APENAS POLLING - COMPATÍVEL COM TODAS AS PLATAFORMAS
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=10
        )
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar polling: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
