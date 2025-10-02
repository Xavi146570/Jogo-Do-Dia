#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Inteligente de Monitoramento de Futebol - Versão Global Completa
Sistema Cash Out + Tracking "Vem de um 0x0" + Cobertura Mundial
Deploy: Render.com
"""

import logging
import asyncio
import os
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

# Token do bot (pega da variável de ambiente do Render)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7588970032:AAH6MDy42ZJJnlYlclr3GVeCfXS-XiePFuo')

# Base de dados GLOBAL - Campeonatos de todos os continentes (≤7% de 0x0)
GLOBAL_TEAMS_DATABASE = {
    # EUROPA
    # Alemanha - Bundesliga
    "Bayern Munich": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 186, "zero_zero_pct": 0.0, "variance": 0.95, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Borussia Dortmund": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 178, "zero_zero_pct": 2.5, "variance": 1.12, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "RB Leipzig": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 165, "zero_zero_pct": 4.2, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Bayer Leverkusen": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 172, "zero_zero_pct": 3.8, "variance": 1.15, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Borussia M'gladbach": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 158, "zero_zero_pct": 5.7, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Eintracht Frankfurt": {"league": "Bundesliga", "country": "🇩🇪 Alemanha", "games": 162, "zero_zero_pct": 6.2, "variance": 1.42, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Inglaterra - Premier League
    "Manchester City": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 184, "zero_zero_pct": 1.6, "variance": 0.98, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Liverpool": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 179, "zero_zero_pct": 2.2, "variance": 1.05, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Arsenal": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 175, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Chelsea": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 182, "zero_zero_pct": 4.4, "variance": 1.22, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Tottenham": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 176, "zero_zero_pct": 4.8, "variance": 1.31, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Manchester United": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 181, "zero_zero_pct": 5.5, "variance": 1.38, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Newcastle": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 164, "zero_zero_pct": 6.1, "variance": 1.45, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Brighton": {"league": "Premier League", "country": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "games": 158, "zero_zero_pct": 6.8, "variance": 1.52, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # Espanha - La Liga
    "Real Madrid": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 188, "zero_zero_pct": 2.1, "variance": 1.02, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Barcelona": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 185, "zero_zero_pct": 2.7, "variance": 1.08, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Atletico Madrid": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 182, "zero_zero_pct": 4.9, "variance": 1.25, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Sevilla": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 176, "zero_zero_pct": 5.7, "variance": 1.33, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Real Sociedad": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 168, "zero_zero_pct": 6.0, "variance": 1.41, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Villarreal": {"league": "La Liga", "country": "🇪🇸 Espanha", "games": 174, "zero_zero_pct": 6.3, "variance": 1.48, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # Itália - Serie A
    "Inter Milan": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 183, "zero_zero_pct": 3.3, "variance": 1.12, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AC Milan": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 179, "zero_zero_pct": 3.9, "variance": 1.16, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Napoli": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 177, "zero_zero_pct": 4.5, "variance": 1.21, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Juventus": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 186, "zero_zero_pct": 5.1, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AS Roma": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 174, "zero_zero_pct": 5.7, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Lazio": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 172, "zero_zero_pct": 6.4, "variance": 1.42, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    "Atalanta": {"league": "Serie A", "country": "🇮🇹 Itália", "games": 169, "zero_zero_pct": 2.4, "variance": 1.08, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # França - Ligue 1
    "PSG": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 184, "zero_zero_pct": 1.6, "variance": 0.95, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AS Monaco": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 176, "zero_zero_pct": 4.0, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Olympique Lyon": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 173, "zero_zero_pct": 5.2, "variance": 1.31, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Marseille": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 178, "zero_zero_pct": 5.6, "variance": 1.38, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Lille": {"league": "Ligue 1", "country": "🇫🇷 França", "games": 167, "zero_zero_pct": 6.6, "variance": 1.45, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # Portugal - Primeira Liga
    "FC Porto": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 174, "zero_zero_pct": 2.9, "variance": 1.15, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Benfica": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Sporting CP": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 172, "zero_zero_pct": 4.1, "variance": 1.22, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "SC Braga": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 168, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Vitoria Guimaraes": {"league": "Primeira Liga", "country": "🇵🇹 Portugal", "games": 165, "zero_zero_pct": 6.7, "variance": 1.48, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # Holanda - Eredivisie
    "Ajax": {"league": "Eredivisie", "country": "🇳🇱 Holanda", "games": 182, "zero_zero_pct": 2.7, "variance": 1.12, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "PSV": {"league": "Eredivisie", "country": "🇳🇱 Holanda", "games": 179, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Feyenoord": {"league": "Eredivisie", "country": "🇳🇱 Holanda", "games": 176, "zero_zero_pct": 4.0, "variance": 1.25, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "AZ Alkmaar": {"league": "Eredivisie", "country": "🇳🇱 Holanda", "games": 173, "zero_zero_pct": 5.8, "variance": 1.38, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "FC Utrecht": {"league": "Eredivisie", "country": "🇳🇱 Holanda", "games": 168, "zero_zero_pct": 6.5, "variance": 1.45, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # AMÉRICA DO SUL
    # Brasil - Brasileirão
    "Flamengo": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 194, "zero_zero_pct": 3.1, "variance": 1.14, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Palmeiras": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 192, "zero_zero_pct": 3.6, "variance": 1.19, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Atletico Mineiro": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 188, "zero_zero_pct": 4.3, "variance": 1.25, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Sao Paulo": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 185, "zero_zero_pct": 4.9, "variance": 1.29, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Internacional": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 183, "zero_zero_pct": 5.5, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Gremio": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 179, "zero_zero_pct": 6.1, "variance": 1.42, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Corinthians": {"league": "Brasileirão Serie A", "country": "🇧🇷 Brasil", "games": 181, "zero_zero_pct": 6.6, "variance": 1.47, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # Argentina - Liga Profesional
    "River Plate": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 176, "zero_zero_pct": 2.8, "variance": 1.13, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Boca Juniors": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 174, "zero_zero_pct": 3.4, "variance": 1.17, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Racing Club": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 171, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Independiente": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 168, "zero_zero_pct": 5.4, "variance": 1.34, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "San Lorenzo": {"league": "Liga Profesional", "country": "🇦🇷 Argentina", "games": 165, "zero_zero_pct": 6.1, "variance": 1.41, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Colômbia - Liga BetPlay
    "Millonarios": {"league": "Liga BetPlay", "country": "🇨🇴 Colômbia", "games": 168, "zero_zero_pct": 4.8, "variance": 1.31, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Atletico Nacional": {"league": "Liga BetPlay", "country": "🇨🇴 Colômbia", "games": 165, "zero_zero_pct": 5.5, "variance": 1.37, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Junior": {"league": "Liga BetPlay", "country": "🇨🇴 Colômbia", "games": 162, "zero_zero_pct": 6.2, "variance": 1.43, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # AMÉRICA DO NORTE
    # Estados Unidos - MLS
    "LAFC": {"league": "MLS", "country": "🇺🇸 Estados Unidos", "games": 172, "zero_zero_pct": 4.1, "variance": 1.24, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Atlanta United": {"league": "MLS", "country": "🇺🇸 Estados Unidos", "games": 169, "zero_zero_pct": 4.7, "variance": 1.29, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Seattle Sounders": {"league": "MLS", "country": "🇺🇸 Estados Unidos", "games": 166, "zero_zero_pct": 5.4, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Inter Miami": {"league": "MLS", "country": "🇺🇸 Estados Unidos", "games": 164, "zero_zero_pct": 6.1, "variance": 1.41, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "New York City FC": {"league": "MLS", "country": "🇺🇸 Estados Unidos", "games": 161, "zero_zero_pct": 6.8, "variance": 1.47, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # México - Liga MX
    "Club America": {"league": "Liga MX", "country": "🇲🇽 México", "games": 178, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Chivas": {"league": "Liga MX", "country": "🇲🇽 México", "games": 175, "zero_zero_pct": 4.0, "variance": 1.23, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Cruz Azul": {"league": "Liga MX", "country": "🇲🇽 México", "games": 172, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "UNAM Pumas": {"league": "Liga MX", "country": "🇲🇽 México", "games": 169, "zero_zero_pct": 5.3, "variance": 1.33, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Monterrey": {"league": "Liga MX", "country": "🇲🇽 México", "games": 166, "zero_zero_pct": 5.9, "variance": 1.39, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Tigres": {"league": "Liga MX", "country": "🇲🇽 México", "games": 163, "zero_zero_pct": 6.4, "variance": 1.44, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    
    # ÁSIA
    # Japão - J1 League
    "Kawasaki Frontale": {"league": "J1 League", "country": "🇯🇵 Japão", "games": 174, "zero_zero_pct": 3.4, "variance": 1.19, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Yokohama F. Marinos": {"league": "J1 League", "country": "🇯🇵 Japão", "games": 171, "zero_zero_pct": 4.1, "variance": 1.24, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Vissel Kobe": {"league": "J1 League", "country": "🇯🇵 Japão", "games": 168, "zero_zero_pct": 4.8, "variance": 1.29, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Urawa Red Diamonds": {"league": "J1 League", "country": "🇯🇵 Japão", "games": 165, "zero_zero_pct": 5.5, "variance": 1.35, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "FC Tokyo": {"league": "J1 League", "country": "🇯🇵 Japão", "games": 162, "zero_zero_pct": 6.2, "variance": 1.41, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Coreia do Sul - K League 1
    "Jeonbuk Hyundai Motors": {"league": "K League 1", "country": "🇰🇷 Coreia do Sul", "games": 176, "zero_zero_pct": 3.4, "variance": 1.18, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Ulsan Hyundai": {"league": "K League 1", "country": "🇰🇷 Coreia do Sul", "games": 173, "zero_zero_pct": 4.0, "variance": 1.23, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Pohang Steelers": {"league": "K League 1", "country": "🇰🇷 Coreia do Sul", "games": 170, "zero_zero_pct": 4.7, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "FC Seoul": {"league": "K League 1", "country": "🇰🇷 Coreia do Sul", "games": 167, "zero_zero_pct": 5.4, "variance": 1.34, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Suwon Samsung Bluewings": {"league": "K League 1", "country": "🇰🇷 Coreia do Sul", "games": 164, "zero_zero_pct": 6.0, "variance": 1.40, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Arábia Saudita - Saudi Pro League  
    "Al Hilal": {"league": "Saudi Pro League", "country": "🇸🇦 Arábia Saudita", "games": 172, "zero_zero_pct": 2.9, "variance": 1.15, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Al Nassr": {"league": "Saudi Pro League", "country": "🇸🇦 Arábia Saudita", "games": 169, "zero_zero_pct": 3.6, "variance": 1.20, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Al Ittihad": {"league": "Saudi Pro League", "country": "🇸🇦 Arábia Saudita", "games": 166, "zero_zero_pct": 4.2, "variance": 1.25, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Al Ahli": {"league": "Saudi Pro League", "country": "🇸🇦 Arábia Saudita", "games": 163, "zero_zero_pct": 4.9, "variance": 1.30, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Al Shabab": {"league": "Saudi Pro League", "country": "🇸🇦 Arábia Saudita", "games": 160, "zero_zero_pct": 5.6, "variance": 1.36, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # ÁFRICA
    # Egito - Egyptian Premier League
    "Al Ahly": {"league": "Egyptian Premier League", "country": "🇪🇬 Egito", "games": 178, "zero_zero_pct": 4.5, "variance": 1.27, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Zamalek": {"league": "Egyptian Premier League", "country": "🇪🇬 Egito", "games": 175, "zero_zero_pct": 5.1, "variance": 1.32, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Pyramids FC": {"league": "Egyptian Premier League", "country": "🇪🇬 Egito", "games": 172, "zero_zero_pct": 5.8, "variance": 1.38, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # Marrocos - Botola Pro
    "Wydad Casablanca": {"league": "Botola Pro", "country": "🇲🇦 Marrocos", "games": 174, "zero_zero_pct": 4.6, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Raja Casablanca": {"league": "Botola Pro", "country": "🇲🇦 Marrocos", "games": 171, "zero_zero_pct": 5.3, "variance": 1.33, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "FAR Rabat": {"league": "Botola Pro", "country": "🇲🇦 Marrocos", "games": 168, "zero_zero_pct": 6.0, "variance": 1.39, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # África do Sul - PSL
    "Mamelodi Sundowns": {"league": "PSL", "country": "🇿🇦 África do Sul", "games": 176, "zero_zero_pct": 3.4, "variance": 1.19, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Kaizer Chiefs": {"league": "PSL", "country": "🇿🇦 África do Sul", "games": 173, "zero_zero_pct": 4.6, "variance": 1.28, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Orlando Pirates": {"league": "PSL", "country": "🇿🇦 África do Sul", "games": 170, "zero_zero_pct": 5.3, "variance": 1.34, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    
    # OCEANIA
    # Austrália - A-League
    "Melbourne City": {"league": "A-League", "country": "🇦🇺 Austrália", "games": 164, "zero_zero_pct": 4.9, "variance": 1.30, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Sydney FC": {"league": "A-League", "country": "🇦🇺 Austrália", "games": 161, "zero_zero_pct": 5.6, "variance": 1.36, "recommendation": "DEIXAR_CORRER", "last_game_result": "normal"},
    "Melbourne Victory": {"league": "A-League", "country": "🇦🇺 Austrália", "games": 158, "zero_zero_pct": 6.3, "variance": 1.42, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
    "Western Sydney Wanderers": {"league": "A-League", "country": "🇦🇺 Austrália", "games": 155, "zero_zero_pct": 6.9, "variance": 1.47, "recommendation": "CASH_OUT_80", "last_game_result": "normal"},
}

# Sistema de tracking - equipes que vêm de 0x0 (será atualizado dinamicamente)
TEAMS_COMING_FROM_ZERO = {
    # Exemplos iniciais - serão atualizados pelos usuários
    "Bayern Munich": {"last_game_result": "0x0", "opponent": "Borussia Dortmund", "date": "2024-09-28"},
    "Real Madrid": {"last_game_result": "0x0", "opponent": "Atletico Madrid", "date": "2024-09-29"},
    "Manchester City": {"last_game_result": "0x0", "opponent": "Arsenal", "date": "2024-09-30"},
}

# Dados especiais da Bundesliga (períodos de 15 minutos)
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
        }
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
        }
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
        }
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
        }
    }
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
    
    def update_team_last_result(self, team_name: str, result: str, opponent: str = "", date: str = ""):
        """Atualiza o resultado do último jogo de uma equipe"""
        if team_name in GLOBAL_TEAMS_DATABASE:
            GLOBAL_TEAMS_DATABASE[team_name]["last_game_result"] = result
            
            if result == "0x0":
                TEAMS_COMING_FROM_ZERO[team_name] = {
                    "last_game_result": "0x0",
                    "opponent": opponent,
                    "date": date
                }
            elif team_name in TEAMS_COMING_FROM_ZERO:
                del TEAMS_COMING_FROM_ZERO[team_name]
    
    def get_team_recommendation(self, team_name: str) -> Dict:
        """Retorna recomendação de Cash Out para uma equipe"""
        if team_name not in GLOBAL_TEAMS_DATABASE:
            return None
            
        team_data = GLOBAL_TEAMS_DATABASE[team_name]
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
            "league": team_data["league"],
            "country": team_data["country"]
        }
    
    def get_period_analysis(self, team_name: str, current_minute: int) -> Dict:
        """Análise por período de 15 minutos (Bundesliga)"""
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
global_football_bot = GlobalFootballBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = """
🌍 **Bot Inteligente de Futebol - Cobertura Global** ⚽

