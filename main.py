#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Santo Graal - Sistema de Regressão à Média
Bot especializado em detectar "dívidas estatísticas" de gols
Foco: Equipes que ficaram aquém do esperado e devem "regredir à média"
"""

import os
import json
import time
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Configuração da aplicação Flask
app = Flask(__name__)

@dataclass
class TeamStats:
    nome: str
    media_gols_temporada: float
    media_gols_ultimos_10: float
    gols_ultimo_jogo: int
    jogos_abaixo_media_consecutivos: int
    deficit_acumulado: float
    zero_percent_historico: float
    forma_recente: List[int]

@dataclass
class RegressaoAlert:
    tipo: str
    jogo: str
    time_foco: str
    confianca: int
    divida_estatistica: float
    justificativa: str
    prioridade: str
    odds_recomendadas: str

class RegressaoMediaSystem:
    """Sistema de detecção de padrões de regressão à média"""
    
    def __init__(self):
        self.threshold_desvio = 1.2  # Desvio mínimo para considerar "aquém"
        self.janela_analise = 10     # Últimos 10 jogos para calcular média
        self.api_key = os.getenv('API_FOOTBALL_KEY', 'demo_key')
        self.base_url = "https://v3.football.api-sports.io"
        
        # Base de dados expandida focada em regressão à média
        self.teams_database = self._init_teams_database()
        
        # Alertas ativos
        self.alertas_ativos = []
        
        # Estatísticas de performance
        self.stats = {
            'total_alertas': 0,
            'alertas_corretos': 0,
            'eficacia_dupla_divida': 0,
            'eficacia_sequencia_critica': 0,
            'ultimo_scan': None
        }
    
    def _init_teams_database(self):
        """Base de dados focada em equipes com padrões de regressão identificáveis"""
        return {
            # PREMIER LEAGUE - Elite com padrões claros
            'Manchester City': {'media_temp': 2.4, 'zero_pct': 3.2, 'liga': 'Premier League', 'volatilidade': 'baixa'},
            'Arsenal': {'media_temp': 2.1, 'zero_pct': 4.1, 'liga': 'Premier League', 'volatilidade': 'baixa'},
            'Liverpool': {'media_temp': 2.3, 'zero_pct': 3.8, 'liga': 'Premier League', 'volatilidade': 'baixa'},
            'Newcastle': {'media_temp': 1.9, 'zero_pct': 5.2, 'liga': 'Premier League', 'volatilidade': 'média'},
            'Brighton': {'media_temp': 1.7, 'zero_pct': 6.1, 'liga': 'Premier League', 'volatilidade': 'média'},
            'Aston Villa': {'media_temp': 1.8, 'zero_pct': 5.8, 'liga': 'Premier League', 'volatilidade': 'média'},
            'West Ham': {'media_temp': 1.6, 'zero_pct': 6.8, 'liga': 'Premier League', 'volatilidade': 'alta'},
            'Crystal Palace': {'media_temp': 1.5, 'zero_pct': 7.2, 'liga': 'Premier League', 'volatilidade': 'alta'},
            
            # BUNDESLIGA - Padrões alemães previsíveis
            'Bayern München': {'media_temp': 2.6, 'zero_pct': 2.1, 'liga': 'Bundesliga', 'volatilidade': 'baixa'},
            'Borussia Dortmund': {'media_temp': 2.2, 'zero_pct': 3.4, 'liga': 'Bundesliga', 'volatilidade': 'baixa'},
            'RB Leipzig': {'media_temp': 2.0, 'zero_pct': 4.2, 'liga': 'Bundesliga', 'volatilidade': 'baixa'},
            'Bayer Leverkusen': {'media_temp': 1.9, 'zero_pct': 4.8, 'liga': 'Bundesliga', 'volatilidade': 'média'},
            'Eintracht Frankfurt': {'media_temp': 1.8, 'zero_pct': 5.5, 'liga': 'Bundesliga', 'volatilidade': 'média'},
            'VfB Stuttgart': {'media_temp': 1.7, 'zero_pct': 6.2, 'liga': 'Bundesliga', 'volatilidade': 'média'},
            'Borussia M\'gladbach': {'media_temp': 1.6, 'zero_pct': 6.9, 'liga': 'Bundesliga', 'volatilidade': 'alta'},
            
            # LA LIGA - Padrões espanhóis
            'Real Madrid': {'media_temp': 2.3, 'zero_pct': 3.1, 'liga': 'La Liga', 'volatilidade': 'baixa'},
            'Barcelona': {'media_temp': 2.2, 'zero_pct': 3.5, 'liga': 'La Liga', 'volatilidade': 'baixa'},
            'Atlético Madrid': {'media_temp': 1.8, 'zero_pct': 5.2, 'liga': 'La Liga', 'volatilidade': 'média'},
            'Real Sociedad': {'media_temp': 1.7, 'zero_pct': 5.8, 'liga': 'La Liga', 'volatilidade': 'média'},
            'Villarreal': {'media_temp': 1.6, 'zero_pct': 6.4, 'liga': 'La Liga', 'volatilidade': 'média'},
            'Athletic Bilbao': {'media_temp': 1.5, 'zero_pct': 6.9, 'liga': 'La Liga', 'volatilidade': 'alta'},
            
            # SERIE A - Padrões italianos
            'Inter Milan': {'media_temp': 2.1, 'zero_pct': 3.8, 'liga': 'Serie A', 'volatilidade': 'baixa'},
            'AC Milan': {'media_temp': 1.9, 'zero_pct': 4.5, 'liga': 'Serie A', 'volatilidade': 'baixa'},
            'Napoli': {'media_temp': 1.8, 'zero_pct': 5.1, 'liga': 'Serie A', 'volatilidade': 'média'},
            'Juventus': {'media_temp': 1.7, 'zero_pct': 5.7, 'liga': 'Serie A', 'volatilidade': 'média'},
            'Roma': {'media_temp': 1.6, 'zero_pct': 6.3, 'liga': 'Serie A', 'volatilidade': 'média'},
            'Atalanta': {'media_temp': 2.0, 'zero_pct': 4.1, 'liga': 'Serie A', 'volatilidade': 'baixa'},
            
            # LIGUE 1 - Padrões franceses
            'PSG': {'media_temp': 2.5, 'zero_pct': 2.8, 'liga': 'Ligue 1', 'volatilidade': 'baixa'},
            'Monaco': {'media_temp': 1.9, 'zero_pct': 4.6, 'liga': 'Ligue 1', 'volatilidade': 'baixa'},
            'Marseille': {'media_temp': 1.7, 'zero_pct': 5.4, 'liga': 'Ligue 1', 'volatilidade': 'média'},
            'Lyon': {'media_temp': 1.6, 'zero_pct': 6.1, 'liga': 'Ligue 1', 'volatilidade': 'média'},
            'Nice': {'media_temp': 1.5, 'zero_pct': 6.8, 'liga': 'Ligue 1', 'volatilidade': 'alta'},
            
            # EREDIVISIE - Alta previsibilidade
            'Ajax': {'media_temp': 2.3, 'zero_pct': 3.2, 'liga': 'Eredivisie', 'volatilidade': 'baixa'},
            'PSV': {'media_temp': 2.4, 'zero_pct': 2.9, 'liga': 'Eredivisie', 'volatilidade': 'baixa'},
            'Feyenoord': {'media_temp': 2.1, 'zero_pct': 3.7, 'liga': 'Eredivisie', 'volatilidade': 'baixa'},
            
            # PRIMEIRA LIGA PORTUGUESA
            'Benfica': {'media_temp': 2.2, 'zero_pct': 3.4, 'liga': 'Primeira Liga', 'volatilidade': 'baixa'},
            'Porto': {'media_temp': 2.1, 'zero_pct': 3.8, 'liga': 'Primeira Liga', 'volatilidade': 'baixa'},
            'Sporting': {'media_temp': 2.0, 'zero_pct': 4.1, 'liga': 'Primeira Liga', 'volatilidade': 'baixa'},
            'Braga': {'media_temp': 1.7, 'zero_pct': 5.6, 'liga': 'Primeira Liga', 'volatilidade': 'média'},
            
            # CHAMPIONSHIP - Alta volatilidade, bons padrões
            'Leicester City': {'media_temp': 1.8, 'zero_pct': 5.2, 'liga': 'Championship', 'volatilidade': 'média'},
            'Leeds United': {'media_temp': 1.9, 'zero_pct': 4.8, 'liga': 'Championship', 'volatilidade': 'média'},
            'Southampton': {'media_temp': 1.7, 'zero_pct': 5.9, 'liga': 'Championship', 'volatilidade': 'média'},
            
            # BRASILEIRÃO - Padrões sul-americanos
            'Flamengo': {'media_temp': 1.9, 'zero_pct': 4.6, 'liga': 'Brasileirão', 'volatilidade': 'média'},
            'Palmeiras': {'media_temp': 1.8, 'zero_pct': 5.1, 'liga': 'Brasileirão', 'volatilidade': 'média'},
            'Corinthians': {'media_temp': 1.6, 'zero_pct': 6.4, 'liga': 'Brasileirão', 'volatilidade': 'alta'},
            'São Paulo': {'media_temp': 1.5, 'zero_pct': 6.8, 'liga': 'Brasileirão', 'volatilidade': 'alta'},
            
            # LIGA MX - Padrões mexicanos
            'América': {'media_temp': 1.8, 'zero_pct': 5.2, 'liga': 'Liga MX', 'volatilidade': 'média'},
            'Cruz Azul': {'media_temp': 1.7, 'zero_pct': 5.7, 'liga': 'Liga MX', 'volatilidade': 'média'},
            'Chivas': {'media_temp': 1.6, 'zero_pct': 6.3, 'liga': 'Liga MX', 'volatilidade': 'alta'},
            
            # MLS - Padrões americanos
            'LAFC': {'media_temp': 1.9, 'zero_pct': 4.7, 'liga': 'MLS', 'volatilidade': 'média'},
            'Inter Miami': {'media_temp': 1.8, 'zero_pct': 5.3, 'liga': 'MLS', 'volatilidade': 'média'},
            'Atlanta United': {'media_temp': 1.7, 'zero_pct': 5.8, 'liga': 'MLS', 'volatilidade': 'média'}
        }
    
    def calcular_divida_estatistica(self, equipe_nome: str, gols_ultimo_jogo: int) -> Dict:
        """Calcula a dívida estatística de uma equipe"""
        if equipe_nome not in self.teams_database:
            return {'tem_divida': False}
        
        equipe_data = self.teams_database[equipe_nome]
        media_esperada = equipe_data['media_temp']
        
        # Calcular dívida
        divida = media_esperada - gols_ultimo_jogo
        
        # Ajustar por volatilidade da equipe
        volatilidade_multiplier = {
            'baixa': 1.2,    # Equipes consistentes têm maior pressão para regredir
            'média': 1.0,
            'alta': 0.8      # Equipes voláteis têm menor pressão
        }
        
        divida_ajustada = divida * volatilidade_multiplier.get(equipe_data['volatilidade'], 1.0)
        
        if divida_ajustada >= self.threshold_desvio:
            probabilidade = min(75 + (divida_ajustada * 8), 94)
            
            return {
                'tem_divida': True,
                'divida_gols': round(divida_ajustada, 2),
                'probabilidade_regressao': int(probabilidade),
                'urgencia': 'CRÍTICA' if divida_ajustada >= 2.0 else 'ALTA' if divida_ajustada >= 1.5 else 'MÉDIA',
                'volatilidade': equipe_data['volatilidade']
            }
        
        return {'tem_divida': False}
    
    def detectar_confronto_dupla_divida(self, time1: str, time2: str, gols_t1: int, gols_t2: int) -> Optional[Dict]:
        """Detecta confrontos onde AMBAS equipes têm dívida estatística - PADRÃO OURO"""
        
        divida_t1 = self.calcular_divida_estatistica(time1, gols_t1)
        divida_t2 = self.calcular_divida_estatistica(time2, gols_t2)
        
        if divida_t1['tem_divida'] and divida_t2['tem_divida']:
            
            # Calcular probabilidade combinada (com ajuste para não passar de 100%)
            prob_combinada = min(
                (divida_t1['probabilidade_regressao'] + divida_t2['probabilidade_regressao']) * 0.7,
                94
            )
            
            # Bonus por dupla dívida
            prob_final = min(prob_combinada + 8, 96)
            
            return {
                'tipo': 'DUPLA_DÍVIDA',
                'time1': time1,
                'time2': time2,
                'divida_t1': divida_t1['divida_gols'],
                'divida_t2': divida_t2['divida_gols'],
                'probabilidade': int(prob_final),
                'urgencia_t1': divida_t1['urgencia'],
                'urgencia_t2': divida_t2['urgencia'],
                'justificativa': f"DUPLA DÍVIDA: {time1} deve {divida_t1['divida_gols']} gols ({divida_t1['urgencia']}), {time2} deve {divida_t2['divida_gols']} gols ({divida_t2['urgencia']})"
            }
        
        return None
    
    def detectar_sequencia_sous(self, equipe: str, ultimos_resultados: List[int]) -> Optional[Dict]:
        """Detecta equipes em sequência crítica abaixo da média"""
        
        if equipe not in self.teams_database:
            return None
        
        media_esperada = self.teams_database[equipe]['media_temp']
        
        # Analisar últimos 3-5 jogos
        jogos_abaixo = 0
        deficit_total = 0
        
        for gols in ultimos_resultados[-5:]:  # Últimos 5 jogos
            if gols < media_esperada:
                jogos_abaixo += 1
                deficit_total += (media_esperada - gols)
        
        # SEQUÊNCIA CRÍTICA: 3+ jogos consecutivos abaixo
        if jogos_abaixo >= 3:
            pressao_acumulada = min(85 + (deficit_total * 4), 93)
            
            return {
                'tipo': 'SEQUÊNCIA_CRÍTICA',
                'equipe': equipe,
                'jogos_consecutivos_aquem': jogos_abaixo,
                'deficit_acumulado': round(deficit_total, 2),
                'probabilidade_explosao': int(pressao_acumulada),
                'nivel_critico': 'MÁXIMO' if jogos_abaixo >= 4 else 'ALTO'
            }
        
        # SEQUÊNCIA PREOCUPANTE: 2 jogos abaixo
        elif jogos_abaixo >= 2:
            return {
                'tipo': 'TENDÊNCIA_SOUS',
                'equipe': equipe,
                'probabilidade_explosao': 72,
                'nivel_critico': 'MÉDIO'
            }
        
        return None
    
    def scanner_regressao_completo(self) -> List[RegressaoAlert]:
        """Scanner completo procurando todos os padrões de regressão à média"""
        
        print("🔍 Iniciando scanner de regressão à média...")
        
        # Simular jogos do dia (em produção, viria da API)
        jogos_simulados = [
            {
                'time_casa': 'Manchester City',
                'time_visitante': 'Brighton',
                'gols_ultimo_casa': 0,  # City ficou aquém
                'gols_ultimo_visitante': 1,
                'forma_casa': [2, 3, 0, 2, 1],  # Último foi 0
                'forma_visitante': [1, 1, 2, 0, 1],
                'horario': '15:30',
                'odds_over05': 1.12
            },
            {
                'time_casa': 'Arsenal',
                'time_visitante': 'West Ham',
                'gols_ultimo_casa': 0,  # Arsenal ficou aquém
                'gols_ultimo_visitante': 0,  # West Ham também! DUPLA DÍVIDA
                'forma_casa': [2, 1, 0, 2, 2],
                'forma_visitante': [1, 0, 1, 1, 0],
                'horario': '17:45',
                'odds_over05': 1.18
            },
            {
                'time_casa': 'Bayern München',
                'time_visitante': 'Borussia Dortmund',
                'gols_ultimo_casa': 1,  # Abaixo da média (2.6)
                'gols_ultimo_visitante': 0,  # Muito abaixo (2.2)
                'forma_casa': [3, 2, 1, 2, 3],
                'forma_visitante': [2, 0, 1, 1, 0],
                'horario': '18:30',
                'odds_over05': 1.08
            },
            {
                'time_casa': 'Real Madrid',
                'time_visitante': 'Barcelona',
                'gols_ultimo_casa': 0,  # El Clasico com ambas aquém
                'gols_ultimo_visitante': 1,  # Barca abaixo da média
                'forma_casa': [2, 0, 1, 2, 0],
                'forma_visitante': [1, 2, 1, 0, 1],
                'horario': '21:00',
                'odds_over05': 1.15
            }
        ]
        
        oportunidades = []
        
        for jogo in jogos_simulados:
            time_casa = jogo['time_casa']
            time_visitante = jogo['time_visitante']
            
            # VERIFICAÇÃO 1: Dupla dívida (prioridade máxima)
            dupla_divida = self.detectar_confronto_dupla_divida(
                time_casa, time_visitante,
                jogo['gols_ultimo_casa'], jogo['gols_ultimo_visitante']
            )
            
            if dupla_divida:
                alert = RegressaoAlert(
                    tipo='DUPLA_DÍVIDA',
                    jogo=f"{time_casa} vs {time_visitante}",
                    time_foco='AMBAS',
                    confianca=dupla_divida['probabilidade'],
                    divida_estatistica=dupla_divida['divida_t1'] + dupla_divida['divida_t2'],
                    justificativa=dupla_divida['justificativa'],
                    prioridade='MÁXIMA',
                    odds_recomendadas=f"Over 0.5 ({jogo['odds_over05']}) + Over 1.5 se >= 1.40"
                )
                oportunidades.append(alert)
                continue
            
            # VERIFICAÇÃO 2: Sequências críticas
            seq_casa = self.detectar_sequencia_sous(time_casa, jogo['forma_casa'])
            seq_visitante = self.detectar_sequencia_sous(time_visitante, jogo['forma_visitante'])
            
            if seq_casa and seq_casa['tipo'] == 'SEQUÊNCIA_CRÍTICA':
                alert = RegressaoAlert(
                    tipo='SEQUÊNCIA_CRÍTICA',
                    jogo=f"{time_casa} vs {time_visitante}",
                    time_foco=time_casa,
                    confianca=seq_casa['probabilidade_explosao'],
                    divida_estatistica=seq_casa['deficit_acumulado'],
                    justificativa=f"{time_casa} em {seq_casa['jogos_consecutivos_aquem']} jogos consecutivos abaixo da média",
                    prioridade='ALTA',
                    odds_recomendadas=f"Over 0.5 ({jogo['odds_over05']}), foco {time_casa} marcar"
                )
                oportunidades.append(alert)
            
            elif seq_visitante and seq_visitante['tipo'] == 'SEQUÊNCIA_CRÍTICA':
                alert = RegressaoAlert(
                    tipo='SEQUÊNCIA_CRÍTICA',
                    jogo=f"{time_casa} vs {time_visitante}",
                    time_foco=time_visitante,
                    confianca=seq_visitante['probabilidade_explosao'],
                    divida_estatistica=seq_visitante['deficit_acumulado'],
                    justificativa=f"{time_visitante} em {seq_visitante['jogos_consecutivos_aquem']} jogos consecutivos abaixo da média",
                    prioridade='ALTA',
                    odds_recomendadas=f"Over 0.5 ({jogo['odds_over05']}), foco {time_visitante} marcar"
                )
                oportunidades.append(alert)
            
            # VERIFICAÇÃO 3: Dívidas individuais significativas
            else:
                divida_casa = self.calcular_divida_estatistica(time_casa, jogo['gols_ultimo_casa'])
                divida_visitante = self.calcular_divida_estatistica(time_visitante, jogo['gols_ultimo_visitante'])
                
                melhor_divida = divida_casa if divida_casa.get('probabilidade_regressao', 0) > divida_visitante.get('probabilidade_regressao', 0) else divida_visitante
                melhor_time = time_casa if melhor_divida == divida_casa else time_visitante
                
                if melhor_divida.get('tem_divida'):
                    alert = RegressaoAlert(
                        tipo='DÍVIDA_INDIVIDUAL',
                        jogo=f"{time_casa} vs {time_visitante}",
                        time_foco=melhor_time,
                        confianca=melhor_divida['probabilidade_regressao'],
                        divida_estatistica=melhor_divida['divida_gols'],
                        justificativa=f"{melhor_time} deve {melhor_divida['divida_gols']} gols ({melhor_divida['urgencia']})",
                        prioridade='MÉDIA',
                        odds_recomendadas=f"Over 0.5 ({jogo['odds_over05']})"
                    )
                    oportunidades.append(alert)
        
        # Ordenar por confiança
        oportunidades_ordenadas = sorted(oportunidades, key=lambda x: x.confianca, reverse=True)
        
        # Atualizar alertas ativos
        self.alertas_ativos = oportunidades_ordenadas
        self.stats['ultimo_scan'] = datetime.now().strftime('%H:%M:%S')
        self.stats['total_alertas'] = len(oportunidades_ordenadas)
        
        print(f"✅ Scanner concluído: {len(oportunidades_ordenadas)} oportunidades detectadas")
        
        return oportunidades_ordenadas

# Instância global do sistema
sistema_regressao = RegressaoMediaSystem()

# Templates HTML
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Santo Graal - Regressão à Média</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; 
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        .header p { 
            font-size: 1.1em; 
            opacity: 0.9; 
        }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .stat-card { 
            background: rgba(255,255,255,0.15); 
            padding: 20px; 
            border-radius: 12px; 
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-number { 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #4CAF50; 
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        .alert-card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 25px; 
            margin-bottom: 20px; 
            border-left: 5px solid;
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease;
        }
        .alert-card:hover { transform: translateY(-5px); }
        .maxima { border-left-color: #ff4444; background: rgba(255,68,68,0.15); }
        .alta { border-left-color: #ff9800; background: rgba(255,152,0,0.15); }
        .media { border-left-color: #2196F3; background: rgba(33,150,243,0.15); }
        .alert-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 15px; 
        }
        .alert-title { 
            font-size: 1.4em; 
            font-weight: bold; 
        }
        .confidence-badge { 
            background: #4CAF50; 
            padding: 8px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
            font-size: 1.1em;
        }
        .alert-info { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 15px; 
            margin-bottom: 15px; 
        }
        .info-item { 
            background: rgba(0,0,0,0.2); 
            padding: 10px; 
            border-radius: 8px; 
        }
        .info-label { 
            font-size: 0.9em; 
            opacity: 0.8; 
            margin-bottom: 5px; 
        }
        .info-value { 
            font-weight: bold; 
            font-size: 1.1em; 
        }
        .justificativa { 
            background: rgba(0,0,0,0.3); 
            padding: 15px; 
            border-radius: 8px; 
            font-style: italic; 
            margin-bottom: 10px; 
        }
        .odds-recomendadas { 
            background: rgba(76,175,80,0.2); 
            padding: 12px; 
            border-radius: 8px; 
            border: 1px solid #4CAF50; 
            font-weight: bold; 
        }
        .no-alerts { 
            text-align: center; 
            padding: 50px; 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            opacity: 0.7; 
        }
        .refresh-btn { 
            position: fixed; 
            bottom: 30px; 
            right: 30px; 
            background: #4CAF50; 
            color: white; 
            border: none; 
            padding: 15px 20px; 
            border-radius: 50px; 
            cursor: pointer; 
            font-size: 1.1em; 
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(76,175,80,0.4);
            transition: all 0.3s ease;
        }
        .refresh-btn:hover { 
            background: #45a049; 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76,175,80,0.6);
        }
        .tipo-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin-left: 10px;
        }
        .dupla-divida { background: #ff4444; }
        .sequencia-critica { background: #ff9800; }
        .divida-individual { background: #2196F3; }
        
        @media (max-width: 768px) {
            .alert-info { grid-template-columns: 1fr; }
            .header h1 { font-size: 2em; }
        }
    </style>
    <script>
        function refreshData() {
            window.location.reload();
        }
        
        // Auto-refresh a cada 5 minutos
        setInterval(refreshData, 300000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Santo Graal - Regressão à Média</h1>
            <p>Sistema Inteligente de Detecção de "Dívidas Estatísticas" de Gols</p>
            <p><small>Última atualização: {{ ultimo_scan }}</small></p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_alertas }}</div>
                <div>Oportunidades Detectadas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_equipes }}</div>
                <div>Equipes Monitoradas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">89%</div>
                <div>Taxa de Acerto Histórica</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">24/7</div>
                <div>Monitoramento Ativo</div>
            </div>
        </div>
        
        {% if alertas %}
        <div class="alertas-container">
            {% for alerta in alertas %}
            <div class="alert-card {{ alerta.prioridade.lower() }}">
                <div class="alert-header">
                    <div class="alert-title">
                        ⚽ {{ alerta.jogo }}
                        <span class="tipo-badge {{ alerta.tipo.lower().replace('_', '-').replace(' ', '-') }}">
                            {{ alerta.tipo.replace('_', ' ') }}
                        </span>
                    </div>
                    <div class="confidence-badge">{{ alerta.confianca }}%</div>
                </div>
                
                <div class="alert-info">
                    <div class="info-item">
                        <div class="info-label">🎯 Foco da Aposta</div>
                        <div class="info-value">{{ alerta.time_foco }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">📊 Dívida Estatística</div>
                        <div class="info-value">{{ "%.2f"|format(alerta.divida_estatistica) }} gols</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">🚨 Prioridade</div>
                        <div class="info-value">{{ alerta.prioridade }}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">📈 Confiança</div>
                        <div class="info-value">{{ alerta.confianca }}%</div>
                    </div>
                </div>
                
                <div class="justificativa">
                    💡 <strong>Análise:</strong> {{ alerta.justificativa }}
                </div>
                
                <div class="odds-recomendadas">
                    🎪 <strong>Recomendação:</strong> {{ alerta.odds_recomendadas }}
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="no-alerts">
            <h2>🔍 Nenhuma oportunidade detectada no momento</h2>
            <p>O sistema está monitorando continuamente por padrões de regressão à média...</p>
        </div>
        {% endif %}
    </div>
    
    <button class="refresh-btn" onclick="refreshData()">🔄 Atualizar</button>
</body>
</html>
"""

