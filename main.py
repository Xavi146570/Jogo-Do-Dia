import requests
import os
from datetime import datetime

# Variáveis de ambiente (configura no Render)
API_KEY = os.environ.get("API_KEY")  # chave da API de futebol
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def enviar_telegram(msg: str):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M %d/%m')}] ❌ Erro ao enviar para o Telegram: {e}")

def buscar_jogos():
    """Procura jogos na API e envia para o Telegram"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos para {hoje}...")

    url = f"https://api.football-data.org/v4/matches?dateFrom={hoje}&dateTo={hoje}"
    headers = {"X-Auth-Token": API_KEY}

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        dados = r.json()
    except Exception as e:
        enviar_telegram(f"❌ Erro ao buscar jogos: {e}")
        return

    jogos = []
    for match in dados.get("matches", []):
        # filtra apenas jogos a partir de 2025
        season = match.get("season", {}).get("startDate", "2025")[:5]
        if int(season) < 2025:
            continue

        casa = match["homeTeam"]["name"]
        fora = match["awayTeam"]["name"]
        hora = match["utcDate"][11:16]  # só pega HH:MM

        jogos.append(f"{hora} - {casa} vs {fora}")

    if jogos:
        msg = "🔥 <b>JOGO TOP DO DIA</b> 🔥\n\n" + "\n".join(jogos)
    else:
        msg = f"⚽ Nenhum jogo encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')})."

    enviar_telegram(msg)

if __name__ == "__main__":
    buscar_jogos()

