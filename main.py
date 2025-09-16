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
        print("❌ Erro: TELEGRAM_BOT_TOKEN não está configurado.")
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
        print(f"[{datetime.now().strftime('%H:%M')}] ✅ Mensagem enviada para o Telegram")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M')}] ❌ Erro ao enviar para o Telegram: {e}")

def get_media_gols(equipe_id, liga_id, temporada):
    """Busca a média de gols por jogo (marcados + sofridos) da equipa."""
    url = "https://v3.football.api-sports.io/teams/statistics"
    querystring = {"league": liga_id, "season": temporada, "team": equipe_id}
    headers = {"x-apisports-key": API_KEY}

    print(f"➡️ Request para estatísticas: {url} params={querystring}")

    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        dados = r.json()
        media_marcados = float(dados["response"]["goals"]["for"]["average"]["total"])
        media_sofridos = float(dados["response"]["goals"]["against"]["average"]["total"])
        return media_marcados + media_sofridos
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas da equipa {equipe_id}: {e}")
        return 0

def get_ultimo_resultado(equipe_id, temporada):
    """Busca o último resultado da equipa e retorna alerta se terminou 0x0, 1x0 ou 0x1."""
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"season": temporada, "team": equipe_id, "last": 1}
    headers = {"x-apisports-key": API_KEY}

    print(f"➡️ Request para último resultado: {url} params={querystring}")

    try:
        r = requests.get(url, headers=headers, params=querystring)
        r.raise_for_status()
        dados = r.json()
        jogos = dados.get("response", [])
        if not jogos:
            return ""

        jogo = jogos[0]
        gols_casa = jogo["goals"]["home"]
        gols_fora = jogo["goals"]["away"]
        resultado = f"{gols_casa}x{gols_fora}"

        if resultado in ["0x0", "1x0", "0x1"]:
            return f"⚠️ Atenção: Último jogo terminou {resultado}."
        return ""
    except Exception as e:
        print(f"❌ Erro ao buscar último resultado da equipa {equipe_id}: {e}")
        return ""

def buscar_jogos():
    """Procura jogos na API e envia para o Telegram."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos para {hoje}...")
    
    if not API_KEY:
        enviar_telegram("❌ Erro: A chave da API de futebol (LIVESCORE_API_KEY) não está configurada.")
        return
        
    url = "https://v3.football.api-sports.io/fixtures"
    querystring = {"date": hoje}
    headers = {"x-apisports-key": API_KEY}

    print(f"➡️ Request principal: {url} params={querystring}")

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
        liga_id = match["league"]["id"]
        temporada = match["league"]["season"]

        if casa in EQUIPAS_DE_INTERESSE or fora in EQUIPAS_DE_INTERESSE:
            hora = datetime.fromtimestamp(match["fixture"]["timestamp"]).strftime("%H:%M")

            if casa in EQUIPAS_DE_INTERESSE:
                equipa_id = match["teams"]["home"]["id"]
                equipa = casa
            else:
                equipa_id = match["teams"]["away"]["id"]
                equipa = fora

            media_gols = get_media_gols(equipa_id, liga_id, temporada)

            if media_gols > 2.3:
                alerta = get_ultimo_resultado(equipa_id, temporada)
                mensagem_jogo = (
                    f"🔥 JOGO TOP DO DIA 🔥\n"
                    f"⏰ {hora} - {casa} vs {fora}\n"
                    f"⚽ {equipa} (Liga: {EQUIPAS_DE_INTERESSE[equipa]})\n"
                    f"📊 Média de gols/jogo: {media_gols:.2f}\n"
                    f"{alerta}\n\n"
                    f"👉 Sugestão: Over 1.5 gols"
                )
                jogos_encontrados.append(mensagem_jogo)

    if jogos_encontrados:
        msg = "\n\n".join(jogos_encontrados)
    else:
        msg = f"⚽ Nenhum jogo válido encontrado hoje ({datetime.now().strftime('%H:%M %d/%m')})."
    enviar_telegram(msg)

if __name__ == "__main__":
    buscar_jogos()
