import requests
import os
from datetime import datetime, timedelta

# Variáveis de ambiente (configure no Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

# Equipas de interesse
EQUIPAS_DE_INTERESSE = [
    "Manchester City", "Arsenal", "Liverpool",
    "Sporting CP", "Benfica", "Porto",
    "Feyenoord", "PSV Eindhoven", "Ajax",
    "Shanghai Port", "Shanghai Shenhua", "Chengdu Rongcheng",
    "Palmeiras", "Celtic",
    "Barcelona", "Real Madrid", "Atlético de Madrid",
    "Bayern de Munique", "Bayer Leverkusen", "Borussia Dortmund"
]

def enviar_telegram(msg: str):
    """Envia mensagem para o Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Erro: Variáveis TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configuradas.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print(f"[{datetime.now().strftime('%H:%M')}] ✅ Mensagem enviada para o Telegram")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M')}] ❌ Erro ao enviar para o Telegram: {e}")

def get_last_match(team_id):
    """Obtém o último jogo finalizado da equipa"""
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"team": team_id, "last": 1}
    headers = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        data = r.json()
        if data.get("response"):
            return data["response"][0]
    except Exception as e:
        print(f"Erro ao buscar último jogo da equipa {team_id}: {e}")
    return None

def media_gols(team_id):
    """Calcula a média de gols marcados + sofridos por jogo"""
    url = "https://v3.football.api-sports.io/teams/statistics"
    querystring = {"team": team_id, "season": datetime.now().year, "league": ""}
    headers = {"x-apisports-key": API_KEY}
    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        stats = r.json().get("response", {})
        if stats:
            played = stats["fixtures"]["played"]["total"]
            goals_for = stats["goals"]["for"]["total"]["total"]
            goals_against = stats["goals"]["against"]["total"]["total"]
            if played > 0:
                return (goals_for + goals_against) / played
    except Exception as e:
        print(f"Erro ao calcular média de gols da equipa {team_id}: {e}")
    return 0

def buscar_jogos():
    """Procura jogos e envia para o Telegram"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos para {hoje}...")

    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": hoje}
    headers = {"x-apisports-key": API_KEY}

    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        dados = r.json()
    except requests.exceptions.RequestException as e:
        enviar_telegram(f"❌ Erro ao buscar jogos: {e}")
        return

    jogos_validos = []
    jogos_proximos = []

    for match in dados.get("response", []):
        casa = match["teams"]["home"]["name"]
        fora = match["teams"]["away"]["name"]
        id_casa = match["teams"]["home"]["id"]
        id_fora = match["teams"]["away"]["id"]

        if casa in EQUIPAS_DE_INTERESSE or fora in EQUIPAS_DE_INTERESSE:
            media_casa = media_gols(id_casa)
            media_fora = media_gols(id_fora)
            media_total = (media_casa + media_fora) / 2

            ultimo_casa = get_last_match(id_casa)
            ultimo_fora = get_last_match(id_fora)

            terminou_crit = False
            terminou_prox = False

            # Último jogo 0x0, 1x0 ou 0x1 = critério principal
            if ultimo_casa:
                g_casa = ultimo_casa["teams"]["home"]["goals"]
                g_fora = ultimo_casa["teams"]["away"]["goals"]
                if (g_casa, g_fora) in [(0,0),(1,0),(0,1)]:
                    terminou_crit = True
                elif (g_casa, g_fora) in [(1,0),(0,1)]:
                    terminou_prox = True

            if ultimo_fora and not terminou_crit:
                g_casa = ultimo_fora["teams"]["home"]["goals"]
                g_fora = ultimo_fora["teams"]["away"]["goals"]
                if (g_casa, g_fora) in [(0,0),(1,0),(0,1)]:
                    terminou_crit = True
                elif (g_casa, g_fora) in [(1,0),(0,1)]:
                    terminou_prox = True

            hora = datetime.fromtimestamp(match["fixture"]["timestamp"]).strftime("%H:%M")
            descricao = f"⚽ {hora} - {casa} vs {fora}\nMédia gols: {media_total:.2f}"

            if media_total > 2.3 and terminou_crit:
                jogos_validos.append(descricao)
            elif media_total > 2.3 and terminou_prox:
                jogos_proximos.append(descricao)

    if jogos_validos:
        msg = "🔥 JOGO TOP DO DIA 🔥\nSugestão Over 1.5 gols\n\n" + "\n\n".join(jogos_validos)
    elif jogos_proximos:
        msg = "🔥 JOGO TOP DO DIA 🔥\nSugestão Over 1.5 gols\n⚠️ Jogo próximo dos critérios\n\n" + "\n\n".join(jogos_proximos)
    else:
        msg = f"⚽ Nenhum jogo encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')})."

    enviar_telegram(msg)

if __name__ == "__main__":
    buscar_jogos()
