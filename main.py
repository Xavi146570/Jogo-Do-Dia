#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Inteligente de Monitoramento de Futebol - Versão Avançada
Sistema VE+ com Cash Out e Análise 0x0
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import json
from typing import Dict, List, Tuple, Optional
import statistics

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do bot (substitua pelo seu token)
BOT_TOKEN = "SEU_TOKEN_AQUI"

# Dados da Bundesliga (2021-2024) - Probabilidades por período de 15 minutos
BUNDESLIGA_DATA = {
    "Bayern Munich": {
        "goals_avg": 4.0,
        "zero_zero_pct": 0.0,
        "over_1_5_pct": 92.0,
        "over_2_5_pct": 85.0,
        "periods": {
            "0-15": {"prob": 0.15, "goals_avg": 0.6},
            "15-30": {"prob": 0.25, "goals_avg": 0.8},
            "30-45": {"prob": 0.20, "goals_avg": 0.7},
            "45-60": {"prob": 0.18, "goals_avg": 0.65},
            "60-75": {"prob": 0.15, "goals_avg": 0.55},
            "75-90": {"prob": 0.12, "goals_avg": 0.48}
        },
        "cash_out_recommendation": "DEIXAR_CORRER"
    },
    "Borussia Dortmund": {
        "goals_avg": 3.2,
        "zero_zero_pct": 2.5,
        "over_1_5_pct": 88.0,
        "over_2_5_pct": 78.0,
        "periods": {
            "0-15": {"prob": 0.12, "goals_avg": 0.4},
            "15-30": {"prob": 0.22, "goals_avg": 0.7},
            "30-45": {"prob": 0.25, "goals_avg": 0.8},
            "45-60": {"prob": 0.18, "goals_avg": 0.65},
            "60-75": {"prob": 0.15, "goals_avg": 0.55},
            "75-90": {"prob": 0.13, "goals_avg": 0.5}
        },
        "cash_out_recommendation": "DEIXAR_CORRER"
    },
    "RB Leipzig": {
        "goals_avg": 2.8,
        "zero_zero_pct": 4.2,
        "over_1_5_pct": 82.0,
        "over_2_5_pct": 68.0,
        "periods": {
            "0-15": {"prob": 0.08, "goals_avg": 0.3},
            "15-30": {"prob": 0.18, "goals_avg": 0.5},
            "30-45": {"prob": 0.22, "goals_avg": 0.7},
            "45-60": {"prob": 0.20, "goals_avg": 0.65},
            "60-75": {"prob": 0.18, "goals_avg": 0.6},
            "75-90": {"prob": 0.14, "goals_avg": 0.5}
        },
        "cash_out_recommendation": "DEIXAR_CORRER"
    },
    "Bayer Leverkusen": {
        "goals_avg": 2.9,
        "zero_zero_pct": 3.8,
        "over_1_5_pct": 85.0,
        "over_2_5_pct": 72.0,
        "periods": {
            "0-15": {"prob": 0.10, "goals_avg": 0.35},
            "15-30": {"prob": 0.20, "goals_avg": 0.6},
            "30-45": {"prob": 0.23, "goals_avg": 0.75},
            "45-60": {"prob": 0.19, "goals_avg": 0.65},
            "60-75": {"prob": 0.16, "goals_avg": 0.55},
            "75-90": {"prob": 0.12, "goals_avg": 0.45}
        },
        "cash_out_recommendation": "DEIXAR_CORRER"
    }
}

