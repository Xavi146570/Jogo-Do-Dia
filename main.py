import requests
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo   # Disponível no Python 3.9+

# Variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# ==============================
# EQUIPAS QUE LUTAM PELO TÍTULO
# ==============================
EQUIPAS_DE_TITULO = [
    # Inglaterra
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea",
    # Espanha
    "Real Madrid", "Barcelona", "Atletico Madrid", "Girona",
    # Alemanha
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    # Itália
    "Inter", "AC Milan", "Juventus", "Napoli",
    # França
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille",
    # Portugal
    "Benfica", "Porto", "Sporting CP", "Braga",
    # Holanda
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar",
    # Escócia
    "Celtic", "Rangers",
    # Brasil
    "Palmeiras", "Flamengo", "Internacional", "Gremio", "Atletico Mineiro", "Corinthians", "Fluminense",
    # Argentina
    "Boca Juniors", "River Plate", "Racing Club", "Rosario Central",
    # China
    "Shanghai Port", "Shanghai Shenhua", "Shandong Luneng", "Chengdu Rongcheng"
]

# ======================================
# Funções auxiliares
# ======================================
def enviar_telegram(msg: str):
    """Envia mensagem para o Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Variáveis TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configuradas.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print(f"[{datetime.now().strftime('%H:%M')}] ✅ Mensagem enviada para o Telegram")
    except Exception as e:
        print("Erro ao enviar mensagem:", e)

def buscar_estatisticas(equipe_id, league_id, season):
    """Busca estatísticas de uma equipa na API"""
    url = f"{BASE_URL}/teams/statistics?team={equipe_id}&league={league_id}&season={season}"
    r = requests.get(url, headers=HEADERS).json()
    if "response" not in r or not r["response"]:
        return None
    stats = r["response"]
    media_gols = stats["goals"]["for"]["average"]["total"]
    perc_vitorias = stats["fixtures"]["wins"]["total"] / stats["fixtures"]["played"]["total"] * 100
    return media_gols, perc_vitorias

def buscar_ultimo_jogo(equipe_id):
    """Busca o último jogo de uma equipa"""
    url = f"{BASE_URL}/fixtures?team={equipe_id}&last=1"
    r = requests.get(url, headers=HEADERS).json()
    if "response" not in r or not r["response"]:
        return None
    jogo = r["response"][0]
    mandante = jogo["teams"]["home"]["name"]
    visitante = jogo["teams"]["away"]["name"]
    placar = f"{jogo['goals']['home']}x{jogo['goals']['away']}"
    return f"{mandante} {placar} {visitante}"

def formatar_contagem_regressiva(delta: timedelta) -> str:
    """Formata um timedelta em 'Xh Ymin'"""
    horas, resto = divmod(int(delta.total_seconds()), 3600)
    minutos = resto // 60
    if horas > 0:
        return f"{horas}h {minutos}min"
    else:
        return f"{minutos}min"

# ======================================
# Função principal
# ======================================
def verificar_jogos():
    agora_utc = datetime.utcnow()
    daqui_24h = agora_utc + timedelta(hours=24)

    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos nas próximas 24h...")

    # Buscar próximos 200 jogos
    url = f"{BASE_URL}/fixtures?next=200"
    r = requests.get(url, headers=HEADERS).json()

    if "response" not in r or not r["response"]:
        enviar_telegram("⚽ Nenhum jogo encontrado nas próximas 24 horas.")
        return

    for jogo in r["response"]:
        home = jogo["teams"]["home"]["name"]
        away = jogo["teams"]["away"]["name"]
        data_jogo_utc = datetime.fromisoformat(jogo["fixture"]["date"].replace("Z", "+00:00"))

        # Converter horário para Lisboa
        data_jogo_lisboa = data_jogo_utc.astimezone(ZoneInfo("Europe/Lisbon"))

        # ⚠️ Filtrar só jogos dentro das próximas 24h e que ainda não começaram
        if agora_utc < data_jogo_utc <= daqui_24h:
            horario = data_jogo_lisboa.strftime("%H:%M")
            falta = formatar_contagem_regressiva(data_jogo_utc - agora_utc)

            if home in EQUIPAS_DE_TITULO or away in EQUIPAS_DE_TITULO:
                equipa = home if home in EQUIPAS_DE_TITULO else away

                # Estatísticas e último jogo
                league_id = jogo["league"]["id"]
                season = jogo["league"]["season"]
                equipe_id = jogo["teams"]["home"]["id"] if home == equipa else jogo["teams"]["away"]["id"]

                stats = buscar_estatisticas(equipe_id, league_id, season)
                ultimo_jogo = buscar_ultimo_jogo(equipe_id)

                if stats:
                    media_gols, perc_vitorias = stats
                    msg = (
                        f"🏆 <b>Equipa de Elite em campo</b> 🏆\n"
                        f"⏰ {horario} (hora Lisboa) - {home} vs {away}\n"
                        f"⏳ Começa em {falta}\n\n"
                        f"📊 Estatísticas recentes do <b>{equipa}</b>:\n"
                        f"• Gols/jogo: {media_gols}\n"
                        f"• Vitórias: {perc_vitorias:.1f}%\n"
                        f"• Último resultado: {ultimo_jogo}\n\n"
                        f"⚔️ Esta equipa normalmente luta pelo título!"
                    )
                    enviar_telegram(msg)

# Executar
if __name__ == "__main__":
    verificar_jogos()
