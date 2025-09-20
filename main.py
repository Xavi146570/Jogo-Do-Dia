import requests
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
    "Manchester City", "Arsenal", "Liverpool", "Manchester United", "Chelsea",
    "Real Madrid", "Barcelona", "Atletico Madrid", "Girona",
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    "Inter", "AC Milan", "Juventus", "Napoli",
    "Paris Saint Germain", "Lyon", "Monaco", "Lille", "Marseille",
    "Benfica", "Porto", "Sporting CP", "Braga",
    "Ajax", "PSV Eindhoven", "Feyenoord", "AZ Alkmaar",
    "Celtic", "Rangers",
    "Palmeiras", "Flamengo", "Internacional", "Gremio", "Atletico Mineiro", "Corinthians", "Fluminense",
    "Boca Juniors", "River Plate", "Racing Club", "Rosario Central",
    "Shanghai Port", "Shanghai Shenhua", "Shandong Luneng", "Chengdu Rongcheng"
]

# ======================================
# Funções auxiliares
# ======================================
def enviar_telegram(msg: str):
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
    url = f"{BASE_URL}/teams/statistics?team={equipe_id}&league={league_id}&season={season}"
    r = requests.get(url, headers=HEADERS).json()
    if "response" not in r or not r["response"]:
        return None
    stats = r["response"]
    media_gols = stats["goals"]["for"]["average"]["total"]
    perc_vitorias = stats["fixtures"]["wins"]["total"] / stats["fixtures"]["played"]["total"] * 100
    return media_gols, perc_vitorias

def buscar_ultimo_jogo(equipe_id):
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
    agora_utc = datetime.now(timezone.utc)
    daqui_24h_utc = agora_utc + timedelta(hours=24)
    hoje_str = agora_utc.date().isoformat()
    amanha_str = daqui_24h_utc.date().isoformat()

    print(f"[{datetime.now().strftime('%H:%M %d/%m')}] 🔎 Verificando jogos das equipas de elite nas próximas 24h...")

    encontrados = 0
    jogos_monitorados = []

    # Busca todos os jogos entre hoje e amanhã
    url_all_fixtures = f"{BASE_URL}/fixtures?from={hoje_str}&to={amanha_str}"
    try:
        r = requests.get(url_all_fixtures, headers=HEADERS).json()
        jogos = r.get("response", [])
    except Exception as e:
        enviar_telegram(f"❌ Erro na requisição principal da API: {e}")
        return
        
    print(f"📌 API retornou {len(jogos)} jogos no total para as próximas 24h.")
    
    for jogo in jogos:
        home = jogo["teams"]["home"]["name"]
        away = jogo["teams"]["away"]["name"]
        data_jogo_utc = datetime.fromisoformat(jogo["fixture"]["date"].replace("Z", "+00:00"))
        
        # Apenas jogos que ainda não começaram e estão dentro das próximas 24h
        if agora_utc < data_jogo_utc <= daqui_24h_utc:
            if home in EQUIPAS_DE_TITULO or away in EQUIPAS_DE_TITULO:
                # Verifica se o jogo já foi processado para evitar duplicatas
                if jogo["fixture"]["id"] not in [j["id"] for j in jogos_monitorados]:
                    jogos_monitorados.append({"id": jogo["fixture"]["id"], "data": jogo})
                    encontrados += 1
                    
                    equipe_id = jogo["teams"]["home"]["id"] if home in EQUIPAS_DE_TITULO else jogo["teams"]["away"]["id"]
                    league_id = jogo["league"]["id"]
                    season = jogo["league"]["season"]
                    
                    stats = buscar_estatisticas(equipe_id, league_id, season)
                    ultimo_jogo = buscar_ultimo_jogo(equipe_id)
                    
                    data_jogo_lisboa = data_jogo_utc.astimezone(ZoneInfo("Europe/Lisbon"))
                    falta = formatar_contagem_regressiva(data_jogo_utc - agora_utc)
                    
                    if stats:
                        media_gols, perc_vitorias = stats
                        msg = (
                            f"🏆 <b>Equipa de Elite em campo</b> 🏆\n"
                            f"⏰ {data_jogo_lisboa.strftime('%H:%M')} (hora Lisboa) - {home} vs {away}\n"
                            f"⏳ Começa em {falta}\n\n"
                            f"📊 Estatísticas recentes do <b>{home if home in EQUIPAS_DE_TITULO else away}</b>:\n"
                            f"• Gols/jogo: {media_gols}\n"
                            f"• Vitórias: {perc_vitorias:.1f}%\n"
                            f"• Último resultado: {ultimo_jogo}\n\n"
                            f"⚔️ Esta equipa normalmente luta pelo título!"
                        )
                        enviar_telegram(msg)
                        
    if encontrados == 0:
        enviar_telegram(f"⚽ Nenhum jogo de equipa monitorada encontrado nas próximas 24h ({datetime.now().strftime('%H:%M %d/%m')}).")

# Executar
if __name__ == "__main__":
    verificar_jogos()