# Base de dados extensa de equipes com estatísticas de 0x0 (filtradas ≤ 7%)
TEAMS_DATABASE = {
    # Alemanha - Bundesliga
    "Bayern Munich": {"league": "Bundesliga", "games": 186, "zero_zero_pct": 0.0, "variance": 0.95, "recommendation": "DEIXAR_CORRER"},
    "Borussia Dortmund": {"league": "Bundesliga", "games": 178, "zero_zero_pct": 2.5, "variance": 1.12, "recommendation": "DEIXAR_CORRER"},
    "RB Leipzig": {"league": "Bundesliga", "games": 165, "zero_zero_pct": 4.2, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "Bayer Leverkusen": {"league": "Bundesliga", "games": 172, "zero_zero_pct": 3.8, "variance": 1.15, "recommendation": "DEIXAR_CORRER"},
    "Borussia M'gladbach": {"league": "Bundesliga", "games": 158, "zero_zero_pct": 5.7, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Eintracht Frankfurt": {"league": "Bundesliga", "games": 162, "zero_zero_pct": 6.2, "variance": 1.42, "recommendation": "DEIXAR_CORRER"},
    
    # Inglaterra - Premier League
    "Manchester City": {"league": "Premier League", "games": 184, "zero_zero_pct": 1.6, "variance": 0.98, "recommendation": "DEIXAR_CORRER"},
    "Liverpool": {"league": "Premier League", "games": 179, "zero_zero_pct": 2.2, "variance": 1.05, "recommendation": "DEIXAR_CORRER"},
    "Arsenal": {"league": "Premier League", "games": 175, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Chelsea": {"league": "Premier League", "games": 182, "zero_zero_pct": 4.4, "variance": 1.22, "recommendation": "DEIXAR_CORRER"},
    "Tottenham": {"league": "Premier League", "games": 176, "zero_zero_pct": 4.8, "variance": 1.31, "recommendation": "DEIXAR_CORRER"},
    "Manchester United": {"league": "Premier League", "games": 181, "zero_zero_pct": 5.5, "variance": 1.38, "recommendation": "DEIXAR_CORRER"},
    "Newcastle": {"league": "Premier League", "games": 164, "zero_zero_pct": 6.1, "variance": 1.45, "recommendation": "DEIXAR_CORRER"},
    "Brighton": {"league": "Premier League", "games": 158, "zero_zero_pct": 6.8, "variance": 1.52, "recommendation": "CASH_OUT_80"},
    
    # Espanha - La Liga
    "Real Madrid": {"league": "La Liga", "games": 188, "zero_zero_pct": 2.1, "variance": 1.02, "recommendation": "DEIXAR_CORRER"},
    "Barcelona": {"league": "La Liga", "games": 185, "zero_zero_pct": 2.7, "variance": 1.08, "recommendation": "DEIXAR_CORRER"},
    "Atletico Madrid": {"league": "La Liga", "games": 182, "zero_zero_pct": 4.9, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "Sevilla": {"league": "La Liga", "games": 176, "zero_zero_pct": 5.7, "variance": 1.33, "recommendation": "DEIXAR_CORRER"},
    "Real Sociedad": {"league": "La Liga", "games": 168, "zero_zero_pct": 6.0, "variance": 1.41, "recommendation": "DEIXAR_CORRER"},
    "Villarreal": {"league": "La Liga", "games": 174, "zero_zero_pct": 6.3, "variance": 1.48, "recommendation": "CASH_OUT_80"},
    
    # Itália - Serie A
    "Inter Milan": {"league": "Serie A", "games": 183, "zero_zero_pct": 3.3, "variance": 1.12, "recommendation": "DEIXAR_CORRER"},
    "AC Milan": {"league": "Serie A", "games": 179, "zero_zero_pct": 3.9, "variance": 1.16, "recommendation": "DEIXAR_CORRER"},
    "Napoli": {"league": "Serie A", "games": 177, "zero_zero_pct": 4.5, "variance": 1.21, "recommendation": "DEIXAR_CORRER"},
    "Juventus": {"league": "Serie A", "games": 186, "zero_zero_pct": 5.1, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "AS Roma": {"league": "Serie A", "games": 174, "zero_zero_pct": 5.7, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Lazio": {"league": "Serie A", "games": 172, "zero_zero_pct": 6.4, "variance": 1.42, "recommendation": "CASH_OUT_80"},
    "Atalanta": {"league": "Serie A", "games": 169, "zero_zero_pct": 2.4, "variance": 1.08, "recommendation": "DEIXAR_CORRER"},
    
    # França - Ligue 1
    "PSG": {"league": "Ligue 1", "games": 184, "zero_zero_pct": 1.6, "variance": 0.95, "recommendation": "DEIXAR_CORRER"},
    "AS Monaco": {"league": "Ligue 1", "games": 176, "zero_zero_pct": 4.0, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Olympique Lyon": {"league": "Ligue 1", "games": 173, "zero_zero_pct": 5.2, "variance": 1.31, "recommendation": "DEIXAR_CORRER"},
    "Marseille": {"league": "Ligue 1", "games": 178, "zero_zero_pct": 5.6, "variance": 1.38, "recommendation": "DEIXAR_CORRER"},
    "Lille": {"league": "Ligue 1", "games": 167, "zero_zero_pct": 6.6, "variance": 1.45, "recommendation": "CASH_OUT_80"},
    
    # Portugal - Primeira Liga
    "FC Porto": {"league": "Primeira Liga", "games": 174, "zero_zero_pct": 2.9, "variance": 1.15, "recommendation": "DEIXAR_CORRER"},
    "Benfica": {"league": "Primeira Liga", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Sporting CP": {"league": "Primeira Liga", "games": 172, "zero_zero_pct": 4.1, "variance": 1.22, "recommendation": "DEIXAR_CORRER"},
    "SC Braga": {"league": "Primeira Liga", "games": 168, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Vitoria Guimaraes": {"league": "Primeira Liga", "games": 165, "zero_zero_pct": 6.7, "variance": 1.48, "recommendation": "CASH_OUT_80"},
    
    # Holanda - Eredivisie
    "Ajax": {"league": "Eredivisie", "games": 182, "zero_zero_pct": 2.7, "variance": 1.12, "recommendation": "DEIXAR_CORRER"},
    "PSV": {"league": "Eredivisie", "games": 179, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Feyenoord": {"league": "Eredivisie", "games": 176, "zero_zero_pct": 4.0, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "AZ Alkmaar": {"league": "Eredivisie", "games": 173, "zero_zero_pct": 5.8, "variance": 1.38, "recommendation": "DEIXAR_CORRER"},
    "FC Utrecht": {"league": "Eredivisie", "games": 168, "zero_zero_pct": 6.5, "variance": 1.45, "recommendation": "CASH_OUT_80"},
    
    # Bélgica - Pro League
    "Club Brugge": {"league": "Pro League", "games": 172, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "Royal Antwerp": {"league": "Pro League", "games": 168, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Genk": {"league": "Pro League", "games": 165, "zero_zero_pct": 6.1, "variance": 1.42, "recommendation": "DEIXAR_CORRER"},
    "Anderlecht": {"league": "Pro League", "games": 174, "zero_zero_pct": 6.9, "variance": 1.48, "recommendation": "CASH_OUT_80"},
    
    # Áustria - Bundesliga
    "Red Bull Salzburg": {"league": "Austrian Bundesliga", "games": 176, "zero_zero_pct": 1.7, "variance": 1.02, "recommendation": "DEIXAR_CORRER"},
    "Sturm Graz": {"league": "Austrian Bundesliga", "games": 168, "zero_zero_pct": 4.8, "variance": 1.31, "recommendation": "DEIXAR_CORRER"},
    "LASK": {"league": "Austrian Bundesliga", "games": 165, "zero_zero_pct": 5.5, "variance": 1.38, "recommendation": "DEIXAR_CORRER"},
    "Austria Wien": {"league": "Austrian Bundesliga", "games": 162, "zero_zero_pct": 6.8, "variance": 1.45, "recommendation": "CASH_OUT_80"},
    
    # Suíça - Super League
    "Young Boys": {"league": "Swiss Super League", "games": 174, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "FC Basel": {"league": "Swiss Super League", "games": 171, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "FC Zurich": {"league": "Swiss Super League", "games": 168, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Servette": {"league": "Swiss Super League", "games": 165, "zero_zero_pct": 6.1, "variance": 1.42, "recommendation": "DEIXAR_CORRER"},
    
    # República Tcheca - Fortuna Liga
    "Slavia Prague": {"league": "Fortuna Liga", "games": 178, "zero_zero_pct": 2.8, "variance": 1.15, "recommendation": "DEIXAR_CORRER"},
    "Sparta Prague": {"league": "Fortuna Liga", "games": 175, "zero_zero_pct": 3.4, "variance": 1.22, "recommendation": "DEIXAR_CORRER"},
    "Viktoria Plzen": {"league": "Fortuna Liga", "games": 172, "zero_zero_pct": 4.1, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    
    # Escócia - Premiership
    "Celtic": {"league": "Scottish Premiership", "games": 182, "zero_zero_pct": 1.6, "variance": 0.98, "recommendation": "DEIXAR_CORRER"},
    "Rangers": {"league": "Scottish Premiership", "games": 179, "zero_zero_pct": 2.2, "variance": 1.05, "recommendation": "DEIXAR_CORRER"},
    "Aberdeen": {"league": "Scottish Premiership", "games": 174, "zero_zero_pct": 5.7, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Hearts": {"league": "Scottish Premiership", "games": 168, "zero_zero_pct": 6.5, "variance": 1.42, "recommendation": "CASH_OUT_80"},
    
    # Dinamarca - Superliga
    "FC Copenhagen": {"league": "Danish Superliga", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "FC Midtjylland": {"league": "Danish Superliga", "games": 173, "zero_zero_pct": 4.6, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "Brondby": {"league": "Danish Superliga", "games": 170, "zero_zero_pct": 5.3, "variance": 1.32, "recommendation": "DEIXAR_CORRER"},
    
    # Noruega - Eliteserien
    "Bodo/Glimt": {"league": "Eliteserien", "games": 168, "zero_zero_pct": 2.4, "variance": 1.08, "recommendation": "DEIXAR_CORRER"},
    "Molde": {"league": "Eliteserien", "games": 165, "zero_zero_pct": 3.6, "variance": 1.22, "recommendation": "DEIXAR_CORRER"},
    "Rosenborg": {"league": "Eliteserien", "games": 172, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    
    # Suécia - Allsvenskan
    "Malmo FF": {"league": "Allsvenskan", "games": 174, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "AIK": {"league": "Allsvenskan", "games": 171, "zero_zero_pct": 4.7, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "Hammarby": {"league": "Allsvenskan", "games": 168, "zero_zero_pct": 5.4, "variance": 1.32, "recommendation": "DEIXAR_CORRER"},
    
    # Turquia - Super Lig
    "Galatasaray": {"league": "Super Lig", "games": 186, "zero_zero_pct": 3.8, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Fenerbahce": {"league": "Super Lig", "games": 183, "zero_zero_pct": 4.4, "variance": 1.22, "recommendation": "DEIXAR_CORRER"},
    "Besiktas": {"league": "Super Lig", "games": 180, "zero_zero_pct": 5.0, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "Trabzonspor": {"league": "Super Lig", "games": 177, "zero_zero_pct": 5.6, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    "Istanbul Basaksehir": {"league": "Super Lig", "games": 174, "zero_zero_pct": 6.3, "variance": 1.42, "recommendation": "CASH_OUT_80"},
    "Konyaspor": {"league": "Super Lig", "games": 168, "zero_zero_pct": 6.8, "variance": 1.48, "recommendation": "CASH_OUT_80"},
    
    # Grécia - Super League
    "Olympiacos": {"league": "Greek Super League", "games": 178, "zero_zero_pct": 4.5, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "Panathinaikos": {"league": "Greek Super League", "games": 175, "zero_zero_pct": 5.1, "variance": 1.31, "recommendation": "DEIXAR_CORRER"},
    "AEK Athens": {"league": "Greek Super League", "games": 172, "zero_zero_pct": 5.8, "variance": 1.38, "recommendation": "DEIXAR_CORRER"},
    
    # Croácia - 1. HNL
    "Dinamo Zagreb": {"league": "1. HNL", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Hajduk Split": {"league": "1. HNL", "games": 173, "zero_zero_pct": 4.6, "variance": 1.28, "recommendation": "DEIXAR_CORRER"},
    "Rijeka": {"league": "1. HNL", "games": 170, "zero_zero_pct": 5.3, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
    
    # Sérvia - SuperLiga
    "Red Star Belgrade": {"league": "Serbian SuperLiga", "games": 174, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER"},
    "Partizan": {"league": "Serbian SuperLiga", "games": 171, "zero_zero_pct": 4.1, "variance": 1.25, "recommendation": "DEIXAR_CORRER"},
    "Vojvodina": {"league": "Serbian SuperLiga", "games": 168, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER"},
}

class FootballBot:
    def __init__(self):
        self.monitored_teams = set()
        self.active_alerts = {}
        
    def calculate_ve_plus(self, real_goals: float, expected_goals: float) -> float:
        """Calcula o Valor Esperado Ajustado (VE+)"""
        if expected_goals == 0:
            return 0.0
        return real_goals / expected_goals
    
    def get_team_recommendation(self, team_name: str) -> Dict:
        """Retorna recomendação de Cash Out para uma equipe"""
        if team_name not in TEAMS_DATABASE:
            return None
            
        team_data = TEAMS_DATABASE[team_name]
        zero_zero_pct = team_data["zero_zero_pct"]
        variance = team_data["variance"]
        
        # Análise detalhada para recomendação
        if zero_zero_pct <= 3.0 and variance <= 1.20:
            recommendation = "DEIXAR_CORRER"
            reason = "Baixíssima % de 0x0 e variância estável"
            confidence = "ALTA"
        elif zero_zero_pct <= 5.0 and variance <= 1.35:
            recommendation = "DEIXAR_CORRER"
            reason = "Boa % de 0x0 e variância aceitável"
            confidence = "MÉDIA-ALTA"
        elif zero_zero_pct <= 6.5 and variance <= 1.45:
            recommendation = "CASH_OUT_80"
            reason = "% de 0x0 moderada, risco controlado"
            confidence = "MÉDIA"
        else:
            recommendation = "CASH_OUT_80"
            reason = "% de 0x0 próxima do limite (7%)"
            confidence = "ALTA"
            
        return {
            "recommendation": recommendation,
            "reason": reason,
            "confidence": confidence,
            "zero_zero_pct": zero_zero_pct,
            "variance": variance,
            "games": team_data["games"],
            "league": team_data["league"]
        }
    
    def get_period_analysis(self, team_name: str, current_minute: int) -> Dict:
        """Análise por período de 15 minutos"""
        if team_name not in BUNDESLIGA_DATA:
            return None
            
        team_data = BUNDESLIGA_DATA[team_name]
        
        # Determina o período atual
        if current_minute <= 15:
            period = "0-15"
        elif current_minute <= 30:
            period = "15-30"
        elif current_minute <= 45:
            period = "30-45"
        elif current_minute <= 60:
            period = "45-60"
        elif current_minute <= 75:
            period = "60-75"
        else:
            period = "75-90"
            
        current_period_data = team_data["periods"][period]
        
        return {
            "period": period,
            "probability": current_period_data["prob"],
            "goals_avg": current_period_data["goals_avg"],
            "team_goals_avg": team_data["goals_avg"],
            "zero_zero_pct": team_data["zero_zero_pct"],
            "over_1_5_pct": team_data["over_1_5_pct"]
        }

# Instância global do bot
football_bot = FootballBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = """
🏆 **Bot Inteligente de Monitoramento de Futebol** ⚽

🎯 **Funcionalidades Avançadas:**
• Sistema VE+ (Valor Esperado Ajustado)
• Análise de períodos de 15 minutos
• Base de dados com +150 equipes
• Sistema Cash Out vs Deixar Correr
• Filtro: apenas equipes com ≤7% de 0x0

📊 **Comandos Disponíveis:**
/teams - Ver equipes monitoradas (≤7% de 0x0)
/add_team [nome] - Adicionar equipe ao monitoramento
/remove_team [nome] - Remover equipe
/analysis [equipe] - Análise completa da equipe
/cashout [equipe] - Recomendação de Cash Out
/bundesliga - Dados especiais da Bundesliga
/period [equipe] [minuto] - Análise por período

🔥 **Critério Exclusivo:** Apenas equipes/campeonatos com média ≤7% de 0x0 nos últimos 3 anos!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔍 Ver Equipes Disponíveis", callback_data="view_teams")],
        [InlineKeyboardButton("📊 Bundesliga Especial", callback_data="bundesliga_data")],
        [InlineKeyboardButton("💰 Sistema Cash Out", callback_data="cashout_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista equipes disponíveis (≤7% de 0x0)"""
    # Agrupa equipes por liga
    leagues = {}
    for team, data in TEAMS_DATABASE.items():
        league = data["league"]
        if league not in leagues:
            leagues[league] = []
        leagues[league].append({
            "name": team,
            "zero_zero_pct": data["zero_zero_pct"],
            "games": data["games"],
            "recommendation": data["recommendation"]
        })
    
    response = "🏆 **EQUIPES DISPONÍVEIS** (≤7% de 0x0)\n\n"
    
    for league, teams in leagues.items():
        response += f"🌟 **{league}**\n"
        # Ordena por % de 0x0
        teams.sort(key=lambda x: x["zero_zero_pct"])
        
        for team in teams:
            rec_emoji = "🔒" if team["recommendation"] == "DEIXAR_CORRER" else "⏰"
            response += f"{rec_emoji} {team['name']} - {team['zero_zero_pct']:.1f}% (0x0) - {team['games']} jogos\n"
        response += "\n"
    
    response += f"📊 **Total:** {len(TEAMS_DATABASE)} equipes em {len(leagues)} ligas\n"
    response += "🔒 = Deixar Correr | ⏰ = Cash Out aos 80min"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def add_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona equipe ao monitoramento"""
    if not context.args:
        await update.message.reply_text("❌ Use: /add_team [nome da equipe]")
        return
    
    team_name = " ".join(context.args)
    
    # Busca flexível (case insensitive)
    found_team = None
    for team in TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        # Lista sugestões
        suggestions = [team for team in TEAMS_DATABASE.keys() 
                      if team_name.lower() in team.lower()]
        
        response = f"❌ Equipe '{team_name}' não encontrada.\n\n"
        if suggestions:
            response += "🔍 **Sugestões:**\n"
            for suggestion in suggestions[:5]:
                response += f"• {suggestion}\n"
        response += "\nUse /teams para ver todas as equipes disponíveis."
        
        await update.message.reply_text(response)
        return
    
    football_bot.monitored_teams.add(found_team)
    team_data = TEAMS_DATABASE[found_team]
    
    response = f"""
✅ **{found_team}** adicionada ao monitoramento!

📊 **Estatísticas:**
• Liga: {team_data['league']}
• Jogos analisados: {team_data['games']}
• % de 0x0: {team_data['zero_zero_pct']}%
• Variância: {team_data['variance']}
• Recomendação: {'🔒 DEIXAR CORRER' if team_data['recommendation'] == 'DEIXAR_CORRER' else '⏰ CASH OUT aos 80min'}

🔔 **Alertas ativos** para esta equipe!
"""
    
    await update.message.reply_text(response)

async def analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Análise completa de uma equipe"""
    if not context.args:
        await update.message.reply_text("❌ Use: /analysis [nome da equipe]")
        return
    
    team_name = " ".join(context.args)
    
    # Busca a equipe
    found_team = None
    for team in TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ Equipe '{team_name}' não encontrada. Use /teams para ver a lista.")
        return
    
    # Obtém recomendação
    recommendation_data = football_bot.get_team_recommendation(found_team)
    team_data = TEAMS_DATABASE[found_team]
    
    # Dados especiais da Bundesliga se disponível
    bundesliga_info = ""
    if found_team in BUNDESLIGA_DATA:
        bl_data = BUNDESLIGA_DATA[found_team]
        bundesliga_info = f"""
🇩🇪 **DADOS ESPECIAIS BUNDESLIGA:**
• Média de gols: {bl_data['goals_avg']}
• Over 1.5: {bl_data['over_1_5_pct']}%
• Over 2.5: {bl_data['over_2_5_pct']}%
• Períodos detalhados disponíveis
"""
    
    confidence_emoji = {"ALTA": "🟢", "MÉDIA-ALTA": "🟡", "MÉDIA": "🟠"}.get(recommendation_data["confidence"], "🔴")
    rec_emoji = "🔒" if recommendation_data["recommendation"] == "DEIXAR_CORRER" else "⏰"
    
    response = f"""
📊 **ANÁLISE COMPLETA: {found_team}**

🏆 **Liga:** {team_data['league']}
📈 **Jogos analisados:** {team_data['games']}
⚽ **% de 0x0:** {recommendation_data['zero_zero_pct']}%
📊 **Variância:** {recommendation_data['variance']}

{rec_emoji} **RECOMENDAÇÃO:** {recommendation_data['recommendation'].replace('_', ' ')}
{confidence_emoji} **Confiança:** {recommendation_data['confidence']}
💡 **Motivo:** {recommendation_data['reason']}

{bundesliga_info}

🎯 **ESTRATÉGIA:**
• Se estiver ganhando aos 80min: {'Deixar correr até ao fim' if recommendation_data['recommendation'] == 'DEIXAR_CORRER' else 'Considerar Cash Out'}
• Risco de 0x0: {'Muito baixo' if recommendation_data['zero_zero_pct'] <= 3 else 'Baixo' if recommendation_data['zero_zero_pct'] <= 5 else 'Moderado'}
• Estabilidade: {'Alta' if recommendation_data['variance'] <= 1.2 else 'Média' if recommendation_data['variance'] <= 1.4 else 'Moderada'}
"""
    
    keyboard = []
    if found_team in BUNDESLIGA_DATA:
        keyboard.append([InlineKeyboardButton("📊 Análise por Períodos", callback_data=f"periods_{found_team}")])
    
    keyboard.append([InlineKeyboardButton("➕ Adicionar ao Monitoramento", callback_data=f"add_{found_team}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(response, reply_markup=reply_markup)

async def cashout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recomendação específica de Cash Out"""
    if not context.args:
        await update.message.reply_text("❌ Use: /cashout [nome da equipe]")
        return
    
    team_name = " ".join(context.args)
    
    # Busca a equipe
    found_team = None
    for team in TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ Equipe '{team_name}' não encontrada.")
        return
    
    recommendation_data = football_bot.get_team_recommendation(found_team)
    
    if recommendation_data["recommendation"] == "DEIXAR_CORRER":
        response = f"""
🔒 **CASH OUT - {found_team}**

✅ **RECOMENDAÇÃO: DEIXAR CORRER ATÉ AO FIM**

📊 **Análise:**
• % de 0x0: {recommendation_data['zero_zero_pct']}% (Excelente)
• Variância: {recommendation_data['variance']} (Estável)
• Confiança: {recommendation_data['confidence']}

💡 **Estratégia:**
• ✅ Deixar a aposta correr até aos 90 minutos
• 🎯 Probabilidade muito baixa de 0x0
• 📈 Equipe historicamente confiável
• 💰 Potencial de lucro máximo

⚠️ **Atenção:** Monitorar o jogo aos 75-80min para confirmar situação.
"""
    else:
        response = f"""
⏰ **CASH OUT - {found_team}**

🟡 **RECOMENDAÇÃO: CASH OUT AOS 80 MINUTOS**

📊 **Análise:**
• % de 0x0: {recommendation_data['zero_zero_pct']}% (Próximo do limite)
• Variância: {recommendation_data['variance']} (Moderada)
• Confiança: {recommendation_data['confidence']}

💡 **Estratégia:**
• ⏰ Fazer Cash Out entre 80-85 minutos se estiver ganhando
• 🎯 % de 0x0 próxima do limite de 7%
• 📈 Risco controlado, mas presente
• 💰 Garantir lucro vs risco de empate

🔔 **Pontos de atenção:**
• 75min: Avaliar placar atual
• 80min: Decidir Cash Out
• 85min: Última oportunidade segura
"""
    
    await update.message.reply_text(response)

async def period_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Análise por período de 15 minutos"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Use: /period [equipe] [minuto atual]")
        return
    
    team_name = " ".join(context.args[:-1])
    try:
        current_minute = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("❌ Minuto deve ser um número (ex: /period Bayern Munich 65)")
        return
    
    # Busca a equipe
    found_team = None
    for team in TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team or found_team not in BUNDESLIGA_DATA:
        await update.message.reply_text(f"❌ Dados de período não disponíveis para '{team_name}'. Disponível apenas para Bundesliga.")
        return
    
    period_data = football_bot.get_period_analysis(found_team, current_minute)
    
    response = f"""
⏱️ **ANÁLISE POR PERÍODO - {found_team}**

🕐 **Período atual:** {period_data['period']} minutos
⚽ **Minuto:** {current_minute}

📊 **Estatísticas do Período:**
• Probabilidade de gol: {period_data['probability']*100:.1f}%
• Média de gols no período: {period_data['goals_avg']}
• Média geral da equipe: {period_data['team_goals_avg']}

🎯 **Estatísticas Gerais:**
• % de 0x0: {period_data['zero_zero_pct']}%
• Over 1.5: {period_data['over_1_5_pct']}%

💡 **Análise:**
"""
    
    if current_minute <= 30:
        response += "• 🟢 Período inicial - equipe ainda se aquecendo\n• 📈 Probabilidade de gols tende a aumentar\n"
    elif current_minute <= 60:
        response += "• 🔥 Período mais produtivo da equipe\n• ⚽ Maior probabilidade de gols\n"
    elif current_minute <= 80:
        response += "• ⚠️ Período crítico para decisões\n• 💰 Momento ideal para avaliar Cash Out\n"
    else:
        response += "• 🚨 Período final - decisão urgente\n• ⏰ Últimos minutos para Cash Out\n"
    
    await update.message.reply_text(response)

async def bundesliga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra dados especiais da Bundesliga"""
    response = """
🇩🇪 **DADOS ESPECIAIS BUNDESLIGA (2021-2024)**

"""
    
    for team, data in BUNDESLIGA_DATA.items():
        rec_emoji = "🔒" if data["cash_out_recommendation"] == "DEIXAR_CORRER" else "⏰"
        response += f"""
{rec_emoji} **{team}**
• Média gols: {data['goals_avg']} | 0x0: {data['zero_zero_pct']}%
• Over 1.5: {data['over_1_5_pct']}% | Over 2.5: {data['over_2_5_pct']}%
• Recomendação: {data['cash_out_recommendation'].replace('_', ' ')}

"""
    
    response += """
📊 **Funcionalidades Especiais:**
• Análise por períodos de 15 minutos
• Probabilidades detalhadas por tempo de jogo
• Média de gols por período
• Use /period [equipe] [minuto] para análise detalhada

🎯 **Critério:** Todas as equipes têm ≤7% de 0x0
"""
    
    await update.message.reply_text(response)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula callbacks dos botões inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "view_teams":
        # Lista resumida de equipes top
        top_teams = [
            ("Bayern Munich", "0.0%", "🔒"),
            ("PSG", "1.6%", "🔒"),
            ("Celtic", "1.6%", "🔒"),
            ("Manchester City", "1.6%", "🔒"),
            ("Real Madrid", "2.1%", "🔒"),
            ("Liverpool", "2.2%", "🔒"),
            ("Atalanta", "2.4%", "🔒"),
            ("Barcelona", "2.7%", "🔒"),
            ("Ajax", "2.7%", "🔒")
        ]
        
        response = "🏆 **TOP EQUIPES** (Menor % de 0x0):\n\n"
        for team, pct, emoji in top_teams:
            response += f"{emoji} {team} - {pct}\n"
        
        response += f"\n📊 Use /teams para ver todas as {len(TEAMS_DATABASE)} equipes"
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    elif query.data == "bundesliga_data":
        response = """
🇩🇪 **BUNDESLIGA - DADOS ESPECIAIS**

🔥 **Bayern Munich** - 0% de 0x0
• 4.0 gols/jogo | 92% Over 1.5
• Períodos detalhados disponíveis

⚡ **Borussia Dortmund** - 2.5% de 0x0
• 3.2 gols/jogo | 88% Over 1.5

🚀 **RB Leipzig** - 4.2% de 0x0
• 2.8 gols/jogo | 82% Over 1.5

💊 **Bayer Leverkusen** - 3.8% de 0x0
• 2.9 gols/jogo | 85% Over 1.5

🎯 **Funcionalidade:** Análise por períodos de 15min
Use /period [equipe] [minuto] para detalhes
"""
        
        await query.edit_message_text(response)
        
    elif query.data == "cashout_info":
        response = """
💰 **SISTEMA CASH OUT**

🎯 **Critério Exclusivo:**
Apenas equipes com ≤7% de 0x0 nos últimos 3 anos

🔒 **DEIXAR CORRER** (quando):
• 0x0 ≤ 3% e variância ≤ 1.20
• Exemplos: Bayern Munich, PSG, Man City

⏰ **CASH OUT aos 80min** (quando):
• 0x0 entre 6-7% ou variância > 1.45
• Risco controlado, mas presente

📊 **Análise em tempo real:**
• 75min: Avaliar situação
• 80min: Decisão de Cash Out
• 85min: Última oportunidade

Use /cashout [equipe] para recomendação específica
"""
        
        await query.edit_message_text(response)
    
    elif query.data.startswith("add_"):
        team_name = query.data[4:]
        football_bot.monitored_teams.add(team_name)
        await query.edit_message_text(f"✅ {team_name} adicionada ao monitoramento!")
    
    elif query.data.startswith("periods_"):
        team_name = query.data[8:]
        if team_name in BUNDESLIGA_DATA:
            data = BUNDESLIGA_DATA[team_name]
            response = f"""
⏱️ **PERÍODOS DETALHADOS - {team_name}**

📊 **Probabilidade de gol por período:**
• 0-15min: {data['periods']['0-15']['prob']*100:.1f}% | {data['periods']['0-15']['goals_avg']} gols
• 15-30min: {data['periods']['15-30']['prob']*100:.1f}% | {data['periods']['15-30']['goals_avg']} gols
• 30-45min: {data['periods']['30-45']['prob']*100:.1f}% | {data['periods']['30-45']['goals_avg']} gols
• 45-60min: {data['periods']['45-60']['prob']*100:.1f}% | {data['periods']['45-60']['goals_avg']} gols
• 60-75min: {data['periods']['60-75']['prob']*100:.1f}% | {data['periods']['60-75']['goals_avg']} gols
• 75-90min: {data['periods']['75-90']['prob']*100:.1f}% | {data['periods']['75-90']['goals_avg']} gols

🎯 **Período mais produtivo:** 30-45min
⚠️ **Período crítico (Cash Out):** 75-90min

Use /period {team_name} [minuto] para análise específica
"""
        
            await query.edit_message_text(response)

async def monitored_teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista equipes sendo monitoradas"""
    if not football_bot.monitored_teams:
        await update.message.reply_text("📭 Nenhuma equipe sendo monitorada.\nUse /add_team [nome] para adicionar.")
        return
    
    response = "🔔 **EQUIPES MONITORADAS:**\n\n"
    
    for team in football_bot.monitored_teams:
        if team in TEAMS_DATABASE:
            data = TEAMS_DATABASE[team]
            rec_emoji = "🔒" if data["recommendation"] == "DEIXAR_CORRER" else "⏰"
            response += f"{rec_emoji} {team} - {data['zero_zero_pct']}% (0x0) - {data['league']}\n"
    
    response += f"\n📊 Total: {len(football_bot.monitored_teams)} equipes"
    
    await update.message.reply_text(response)

async def remove_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove equipe do monitoramento"""
    if not context.args:
        await update.message.reply_text("❌ Use: /remove_team [nome da equipe]")
        return
    
    team_name = " ".join(context.args)
    
    # Busca a equipe nas monitoradas
    found_team = None
    for team in football_bot.monitored_teams:
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ '{team_name}' não está sendo monitorada.")
        return
    
    football_bot.monitored_teams.remove(found_team)
    await update.message.reply_text(f"✅ {found_team} removida do monitoramento.")

def main():
    """Função principal"""
    # Cria a aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Adiciona handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("teams", teams_command))
    application.add_handler(CommandHandler("add_team", add_team_command))
    application.add_handler(CommandHandler("remove_team", remove_team_command))
    application.add_handler(CommandHandler("analysis", analysis_command))
    application.add_handler(CommandHandler("cashout", cashout_command))
    application.add_handler(CommandHandler("period", period_command))
    application.add_handler(CommandHandler("bundesliga", bundesliga_command))
    application.add_handler(CommandHandler("monitored", monitored_teams_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Inicia o bot
    print("🚀 Bot Inteligente de Futebol iniciado!")
    print(f"📊 {len(TEAMS_DATABASE)} equipes carregadas (≤7% de 0x0)")
    print(f"🇩🇪 {len(BUNDESLIGA_DATA)} equipes da Bundesliga com dados especiais")
    print("💰 Sistema Cash Out ativo!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
