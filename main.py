import requests
import os
from datetime import datetime

# Variáveis de ambiente (configure no Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

def enviar_telegram(msg: str):
    """Envia mensagem para o Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Erro: A variável de ambiente TELEGRAM_BOT_TOKEN não está configurada.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M %d/%m')}] ❌ Erro ao enviar para o Telegram: {e}")

def buscar_jogos():
    """Procura jogos na API e envia para o Telegram."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos para {hoje}...")
    
    # AQUI ESTÁ A MUDANÇA
    # Verificação para garantir que a API Key existe
    if not API_KEY:
        enviar_telegram("❌ Erro: A chave da API de futebol (LIVESCORE_API_KEY) não está configurada corretamente no Render.")
        return
        
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": hoje}
    headers = {
        'x-rapidapi-key': API_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }

    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        dados = r.json()
    except requests.exceptions.RequestException as e:
        enviar_telegram(f"❌ Erro ao buscar jogos: {e}")
        return

    jogos = []
    for match in dados.get("response", []):
        casa = match["teams"]["home"]["name"]
        fora = match["teams"]["away"]["name"]
        hora = datetime.fromtimestamp(match["fixture"]["timestamp"]).strftime("%H:%M")

        jogos.append(f"{hora} - {casa} vs {fora}")

    if jogos:
        msg = "🔥 <b>JOGO TOP DO DIA</b> 🔥\n\n" + "\n".join(jogos)
    else:
        msg = f"⚽ Nenhum jogo encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')})."

    enviar_telegram(msg)

if __name__ == "__main__":
    buscar_jogos()
