/home/user/teste_api_key.py
import requests
import os

# Teste rápido da API Key
API_KEY = os.environ.get("LIVESCORE_API_KEY")

if not API_KEY:
    print("❌ ERRO: LIVESCORE_API_KEY não configurada!")
    print("\n🔧 CONFIGURAÇÃO NECESSÁRIA:")
    print("export LIVESCORE_API_KEY='968c152b0a72f3fa63087d74b04eee5d'")
    print("\n📌 Para obter uma chave:")
    print("1. Acesse: https://www.api-football.com/")
    print("2. Registre-se gratuitamente")
    print("3. Copie sua API Key")
    exit(1)

print(f"🔑 API Key encontrada: {API_KEY[:10]}...{API_KEY[-5:]}")

# Teste básico
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

try:
    print("\n🧪 Testando conexão com API...")
    response = requests.get(f"{BASE_URL}/status", headers=HEADERS, timeout=10)
    
    print(f"📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API funcionando!")
        
        if 'response' in data:
            status = data['response']
            print(f"📈 Requests restantes hoje: {status.get('requests', {}).get('current', 'N/A')}")
            print(f"📊 Limite diário: {status.get('requests', {}).get('limit_day', 'N/A')}")
        
    elif response.status_code == 401:
        print("❌ ERRO 401: API Key inválida!")
        print("Verifique se copiou a chave corretamente")
        
    elif response.status_code == 429:
        print("❌ ERRO 429: Limite de requests excedido!")
        print("Aguarde um tempo ou use uma nova chave")
        
    else:
        print(f"❌ ERRO {response.status_code}: {response.text}")

except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    print("Verifique sua internet e tente novamente")

print("\n" + "="*50)
print("Se API está OK, execute: python debug_girona_valencia.py")
