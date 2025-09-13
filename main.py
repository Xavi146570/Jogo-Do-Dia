import requests
import os
from datetime import datetime

# 🔑 Variáveis de ambiente (configure no Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_KEY = os.environ.get("LIVESCORE_API_KEY")

# ⚽ Equipas de interesse fixas
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
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Erro: Variável TELEGRAM_BOT_TOKEN não configurada.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M %d/%m')}] ❌ Erro Telegram: {e}")

def verificar_condicoes(team_id, league_id):
    """Verifica se equipa/seleção tem Over 1.5 alto e último jogo ≤ 1 golo"""
    headers = {"x-apisports-key": API_KEY}

    # 📊 Estatísticas da equipa
    url_stats = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season={datetime.now().year}&team={team_id}"
    try:
        r = requests.get(url_stats, headers=headers)
        r.raise_for_status()
        stats = r.json().get("response", {})
    except Exception as e:
        print(f"Erro estatísticas: {e}")
        return False, None

    over15 = stats.get("goals", {}).get("for", {}).get("over", {}).get("1.5", 0)
    if over15 < 70:  # só aceita se tiver ≥70% Over 1.5
        return False, None

    # 📅 Último jogo
    url_last = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=1"
    try:
        r = requests.get(url_last, headers=headers)
        r.raise_for_status()
        last_game = r.json().get("response", [])[0]
    except Exception as e:
        print(f"Erro último jogo: {e}")
        return False, None

    gols_casa = last_game["goals"]["home"]
    gols_fora = last_game["goals"]["away"]
    total_gols = gols_casa + gols_fora

    # Aceita últimos jogos terminados em 0x0, 1x0 ou 0x1
    if total_gols <= 1:
        return True, f"{last_game['teams']['home']['name']} {gols_casa}x{gols_fora} {last_game['teams']['away']['name']}"

    return False, None

def buscar_jogos():
    """Procura jogos e envia para o Telegram"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos de {hoje}...")

    headers = {"x-apisports-key": API_KEY}
    url = "https://v3.football.api-sports.io/fixtures"
    query = {"date": hoje}

    try:
        r = requests.get(url, headers=headers, params=query)
        r.raise_for_status()
        dados = r.json()
    except Exception as e:
        enviar_telegram(f"❌ Erro ao buscar jogos: {e}")
        return

    jogos_encontrados = []

    for match in dados.get("response", []):
        casa = match["teams"]["home"]["name"]
        fora = match["teams"]["away"]["name"]
        hora = datetime.fromtimestamp(match["fixture"]["timestamp"]).strftime("%H:%M")

        # ⚽ Caso 1: Equipa fixa de interesse
        if casa in EQUIPAS_DE_INTERESSE or fora in EQUIPAS_DE_INTERESSE:
            equipa = casa if casa in EQUIPAS_DE_INTERESSE else fora
            liga = EQUIPAS_DE_INTERESSE[equipa]
            mensagem = (
                f"🔥 JOGO TOP DO DIA 🔥\n"
                f"{hora} - {casa} vs {fora}\n"
                f"⚽️ {equipa} (Liga: {liga}) joga hoje!\n\n"
                f"💡 Sugestão: Over 1.5 gols"
            )
            jogos_encontrados.append(mensagem)

        # ⚽ Caso 2: Seleções/Outras equipas com filtro estatístico
        else:
            team_id = match["teams"]["home"]["id"]
            league_id = match["league"]["id"]

            passou, ultimo_resultado = verificar_condicoes(team_id, league_id)
            if passou:
                extra_info = f"\n📊 Último jogo: {ultimo_resultado}" if ultimo_resultado else ""
                mensagem = (
                    f"🔥 JOGO TOP DO DIA 🔥\n"
                    f"{hora} - {casa} vs {fora}\n"
                    f"⚠️ Equipa com >70% Over 1.5 e último jogo ≤1 golo.{extra_info}\n\n"
                    f"💡 Sugestão: Over 1.5 gols"
                )
                jogos_encontrados.append(mensagem)

    if jogos_encontrados:
        enviar_telegram("\n\n".join(jogos_encontrados))
    else:
        enviar_telegram(f"⚽ Nenhum jogo encontrado ({datetime.now().strftime('%H:%M %d/%m')}).")

if __name__ == "__main__":
    buscar_jogos()