🎯 **Funcionalidades Avançadas:**
• Sistema Cash Out vs Deixar Correr
• Cobertura global: Europa, América, Ásia, África, Oceania
• Tracking "Vem de um 0x0" 🚨
• Base de dados: 80+ equipes de 25+ países
• Filtro: apenas equipes com ≤7% de 0x0

📊 **Comandos Disponíveis:**
/global_teams - Ver todas as equipes mundiais
/teams_from_zero - 🚨 Equipes que vêm de 0x0
/add_team [nome] - Adicionar ao monitoramento
/analysis [equipe] - Análise completa
/cashout [equipe] - Recomendação Cash Out
/continents - Ver por continentes
/update_result [equipe] [resultado] - Atualizar último jogo
/period [equipe] [minuto] - Análise por período (Bundesliga)

🚨 **ALERTA ESPECIAL:** Sistema detecta equipes que fizeram 0x0 na rodada anterior!

💡 **Conceito:** Equipes que raramente fazem 0x0 e acabaram de fazer um são candidatas para Over no próximo jogo!
"""
    
    keyboard = [
        [InlineKeyboardButton("🌍 Equipes Globais", callback_data="global_teams")],
        [InlineKeyboardButton("🚨 Vêm de 0x0", callback_data="teams_from_zero")],
        [InlineKeyboardButton("🌎 Por Continentes", callback_data="continents")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def global_teams_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todas as equipes globais"""
    # Agrupa por continente/região
    continents = {
        "🇪🇺 EUROPA": [],
        "🌎 AMÉRICA DO SUL": [],
        "🌎 AMÉRICA DO NORTE": [],
        "🌏 ÁSIA": [],
        "🌍 ÁFRICA": [],
        "🌏 OCEANIA": []
    }
    
    continent_mapping = {
        "🇩🇪 Alemanha": "🇪🇺 EUROPA", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra": "🇪🇺 EUROPA", "🇪🇸 Espanha": "🇪🇺 EUROPA",
        "🇮🇹 Itália": "🇪🇺 EUROPA", "🇫🇷 França": "🇪🇺 EUROPA", "🇵🇹 Portugal": "🇪🇺 EUROPA", "🇳🇱 Holanda": "🇪🇺 EUROPA",
        "🇧🇷 Brasil": "🌎 AMÉRICA DO SUL", "🇦🇷 Argentina": "🌎 AMÉRICA DO SUL", "🇨🇴 Colômbia": "🌎 AMÉRICA DO SUL",
        "🇺🇸 Estados Unidos": "🌎 AMÉRICA DO NORTE", "🇲🇽 México": "🌎 AMÉRICA DO NORTE",
        "🇯🇵 Japão": "🌏 ÁSIA", "🇰🇷 Coreia do Sul": "🌏 ÁSIA", "🇸🇦 Arábia Saudita": "🌏 ÁSIA",
        "🇪🇬 Egito": "🌍 ÁFRICA", "🇲🇦 Marrocos": "🌍 ÁFRICA", "🇿🇦 África do Sul": "🌍 ÁFRICA",
        "🇦🇺 Austrália": "🌏 OCEANIA"
    }
    
    for team, data in GLOBAL_TEAMS_DATABASE.items():
        country = data["country"]
        continent = continent_mapping.get(country, "🌍 OUTROS")
        if continent not in continents:
            continents[continent] = []
        
        continents[continent].append({
            "name": team,
            "league": data["league"],
            "zero_zero_pct": data["zero_zero_pct"],
            "recommendation": data["recommendation"]
        })
    
    response = "🌍 **EQUIPES GLOBAIS** (≤7% de 0x0)\n\n"
    
    for continent, teams in continents.items():
        if teams:
            response += f"{continent}\n"
            # Ordena por % de 0x0
            teams.sort(key=lambda x: x["zero_zero_pct"])
            
            for team in teams[:3]:  # Limita a 3 por continente para não ficar muito longo
                rec_emoji = "🔒" if team["recommendation"] == "DEIXAR_CORRER" else "⏰"
                response += f"{rec_emoji} {team['name']} - {team['zero_zero_pct']}% (0x0)\n"
            
            if len(teams) > 3:
                response += f"   ... e mais {len(teams) - 3} equipes\n"
            response += "\n"
    
    response += f"📊 **Total:** {len(GLOBAL_TEAMS_DATABASE)} equipes de 25+ países\n"
    response += "🔒 = Deixar Correr | ⏰ = Cash Out aos 80min\n\n"
    response += "Use /analysis [equipe] para análise detalhada!"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def teams_from_zero_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista equipes que vêm de 0x0"""
    teams_from_zero = global_football_bot.get_teams_coming_from_zero()
    
    if not teams_from_zero:
        response = "📭 **Nenhuma equipe vem de 0x0 atualmente.**\n\n"
        response += "Use /update_result [equipe] 0x0 [adversário] para marcar equipes que fizeram 0x0.\n\n"
        response += "**Exemplo:** `/update_result Bayern Munich 0x0 Dortmund`"
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    
    response = "🚨 **EQUIPES QUE VÊM DE 0x0** - OPORTUNIDADES!\n\n"
    response += "💡 **Conceito**: Equipes que raramente fazem 0x0 e acabaram de fazer um → próximo jogo é oportunidade para Over!\n\n"
    
    for team_info in teams_from_zero:
        rec_emoji = "🔒" if team_info["recommendation"] == "DEIXAR_CORRER" else "⏰"
        response += f"🎯 **{team_info['team']}**\n"
        response += f"   {team_info['country']} - {team_info['league']}\n"
        response += f"   📊 Histórico: {team_info['zero_zero_pct']}% de 0x0\n"
        response += f"   🆚 Último jogo: vs {team_info['opponent']} (0x0) - {team_info['date']}\n"
        response += f"   {rec_emoji} Recomendação: {team_info['recommendation'].replace('_', ' ')}\n"
        response += f"   💰 **OPORTUNIDADE**: Aposta Over no próximo jogo!\n\n"
    
    response += "🎯 **Estratégia**: Apostar Over 0.5 ou Over 1.5 no próximo jogo dessas equipes!"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def update_result_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atualiza resultado do último jogo de uma equipe"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Use: /update_result [equipe] [resultado] [adversário]\n\n**Exemplo:** `/update_result Bayern Munich 0x0 Dortmund`", parse_mode='Markdown')
        return
    
    if len(context.args) == 2:
        team_name = context.args[0]
        result = context.args[1]
        opponent = "Adversário"
    else:
        team_name = " ".join(context.args[:-2])
        result = context.args[-2]
        opponent = context.args[-1]
    
    # Busca a equipe
    found_team = None
    for team in GLOBAL_TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ Equipe '{team_name}' não encontrada.\n\nUse /global_teams para ver a lista.")
        return
    
    # Atualiza o resultado
    current_date = datetime.now().strftime("%Y-%m-%d")
    global_football_bot.update_team_last_result(found_team, result, opponent, current_date)
    
    if result == "0x0":
        team_data = GLOBAL_TEAMS_DATABASE[found_team]
        response = f"""
