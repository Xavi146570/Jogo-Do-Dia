import requests
import os
from datetime import datetime, timedelta

# Variáveis de ambiente (configure no Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Dicionário de equipas fixas
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
        print(f"❌ Erro ao enviar para Telegram: {e}")


def buscar_ultimo_jogo(team_id, season):
    """Retorna o último jogo finalizado da equipa"""
    url = f"{BASE_URL}/fixtures"
    params = {"team": team_id, "season": season, "status": "FT"}
    try:
        r = requests.get(url, headers=HEADERS, params=params).json()
        jogos = r.get("response", [])
        if not jogos:
            return None
        # Ordena por data e pega o mais recente
        jogos.sort(key=lambda x: x["fixture"]["timestamp"], reverse=True)
        return jogos[0]
    except Exception as e:
        print(f"Erro ao buscar último jogo: {e}")
        return None


def media_golos(stats):
    """Calcula média de golos por jogo"""
    try:
        jogos = stats["fixtures"]["played"]["total"]
        gm = stats["goals"]["for"]["total"]["total"]
        gs = stats["goals"]["against"]["total"]["total"]
        return (gm + gs) / jogos if jogos > 0 else 0
    except:
        return 0


def buscar_jogo_top():
    """Procura jogos válidos para Over 1.5"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos para {hoje}...")

    url = f"{BASE_URL}/fixtures"
    params = {"date": hoje}
    try:
        res = requests.get(url, headers=HEADERS, params=params).json()
        jogos = res.get("response", [])
    except Exception as e:
        enviar_telegram(f"❌ Erro ao buscar jogos: {e}")
        return

    jogos_validos = []
    candidatos_proximos = []

    for jogo in jogos:
        casa = jogo["teams"]["home"]["name"]
        fora = jogo["teams"]["away"]["name"]
        hora = datetime.fromtimestamp(jogo["fixture"]["timestamp"]).strftime("%H:%M")
        season = jogo["league"]["season"]

        for equipa in [casa, fora]:
            # Verifica se equipa é de interesse
            if equipa in EQUIPAS_DE_INTERESSE:
                # Busca estatísticas
                stats_url = f"{BASE_URL}/teams/statistics"
                stats_params = {
                    "league": jogo["league"]["id"],
                    "season": season,
                    "team": jogo["teams"]["home"]["id"] if equipa == casa else jogo["teams"]["away"]["id"],
                }
                stats = requests.get(stats_url, headers=HEADERS, params=stats_params).json().get("response", {})

                if not stats:
                    continue

                media = media_golos(stats)
                ultimo = buscar_ultimo_jogo(stats["team"]["id"], season)

                if ultimo:
                    g_casa = ultimo["goals"]["home"]
                    g_fora = ultimo["goals"]["away"]
                    total = g_casa + g_fora

                    if media > 2.3 and total <= 1:  # jogo anterior under 1.5
                        msg = (f"🔥 JOGO TOP DO DIA 🔥\n"
                               f"⏰ {hora} - {casa} vs {fora}\n"
                               f"⚽ {equipa} ({EQUIPAS_DE_INTERESSE[equipa]})\n"
                               f"📊 Média de {media:.2f} golos/jogo\n"
                               f"Último jogo terminou {g_casa}x{g_fora}\n\n"
                               f"Sugestão: Over 1.5 golos")
                        jogos_validos.append(msg)
                    else:
                        msg = (f"⚠️ Jogo próximo dos critérios\n"
                               f"⏰ {hora} - {casa} vs {fora}\n"
                               f"⚽ {equipa} ({EQUIPAS_DE_INTERESSE[equipa]})\n"
                               f"📊 Média de {media:.2f} golos/jogo\n"
                               f"Último jogo terminou {g_casa}x{g_fora}")
                        candidatos_proximos.append(msg)

    if jogos_validos:
        enviar_telegram("\n\n".join(jogos_validos))
    elif candidatos_proximos:
        enviar_telegram("\n\n".join(candidatos_proximos))
    else:
        enviar_telegram(f"⚽ Nenhum jogo encontrado nesta execução ({datetime.now().strftime('%H:%M %d/%m')}).")


if __name__ == "__main__":
    buscar_jogo_top()

