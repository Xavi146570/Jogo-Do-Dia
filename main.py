import requests
import os
from datetime import datetime

# Variáveis de ambiente (configure no Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

# Dicionário de equipas e ligas para filtrar
EQUIPAS_DE_INTERESSE = {
    "Manchester City": "Inglaterra – Premier League",
    "Arsenal": "Inglaterra – Premier League",
    "Liverpool": "Inglaterra – Premier League",
    "Sporting CP": "Portugal – Primeira Liga",
    "Benfica": "Portugal – Primeira Liga",
    "Porto": "Portugal – Primeira Liga",
    "Feyenoord": "Holanda – Eredivisie",
    "PSV Eindhoven": "Holanda – Eredivisie",
    "Ajax": "Holanda – Eredivisie",
    "Shanghai Port": "China – Chinese Super League",
    "Shanghai Shenhua": "China – Chinese Super League",
    "Chengdu Rongcheng": "China – Chinese Super League",
    "Palmeiras": "Brasil – Brasileirão Série A",
    "Celtic": "Escócia – Scottish Premiership",
    "Barcelona": "Espanha – La Liga",
    "Real Madrid": "Espanha – La Liga",
    "Atlético de Madrid": "Espanha – La Liga",
    "Bayern de Munique": "Alemanha – Bundesliga",
    "Bayer Leverkusen": "Alemanha – Bundesliga",
    "Borussia Dortmund": "Alemanha – Bundesliga"
}

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

    jogos_encontrados = []
    for match in dados.get("response", []):
        casa = match["teams"]["home"]["name"]
        fora = match["teams"]["away"]["name"]

        # Verifica se alguma das equipas no jogo está na nossa lista de interesse
        if casa in EQUIPAS_DE_INTERESSE or fora in EQUIPAS_DE_INTERESSE:
            hora = datetime.fromtimestamp(match["fixture"]["timestamp"]).strftime("%H:%M")
            
            # Determina qual das equipas é de interesse e a sua liga
            if casa in EQUIPAS_DE_INTERESSE:
                liga = EQUIPAS_DE_INTERESSE[casa]
                equipa = casa
            else:
                liga = EQUIPAS_DE_INTERESSE[fora]
                equipa = fora
                
            mensagem_jogo = (
                f"🔥 {hora} - {casa} vs {fora}\n"
                f"⚽️ **{equipa}** joga hoje! (Liga: {liga})\n"
                f"Esta equipa joga hoje e luta pelo título"
            )
            jogos_encontrados.append(mensagem_jogo)

    if jogos_encontrados:
        msg = "\n\n".join(jogos_encontrados)
    else:
        msg = f"⚽ Nenhum jogo das equipas de interesse encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')})."

    enviar_telegram(msg)

if __name__ == "__main__":
    buscar_jogos()