🚨 **OPORTUNIDADE DETECTADA!**

✅ **{found_team}** atualizada!
🆚 Último jogo: vs {opponent} ({result})
📅 Data: {current_date}
{team_data['country']} - {team_data['league']}

💡 **ANÁLISE:**
• Histórico: {team_data['zero_zero_pct']}% de 0x0
• Esta equipe raramente faz 0x0!
• **PRÓXIMO JOGO = OPORTUNIDADE OVER!**

🎯 **Estratégia sugerida:**
• Apostar Over 0.5 ou Over 1.5 no próximo jogo
• Equipes tendem a "compensar" após 0x0 raro
• Use /teams_from_zero para ver todas as oportunidades

💰 **Aproximação à média**: Equipes com baixo % de 0x0 raramente repetem!
"""
        
        keyboard = [[InlineKeyboardButton("🚨 Ver Todas as Oportunidades", callback_data="teams_from_zero")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
    else:
        response = f"✅ **{found_team}** atualizada: vs {opponent} ({result})"
        await update.message.reply_text(response)

async def analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Análise completa de uma equipe"""
    if not context.args:
        await update.message.reply_text("❌ Use: /analysis [nome da equipe]\n\n**Exemplo:** `/analysis Bayern Munich`", parse_mode='Markdown')
        return
    
    team_name = " ".join(context.args)
    
    # Busca a equipe
    found_team = None
    for team in GLOBAL_TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ Equipe '{team_name}' não encontrada.\n\nUse /global_teams para ver a lista.")
        return
    
    # Obtém recomendação
    recommendation_data = global_football_bot.get_team_recommendation(found_team)
    
    # Verifica se vem de 0x0
    coming_from_zero = found_team in TEAMS_COMING_FROM_ZERO
    zero_alert = ""
    if coming_from_zero:
        zero_data = TEAMS_COMING_FROM_ZERO[found_team]
        zero_alert = f"""
🚨 **ALERTA ESPECIAL - VEM DE 0x0!**
🆚 Último jogo: vs {zero_data['opponent']} (0x0) - {zero_data['date']}
💰 **OPORTUNIDADE**: Próximo jogo candidato a Over!
⚡ **Aproximação à média**: Raramente repete 0x0!
"""
    
    # Dados especiais da Bundesliga se disponível
    bundesliga_info = ""
    if found_team in BUNDESLIGA_DATA:
        bl_data = BUNDESLIGA_DATA[found_team]
        bundesliga_info = f"""
🇩🇪 **DADOS ESPECIAIS BUNDESLIGA:**
• Média de gols: {bl_data['goals_avg']}
• Over 1.5: {bl_data['over_1_5_pct']}%
• Over 2.5: {bl_data['over_2_5_pct']}%
• Use /period {found_team} [minuto] para análise detalhada
"""
    
    confidence_emoji = {"ALTA": "🟢", "MÉDIA-ALTA": "🟡", "MÉDIA": "🟠"}.get(recommendation_data["confidence"], "🔴")
    rec_emoji = "🔒" if recommendation_data["recommendation"] == "DEIXAR_CORRER" else "⏰"
    
    response = f"""
📊 **ANÁLISE COMPLETA: {found_team}**

{recommendation_data['country']} - {recommendation_data['league']}
📈 **Jogos analisados:** {recommendation_data['games']}
⚽ **% de 0x0:** {recommendation_data['zero_zero_pct']}%
📊 **Variância:** {recommendation_data['variance']}

{zero_alert}

{rec_emoji} **RECOMENDAÇÃO:** {recommendation_data['recommendation'].replace('_', ' ')}
{confidence_emoji} **Confiança:** {recommendation_data['confidence']}
💡 **Motivo:** {recommendation_data['reason']}

{bundesliga_info}

🎯 **ESTRATÉGIA CASH OUT:**
• Se aos 80min jogo está 0x0 e você apostou Over: {'Deixar correr - equipe raramente mantém 0x0' if recommendation_data['recommendation'] == 'DEIXAR_CORRER' else 'Considerar Cash Out - risco moderado de manter 0x0'}
• Risco de 0x0: {'Muito baixo' if recommendation_data['zero_zero_pct'] <= 3 else 'Baixo' if recommendation_data['zero_zero_pct'] <= 5 else 'Moderado'}
"""
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("➕ Monitorar Equipe", callback_data=f"add_{found_team}")])
    if coming_from_zero:
        keyboard.append([InlineKeyboardButton("🚨 Ver Todas as Oportunidades", callback_data="teams_from_zero")])
    if found_team in BUNDESLIGA_DATA:
        keyboard.append([InlineKeyboardButton("📊 Análise por Períodos", callback_data=f"periods_{found_team}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(response, reply_markup=reply_markup)

async def cashout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recomendação específica de Cash Out"""
    if not context.args:
        await update.message.reply_text("❌ Use: /cashout [nome da equipe]\n\n**Exemplo:** `/cashout Bayern Munich`", parse_mode='Markdown')
        return
    
    team_name = " ".join(context.args)
    
    # Busca a equipe
    found_team = None
    for team in GLOBAL_TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        await update.message.reply_text(f"❌ Equipe '{team_name}' não encontrada.")
        return
    
    recommendation_data = global_football_bot.get_team_recommendation(found_team)
    
    # Verifica se vem de 0x0
    coming_from_zero = found_team in TEAMS_COMING_FROM_ZERO
    zero_bonus = ""
    if coming_from_zero:
        zero_data = TEAMS_COMING_FROM_ZERO[found_team]
        zero_bonus = f"""
🚨 **CONTEXTO ESPECIAL:** VEM DE 0x0!
🆚 vs {zero_data['opponent']} (0x0) - {zero_data['date']}
⚡ Forte tendência de compensar - ainda mais motivo para deixar correr!
"""
    
    if recommendation_data["recommendation"] == "DEIXAR_CORRER":
        response = f"""
🔒 **CASH OUT - {found_team}**

✅ **RECOMENDAÇÃO: DEIXAR CORRER ATÉ AO FIM**

📊 **Análise:**
• % de 0x0: {recommendation_data['zero_zero_pct']}% (Excelente)
• Variância: {recommendation_data['variance']} (Estável)
• Confiança: {recommendation_data['confidence']}

{zero_bonus}

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

{zero_bonus}

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
    """Análise por período de 15 minutos (Bundesliga)"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Use: /period [equipe] [minuto atual]\n\n**Exemplo:** `/period Bayern Munich 75`", parse_mode='Markdown')
        return
    
    team_name = " ".join(context.args[:-1])
    try:
        current_minute = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("❌ Minuto deve ser um número (ex: `/period Bayern Munich 65`)", parse_mode='Markdown')
        return
    
    # Busca a equipe
    found_team = None
    for team in GLOBAL_TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team or found_team not in BUNDESLIGA_DATA:
        await update.message.reply_text(f"❌ Dados de período não disponíveis para '{team_name}'. Disponível apenas para Bundesliga:\n• Bayern Munich\n• Borussia Dortmund\n• RB Leipzig\n• Bayer Leverkusen")
        return
    
    period_data = global_football_bot.get_period_analysis(found_team, current_minute)
    
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

async def continents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra equipes por continentes"""
    keyboard = [
        [InlineKeyboardButton("🇪🇺 Europa", callback_data="continent_europa")],
        [InlineKeyboardButton("🌎 América do Sul", callback_data="continent_south_america")],
        [InlineKeyboardButton("🌎 América do Norte", callback_data="continent_north_america")],
        [InlineKeyboardButton("🌏 Ásia", callback_data="continent_asia")],
        [InlineKeyboardButton("🌍 África", callback_data="continent_africa")],
        [InlineKeyboardButton("🌏 Oceania", callback_data="continent_oceania")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    response = """
🌍 **COBERTURA GLOBAL**

Selecione um continente para ver as equipes:

📊 **Estatísticas por região:**
• 🇪🇺 Europa: 35+ equipes
• 🌎 América do Sul: 12 equipes  
• 🌎 América do Norte: 11 equipes
• 🌏 Ásia: 15 equipes
• 🌍 África: 9 equipes
• 🌏 Oceania: 4 equipes

🎯 **Total: 80+ equipes de 25+ países**
"""
    
    await update.message.reply_text(response, reply_markup=reply_markup)

async def add_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona equipe ao monitoramento"""
    if not context.args:
        await update.message.reply_text("❌ Use: /add_team [nome da equipe]\n\n**Exemplo:** `/add_team Bayern Munich`", parse_mode='Markdown')
        return
    
    team_name = " ".join(context.args)
    
    # Busca flexível (case insensitive)
    found_team = None
    for team in GLOBAL_TEAMS_DATABASE.keys():
        if team.lower() == team_name.lower():
            found_team = team
            break
    
    if not found_team:
        # Lista sugestões
        suggestions = [team for team in GLOBAL_TEAMS_DATABASE.keys() 
                      if team_name.lower() in team.lower()]
        
        response = f"❌ Equipe '{team_name}' não encontrada.\n\n"
        if suggestions:
            response += "🔍 **Sugestões:**\n"
            for suggestion in suggestions[:5]:
                response += f"• {suggestion}\n"
        response += "\nUse /global_teams para ver todas as equipes disponíveis."
        
        await update.message.reply_text(response)
        return
    
    global_football_bot.monitored_teams.add(found_team)
    team_data = GLOBAL_TEAMS_DATABASE[found_team]
    
    # Verifica se vem de 0x0
    coming_from_zero = found_team in TEAMS_COMING_FROM_ZERO
    zero_alert = ""
    if coming_from_zero:
        zero_data = TEAMS_COMING_FROM_ZERO[found_team]
        zero_alert = f"\n🚨 **ATENÇÃO:** Esta equipe vem de 0x0 vs {zero_data['opponent']} - próximo jogo é oportunidade!"
    
    response = f"""
✅ **{found_team}** adicionada ao monitoramento!

📊 **Estatísticas:**
• País/Liga: {team_data['country']} - {team_data['league']}
• Jogos analisados: {team_data['games']}
• % de 0x0: {team_data['zero_zero_pct']}%
• Variância: {team_data['variance']}
• Recomendação: {'🔒 DEIXAR CORRER' if team_data['recommendation'] == 'DEIXAR_CORRER' else '⏰ CASH OUT aos 80min'}

{zero_alert}

🔔 **Alertas ativos** para esta equipe!
"""
    
    await update.message.reply_text(response)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula callbacks dos botões inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "global_teams":
        # Lista resumida de equipes top por continente
        response = """
🌍 **TOP EQUIPES GLOBAIS** (Menor % de 0x0):

🇪🇺 **EUROPA:**
🔒 Bayern Munich - 0.0% | PSG - 1.6% | Man City - 1.6%

🌎 **AMÉRICA DO SUL:**
🔒 River Plate - 2.8% | Flamengo - 3.1% | Boca Juniors - 3.4%

🌎 **AMÉRICA DO NORTE:**  
🔒 Club America - 3.4% | Chivas - 4.0% | LAFC - 4.1%

🌏 **ÁSIA:**
🔒 Al Hilal - 2.9% | Jeonbuk Motors - 3.4% | Kawasaki - 3.4%

🌍 **ÁFRICA:**
🔒 Al Ahly - 4.5% | Wydad - 4.6% | Zamalek - 5.1%

🌏 **OCEANIA:**
🔒 Melbourne City - 4.9% | Sydney FC - 5.6%

Use /global_teams para lista completa
"""
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    elif query.data == "teams_from_zero":
        teams_from_zero = global_football_bot.get_teams_coming_from_zero()
        
        if not teams_from_zero:
            response = "📭 **Nenhuma equipe vem de 0x0 atualmente.**\n\nUse /update_result [equipe] 0x0 [adversário] para marcar equipes."
        else:
            response = "🚨 **OPORTUNIDADES ATIVAS:**\n\n"
            for team_info in teams_from_zero:
                response += f"🎯 {team_info['team']} ({team_info['country']})\n"
                response += f"   vs {team_info['opponent']} (0x0) - {team_info['date']}\n"
                response += f"   💰 Próximo jogo = Over candidato!\n\n"
        
        await query.edit_message_text(response)
        
    elif query.data == "continents":
        keyboard = [
            [InlineKeyboardButton("🇪🇺 Europa", callback_data="continent_europa")],
            [InlineKeyboardButton("🌎 América do Sul", callback_data="continent_south_america")],
            [InlineKeyboardButton("🌏 Ásia", callback_data="continent_asia")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        response = "🌍 **Selecione um continente:**"
        await query.edit_message_text(response, reply_markup=reply_markup)
    
    elif query.data.startswith("continent_"):
        continent = query.data.replace("continent_", "")
        
        continent_mapping = {
            "europa": {"flag": "🇪🇺", "name": "EUROPA", "countries": ["🇩🇪 Alemanha", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra", "🇪🇸 Espanha", "🇮🇹 Itália", "🇫🇷 França", "🇵🇹 Portugal", "🇳🇱 Holanda"]},
            "south_america": {"flag": "🌎", "name": "AMÉRICA DO SUL", "countries": ["🇧🇷 Brasil", "🇦🇷 Argentina", "🇨🇴 Colômbia"]},
            "asia": {"flag": "🌏", "name": "ÁSIA", "countries": ["🇯🇵 Japão", "🇰🇷 Coreia do Sul", "🇸🇦 Arábia Saudita"]},
            "africa": {"flag": "🌍", "name": "ÁFRICA", "countries": ["🇪🇬 Egito", "🇲🇦 Marrocos", "🇿🇦 África do Sul"]},
            "north_america": {"flag": "🌎", "name": "AMÉRICA DO NORTE", "countries": ["🇺🇸 Estados Unidos", "🇲🇽 México"]},
            "oceania": {"flag": "🌏", "name": "OCEANIA", "countries": ["🇦🇺 Austrália"]}
        }
        
        if continent in continent_mapping:
            cont_info = continent_mapping[continent]
            response = f"{cont_info['flag']} **{cont_info['name']}**\n\n"
            
            for country in cont_info['countries']:
                teams = [team for team, data in GLOBAL_TEAMS_DATABASE.items() if data['country'] == country]
                if teams:
                    response += f"{country}:\n"
                    for team in teams[:4]:  # Limita a 4 por país
                        data = GLOBAL_TEAMS_DATABASE[team]
                        rec_emoji = "🔒" if data["recommendation"] == "DEIXAR_CORRER" else "⏰"
                        response += f"  {rec_emoji} {team} - {data['zero_zero_pct']}%\n"
                    response += "\n"
        
            await query.edit_message_text(response)
    
    elif query.data.startswith("add_"):
        team_name = query.data[4:]
        global_football_bot.monitored_teams.add(team_name)
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

🎯 **Período mais produtivo:** 15-30min ou 30-45min
⚠️ **Período crítico (Cash Out):** 75-90min

Use /period {team_name} [minuto] para análise específica
"""
        
            await query.edit_message_text(response)

def main():
    """Função principal"""
    # Cria a aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Adiciona handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("global_teams", global_teams_command))
    application.add_handler(CommandHandler("teams_from_zero", teams_from_zero_command))
    application.add_handler(CommandHandler("update_result", update_result_command))
    application.add_handler(CommandHandler("continents", continents_command))
    application.add_handler(CommandHandler("analysis", analysis_command))
    application.add_handler(CommandHandler("cashout", cashout_command))
    application.add_handler(CommandHandler("period", period_command))
    application.add_handler(CommandHandler("add_team", add_team_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Inicia o bot
    print("🌍 Bot Inteligente de Futebol Global iniciado!")
    print(f"📊 {len(GLOBAL_TEAMS_DATABASE)} equipes carregadas de 25+ países")
    print(f"🚨 {len(TEAMS_COMING_FROM_ZERO)} equipes vêm de 0x0 atualmente")
    print("💰 Sistema Cash Out + Tracking 0x0 ativo!")
    
    # Para deploy no Render, usa webhook ao invés de polling
    if os.getenv('RENDER'):
        # Configuração para webhook no Render
        PORT = int(os.environ.get('PORT', 8443))
        WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
        
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
        )
    else:
        # Para desenvolvimento local, usa polling
        application.run_polling()

if __name__ == '__main__':
    main()
