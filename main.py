import requests
import time
from datetime import datetime, timedelta
import logging
import pytz

# 🔑 COLOQUE A MESMA API KEY QUE FUNCIONOU NO SEU BOT:
API_KEY = "968c152b0a72f3fa63087d74b04eee5d"

# ================================================================

if API_KEY == "968c152b0a72f3fa63087d74b04eee5d":
    print("❌ Coloque sua API Key (a mesma que funcionou no bot)")
    exit(1)

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def make_api_request(endpoint, params=None):
    if params is None:
        params = {}
    
    url = f"{BASE_URL}{endpoint}"
    
    try:
        print(f"🔍 {endpoint}")
        if params:
            print(f"📊 {params}")
        response = requests.get(url, headers=HEADERS, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        result = data.get("response", [])
        print(f"✅ {len(result)} registros")
        return result
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def main():
    print("🔍 DEBUG: Por que Girona vs Valencia não foi detectado?")
    print("="*60)
    
    # Passo 1: Verificar se API funciona
    print("\n1️⃣ TESTANDO API...")
    status = make_api_request("/status")
    if status:
        print("✅ API funcionando")
    
    # Passo 2: Buscar Girona
    print("\n2️⃣ BUSCANDO GIRONA...")
    girona_teams = make_api_request("/teams", {"search": "girona"})
    
    girona_id = None
    for team in girona_teams:
        team_info = team['team']
        print(f"  • {team_info['name']} (ID: {team_info['id']}) - {team_info['country']}")
        if team_info['country'] == "Spain":
            girona_id = team_info['id']
            print(f"    🎯 GIRONA ESPANHOL: ID {girona_id}")
    
    if not girona_id:
        print("❌ Girona não encontrado!")
        return
    
    # Passo 3: Histórico do Girona
    print(f"\n3️⃣ HISTÓRICO DO GIRONA (ID: {girona_id})...")
    
    end_date = datetime.now(pytz.utc)
    start_date = end_date - timedelta(days=21)  # 3 semanas
    
    matches = make_api_request("/fixtures", {
        "team": girona_id,
        "from": start_date.strftime('%Y-%m-%d'),
        "to": end_date.strftime('%Y-%m-%d'),
        "status": "FT"
    })
    
    if matches:
        print(f"📊 Encontrados {len(matches)} jogos finalizados")
        matches_sorted = sorted(matches, key=lambda x: x['fixture']['date'], reverse=True)
        
        encontrou_0x0 = False
        for i, match in enumerate(matches_sorted[:6]):
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            
            goals = match.get('goals', {})
            home_goals = goals.get('home', 0) if goals.get('home') is not None else 0
            away_goals = goals.get('away', 0) if goals.get('away') is not None else 0
            
            score = f"{home_goals}x{away_goals}"
            date = match['fixture']['date'][:10]
            
            is_0x0 = (home_goals == 0 and away_goals == 0)
            is_under = (home_goals + away_goals < 2)
            
            status = ""
            if is_0x0:
                status = " 🔥 0x0!"
                encontrou_0x0 = True
            elif is_under:
                status = " 🎯 Under 1.5"
            
            print(f"  {i+1}. {home} {score} {away} | {date}{status}")
            
            # Procurar Espanyol especificamente
            if "espanyol" in (home + away).lower() and is_0x0:
                print(f"      🎯 GIRONA vs ESPANYOL 0x0 CONFIRMADO!")
        
        if encontrou_0x0:
            print(f"\n🔥 GIRONA VEM DE 0x0 - DEVERIA TER GERADO ALERTA!")
        else:
            print(f"\n⚠️ Girona não vem de 0x0 nos últimos jogos")
    
    # Passo 4: Buscar jogo de hoje
    print(f"\n4️⃣ JOGO DE HOJE...")
    today = datetime.now(pytz.utc).strftime('%Y-%m-%d')
    
    # Tentar diferentes status
    statuses = ["NS", "1H", "HT", "2H", "FT", "LIVE"]
    
    for status in statuses:
        fixtures = make_api_request("/fixtures", {
            "date": today,
            "status": status
        })
        
        for fixture in fixtures:
            home = fixture['teams']['home']['name']
            away = fixture['teams']['away']['name']
            
            if (fixture['teams']['home']['id'] == girona_id or 
                fixture['teams']['away']['id'] == girona_id):
                
                print(f"🎯 GIRONA HOJE: {home} vs {away}")
                print(f"   Status: {fixture['fixture']['status']['long']}")
                print(f"   Liga: {fixture['league']['name']}")
                print(f"   Horário: {fixture['fixture']['date']}")
                
                if "valencia" in (home + away).lower():
                    print(f"   🔥 CONTRA VALENCIA!")
    
    print("\n" + "="*60)
    print("📋 DIAGNÓSTICO:")
    if encontrou_0x0:
        print("✅ Girona vem de 0x0")
        print("🔥 ESTE CASO DEVERIA TER SIDO DETECTADO!")
        print("\n💡 POSSÍVEIS PROBLEMAS NO BOT:")
        print("   1. Filtro de liga muito restritivo")
        print("   2. Busca apenas jogos 'NS' (Not Started)")
        print("   3. Range de datas inadequado")
        print("   4. ID da La Liga incorreto")
    else:
        print("❌ Girona não vem de 0x0 recente")

if __name__ == "__main__":
    main()