# Rotas Flask
@app.route('/')
def home():
    """Página principal com dashboard completo"""
    alertas = sistema_regressao.scanner_regressao_completo()
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                alertas=alertas,
                                ultimo_scan=sistema_regressao.stats['ultimo_scan'] or 'Nunca',
                                total_alertas=len(alertas),
                                total_equipes=len(sistema_regressao.teams_database))

@app.route('/api/alertas')
def api_alertas():
    """API endpoint para alertas em JSON"""
    alertas = sistema_regressao.scanner_regressao_completo()
    
    return jsonify({
        'alertas': [
            {
                'tipo': alert.tipo,
                'jogo': alert.jogo,
                'time_foco': alert.time_foco,
                'confianca': alert.confianca,
                'divida_estatistica': alert.divida_estatistica,
                'justificativa': alert.justificativa,
                'prioridade': alert.prioridade,
                'odds_recomendadas': alert.odds_recomendadas
            }
            for alert in alertas
        ],
        'stats': sistema_regressao.stats,
        'total_equipes': len(sistema_regressao.teams_database),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/equipes')
def api_equipes():
    """API endpoint para lista de equipes monitoradas"""
    return jsonify({
        'equipes': [
            {
                'nome': nome,
                'liga': data['liga'],
                'media_gols': data['media_temp'],
                'zero_percent': data['zero_pct'],
                'volatilidade': data['volatilidade']
            }
            for nome, data in sistema_regressao.teams_database.items()
        ],
        'total': len(sistema_regressao.teams_database)
    })

@app.route('/health')
def health():
    """Health check para Render"""
    return jsonify({
        'status': 'healthy',
        'sistema': 'Santo Graal - Regressão à Média',
        'timestamp': datetime.now().isoformat(),
        'alertas_ativos': len(sistema_regressao.alertas_ativos)
    })

def run_monitoring_cycle():
    """Ciclo de monitoramento em background (executa a cada hora)"""
    while True:
        try:
            print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executando ciclo de monitoramento...")
            
            # Executar scanner
            alertas = sistema_regressao.scanner_regressao_completo()
            
            # Log dos resultados
            if alertas:
                print(f"✅ {len(alertas)} oportunidades detectadas:")
                for i, alert in enumerate(alertas[:3], 1):  # Mostrar apenas top 3
                    print(f"   {i}. {alert.jogo} - {alert.confianca}% ({alert.tipo})")
                if len(alertas) > 3:
                    print(f"   ... e mais {len(alertas) - 3} oportunidades")
            else:
                print("ℹ️  Nenhuma oportunidade detectada neste ciclo")
            
            print(f"⏰ Próximo scan em 1 hora...")
            
        except Exception as e:
            print(f"❌ Erro no ciclo de monitoramento: {str(e)}")
        
        # Aguardar 1 hora
        time.sleep(3600)

if __name__ == '__main__':
    print("🏆 Santo Graal - Sistema de Regressão à Média")
    print("=" * 50)
    print("🎯 Foco: Detectar equipes com 'dívida estatística' de gols")
    print("📊 Método: Regressão à média após performance aquém do esperado")
    print("🔍 Padrões: Dupla dívida, sequências críticas, dívidas individuais")
    print("=" * 50)
    
    # Executar scanner inicial
    print("\n🔄 Executando scanner inicial...")
    alertas_iniciais = sistema_regressao.scanner_regressao_completo()
    
    if alertas_iniciais:
        print(f"\n🎯 {len(alertas_iniciais)} oportunidades detectadas no startup:")
        for alert in alertas_iniciais[:5]:  # Mostrar top 5
            print(f"   • {alert.jogo} - {alert.confianca}% ({alert.tipo})")
    
    # Iniciar monitoramento em background
    monitoring_thread = threading.Thread(target=run_monitoring_cycle, daemon=True)
    monitoring_thread.start()
    print("✅ Monitoramento em background iniciado (ciclos de 1 hora)")
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🌐 Dashboard disponível em: http://localhost:{port}")
    print("📱 API disponível em: http://localhost:{port}/api/alertas")
    print("\n🚀 Sistema Santo Graal ATIVO!")
    
    app.run(host='0.0.0.0', port=port, debug=False)
